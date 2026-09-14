"""Fiziksel donusumler. Kaynak: HACKATHON_ANALIZ_RAPORU.md 15.1."""

from __future__ import annotations

import math

MAGNUS_B = 17.62
MAGNUS_C = 243.12


def dew_point(t_c: float, rh_pct: float) -> float:
    """Magnus formuluyle ciy noktasi (degC).

    gamma = ln(RH/100) + b*T/(c+T);  Td = c*gamma / (b - gamma)
    """
    if not 0.0 < rh_pct <= 100.0:
        raise ValueError(f"rh_pct (0,100] araliginda olmali: {rh_pct}")
    gamma = math.log(rh_pct / 100.0) + MAGNUS_B * t_c / (MAGNUS_C + t_c)
    return MAGNUS_C * gamma / (MAGNUS_B - gamma)


def dew_point_margin(surface_t_c: float, air_t_c: float, rh_pct: float) -> float:
    """Yuzey sicakligi ile ciy noktasi arasindaki marj (K). Negatif = yogusma."""
    return surface_t_c - dew_point(air_t_c, rh_pct)
