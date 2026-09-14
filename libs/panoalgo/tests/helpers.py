"""Testlerde tekrar eden kucuk yardimcilar (conftest'ten import etmek yerine).

Istatistik yardimcilari BILEREK burada durur, uretim kodunda degil: lag-1
otokorelasyon uretecin bir ozelligi degil, uretecin uzerine kurulan bir
OLCUTTUR (PLAN.md TA1 Adim 6c).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

# tests -> panoalgo -> libs -> repo koku
REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS_DIR = REPO_ROOT / "contracts"


def utc(*args: int) -> datetime:
    """Kisa UTC zaman damgasi kurucusu: utc(2026, 9, 16, 20)."""
    return datetime(*args, tzinfo=timezone.utc)


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def lag1_autocorr(series: Sequence[float]) -> float:
    """Lag-1 ornek otokorelasyonu r1 = sum((x[k]-m)(x[k+1]-m)) / sum((x[k]-m)^2).

    Verilen 'Istenen Veriler.xlsx'te bu deger 0,00 cikiyor (rapor 3.4a); fiziksel
    bir yuk serisinde 1'e yakin olmasi beklenir.
    """
    if len(series) < 3:
        raise ValueError(f"lag-1 otokorelasyon icin en az 3 ornek gerekir: {len(series)}")
    m = mean(series)
    num = sum((series[k] - m) * (series[k + 1] - m) for k in range(len(series) - 1))
    den = sum((x - m) ** 2 for x in series)
    if den == 0.0:
        raise ValueError("seri sabit; otokorelasyon tanimsiz")
    return num / den
