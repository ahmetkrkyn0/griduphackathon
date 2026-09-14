"""L0 mutlak limit testleri — PLAN.md TA2 Adim 5.

Beklenen degerlerin kaynagi:
  - TUM esikler contracts/alarm-codes.yaml'dan `thresholds` fixture'i ile okunur;
    bu dosyada 50 / 70 / 105 / 15 / 2312 gibi HICBIR sayi elle yazili degildir
    (PLAN.md kural 10).
  - Karsilastirma yonu backend/app/risk.py:58-59 ile ayni olmak ZORUNDA: kesin
    buyuktur (`>`). backend/tests/test_risk.py tam esikteki degerin alarm
    URETMEDIGINI kilitliyor; panoalgo `>=` kullanirsa alarm konsolu kirmizi
    gosterirken dijital ikizde nokta yesil kalir.
  - Faz farki gruplamasi ve notr dislamasi da risk.py:38 `^(GIRIS|DSYA\\d)_L[123]$`
    deseniyle ayni.

Ornek yuk, TA1 uretecinden alinir: boylece testler gercek sema-gecerli bir yuk
uzerinde calisir, elle kurulmus yapay sozluk uzerinde degil.
"""

from __future__ import annotations

import pytest

from panoalgo.limits import evaluate


def _set_point(sample: dict, pt: str, **fields) -> dict:
    for point in sample["t_conn"]:
        if point["pt"] == pt:
            point.update(fields)
            return sample
    raise KeyError(pt)


def _flatten_rises(sample: dict, value: float) -> dict:
    for point in sample["t_conn"]:
        point["dt_c"] = value
    return sample


# --------------------------------------------------------------- saglikli taban


def test_healthy_sample_raises_no_l0_alarm(sample):
    assert evaluate(sample) == []


def test_result_contains_only_codes_defined_in_the_contract(sample, alarm_codes):
    known = {a["code"] for a in alarm_codes["alarms"]}
    _set_point(sample, "GIRIS_L1", dt_c=999.0)
    sample["env"]["td_margin_k"] = -5.0
    sample["elec"]["i_ph"] = [9999.0, 9999.0, 9999.0]

    assert set(evaluate(sample)) <= known


# ------------------------------------------------------------ sicaklik artisi


def test_terminal_warning_fires_just_above_the_threshold(sample, thresholds):
    _set_point(sample, "DSYA3_L2", dt_c=thresholds["term_rise_warn_k"] + 0.1)
    assert "ALM-THR-TERM-WARN" in evaluate(sample)


def test_terminal_warning_does_not_fire_exactly_at_the_threshold(sample, thresholds):
    """risk.py:58 `value > limit` — tam esik alarm DEGILDIR."""
    _flatten_rises(sample, thresholds["term_rise_warn_k"])
    assert "ALM-THR-TERM-WARN" not in evaluate(sample)


def test_terminal_alarm_fires_above_seventy_kelvin(sample, thresholds):
    _set_point(sample, "GIRIS_L2", dt_c=thresholds["term_rise_alarm_k"] + 1.0)
    codes = evaluate(sample)
    assert "ALM-THR-TERM-ALM" in codes
    assert "ALM-THR-TERM-WARN" in codes, "70 K'yi gecen deger 50 K'yi de gecmistir"


def test_busbar_alarm_fires_above_its_own_threshold(sample, thresholds):
    _set_point(sample, "GIRIS_L1", dt_c=thresholds["bus_rise_alarm_k"] + 1.0)
    assert "ALM-THR-BUS-ALM" in evaluate(sample)


def test_busbar_alarm_stays_silent_between_terminal_and_busbar_limits(sample, thresholds):
    _set_point(sample, "GIRIS_L1", dt_c=thresholds["term_rise_alarm_k"] + 1.0)
    assert "ALM-THR-BUS-ALM" not in evaluate(sample)


# --------------------------------------------------------------- faz farki


def test_phase_difference_alarm_uses_the_hottest_and_coldest_phase_of_a_group(sample, thresholds):
    _flatten_rises(sample, 10.0)
    _set_point(sample, "DSYA4_L1", dt_c=10.0 + thresholds["phase_diff_alarm_k"] + 1.0)
    assert "ALM-THR-PHASE-DIF" in evaluate(sample)


def test_phase_difference_ignores_the_neutral_point(sample, thresholds):
    """risk.py:38 notru desen disinda birakir; notr fazlardan soguk olmasi normaldir."""
    _flatten_rises(sample, 10.0 + thresholds["phase_diff_alarm_k"] + 1.0)
    _set_point(sample, "GIRIS_N", dt_c=0.0)
    assert "ALM-THR-PHASE-DIF" not in evaluate(sample)


