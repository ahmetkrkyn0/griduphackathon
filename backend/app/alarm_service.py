"""Alarm servisi (TB2, Kisi B): risk motoru + ISA-18.2 alarm yoneticisi + depo + canli akis.

Akis:
    ingest yazici thread'i --on_samples--> RiskEngine.evaluate --> AlarmManager.observe
    alarm zamanlayicisi (5 s) --tick-----> raf suresi dolanlar + haberlesme denetimi (ALM-COMMS-LOST)
                                          + gunde bir kez (DIGEST_AT) P3/SYS gunluk ozeti
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
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING

from .alarm_manager import Alarm, AlarmManager, AlarmNotFound, AlarmStateConflict, Change
from .api.alarms import ALARM_STATES
from .api.stream import StreamHub
from .api.views import alarm_view
from .config import PRIO_ORDER, Contracts, digest_at_from_env
from .db import Store, StoreError
from .models import Sample
from .outage import SilentPanel, correlate
from .risk import CentralDetector, RiskEngine, signal

if TYPE_CHECKING:
    from .notify.dispatcher import Delivery

log = logging.getLogger("gridup.alarms")

COMMS_LOST = "ALM-COMMS-LOST"
MAX_UNSAVED_BATCHES = 10_000

# Gunluk ozet (contracts/alarm-codes.yaml: P3 daily_digest, SYS sms: digest_only).
DIGEST_WINDOW = timedelta(hours=24)  # ozet penceresi: [ozet saati - 24 sa, ozet saati)
DIGEST_LIMIT = 1000  # tek ozette taranan en fazla alarm (alarm konsolunun ust siniriyla ayni)
DIGEST_CHANNEL = "sms"  # ozet SMS ile gider; alarmin kanal rozeti (contracts/openapi.yaml Alarm.notified)

ChangeListener = Callable[[list[Change]], None]


@dataclass(frozen=True)
class Digest:
    """Gunde bir kez gonderilen ozetin icerigi; metne cevirmek bildirim katmaninin isidir.

    `counts` etiketleri oncelik tablosundan gelir ("uyari (P3)", "sistem (SYS)") — sayilar ve
    etiketler koda gomulmez (PLAN.md kural 10).
    """

    day: date
    hours: int  # ozet penceresinin uzunlugu (DIGEST_WINDOW)
    counts: tuple[tuple[str, int], ...]
    panels: int
    top_pano: str
    top_count: int
    top_text: str

    @property
    def total(self) -> int:
        return sum(count for _, count in self.counts)


DigestListener = Callable[[Digest], bool]


class AlarmService:
    def __init__(
        self,
        contracts: Contracts,
        store: Store,
        hub: StreamHub,
        *,
        clock: Callable[[], datetime],
        detector: CentralDetector | None = None,
        digest_at: time | None = None,
    ) -> None:
        self._contracts = contracts
        self._store = store
        self._hub = hub
        self._clock = clock
        self._risk = RiskEngine(contracts, detector)
        self._comms_timeout = timedelta(minutes=contracts.thresholds["heartbeat_timeout_min"])
        # F-22 ust sebeke kesintisi bagintisi. Esikler contracts/alarm-codes.yaml'dan gelir
        # (PLAN.md kural 10); AlarmService Settings ALMIYOR ama Contracts aliyor, bu yuzden
        # esigi sozlesmeye koymak yeni bir yapilandirma yolu acmadan calisir.
        self._outage_min_panels = int(contracts.thresholds["outage_min_panels"])
        self._outage_window = timedelta(minutes=contracts.thresholds["outage_window_min"])
        # pano_id -> (fider_id, ad, abone sayisi). F-21 kunyesinden, acilista bir kez okunur.
        self._asset: dict[str, tuple[str | None, str | None, int | None]] = {}
        self._open_outages: dict[str, set[str]] = {}  # outage_id -> panolari
        # Ozet saati: uygulama fabrikasi alarm servisini Settings olmadan kurar, bu yuzden
        # verilmediyse ayni yardimciyla ortamdan okunur (DIGEST_AT).
        self._digest_at = digest_at or digest_at_from_env()
        self._digest_prios = _digest_prios(contracts)
        self._digest_day: date | None = None  # bugunun ozeti icin depo tarandi mi
        self._digest_listeners: list[DigestListener] = []
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
                records = self._store.list_panels()
                seen = {r.pano_id: r.last_rx for r in records if r.last_rx is not None}
                # F-22: pano -> fider eslemesi ayni okumadan gelir; ayri sorgu acilmaz.
                asset = {r.pano_id: (r.fider_id, r.name, r.abone_sayisi) for r in records}
                with self._lock:
                    for pano_id, last_rx in seen.items():
                        self._last_rx.setdefault(pano_id, last_rx)
                    self._asset = asset
                self._manager = manager
                log.info("alarm durumu yuklendi: %d acik alarm", len(manager.open_alarms()))
            return self._manager

    def add_listener(self, listener: ChangeListener) -> None:
        """Degisiklik dinleyicisi. `digest` metodu olan dinleyici (bildirim ag gecidi) gunluk ozeti de alir."""
        self._listeners.append(listener)
        digest = getattr(listener, "digest", None)
        if callable(digest):
            self.add_digest_listener(digest)

    def add_digest_listener(self, listener: DigestListener) -> None:
        """Gunluk ozet (DIGEST_AT) dinleyicisi; AYNI dinleyici iki kez kaydedilmez.

        `add_listener` bunu `digest` metodunu goren dinleyiciler icin kendisi cagirir.
        Kurulumun bu ortuk tespite bagli kalmamasi icin dogrudan da cagrilabilir
        (bkz. app/main.py `_start_notifier`); tekrar kaydi burasi eler, boylece iki
        yol birlikte kullanildiginda ozet IKI KEZ gonderilmez.
        """
        if listener in self._digest_listeners:
            return
        self._digest_listeners.append(listener)

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
            # F-22: es zamanli susan panolari TEK kesinti olayina topla. Bu adim ALARM
            # URETMEZ ve HICBIR ALARMI BASTIRMAZ — asagidaki dongu aynen calisir. Tek
            # panolu durumda (esik 3) hicbir grup olusmaz ve eski davranis birebir korunur.
            self._correlate_outages(silent, now)
            timeout_min = self._comms_timeout.total_seconds() / 60.0
            for pano_id, duration in silent:
                minutes = round(duration.total_seconds() / 60.0, 1)
                condition = self._risk.center_condition(
                    COMMS_LOST, [signal("last_rx_age_min", minutes, timeout_min, "min")]
                )
                changes += manager.assert_condition(pano_id, condition, ts=now, now=now)
            self._apply(changes, now)
        self._maybe_digest(now)

    def _correlate_outages(self, silent: list[tuple[str, timedelta]], now: datetime) -> None:
        """Es zamanli susan panolari kesinti olaylarina toplar (F-22).

        BU METOT ALARM URETMEZ VE BASTIRMAZ. Alt alarmlar cagiran dongude aynen uretilir;
        baginti yalnizca "bunlar tek bir ust sebeke olayidir" bilgisini ekler.

        Depo hatasi bagintiyi dusurur ama ALARM URETIMINI DURDURMAZ: kesinti gruplamasi bir
        kolayliktir, haberlesme kaybi alarmi ise emniyet islevidir ve ikincisi birincisine
        bagimli olmamali.
        """
        with self._lock:
            groups = correlate(
                [
                    SilentPanel(
                        pano_id=pano_id,
                        last_rx=self._last_rx[pano_id],
                        fider_id=asset[0],
                        name=asset[1],
                        abone_sayisi=asset[2],
                    )
                    for pano_id, _ in silent
                    if (asset := self._asset.get(pano_id, (None, None, None)))[0] is not None
                ],
                min_panels=self._outage_min_panels,
                window=self._outage_window,
            )
        still_silent = {pano_id for pano_id, _ in silent}
        try:
            if groups:
                self._store.save_outages(groups, detected_at=now)
                for group in groups:
                    self._open_outages[group.outage_id] = {p.pano_id for p in group.panels}
            # Panolarinin HEPSI konustuysa kesinti kapanir. DIKKAT: `ended_at` enerjinin geri
            # geldigi an DEGILDIR, haberlesmenin dondugu andir ve histerezislidir (F-23).
            closed = [
                outage_id
                for outage_id, panels in self._open_outages.items()
                if not (panels & still_silent)
            ]
            if closed:
                self._store.close_outages(closed, at=now)
                for outage_id in closed:
                    self._open_outages.pop(outage_id, None)
        except StoreError as exc:
            log.warning("kesinti bagintisi yazilamadi (alarm uretimi etkilenmedi): %s", exc)

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

    # ----------------------------------------------------------- gunluk ozet
    def _maybe_digest(self, now: datetime) -> None:
        """Gunde bir kez, DIGEST_AT saatinde: P3 uyarilari ve SYS alarmlari tek SMS'lik ozete girer.

        Pencere sabittir: [ozet saati - 24 sa, ozet saati). Ozetlenen alarmin `notified` alanina
        'sms' yazilir ve bu alarms tablosunda kalicidir; penceredeki bir alarm zaten isaretliyse
        bugunun ozeti gonderilmis demektir, yeniden baslatma ikinci mesaj uretmez. Ozet saatinden
        sonra olusan alarmlar bir sonraki gunun penceresine dusar.
        """
        if self._digest_at is None or not self._digest_listeners or self._digest_day == now.date():
            return
        due = datetime.combine(now.date(), self._digest_at, tzinfo=now.tzinfo)
        if now < due:
            return
        try:
            pending = self._digest_alarms(due)
        except StoreError as exc:  # depo erisilebilir oldugunda sonraki tick tekrar dener
            log.warning("gunluk ozet hazirlanamadi: %s", exc)
            return
        self._digest_day = now.date()
        if not pending:
            return
        summary = _digest_summary(self._contracts, due, pending, self._digest_prios)
        if not [listener for listener in self._digest_listeners if listener(summary)]:
            log.warning("gunluk ozet gonderilemedi, SMS kanali ya da alici yok (%d alarm)", summary.total)
            return
        self._mark_digested(pending, now)
        log.info("gunluk ozet gonderildi: %d alarm, %d pano", summary.total, summary.panels)

    def _digest_alarms(self, due: datetime) -> list[Alarm]:
        """Ozet penceresindeki, henuz ozetlenmemis P3/SYS alarmlari (StoreError atabilir).

        Penceredeki bir alarm zaten isaretliyse bugunun ozeti gitmistir: bos liste doner.
        """
        rows = self._store.list_alarms(ALARM_STATES, self._digest_prios, None, DIGEST_LIMIT)
        window = [alarm for alarm in rows if due - DIGEST_WINDOW <= alarm.raised_at < due]
        pending = [alarm for alarm in window if DIGEST_CHANNEL not in alarm.notified]
        return [] if len(pending) < len(window) else pending

    def _mark_digested(self, alarms: list[Alarm], now: datetime) -> None:
        """Ozetlenen alarmlara kanal rozetini yazar (Alarm.notified 'sms').

        Acik alarm yoneticiden, temizlenmis alarm depodan gelen kopyadan isaretlenir; ikisi de ayni
        yazma yolundan (save_alarm_changes) gecer, boylece isaret yeniden baslatmayi asar.
        """
        manager = self._manager
        changes: list[Change] = []
        for alarm in alarms:
            change = manager.mark_notified(alarm.id, DIGEST_CHANNEL) if manager is not None else None
            if change is None:
                marked = replace(alarm, notified=(*alarm.notified, DIGEST_CHANNEL))
                change = Change("notified", marked, step=DIGEST_CHANNEL, note=DIGEST_CHANNEL)
            changes.append(change)
        with self._serial:
            self._apply(changes, now)

    # ------------------------------------------------------------ sorgular
    def list_alarms(self, states: Sequence[str], prios: Sequence[str] | None, pano_id: str | None, limit: int) -> list[Alarm]:
        return self._store.list_alarms(states, prios, pano_id, limit)

    def active_for_panel(self, pano_id: str) -> list[Alarm]:
        """Pano detayindaki active_alarms: konsolun varsayilan filtresiyle ayni (active, acked)."""
        return [a for a in self.load().open_alarms(pano_id) if a.state in ("active", "acked")]

    def open_alarms(self, pano_id: str | None = None) -> list[Alarm] | None:
        """Bellekteki acik alarmlar (tum durumlar; pano_id None ise tum filo); durum henuz yuklenmediyse None.

        Veritabanina GITMEZ: Modbus ag gecidi bunu olay dongusunden, her okuma isteginde cagirir.
        """
        manager = self._manager
        return None if manager is None else manager.open_alarms(pano_id)

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


def _digest_prios(contracts: Contracts) -> tuple[str, ...]:
    """Ozete girecek oncelikler sozlesmeden okunur: daily_digest: true (P3), sms: digest_only (SYS)."""
    priorities = contracts.alarm_codes["priorities"]
    return tuple(
        prio
        for prio in PRIO_ORDER
        if prio in priorities
        and (priorities[prio].get("daily_digest") is True or priorities[prio].get("sms") == "digest_only")
    )


def _digest_summary(contracts: Contracts, due: datetime, alarms: list[Alarm], prios: tuple[str, ...]) -> Digest:
    """Oncelik basina sayi, pano sayisi ve en cok alarm ureten panonun en sik alarm metni."""
    priorities = contracts.alarm_codes["priorities"]
    by_prio = Counter(alarm.prio for alarm in alarms)
    by_pano = Counter(alarm.pano_id for alarm in alarms)
    top_pano, top_count = _most_common(by_pano)
    top_code, _ = _most_common(Counter(alarm.code for alarm in alarms if alarm.pano_id == top_pano))
    return Digest(
        day=due.date(),
        hours=int(DIGEST_WINDOW.total_seconds() // 3600),
        counts=tuple(
            (f"{priorities[prio].get('name', prio).lower()} ({prio})", by_prio[prio])
            for prio in prios
            if by_prio[prio]
        ),
        panels=len(by_pano),
        top_pano=top_pano,
        top_count=top_count,
        top_text=(contracts.alarm(top_code) or {}).get("text", top_code),
    )


def _most_common(counter: Counter) -> tuple[str, int]:
    """Counter.most_common yerine: esitlikte alfabetik ilk, boylece ayni veri ayni ozeti verir."""
    return min(counter.items(), key=lambda item: (-item[1], item[0]))


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
