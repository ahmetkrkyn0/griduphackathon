"""TB1 — PgStore'un gercek PostgreSQL/TimescaleDB'ye karsi davranisi.

Yigin ayaktayken calistirma:
    TEST_DB_DSN=postgresql://postgres:gridup@localhost:5432/gridup pytest -m integration

Tablolar deploy/initdb/*.sql ile olusmus olmalidir. Testler yalnizca kendi urettikleri
TST-xxxxx panolarini yazar ve siler; demo verisine dokunmaz.
"""

from __future__ import annotations

import copy
import os
import random
from datetime import timedelta

import psycopg
import pytest

from app.db import PgStore, StoreError
from app.ingest import IngestPipeline
from app.models import Rejection
from helpers import encode, utc

DSN = os.getenv("TEST_DB_DSN")
needs_db = pytest.mark.skipif(not DSN, reason="TEST_DB_DSN tanimli degil (gercek veritabani gerekir)")
pytestmark = pytest.mark.integration

RX = utc(2026, 9, 13, 10, 0, 2)


@pytest.fixture
def pano_id() -> str:
    return f"TST-{random.randrange(100_000):05d}"


@pytest.fixture
def db(pano_id):
    with psycopg.connect(DSN, autocommit=True) as conn:
        yield conn
        conn.execute("DELETE FROM telemetry WHERE pano_id = %s", (pano_id,))
        conn.execute("DELETE FROM panel_latest WHERE pano_id = %s", (pano_id,))
        conn.execute("DELETE FROM quarantine WHERE topic LIKE %s", (f"gridup/pano/{pano_id}/%",))
        conn.execute("DELETE FROM panels WHERE pano_id = %s", (pano_id,))


@pytest.fixture
def store(db):
    pg = PgStore(DSN)
    yield pg
    pg.close()


def make_payload(tel_payload: dict, pano_id: str, **changes) -> dict:
    payload = copy.deepcopy(tel_payload)
    payload["pano_id"] = pano_id
    payload.update(changes)
    return payload


def ingest(contracts, store, payload: dict, received_at=RX) -> IngestPipeline:
    pipeline = IngestPipeline(contracts, store, clock=lambda: received_at)
    pipeline.handle_message(f"gridup/pano/{payload['pano_id']}/tel", encode(payload))
    assert pipeline.flush()
    assert pipeline.stats["dropped"] == 0
    return pipeline


@needs_db
def test_rows_are_written_in_long_format_and_unknown_panel_registers(contracts, store, db, tel_payload, pano_id):
    ingest(contracts, store, make_payload(tel_payload, pano_id))

    [(count,)] = db.execute("SELECT count(*) FROM telemetry WHERE pano_id = %s", (pano_id,)).fetchall()
    assert count == 67
    row = db.execute(
        "SELECT ts, value, q FROM telemetry WHERE pano_id = %s AND tag = 't_conn.GIRIS_N.dt_c'", (pano_id,)
    ).fetchone()
    assert row == (utc(2026, 9, 13, 10, 0, 0), 2.1, 4)
    assert db.execute("SELECT name FROM panels WHERE pano_id = %s", (pano_id,)).fetchone() == (pano_id,)


@needs_db
def test_quality_bits_above_smallint_range_are_stored(contracts, store, db, tel_payload, pano_id):
    payload = make_payload(tel_payload, pano_id)
    payload["t_conn"][3]["q"] = 1 << 16  # ALM-DQ-BELOW-AMBIENT biti

    ingest(contracts, store, payload)

    [(q,)] = db.execute(
        "SELECT DISTINCT q FROM telemetry WHERE pano_id = %s AND tag LIKE 't_conn.GIRIS_N.%%'", (pano_id,)
    ).fetchall()
    assert q == 65536


@needs_db
def test_get_panel_returns_full_latest_payload(contracts, store, tel_payload, pano_id):
    payload = make_payload(tel_payload, pano_id)
    ingest(contracts, store, payload)

    record = store.get_panel(pano_id)

    assert record.payload == payload
    assert record.last_rx == RX
    assert (record.name, record.lat, record.lon, record.baseline_day) == (pano_id, None, None, 0)
    assert record.installed_at is not None


