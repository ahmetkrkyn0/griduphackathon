"""`app.db.Store` sozlesmesinin bellek ici test cifti.

Uretimde PgStore kullanilir; bu sinif yalnizca DB gerektirmeyen testler icindir ve
PgStore'un belgelenmis davranisini taklit eder:
  - bilinmeyen pano ilk mesajinda kendiliginden kaydolur (ad = pano_id)
  - son durum yalnizca DAHA YENI `ts` ile degisir (backfill ezmez); `last_rx` her mesajda ilerler
  - list_panels() PgStore gibi yalnizca ozet alanlarini dondurur, get_panel() tam yuku
  - alarm satirinda aciklama (reason/advice/ttl_h) ilk yazimdan sonra degismez; liste en yeni once
PgStore'un kendisi tests/test_db_integration.py ve tests/test_alarm_store.py icinde gercek
TimescaleDB'ye karsi test edilir.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from app.db import StoreError
from app.models import PanelRecord

DEFAULT_INSTALLED_AT = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _summary_projection(payload: dict) -> dict:
    """PgStore.list_panels'in SQL projeksiyonunun aynisi (jsonb_strip_nulls dahil)."""
    projected = {
        "ts": payload.get("ts"),
        "risk": payload.get("risk"),
        "alarms": payload.get("alarms"),
        "health": {"baseline_day": (payload.get("health") or {}).get("baseline_day")},
    }
    return _strip_nulls(projected)


def _strip_nulls(value):
    if isinstance(value, dict):
        return {k: _strip_nulls(v) for k, v in value.items() if v is not None}
    return value


class MemoryStore:
    def __init__(self, panels: tuple[dict, ...] | list[dict] = ()) -> None:
        self._meta: dict[str, dict] = {}
        self._latest: dict[str, dict] = {}
        self.telemetry: list[tuple] = []  # (ts, pano_id, tag, value, q)
        self.quarantined: list[tuple] = []  # (received, topic, reason, raw)
        self.batches: list[tuple[list, list]] = []
        self.fail_writes = 0  # >0 ise siradaki N yazma `fail_exc` atar
        self.fail_exc: Exception = StoreError("yapay yazma hatasi")
        self.poison_pano: str | None = None  # bu panonun mesajini iceren her yazma veri hatasi verir
        self.unavailable = False  # True ise okumalar ve alarm yazimlari StoreError atar
        self.alarms: dict[int, object] = {}  # id -> Alarm
        self.events: dict[str, tuple] = {}  # event_id -> (pano_id, occurred_at, code)
        self.journal: list[tuple] = []  # (alarm_id, at, action, state, by, note)
        self.fail_alarm_saves = 0  # >0 ise siradaki N alarm yazimi StoreError atar
        self.notifications: list = []  # Delivery kayitlari
        for panel in panels:
            self.add_panel(**panel)

    def add_panel(
        self,
        pano_id: str,
        name: str,
        lat: float | None = None,
        lon: float | None = None,
        pano_type: str = "1600kVA-dahili",
        installed_at: datetime = DEFAULT_INSTALLED_AT,
        baseline_day: int = 0,
    ) -> None:
        self._meta[pano_id] = {
            "pano_id": pano_id,
            "name": name,
            "lat": lat,
            "lon": lon,
            "pano_type": pano_type,
            "installed_at": installed_at,
            "baseline_day": baseline_day,
        }

    # ----------------------------------------------------------- Store sozlesmesi
    def write_batch(self, samples, rejections) -> None:
        if self.fail_writes > 0:
            self.fail_writes -= 1
            raise self.fail_exc
        if any(s.pano_id == self.poison_pano for s in samples):
            raise ValueError(f"yapay veri hatasi: {self.poison_pano}")
        self.batches.append((list(samples), list(rejections)))
        for s in samples:
            if s.pano_id not in self._meta:
                self.add_panel(s.pano_id, s.pano_id)
            self.telemetry.extend((s.ts, s.pano_id, r.tag, r.value, r.q) for r in s.rows)
            current = self._latest.get(s.pano_id)
            if current is None or s.ts >= current["ts"]:
                last_rx = s.received_at if current is None else max(current["last_rx"], s.received_at)
                self._latest[s.pano_id] = {"ts": s.ts, "payload": s.payload, "last_rx": last_rx}
            else:
                current["last_rx"] = max(current["last_rx"], s.received_at)
        for r in rejections:
            self.quarantined.append((r.received_at, r.topic, r.reason, r.raw))

    def list_panels(self, pano_ids=None) -> list[PanelRecord]:
        self._check()
        ids = self._meta.keys() if pano_ids is None else [i for i in pano_ids if i in self._meta]
        return [self._record(i, summary=True) for i in ids]

    def get_panel(self, pano_id: str) -> PanelRecord | None:
        self._check()
        return self._record(pano_id, summary=False) if pano_id in self._meta else None

    def ping(self) -> bool:
        return not self.unavailable

    def save_alarm_changes(self, changes, at) -> None:
        self._check()
        if self.fail_alarm_saves > 0:
            self.fail_alarm_saves -= 1
            raise StoreError("yapay alarm yazma hatasi")
        for change in changes:
            alarm = change.alarm
            if change.opened_event:
                self.events.setdefault(alarm.event_id, (alarm.pano_id, alarm.raised_at, alarm.code))
            stored = self.alarms.get(alarm.id)
            if stored is not None:  # PgStore gibi: aciklama olustugu anin kanitidir
                alarm = replace(alarm, reason=stored.reason, advice=stored.advice, ttl_h=stored.ttl_h)
            self.alarms[alarm.id] = replace(alarm)
            self.journal.append((alarm.id, at, change.kind, alarm.state, change.by, change.note))

    def load_open_alarms(self):
        self._check()
        return [replace(a) for _, a in sorted(self.alarms.items()) if a.state != "cleared"]

    def list_alarms(self, states, prios, pano_id, limit):
        self._check()
        selected = [
            a
            for a in self.alarms.values()
            if a.state in states and (prios is None or a.prio in prios) and (pano_id is None or a.pano_id == pano_id)
        ]
        selected.sort(key=lambda a: (a.raised_at, a.id), reverse=True)
        return [replace(a) for a in selected[:limit]]

    def get_alarm(self, alarm_id: int):
        self._check()
        alarm = self.alarms.get(alarm_id)
        return replace(alarm) if alarm else None

    def next_alarm_id(self) -> int:
        self._check()
        return max(self.alarms, default=0) + 1

    def record_notification(self, delivery) -> None:
        self._check()
        self.notifications.append(delivery)

    # ------------------------------------------------------------ test yardimcilari
    def set_last_rx(self, pano_id: str, when: datetime) -> None:
        self._latest[pano_id]["last_rx"] = when

    def _check(self) -> None:
        if self.unavailable:
            raise StoreError("yapay baglanti hatasi")

    def _record(self, pano_id: str, summary: bool) -> PanelRecord:
        meta = self._meta[pano_id]
        latest = self._latest.get(pano_id)
        payload = None
        if latest is not None:
            payload = _summary_projection(latest["payload"]) if summary else latest["payload"]
        return PanelRecord(
            **meta,
            last_rx=latest["last_rx"] if latest else None,
            payload=payload,
        )
