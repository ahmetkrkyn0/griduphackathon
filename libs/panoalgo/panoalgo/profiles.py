"""Saat-of-hafta yuk profilleri (TA1 Adim 5, Kisi A): 168 kutu, 0-1 normalize.

Rapor 15.2 su uc profili istiyor: konut (07-09 ve 18-23 pikleri), ticari (09-18),
karma; hafta ici / hafta sonu ayrimi ve mevsim katsayisi (Ege yaz klima piki).

Burada YALNIZCA deterministik SEKIL vardir. Gurultu (AR(1)) ve fizik bilerek
disaridadir — generator.py onlari bu sekil uzerine bindirir. Boylece ayni ts
her cagrida ayni yuku verir ve senaryolar tekrarlanabilir kalir.

Kutu degerleri rapor 15.2'nin nitel tarifinden TURETILMISTIR (rapor saat basi
sayisal tablo vermez); testler sayilari degil, rapordaki iddialari dogrular:
konut aksam piki > gece, ticari gunduz > gece, ticari hafta sonu duser.
"""

from __future__ import annotations

import math
import random
from datetime import datetime
from typing import Literal

ProfileKind = Literal["konut", "ticari", "karma"]

PROFILE_KINDS: tuple[str, ...] = ("konut", "ticari", "karma")

HOURS_PER_WEEK = 168
_WEEKEND_FIRST_DAY = 5  # datetime.weekday(): 5 = Cumartesi, 6 = Pazar

# Saat basi (0-23) normalize yuk. Kaynak: rapor 15.2 nitel tarifi — TURETILMIS.
_KONUT_WEEKDAY = (
    0.30, 0.27, 0.25, 0.24, 0.24, 0.26, 0.35, 0.62, 0.72, 0.58, 0.45, 0.44,
    0.46, 0.42, 0.40, 0.41, 0.47, 0.58, 0.76, 0.88, 1.00, 0.96, 0.82, 0.55,
)
_KONUT_WEEKEND = (
    0.36, 0.32, 0.29, 0.27, 0.26, 0.26, 0.30, 0.40, 0.55, 0.66, 0.70, 0.68,
    0.66, 0.62, 0.58, 0.56, 0.58, 0.64, 0.78, 0.90, 0.98, 0.94, 0.84, 0.62,
)
_TICARI_WEEKDAY = (
    0.16, 0.15, 0.14, 0.14, 0.14, 0.15, 0.18, 0.28, 0.55, 0.82, 0.92, 0.97,
    0.94, 0.90, 0.95, 1.00, 0.93, 0.80, 0.54, 0.36, 0.28, 0.24, 0.20, 0.18,
)
_TICARI_WEEKEND = (
    0.14, 0.13, 0.12, 0.12, 0.12, 0.13, 0.14, 0.16, 0.20, 0.26, 0.30, 0.32,
    0.32, 0.31, 0.30, 0.29, 0.28, 0.26, 0.24, 0.22, 0.20, 0.18, 0.16, 0.15,
)


def _week_table(weekday_hours: tuple[float, ...], weekend_hours: tuple[float, ...]) -> tuple[float, ...]:
    """24 saatlik gunduz/hafta sonu sekillerini 168 kutuluk hafta tablosuna serer."""
    table: list[float] = []
    for day in range(7):
        source = weekend_hours if day >= _WEEKEND_FIRST_DAY else weekday_hours
        table.extend(source)
    return tuple(table)


_KONUT = _week_table(_KONUT_WEEKDAY, _KONUT_WEEKEND)
_TICARI = _week_table(_TICARI_WEEKDAY, _TICARI_WEEKEND)
# Karma = ikisinin ortalamasi. BILEREK yeniden normalize EDILMEZ: normalize edilseydi
# karma, mesai ortasinda ticariyi asardi ve "iki profilin karisimi" olmaktan cikardi.
_KARMA = tuple((k + t) / 2.0 for k, t in zip(_KONUT, _TICARI))

