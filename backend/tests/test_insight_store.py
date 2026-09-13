"""TB3 — analiz uclarinin PgStore sorgulari gercek TimescaleDB'de: series, get_event, panel_journal,
alarm_counts, delivery_latencies_ms. Ayni davranisin bellek ici cifti tests/fakes.py'dedir.

Yigin ayaktayken calistirma:
    TEST_DB_DSN=postgresql://postgres:gridup@localhost:5432/gridup pytest -m integration

Zamanlar 2099'dadir ve panolar TST-xxxxx: ayni veritabanina yazan canli yiginin verisiyle karismaz
(alarm_counts / delivery_latencies_ms pano suzgeci almaz, `since` ile ayrisir).
"""

from __future__ import annotations

import copy
import os
import random
from datetime import timedelta

import psycopg
import pytest

from app.alarm_manager import AlarmManager, Condition
from app.db import PgStore
from app.ingest import IngestPipeline
from app.models import EventRecord
from app.notify.dispatcher import Delivery
from helpers import encode, utc

DSN = os.getenv("TEST_DB_DSN")
needs_db = pytest.mark.skipif(not DSN, reason="TEST_DB_DSN tanimli degil (gercek veritabani gerekir)")
pytestmark = [pytest.mark.integration, needs_db]

T0 = utc(2099, 1, 5, 10, 0, 0)
RX = T0 + timedelta(seconds=2)


@pytest.fixture
def pano_id() -> str:
    return f"TST-{random.randrange(100_000):05d}"


@pytest.fixture
def db(pano_id):
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute("INSERT INTO panels (pano_id, name) VALUES (%s, %s)", (pano_id, pano_id))
        yield conn
        mine = "SELECT id FROM alarms WHERE pano_id = %s"
        conn.execute(f"DELETE FROM alarm_journal WHERE alarm_id IN ({mine})", (pano_id,))
        conn.execute(f"DELETE FROM notifications WHERE alarm_id IN ({mine})", (pano_id,))
        conn.execute("DELETE FROM alarms WHERE pano_id = %s", (pano_id,))
        conn.execute("DELETE FROM events WHERE pano_id = %s", (pano_id,))
        conn.execute("DELETE FROM telemetry WHERE pano_id = %s", (pano_id,))
        conn.execute("DELETE FROM panel_latest WHERE pano_id = %s", (pano_id,))
        conn.execute("DELETE FROM panels WHERE pano_id = %s", (pano_id,))


@pytest.fixture
def store(db):
    pg = PgStore(DSN)
    yield pg
    pg.close()


@pytest.fixture
def manager(contracts) -> AlarmManager:
    return AlarmManager(contracts, first_id=10**12 + random.randrange(10**9))


def ingest(contracts, store, tel_payload, pano_id, ts, seq, dt_l2):
    payload = copy.deepcopy(tel_payload)
    payload.update(pano_id=pano_id, ts=ts.isoformat(), seq=seq)
    payload["t_conn"][1]["dt_c"] = dt_l2  # GIRIS_L2
    pipeline = IngestPipeline(contracts, store, clock=lambda: ts + timedelta(seconds=2))
    pipeline.handle_message(f"gridup/pano/{pano_id}/tel", encode(payload))
    assert pipeline.flush()


def observe(manager, store, pano_id, minutes: float, *codes: str):
    conditions = [Condition(code, "GIRIS_L2" if code.startswith("ALM-K") else None) for code in codes]
    now = RX + timedelta(minutes=minutes)
    changes = manager.observe(pano_id, T0 + timedelta(minutes=minutes), conditions, now=now)
    store.save_alarm_changes(changes, at=now)
    return {change.alarm.code: change.alarm for change in changes}


