"""TB2 Adim 4 — merkez dedektorun gercekten BAGLI oldugu (Kisi B, K5).

Kanca 13 Eylul'den beri hazirdi (`AlarmService(..., detector=...)` -> `RiskEngine`),
uygulama da hazirdi (`panoalgo.central.CentralDetector`), ama `main.py` ikisini hic
birlestirmemisti: `detector` parametresi verilmiyordu. Bu dosya bagi olcer.

Merkez dedektor bir EMNIYET AGIDIR: asil tespit kenarda calisir ve sonucu yukun
`alarms` alanindadir. Emniyet agi, kenar tespitini yapamayan eski/gudulu bir firmware
icin esik ihlallerini merkezde yine de yakalar.
"""

from __future__ import annotations

import copy

import pytest

from app.config import Settings
from app.main import _central_detector
from app.risk import RiskEngine
from helpers import CONTRACTS_DIR

from test_risk import to_sample


@pytest.fixture
def settings() -> Settings:
    return Settings(contracts_dir=CONTRACTS_DIR, ingest_enabled=False)


def test_the_application_actually_builds_a_central_detector(settings):
    """main.py artik dedektoru kuruyor (eskiden hic cagrilmiyordu)."""
    detector = _central_detector(settings)

    assert detector is not None, "merkez dedektor bagli degil (TB2 Adim 4 acik kalir)"
    assert hasattr(detector, "detect")


def test_it_can_be_turned_off_on_purpose(settings):
    """CENTRAL_DETECTOR=0 bilincli bir karardir ve sessizce degil, ayarla ifade edilir."""
    assert _central_detector(Settings(contracts_dir=CONTRACTS_DIR, central_detector_enabled=False)) is None


def test_settings_read_the_switch_from_the_environment(monkeypatch):
    monkeypatch.setenv("CENTRAL_DETECTOR", "0")
    assert Settings.from_env().central_detector_enabled is False

    monkeypatch.setenv("CENTRAL_DETECTOR", "1")
    assert Settings.from_env().central_detector_enabled is True

    monkeypatch.delenv("CENTRAL_DETECTOR")
    assert Settings.from_env().central_detector_enabled is True, "varsayilan ACIK olmali"


def test_a_missing_library_is_logged_loudly_but_does_not_stop_the_service(settings, monkeypatch, caplog):
    """panoalgo yoksa servis ayaga kalkar (kenar tespiti calisir) ama sessiz kalmaz."""
    import builtins

    real_import = builtins.__import__

    def deny_panoalgo(name, *args, **kwargs):
        if name.startswith("panoalgo"):
            raise ImportError("test: panoalgo yok")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", deny_panoalgo)

    with caplog.at_level("ERROR"):
        assert _central_detector(settings) is None

    assert any("merkez dedektor YUKLENEMEDI" in r.message for r in caplog.records), \
        "kutuphane eksikken sessizce gecildi"


def test_the_safety_net_catches_a_threshold_breach_that_the_edge_did_not_report(contracts, tel_payload, settings):
    """Kenar susarsa merkez esik ihlalini yine de bulur — emniyet aginin tum amaci bu."""
    payload = copy.deepcopy(tel_payload)
    limit = float(contracts.thresholds["term_rise_alarm_k"])
    payload["t_conn"][0]["dt_c"] = limit + 15.0
    payload["alarms"] = []  # kenar HICBIR SEY bildirmiyor (eski firmware)
    sample = to_sample(contracts, payload)

    without = RiskEngine(contracts).evaluate(sample)
    with_net = RiskEngine(contracts, _central_detector(settings)).evaluate(sample)

    assert not [c for c in without if c.code == "ALM-THR-TERM-ALM"], \
        "dedektorsuz de bulundu; test ihlali gostermiyor olabilir"
    assert [c for c in with_net if c.code == "ALM-THR-TERM-ALM"], \
        "merkez dedektor esik ihlalini kacirdi"


def test_the_safety_net_does_not_duplicate_what_the_edge_already_reported(contracts, tel_payload, settings):
    """Ayni kodu ikisi de uretirse TEK kosul kalir; aksi halde iki alarm, iki SMS."""
    payload = copy.deepcopy(tel_payload)
    limit = float(contracts.thresholds["term_rise_alarm_k"])
    payload["t_conn"][0]["dt_c"] = limit + 15.0
    payload["alarms"] = ["ALM-THR-TERM-ALM"]  # kenar da bildiriyor
    sample = to_sample(contracts, payload)

    conditions = RiskEngine(contracts, _central_detector(settings)).evaluate(sample)

    matches = [c for c in conditions if c.code == "ALM-THR-TERM-ALM"]
    assert len(matches) == 1, f"ayni ariza icin {len(matches)} kosul uretildi"


def test_the_safety_net_stays_out_of_codes_the_centre_owns(contracts, tel_payload, settings):
    """ALM-COMMS-LOST ve ALM-DQ-* merkezin kendi mekanizmalarindir; dedektor onlari basmaz."""
    detector = _central_detector(settings)

    codes = detector.detect(copy.deepcopy(tel_payload), None)

    assert "ALM-COMMS-LOST" not in codes
    assert not [c for c in codes if c.startswith("ALM-DQ-")]


def test_a_broken_payload_never_takes_down_the_ingest_batch(settings):
    """Dedektorden istisna sizmaz: sizsaydi TUM ingest partisi duserdi (risk.py:95)."""
    detector = _central_detector(settings)

    assert detector.detect({"bozuk": True}, None) == []
    assert detector.detect({}, {"eski": "veri"}) == []
