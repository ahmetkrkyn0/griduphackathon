"""TB2 — alarm kaliciligi: PgStore'un gercek PostgreSQL/TimescaleDB'ye karsi davranisi.

Yigin ayaktayken calistirma:
    TEST_DB_DSN=postgresql://postgres:gridup@localhost:5432/gridup pytest -m integration

Tablolar deploy/initdb/*.sql (003_alarms.sql dahil) ile olusmus olmalidir. Testler yalnizca kendi
TST-xxxxx panolarini ve cok yuksek alarm kimliklerini kullanir: ayni veritabanina yazan canli
backend'in alarmlariyla cakismaz, demo verisine dokunmaz.
"""

from __future__ import annotations

import os
import random
from datetime import timedelta

import psycopg
import pytest

from app.alarm_manager import AlarmManager, Condition
from app.db import PgStore
from app.notify.dispatcher import Delivery
from helpers import utc

DSN = os.getenv("TEST_DB_DSN")
needs_db = pytest.mark.skipif(not DSN, reason="TEST_DB_DSN tanimli degil (gercek veritabani gerekir)")
pytestmark = [pytest.mark.integration, needs_db]

T0 = utc(2026, 9, 13, 10, 0, 0)
RX = T0 + timedelta(seconds=2)

REASON = {
    "signals": [{"tag": "t_conn.GIRIS_L2.k_ratio", "value": 1.45, "threshold": 1.3, "unit": "K/K0"}],
    "layer": "L1",
    "point": "GIRIS_L2",
    "basis": "Rapor 6.5 L1-1",
}


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
        conn.execute("DELETE FROM panels WHERE pano_id = %s", (pano_id,))


@pytest.fixture
def store(db):
    pg = PgStore(DSN)
    yield pg
    pg.close()


@pytest.fixture
def manager(contracts) -> AlarmManager:
    return AlarmManager(contracts, first_id=10**12 + random.randrange(10**9))


def raise_k_warn(manager, store, pano_id, minutes: float = 0):
    ts = T0 + timedelta(minutes=minutes)
    condition = Condition("ALM-K-WARN", "GIRIS_L2", reason=REASON, advice="tork kontrolu", ttl_h=150.5)
    changes = manager.observe(pano_id, ts, [condition], now=RX + timedelta(minutes=minutes))
    store.save_alarm_changes(changes, at=RX + timedelta(minutes=minutes))
    [change] = changes
    return change.alarm


def test_raised_alarm_is_stored_with_its_event_and_journal_entry(manager, store, db, pano_id):
    alarm = raise_k_warn(manager, store, pano_id)

    row = db.execute(
        "SELECT event_id, pano_id, code, prio, state, point, raised_at, last_true_at, annunciated_at,"
        " reason, advice, ttl_h, notified, escalation_level FROM alarms WHERE id = %s",
        (alarm.id,),
    ).fetchone()
    assert row == (
        alarm.event_id, pano_id, "ALM-K-WARN", "P3", "active", "GIRIS_L2", T0, T0, RX,
        REASON, "tork kontrolu", 150.5, [], 0,
    )
    event = db.execute("SELECT pano_id, occurred_at, code FROM events WHERE event_id = %s", (alarm.event_id,)).fetchone()
    assert event == (pano_id, T0, "ALM-K-WARN")
    journal = db.execute("SELECT at, action, state, by_user, note FROM alarm_journal WHERE alarm_id = %s", (alarm.id,)).fetchall()
    assert journal == [(RX, "raised", "active", None, None)]


def test_operator_actions_update_the_row_and_append_to_the_journal(manager, store, db, pano_id):
    alarm = raise_k_warn(manager, store, pano_id)
    acked_at, shelved_at = RX + timedelta(minutes=3), RX + timedelta(minutes=4)

    store.save_alarm_changes([manager.ack(alarm.id, by="vardiya.amiri", now=acked_at, note="ekip yolda")], at=acked_at)
    store.save_alarm_changes(
        [manager.shelve(alarm.id, by="vardiya.amiri", minutes=60, reason="bakim ekibi sahada", now=shelved_at)],
        at=shelved_at,
    )

    row = db.execute(
        "SELECT state, acked_at, acked_by, shelved_until, shelve_reason FROM alarms WHERE id = %s", (alarm.id,)
    ).fetchone()
    assert row == ("shelved", acked_at, "vardiya.amiri", shelved_at + timedelta(minutes=60), "bakim ekibi sahada")
    journal = db.execute(
        "SELECT action, state, by_user, note FROM alarm_journal WHERE alarm_id = %s ORDER BY id", (alarm.id,)
    ).fetchall()
    assert journal == [
        ("raised", "active", None, None),
        ("acked", "acked", "vardiya.amiri", "ekip yolda"),
        ("shelved", "shelved", "vardiya.amiri", "bakim ekibi sahada"),
    ]