@needs_db
def test_backfill_keeps_latest_state_but_refreshes_last_rx(contracts, store, db, tel_payload, pano_id):
    ingest(contracts, store, make_payload(tel_payload, pano_id, seq=42), received_at=RX)
    older = make_payload(tel_payload, pano_id, seq=7, ts="2026-09-13T09:00:00+00:00")
    ingest(contracts, store, older, received_at=RX + timedelta(minutes=5))

    record = store.get_panel(pano_id)

    assert record.payload["seq"] == 42
    assert record.last_rx == RX + timedelta(minutes=5)
    [(count,)] = db.execute("SELECT count(*) FROM telemetry WHERE pano_id = %s", (pano_id,)).fetchall()
    assert count == 134  # gecmis veri de saklanir


@needs_db
def test_list_panels_projects_only_summary_fields(contracts, store, tel_payload, pano_id):
    payload = make_payload(tel_payload, pano_id)
    payload["risk"]["ttl_h"] = None
    ingest(contracts, store, payload)

    [record] = store.list_panels([pano_id])

    assert record.payload == {
        "ts": "2026-09-13T10:00:00+00:00",
        "risk": {"score": 38, "mode": "HYP-LOOSE-CONN", "contributions": {"ALM-K-WARN": 0.6, "ALM-THR-TERM-WARN": 0.4}},
        "alarms": ["ALM-THR-TERM-WARN", "ALM-K-WARN"],
        "health": {"baseline_day": 7},
    }
    assert record.last_rx == RX


@needs_db
def test_list_panel_health_projects_health_block_and_root_fw(contracts, store, tel_payload, pano_id):
    """GET /fleet/health'in SQL projeksiyonu: saglik blogu TAM, `fw` kokten yukseltilmis.

    MemoryStore bunu taklit ediyor (fakes._health_projection); burada gercek
    TimescaleDB'ye karsi sinanir — iki taraf ayrisirsa testler yesil kalir ama
    uretimde ekran bos alan gosterir.
    """
    ingest(contracts, store, make_payload(tel_payload, pano_id))

    [record] = [r for r in store.list_panel_health() if r.pano_id == pano_id]

    assert record.payload == {
        "health": {
            "uptime_s": 86400, "nodes_ok": 5, "nodes_total": 5, "rssi_dbm": -71.0,
            "vbak_pct": 100.0, "buffered": 0, "maint_mode": False, "baseline_day": 7,
        },
        "fw": "0.1.0",
    }
    assert record.last_rx == RX
    # Tam yuk CEKILMEZ: 1.000 panoda fark buradan gelir.
    assert "t_conn" not in record.payload and "elec" not in record.payload


@needs_db
def test_list_panel_health_returns_null_payload_without_telemetry(store, db, pano_id):
    db.execute("INSERT INTO panels (pano_id, name) VALUES (%s, 'Test TM-02')", (pano_id,))

    [record] = [r for r in store.list_panel_health() if r.pano_id == pano_id]

    assert (record.payload, record.last_rx) == (None, None)


@needs_db
def test_list_panels_includes_registered_panel_without_telemetry(store, db, pano_id):
    db.execute("INSERT INTO panels (pano_id, name, lat, lon) VALUES (%s, 'Test TM-01', 38.1, 27.1)", (pano_id,))

    [record] = store.list_panels([pano_id])

    assert (record.name, record.lat, record.lon) == ("Test TM-01", 38.1, 27.1)
    assert (record.payload, record.last_rx) == (None, None)
    assert pano_id in {r.pano_id for r in store.list_panels()}


@needs_db
def test_quarantine_keeps_topic_reason_and_raw(contracts, store, db, pano_id):
    topic = f"gridup/pano/{pano_id}/tel"
    pipeline = IngestPipeline(contracts, store, clock=lambda: RX)
    pipeline.handle_message(topic, b"{bozuk")
    assert pipeline.flush()

    received, reason, raw = db.execute(
        "SELECT received, reason, raw FROM quarantine WHERE topic = %s", (topic,)
    ).fetchone()
    assert received == RX
    assert "JSON" in reason
    assert raw == {"raw_text": "{bozuk"}


@needs_db
def test_unknown_panel_is_none(store):
    assert store.get_panel("ZZZ-00000") is None


def test_unreachable_database_raises_store_error_instead_of_hanging():
    """DB yokken API 503 donebilsin ve ingest veriyi tekrar denemek uzere tutabilsin."""
    store = PgStore("postgresql://postgres:x@127.0.0.1:1/yok", timeout_s=0.5)
    rejection = Rejection(received_at=RX, topic="gridup/pano/TST-00000/tel", reason="test", raw={})
    try:
        assert store.ping() is False
        with pytest.raises(StoreError):
            store.list_panels()
        with pytest.raises(StoreError):
            store.write_batch([], [rejection])
    finally:
        store.close()
