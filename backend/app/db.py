"""Depolama katmani (Kisi B).

`Store` sozlesmesini hem uretimdeki PgStore hem de testlerdeki bellek ici cift uygular.
Tablolar: deploy/initdb/001_schema.sql (panels, telemetry, quarantine, events, alarms),
002_ingest.sql (panel_latest) ve 003_alarms.sql (alarm_journal + durum makinesi zamanlari).
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import fields
from datetime import datetime
from typing import Any, Protocol

import psycopg
from psycopg.rows import class_row, dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool, PoolTimeout

from .alarm_manager import Alarm, Change
from .models import PanelRecord, Rejection, Sample


class StoreError(RuntimeError):
    """Gecici depolama hatasi (baglanti yok, zaman asimi). Tekrar denenebilir; API 503 doner."""


class Store(Protocol):
    def write_batch(self, samples: Sequence[Sample], rejections: Sequence[Rejection]) -> None:
        """Tek transaction: telemetri satirlari + son durum + karantina.

        - Bilinmeyen pano ilk mesajinda kaydolur (ad = pano_id).
        - Son durum yalnizca daha yeni `ts` ile degisir (backfill ezmez); `last_rx` her mesajda ilerler.
        - Gecici hatada StoreError atar; toplu yazmanin tamami geri alinir.
        """
        ...

    def list_panels(self, pano_ids: Sequence[str] | None = None) -> list[PanelRecord]:
        """Tum panolar (veya verilenler); payload yalnizca ozet alanlarini icerir:
        ts, risk, alarms, health.baseline_day."""
        ...

    def get_panel(self, pano_id: str) -> PanelRecord | None:
        """Tek pano, tam son yukle."""
        ...

    def ping(self) -> bool: ...

    # ------------------------------------------------------------ alarmlar (TB2)
    def save_alarm_changes(self, changes: Sequence[Change], at: datetime) -> None:
        """Tek transaction, verilen sirayla: yeni olaylar -> alarm satirlari (upsert) -> denetim izi.

        Ayni alarmin ardisik degisiklikleri (raised, acked) ayni partide gelebilir; son durum kalir.
        """
        ...

    def load_open_alarms(self) -> list[Alarm]:
        """Temizlenmemis tum alarmlar (yeniden baslatmada alarm yoneticisine geri yuklenir)."""
        ...

    def list_alarms(
        self, states: Sequence[str], prios: Sequence[str] | None, pano_id: str | None, limit: int
    ) -> list[Alarm]:
        """En yeni once (raised_at, esitlikte id)."""
        ...

    def get_alarm(self, alarm_id: int) -> Alarm | None: ...

    def next_alarm_id(self) -> int:
        """Alarm kimligini tek yazici alarm yoneticisi verir: acilista max(id) + 1."""
        ...


_REGISTER_PANEL = "INSERT INTO panels (pano_id, name) VALUES (%s, %s) ON CONFLICT (pano_id) DO NOTHING"

_COPY_TELEMETRY = "COPY telemetry (ts, pano_id, tag, value, q) FROM STDIN"

# Yalnizca daha yeni olcum son durumu degistirir; last_rx her mesajda ilerler.
_UPSERT_LATEST = """
INSERT INTO panel_latest AS cur (pano_id, ts, seq, last_rx, payload)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (pano_id) DO UPDATE SET
    ts      = CASE WHEN EXCLUDED.ts >= cur.ts THEN EXCLUDED.ts      ELSE cur.ts      END,
    seq     = CASE WHEN EXCLUDED.ts >= cur.ts THEN EXCLUDED.seq     ELSE cur.seq     END,
    payload = CASE WHEN EXCLUDED.ts >= cur.ts THEN EXCLUDED.payload ELSE cur.payload END,
    last_rx = GREATEST(cur.last_rx, EXCLUDED.last_rx)
