"""Saat-of-hafta yuk profili testleri — PLAN.md TA1 Adim 5.

Burada SAYISAL degerler degil, profilin SEKLI dogrulanir: rapor 15.2'de
"konut (07-09 ve 18-23 pikleri), ticari (09-18), karma; hafta ici/sonu;
mevsim katsayisi" deniyor. Testler bu nitel iddialari falsifiye edilebilir
hale getirir — profilin egrisi degisirse burasi kirilir.
"""

from datetime import datetime, timezone

import pytest

from helpers import lag1_autocorr
from panoalgo.profiles import PROFILE_KINDS, load_profile

# 2026 takviminde bilinen gunler (UTC): Carsamba is gunu, Pazar hafta sonu.
WEEKDAY = datetime(2026, 9, 16, tzinfo=timezone.utc)  # Carsamba
WEEKEND = datetime(2026, 9, 20, tzinfo=timezone.utc)  # Pazar


def at(day: datetime, hour: int) -> datetime:
    return day.replace(hour=hour, minute=0, second=0, microsecond=0)


@pytest.mark.parametrize("kind", ["konut", "ticari", "karma"])
@pytest.mark.parametrize("hour", range(0, 24))
def test_profile_is_normalised_between_zero_and_one(kind, hour):
    """Sozlesme: 0-1 normalize yuk. Disari tasarsa I = yuk * I_nominal patlar."""
    value = load_profile(kind, at(WEEKDAY, hour))
    assert 0.0 <= value <= 1.0


def test_profile_kinds_are_exactly_the_three_named_in_the_report():
    assert set(PROFILE_KINDS) == {"konut", "ticari", "karma"}


def test_unknown_profile_kind_is_rejected():
    with pytest.raises(ValueError):
        load_profile("fabrika", at(WEEKDAY, 12))


def test_konut_evening_peak_exceeds_night_trough():
    """Rapor 15.2: konut pikleri 18-23. Gece 03:00 en dusuk bolge."""
    assert load_profile("konut", at(WEEKDAY, 20)) > load_profile("konut", at(WEEKDAY, 3))


def test_konut_morning_peak_exceeds_midday():
    """Rapor 15.2: konut pikleri 07-09; ogle arasi daha dusuk."""
    assert load_profile("konut", at(WEEKDAY, 8)) > load_profile("konut", at(WEEKDAY, 13))


def test_ticari_daytime_exceeds_night():
    """Rapor 15.2: ticari 09-18 mesai bandi."""
    assert load_profile("ticari", at(WEEKDAY, 14)) > load_profile("ticari", at(WEEKDAY, 2))


def test_ticari_and_konut_peak_at_different_hours():
    """Iki profil ayni egri olsaydi 'profil' kavrami anlamsiz olurdu."""
    konut_peak = max(range(24), key=lambda h: load_profile("konut", at(WEEKDAY, h)))
    ticari_peak = max(range(24), key=lambda h: load_profile("ticari", at(WEEKDAY, h)))
    assert konut_peak != ticari_peak


def test_ticari_load_drops_on_weekend():
    """Rapor 15.2: hafta ici / hafta sonu ayrimi. Ticari pano pazar gunu bosalir."""
    assert load_profile("ticari", at(WEEKEND, 14)) < load_profile("ticari", at(WEEKDAY, 14))


def test_karma_sits_between_konut_and_ticari_at_business_noon():
    """Karma profil ikisinin harmani; mesai ortasinda ikisinin arasinda kalmali."""
    konut = load_profile("konut", at(WEEKDAY, 14))
    ticari = load_profile("ticari", at(WEEKDAY, 14))
    karma = load_profile("karma", at(WEEKDAY, 14))
    assert min(konut, ticari) <= karma <= max(konut, ticari)


def test_profile_interpolates_between_hour_buckets():
    """168 kutu arasi dogrusal gecis: basamakli profil isil modele sahte sicrama verir."""
    h20 = load_profile("konut", at(WEEKDAY, 20))
    h21 = load_profile("konut", at(WEEKDAY, 21))
    half_past = load_profile("konut", at(WEEKDAY, 20).replace(minute=30))

    assert min(h20, h21) < half_past < max(h20, h21)


def test_profile_is_deterministic():
    """Gurultu profilde degil ureticide; ayni ts ayni degeri vermeli."""
    ts = at(WEEKDAY, 19)
    assert load_profile("konut", ts) == load_profile("konut", ts)


