"""L-1 veri kalitesi testleri — PLAN.md TA2 Adim 5.

Beklenen degerlerin kaynagi:
  - Esikler contracts/alarm-codes.yaml: dq_frozen_samples, dq_max_rate_k_per_min.
  - Bit numaralari contracts/alarm-codes.yaml alarms[].bit (FROZEN=14, JUMP=15,
    BELOW-AMBIENT=16) — backend/app/risk.py:184-192 t_conn[].q alanini bu bitlerle
    okur.
  - "Ortam alti" olu bandi sozlesmede TANIMLI DEGIL; contracts/changes/ altinda
    onerildi. Sozlesmede yoksa turetilmis varsayilan kullanilir (3 sigma).

Ornek yuk TA1 uretecinden gelir; bozukluk testte bilerek enjekte edilir.
"""

from __future__ import annotations

import copy

import pytest

from panoalgo.quality import QualityTracker, check, point_quality, q_bits


def _point(sample: dict, pt: str) -> dict:
    return next(p for p in sample["t_conn"] if p["pt"] == pt)


def _advance(sample: dict, seconds: float) -> dict:
    from datetime import datetime, timedelta

    nxt = copy.deepcopy(sample)
    ts = datetime.fromisoformat(sample["ts"]) + timedelta(seconds=seconds)
    nxt["ts"] = ts.isoformat(timespec="seconds")
    nxt["seq"] = sample["seq"] + 1
    return nxt


# ------------------------------------------------------------- saglikli taban


def test_healthy_sample_has_no_quality_alarm(sample):
    assert check(sample, None) == []


def test_first_sample_alone_cannot_be_judged_for_rate(sample):
    """Onceki ornek yoksa degisim hizi hesaplanamaz; uydurmak yerine sessiz kal."""
    assert "ALM-DQ-JUMP" not in check(sample, None)


def test_returned_codes_are_all_data_quality_codes(sample, alarm_codes):
    dq = {a["code"] for a in alarm_codes["alarms"] if a["code"].startswith("ALM-DQ-")}
    nxt = _advance(sample, 60.0)
    _point(nxt, "GIRIS_L1")["t_c"] = _point(sample, "GIRIS_L1")["t_c"] + 500.0
    _point(nxt, "DSYA1_L1")["t_c"] = nxt["env"]["t_low_c"] - 50.0

    assert set(check(nxt, sample)) <= dq | {"ALM-NODE-LOST"}


# ------------------------------------------------- fiziksel olmayan degisim hizi


def test_jump_alarm_fires_above_the_contract_rate(sample, thresholds):
    """Excel'deki 15 dk'da 438 A siciramalari bu katmanda isaretlenir."""
    nxt = _advance(sample, 60.0)
    _point(nxt, "GIRIS_L1")["t_c"] = _point(sample, "GIRIS_L1")["t_c"] + thresholds["dq_max_rate_k_per_min"] + 1.0

    assert "ALM-DQ-JUMP" in check(nxt, sample)


def test_jump_alarm_silent_for_a_physically_plausible_change(sample, thresholds):
    nxt = _advance(sample, 60.0)
    _point(nxt, "GIRIS_L1")["t_c"] = _point(sample, "GIRIS_L1")["t_c"] + thresholds["dq_max_rate_k_per_min"] - 1.0

    assert "ALM-DQ-JUMP" not in check(nxt, sample)


def test_jump_alarm_is_rate_based_not_difference_based(sample, thresholds):
    """Ayni fark 10 kat uzun surede olursa fiziksel olarak makuldur."""
    jump = thresholds["dq_max_rate_k_per_min"] * 5.0
    nxt = _advance(sample, 600.0)  # 10 dakika
    _point(nxt, "GIRIS_L1")["t_c"] = _point(sample, "GIRIS_L1")["t_c"] + jump

    assert "ALM-DQ-JUMP" not in check(nxt, sample)


def test_jump_alarm_also_catches_a_sudden_drop(sample, thresholds):
    """Sensor kopmasi da ani DUSUS uretir; mutlak deger alinmali."""
    nxt = _advance(sample, 60.0)
    _point(nxt, "GIRIS_L1")["t_c"] = _point(sample, "GIRIS_L1")["t_c"] - thresholds["dq_max_rate_k_per_min"] - 1.0

    assert "ALM-DQ-JUMP" in check(nxt, sample)


def test_backfill_sample_does_not_produce_a_false_jump(sample, thresholds):
    """Gecmise donuk (backfill) ornek ts'i GERI goturur; negatif sure ile
    bolunurse sahte sicrama cikar (backend/app/alarm_manager.py:199 backfill notu)."""
    older = _advance(sample, -600.0)
    _point(older, "GIRIS_L1")["t_c"] = _point(sample, "GIRIS_L1")["t_c"] + 100.0

    assert "ALM-DQ-JUMP" not in check(older, sample)


def test_two_samples_with_the_same_timestamp_do_not_divide_by_zero(sample):
    twin = copy.deepcopy(sample)
    _point(twin, "GIRIS_L1")["t_c"] += 100.0
    assert isinstance(check(twin, sample), list)


# ------------------------------------------------------------- ortam alti


def test_below_ambient_alarm_when_a_terminal_reads_colder_than_the_panel_air(sample):
    """Sensor yerinden dusmusse ortamin altini olcer (alarm-codes.yaml bit 16)."""
    _point(sample, "DSYA2_L2")["t_c"] = sample["env"]["t_low_c"] - 10.0
    assert "ALM-DQ-BELOW-AMBIENT" in check(sample, None)


