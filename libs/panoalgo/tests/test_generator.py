"""Sentetik veri ureteci testleri — PLAN.md TA1 Adim 6.

Beklenen degerlerin kaynagi:
  - Sema uyumu: contracts/mqtt-telemetry.schema.json (donmus sozlesme).
  - Esikler (70 K, 2312 A, 900 s ...): contracts/alarm-codes.yaml — koda gomulmez
    (PLAN.md kural 10), testler de sozlesmeden okur.
  - Nokta adlari: contracts/modbus-map.yaml conn_temp.points.
  - Isil model ve lag-1 otokorelasyon esigi: HACKATHON_ANALIZ_RAPORU.md 15.1 / 15.2
    ve PLAN.md TA1 Adim 6 (lag-1 > 0.9, verilen Excel'in 0,00'ina karsit).

Karantina kurallari backend/app/ingest.py'den gelir: NaN/Infinity, saat dilimsiz ts,
semada olmayan alan ve 64000 bayt ustu mesaj Kisi B'nin ingest'inde karantinaya
duser — bu yuzden asagida hepsi ayri ayri dogrulanir.
"""

from __future__ import annotations

import json
import math
import statistics
from datetime import datetime, timedelta, timezone

import pytest

from helpers import lag1_autocorr
from panoalgo.generator import MAX_MESSAGE_BYTES, PanelSimulator

START = datetime(2026, 9, 16, 0, 0, tzinfo=timezone.utc)  # Carsamba
SUMMER = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
WINTER = datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc)
STEP_S = 10.0


def make(pano_id: str = "SIM-00001", seed: int = 42, profile: str = "karma", start: datetime = START):
    return PanelSimulator(pano_id=pano_id, seed=seed, profile=profile, start=start)


def run(sim: PanelSimulator, steps: int, dt_s: float = STEP_S) -> list[dict]:
    return [sim.step(dt_s) for _ in range(steps)]


# ------------------------------------------------------------------- sozlesme


def test_first_sample_matches_the_frozen_telemetry_schema(assert_valid_telemetry):
    assert_valid_telemetry(make().step(STEP_S))


def test_every_sample_of_a_long_run_matches_the_schema(assert_valid_telemetry):
    """Tek ornek gecmesi yetmez; gun boyu surerken sinirlarin disina tasmamali."""
    sim = make()
    for sample in run(sim, 600, dt_s=60.0):  # 10 saat
        assert_valid_telemetry(sample)


def test_payload_is_json_serialisable_without_nan_or_infinity():
    """backend/app/ingest.py NaN/Infinity goren mesaji karantinaya atar."""
    for sample in run(make(), 200, dt_s=60.0):
        json.dumps(sample, allow_nan=False)


def test_payload_stays_under_the_ingest_size_limit():
    sample = make().step(STEP_S)
    assert len(json.dumps(sample, allow_nan=False).encode("utf-8")) < MAX_MESSAGE_BYTES


def test_point_names_come_from_the_modbus_contract():
    """Nokta adlari uydurulmaz; conn_temp.points listesinden okunur (kural 10)."""
    import yaml

    from helpers import CONTRACTS_DIR

    modbus = yaml.safe_load((CONTRACTS_DIR / "modbus-map.yaml").read_text(encoding="utf-8"))
    conn_temp = next(b for b in modbus["blocks"] if b["name"] == "conn_temp")

    produced = [p["pt"] for p in make().step(STEP_S)["t_conn"]]
    assert produced == conn_temp["points"]


def test_timestamp_is_timezone_aware_utc_and_advances_by_the_step():
    """Naive ts backend'de karantinaya duser (ingest.py:277)."""
    sim = make()
    first, second = sim.step(STEP_S), sim.step(STEP_S)

    t0 = datetime.fromisoformat(first["ts"])
    t1 = datetime.fromisoformat(second["ts"])
    assert t0.tzinfo is not None
    assert t0.utcoffset() == timedelta(0)
    assert t1 - t0 == timedelta(seconds=STEP_S)


def test_sequence_number_increases_by_one_per_step():
    samples = run(make(), 5)
    assert [s["seq"] for s in samples] == [1, 2, 3, 4, 5]


