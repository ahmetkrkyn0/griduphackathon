"""Merkez API — uygulama fabrikasi (Kisi B).

Calistirma (Dockerfile):  uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
Uc sozlesmesi: contracts/openapi.yaml — alan adlari oradan degismez.

Sozlesmeler uygulama olusturulurken okunur: /contracts bagli degilse veya bir dosya
bozuksa servis HIC ayaga kalkmaz (yanlis esikle calismaktansa gurultulu hata).
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .alarm_service import AlarmService, PeriodicWorker
from .api import alarms, insights, panels, stream
from .api.stream import StreamHub
from .api.views import REQUIRED_HYPOTHESES, panel_summary
from .config import Contracts, Settings, digest_at_from_env, load_contracts
from .db import Store, StoreError
from .ingest import IngestPipeline, MqttSubscriber, utcnow
from .models import Sample
from .notify.dispatcher import Notifier, NotifyConfig, channels_from_env
from .scada.encoder import PanelEncoder
from .scada.gateway import CommandSink, ScadaGateway, parse_units
from .scada.iec104_points import PointCatalog
from .scada.iec104_server import Iec104Server
from .scada.map_loader import RegisterMap, load_map
from .scada.modbus_tcp import ModbusTcpServer
from .scada.service import GatewayStations, ScadaService

log = logging.getLogger("gridup")


def _central_detector(settings: Settings):
    """panoalgo merkez dedektorunu yukler (TB2 Adim 4); yoksa GURULTULU sekilde gecer.

    Neden servisi durdurmuyoruz: merkez dedektor bir EMNIYET AGIDIR, birincil yol degil.
    Asil tespit kenarda calisir ve sonucu telemetri yukunun `alarms` alanindadir; o yol
    bu import olmadan da isler. Kutuphane gelmediginde sessizce devam etmek ise kabul
    edilemez — o yuzden hata seviyesinde loglanir (PLAN.md: sessiz basarisizlik yok).

    Imaj kurulumu: backend/Dockerfile libs/panoalgo'yu kopyalar ve kurar.
    Testler: backend/pytest.ini pythonpath'e ../libs/panoalgo ekler.
    """
    if not settings.central_detector_enabled:
        log.info("merkez dedektor bilinerek kapali (CENTRAL_DETECTOR=0)")
        return None
    try:
        from panoalgo.central import CentralDetector
    except ImportError as exc:
        log.error(
            "merkez dedektor YUKLENEMEDI, emniyet agi olmadan devam ediliyor "
            "(kenar tespiti calismaya devam eder): %s",
            exc,
        )
        return None
    log.info("merkez dedektor etkin: panoalgo.central.CentralDetector")
    return CentralDetector(contracts_dir=settings.contracts_dir)


def create_app(
    settings: Settings | None = None,
    *,
    store: Store | None = None,
    clock: Callable[[], datetime] = utcnow,
) -> FastAPI:
    settings = settings or Settings.from_env()
    if settings.ingest_enabled:
        _configure_logging()
    contracts = load_contracts(settings.contracts_dir)
    missing = [code for code in REQUIRED_HYPOTHESES if code not in contracts.hypothesis_codes]
    if missing:
        raise ValueError(f"alarm-codes.yaml hipotezlerinde eksik: {missing}")
    # SCADA: bozuk harita veya birim eslemesi servisi hic kaldirmaz (yanlis adresle yayin yapilmaz)
    scada_enabled = settings.modbus_enabled or settings.iec104_enabled
    regmap = load_map(settings.contracts_dir / "modbus-map.yaml") if scada_enabled else None
    units = parse_units(settings.modbus_units, contracts.pano_id_re) if scada_enabled else {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        owns_store = store is None
        if owns_store:
            from .db import PgStore

            active_store: Store = PgStore(settings.db_dsn)
        else:
            active_store = store
        hub = StreamHub()
        pipeline = IngestPipeline(contracts, active_store, clock=clock)
        alarm_service = AlarmService(
            contracts, active_store, hub, clock=clock, detector=_central_detector(settings)
        )
        try:
            alarm_service.load()
        except StoreError as exc:  # TB1 davranisi: DB kapaliyken de ayaga kalk, DB gelince yukle
            log.warning("alarm durumu acilista yuklenemedi, veritabani gelince yuklenecek: %s", exc)
        pipeline.add_listener(_panel_update_publisher(active_store, hub, contracts, clock))
        pipeline.add_listener(alarm_service.on_samples)
        scada = None
        if regmap is not None:  # dinleyiciler ingest baslamadan eklenir: ilk ornekler kacmaz
            scada = _scada_service(app, settings, contracts, regmap, units, active_store, alarm_service, pipeline, clock)
            await scada.start()
        subscriber = None
        alarm_worker = None
        notifier = None
        if settings.ingest_enabled:
            pipeline.start()
            notifier = _start_notifier(contracts, alarm_service, clock)
            alarm_worker = PeriodicWorker(alarm_service.tick, settings.alarm_tick_s, name="alarm-tick")
            alarm_worker.start()
            subscriber = MqttSubscriber(
                settings.mqtt_host, settings.mqtt_port, contracts, pipeline.handle_message
            )
            subscriber.start()
        app.state.store = active_store
        app.state.hub = hub
        app.state.pipeline = pipeline
        app.state.alarms = alarm_service
        app.state.subscriber = subscriber
        app.state.scada = scada
        try:
            yield
        finally:
            if scada is not None:
                await scada.stop()
            if subscriber is not None:
                subscriber.stop()
            if alarm_worker is not None:
                alarm_worker.stop()
            pipeline.stop()
            if notifier is not None:
                notifier.stop()
            if owns_store:
                active_store.close()

    app = FastAPI(
        title="Grid Up — Pano Beyni Merkez API",
        version=__version__,
        description="On-prem izleme platformu. Sozlesme: contracts/openapi.yaml",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.contracts = contracts
    app.state.clock = clock

    # Gelistirmede frontend ayri portta (3000); uretimde nginx arkasinda ayni koken.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(StoreError, _store_unavailable)
    app.include_router(panels.router)
    app.include_router(insights.router)
    app.include_router(alarms.router)
    app.include_router(stream.router)

    @app.get("/health", tags=["system"])
    def health(request: Request) -> dict:
        state = request.app.state
        subscriber = state.subscriber
        return {
            "ok": True,
            "version": __version__,
            "mqtt": bool(subscriber and subscriber.connected),
            "db": state.store.ping(),
            "contracts": True,
            "contracts_loaded": {
                "alarm_codes": len(contracts.alarm_codes["alarms"]),
                "hypotheses": len(contracts.hypothesis_codes),
                "ingest_topics": list(contracts.ingest_topics),
            },
            "ingest": dict(state.pipeline.stats),
            "scada": state.scada.status() if state.scada is not None else None,
        }

    return app


def _start_notifier(contracts: Contracts, alarm_service: AlarmService, clock: Callable[[], datetime]) -> Notifier:
    """Kanallar ortam degiskenlerinden (deploy/.env): SMS_DEVICE, ALERT_*, WHATSAPP_*."""
    config = NotifyConfig.from_env()
    sms, whatsapp = channels_from_env()
    notifier = Notifier(
        contracts,
        config,
        sms=sms,
        whatsapp=whatsapp,
        on_delivery=alarm_service.record_delivery,
        on_reply=lambda alarm_id, by, note: alarm_service.ack(alarm_id, by=by, note=note),
        clock=clock,
    )
    alarm_service.add_listener(notifier)
    # Gunluk P3/SYS ozeti (DIGEST_AT) ACIKCA kaydedilir. add_listener bunu notifier'in
    # `digest` metodunu gorerek de yapar; kurulumun o ORTUK tespite bagli kalmamasi icin
    # burada ayrica yaziliyor. Tekrar kaydi add_digest_listener eler.
    alarm_service.add_digest_listener(notifier.digest)
    notifier.start()
    digest_at = digest_at_from_env()
    log.info(
        "bildirim kanallari: sms=%s whatsapp=%s, %d saha + %d eskalasyon alicisi; gunluk ozet %s",
        "acik" if sms else "kapali",
        "acik" if whatsapp else "kapali",
        len(config.recipients),
        len(config.escalation),
        f"{digest_at:%H:%M} (sunucu saati)" if digest_at is not None else "kapali",
    )
    return notifier


def _scada_service(
    app: FastAPI,
    settings: Settings,
    contracts: Contracts,
    regmap: RegisterMap,
    units: dict[int, str],
    store: Store,
    alarm_service: AlarmService,
    pipeline: IngestPipeline,
    clock: Callable[[], datetime],
) -> ScadaService:
    """SCADA ag gecidi (TB3): Modbus TCP ve IEC 104 ayni birim eslemesini paylasir; ayarlar MODBUS_* / IEC104_*."""
    gateway = ScadaGateway(
        regmap,
        contracts,
        alarms=alarm_service,
        store=store,
        clock=clock,
        units=units or None,
        password=settings.modbus_password,
        command_sink=_edge_command_sink(app, clock),
    )
    pipeline.add_listener(gateway.on_samples)
    alarm_service.add_listener(gateway.on_alarm_changes)
    modbus = None
    if settings.modbus_enabled:
        modbus = ModbusTcpServer(
            gateway,
            host=settings.modbus_host,
            port=settings.modbus_port,
            allowed_networks=settings.modbus_allowed_clients,
        )
    iec104 = None
    if settings.iec104_enabled:
        stations = GatewayStations(gateway, PointCatalog(regmap, PanelEncoder(regmap, contracts)), clock)
        iec104 = Iec104Server(
            stations,
            host=settings.iec104_host,
            port=settings.iec104_port,
            allowed_networks=settings.iec104_allowed_clients,
        )
    return ScadaService(gateway, modbus, iec104=iec104, refresh_s=settings.modbus_refresh_s)


def _edge_command_sink(app: FastAPI, clock: Callable[[], datetime]) -> CommandSink:
    """SCADA'nin bakim modu / test alarmi komutu MQTT cmd topic'iyle kenara; abone yoksa iletilemedi (False)."""

    def send(pano_id: str, cmd: str, args: dict) -> bool:
        subscriber = getattr(app.state, "subscriber", None)
        return subscriber is not None and subscriber.publish_command(pano_id, cmd, args, ts=clock())

    return send


def _configure_logging() -> None:
    """Uygulama kayitlari (gridup.*) konteyner loguna duser; uvicorn kendi logger'larini ayri kurar."""
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=os.getenv("LOG_LEVEL", "INFO").upper(),
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )


def _panel_update_publisher(
    store: Store, hub: StreamHub, contracts: Contracts, clock: Callable[[], datetime]
) -> Callable[[list[Sample]], None]:
    """Yazilan her partiden sonra degisen panolarin ozetini WebSocket'e yayinlar."""

    def publish(samples: list[Sample]) -> None:
        if not hub.has_clients:
            return
        pano_ids = list(dict.fromkeys(sample.pano_id for sample in samples))
        now = clock()
        for record in store.list_panels(pano_ids):
            hub.publish({"type": "tel", "payload": panel_summary(record, contracts, now)})

    return publish


async def _store_unavailable(request: Request, exc: StoreError) -> JSONResponse:
    log.warning("veritabani erisilemiyor: %s", exc)
    return JSONResponse(status_code=503, content={"detail": "Veritabani su an erisilemiyor"})
