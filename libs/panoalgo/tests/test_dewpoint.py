"""Ciy noktasi (Magnus) testleri — PLAN.md TA1 Adim 1.

Referans degerler HACKATHON_ANALIZ_RAPORU.md 15.1 tablosundan alinmistir;
uydurulmus degil, rapordan kopyalanmistir.
"""

import pytest

from panoalgo.physics import dew_point, dew_point_margin


@pytest.mark.parametrize(
    "t_c,rh_pct,expected",
    [(25.0, 60.0, 16.7), (20.0, 85.0, 17.4), (15.0, 95.0, 14.2), (35.0, 50.0, 23.0)],
)
def test_dew_point_magnus(t_c, rh_pct, expected):
    """Rapor 15.1 tablosundaki dort referans deger."""
    assert dew_point(t_c, rh_pct) == pytest.approx(expected, abs=0.1)


def test_dew_point_rejects_invalid_humidity():
    with pytest.raises(ValueError):
        dew_point(20.0, 0.0)


def test_dew_point_margin_positive_when_surface_above_dew_point():
    """Yuzey 25 degC, hava 20 degC / %85 BN -> Td = 17,4; marj ~ +7,6 K."""
    assert dew_point_margin(25.0, 20.0, 85.0) == pytest.approx(7.6, abs=0.1)


def test_dew_point_margin_negative_means_condensation():
    """Yuzey ciy noktasinin altinda -> negatif marj (yogusma)."""
    assert dew_point_margin(15.0, 20.0, 85.0) < 0.0
