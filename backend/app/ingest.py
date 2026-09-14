"""MQTT ingestion (TB1, Kisi B).

Akis:
    MQTT (paho ag thread'i) -> handle_message: boyut / JSON / sema / topic / ts denetimi
    -> bellek kuyrugu -> yazici thread: toplu write_batch (telemetri + son durum + karantina)
    -> dinleyiciler (WebSocket yayini)

Ag thread'i veritabanini hic beklemez; DB yavaslarsa kuyruk dolar, MQTT keepalive'i bozulmaz.
Sema disi mesaj DUSURULMEZ, nedeniyle karantinaya yazilir (veri kalitesi kaniti, rapor 15.2).

Uzun format etiket kurali — Grafana panolari, /series ucu ve yuk testi bu adlara guvenir:
    t_conn.<pt>.<alan>   nokta alanlari (t_c, dt_c, k, k_ratio, tau_s, ttl_h, excited);
                         noktanin q bayragi ayri etiket degil, satirlarin q sutunudur
    <bolum>.<alan>       elec / env / tvoc / pd / risk / health altindaki yapraklar
    <bolum>.<alan>.<i>   dizi elemanlari (elec.i_ph.0 = L1 faz akimi)
    boolean -> 1.0 / 0.0; null, metin (risk.mode) ve ic ice nesneler (risk.contributions) yazilmaz.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from typing import Any

import paho.mqtt.client as mqtt
from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

from .config import PANO_ID_PLACEHOLDER, Contracts, topic_filter, topic_regex
from .db import Store, StoreError
from .models import Rejection, Sample, TelemetryRow

log = logging.getLogger("gridup.ingest")

SECTIONS = ("elec", "env", "tvoc", "pd", "risk", "health")
POINT_KEY_FIELDS = ("pt", "q")

Listener = Callable[[list[Sample]], None]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def flatten(payload: dict[str, Any]) -> tuple[TelemetryRow, ...]:
    rows: list[TelemetryRow] = []
    for point in payload["t_conn"]:
        q = int(point.get("q", 0))
        for field, value in point.items():
            number = None if field in POINT_KEY_FIELDS else _as_number(value)
            if number is not None:
                rows.append(TelemetryRow(f"t_conn.{point['pt']}.{field}", number, q))
    for section in SECTIONS:
        block = payload.get(section)
        if not isinstance(block, dict):
            continue
        for field, value in block.items():
            items = enumerate(value) if isinstance(value, list) else [(None, value)]
            for index, item in items:
                number = _as_number(item)
                if number is not None:
                    tag = f"{section}.{field}" if index is None else f"{section}.{field}.{index}"
                    rows.append(TelemetryRow(tag, number))
    return tuple(rows)


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return None


class _NonFiniteNumber(ValueError):
    pass


def _reject_constant(name: str) -> float:
    raise _NonFiniteNumber(name)


def _text(raw: bytes) -> str:
    """Karantinaya yazilabilir metin: PostgreSQL text/JSONB NUL karakteri kabul etmez."""
    return raw.decode("utf-8", errors="replace").replace("\x00", "\\u0000")


def _contains_nul(value: Any) -> bool:
    if isinstance(value, str):
        return "\x00" in value
    if isinstance(value, dict):
        return any(_contains_nul(k) or _contains_nul(v) for k, v in value.items())
    if isinstance(value, list):
        return any(_contains_nul(item) for item in value)
    return False


class RateMeter:
    """Son `window_s` saniyedeki olay hizi (1 s kovalari); /fleet/kpi ingest_msgs_per_s. Ag thread'inden cagrilir.

    Pencere ortalamasidir: acilistan sonraki ilk `window_s` saniyede gercek hizin altinda gosterir. Yuk testi
    olcumleri bunun yerine veritabanindaki satir sayisindan ve Grafana panosundan alinir (docs/09).
    """

    def __init__(self, window_s: int = 60, clock: Callable[[], float] = time.monotonic) -> None:
        self._window_s = window_s
        self._clock = clock
        self._buckets: deque[list[int]] = deque()  # [saniye, adet], eskiden yeniye
        self._lock = threading.Lock()

    def add(self, amount: int = 1) -> None:
        second = int(self._clock())
        with self._lock:
            if self._buckets and self._buckets[-1][0] == second:
                self._buckets[-1][1] += amount
            else:
                self._buckets.append([second, amount])
            self._trim(second)

    def per_second(self) -> float:
        now = int(self._clock())
        with self._lock:
            self._trim(now)
            return sum(count for _, count in self._buckets) / self._window_s

    def _trim(self, now: int) -> None:
        while self._buckets and self._buckets[0][0] <= now - self._window_s:
            self._buckets.popleft()


class IngestPipeline:
    def __init__(
        self,
        contracts: Contracts,
        store: Store,
        *,
        clock: Callable[[], datetime] = utcnow,
        max_queue: int = 50_000,
        max_batch: int = 500,
        flush_interval_s: float = 0.5,
        max_message_bytes: int = 64_000,
    ) -> None:
        self._store = store
        self._clock = clock
        self._validator = Draft202012Validator(contracts.telemetry_schema)
        self._topics = [topic_regex(t) for t in contracts.ingest_topics]
        self._max_queue = max_queue
        self._max_batch = max_batch
        self._flush_interval_s = flush_interval_s
        self._max_message_bytes = max_message_bytes

        self._queue: deque[Sample | Rejection] = deque()
        self._pending: list[Sample | Rejection] = []  # yazilamayan parti; once bu denenir
        self._lock = threading.Lock()
        self._flush_lock = threading.Lock()
        self._listeners: list[Listener] = []
        self.stats = {"received": 0, "rejected": 0, "written": 0, "dropped": 0, "write_errors": 0}
        self._rate = RateMeter()

        self._wake = threading.Event()
        self._stopping = threading.Event()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------ giris
    def handle_message(self, topic: str, raw: bytes) -> None:
        """paho ag thread'inden cagrilir: yalnizca ayristirir ve kuyruga koyar, DB'yi beklemez."""
        item = self._parse(topic, raw, self._clock())
        self._rate.add()
        with self._lock:
            self.stats["received"] += 1
            if isinstance(item, Rejection):
                self.stats["rejected"] += 1
            if len(self._queue) >= self._max_queue:
                self.stats["dropped"] += 1
                return
            self._queue.append(item)
            if len(self._queue) >= self._max_batch:
                self._wake.set()

    def add_listener(self, listener: Listener) -> None:
        self._listeners.append(listener)

    def msgs_per_s(self) -> float:
        """Son 60 s'de alinan mesaj hizi (reddedilenler dahil: broker'dan gelen yuk)."""
        return self._rate.per_second()

    # ----------------------------------------------------------------- yazma
    def flush(self) -> bool:
        """Kuyrugu partiler halinde yazar.

        True  = kuyruk bosaldi.
        False = gecici depolama hatasi; yazilamayan parti kuyrukta kalir, sonraki flush tekrar dener.
        Veri hatasi (StoreError disi) tekrar denemekle gecmez: parti tek tek yazilarak bozuk
        mesaj ayiklanir ve dusurulur, saglam mesajlar yazilir (tek cihaz tum filoyu durduramaz).
        """
        with self._flush_lock:
            while True:
                with self._lock:
                    if not self._pending:
                        count = min(self._max_batch, len(self._queue))
                        self._pending = [self._queue.popleft() for _ in range(count)]
                    batch = list(self._pending)
                if not batch:
                    return True
                try:
                    self._write(batch)
                except StoreError as exc:
                    self._count("write_errors")
                    log.warning("yazma basarisiz, %d oge tekrar denenecek: %s", len(batch), exc)
                    return False
                except Exception:
                    self._count("write_errors")
                    log.exception("partide veri hatasi, %d oge tek tek yaziliyor", len(batch))
                    if not self._write_one_by_one(batch):
                        return False
                with self._lock:
                    self._pending = []

    def _write(self, items: list[Sample | Rejection]) -> None:
        samples = [item for item in items if isinstance(item, Sample)]
        rejections = [item for item in items if isinstance(item, Rejection)]
        self._store.write_batch(samples, rejections)
        self._count("written", len(samples))
        self._notify(samples)

    def _write_one_by_one(self, batch: list[Sample | Rejection]) -> bool:
        for index, item in enumerate(batch):
            try:
                self._write([item])
            except StoreError:
                with self._lock:
                    self._pending = batch[index:]
                return False
            except Exception:
                self._count("dropped")
                log.exception("yazilamayan mesaj dusuruldu: %s", getattr(item, "topic", "?"))
        return True

    def _count(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self.stats[name] += amount

    def _notify(self, samples: list[Sample]) -> None:
        if not samples:
            return
        for listener in self._listeners:
            try:
                listener(samples)
            except Exception:  # bir dinleyicinin hatasi ingest'i durdurmaz
                log.exception("ingest dinleyicisi hata verdi")

    # ------------------------------------------------------- arka plan yazicisi
    def start(self) -> None:
        if self._thread is not None:
            return
        self._stopping.clear()
        self._thread = threading.Thread(target=self._run, name="ingest-writer", daemon=True)
        self._thread.start()

    def stop(self, timeout_s: float = 5.0) -> None:
        self._stopping.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout_s)
            self._thread = None
        self.flush()

    def _run(self) -> None:
        delay = self._flush_interval_s
        while not self._stopping.is_set():
            self._wake.wait(delay)
            self._wake.clear()
            ok = self.flush()
            delay = self._flush_interval_s if ok else min(delay * 2, 5.0)

    # ------------------------------------------------------------ ayristirma
    def _parse(self, topic: str, raw: bytes, received_at: datetime) -> Sample | Rejection:
        def reject(reason: str, stored: Any) -> Rejection:
            return Rejection(received_at=received_at, topic=topic, reason=reason, raw=stored)

        if len(raw) > self._max_message_bytes:
            return reject(
                f"mesaj cok buyuk: {len(raw)} bayt (sinir {self._max_message_bytes})",
                {"raw_text": _text(raw[: self._max_message_bytes]), "truncated": True},
            )
        try:
            payload = json.loads(raw, parse_constant=_reject_constant)
        except _NonFiniteNumber as exc:
            return reject(f"gecersiz sayi {exc.args[0]}: JSON'da NaN/Infinity yoktur", {"raw_text": _text(raw)})
        except ValueError as exc:
            return reject(f"JSON ayristirilamadi: {exc}", {"raw_text": _text(raw)})
        if _contains_nul(payload):
            return reject("metinde NUL karakteri var (veritabanina yazilamaz)", {"raw_text": _text(raw)})

        error = best_match(self._validator.iter_errors(payload))
        if error is not None:
            return reject(f"sema ihlali {error.json_path}: {error.message}", payload)

        match = next((m for m in (p.match(topic) for p in self._topics) if m), None)
        if match is None:
            return reject("telemetri topic'i degil", payload)
        if match["pano_id"] != payload["pano_id"]:
            return reject(
                f"topic pano_id ({match['pano_id']}) ile yukteki pano_id ({payload['pano_id']}) uyusmuyor",
                payload,
            )

        try:
            ts = datetime.fromisoformat(payload["ts"])
        except ValueError:
            return reject(f"ts ayristirilamadi: {payload['ts']!r}", payload)
        if ts.tzinfo is None:
            return reject(f"ts saat dilimi icermiyor (UTC ofseti zorunlu): {payload['ts']!r}", payload)

        return Sample(
            pano_id=payload["pano_id"],
            ts=ts.astimezone(timezone.utc),
            seq=payload["seq"],
            received_at=received_at,
            topic=topic,
            payload=payload,
            rows=flatten(payload),
        )


class MqttSubscriber:
    """Broker'a baglanir, sozlesmedeki telemetri topic'lerine abone olur, mesajlari iletir.

    clean_session=False + sabit client_id: backend yeniden baslarken broker QoS 1 mesajlari
    bekletir (mosquitto.conf max_queued_messages), yeniden baslatma veri kaybettirmez.

    Ayni baglanti merkez -> kenar komutlarini da yayinlar (x-topics cmd; SCADA ag gecidi kullanir).
    """

    def __init__(
        self,
        host: str,
        port: int,
        contracts: Contracts,
        on_message: Callable[[str, bytes], None],
        *,
        client_id: str = "gridup-backend-ingest",
        client: Any = None,
    ) -> None:
        self._host = host
        self._port = port
        self._subscriptions = [(topic_filter(t), qos) for t, qos in contracts.ingest_topics.items()]
        self._command_topic = contracts.command_topic
        self._command_qos = contracts.command_qos
        self._forward = on_message
        self.connected = False
        self._client = client or mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, clean_session=False
        )
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def start(self) -> None:
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)
        self._client.connect_async(self._host, self._port, keepalive=30)
        self._client.loop_start()

    def stop(self) -> None:
        self._client.disconnect()
        self._client.loop_stop()

    def publish_command(self, pano_id: str, cmd: str, args: dict[str, Any], *, ts: datetime) -> bool:
        """Kenara komut; True = broker'a teslim edilmek uzere paho'ya verildi.

        Kopukken KUYRUGA ALINMAZ: saatler sonra teslim edilen eski bir komut (or. bakim modu) sahada
        surpriz yaratir. Cagiran (SCADA ag gecidi) basarisizligi istemciye bildirir, operator tekrar dener.
        """
        if not self.connected:
            log.warning("MQTT kopuk, kenar komutu gonderilmedi: %s -> %s", cmd, pano_id)
            return False
        topic = self._command_topic.replace(PANO_ID_PLACEHOLDER, pano_id)
        body = json.dumps({"v": 1, "ts": ts.isoformat(), "cmd": cmd, "args": args}, ensure_ascii=False)
        info = self._client.publish(topic, body, qos=self._command_qos, retain=False)
        return info.rc == mqtt.MQTT_ERR_SUCCESS

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code.is_failure:
            self.connected = False
            log.warning("MQTT baglantisi reddedildi: %s", reason_code)
            return
        client.subscribe(self._subscriptions)
        self.connected = True
        log.info("MQTT %s:%s baglandi, abonelik: %s", self._host, self._port, self._subscriptions)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties) -> None:
        self.connected = False
        log.warning("MQTT baglantisi koptu: %s", reason_code)

    def _on_message(self, client, userdata, message) -> None:
        self._forward(message.topic, message.payload)
