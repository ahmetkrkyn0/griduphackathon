"""K indeksi (RLS) testleri — PLAN.md TA2 Adim 1.

Beklenen degerlerin kaynagi:
  - Test govdeleri ve esikleri PLAN.md TA2 Adim 1'deki kod blogundan BIREBIR alinmistir.
  - Isil model ve RLS formulleri: HACKATHON_ANALIZ_RAPORU.md 15.1.
  - lam, uyarim esigi gibi sabitler contracts/alarm-codes.yaml'dan okunur (kural 10).

Test verisi gercek bir olcumden degil, isil modelin KENDISINDEN uretilir: kestirimci
modeli dogru cozuyorsa K'yi geri bulmalidir. k_true 2.0e-4 -> 3.2e-4 (x1.6) bozulma,
alarm-codes.yaml k_ratio_alarm esigiyle ayni buyukluktedir.
"""

from __future__ import annotations

import numpy as np

from panoalgo.detect import KIndexEstimator


def _simulate(k_true: float, n: int, ts: float = 60.0, tau: float = 900.0, seed: int = 0):
    """Isil modelden sentetik (akim, sicaklik artisi) cifti uretir."""
    rng = np.random.default_rng(seed)
    a = np.exp(-ts / tau)
    dt = 0.0
    out = []
    for i in range(n):
        i_a = 200.0 + 150.0 * np.sin(2 * np.pi * i / 96) + rng.normal(0, 10)
        dt = a * dt + (1 - a) * k_true * i_a**2
        out.append((i_a, dt + rng.normal(0, 0.2)))
    return out


def test_k_index_tracks_degradation():
    """Gevseyen baglantida K/K0 yukselir; tau makul araliktadir."""
    est = KIndexEstimator(ts=60.0, lam=0.998)
    for i_a, dt_c in _simulate(k_true=2.0e-4, n=2000):
        est.update(i_a=i_a, dt_c=dt_c)
    est.freeze_baseline()

    state = None
    for i_a, dt_c in _simulate(k_true=3.2e-4, n=2000, seed=1):
        state = est.update(i_a=i_a, dt_c=dt_c)

    assert state.k_ratio > 1.5, f"bozulma yakalanmadi: {state.k_ratio}"
    assert 600 < state.tau_s < 1400, f"tau kestirimi sapti: {state.tau_s}"


def test_k_index_not_updated_without_excitation():
    """Yuk sabitse RLS guncellenmez (kalici uyarim kosulu)."""
    est = KIndexEstimator(ts=60.0, lam=0.998)
    state = None
    for _ in range(500):
        state = est.update(i_a=300.0, dt_c=18.0)
    assert state.excited is False