def test_below_ambient_has_a_deadband_wider_than_sensor_noise(sample):
    """Hafif yuklu nokta fiziksel olarak ortamda oturur; sigma 0,2 K gurultu ile
    dt_c ara ara negatife duser. Olu bant olmasaydi saglikli pano SYS alarmi uretirdi
    (TA1 bulgusu, generator.py modul notu)."""
    _point(sample, "GIRIS_N")["t_c"] = sample["env"]["t_low_c"] - 0.3
    assert "ALM-DQ-BELOW-AMBIENT" not in check(sample, None)


# --------------------------------------------------------------- donmus sensor


def test_frozen_alarm_needs_the_contract_number_of_identical_samples(sample, thresholds):
    tracker = QualityTracker()
    current = sample
    frozen_value = _point(sample, "DSYA3_L1")["t_c"]

    for _ in range(thresholds["dq_frozen_samples"] - 1):
        _point(current, "DSYA3_L1")["t_c"] = frozen_value
        codes = tracker.check(current)
        current = _advance(current, 10.0)

    assert "ALM-DQ-FROZEN" not in codes.get("DSYA3_L1", [])


def test_frozen_alarm_fires_once_the_window_is_full(sample, thresholds):
    tracker = QualityTracker()
    current = sample
    frozen_value = _point(sample, "DSYA3_L1")["t_c"]

    for _ in range(thresholds["dq_frozen_samples"] + 2):
        _point(current, "DSYA3_L1")["t_c"] = frozen_value
        codes = tracker.check(current)
        current = _advance(current, 10.0)

    assert "ALM-DQ-FROZEN" in codes["DSYA3_L1"]


def test_a_moving_sensor_is_never_reported_as_frozen(sample, thresholds):
    tracker = QualityTracker()
    current = sample

    for step in range(thresholds["dq_frozen_samples"] + 5):
        _point(current, "DSYA3_L1")["t_c"] = 40.0 + step * 0.01
        codes = tracker.check(current)
        current = _advance(current, 10.0)

    assert "ALM-DQ-FROZEN" not in codes["DSYA3_L1"]


def test_frozen_state_is_kept_per_panel(sample, thresholds):
    """Tek dedektor ornegi TUM panolar icin paylasilir (backend/app/risk.py:63);
    durum pano_id ile anahtarlanmazsa panolar birbirinin gecmisini bozar."""
    tracker = QualityTracker()
    other = copy.deepcopy(sample)
    other["pano_id"] = "ADM-00002"
    frozen_value = _point(sample, "DSYA3_L1")["t_c"]

    current, current_other = sample, other
    for _ in range(thresholds["dq_frozen_samples"] + 2):
        _point(current, "DSYA3_L1")["t_c"] = frozen_value
        tracker.check(current)
        tracker.check(current_other)  # bu panonun degeri hareketli
        current = _advance(current, 10.0)
        current_other = _advance(current_other, 10.0)
        _point(current_other, "DSYA3_L1")["t_c"] += 0.05

    assert "ALM-DQ-FROZEN" in tracker.check(current)["DSYA3_L1"]
    assert "ALM-DQ-FROZEN" not in tracker.check(current_other)["DSYA3_L1"]


# ------------------------------------------------------------- dugum kaybi


def test_node_lost_when_fewer_nodes_answer_than_expected(sample):
    sample["health"]["nodes_ok"] = sample["health"]["nodes_total"] - 1
    assert "ALM-NODE-LOST" in check(sample, None)


def test_no_node_lost_when_every_node_answers(sample):
    assert "ALM-NODE-LOST" not in check(sample, None)


# ------------------------------------------------------------------ q bitleri


def test_q_bits_match_the_contract_bit_numbers(alarm_codes):
    bits = {a["code"]: a["bit"] for a in alarm_codes["alarms"]}
    assert q_bits(["ALM-DQ-FROZEN"]) == 1 << bits["ALM-DQ-FROZEN"]
    assert q_bits(["ALM-DQ-JUMP"]) == 1 << bits["ALM-DQ-JUMP"]


def test_q_bits_combine_with_bitwise_or(alarm_codes):
    bits = {a["code"]: a["bit"] for a in alarm_codes["alarms"]}
    expected = (1 << bits["ALM-DQ-JUMP"]) | (1 << bits["ALM-DQ-BELOW-AMBIENT"])
    assert q_bits(["ALM-DQ-JUMP", "ALM-DQ-BELOW-AMBIENT"]) == expected


def test_clean_point_has_q_zero():
    assert q_bits([]) == 0


def test_point_quality_reports_which_point_is_broken(sample):
    """check() nokta bilgisini kaybeder; kenarin q bitini dogru noktaya yazabilmesi
    icin nokta bazli surum sart."""
    _point(sample, "DSYA6_L3")["t_c"] = sample["env"]["t_low_c"] - 10.0
    per_point = point_quality(sample, None)

    assert "ALM-DQ-BELOW-AMBIENT" in per_point["DSYA6_L3"]
    assert per_point["GIRIS_L1"] == []


# ------------------------------------------------------------- dayaniklilik


def test_check_never_raises_on_a_malformed_payload():
    assert check({"bozuk": True}, None) == []


def test_tracker_never_raises_on_a_malformed_payload():
    assert QualityTracker().check({"bozuk": True}) == {}


def test_check_returns_no_duplicate_codes(sample, thresholds):
    nxt = _advance(sample, 60.0)
    for point in nxt["t_conn"]:
        point["t_c"] = nxt["env"]["t_low_c"] - 50.0
    codes = check(nxt, sample)
    assert len(codes) == len(set(codes))


def test_check_never_returns_the_centre_owned_comms_alarm(sample):
    sample["health"]["nodes_ok"] = 0
    assert "ALM-COMMS-LOST" not in check(sample, None)
