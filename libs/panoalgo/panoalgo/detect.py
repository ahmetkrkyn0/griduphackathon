"""L1 fizik tabanli tespit (TA2, Kisi A): K indeksi kestirimi ve faz karsilastirmasi.

Isil model (rapor 15.1):
    surekli : tau * d(dT)/dt + dT = K * I^2
    ayrik   : dT[k+1] = a*dT[k] + beta*I2[k],  a = exp(-Ts/tau),  K = beta/(1-a)

Kestirim, unutma faktorlu ozyinelemeli en kucuk kareler (RLS) ile yapilir:
    theta = [a, beta]^T,  phi[k] = [dT[k], I2[k]]^T,  hedef = dT[k+1]
    e = dT[k+1] - phi^T theta
    g = P phi / (lam + phi^T P phi)
    theta <- theta + g e
    P     <- (P - g phi^T P) / lam

NEDEN NUMPY YOK: bu dosya 2x2 matris cebrini elle yapar. Sebep TA3 — ayni cekirdek
firmware/core/rls.c icinde C'ye tasinacak ve iki taraf ayni test vektorunu (PLAN.md
TA3 Adim 3) 1e-6 farkla gecmek zorunda. Saf Python surum, C surumunun satir satir
esidir; numpy kullanilsaydi bu esleme kaybolurdu.

OLCEKLEME: phi'nin iki bileseni cok farkli buyuklukte (dT ~ 10 K, I^2 ~ 1e5 A^2).
Ham haliyle P matrisi kotu kosullanir. Bu yuzden I^2 sabit bir olcekle bolunur ve
beta geri cevrilir; matematik degismez, sayisal kararlilik duzelir.

Esikler (lam, tau baslangici, kalici uyarim siniri) contracts/alarm-codes.yaml'dan
okunur — bu dosyada gomulu esik YOKTUR (PLAN.md kural 10).
"""

from __future__ import annotations

import math
import os
from collections import deque
from pathlib import Path
from typing import NamedTuple

import yaml

I2_SCALE = 1.0e5  # A^2; regresor bilesenlerini ayni buyukluk mertebesine getirir
P0 = 10.0         # dagitik onsel (olceklenmis parametreler O(1))
EXCITATION_WINDOW = 30   # kalici uyarim icin var(I^2) penceresi (ornek sayisi)
BASELINE_WINDOW = 1000   # K0 medyani icin saklanan kestirim sayisi

# a = exp(-Ts/tau) fiziksel olarak (0,1) araligindadir. RLS gurultude bu araligin
# disina tasabilir; tau ve K raporlanirken guvenli araliga kirpilir.
A_MIN, A_MAX = 1.0e-6, 1.0 - 1.0e-6


class KState(NamedTuple):
    """Bir noktanin anlik isil saglik durumu."""

    k: float             # isil direnc indeksi, dT = K * I^2
    k_ratio: float       # K / K0 (K0 = taban medyani); taban yoksa 1.0
    tau_s: float         # isil zaman sabiti kestirimi (s)
    ttl_h: float | None  # 70 K sinirina tahmini kalan saat (TA2 Adim 6'da doldurulur)
    excited: bool        # son pencerede yeterli yuk degisimi var miydi


def default_contracts_dir() -> Path:
    """CONTRACTS_DIR ortam degiskeni, yoksa repo icindeki contracts/ dizini."""
    env = os.getenv("CONTRACTS_DIR")
    if env:
        return Path(env)
    in_repo = Path(__file__).resolve().parents[3] / "contracts"
    return in_repo if in_repo.is_dir() else Path("/contracts")


def load_thresholds(contracts_dir: Path | None = None) -> dict:
    """contracts/alarm-codes.yaml thresholds blogu."""
    directory = contracts_dir or default_contracts_dir()
    return yaml.safe_load((directory / "alarm-codes.yaml").read_text(encoding="utf-8"))["thresholds"]