def test_profile_covers_all_168_hour_of_week_buckets():
    """168 kutunun hepsi tanimli ve sayisal olmali (delik yok)."""
    values = [
        load_profile("karma", datetime(2026, 9, 14, h, tzinfo=timezone.utc) + _days(d))
        for d in range(7)
        for h in range(24)
    ]
    assert len(values) == 168
    assert all(isinstance(v, float) for v in values)


def _days(n: int):
    from datetime import timedelta

    return timedelta(days=n)


# --------------------------------------------------------------- mevsim katsayisi


def test_summer_factor_exceeds_winter_factor():
    """Rapor 15.2: 'mevsim katsayisi (Ege yaz klima piki)'."""
    from panoalgo.profiles import season_factor

    assert season_factor(datetime(2026, 8, 1, tzinfo=timezone.utc)) > season_factor(
        datetime(2026, 1, 15, tzinfo=timezone.utc)
    )


def test_season_factor_stays_in_a_sane_band():
    """Katsayi yuku 2 katina cikarmamali; aksi halde anma akimi anlamsizlasir."""
    from panoalgo.profiles import season_factor

    values = [season_factor(datetime(2026, m, 15, tzinfo=timezone.utc)) for m in range(1, 13)]
    assert all(0.5 <= v <= 1.5 for v in values)


def test_season_factor_is_continuous_across_year_end():
    """31 Aralik ile 1 Ocak arasinda basamak olmamali (dongusel model)."""
    from panoalgo.profiles import season_factor

    dec31 = season_factor(datetime(2026, 12, 31, 23, tzinfo=timezone.utc))
    jan01 = season_factor(datetime(2027, 1, 1, 0, tzinfo=timezone.utc))
    assert abs(dec31 - jan01) < 0.01


# ------------------------------------------------------------------ AR(1) gurultu


def test_ar1_phi_matches_exp_minus_ts_over_tau():
    """phi1 = exp(-Ts/tau_yuk) — isil modeldeki 'a' ile ayni kalip."""
    import math

    from panoalgo.profiles import ar1_phi

    assert ar1_phi(ts_s=10.0, tau_s=1800.0) == pytest.approx(math.exp(-10.0 / 1800.0))


def test_ar1_phi_rejects_non_positive_tau():
    from panoalgo.profiles import ar1_phi

    with pytest.raises(ValueError):
        ar1_phi(ts_s=10.0, tau_s=0.0)


def test_ar1_series_is_strongly_autocorrelated():
    """PLAN.md TA1 Adim 6c: lag-1 otokorelasyon > 0.9 (Excel'in 0,00'ina karsit)."""
    from panoalgo.profiles import Ar1Noise, ar1_phi

    noise = Ar1Noise(phi=ar1_phi(ts_s=10.0, tau_s=1800.0), sigma=0.05, seed=42)
    series = [noise.step() for _ in range(2000)]

    assert lag1_autocorr(series) > 0.9


def test_ar1_series_is_reproducible_for_the_same_seed():
    from panoalgo.profiles import Ar1Noise

    a = [Ar1Noise(phi=0.99, sigma=0.05, seed=7).step() for _ in range(50)]
    b = [Ar1Noise(phi=0.99, sigma=0.05, seed=7).step() for _ in range(50)]
    assert a == b


def test_ar1_series_differs_for_different_seeds():
    from panoalgo.profiles import Ar1Noise

    a = [Ar1Noise(phi=0.99, sigma=0.05, seed=7).step() for _ in range(50)]
    c = [Ar1Noise(phi=0.99, sigma=0.05, seed=8).step() for _ in range(50)]
    assert a != c


def test_ar1_stationary_spread_matches_requested_sigma():
    """sigma, SERININ standart sapmasidir; surucu gurultusu sigma*sqrt(1-phi^2)'dir."""
    import statistics

    from panoalgo.profiles import Ar1Noise

    noise = Ar1Noise(phi=0.99, sigma=0.05, seed=3)
    series = [noise.step() for _ in range(20000)]

    assert statistics.pstdev(series) == pytest.approx(0.05, rel=0.25)


def test_ar1_rejects_phi_outside_unit_circle():
    from panoalgo.profiles import Ar1Noise

    with pytest.raises(ValueError):
        Ar1Noise(phi=1.0, sigma=0.05, seed=1)