def test_topic_pano_id_is_echoed_in_the_payload():
    """Topic ile yukteki pano_id ayrisirsa ingest karantinaya atar (ingest.py:267)."""
    assert make(pano_id="GDZ-00123").step(STEP_S)["pano_id"] == "GDZ-00123"


def test_invalid_pano_id_is_rejected_at_construction():
    """Sema deseni ^[A-Z]{3}-[0-9]{5}$ — hata yayin aninda degil, kurulumda cikmali."""
    with pytest.raises(ValueError):
        make(pano_id="SIM-1")


# ------------------------------------------------------------ tekrarlanabilirlik


def test_same_seed_produces_an_identical_series():
    a = run(make(seed=7), 60)
    b = run(make(seed=7), 60)
    assert a == b


def test_different_seeds_produce_different_series():
    a = run(make(seed=7), 60)
    c = run(make(seed=8), 60)
    assert a != c


def test_profile_kind_changes_the_load_shape():
    konut = run(make(profile="konut"), 60)
    ticari = run(make(profile="ticari"), 60)
    assert [s["elec"]["i_ph"][0] for s in konut] != [s["elec"]["i_ph"][0] for s in ticari]


# ---------------------------------------------------------------- istatistik


def test_load_series_is_strongly_autocorrelated():
    """PLAN.md TA1 Adim 6c: lag-1 > 0.9. Verilen Excel'de bu deger 0,00 (rapor 3.4a)."""
    series = [s["elec"]["i_ph"][0] for s in run(make(), 2000)]
    assert lag1_autocorr(series) > 0.9


def test_connection_temperature_series_is_strongly_autocorrelated():
    """Isil atalet (tau 10-30 dk) sicakligi akimdan bile daha duz yapmali."""
    series = [s["t_conn"][0]["t_c"] for s in run(make(), 2000)]
    assert lag1_autocorr(series) > 0.9


# --------------------------------------------------------------- fizik modeli


def test_temperature_rise_reaches_the_steady_state_of_the_thermal_model():
    """Sabit akimda dT -> K*I^2 (rapor 15.1 kararli durum)."""
    sim = make()
    sim.freeze_load(0.8)
    for _ in range(4000):  # 4000 x 10 s = 11 saat >> tau
        sample = sim.step(STEP_S)

    point = sample["t_conn"][0]
    expected = sim.point_k("GIRIS_L1") * sim.point_current("GIRIS_L1") ** 2
    assert point["dt_c"] == pytest.approx(expected, rel=0.15)


def test_temperature_rise_follows_the_discrete_time_constant():
    """Bir tau sonunda adim yanitinin ~%63'u tamamlanmis olmali (1 - 1/e)."""
    sim = make()
    sim.freeze_load(0.8)
    for _ in range(6000):
        sim.step(STEP_S)
    final = sim.point_k("GIRIS_L1") * sim.point_current("GIRIS_L1") ** 2

    cold = make()
    cold.freeze_load(0.8)
    tau_s = cold.point_tau_s("GIRIS_L1")
    for _ in range(int(tau_s / STEP_S)):
        sample = cold.step(STEP_S)

    assert sample["t_conn"][0]["dt_c"] == pytest.approx(0.632 * final, rel=0.25)


def test_time_constant_stays_in_the_range_the_report_gives():
    """Rapor 15.2: tau = 10-30 dk."""
    sim = make()
    for name in sim.point_names:
        assert 600.0 <= sim.point_tau_s(name) <= 1800.0


def test_healthy_panel_never_breaches_the_l0_terminal_alarm(thresholds):
    """Saglikli pano hicbir noktada 70 K artisi gecmemeli; gecerse S0 etiketi yalan olur."""
    worst = 0.0
    for sample in run(make(start=SUMMER), 1500, dt_s=60.0):
        worst = max(worst, max(p["dt_c"] for p in sample["t_conn"]))
    assert worst < thresholds["term_rise_alarm_k"]


def test_healthy_panel_leaves_headroom_for_the_loose_connection_scenario(thresholds):
    """S1'de K uc katina cikar; 70 K'yi asabilmesi icin saglikli tepe >= 70/3 olmali."""
    worst = 0.0
    for sample in run(make(start=SUMMER), 1500, dt_s=60.0):
        worst = max(worst, max(p["dt_c"] for p in sample["t_conn"]))
    assert worst >= thresholds["term_rise_alarm_k"] / 3.0