_TABLES: dict[str, tuple[float, ...]] = {"konut": _KONUT, "ticari": _TICARI, "karma": _KARMA}


def hour_of_week(ts: datetime) -> int:
    """Pazartesi 00:00 = 0 ... Pazar 23:00 = 167."""
    return ts.weekday() * 24 + ts.hour


def load_profile(kind: ProfileKind, ts: datetime) -> float:
    """Verilen ana ait 0-1 normalize yuk.

    Kutular arasi dogrusal ara deger alinir: aksi halde her saat basi yuk
    basamak yapar ve isil model sahte sicrama gorur.
    """
    table = _TABLES.get(kind)
    if table is None:
        raise ValueError(f"bilinmeyen profil turu {kind!r}; gecerli: {PROFILE_KINDS}")
    index = hour_of_week(ts)
    frac = (ts.minute * 60 + ts.second + ts.microsecond / 1e6) / 3600.0
    here = table[index]
    nxt = table[(index + 1) % HOURS_PER_WEEK]
    return here + (nxt - here) * frac


# --------------------------------------------------------------- mevsim katsayisi

# Ege'de yaz klima piki (rapor 15.2). Tepe gunu ~27 Temmuz, genlik +/- %18.
# Sayilar TURETILMISTIR; rapor yalnizca "mevsim katsayisi (Ege yaz klima piki)" der.
SEASON_PEAK_DAY_OF_YEAR = 208
SEASON_AMPLITUDE = 0.18
_DAYS_PER_YEAR = 365.25


def season_factor(ts: datetime) -> float:
    """Yillik dongusel yuk katsayisi; yaz > kis, yil sonunda basamak yok."""
    day_of_year = ts.timetuple().tm_yday
    phase = 2.0 * math.pi * (day_of_year - SEASON_PEAK_DAY_OF_YEAR) / _DAYS_PER_YEAR
    return 1.0 + SEASON_AMPLITUDE * math.cos(phase)


# ------------------------------------------------------------------ AR(1) gurultu


def ar1_phi(ts_s: float, tau_s: float) -> float:
    """Ornekleme periyodundan AR(1) katsayisi: phi = exp(-Ts/tau).

    Isil modeldeki a = exp(-Ts/tau) ile ayni kalip; yuk dalgalanmasinin da bir
    zaman sabiti vardir, bagimsiz rastgele sayi degildir (rapor 3.4a: verilen
    Excel'de lag-1 otokorelasyon 0,00 — fiziksel olarak imkansiz).
    """
    if ts_s <= 0.0:
        raise ValueError(f"ts_s pozitif olmali: {ts_s}")
    if tau_s <= 0.0:
        raise ValueError(f"tau_s pozitif olmali: {tau_s}")
    return math.exp(-ts_s / tau_s)


class Ar1Noise:
    """Duragan AR(1) gurultu kaynagi: n[k] = phi*n[k-1] + eps[k].

    sigma, URETILEN SERININ standart sapmasidir (surucu gurultusunun degil);
    surucu sigma_eps = sigma*sqrt(1-phi^2) olarak secilir ve ilk deger duragan
    dagilimdan cekilir, boylece serinin basinda isinma donemi olmaz.
    """

    def __init__(self, phi: float, sigma: float, seed: int) -> None:
        if not 0.0 <= phi < 1.0:
            raise ValueError(f"phi [0,1) araliginda olmali (duraganlik): {phi}")
        if sigma < 0.0:
            raise ValueError(f"sigma negatif olamaz: {sigma}")
        self.phi = phi
        self.sigma = sigma
        self._rng = random.Random(seed)
        self._sigma_eps = sigma * math.sqrt(1.0 - phi * phi)
        self._state = self._rng.gauss(0.0, sigma)

    def step(self) -> float:
        """Bir sonraki gurultu ornegi."""
        self._state = self.phi * self._state + self._rng.gauss(0.0, self._sigma_eps)
        return self._state
