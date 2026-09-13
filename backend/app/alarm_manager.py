"""ISA-18.2 alarm yoneticisi (TB2, Kisi B).

Saf durum makinesi: veritabani, ag ve saat bagimliligi yoktur; zaman disaridan verilir.
Kalicilik, WebSocket yayini ve bildirim ust katmandadir — bu modul yalnizca "ne degisti"yi
`Change` listesi olarak dondurur.

Yasam dongusu (contracts/openapi.yaml Alarm.state; H = hysteresis_clear_min):

    kosul geldi ─────────────► active ──ack──► acked ──kosul H dk yok──► cleared
                                 │                │
                                 │                └─shelve─► shelved ──kosul H dk yok──► cleared
                                 ├─shelve(sure, gerekce)─►┘   └─sure doldu──► active (yeniden duyurulur)
                                 ├─kosul H dk yok, bastirilabilir──► cleared   (mandalsiz)
                                 └─kosul H dk yok, bastirilamaz (P1)──► active + cleared_at
                                                                        ("RTN unack": mandalli, ack ile cleared)

Zaman tabani:
  - Histerezis ve gruplama OLAY zamaniyla (telemetri `ts`) olculur: sure fizikseldir,
    hizlandirilmis senaryo oynatmada da ayni davranir.
  - Raf suresi ve eskalasyon DUVAR saatiyle (`now`) olculur: sure operatorun tepki suresidir.
  - Panonun en son isledigi `ts`'ten eski ornekler (kopukluk sonrasi backfill) canli alarm
    durumunu degistirmez; gecmis veri yine de telemetri tablosunda saklanir.

Alarm seli onleme (rapor 6.6b):
  - Bakim modunda bastirilabilir alarmlar olusmaz; bastirilamaz (P1) alarmlar her zaman olusur.
  - Ayni panoda `group_window_min` icinde ayni kok nedenden (ortak hipotez kaniti veya ayni
    baglanti noktasi) gelen alarmlar tek olayda toplanir; P1 ile acilan olay, pencere icindeki
    sonraki tum alarmlari altina alir (ilk-cikan / first-out).
  - Olayin ilk alarmi, olaydakilerden daha acil bir alarm ve her P1 telefonu cagirir (`notify`);
    ayni olayin esit/dusuk oncelikli tekrarlari cagirmaz. Hangi kanalin kullanilacagini
    oncelik tablosu (priorities.*.sms/whatsapp) belirler, bu modul degil.

Tum esikler ve oncelik ozellikleri contracts/alarm-codes.yaml'dan okunur (PLAN.md kural 10).
"""

from __future__ import annotations

import itertools
import logging
import threading
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from typing import Any, Literal

from .config import PRIO_ORDER, Contracts

log = logging.getLogger("gridup.alarms")

ChangeKind = Literal["raised", "reactivated", "returned", "cleared", "acked", "shelved", "unshelved", "escalated", "notified"]
AlarmKey = tuple[str, str, str | None]  # (pano_id, code, point)

SHELVE_MIN_REASON_CHARS = 3  # contracts/openapi.yaml shelve.reason minLength


class AlarmNotFound(LookupError):
    """Acik alarmlar arasinda bu kimlik yok (hic olmamis veya temizlenmis)."""


class AlarmStateConflict(RuntimeError):
    """Istenen gecis alarmin su anki durumunda yapilamaz (or. iki kez onay)."""


class AlarmNotSuppressible(PermissionError):
    """Bastirilamaz oncelik (P1) rafa alinamaz."""


@dataclass(frozen=True)
class Condition:
    """Bir ornekte dogru olan alarm kosulu; `reason`/`advice`/`ttl_h` alarm olustugu an saklanir."""

    code: str
    point: str | None = None
    reason: dict[str, Any] = field(default_factory=dict)
    advice: str | None = None
    ttl_h: float | None = None


@dataclass
class Alarm:
    id: int
    pano_id: str
    code: str
    prio: str
    point: str | None
    event_id: str
    raised_at: datetime  # olay zamani
    last_true_at: datetime  # olay zamani; histerezis bundan olculur
    annunciated_at: datetime  # duvar saati; eskalasyon bundan olculur
    state: str = "active"
    cleared_at: datetime | None = None
    acked_at: datetime | None = None
    acked_by: str | None = None
    shelved_until: datetime | None = None
    shelve_reason: str | None = None
    escalation_level: int = 0
    notified: tuple[str, ...] = ()
    reason: dict[str, Any] = field(default_factory=dict)
    advice: str | None = None
    ttl_h: float | None = None

    @property
    def key(self) -> AlarmKey:
        return (self.pano_id, self.code, self.point)


