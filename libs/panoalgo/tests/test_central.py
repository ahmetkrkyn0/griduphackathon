"""Merkez dedektor adaptoru testleri — PLAN.md TA2, backend/app/risk.py:43-46.

B'nin kancasi su Protocol'u bekliyor:
    class CentralDetector(Protocol):
        def detect(self, payload: dict, previous: dict | None) -> list[str]: ...

Bu dosya adaptorun o sozlesmeye uydugunu ve merkezde CIFT ALARM yaratmadigini
dogrular. Beklentilerin kaynagi backend/app/risk.py, alarm_manager.py ve
alarm_service.py okunarak cikarilmistir; ilgili satirlar testlerde yazili.
"""

from __future__ import annotations

import copy

import pytest

from panoalgo.central import CentralDetector


def _point(sample: dict, pt: str) -> dict:
    return next(p for p in sample["t_conn"] if p["pt"] == pt)


def test_detector_exposes_the_protocol_method(sample):
    """Imza: iki konumsal parametre, donus list[str] (risk.py:43-46)."""
    result = CentralDetector().detect(sample, None)
    assert isinstance(result, list)
    assert all(isinstance(code, str) for code in result)


def test_detector_reports_a_real_threshold_breach(sample, thresholds):
    _point(sample, "DSYA1_L1")["dt_c"] = thresholds["term_rise_alarm_k"] + 5.0
    assert "ALM-THR-TERM-ALM" in CentralDetector().detect(sample, None)


def test_detector_returns_only_codes_the_contract_defines(sample, alarm_codes, thresholds):
    """Sozlesmede olmayan kod alarm_manager.py:206-211'de sessizce ATILIR."""
    known = {a["code"] for a in alarm_codes["alarms"]}
    _point(sample, "DSYA1_L1")["dt_c"] = thresholds["bus_rise_alarm_k"] + 5.0
    sample["env"]["td_margin_k"] = -2.0

    assert set(CentralDetector().detect(sample, None)) <= known


def test_detector_does_not_return_data_quality_codes(sample):
    """q bitleri zaten risk.py:184-192'de DOGRU NOKTAYA baglanip alarm uretiyor.
    Ayni kodu detect()'ten de dondurmek (kod, None) anahtariyla IKINCI bir alarm
    acar (alarm_manager.py:51 AlarmKey) — ayni ariza, iki SMS."""
    for point in sample["t_conn"]:
        point["t_c"] = sample["env"]["t_low_c"] - 50.0

    assert not [c for c in CentralDetector().detect(sample, None) if c.startswith("ALM-DQ-")]


def test_detector_never_returns_the_centre_owned_comms_alarm(sample):
    """ALM-COMMS-LOST'u merkez kendi uretir (alarm_service.py:120-127); buradan da
    gelirse observe() onu histerezis sonrasi temizlemeye calisir ve iki mekanizma
    birbiriyle kavga eder."""
    sample["health"]["nodes_ok"] = 0
    assert "ALM-COMMS-LOST" not in CentralDetector().detect(sample, None)


def test_detector_does_not_latch(sample, thresholds):
    """Merkez 'listede olmayan kod o an yok' semantigi ile calisir
    (alarm_manager.py:196); kendi mandalimizi kurarsak alarm hic temizlenmez."""
    detector = CentralDetector()
    hot = copy.deepcopy(sample)
    _point(hot, "DSYA1_L1")["dt_c"] = thresholds["term_rise_alarm_k"] + 5.0

    assert "ALM-THR-TERM-ALM" in detector.detect(hot, None)
    assert "ALM-THR-TERM-ALM" not in detector.detect(sample, hot)


def test_detector_passes_the_previous_sample_through_for_transitions(sample):
    """Ark tripi iki ornek arasindaki sayac farkindan anlasilir."""
    previous = copy.deepcopy(sample)
    previous["tvoc"]["trips"] = 2
    sample["tvoc"]["trips"] = 3

    assert "ALM-ARC-TRIP" in CentralDetector().detect(sample, previous)


@pytest.mark.parametrize("payload", [{}, {"t_conn": None}, {"bozuk": True}, None])
def test_detector_never_raises(payload):
    """risk.py:95 bu cagriyi try/except ile sarmiyor — bir istisna TUM ingest
    partisini dusururdu."""
    assert CentralDetector().detect(payload, None) == []


def test_detector_is_safe_to_share_between_panels(sample, thresholds):
    """Merkezde TEK ornek tum panolar icin kullanilir (risk.py:63)."""
    detector = CentralDetector()
    other = copy.deepcopy(sample)
    other["pano_id"] = "ADM-00002"
    _point(other, "DSYA1_L1")["dt_c"] = thresholds["term_rise_alarm_k"] + 5.0

    assert detector.detect(sample, None) == []
    assert "ALM-THR-TERM-ALM" in detector.detect(other, None)
    assert detector.detect(sample, None) == []
