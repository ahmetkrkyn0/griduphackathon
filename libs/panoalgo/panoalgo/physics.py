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


def point_current(payload: dict, point_name: str) -> float:
    """Bir olcum noktasindan gecen akim (A); dT = K * I^2 iliskisinin I'si.

    Fider noktalarinda ana giris akiminin sabit bir kesri gecer; kesir OLCULMUYOR
    (telemetri yalnizca ana faz akimlarini ve notru tasir) ve bu yuzden ana faz
    akimi kullanilir. K kestirimi o kesri kendi icine emer; K/K0 ORANI bundan
    etkilenmez cunku taban da ayni kesirle ogrenilir.

    IKI YER OKUR: edge.EdgePipeline (K kestirimi icin) ve quality.QualityTracker
    (yuk bagimsiz kayma kurali icin). Ayni eslemenin iki kopyasi olsaydi biri
    degistiginde digeri sessizce yanlis akimla calisirdi.
    """
    elec = payload["elec"]
    if point_name.endswith("_N"):
        return float(elec["i_n"])
    phase = int(point_name[-1]) - 1
    return float(elec["i_ph"][phase])