"""

_INSERT_QUARANTINE = "INSERT INTO quarantine (received, topic, reason, raw) VALUES (%s, %s, %s, %s)"

_PANEL_COLUMNS = "p.pano_id, p.name, p.pano_type, p.lat, p.lon, p.installed_at, p.baseline_day, l.last_rx"

# Filo listesi 1.000 pano icin tam yukleri tasimasin: yalnizca ozetin okudugu alanlar.
_SUMMARY_PAYLOAD = """
CASE WHEN l.pano_id IS NULL THEN NULL ELSE jsonb_strip_nulls(jsonb_build_object(
    'ts',     l.payload -> 'ts',
    'risk',   l.payload -> 'risk',
    'alarms', l.payload -> 'alarms',
    'health', jsonb_build_object('baseline_day', l.payload -> 'health' -> 'baseline_day')
)) END
"""

_LIST_PANELS = f"""
SELECT {_PANEL_COLUMNS}, {_SUMMARY_PAYLOAD} AS payload
FROM panels p LEFT JOIN panel_latest l ON l.pano_id = p.pano_id
WHERE %(ids)s::text[] IS NULL OR p.pano_id = ANY(%(ids)s::text[])
ORDER BY p.pano_id
"""

_GET_PANEL = f"""
SELECT {_PANEL_COLUMNS}, l.payload
FROM panels p LEFT JOIN panel_latest l ON l.pano_id = p.pano_id
WHERE p.pano_id = %s
"""


ALARM_COLUMNS = tuple(f.name for f in fields(Alarm))

_INSERT_EVENT = """
INSERT INTO events (event_id, pano_id, occurred_at, code, payload)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (event_id) DO NOTHING
"""

# Aciklama (reason/advice/ttl_h) alarm olustugu anin kanitidir: guncellenmez.
_ALARM_MUTABLE = (
    "state", "last_true_at", "annunciated_at", "cleared_at", "acked_at", "acked_by",
    "shelved_until", "shelve_reason", "escalation_level", "notified",
)
_UPSERT_ALARM = f"""
INSERT INTO alarms ({", ".join(ALARM_COLUMNS)})
VALUES ({", ".join(f"%({c})s" for c in ALARM_COLUMNS)})
ON CONFLICT (id) DO UPDATE SET {", ".join(f"{c} = EXCLUDED.{c}" for c in _ALARM_MUTABLE)}
"""

_INSERT_JOURNAL = "INSERT INTO alarm_journal (alarm_id, at, action, state, by_user, note) VALUES (%s, %s, %s, %s, %s, %s)"

_SELECT_ALARMS = f"SELECT {', '.join(ALARM_COLUMNS)} FROM alarms"

_LIST_ALARMS = f"""
{_SELECT_ALARMS}
WHERE state = ANY(%(states)s::text[])
  AND (%(prios)s::text[] IS NULL OR prio = ANY(%(prios)s::text[]))
  AND (%(pano_id)s::text IS NULL OR pano_id = %(pano_id)s::text)
