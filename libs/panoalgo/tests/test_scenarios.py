"""Etiketli senaryo ureteci testleri — PLAN.md TA2 Adim 7.

Beklenen degerlerin kaynagi:
  - Senaryo kimlikleri ve etiket bicimi: contracts/scenario-labels.schema.json
    (DONMUS; kok nesnede 6 zorunlu alan, labels[] ogesinde 5).
  - Enjeksiyon modelleri ve beklenen tespitler: HACKATHON_ANALIZ_RAPORU.md 15.2
    "Etiketli ariza enjeksiyonlari" tablosu.
  - Kabul kriteri (PLAN.md TA2): S1'de K/K0 1.6 esigini L0 ihlalinden EN AZ 48 SAAT
    once geciyor. Bu sayi docs/12'nin ana kanitidir.

Testler senaryolari GERCEKTEN kosturur (uretec + kenar boru hatti); beklenen
sonuclar etiket dosyasindan degil, algoritmanin ciktisindan olculur.
"""

from __future__ import annotations

import json

import pytest

from panoalgo.scenarios import SCENARIOS, build, list_scenarios

SHORT_H = 48.0


@pytest.fixture(scope="module")
def s1():
    frame, labels = build("S1_loose_conn", seed=1304, duration_h=720.0)
    return frame, labels


def _schema_scenario_ids() -> set[str]:
    from helpers import CONTRACTS_DIR

    schema = json.loads((CONTRACTS_DIR / "scenario-labels.schema.json").read_text(encoding="utf-8"))
    return set(schema["properties"]["scenario_id"]["enum"])


def _contract_points() -> set[str]:
    import yaml

    from helpers import CONTRACTS_DIR

    data = yaml.safe_load((CONTRACTS_DIR / "modbus-map.yaml").read_text(encoding="utf-8"))
    return set(next(b for b in data["blocks"] if b["name"] == "conn_temp")["points"])


# ------------------------------------------------------------------- katalog


def test_catalogue_matches_the_scenario_ids_the_contract_allows():
    assert set(SCENARIOS) == _schema_scenario_ids()


def test_catalogue_has_ten_scenarios():
    """PLAN.md TA2 kabul: --list 10 senaryo listeliyor."""
    assert len(list_scenarios()) == 10


def test_every_catalogue_entry_has_a_human_readable_description():
    for entry in list_scenarios():
        assert entry["text"].strip()


def test_unknown_scenario_is_rejected():
    with pytest.raises(ValueError):
        build("S99_yok", seed=1, duration_h=1.0)


# ------------------------------------------------------------- etiket semasi


@pytest.mark.parametrize(
    "scenario_id", ["S0_normal", "S1_loose_conn", "S2_overload", "S8_sensor_fault"]
)
def test_labels_match_the_frozen_label_schema(scenario_id, assert_valid_labels):
    _, labels = build(scenario_id, seed=7, duration_h=SHORT_H)
    assert_valid_labels(labels)


def test_normal_scenario_has_an_empty_label_list():
    """Sema aciklamasi: 'bos dizi = tamamen normal senaryo (S0); yanlis alarm
    olcumu bununla yapilir'."""
    _, labels = build("S0_normal", seed=7, duration_h=SHORT_H)
    assert labels["labels"] == []


def test_label_windows_are_ordered_in_time():
    _, labels = build("S1_loose_conn", seed=7, duration_h=240.0)
    for label in labels["labels"]:
        assert label["t_start"] < label["t_end"]


def test_expected_codes_exist_in_the_alarm_contract(alarm_codes):
    """Sema yalnizca ^ALM-...$ desenini dogrular, UYELIGI dogrulamaz."""
    known = {a["code"] for a in alarm_codes["alarms"]}
    for scenario_id in SCENARIOS:
        _, labels = build(scenario_id, seed=3, duration_h=SHORT_H)
        for label in labels["labels"]:
            assert set(label["expect"]) <= known
            assert set(label.get("not_expect", [])) <= known


def test_affected_points_are_real_contract_points():
    allowed = {"PANEL", "SYSTEM"} | _contract_points()
    for scenario_id in SCENARIOS:
        _, labels = build(scenario_id, seed=3, duration_h=SHORT_H)
        for label in labels["labels"]:
            assert label["point"] in allowed


# --------------------------------------------------------- tekrarlanabilirlik


def test_same_seed_produces_identical_data():
    a, _ = build("S2_overload", seed=11, duration_h=24.0)
    b, _ = build("S2_overload", seed=11, duration_h=24.0)
    assert a.equals(b)


def test_different_seeds_produce_different_data():
    a, _ = build("S2_overload", seed=11, duration_h=24.0)
    c, _ = build("S2_overload", seed=12, duration_h=24.0)
    assert not a.equals(c)


def test_seed_is_recorded_in_the_labels():
    _, labels = build("S0_normal", seed=4242, duration_h=24.0)
    assert labels["seed"] == 4242


# ----------------------------------------------------------- S1 kabul kriteri


def test_s1_marks_the_moment_the_fixed_threshold_is_breached(s1):
    """l0_breach_at = 70 K'nin asildigi an; sabit esik ancak BURADA uyarir."""
    _, labels = s1
    assert labels["labels"][0]["l0_breach_at"] is not None


