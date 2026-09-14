"""Sinira kalan sure ve faz karsilastirmasi testleri — PLAN.md TA2 Adim 6.

Beklenen degerlerin kaynagi:
  - ttl yontemi: HACKATHON_ANALIZ_RAPORU.md 15.1 "Sinira kalan sure":
        K(t) ~ K_simdi + Kdot * t     (Kdot EWMA ile)
        dT_tahmin(t) = K(t) * I2_profil(t)
        ttl = dT_tahmin(t) >= 70 K olan ILK t
    70 K = contracts/alarm-codes.yaml term_rise_alarm_k (fixture'dan okunur).
  - Faz karsilastirmasi: rapor 6.5 L1-3 — ham dT farki DEGIL, akimla duzeltilmis
    oran r_i = dT_i / I_i^2 karsilastirilir; dengesiz yukte yanlis alarmi onler.
    Notr disarida (backend/app/risk.py:38 ile ayni).

Bu dosyadaki sayisal ornekler elle hesaplanmistir; her testin docstring'inde hesap
yazilidir.
"""

from __future__ import annotations

import math

import pytest

from panoalgo.detect import KIndexEstimator, phase_compare, time_to_limit

CONSTANT_I2 = 250_000.0  # 500 A sabit yuk -> I^2
LIGHT_I2 = 90_000.0      # 300 A sabit yuk; bu yukte K uc katina ciksa bile 70 K asilmaz


def _flat_profile(_hours: float) -> float:
    return CONSTANT_I2


def _light_profile(_hours: float) -> float:
    return LIGHT_I2


# --------------------------------------------------------- sinira kalan sure


def test_time_to_limit_matches_a_hand_computed_linear_case(thresholds):
    """K = 2.0e-4, Kdot = 1.0e-5 / saat, I^2 = 250000, sinir 70 K.

    dT(t) = (2.0e-4 + 1.0e-5*t) * 250000 = 50 + 2.5*t
    70 = 50 + 2.5*t  ->  t = 8 saat.
    """
    limit = thresholds["term_rise_alarm_k"]
    ttl = time_to_limit(
        k_now=2.0e-4, k_slope_per_h=1.0e-5, expected_i2=_flat_profile, limit_k=limit, step_h=0.25
    )
    assert ttl == pytest.approx(8.0, abs=0.3)


def test_time_to_limit_is_none_when_the_index_is_not_growing():
    """Kdot <= 0 ise sinir asilmaz; sema ttl_h icin null bekliyor ('tahmin yok')."""
    assert time_to_limit(k_now=2.0e-4, k_slope_per_h=0.0, expected_i2=_flat_profile, limit_k=70.0) is None
    assert time_to_limit(k_now=2.0e-4, k_slope_per_h=-1e-6, expected_i2=_flat_profile, limit_k=70.0) is None


def test_time_to_limit_is_none_beyond_the_horizon():
    """Cok yavas buyume 'yuz yil sonra' gibi anlamsiz bir sayi uretmemeli."""
    ttl = time_to_limit(
        k_now=1.0e-5, k_slope_per_h=1.0e-12, expected_i2=_flat_profile, limit_k=70.0, horizon_h=90 * 24
    )
    assert ttl is None


def test_time_to_limit_is_zero_when_the_limit_is_already_breached():
    """Sinir zaten asilmissa 'kalan sure' sifirdir, negatif degil."""
    ttl = time_to_limit(k_now=1.0e-3, k_slope_per_h=1.0e-6, expected_i2=_flat_profile, limit_k=70.0)
    assert ttl == 0.0


def test_time_to_limit_uses_the_expected_load_profile_not_a_constant():
    """Rapor 15.1: dT_tahmin(t) = K(t) * I2_PROFIL(t). Gelecekte yuk dususe geciyorsa
    sinir daha gec asilir; sabit akim varsayimi bu farki kacirir."""
    def falling(hours: float) -> float:
        return CONSTANT_I2 * max(0.2, 1.0 - hours / 40.0)

    flat = time_to_limit(k_now=2.0e-4, k_slope_per_h=1.0e-5, expected_i2=_flat_profile, limit_k=70.0)
    fading = time_to_limit(k_now=2.0e-4, k_slope_per_h=1.0e-5, expected_i2=falling, limit_k=70.0)

    assert flat is not None and fading is not None
    assert fading > flat


# ------------------------------------------------- kestirimciye bagli ttl


def _feed(est: KIndexEstimator, k_true: float, n: int, seed: int = 0) -> None:
    """Isil modelden deterministik (akim, artis) cifti uretip kestirimciyi besler."""
    a = math.exp(-est.ts / 900.0)
    dt = 0.0
    for i in range(n):
        i_a = 200.0 + 150.0 * math.sin(2 * math.pi * (i + seed) / 96)
        dt = a * dt + (1 - a) * k_true * i_a**2
        est.update(i_a=i_a, dt_c=dt)


def test_estimator_reports_no_time_to_limit_for_a_stable_connection():
    """Saglikli baglantida K sabittir; ttl_h null olmali (sahte aciliyet uretme)."""
    est = KIndexEstimator(ts=60.0, expected_i2=_flat_profile)
    _feed(est, k_true=2.0e-4, n=1500)
    assert est.state().ttl_h is None


