"""TB2 Adim 1 — ISA-18.2 alarm yasam dongusu (app.alarm_manager).

Zaman tabani:
  - Histerezis ve gruplama OLAY zamaniyla (telemetri `ts`) olculur: sure fizikseldir,
    hizlandirilmis senaryo oynatmada da ayni davranir.
  - Raf suresi ve eskalasyon DUVAR saatiyle (`now`) olculur: sure operatorun tepki suresidir.

Esikler (histerezis, gruplama penceresi, raf siniri) ve oncelikler contracts/alarm-codes.yaml'dan
okunur — testler de uretim kodu gibi bu degerleri koda gommez (PLAN.md kural 10).
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.alarm_manager import (
    AlarmManager,
    AlarmNotFound,
    AlarmNotSuppressible,
    AlarmStateConflict,
    Condition,
)
from helpers import utc

T0 = utc(2026, 9, 13, 10, 0, 0)
PANO = "ADM-00001"

K_WARN = "ALM-K-WARN"  # P3, gevsek baglanti kaniti
K_ALM = "ALM-K-ALM"  # P2, gevsek baglanti kaniti
PHASE_DIF = "ALM-THR-PHASE-DIF"  # P2, gevsek baglanti kaniti
TERM_WARN = "ALM-THR-TERM-WARN"  # P3, hicbir hipotezin kaniti degil
TERM_ALM = "ALM-THR-TERM-ALM"  # P2
DEW_WARN = "ALM-DEW-WARN"  # P3, yogusma kaniti
ARC_TRIP = "ALM-ARC-TRIP"  # P1, bastirilamaz
PROT_HEALTH = "ALM-PROT-HEALTH"  # P1, bastirilamaz


def at(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


def cond(code: str, point: str | None = None) -> Condition:
    return Condition(code=code, point=point)


def observe(manager: AlarmManager, minutes: float, *conditions: Condition, pano_id: str = PANO, maint_mode: bool = False):
    """Gercek zamanli akis: olay zamani = duvar saati."""
    return manager.observe(pano_id, at(minutes), list(conditions), now=at(minutes), maint_mode=maint_mode)


@pytest.fixture
def manager(contracts) -> AlarmManager:
    return AlarmManager(contracts)


@pytest.fixture
def hyst(contracts) -> float:
    return contracts.thresholds["hysteresis_clear_min"]


# ------------------------------------------------------------------ olusma
def test_new_condition_raises_active_alarm_with_contract_priority(manager, contracts):
    [change] = observe(manager, 0, cond(K_WARN, "GIRIS_L2"))

    alarm = change.alarm
    assert change.kind == "raised"
    assert (alarm.pano_id, alarm.code, alarm.point, alarm.state) == (PANO, K_WARN, "GIRIS_L2", "active")
    assert alarm.prio == contracts.prio_of(K_WARN)
    assert alarm.raised_at == T0
    assert alarm.event_id
    assert manager.get(alarm.id).state == "active"


def test_persisting_condition_does_not_raise_again(manager):
    [raised] = observe(manager, 0, cond(K_WARN, "GIRIS_L2"))

    assert observe(manager, 1, cond(K_WARN, "GIRIS_L2")) == []
    assert [a.id for a in manager.open_alarms()] == [raised.alarm.id]


def test_same_code_on_two_points_is_two_alarms(manager):
    changes = observe(manager, 0, cond(K_WARN, "GIRIS_L2"), cond(K_WARN, "DSYA3_L2"))

    assert sorted(c.alarm.point for c in changes) == ["DSYA3_L2", "GIRIS_L2"]
    assert len({c.alarm.id for c in changes}) == 2


def test_same_code_on_two_panels_is_two_alarms(manager):
    [first] = observe(manager, 0, cond(TERM_ALM, "GIRIS_L2"))
    [second] = observe(manager, 0, cond(TERM_ALM, "GIRIS_L2"), pano_id="ADM-00002")

    assert first.alarm.id != second.alarm.id
    assert [a.id for a in manager.open_alarms(pano_id="ADM-00002")] == [second.alarm.id]


def test_backfilled_older_sample_does_not_raise_or_clear(manager, hyst):
    """Kopukluk sonrasi 7 gunluk backfill gecmis `ts` ile gelir: canli alarm durumunu degistirmez."""
    [raised] = observe(manager, 30, cond(K_WARN, "GIRIS_L2"))

    assert observe(manager, 0, cond(DEW_WARN)) == []
    assert observe(manager, 30 - 2 * hyst) == []
    assert [a.id for a in manager.open_alarms()] == [raised.alarm.id]


def test_restored_open_alarms_continue_their_lifecycle(contracts, hyst):
    """Backend yeniden baslar: depodan yuklenen acik alarm ayni kimlikle surer, yeni alarm cakismaz."""
    before = AlarmManager(contracts, first_id=40)
    [raised] = observe(before, 0, cond(TERM_ALM, "GIRIS_L2"))

    after = AlarmManager(contracts, first_id=41)
    after.restore([raised.alarm])

    assert observe(after, 1, cond(TERM_ALM, "GIRIS_L2")) == []
    [new] = observe(after, 2, cond(TERM_ALM, "GIRIS_L2"), cond(K_WARN, "DSYA3_L2"))
    assert new.alarm.id == 41
    assert after.ack(40, by="op", now=at(3)).alarm.state == "acked"
    [cleared] = observe(after, 2 + hyst, cond(K_WARN, "DSYA3_L2"))
    assert cleared.alarm.id == 40


def test_restored_alarm_is_not_cleared_before_hysteresis_after_restart(contracts, hyst):
    """Depodaki last_true_at yalnizca durum degisiminde yazilir (eskidir). Kesinti boyunca kosulun
    ne oldugunu bilmiyoruz: yeniden baslatmadan sonraki ilk ornekten itibaren H dk dogrulanmadan
    alarm temizlenmez (aksi halde sinirda salinan kosul yeniden baslatmada yeni alarm + bildirim uretir)."""
    before = AlarmManager(contracts, first_id=40)
    [raised] = observe(before, 0, cond(K_WARN, "GIRIS_L2"))  # depoya yazilan son hal: last_true_at = 0

    after = AlarmManager(contracts, first_id=41)
    after.restore([raised.alarm])

    assert observe(after, 180) == []  # 3 saat sonra ilk ornek, kosul yok
    assert observe(after, 180 + hyst - 1) == []
    [cleared] = observe(after, 180 + hyst)
    assert (cleared.kind, cleared.alarm.id) == ("cleared", 40)


# -------------------------------------------------------------------- onay
def test_ack_records_operator_and_time(manager):
    [raised] = observe(manager, 0, cond(TERM_ALM, "GIRIS_L2"))

    change = manager.ack(raised.alarm.id, by="vardiya.amiri", now=at(2), note="ekip yolda")

    assert change.kind == "acked"
    assert (change.alarm.state, change.alarm.acked_by, change.alarm.acked_at) == ("acked", "vardiya.amiri", at(2))
    assert manager.get(raised.alarm.id).state == "acked"


def test_ack_twice_is_a_conflict(manager):
    [raised] = observe(manager, 0, cond(TERM_ALM, "GIRIS_L2"))
    manager.ack(raised.alarm.id, by="op", now=at(1))

    with pytest.raises(AlarmStateConflict):
        manager.ack(raised.alarm.id, by="op", now=at(2))


def test_ack_of_unknown_alarm_is_not_found(manager):
    with pytest.raises(AlarmNotFound):
        manager.ack(999, by="op", now=at(0))


# --------------------------------------------------------------- histerezis
def test_acked_alarm_clears_only_after_condition_stays_away_for_hysteresis(manager, hyst):
    [raised] = observe(manager, 0, cond(TERM_ALM, "GIRIS_L2"))
    manager.ack(raised.alarm.id, by="op", now=at(1))

    assert observe(manager, hyst - 0.5) == []
    assert manager.get(raised.alarm.id).state == "acked"

    [cleared] = observe(manager, hyst)
    assert (cleared.kind, cleared.alarm.id) == ("cleared", raised.alarm.id)
    assert (cleared.alarm.state, cleared.alarm.cleared_at) == ("cleared", at(hyst))
    assert manager.open_alarms() == []


def test_condition_returning_within_hysteresis_keeps_the_same_alarm(manager, hyst):
    """Esik cevresinde salinan sinyal alarm seli uretmez (chattering)."""
    [raised] = observe(manager, 0, cond(K_ALM, "GIRIS_L2"))

    assert observe(manager, 1) == []
    assert observe(manager, hyst - 1, cond(K_ALM, "GIRIS_L2")) == []
    assert observe(manager, 2 * hyst - 1.5) == []

    [cleared] = observe(manager, 2 * hyst - 1)
    assert (cleared.kind, cleared.alarm.id) == ("cleared", raised.alarm.id)


def test_unacknowledged_suppressible_alarm_clears_without_ack(manager, hyst):
    observe(manager, 0, cond(K_WARN, "GIRIS_L2"))

    [cleared] = observe(manager, hyst)

    assert (cleared.kind, cleared.alarm.state, cleared.alarm.acked_at) == ("cleared", "cleared", None)


def test_p1_that_returns_to_normal_stays_latched_until_acknowledged(manager, hyst):
    """Bastirilamaz alarm operator gormeden kaybolamaz (ISA-18.2 'RTN unack' durumu)."""
    [raised] = observe(manager, 0, cond(ARC_TRIP))

    [returned] = observe(manager, hyst + 10)
    assert returned.kind == "returned"
    assert (returned.alarm.state, returned.alarm.cleared_at) == ("active", at(hyst + 10))
    assert [a.id for a in manager.open_alarms()] == [raised.alarm.id]

    acked = manager.ack(raised.alarm.id, by="op", now=at(hyst + 12))
    assert (acked.kind, acked.alarm.state, acked.alarm.acked_by) == ("acked", "cleared", "op")
    assert manager.open_alarms() == []


def test_latched_p1_reoccurring_before_ack_is_back_in_alarm(manager, hyst):
    [raised] = observe(manager, 0, cond(ARC_TRIP))
    observe(manager, hyst)

    [change] = observe(manager, hyst + 1, cond(ARC_TRIP))

    assert (change.kind, change.alarm.id, change.notify) == ("reactivated", raised.alarm.id, False)
    assert (change.alarm.state, change.alarm.cleared_at) == ("active", None)


# --------------------------------------------------------------------- raf
def test_shelved_alarm_is_reannunciated_when_shelve_expires(manager):
    [raised] = observe(manager, 0, cond(K_ALM, "GIRIS_L2"))
    manager.ack(raised.alarm.id, by="op", now=at(1))

    shelved = manager.shelve(raised.alarm.id, by="op", minutes=30, reason="bakim ekibi sahada", now=at(2))
    assert shelved.kind == "shelved"
    assert (shelved.alarm.state, shelved.alarm.shelved_until, shelved.alarm.shelve_reason) == (
        "shelved",
        at(32),
        "bakim ekibi sahada",
    )

    observe(manager, 20, cond(K_ALM, "GIRIS_L2"))
    assert manager.tick(at(31)) == []

    [unshelved] = manager.tick(at(32))
    assert (unshelved.kind, unshelved.notify) == ("unshelved", True)
    assert (unshelved.alarm.state, unshelved.alarm.acked_at, unshelved.alarm.shelved_until) == ("active", None, None)


@pytest.mark.parametrize("minutes,reason", [(0, "gecerli gerekce"), (None, "gecerli gerekce"), (30, " a ")])
def test_shelve_requires_a_reason_and_bounded_duration(manager, contracts, minutes, reason):
    [raised] = observe(manager, 0, cond(K_ALM, "GIRIS_L2"))
    over_max = contracts.thresholds["shelve_max_min"] + 1

    with pytest.raises(ValueError):
        manager.shelve(raised.alarm.id, by="op", minutes=over_max if minutes is None else minutes, reason=reason, now=at(1))
    assert manager.get(raised.alarm.id).state == "active"


def test_shelve_accepts_the_contract_maximum(manager, contracts):
    [raised] = observe(manager, 0, cond(K_ALM, "GIRIS_L2"))
    max_min = contracts.thresholds["shelve_max_min"]

    shelved = manager.shelve(raised.alarm.id, by="op", minutes=max_min, reason="planli kesinti", now=at(1))

    assert shelved.alarm.shelved_until == at(1 + max_min)


def test_p1_cannot_be_shelved(manager):
    [raised] = observe(manager, 0, cond(ARC_TRIP))

    with pytest.raises(AlarmNotSuppressible):
        manager.shelve(raised.alarm.id, by="op", minutes=30, reason="deneme amacli", now=at(1))
    assert manager.get(raised.alarm.id).state == "active"


def test_shelved_alarm_clears_when_its_condition_goes_away(manager, hyst):
    [raised] = observe(manager, 0, cond(K_ALM, "GIRIS_L2"))
    manager.shelve(raised.alarm.id, by="op", minutes=120, reason="bakim ekibi sahada", now=at(1))

    [cleared] = observe(manager, hyst)

    assert (cleared.kind, cleared.alarm.state, cleared.alarm.shelved_until) == ("cleared", "cleared", None)
    assert manager.tick(at(121)) == []


def test_ack_of_shelved_alarm_ends_shelving(manager):
    [raised] = observe(manager, 0, cond(K_ALM, "GIRIS_L2"))
    manager.shelve(raised.alarm.id, by="op", minutes=60, reason="bakim ekibi sahada", now=at(1))

    change = manager.ack(raised.alarm.id, by="op", now=at(5))

    assert (change.alarm.state, change.alarm.shelved_until) == ("acked", None)
    assert manager.tick(at(61)) == []


# -------------------------------------------------------------- bakim modu
def test_maintenance_mode_suppresses_everything_except_p1(manager):
    changes = observe(manager, 0, cond(TERM_ALM, "GIRIS_L2"), cond(ARC_TRIP), maint_mode=True)

    assert [(c.kind, c.alarm.code) for c in changes] == [("raised", ARC_TRIP)]


def test_suppressed_condition_raises_once_maintenance_ends(manager):
    observe(manager, 0, cond(TERM_ALM, "GIRIS_L2"), maint_mode=True)

    [raised] = observe(manager, 1, cond(TERM_ALM, "GIRIS_L2"), maint_mode=False)

    assert (raised.kind, raised.alarm.raised_at) == ("raised", at(1))


# ---------------------------------------------------------------- gruplama
def test_same_root_cause_within_window_shares_an_event(manager, contracts):
    window = contracts.thresholds["group_window_min"]
    [k_warn] = observe(manager, 0, cond(K_WARN, "GIRIS_L2"))

    [phase] = observe(manager, window, cond(K_WARN, "GIRIS_L2"), cond(PHASE_DIF, "GIRIS_L2"))

    assert phase.alarm.event_id == k_warn.alarm.event_id


def test_different_root_cause_opens_a_new_event(manager):
    [k_warn] = observe(manager, 0, cond(K_WARN, "GIRIS_L2"))

    [dew] = observe(manager, 1, cond(K_WARN, "GIRIS_L2"), cond(DEW_WARN))

    assert dew.alarm.event_id != k_warn.alarm.event_id


def test_same_root_cause_after_window_opens_a_new_event(manager, contracts):
    window = contracts.thresholds["group_window_min"]
    [k_warn] = observe(manager, 0, cond(K_WARN, "GIRIS_L2"))

    [k_alm] = observe(manager, window + 1, cond(K_WARN, "GIRIS_L2"), cond(K_ALM, "GIRIS_L2"))

    assert k_alm.alarm.event_id != k_warn.alarm.event_id


def test_alarms_on_the_same_point_within_window_share_an_event(manager):
    """Hipotezi olmayan L0 limiti (50 K terminal) de ayni fiziksel baglantinin olayina girer."""
    [k_warn] = observe(manager, 0, cond(K_WARN, "DSYA3_L2"))

    changes = observe(manager, 3, cond(K_WARN, "DSYA3_L2"), cond(TERM_WARN, "DSYA3_L2"), cond(TERM_WARN, "GIRIS_L1"))

    events = {c.alarm.point: c.alarm.event_id for c in changes}
    assert events["DSYA3_L2"] == k_warn.alarm.event_id
    assert events["GIRIS_L1"] != k_warn.alarm.event_id


def test_alarms_following_a_p1_on_the_same_panel_join_its_event(manager):
    """Ilk-cikan (first-out): ark tripinden sonra gelen sicaklik alarmlari olayin altina girer."""
    [arc] = observe(manager, 0, cond(ARC_TRIP))

    [term] = observe(manager, 2, cond(ARC_TRIP), cond(TERM_ALM, "DSYA3_L2"))
    [elsewhere] = observe(manager, 2, cond(TERM_ALM, "DSYA3_L2"), pano_id="ADM-00002")

    assert term.alarm.event_id == arc.alarm.event_id
    assert elsewhere.alarm.event_id != arc.alarm.event_id


def test_only_the_first_or_a_more_urgent_alarm_of_an_event_pages_phones(manager):
    """Alarm seli onleme: ayni olayin daha dusuk/esit oncelikli alarmlari telefonu tekrar caldirmaz."""
    [arc] = observe(manager, 0, cond(ARC_TRIP))
    [term] = observe(manager, 1, cond(ARC_TRIP), cond(TERM_ALM, "DSYA3_L2"))
    assert (arc.notify, term.notify) == (True, False)

    [k_warn] = observe(manager, 0, cond(K_WARN, "GIRIS_L2"), pano_id="ADM-00002")
    [k_alm] = observe(manager, 1, cond(K_WARN, "GIRIS_L2"), cond(K_ALM, "GIRIS_L2"), pano_id="ADM-00002")
    assert (k_warn.notify, k_alm.notify) == (True, True)
    assert k_alm.alarm.event_id == k_warn.alarm.event_id


def test_equal_priority_alarm_joining_an_event_does_not_page_again(manager):
    [k_alm] = observe(manager, 0, cond(K_ALM, "GIRIS_L2"))

    [phase] = observe(manager, 2, cond(K_ALM, "GIRIS_L2"), cond(PHASE_DIF, "GIRIS_L2"))

    assert phase.alarm.event_id == k_alm.alarm.event_id
    assert (k_alm.notify, phase.notify) == (True, False)


def test_every_distinct_p1_pages_even_inside_an_existing_event(manager):
    """P1 asla bastirilmaz: koruma sagligi kaybindan 3 dk sonra gelen ark tripi de telefona gider."""
    [health] = observe(manager, 0, cond(PROT_HEALTH))

    [arc] = observe(manager, 3, cond(PROT_HEALTH), cond(ARC_TRIP))

    assert arc.alarm.event_id == health.alarm.event_id
    assert (health.notify, arc.notify) == (True, True)


def test_code_missing_from_contract_is_ignored_and_counted(manager):
    """Kenar yeni bir kod gonderirse (sozlesme surumu kaymasi) canli alarmlar etkilenmez."""
    changes = observe(manager, 0, cond("ALM-YOK-BOYLE"), cond(K_WARN, "GIRIS_L2"))

    assert [c.alarm.code for c in changes] == [K_WARN]
    assert manager.stats["unknown_codes"] == 1