def test_series_averages_clean_rows_per_epoch_aligned_bucket(contracts, store, tel_payload, pano_id):
    for ts, seq, dt in ((T0, 1, 50.0), (T0 + timedelta(seconds=30), 2, 52.0), (T0 + timedelta(minutes=2, seconds=10), 3, 60.0)):
        ingest(contracts, store, tel_payload, pano_id, ts, seq, dt)

    result = store.series(pano_id, ["t_conn.GIRIS_L2.dt_c", "t_conn.GIRIS_N.dt_c", "elec.i_n"], T0, T0 + timedelta(minutes=4), timedelta(minutes=1))

    assert result == {
        "t_conn.GIRIS_L2.dt_c": {T0: 51.0, T0 + timedelta(minutes=2): 60.0},
        "elec.i_n": {T0: 48.0, T0 + timedelta(minutes=2): 48.0},
    }  # GIRIS_N q = 4: temiz satiri yok


def test_series_respects_window_and_quarter_hour_alignment(contracts, store, tel_payload, pano_id):
    ingest(contracts, store, tel_payload, pano_id, T0 + timedelta(minutes=7), 1, 40.0)
    ingest(contracts, store, tel_payload, pano_id, T0 + timedelta(minutes=16), 2, 44.0)

    quarter = store.series(pano_id, ["t_conn.GIRIS_L2.dt_c"], T0, T0 + timedelta(minutes=30), timedelta(minutes=15))
    early = store.series(pano_id, ["t_conn.GIRIS_L2.dt_c"], T0, T0 + timedelta(minutes=10), timedelta(minutes=15))

    assert quarter == {"t_conn.GIRIS_L2.dt_c": {T0: 40.0, T0 + timedelta(minutes=15): 44.0}}
    assert early == {"t_conn.GIRIS_L2.dt_c": {T0: 40.0}}  # 10:16 ornegi pencere disi


def test_event_record_and_panel_journal(manager, store, pano_id):
    alarm = observe(manager, store, pano_id, 0, "ALM-K-WARN")["ALM-K-WARN"]
    ack_at = RX + timedelta(minutes=1)
    store.save_alarm_changes([manager.ack(alarm.id, by="operator", now=ack_at, note="tork kontrolu planlandi")], at=ack_at)

    assert store.get_event(alarm.event_id) == EventRecord(
        event_id=alarm.event_id, pano_id=pano_id, occurred_at=T0, code="ALM-K-WARN", det_label=None, point="GIRIS_L2", prio="P3"
    )
    assert store.get_event("EVT-yok") is None

    journal = store.panel_journal(pano_id, T0, T0 + timedelta(hours=1))
    assert [(e.at, e.action, e.state, e.by_user, e.note, e.code, e.prio, e.point) for e in journal] == [
        (RX, "raised", "active", None, None, "ALM-K-WARN", "P3", "GIRIS_L2"),
        (ack_at, "acked", "acked", "operator", "tork kontrolu planlandi", "ALM-K-WARN", "P3", "GIRIS_L2"),
    ]
    assert store.panel_journal(pano_id, T0 + timedelta(minutes=2), T0 + timedelta(hours=1)) == []


def test_alarm_counts_and_first_phone_delivery_latency(manager, store, pano_id):
    k_warn = observe(manager, store, pano_id, 0, "ALM-K-WARN")["ALM-K-WARN"]
    arc = observe(manager, store, pano_id, 1, "ALM-K-WARN", "ALM-ARC-TRIP")["ALM-ARC-TRIP"]
    for delivery in (
        Delivery(k_warn.id, "sms", "+90*****0001", T0 + timedelta(seconds=1.5), True, "ok"),
        Delivery(k_warn.id, "whatsapp", "+90*****0001", T0 + timedelta(seconds=4), True, "ok"),
        Delivery(arc.id, "sms", "+90*****0002", T0 + timedelta(minutes=1, seconds=2), False, "modem yok"),
        Delivery(arc.id, "call", "+90*****0002", T0 + timedelta(minutes=1, seconds=2.5), True, "ok"),
        Delivery(arc.id, "sms", "+90*****0002", T0 + timedelta(minutes=1, seconds=3), True, "ok"),
    ):
        store.record_notification(delivery)

    assert store.alarm_counts(T0) == {"P3": 1, "P1": 1}
    assert store.alarm_counts(T0 + timedelta(seconds=30)) == {"P1": 1}
    assert sorted(store.delivery_latencies_ms(T0)) == [1500.0, 3000.0]
    assert store.delivery_latencies_ms(T0 + timedelta(minutes=5)) == []