class KIndexEstimator:
    """Tek bir olcum noktasi icin K ve tau kestirimcisi.

    Kullanim: her ornekte update(i_a, dt_c); taban ogrenme suresi dolunca
    freeze_baseline() ile K0 sabitlenir, sonrasinda k_ratio anlamli hale gelir.
    """

    def __init__(
        self,
        ts: float,
        lam: float | None = None,
        contracts_dir: Path | None = None,
        excitation_window: int = EXCITATION_WINDOW,
    ) -> None:
        if ts <= 0.0:
            raise ValueError(f"ts pozitif olmali: {ts}")
        thresholds = load_thresholds(contracts_dir)
        self.ts = ts
        self.lam = float(thresholds["rls_lambda"]) if lam is None else lam
        if not 0.0 < self.lam <= 1.0:
            raise ValueError(f"lam (0,1] araliginda olmali: {self.lam}")

        self._min_var_i2 = float(thresholds["excitation_min_var_i2"])
        tau_init = float(thresholds["tau_init_s"])

        a0 = math.exp(-ts / tau_init)
        self._theta = [a0, 0.0]                       # [a, beta*I2_SCALE]
        self._p = [[P0, 0.0], [0.0, P0]]
        self._prev: tuple[float, float] | None = None  # (dt_c, i2)
        self._i2_window: deque[float] = deque(maxlen=excitation_window)
        self._k_history: deque[float] = deque(maxlen=BASELINE_WINDOW)
        self._k0: float | None = None
        self._excited = False

    # ------------------------------------------------------------------ durum

    @property
    def k(self) -> float:
        """Anlik K kestirimi."""
        a = min(A_MAX, max(A_MIN, self._theta[0]))
        beta = self._theta[1] / I2_SCALE
        return beta / (1.0 - a)

    @property
    def tau_s(self) -> float:
        """Anlik tau kestirimi (s)."""
        a = min(A_MAX, max(A_MIN, self._theta[0]))
        return -self.ts / math.log(a)

    @property
    def k0(self) -> float | None:
        """Dondurulmus taban; freeze_baseline() cagrilmadiysa None."""
        return self._k0

    def freeze_baseline(self) -> None:
        """K0'i simdiye kadarki kestirimlerin MEDYANI olarak sabitler.

        Rapor 15.1: "K0 = devreye almadan sonraki 7 gunluk medyan". Medyan secilir
        cunku ortalama, taban ogrenme penceresindeki tek bir sicramadan bozulur.
        """
        if not self._k_history:
            raise ValueError("taban dondurulemez: henuz hicbir kestirim yok")
        self._k0 = _median(self._k_history)

    # ------------------------------------------------------------------ adim

    def update(self, i_a: float, dt_c: float) -> KState:
        """Bir olcum ciftini isler ve guncel durumu doner.

        Kalici uyarim kosulu (rapor 15.1 uyarisi): yuk neredeyse sabitse I^2
        degismez, RLS kestirimi zayiflar. Bu durumda parametreler GUNCELLENMEZ ve
        excited=False doner — eski kestirim korunur, gurultuyle bozulmaz.
        """
        i2 = i_a * i_a
        self._i2_window.append(i2)
        self._excited = self._has_excitation()

        if self._prev is not None and self._excited:
            prev_dt, prev_i2 = self._prev
            self._rls_step(phi=(prev_dt, prev_i2 / I2_SCALE), target=dt_c)

        self._prev = (dt_c, i2)
        self._k_history.append(self.k)
        return self.state()

    def state(self) -> KState:
        """Guncel durumu yeniden hesaplamadan doner."""
        k = self.k
        k_ratio = 1.0 if self._k0 in (None, 0.0) else k / self._k0
        return KState(k=k, k_ratio=k_ratio, tau_s=self.tau_s, ttl_h=None, excited=self._excited)

    # ------------------------------------------------------------------ ic

    def _has_excitation(self) -> bool:
        if len(self._i2_window) < 3:
            return False
        return _variance(self._i2_window) >= self._min_var_i2

    def _rls_step(self, phi: tuple[float, float], target: float) -> None:
        """Unutma faktorlu RLS'in tek adimi (2x2, elle acilmis — bkz. modul notu)."""
        f0, f1 = phi
        p = self._p

        # P phi
        pf0 = p[0][0] * f0 + p[0][1] * f1
        pf1 = p[1][0] * f0 + p[1][1] * f1

        denom = self.lam + f0 * pf0 + f1 * pf1
        if denom <= 0.0:  # sayisal olarak imkansiza yakin; kestirimi bozmaktansa atla
            return

        g0, g1 = pf0 / denom, pf1 / denom
        error = target - (self._theta[0] * f0 + self._theta[1] * f1)

        self._theta[0] += g0 * error
        self._theta[1] += g1 * error

        # P <- (P - g (P phi)^T) / lam   (P simetrik oldugu icin phi^T P = (P phi)^T)
        self._p = [
            [(p[0][0] - g0 * pf0) / self.lam, (p[0][1] - g0 * pf1) / self.lam],
            [(p[1][0] - g1 * pf0) / self.lam, (p[1][1] - g1 * pf1) / self.lam],
        ]


def _median(values) -> float:
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    return ordered[mid] if n % 2 else (ordered[mid - 1] + ordered[mid]) / 2.0


def _variance(values) -> float:
    items = list(values)
    mean = sum(items) / len(items)
    return sum((v - mean) ** 2 for v in items) / len(items)