def test_s1_gives_at_least_two_days_of_early_warning(s1, thresholds):
    """PLAN.md TA2 KABUL KRITERI ve docs/12'nin ana kaniti:
    K/K0 esigi, sabit 70 K esiginden EN AZ 48 SAAT once asilmali."""
    frame, labels = s1
    lead_h = _lead_time_h(frame, labels, thresholds)
    assert lead_h >= 48.0, f"one alma suresi yetersiz: {lead_h:.1f} saat"


def test_s1_eventually_raises_the_loose_connection_hypothesis(s1):
    frame, _ = s1
    assert "HYP-LOOSE-CONN" in set(frame["risk_mode"])


def test_s1_index_ratio_crosses_the_alarm_threshold(s1, thresholds):
    frame, _ = s1
    assert frame["max_k_ratio"].max() > thresholds["k_ratio_alarm"]


def _lead_time_h(frame, labels, thresholds) -> float:
    """K/K0 alarmi ile 70 K ihlali arasindaki saat farki."""
    import pandas as pd

    breach = pd.Timestamp(labels["labels"][0]["l0_breach_at"])
    detected = frame.loc[frame["max_k_ratio"] > thresholds["k_ratio_alarm"], "ts"]
    assert not detected.empty, "K/K0 esigi hic asilmadi"
    return (breach - pd.Timestamp(detected.iloc[0])).total_seconds() / 3600.0


# ------------------------------------------------ diger senaryo davranislari


def test_overload_does_not_look_like_a_connection_fault(thresholds):
    """Rapor 15.2: asiri yukte 'K sabit' — bu ariza DEGIL. K/K0 esigi asilmamali."""
    frame, _ = build("S2_overload", seed=5, duration_h=120.0)
    assert frame["max_k_ratio"].max() < thresholds["k_ratio_alarm"]


def test_overload_is_visible_as_overcurrent():
    frame, _ = build("S2_overload", seed=5, duration_h=120.0)
    assert any("ALM-I-OVER" in row for row in frame["alarms"])


def test_condensation_scenario_drives_the_dew_margin_down(thresholds):
    frame, _ = build("S3_condense", seed=5, duration_h=72.0)
    assert frame["td_margin_k"].min() < thresholds["dew_margin_alarm_k"]


def test_arc_scenario_raises_the_trip_alarm():
    frame, _ = build("S4_arc", seed=5, duration_h=SHORT_H)
    assert any("ALM-ARC-TRIP" in row for row in frame["alarms"])


def test_protection_health_scenario_reports_an_unprotected_panel():
    frame, _ = build("S5_prot_health", seed=5, duration_h=SHORT_H)
    assert any("ALM-PROT-HEALTH" in row for row in frame["alarms"])


def test_comms_loss_scenario_leaves_a_gap_in_the_data():
    """Rapor 15.2: 'Saatler suren bosluk'. Veri YOK, sahte deger uretilmez."""
    import pandas as pd

    frame, _ = build("S6_comms_loss", seed=5, duration_h=72.0)
    gaps = pd.Series(pd.to_datetime(frame["ts"])).diff().dt.total_seconds().dropna()
    assert gaps.max() > 3600.0


def test_harmonic_scenario_raises_neutral_current_and_distortion():
    normal, _ = build("S0_normal", seed=5, duration_h=72.0)
    harmonic, _ = build("S7_harmonic", seed=5, duration_h=72.0)
    assert harmonic["i_n"].mean() > normal["i_n"].mean()
    assert harmonic["thd_i_mean"].mean() > normal["thd_i_mean"].mean()


def test_sensor_fault_scenario_is_flagged_as_data_quality_not_a_panel_fault():
    """L-1'in varlik sebebi: bozuk sensor pano arizasi gibi gorunmemeli."""
    frame, _ = build("S8_sensor_fault", seed=5, duration_h=72.0)
    assert frame["q_any"].max() > 0
    assert not any("ALM-THR-TERM-ALM" in row for row in frame["alarms"])


def test_partial_discharge_scenario_is_medium_voltage_only():
    """Rapor 3.7: 400 V AG panoda PD beklenmez (Paschen minimumu ~327 V).
    Senaryo OG panosu uzerinde kurulur ve pd blogu dolu gelir."""
    frame, labels = build("S9_pd_trend", seed=5, duration_h=72.0)
    assert labels["pano_type"].startswith("OG")
    assert frame["pd_pps"].max() > 0.0


# ------------------------------------------------------------------- cikti


def test_fixture_stays_under_the_size_budget(tmp_path):
    """PLAN.md kural 4: fixture'lar <= 1 MB, seed'li."""
    from panoalgo.scenarios import write_fixture

    csv_path, labels_path = write_fixture(
        "S1_loose_conn", seed=1304, duration_h=720.0, out_dir=tmp_path
    )
    assert csv_path.stat().st_size <= 1_000_000
    assert labels_path.stat().st_size <= 1_000_000


def test_written_labels_reference_the_written_data_file(tmp_path):
    from panoalgo.scenarios import write_fixture

    csv_path, labels_path = write_fixture("S0_normal", seed=7, duration_h=24.0, out_dir=tmp_path)
    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    assert labels["data_file"] == csv_path.name