def test_estimator_warns_before_the_limit_is_reached():
    """ttl'nin butun amaci 70 K'dan ONCE uyarmak.

    Hafif yukte (300 A) K uc katina ciksa bile dT = 3*2e-4*90000 = 54 K < 70 K;
    yani sinir HENUZ asilmamis ama egim onu gosteriyor. Beklenen: sonlu, POZITIF
    bir kalan sure.
    """
    est = KIndexEstimator(ts=60.0, expected_i2=_light_profile)
    _feed(est, k_true=2.0e-4, n=1200)
    est.freeze_baseline()

    state = None
    for step in range(1, 21):
        _feed(est, k_true=2.0e-4 * (1.0 + 0.06 * step), n=120, seed=step)
        state = est.state()

    assert state.k_ratio > 1.6, "bozulma yakalanmali"
    assert state.k * LIGHT_I2 < 70.0, "sinir henuz asilmamis olmali"
    assert state.ttl_h is not None and state.ttl_h > 0.0


def test_time_to_limit_shrinks_as_the_connection_degrades():
    """Bozulma hizlandikca kalan sure kisalmali — is emrinin aciliyeti buradan gelir."""
    est = KIndexEstimator(ts=60.0, expected_i2=_light_profile)
    _feed(est, k_true=2.0e-4, n=1200)
    est.freeze_baseline()

    readings = []
    for step in range(1, 21):
        _feed(est, k_true=2.0e-4 * (1.0 + 0.06 * step), n=120, seed=step)
        if est.state().ttl_h is not None:
            readings.append(est.state().ttl_h)

    assert len(readings) >= 2, "en az iki tahmin uretilmeli"
    assert readings[-1] < readings[0]


def test_estimator_hides_the_time_to_limit_without_excitation():
    """Uyarim yoksa K guncellenmez, dolayisiyla egim guvenilmez (rapor 15.1 uyarisi)."""
    est = KIndexEstimator(ts=60.0, expected_i2=_flat_profile)
    for _ in range(300):
        state = est.update(i_a=300.0, dt_c=18.0)
    assert state.excited is False
    assert state.ttl_h is None


def test_estimator_without_a_load_profile_reports_no_time_to_limit():
    """expected_i2 verilmezse tahmin yapilamaz; uydurmak yerine null."""
    est = KIndexEstimator(ts=60.0)
    _feed(est, k_true=2.0e-4, n=600)
    assert est.state().ttl_h is None


# ---------------------------------------------------------- faz karsilastirmasi


def _points(rises: dict[str, float]) -> list[dict]:
    return [{"pt": pt, "dt_c": dt} for pt, dt in rises.items()]


def test_phase_compare_returns_one_ratio_per_phase_point():
    points = _points({"GIRIS_L1": 10.0, "GIRIS_L2": 10.0, "GIRIS_L3": 10.0})
    result = phase_compare(points, [500.0, 500.0, 500.0])
    assert set(result) == {"GIRIS_L1", "GIRIS_L2", "GIRIS_L3"}


def test_balanced_group_has_deviation_of_about_one():
    """Ayni akim, ayni artis -> hicbir nokta one cikmaz."""
    points = _points({"GIRIS_L1": 10.0, "GIRIS_L2": 10.0, "GIRIS_L3": 10.0})
    result = phase_compare(points, [500.0, 500.0, 500.0])
    assert all(value == pytest.approx(1.0, abs=0.01) for value in result.values())


def test_a_hot_phase_stands_out():
    """L2 iki kat sicak, akimlar esit -> r_L2 / medyan = 2."""
    points = _points({"GIRIS_L1": 10.0, "GIRIS_L2": 20.0, "GIRIS_L3": 10.0})
    result = phase_compare(points, [500.0, 500.0, 500.0])
    assert result["GIRIS_L2"] == pytest.approx(2.0, abs=0.01)


def test_current_normalisation_prevents_a_false_alarm_on_an_unbalanced_load():
    """EN ONEMLI TEST (rapor 6.5 L1-3): L1 iki kat akim tasiyorsa dT'si dort kat
    olur (dT = K*I^2) ama K'si AYNIDIR — bu anomali DEGILDIR. Ham dT farkina
    bakan bir kural burada yanlis alarm verirdi."""
    points = _points({"GIRIS_L1": 40.0, "GIRIS_L2": 10.0, "GIRIS_L3": 10.0})
    result = phase_compare(points, [1000.0, 500.0, 500.0])
    assert all(value == pytest.approx(1.0, abs=0.01) for value in result.values())


def test_phase_compare_ignores_the_neutral_point():
    points = _points({"GIRIS_L1": 10.0, "GIRIS_L2": 10.0, "GIRIS_L3": 10.0, "GIRIS_N": 1.0})
    assert "GIRIS_N" not in phase_compare(points, [500.0, 500.0, 500.0])


def test_phase_compare_groups_feeders_separately():
    """DSYA1 ile GIRIS ayni gruba girmez; her cikis kendi icinde kiyaslanir."""
    points = _points(
        {"GIRIS_L1": 10.0, "GIRIS_L2": 10.0, "GIRIS_L3": 10.0,
         "DSYA1_L1": 40.0, "DSYA1_L2": 40.0, "DSYA1_L3": 40.0}
    )
    result = phase_compare(points, [500.0, 500.0, 500.0])
    assert all(value == pytest.approx(1.0, abs=0.01) for value in result.values())


def test_phase_compare_survives_zero_current():
    """Gece yuku sifira yaklasirsa I^2'ye bolme patlamamali."""
    points = _points({"GIRIS_L1": 0.0, "GIRIS_L2": 0.0, "GIRIS_L3": 0.0})
    assert phase_compare(points, [0.0, 0.0, 0.0]) == {}