def test_dew_point_margin_matches_the_magnus_formula():
    from panoalgo.physics import dew_point

    sample = make(start=WINTER).step(STEP_S)
    env = sample["env"]
    assert env["td_low_c"] == pytest.approx(dew_point(env["t_low_c"], env["rh_low_pct"]), abs=0.05)


def test_humidity_moves_opposite_to_temperature():
    """Rapor 15.2: 'Nem sicaklikla ters iliskili gunluk dongu'."""
    samples = run(make(start=SUMMER), 1440, dt_s=60.0)  # 24 saat
    hottest = max(samples, key=lambda s: s["env"]["t_low_c"])
    coldest = min(samples, key=lambda s: s["env"]["t_low_c"])
    assert hottest["env"]["rh_low_pct"] < coldest["env"]["rh_low_pct"]


def test_upper_air_node_is_warmer_than_the_lower_one():
    """Sartname 2.2.8.5: altta hava girisi, ustte cikis — cikis daha sicak olmali."""
    for sample in run(make(), 200, dt_s=60.0):
        assert sample["env"]["t_up_c"] > sample["env"]["t_low_c"]
        assert sample["env"]["dt_air_k"] > 0.0


def test_winter_night_can_drive_the_dew_point_margin_into_condensation():
    """Rapor 15.2 yogusma senaryosunun taban kosulu kis gecelerinde olusmali.

    Sema: "td_margin_k ... negatif = yogusma" — yani marj fiilen SIFIRIN ALTINA inmeli.
    """
    margins = [s["env"]["td_margin_k"] for s in run(make(start=WINTER), 4320, dt_s=60.0)]
    assert min(margins) < 0.0


def test_dew_point_margin_cannot_exceed_the_air_to_dew_point_gap():
    """Marj = YUZEY - ciy noktasi. Yuzey pano ici havadan sicak olamayacagi icin
    marj, hava ile ciy noktasi arasindaki farki asamaz. Isaret hatasini yakalar."""
    for sample in run(make(start=SUMMER), 300, dt_s=60.0):
        env = sample["env"]
        assert env["td_margin_k"] <= env["t_low_c"] - env["td_low_c"] + 0.01


def test_connection_temperature_carries_sensor_noise():
    """Rapor 15.2: olcum gurultusu sigma ~ 0,2 degC.

    Gurultusuz seri juriye sahte bir kesinlik gosterir ve L-1 veri kalitesi
    katmaninin (donmus sensor tespiti) test edilmesini imkansiz kilar.
    """
    sim = make()
    sim.freeze_load(0.5)
    for _ in range(3000):
        sim.step(STEP_S)  # kararli duruma otur

    rises = [sim.step(STEP_S)["t_conn"][0]["dt_c"] for _ in range(200)]
    assert statistics.pstdev(rises) > 0.05


# ------------------------------------------------------------------ elektrik


def test_phase_unbalance_stays_in_the_range_the_report_gives():
    """Rapor 15.2: faz dengesizligi %2-15, yavas degisen."""
    for sample in run(make(), 500, dt_s=60.0):
        assert 2.0 <= sample["elec"]["unbal_pct"] <= 15.0


def test_reported_unbalance_matches_the_formula_on_the_reported_currents():
    """%U = max|Ii - Iort| / Iort * 100 (rapor 15.1) — alan ile akimlar tutarli olmali."""
    sample = make().step(STEP_S)
    i = sample["elec"]["i_ph"]
    mean = sum(i) / 3.0
    expected = max(abs(x - mean) for x in i) / mean * 100.0
    assert sample["elec"]["unbal_pct"] == pytest.approx(expected, abs=0.15)


def test_neutral_current_is_positive_and_smaller_than_the_phase_currents():
    for sample in run(make(), 200, dt_s=60.0):
        elec = sample["elec"]
        assert 0.0 < elec["i_n"] < max(elec["i_ph"])


def test_phase_currents_never_exceed_the_rated_current_of_a_healthy_panel(thresholds):
    """S0 normal senaryosunda asiri yuk YOK; ALM-I-OVER tetiklenmemeli."""
    rated = thresholds["rated_current_a"]["main_input"]
    for sample in run(make(start=SUMMER), 1500, dt_s=60.0):
        assert max(sample["elec"]["i_ph"]) < rated * thresholds["current_alarm_ratio"]


