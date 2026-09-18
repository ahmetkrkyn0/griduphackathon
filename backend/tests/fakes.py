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

from app.db import PHONE_CHANNELS, SERIES_ORIGIN, StoreError, UnknownPanel
from app.journal_chain import GENESIS, link_hash
from app.models import ASSET_FIELDS, EventRecord, JournalEntry, PanelRecord

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


def _health_projection(payload: dict) -> dict:
    """PgStore.list_panel_health'in SQL projeksiyonunun aynisi.

    _summary_projection'dan iki farki var ve ikisi de kasitli: saglik blogu
    KIRPILMAZ (tam gelir) ve jsonb_strip_nulls UYGULANMAZ — SQL tarafinda da
    uygulanmiyor, cunku eksik bir saglik alani None olarak gorunmek zorunda.

    `fw` yukun KOK seviyesinden gelir, health'in icinden degil.
    """
    return {"health": payload.get("health"), "fw": payload.get("fw")}


def _points_projection(payload: dict) -> dict:
    """PgStore.list_panel_points'in SQL projeksiyonunun aynisi (F-32).

    Yalnizca nokta dizisi ve zaman damgasi; ortam, elektrik ve risk bloklari
    disarida kalir. strip_nulls UYGULANMAZ — SQL tarafinda da uygulanmiyor.
    """
    return {"ts": payload.get("ts"), "t_conn": payload.get("t_conn")}


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
        self.events: dict[str, EventRecord] = {}
        self.journal: list[tuple] = []  # (alarm_id, at, action, state, by, note)
        self.chain: list[dict] = []     # F-20 hash zinciri satirlari (PgStore.journal_chain karsiligi)
        self.outages: dict[str, dict] = {}  # F-22 kesinti olaylari (outage_id -> satir)
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
        **asset,
    ) -> None:
        """Varlik kutugu alanlari (F-21) `**asset` ile verilir ve VARSAYILAN None'dir.

        Goc 008 her sutunu NULL kabul ettigi icin (bilinmeyen pano ilk telemetri mesajinda
        yalnizca pano_id + name ile kaydolur) testlerin de kunyesiz pano kurabilmesi sart.
        Bilinmeyen anahtar SESSIZCE YUTULMAZ: yazim hatasi yuzunden bir alanin hic
        yazilmamasi, testin yanlis seyi dogrulamasina yol acardi.
        """
        unknown = sorted(set(asset) - set(ASSET_FIELDS))
        if unknown:
            raise TypeError(f"add_panel: bilinmeyen varlik kutugu alani: {', '.join(unknown)}")
        self._meta[pano_id] = {
            "pano_id": pano_id,
            "name": name,
            "lat": lat,
            "lon": lon,
            "pano_type": pano_type,
            "installed_at": installed_at,
            "baseline_day": baseline_day,
            **dict.fromkeys(ASSET_FIELDS),
            **asset,
        }

    # -------------------------------------------------------- kesinti olayi (F-22)
    def save_outages(self, groups, *, detected_at: datetime) -> None:
        """PgStore.save_outages'in ikizi: ayni outage_id tekrar gelirse DEGISTIRMEZ."""
        self._check()
        for group in groups:
            if group.outage_id in self.outages:
                continue  # ON CONFLICT DO NOTHING karsiligi
            self.outages[group.outage_id] = {
                "outage_id": group.outage_id,
                "fider_id": group.fider_id,
                "started_at": group.started_at,
                "detected_at": detected_at,
                "ended_at": None,
                # Kunye kesinti aninda KOPYALANIR (PgStore'da da panels'a JOIN yok):
                # kunye sonradan degisirse gecmis kayit degismemeli.
                "panolar": [
                    {
                        "pano_id": p.pano_id,
                        "name": self._meta.get(p.pano_id, {}).get("name"),
                        "last_rx": p.last_rx,
                        "abone_sayisi": p.abone_sayisi,
                    }
                    for p in group.panels
                ],
            }

    def list_outages(self, *, only_open: bool) -> list[dict]:
        self._check()
        rows = [o for o in self.outages.values() if not only_open or o["ended_at"] is None]
        return sorted(rows, key=lambda o: o["started_at"], reverse=True)

    def get_outage(self, outage_id: str) -> dict | None:
        self._check()
        return self.outages.get(outage_id)

    def close_outages(self, outage_ids, *, at: datetime) -> None:
        self._check()
        for outage_id in outage_ids:
            row = self.outages.get(outage_id)
            if row is not None and row["ended_at"] is None:
                row["ended_at"] = at

    def import_assets(self, rows, *, kunye_kaynak: str, at: datetime) -> int:
        """PgStore.import_assets'in bellek ici ikizi (F-21).

        PgStore tek transaction'da calisir ve ortada bir UnknownPanel atarsa ONCEKI
        satirlar da geri alinir. Burada ayni GOZLENEBILIR sonucu vermek icin once TUM
        satirlar dogrulanir, sonra yazilir — yoksa taklit, gercegin yapmadigi bir kismi
        yazmayi yapar ve testler yanlis seyi dogrular.
        """
        self._check()
        for row in rows:
            if row["pano_id"] not in self._meta:
                raise UnknownPanel(row["pano_id"])
        for row in rows:
            meta = self._meta[row["pano_id"]]
            # GONDERILMEYEN alan DEGISTIRILMEZ; acikca null gonderilen alan temizlenir.
            meta.update({name: row[name] for name in ASSET_FIELDS if name in row})
            meta["kunye_kaynak"] = kunye_kaynak
            meta["kunye_at"] = at
        return len(rows)

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

    def list_panel_health(self) -> list[PanelRecord]:
        self._check()
        return [self._record(i, summary=False, health=True) for i in self._meta]

    def list_panel_points(self) -> list[PanelRecord]:
        self._check()
        return [self._record(i, summary=False, points=True) for i in self._meta]

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
            if change.opened_event:  # PgStore: payload {prio, point}, det_label yazilmaz
                self.events.setdefault(
                    alarm.event_id,
                    EventRecord(alarm.event_id, alarm.pano_id, alarm.raised_at, alarm.code, None, alarm.point, alarm.prio),
                )
            stored = self.alarms.get(alarm.id)
            if stored is not None:  # PgStore gibi: aciklama olustugu anin kanitidir
                alarm = replace(alarm, reason=stored.reason, advice=stored.advice, ttl_h=stored.ttl_h)
            self.alarms[alarm.id] = replace(alarm)
            # F-20: PgStore ile AYNI hesap. Iki taraf ayrisirsa testler yesil kalir ama
            # uretimde dogrulayici zinciri kopuk gorur — o yuzden ayni fonksiyon cagriliyor.
            prev = self.chain[-1]["hash"] if self.chain else GENESIS
            digest = link_hash(
                prev, alarm_id=alarm.id, at=at, action=change.kind,
                state=alarm.state, by_user=change.by, note=change.note,
            )
            self.chain.append({
                "id": len(self.chain) + 1, "alarm_id": alarm.id, "at": at,
                "action": change.kind, "state": alarm.state, "by_user": change.by,
                "note": change.note, "prev_hash": prev, "hash": digest,
            })
            self.journal.append((alarm.id, at, change.kind, alarm.state, change.by, change.note))

    def journal_chain(self) -> list[dict]:
        self._check()
        return [dict(row) for row in self.chain]

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

    # ------------------------------------------------------------ analiz uclari (TB3)
    def series(self, pano_id, tags, start, end, step):
        self._check()
        wanted = set(tags)
        buckets: dict[str, dict[datetime, list[float]]] = {}
        for ts, pid, tag, value, q in self.telemetry:
            if pid != pano_id or tag not in wanted or not start <= ts < end or q != 0 or value is None:
                continue
            bucket = SERIES_ORIGIN + ((ts - SERIES_ORIGIN) // step) * step
            buckets.setdefault(tag, {}).setdefault(bucket, []).append(value)
        return {tag: {b: sum(v) / len(v) for b, v in by_bucket.items()} for tag, by_bucket in buckets.items()}

    def get_event(self, event_id):
        self._check()
        return self.events.get(event_id)

    def panel_journal(self, pano_id, start, end):
        self._check()
        entries = []
        for alarm_id, at, action, state, by, note in self.journal:
            alarm = self.alarms[alarm_id]
            if alarm.pano_id == pano_id and start <= at <= end:
                entries.append(JournalEntry(at, action, state, by, note, alarm_id, alarm.code, alarm.prio, alarm.point))
        return sorted(entries, key=lambda e: e.at)  # kararli: esitlikte kayit sirasi

    def alarm_counts(self, since):
        self._check()
        counts: dict[str, int] = {}
        for alarm in self.alarms.values():
            if alarm.raised_at >= since:
                counts[alarm.prio] = counts.get(alarm.prio, 0) + 1
        return counts

    def delivery_latencies_ms(self, since):
        self._check()
        latencies = []
        for alarm in self.alarms.values():
            if alarm.raised_at < since:
                continue
            sent = [d.sent_at for d in self.notifications if d.alarm_id == alarm.id and d.ok and d.channel in PHONE_CHANNELS]
            if sent:
                latencies.append((min(sent) - alarm.raised_at).total_seconds() * 1000.0)
        return latencies

    # ------------------------------------------------------------ test yardimcilari
    def set_last_rx(self, pano_id: str, when: datetime) -> None:
        self._latest[pano_id]["last_rx"] = when

    def _check(self) -> None:
        if self.unavailable:
            raise StoreError("yapay baglanti hatasi")

    def _record(self, pano_id: str, summary: bool, health: bool = False, points: bool = False) -> PanelRecord:
        meta = self._meta[pano_id]
        latest = self._latest.get(pano_id)
        payload = None
        if latest is not None:
            if health:
                payload = _health_projection(latest["payload"])
            elif points:
                payload = _points_projection(latest["payload"])
            else:
                payload = _summary_projection(latest["payload"]) if summary else latest["payload"]
        return PanelRecord(
            **meta,
            last_rx=latest["last_rx"] if latest else None,
            payload=payload,
        )