def test_phase_difference_does_not_compare_across_different_feeders(sample, thresholds):
    """DSYA1 sicak, DSYA5 soguk olabilir — farkli fiderler farkli yuk tasir."""
    _flatten_rises(sample, 5.0)
    for pt in ("DSYA1_L1", "DSYA1_L2", "DSYA1_L3"):
        _set_point(sample, pt, dt_c=5.0 + thresholds["phase_diff_alarm_k"] + 2.0)
    assert "ALM-THR-PHASE-DIF" not in evaluate(sample)


# ------------------------------------------------------------------- akim


def test_overcurrent_uses_the_main_input_rating(sample, thresholds):
    """risk.py:198-203 tek limit kullanir: current_alarm_ratio * rated main_input."""
    limit = thresholds["current_alarm_ratio"] * thresholds["rated_current_a"]["main_input"]
    sample["elec"]["i_ph"] = [limit + 1.0, 10.0, 10.0]
    assert "ALM-I-OVER" in evaluate(sample)


def test_overcurrent_does_not_fire_exactly_at_the_rating(sample, thresholds):
    limit = thresholds["current_alarm_ratio"] * thresholds["rated_current_a"]["main_input"]
    sample["elec"]["i_ph"] = [limit, limit, limit]
    assert "ALM-I-OVER" not in evaluate(sample)


# ---------------------------------------------------------------- yogusma


def test_dew_warning_fires_below_its_threshold(sample, thresholds):
    sample["env"]["td_margin_k"] = thresholds["dew_margin_warn_k"] - 0.1
    codes = evaluate(sample)
    assert "ALM-DEW-WARN" in codes
    assert "ALM-DEW-ALM" not in codes


def test_dew_alarm_fires_when_condensation_is_imminent(sample, thresholds):
    sample["env"]["td_margin_k"] = thresholds["dew_margin_alarm_k"] - 0.1
    codes = evaluate(sample)
    assert "ALM-DEW-ALM" in codes
    assert "ALM-DEW-WARN" in codes, "1 K'nin altindaki marj 3 K'nin da altindadir"


def test_dew_warning_silent_exactly_at_the_threshold(sample, thresholds):
    sample["env"]["td_margin_k"] = thresholds["dew_margin_warn_k"]
    assert "ALM-DEW-WARN" not in evaluate(sample)


# ------------------------------------------------------------- pano ortami


def test_panel_temperature_alarm_uses_the_upper_air_node(sample, thresholds):
    sample["env"]["t_up_c"] = thresholds["panel_temp_alarm_c"] + 1.0
    assert "ALM-PANEL-TEMP" in evaluate(sample)


# --------------------------------------------------------- koruma sagligi


def test_protection_health_alarm_when_the_arc_guard_reports_a_fault(sample):
    sample["tvoc"]["prot_health_ok"] = False
    assert "ALM-PROT-HEALTH" in evaluate(sample)


def test_protection_health_alarm_when_the_arc_guard_stops_answering(sample):
    """Cevap vermeyen TVOC-2 = pano sessizce korumasiz (rapor 3.5, fabrika ID 248)."""
    sample["tvoc"]["comm_ok"] = False
    assert "ALM-PROT-HEALTH" in evaluate(sample)


def test_no_protection_alarm_when_the_panel_has_no_arc_guard(sample):
    """tvoc null olabilir (sema); bu 'koruma arizali' demek DEGILDIR."""
    sample["tvoc"] = None
    assert "ALM-PROT-HEALTH" not in evaluate(sample)


# ------------------------------------------------------------------- ark


def test_arc_trip_needs_the_trip_counter_to_change(sample):
    """PDU 149 sayaci ARTARSA yeni ark olayi. Sayac sifirlanmadigi icin
    'trips > 0' kurali alarmi sonsuza kadar mandallardi."""
    previous = {"tvoc": {"trips": 3}}
    sample["tvoc"]["trips"] = 4
    assert "ALM-ARC-TRIP" in evaluate(sample, previous)


def test_arc_trip_does_not_latch_on_a_historic_trip_count(sample):
    previous = {"tvoc": {"trips": 4}}
    sample["tvoc"]["trips"] = 4
    assert "ALM-ARC-TRIP" not in evaluate(sample, previous)


def test_arc_trip_is_not_reported_without_a_previous_sample(sample):
    sample["tvoc"]["trips"] = 4
    assert "ALM-ARC-TRIP" not in evaluate(sample)


# ------------------------------------------------------------- dayaniklilik