def test_currents_track_the_load_profile_over_a_day():
    """Konut panosunda aksam piki gece cukurundan belirgin yuksek olmali."""
    sim = make(profile="konut", start=START)
    by_hour: dict[int, float] = {}
    for sample in run(sim, 1440, dt_s=60.0):
        hour = datetime.fromisoformat(sample["ts"]).hour
        by_hour[hour] = max(by_hour.get(hour, 0.0), sample["elec"]["i_ph"][0])

    assert by_hour[20] > by_hour[3] * 1.5


# -------------------------------------------------------------- cihaz durumu


def test_tvoc_starts_calm_with_no_trips():
    """PLAN.md TA1 Adim 5: 'TVOC-2 durum makinesi (baslangicta sakin)'."""
    tvoc = make().step(STEP_S)["tvoc"]
    assert tvoc["trips"] == 0
    assert tvoc["state"] == 0
    assert tvoc["prot_health_ok"] is True
    assert tvoc["comm_ok"] is True


def test_medium_voltage_partial_discharge_block_is_null_on_a_low_voltage_panel():
    """Rapor 3.7: 400 V'ta Paschen minimumunun altinda PD beklenmez."""
    assert make().step(STEP_S)["pd"] is None


def test_data_quality_flags_are_clean_on_a_healthy_panel():
    """q != 0 arayuzde 'stale' gosterir ve SYS alarmi uretir; S0'da 0 olmali."""
    for sample in run(make(), 100):
        assert all(point["q"] == 0 for point in sample["t_conn"])


def test_baseline_day_counts_up_to_the_learning_window(thresholds):
    """health.baseline_day 1..7; 7 = taban ogrenme tamamlandi."""
    sim = make()
    first = sim.step(STEP_S)
    assert first["health"]["baseline_day"] == 1

    for _ in range(int(9 * 24 * 3600 / 3600)):
        sample = sim.step(3600.0)
    assert sample["health"]["baseline_day"] == thresholds["baseline_learning_days"]


def test_uptime_and_node_counts_are_integers_and_consistent():
    sample = make().step(STEP_S)
    health = sample["health"]
    assert isinstance(health["uptime_s"], int)
    assert health["nodes_ok"] == health["nodes_total"] == len(sample["t_conn"])


def test_risk_mode_is_a_code_that_exists_in_the_alarm_contract(alarm_codes):
    codes = {h["code"] for h in alarm_codes["hypotheses"]}
    sample = make().step(STEP_S)
    assert sample["risk"]["mode"] in codes


def test_healthy_panel_reports_no_edge_alarms():
    assert make().step(STEP_S)["alarms"] == []


def test_k_ratio_of_a_healthy_panel_is_about_one():
    """K0 = taban; saglikli panoda K/K0 ~ 1, 1.3 uyari esiginin altinda."""
    for point in make().step(STEP_S)["t_conn"]:
        assert point["k_ratio"] == pytest.approx(1.0, abs=0.05)


def test_estimated_time_constant_is_reported_for_every_point():
    for point in make().step(STEP_S)["t_conn"]:
        assert math.isfinite(point["tau_s"])
        assert point["tau_s"] > 0.0


# ------------------------------------------------------------- pano kimlikleri


def test_pano_id_is_zero_padded_to_the_contract_pattern():
    """Sema ^[A-Z]{3}-[0-9]{5}$ — 'ADM-1' degil 'ADM-00001'."""
    from panoalgo.generator import format_pano_id

    assert format_pano_id("ADM", 1) == "ADM-00001"
    assert format_pano_id("GDZ", 123) == "GDZ-00123"


def test_pano_id_prefix_is_upper_cased():
    from panoalgo.generator import format_pano_id

    assert format_pano_id("sim", 999) == "SIM-00999"


@pytest.mark.parametrize("prefix,index", [("TOOLONG", 1), ("AB", 1), ("A1M", 1), ("ADM", 0), ("ADM", 100000)])
def test_pano_id_rejects_values_the_contract_cannot_express(prefix, index):
    from panoalgo.generator import format_pano_id

    with pytest.raises(ValueError):
        format_pano_id(prefix, index)