def test_open_alarms_are_restored_exactly_and_cleared_ones_are_not(contracts, manager, store, pano_id):
    kept = raise_k_warn(manager, store, pano_id)
    [dew] = manager.observe(pano_id, T0 + timedelta(minutes=1), [Condition("ALM-K-WARN", "GIRIS_L2"), Condition("ALM-DEW-WARN")], now=RX)
    store.save_alarm_changes([dew], at=RX)
    hyst = contracts.thresholds["hysteresis_clear_min"]
    later = T0 + timedelta(minutes=1 + hyst)
    store.save_alarm_changes(manager.observe(pano_id, later, [Condition("ALM-K-WARN", "GIRIS_L2")], now=later), at=later)

    restored = [a for a in store.load_open_alarms() if a.pano_id == pano_id]

    # Depo son KAYDEDILEN hali dondurur. Bellekteki last_true_at kosul surdukce ilerler ama
    # yazilmaz; yeniden baslatmada histerezis ilk ornekle baslar (test_alarm_manager).
    assert restored == [kept]
    assert store.get_alarm(dew.alarm.id).state == "cleared"


def test_list_alarms_filters_by_state_priority_and_panel_newest_first(manager, store, pano_id):
    k_warn = raise_k_warn(manager, store, pano_id, minutes=0)
    changes = manager.observe(
        pano_id,
        T0 + timedelta(minutes=2),
        [Condition("ALM-K-WARN", "GIRIS_L2"), Condition("ALM-THR-TERM-ALM", "GIRIS_L2"), Condition("ALM-DEW-ALM")],
        now=RX + timedelta(minutes=2),
    )
    store.save_alarm_changes(changes, at=RX + timedelta(minutes=2))
    term, dew = (c.alarm for c in sorted(changes, key=lambda c: c.alarm.code, reverse=True))
    store.save_alarm_changes([manager.ack(dew.id, by="op", now=RX + timedelta(minutes=3))], at=RX + timedelta(minutes=3))

    p2_active = store.list_alarms(states=["active"], prios=["P2"], pano_id=pano_id, limit=10)
    everything = store.list_alarms(states=["active", "acked"], prios=None, pano_id=pano_id, limit=10)
    newest = store.list_alarms(states=["active", "acked"], prios=None, pano_id=pano_id, limit=1)

    assert [a.id for a in p2_active] == [term.id]
    assert {a.id for a in everything} == {k_warn.id, term.id, dew.id}
    assert everything[-1].id == k_warn.id  # en eski en sonda
    assert newest[0].raised_at == T0 + timedelta(minutes=2)


def test_notification_attempts_are_stored_for_the_audit_trail(manager, store, db, pano_id):
    alarm = raise_k_warn(manager, store, pano_id)

    store.record_notification(Delivery(alarm.id, "sms", "+90******0001", RX, False, "+CMS ERROR: 500"))
    store.record_notification(Delivery(alarm.id, "whatsapp", "+90******0001", RX, True, "gonderildi"))

    rows = db.execute(
        "SELECT channel, recipient, sent_at, ok, detail FROM notifications WHERE alarm_id = %s ORDER BY id", (alarm.id,)
    ).fetchall()
    assert rows == [
        ("sms", "+90******0001", RX, False, "+CMS ERROR: 500"),
        ("whatsapp", "+90******0001", RX, True, "gonderildi"),
    ]


def test_next_alarm_id_is_above_every_stored_id(manager, store, pano_id):
    alarm = raise_k_warn(manager, store, pano_id)

    assert store.next_alarm_id() > alarm.id


def test_unknown_alarm_id_is_none(store):
    assert store.get_alarm(-1) is None