@dataclass(frozen=True)
class Change:
    kind: ChangeKind
    alarm: Alarm  # degisiklik anindaki kopya
    notify: bool = False
    opened_event: bool = False
    by: str | None = None
    note: str | None = None
    step: str | None = None  # escalated: "call" | "escalate"; notified: kanal


@dataclass
class _Event:
    event_id: str
    opened_at: datetime
    first_out: bool  # bastirilamaz bir alarmla acildi
    hypotheses: set[str]
    points: set[str]
    best_rank: int


class AlarmManager:
    def __init__(self, contracts: Contracts, *, first_id: int = 1) -> None:
        thresholds = contracts.thresholds
        self._hysteresis = timedelta(minutes=thresholds["hysteresis_clear_min"])
        self._group_window = timedelta(minutes=thresholds["group_window_min"])
        self._shelve_max_min = int(thresholds["shelve_max_min"])
        self._contracts = contracts
        priorities = contracts.alarm_codes["priorities"]
        self._suppressible = {prio: bool(spec.get("suppressible", True)) for prio, spec in priorities.items()}
        # Onaysiz alarmin eskalasyon adimlari (dakika sirasiyla): P1 once arama, sonra ust amir
        self._escalation = {
            prio: sorted(
                (timedelta(minutes=spec[field]), step)
                for field, step in (("call_after_min", "call"), ("escalate_after_min", "escalate"))
                if field in spec
            )
            for prio, spec in priorities.items()
        }
        self._hypotheses: dict[str, set[str]] = {}
        for hypothesis in contracts.alarm_codes["hypotheses"]:
            for code in hypothesis["evidence"]:
                self._hypotheses.setdefault(code, set()).add(hypothesis["code"])

        self._ids = itertools.count(first_id)
        self._lock = threading.RLock()
        self._open: dict[str, dict[AlarmKey, Alarm]] = {}  # pano_id -> acik alarmlar
        self._by_id: dict[int, Alarm] = {}
        self._events: dict[str, list[_Event]] = {}
        self._last_ts: dict[str, datetime] = {}
        self._maint: dict[str, bool] = {}  # panonun son ornegindeki bakim modu
        self._restored: set[int] = set()  # histerezis saati henuz ilk ornekle baslatilmamis
        self.stats = {"raised": 0, "cleared": 0, "suppressed_maint": 0, "backfill_ignored": 0, "unknown_codes": 0}

    # ------------------------------------------------------------ sorgular
    def get(self, alarm_id: int) -> Alarm | None:
        with self._lock:
            alarm = self._by_id.get(alarm_id)
            return replace(alarm) if alarm else None

    def open_alarms(self, pano_id: str | None = None) -> list[Alarm]:
        with self._lock:
            alarms = self._by_id.values() if pano_id is None else self._open.get(pano_id, {}).values()
            return [replace(alarm) for alarm in sorted(alarms, key=lambda a: a.id)]

    # ------------------------------------------------------------- girdiler
    def restore(self, alarms: Iterable[Alarm]) -> None:
        """Depodan yuklenen acik alarmlari geri koyar (yeniden baslatma).

        Depodaki `last_true_at` yalnizca durum degisiminde yazilir, yani eskidir; kesinti boyunca
        kosulun ne oldugu bilinmez. Bu yuzden histerezis panonun yeniden baslatma sonrasi ilk
        orneginden baslar: dogrulanmadan temizlenmez. Olay gruplari geri yuklenmez.
        """
        with self._lock:
            for alarm in alarms:
                restored = replace(alarm)
                self._open.setdefault(alarm.pano_id, {})[alarm.key] = restored
                self._by_id[alarm.id] = restored
                self._restored.add(alarm.id)

    def observe(
        self,
        pano_id: str,
        ts: datetime,
        conditions: Iterable[Condition],
        *,
        now: datetime,
        maint_mode: bool = False,
    ) -> list[Change]:
        """Panonun `ts` anindaki TUM dogru kosullari; listede olmayan kod o an yok sayilir."""
        with self._lock:
            last = self._last_ts.get(pano_id)
            if last is not None and ts < last:
                self.stats["backfill_ignored"] += 1
                return []
            self._last_ts[pano_id] = ts
            self._maint[pano_id] = maint_mode

            present: dict[AlarmKey, Condition] = {}
            for condition in conditions:
                if self._contracts.alarm(condition.code) is None:
                    self.stats["unknown_codes"] += 1
                    log.warning("sozlesmede olmayan alarm kodu yok sayildi: %s (%s)", condition.code, pano_id)
                    continue
                present.setdefault((pano_id, condition.code, condition.point), condition)

            open_alarms = self._open.setdefault(pano_id, {})
            for alarm in open_alarms.values():
                if alarm.id in self._restored:
                    alarm.last_true_at = max(alarm.last_true_at, ts)
                    self._restored.discard(alarm.id)
            changes: list[Change] = []
            for key, condition in present.items():
                alarm = open_alarms.get(key)
                if alarm is None:
                    prio = self._contracts.prio_of(condition.code)
                    if maint_mode and self._suppressible[prio]:
                        self.stats["suppressed_maint"] += 1
                        continue
                    changes.append(self._raise(pano_id, condition, prio, ts, now))
                    continue
                alarm.last_true_at = ts
                if alarm.cleared_at is not None:  # mandalli P1 onaylanmadan tekrar alarma girdi
                    alarm.cleared_at = None
                    changes.append(Change("reactivated", replace(alarm)))

            for alarm in [a for key, a in open_alarms.items() if key not in present]:
                if ts - alarm.last_true_at < self._hysteresis:
                    continue
                if alarm.state == "active" and not self._suppressible[alarm.prio]:
                    if alarm.cleared_at is None:
                        alarm.cleared_at = ts
                        changes.append(Change("returned", replace(alarm)))
                    continue
                alarm.cleared_at = ts
                changes.append(self._close(alarm, "cleared"))
            return changes

    def assert_condition(self, pano_id: str, condition: Condition, *, ts: datetime, now: datetime) -> list[Change]:
        """Merkezde uretilen kosul (or. haberlesme kopuklugu) `ts` aninda dogru.

        `observe`'un aksine panonun diger kosullarinin yoklugunu degerlendirmez. Kosul, panodan
        yeniden veri gelip `observe` onu H dk boyunca gormeyince temizlenir. Panonun son ornegi
        bakim modundaysa bastirilabilir kosul olusmaz.
        """
        with self._lock:
            if self._contracts.alarm(condition.code) is None:
                self.stats["unknown_codes"] += 1
                return []
            open_alarms = self._open.setdefault(pano_id, {})
            alarm = open_alarms.get((pano_id, condition.code, condition.point))
            if alarm is None:
                prio = self._contracts.prio_of(condition.code)
                if self._maint.get(pano_id, False) and self._suppressible[prio]:
                    self.stats["suppressed_maint"] += 1
                    return []
                return [self._raise(pano_id, condition, prio, ts, now)]
            alarm.last_true_at = max(alarm.last_true_at, ts)
            if alarm.cleared_at is not None:
                alarm.cleared_at = None
                return [Change("reactivated", replace(alarm))]
            return []

    def ack(self, alarm_id: int, *, by: str, now: datetime, note: str | None = None) -> Change:
        with self._lock:
            alarm = self._find(alarm_id)
            if alarm.state not in ("active", "shelved"):
                raise AlarmStateConflict(f"alarm {alarm_id} onaylanamaz: durum {alarm.state}")
            alarm.acked_at = now
            alarm.acked_by = by
            alarm.shelved_until = None
            alarm.shelve_reason = None
            if alarm.cleared_at is not None:  # normale donmus mandalli alarm: onay son adimdir
                return self._close(alarm, "acked", by=by, note=note)
            alarm.state = "acked"
            return Change("acked", replace(alarm), by=by, note=note)

    def shelve(self, alarm_id: int, *, by: str, minutes: int, reason: str, now: datetime) -> Change:
        with self._lock:
            alarm = self._find(alarm_id)
            if not self._suppressible[alarm.prio]:
                raise AlarmNotSuppressible(f"{alarm.prio} alarm rafa alinamaz (suppressible=false)")
            if not 1 <= minutes <= self._shelve_max_min:
                raise ValueError(f"raf suresi 1-{self._shelve_max_min} dk olmali: {minutes}")
            if len((reason or "").strip()) < SHELVE_MIN_REASON_CHARS:
                raise ValueError("raf gerekcesi zorunludur")
            if alarm.state not in ("active", "acked"):
                raise AlarmStateConflict(f"alarm {alarm_id} rafa alinamaz: durum {alarm.state}")
            alarm.state = "shelved"
            alarm.shelved_until = now + timedelta(minutes=minutes)
            alarm.shelve_reason = reason.strip()
            return Change("shelved", replace(alarm), by=by, note=alarm.shelve_reason)

    def mark_notified(self, alarm_id: int, channel: str) -> Change | None:
        """Basarili teslimde kanal alarmin `notified` listesine bir kez eklenir (arayuzdeki kanal rozetleri)."""
        with self._lock:
            alarm = self._by_id.get(alarm_id)
            if alarm is None or channel in alarm.notified:
                return None
            alarm.notified = (*alarm.notified, channel)
            return Change("notified", replace(alarm), step=channel, note=channel)

    def tick(self, now: datetime) -> list[Change]:
        """Duvar saatine bagli zamanlayicilar.

        - Raf suresi dolan alarm yeniden duyurulur (onaysiz, eskalasyon zinciri bastan).
        - Onaysiz (active) alarm, duyuruldugundan beri gecen sureye gore oncelik tablosundaki eskalasyon
          adimlarini sirayla atar; gecikmis tick'te birikmis adimlarin hepsi sirayla atilir. Bakimdaki
          panoda bastirilabilir alarmin eskalasyonu bekler; P1'inki beklemez.
        """
        with self._lock:
            changes: list[Change] = []
            for alarm in sorted(self._by_id.values(), key=lambda a: a.id):
                if alarm.state == "shelved" and alarm.shelved_until <= now:
                    alarm.state = "active"
                    alarm.shelved_until = None
                    alarm.shelve_reason = None
                    alarm.acked_at = None
                    alarm.acked_by = None
                    alarm.annunciated_at = now
                    alarm.escalation_level = 0
                    changes.append(Change("unshelved", replace(alarm), notify=True))
                    continue
                if alarm.state != "active":
                    continue
                if self._maint.get(alarm.pano_id, False) and self._suppressible[alarm.prio]:
                    continue
                schedule = self._escalation[alarm.prio]
                elapsed = now - alarm.annunciated_at
                while alarm.escalation_level < len(schedule) and elapsed >= schedule[alarm.escalation_level][0]:
                    step = schedule[alarm.escalation_level][1]
                    alarm.escalation_level += 1
                    changes.append(Change("escalated", replace(alarm), notify=True, step=step, note=step))
            return changes

    # ------------------------------------------------------------- ic isler
    def _find(self, alarm_id: int) -> Alarm:
        alarm = self._by_id.get(alarm_id)
        if alarm is None:
            raise AlarmNotFound(f"acik alarm yok: {alarm_id}")
        return alarm

    def _raise(self, pano_id: str, condition: Condition, prio: str, ts: datetime, now: datetime) -> Change:
        alarm_id = next(self._ids)
        rank = PRIO_ORDER.index(prio)
        hypotheses = self._hypotheses.get(condition.code, set())
        suppressible = self._suppressible[prio]

        event = self._find_event(pano_id, ts, hypotheses, condition.point)
        if event is None:
            event = _Event(
                event_id=f"EVT-{alarm_id}",
                opened_at=ts,
                first_out=not suppressible,
                hypotheses=set(hypotheses),
                points=set(),
                best_rank=rank,
            )
            self._events.setdefault(pano_id, []).append(event)
            notify, opened = True, True
        else:
            notify, opened = (not suppressible) or rank < event.best_rank, False
            event.hypotheses |= hypotheses
            event.best_rank = min(event.best_rank, rank)
        if condition.point is not None:
            event.points.add(condition.point)

        alarm = Alarm(
            id=alarm_id,
            pano_id=pano_id,
            code=condition.code,
            prio=prio,
            point=condition.point,
            event_id=event.event_id,
            raised_at=ts,
            last_true_at=ts,
            annunciated_at=now,
            reason=condition.reason,
            advice=condition.advice,
            ttl_h=condition.ttl_h,
        )
        self._open[pano_id][alarm.key] = alarm
        self._by_id[alarm_id] = alarm
        self.stats["raised"] += 1
        return Change("raised", replace(alarm), notify=notify, opened_event=opened)

    def _find_event(self, pano_id: str, ts: datetime, hypotheses: set[str], point: str | None) -> _Event | None:
        events = self._events.get(pano_id, [])
        events[:] = [e for e in events if ts - e.opened_at <= self._group_window]
        for event in reversed(events):
            if event.first_out or hypotheses & event.hypotheses or (point is not None and point in event.points):
                return event
        return None

    def _close(self, alarm: Alarm, kind: ChangeKind, **extra: Any) -> Change:
        alarm.state = "cleared"
        alarm.shelved_until = None
        alarm.shelve_reason = None
        del self._open[alarm.pano_id][alarm.key]
        del self._by_id[alarm.id]
        self.stats["cleared"] += 1
        return Change(kind, replace(alarm), **extra)