ORDER BY raised_at DESC, id DESC
LIMIT %(limit)s
"""


def _alarm_params(alarm: Alarm) -> dict[str, Any]:
    params = {name: getattr(alarm, name) for name in ALARM_COLUMNS}
    params["notified"] = list(alarm.notified)
    params["reason"] = Jsonb(alarm.reason)
    return params


def _alarm_from_row(row: dict[str, Any]) -> Alarm:
    return Alarm(**{**row, "notified": tuple(row["notified"])})


class PgStore:
    """PostgreSQL/TimescaleDB deposu (psycopg 3 baglanti havuzu).

    Baglanti/zaman asimi hatalari StoreError'a cevrilir (gecici, tekrar denenebilir);
    veri hatalari (ornegin tipe sigmayan deger) oldugu gibi yukselir.
    """

    def __init__(self, dsn: str, *, min_size: int = 1, max_size: int = 8, timeout_s: float = 5.0) -> None:
        self._pool = ConnectionPool(
            dsn,
            min_size=min_size,
            max_size=max_size,
            timeout=timeout_s,
            open=False,
            name="gridup",
        )
        self._pool.open(wait=False)

    def close(self) -> None:
        # DB erisilemezken havuz isci thread'leri baglanti denemesinde takili kalir; varsayilan
        # bekleme (isci basina 5 s) konteyner durdurmayi Docker'in 10 s SIGKILL sinirina tasir.
        self._pool.close(timeout=1.0)

    @contextmanager
    def _connection(self, timeout_s: float | None = None) -> Iterator[psycopg.Connection]:
        try:
            with self._pool.connection(timeout=timeout_s) as conn:
                yield conn
        except (PoolTimeout, psycopg.OperationalError) as exc:
            raise StoreError(str(exc)) from exc

    def write_batch(self, samples: Sequence[Sample], rejections: Sequence[Rejection]) -> None:
        if not samples and not rejections:
            return
        with self._connection() as conn, conn.cursor() as cur:
            if samples:
                pano_ids = dict.fromkeys(sample.pano_id for sample in samples)
                cur.executemany(_REGISTER_PANEL, [(pano_id, pano_id) for pano_id in pano_ids])
                with cur.copy(_COPY_TELEMETRY) as copy:
                    for sample in samples:
                        for row in sample.rows:
                            copy.write_row((sample.ts, sample.pano_id, row.tag, row.value, row.q))
                cur.executemany(
                    _UPSERT_LATEST,
                    [(s.pano_id, s.ts, s.seq, s.received_at, Jsonb(s.payload)) for s in samples],
                )
            if rejections:
                cur.executemany(
                    _INSERT_QUARANTINE,
                    [(r.received_at, r.topic, r.reason, Jsonb(r.raw)) for r in rejections],
                )

    def list_panels(self, pano_ids: Sequence[str] | None = None) -> list[PanelRecord]:
        ids = list(pano_ids) if pano_ids is not None else None
        with self._connection() as conn, conn.cursor(row_factory=class_row(PanelRecord)) as cur:
            return cur.execute(_LIST_PANELS, {"ids": ids}).fetchall()

    def get_panel(self, pano_id: str) -> PanelRecord | None:
        with self._connection() as conn, conn.cursor(row_factory=class_row(PanelRecord)) as cur:
            return cur.execute(_GET_PANEL, (pano_id,)).fetchone()

    def ping(self) -> bool:
        try:
            with self._connection(timeout_s=1.0) as conn:
                conn.execute("SELECT 1")
            return True
        except StoreError:
            return False

    # ------------------------------------------------------------ alarmlar (TB2)
    def save_alarm_changes(self, changes: Sequence[Change], at: datetime) -> None:
        if not changes:
            return
        with self._connection() as conn, conn.cursor() as cur:
            events = [
                (c.alarm.event_id, c.alarm.pano_id, c.alarm.raised_at, c.alarm.code,
                 Jsonb({"prio": c.alarm.prio, "point": c.alarm.point}))
                for c in changes
                if c.opened_event
            ]
            if events:
                cur.executemany(_INSERT_EVENT, events)
            cur.executemany(_UPSERT_ALARM, [_alarm_params(c.alarm) for c in changes])
            cur.executemany(
                _INSERT_JOURNAL,
                [(c.alarm.id, at, c.kind, c.alarm.state, c.by, c.note) for c in changes],
            )

    def load_open_alarms(self) -> list[Alarm]:
        return self._select_alarms(f"{_SELECT_ALARMS} WHERE state <> 'cleared' ORDER BY id", ())

    def list_alarms(
        self, states: Sequence[str], prios: Sequence[str] | None, pano_id: str | None, limit: int
    ) -> list[Alarm]:
        params = {
            "states": list(states),
            "prios": list(prios) if prios is not None else None,
            "pano_id": pano_id,
            "limit": limit,
        }
        return self._select_alarms(_LIST_ALARMS, params)

    def get_alarm(self, alarm_id: int) -> Alarm | None:
        alarms = self._select_alarms(f"{_SELECT_ALARMS} WHERE id = %s", (alarm_id,))
        return alarms[0] if alarms else None

    def next_alarm_id(self) -> int:
        with self._connection() as conn:
            (value,) = conn.execute("SELECT COALESCE(max(id), 0) + 1 FROM alarms").fetchone()
            return int(value)

    def _select_alarms(self, query: str, params: Any) -> list[Alarm]:
        with self._connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            return [_alarm_from_row(row) for row in cur.execute(query, params).fetchall()]
