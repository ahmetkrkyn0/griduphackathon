"""Depolama katmani (Kisi B).

`Store` sozlesmesini hem uretimdeki PgStore hem de testlerdeki bellek ici cift uygular.
Tablolar: deploy/initdb/001_schema.sql (panels, telemetry, quarantine) ve 002_ingest.sql (panel_latest).
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Protocol

import psycopg
from psycopg.rows import class_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool, PoolTimeout

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