def test_evaluate_never_returns_the_centre_owned_comms_alarm(sample):
    """ALM-COMMS-LOST merkezin kendi kodudur (backend/app/alarm_service.py);
    kenardan da donerse iki mekanizma ayni alarmi birbirine karsi yonetir."""
    sample["health"]["nodes_ok"] = 0
    assert "ALM-COMMS-LOST" not in evaluate(sample)


def test_evaluate_returns_no_duplicate_codes(sample, thresholds):
    _flatten_rises(sample, thresholds["term_rise_alarm_k"] + 1.0)
    codes = evaluate(sample)
    assert len(codes) == len(set(codes))


def test_evaluate_tolerates_a_payload_with_only_the_required_fields(sample):
    """Opsiyonel bloklar (tvoc, pd, risk) sema geregi eksik olabilir; patlamamali."""
    for optional in ("tvoc", "pd", "risk", "alarms", "fw"):
        sample.pop(optional, None)
    assert isinstance(evaluate(sample), list)


@pytest.mark.parametrize("missing", ["elec", "env", "t_conn"])
def test_evaluate_does_not_raise_on_a_malformed_payload(sample, missing):
    """B'nin risk.py:95 detect() cagrisini try/except ile sarmiyor — bir istisna
    TUM ingest partisini dusururdu. Bozuk yukte bos liste donmek zorundayiz."""
    sample.pop(missing)
    assert evaluate(sample) == []


# ------------------------------------- K indeksi ve sinira kalan sure (L1 esikleri)
#
# Bu kodlar sozlesmede L1 etiketlidir, ama KARARLARI yine duz esik karsilastirmasidir
# (k_ratio ve ttl_h alanlari zaten yukte hazir gelir). Uretim yeri detect.py, KARAR
# yeri burasi — backend/app/risk.py:29-36 POINT_LIMITS tablosu da ayni ayrimi yapar.


def test_k_ratio_warning_fires_above_its_threshold(sample, thresholds):
    _set_point(sample, "DSYA2_L1", k_ratio=thresholds["k_ratio_warn"] + 0.01)
    codes = evaluate(sample)
    assert "ALM-K-WARN" in codes
    assert "ALM-K-ALM" not in codes


def test_k_ratio_alarm_fires_above_its_threshold(sample, thresholds):
    _set_point(sample, "DSYA2_L1", k_ratio=thresholds["k_ratio_alarm"] + 0.01)
    codes = evaluate(sample)
    assert "ALM-K-ALM" in codes
    assert "ALM-K-WARN" in codes, "1.6'yi gecen oran 1.3'u de gecmistir"


def test_k_ratio_silent_exactly_at_the_threshold(sample, thresholds):
    _set_point(sample, "DSYA2_L1", k_ratio=thresholds["k_ratio_warn"])
    assert "ALM-K-WARN" not in evaluate(sample)


def test_healthy_k_ratio_of_one_raises_nothing(sample):
    assert "ALM-K-WARN" not in evaluate(sample)


def test_time_to_limit_alarm_uses_hours_not_days(sample, thresholds):
    """Sozlesme esigi GUN (ttl_warn_days=14), yuk alani SAAT (ttl_h).
    Cevrim unutulursa 14 saat kala degil 14 GUN kala alarm verilir."""
    hours = thresholds["ttl_warn_days"] * 24.0
    _set_point(sample, "DSYA5_L3", ttl_h=hours - 1.0)
    assert "ALM-TTL-14D" in evaluate(sample)


def test_time_to_limit_silent_when_there_is_more_time_than_the_threshold(sample, thresholds):
    hours = thresholds["ttl_warn_days"] * 24.0
    _set_point(sample, "DSYA5_L3", ttl_h=hours + 1.0)
    assert "ALM-TTL-14D" not in evaluate(sample)


def test_time_to_limit_ignores_points_without_an_estimate(sample):
    """ttl_h = null 'tahmin yok' demektir, 'sifir saat kaldi' demek DEGILDIR."""
    for point in sample["t_conn"]:
        point["ttl_h"] = None
    assert "ALM-TTL-14D" not in evaluate(sample)


def test_codes_are_returned_in_contract_bit_order(sample, thresholds, alarm_codes):
    """Sirali cikti, testleri ve gunluk kayitlari kararli kilar."""
    _flatten_rises(sample, thresholds["bus_rise_alarm_k"] + 1.0)
    sample["env"]["td_margin_k"] = -1.0

    bits = {a["code"]: a["bit"] for a in alarm_codes["alarms"]}
    codes = evaluate(sample)
    assert codes == sorted(codes, key=lambda c: bits[c])
