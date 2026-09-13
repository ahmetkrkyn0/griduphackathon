"""Alarm servisi (TB2, Kisi B): risk motoru + ISA-18.2 alarm yoneticisi + depo + canli akis.

Akis:
    ingest yazici thread'i --on_samples--> RiskEngine.evaluate --> AlarmManager.observe
    alarm zamanlayicisi (5 s) --tick-----> raf suresi dolanlar + haberlesme denetimi (ALM-COMMS-LOST)
    API (ack / shelve) ------------------> AlarmManager.ack / shelve
    her degisiklik --> depo (tek transaction) --> WebSocket {"type": "alarm"} --> dinleyiciler (bildirim)

Dayaniklilik:
  - Acik alarmlar DB ilk erisilebilir oldugunda bir kez yuklenir. DB kapaliyken backend yine
    ayaga kalkar (API 503 doner, ingest tekrar dener); yukleme olmadan alarm uretilmez, cunku alarm
    kimligi depodaki en buyuk kimlikten devam etmelidir.
  - Yazilamayan degisiklikler sirasiyla bekletilir ve her tick'te tekrar denenir. WebSocket yayini ve
    bildirim yazmayi BEKLEMEZ: veritabani takilsa da telefon calar.
  - Yonetici islemi + yazma + yayin tek seri kilit altindadir: ingest thread'inin "raised" kaydi ile
    API thread'inin "acked" kaydi DB'ye ters sirada gidip durumu geri alamaz. Dinleyiciler bu kilit
    altinda cagrilir; yavas is (HTTP, modem) yapan dinleyici kendi kuyrugunu kullanmalidir.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from .alarm_manager import Alarm, AlarmManager, AlarmNotFound, AlarmStateConflict, Change
from .api.stream import StreamHub
from .api.views import alarm_view
from .config import Contracts
from .db import Store, StoreError
from .models import Sample
from .risk import CentralDetector, RiskEngine, signal

if TYPE_CHECKING:
    from .notify.dispatcher import Delivery

log = logging.getLogger("gridup.alarms")

COMMS_LOST = "ALM-COMMS-LOST"
MAX_UNSAVED_BATCHES = 10_000

ChangeListener = Callable[[list[Change]], None]


class AlarmService:
    def __init__(
        self,
        contracts: Contracts,
        store: Store,
        hub: StreamHub,
        *,
        clock: Callable[[], datetime],
        detector: CentralDetector | None = None,
    ) -> None:
        self._contracts = contracts
        self._store = store
        self._hub = hub
        self._clock = clock
        self._risk = RiskEngine(contracts, detector)
        self._comms_timeout = timedelta(minutes=contracts.thresholds["heartbeat_timeout_min"])
        self._manager: AlarmManager | None = None
        self._load_lock = threading.Lock()
        self._serial = threading.RLock()  # yonetici islemi -> yazma -> yayin sirasi
        self._lock = threading.Lock()  # _last_rx ve _unsaved
        self._last_rx: dict[str, datetime] = {}
        self._unsaved: list[tuple[list[Change], datetime]] = []
        self._listeners: list[ChangeListener] = []
        self.stats = {"save_errors": 0, "unsaved_dropped": 0}

    # -------------------------------------------------------------- yasam
    def load(self) -> AlarmManager:
        """Acik alarmlari ve panolarin son gorulme zamanini depodan bir kez yukler (StoreError atabilir)."""
        with self._load_lock:
            if self._manager is None:
                manager = AlarmManager(self._contracts, first_id=self._store.next_alarm_id())
                manager.restore(self._store.load_open_alarms())
                seen = {r.pano_id: r.last_rx for r in self._store.list_panels() if r.last_rx is not None}
                with self._lock:
                    for pano_id, last_rx in seen.items():
                        self._last_rx.setdefault(pano_id, last_rx)
                self._manager = manager
                log.info("alarm durumu yuklendi: %d acik alarm", len(manager.open_alarms()))
            return self._manager

    def add_listener(self, listener: ChangeListener) -> None:
        self._listeners.append(listener)

    # ------------------------------------------------------------ girdiler
    def on_samples(self, samples: list[Sample]) -> None:
        """Ingest dinleyicisi: yazilan her partiden sonra (yazici thread'inde) cagrilir."""
        with self._lock:
            for sample in samples:
                previous = self._last_rx.get(sample.pano_id)
                if previous is None or sample.received_at > previous:
                    self._last_rx[sample.pano_id] = sample.received_at
        manager = self.load()
        with self._serial:
            now = self._clock()
            changes: list[Change] = []
            for sample in sorted(samples, key=lambda s: s.ts):
                conditions = self._risk.evaluate(sample)
                maint_mode = bool(sample.payload["health"].get("maint_mode", False))
                changes += manager.observe(sample.pano_id, sample.ts, conditions, now=now, maint_mode=maint_mode)
            self._apply(changes, now)

    def tick(self) -> None:
        """Alarm zamanlayicisi: bekleyen yazimlar, raf suresi, haberlesme denetimi."""
        try:
            manager = self.load()
        except StoreError as exc:
            log.warning("alarm durumu henuz yuklenemedi: %s", exc)
            return
        with self._serial:
            now = self._clock()
            self._retry_unsaved()
            changes = manager.tick(now)
            with self._lock:
                silent = [(p, now - rx) for p, rx in self._last_rx.items() if now - rx > self._comms_timeout]
            timeout_min = self._comms_timeout.total_seconds() / 60.0
            for pano_id, duration in silent:
                minutes = round(duration.total_seconds() / 60.0, 1)
                condition = self._risk.center_condition(
                    COMMS_LOST, [signal("last_rx_age_min", minutes, timeout_min, "min")]
                )
                changes += manager.assert_condition(pano_id, condition, ts=now, now=now)
            self._apply(changes, now)

    def ack(self, alarm_id: int, *, by: str, note: str | None = None) -> Alarm:
        manager = self.load()
        with self._serial:
            now = self._clock()
            try:
                change = manager.ack(alarm_id, by=by, now=now, note=note)
            except AlarmNotFound:
                self._raise_conflict_if_closed(alarm_id)
                raise
            self._apply([change], now)
            return change.alarm

    def shelve(self, alarm_id: int, *, by: str, minutes: int, reason: str) -> Alarm:
        manager = self.load()
        with self._serial:
            now = self._clock()
            try:
                change = manager.shelve(alarm_id, by=by, minutes=minutes, reason=reason, now=now)
            except AlarmNotFound:
                self._raise_conflict_if_closed(alarm_id)
                raise
            self._apply([change], now)
            return change.alarm

    def record_delivery(self, delivery: Delivery) -> None:
        """Bildirim ag gecidinin her denemesi: denetim izine yazilir; basariliysa kanal alarmda gorunur."""
        try:
            self._store.record_notification(delivery)
        except StoreError as exc:
            log.warning("bildirim kaydi yazilamadi (alarm %s, %s): %s", delivery.alarm_id, delivery.channel, exc)
        if not delivery.ok:
            return
        manager = self.load()
        with self._serial:
            change = manager.mark_notified(delivery.alarm_id, delivery.channel)
            if change is not None:
                self._apply([change], self._clock())

    # ------------------------------------------------------------ sorgular
    def list_alarms(self, states: Sequence[str], prios: Sequence[str] | None, pano_id: str | None, limit: int) -> list[Alarm]:
        return self._store.list_alarms(states, prios, pano_id, limit)

    def active_for_panel(self, pano_id: str) -> list[Alarm]:
        """Pano detayindaki active_alarms: konsolun varsayilan filtresiyle ayni (active, acked)."""
        return [a for a in self.load().open_alarms(pano_id) if a.state in ("active", "acked")]

    # ------------------------------------------------------------- ic isler
    def _raise_conflict_if_closed(self, alarm_id: int) -> None:
        stored = self._store.get_alarm(alarm_id)
        if stored is not None:
            raise AlarmStateConflict(f"alarm {alarm_id} zaten {stored.state}")

    def _apply(self, changes: list[Change], now: datetime) -> None:
        if not changes:
            return
        self._retry_unsaved()
        with self._lock:
            pending = bool(self._unsaved)
            if pending:  # sira korunur: eski degisiklikler yazilmadan yenisi yazilmaz
                self._queue_unsaved(changes, now)
        if not pending:
            try:
                self._store.save_alarm_changes(changes, now)
            except StoreError as exc:
                log.warning("%d alarm degisikligi yazilamadi, tekrar denenecek: %s", len(changes), exc)
                with self._lock:
                    self.stats["save_errors"] += 1
                    self._queue_unsaved(changes, now)
            except Exception:
                log.exception("alarm degisikligi veri hatasi nedeniyle yazilamadi")
        for change in changes:
            self._hub.publish({"type": "alarm", "payload": alarm_view(change.alarm, self._contracts)})
        for listener in self._listeners:
            try:
                listener(changes)
            except Exception:  # bildirim hatasi alarm akisini durdurmaz
                log.exception("alarm dinleyicisi hata verdi")

    def _queue_unsaved(self, changes: list[Change], now: datetime) -> None:
        self._unsaved.append((changes, now))
        if len(self._unsaved) > MAX_UNSAVED_BATCHES:
            self._unsaved.pop(0)
            self.stats["unsaved_dropped"] += 1

    def _retry_unsaved(self) -> None:
        while True:
            with self._lock:
                if not self._unsaved:
                    return
                changes, at = self._unsaved[0]
            try:
                self._store.save_alarm_changes(changes, at)
            except StoreError:
                return
            except Exception:
                log.exception("bekleyen alarm degisikligi veri hatasi nedeniyle atildi")
            with self._lock:
                self._unsaved.pop(0)


class PeriodicWorker:
    """Belirli aralikla bir islevi arka plan thread'inde calistirir; hata dongusu durdurmaz."""

    def __init__(self, fn: Callable[[], None], interval_s: float, name: str) -> None:
        self._fn = fn
        self._interval_s = interval_s
        self._name = name
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name=self._name, daemon=True)
        self._thread.start()

    def stop(self, timeout_s: float = 5.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout_s)
            self._thread = None

    def _run(self) -> None:
        while not self._stop.wait(self._interval_s):
            try:
                self._fn()
            except Exception:
                log.exception("%s calisirken hata", self._name)
