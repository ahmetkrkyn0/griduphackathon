"""Unit tests for EN 50160 power quality evaluation module."""

import pytest
from panoalgo.power_quality import (
    evaluate_power_quality,
    NOMINAL_VOLTAGE_V,
    V_MIN_NORMAL,
    V_MAX_NORMAL,
)


def test_nominal_voltage_is_compliant():
    report = evaluate_power_quality([230.0, 230.5, 229.5], unbal_pct=1.2)
    assert report.compliant is True
    assert report.status == "COMPLIANT"
    assert report.score == 100
    assert report.unbal_status == "NORMAL"
    assert len(report.notes) == 0
    for p in report.phases:
        assert p.status == "NORMAL"


def test_voltage_sag_detected():
    # 200V is below 207V (V_MIN_NORMAL)
    report = evaluate_power_quality([200.0, 230.0, 230.0], unbal_pct=1.0)
    assert report.phases[0].status == "VOLTAGE_SAG"
    assert report.score < 100
    assert any("gerilim cokmesi" in n for n in report.notes)


def test_voltage_swell_detected():
    # 260V is above 253V (V_MAX_NORMAL)
    report = evaluate_power_quality([230.0, 260.0, 230.0], unbal_pct=1.0)
    assert report.phases[1].status == "VOLTAGE_SWELL"
    assert report.status in ("WARN", "VIOLATION")
    assert any("asiri gerilim" in n for n in report.notes)


def test_unbalance_thresholds():
    # Normal unbalance <= 2.0%
    r1 = evaluate_power_quality([230.0, 230.0, 230.0], unbal_pct=1.8)
    assert r1.unbal_status == "NORMAL"

    # Warning unbalance > 2.0%
    r2 = evaluate_power_quality([230.0, 230.0, 230.0], unbal_pct=3.5)
    assert r2.unbal_status == "UNBALANCE_WARN"
    assert r2.score < 100

    # Alarm unbalance > 5.0%
    r3 = evaluate_power_quality([230.0, 230.0, 230.0], unbal_pct=6.5)
    assert r3.unbal_status == "UNBALANCE_ALARM"
    assert r3.compliant is False
    assert r3.status == "VIOLATION"


def test_invalid_length_raises():
    with pytest.raises(ValueError):
        evaluate_power_quality([230.0, 230.0])
