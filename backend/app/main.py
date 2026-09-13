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
from .api import alarms, panels, stream
from .api.stream import StreamHub
from .api.views import REQUIRED_HYPOTHESES, panel_summary
from .config import Contracts, Settings, load_contracts
from .db import Store, StoreError
from .ingest import IngestPipeline, MqttSubscriber, utcnow
from .models import Sample
from .notify.dispatcher import Notifier, NotifyConfig, channels_from_env
from .scada.gateway import CommandSink, ScadaGateway, parse_units
from .scada.map_loader import RegisterMap, load_map
from .scada.modbus_tcp import ModbusTcpServer
from .scada.service import ScadaService

log = logging.getLogger("gridup")


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
    regmap = load_map(settings.contracts_dir / "modbus-map.yaml") if settings.modbus_enabled else None
    units = parse_units(settings.modbus_units, contracts.pano_id_re) if settings.modbus_enabled else {}

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
        alarm_service = AlarmService(contracts, active_store, hub, clock=clock)
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
    notifier.start()
    log.info(
        "bildirim kanallari: sms=%s whatsapp=%s, %d saha + %d eskalasyon alicisi",
        "acik" if sms else "kapali",
        "acik" if whatsapp else "kapali",
        len(config.recipients),
        len(config.escalation),
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
    """Modbus TCP ag gecidi (TB3): ayarlar deploy/.env'den (MODBUS_*); bos birim eslemesi = otomatik."""
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
    server = ModbusTcpServer(
        gateway,
        host=settings.modbus_host,
        port=settings.modbus_port,
        allowed_networks=settings.modbus_allowed_clients,
    )
    return ScadaService(gateway, server, refresh_s=settings.modbus_refresh_s)


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
