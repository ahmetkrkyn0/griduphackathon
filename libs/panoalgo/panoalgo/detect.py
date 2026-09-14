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
import re
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import yaml

I2_SCALE = 1.0e5  # A^2; regresor bilesenlerini ayni buyukluk mertebesine getirir
P0 = 10.0         # dagitik onsel (olceklenmis parametreler O(1))
EXCITATION_WINDOW = 30   # kalici uyarim icin var(I^2) penceresi (ornek sayisi)
BASELINE_WINDOW = 1000   # K0 medyani icin saklanan kestirim sayisi

# --- Sinira kalan sure (ttl) ayarlari. Rapor 15.1 yontemi verir, SAYILARI VERMEZ. ---
TTL_HORIZON_H = 90 * 24    # bu ufkun otesi "sinir asilmaz" sayilir (TURETILMIS)
TTL_STEP_H = 1.0           # ileri tarama adimi; profil saat bazli oldugu icin 1 saat
K_SLOPE_ALPHA = 0.05       # Kdot icin EWMA katsayisi (TURETILMIS)
SLOPE_WINDOW = 300         # "egim surekli pozitif" kosulunun penceresi
SLOPE_PERSISTENCE_MIN = 0.6  # pencerenin en az bu orani pozitif olmali
SECONDS_PER_HOUR = 3600.0

# Kalici uyarim, MUTLAK var(I^2) esigi ile OLCEKE BAGIMLIDIR: notr iletken faz
# akiminin ~1/6'sini tasir, I^2 ~36 kat, var(I^2) ~1000 kat kucuktur. Olculdu
# (25 saat, 30 ornek pencere): GIRIS_L1 var = 1.67e9 / cv = 0.022 ; GIRIS_N
# var = 1.24e6 / cv = 0.028 — yani ayni GORELI yuk degisimi, mutlak esik yalnizca
# fazlari geciriyor. Goreli olcut (degisim katsayisi) olcekten bagimsizdir ve iki
# iletkeni de dogru degerlendirir. Sozlesmeye eklenmesi contracts/changes/ ile
# onerildi; sozlesmede varsa oradan okunur.
EXCITATION_MIN_CV_KEY = "excitation_min_cv_i2"
DEFAULT_EXCITATION_MIN_CV = 0.02

_PHASE_POINT = re.compile(r"^(?P<group>GIRIS|DSYA\d)_L(?P<phase>[123])$")

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
        expected_i2: Callable[[float], float] | None = None,
    ) -> None:
        if ts <= 0.0:
            raise ValueError(f"ts pozitif olmali: {ts}")
        thresholds = load_thresholds(contracts_dir)
        self.ts = ts
        self.lam = float(thresholds["rls_lambda"]) if lam is None else lam
        if not 0.0 < self.lam <= 1.0:
            raise ValueError(f"lam (0,1] araliginda olmali: {self.lam}")

        self._min_var_i2 = float(thresholds["excitation_min_var_i2"])
        self._min_cv_i2 = float(
            thresholds.get(EXCITATION_MIN_CV_KEY, DEFAULT_EXCITATION_MIN_CV)
        )
        self._limit_k = float(thresholds["term_rise_alarm_k"])
        self._expected_i2 = expected_i2
        tau_init = float(thresholds["tau_init_s"])

        a0 = math.exp(-ts / tau_init)
        self._theta = [a0, 0.0]                       # [a, beta*I2_SCALE]
        self._p = [[P0, 0.0], [0.0, P0]]
        self._prev: tuple[float, float] | None = None  # (dt_c, i2)
        self._i2_window: deque[float] = deque(maxlen=excitation_window)
        self._k_history: deque[float] = deque(maxlen=BASELINE_WINDOW)
        self._k0: float | None = None
        self._excited = False
        self._prev_k: float | None = None
        self._k_slope_per_h = 0.0
        self._slope_signs: deque[int] = deque(maxlen=SLOPE_WINDOW)

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
        k_now = self.k
        self._track_slope(k_now)
        self._k_history.append(k_now)
        return self.state()

    def state(self) -> KState:
        """Guncel durumu doner."""
        k = self.k
        k_ratio = 1.0 if self._k0 in (None, 0.0) else k / self._k0
        return KState(
            k=k,
            k_ratio=k_ratio,
            tau_s=self.tau_s,
            ttl_h=self._ttl_h(k),
            excited=self._excited,
        )

    # -------------------------------------------------------------- egim / ttl

    def _track_slope(self, k_now: float) -> None:
        """Kdot'i EWMA ile izler ve egimin SUREKLI pozitif olup olmadigini sayar.

        Sureklilik kosulu sozlesmeden gelir: ALM-K-ALM satirinin ek kosulu
        "egim surekli pozitif"tir. Tek basina EWMA yeterli degildir — kararli bir
        K'de bile gurultu egimi kil payi pozitif birakabilir ve ufuk icinde sahte
        bir "sinira kalan sure" uretebilirdi.
        """
        if self._prev_k is not None and self._excited:
            per_hour = (k_now - self._prev_k) / (self.ts / SECONDS_PER_HOUR)
            self._k_slope_per_h = (
                K_SLOPE_ALPHA * per_hour + (1.0 - K_SLOPE_ALPHA) * self._k_slope_per_h
            )
            self._slope_signs.append(1 if per_hour > 0.0 else 0)
        self._prev_k = k_now

    def _slope_is_persistent(self) -> bool:
        if len(self._slope_signs) < SLOPE_WINDOW:
            return False
        return sum(self._slope_signs) / len(self._slope_signs) > SLOPE_PERSISTENCE_MIN

    def _ttl_h(self, k_now: float) -> float | None:
        """Sinira kalan sure; tahmin guvenilir degilse None.

        Guvenilmez sayilan durumlar: yuk profili verilmemis, kalici uyarim yok
        (K guncellenmiyor, dolayisiyla egim anlamsiz), egim surekli pozitif degil.
        """
        if self._expected_i2 is None or not self._excited or not self._slope_is_persistent():
            return None
        return time_to_limit(
            k_now=k_now,
            k_slope_per_h=self._k_slope_per_h,
            expected_i2=self._expected_i2,
            limit_k=self._limit_k,
        )

    @property
    def k_slope_per_h(self) -> float:
        """EWMA ile duzlestirilmis Kdot (saat basina)."""
        return self._k_slope_per_h

    # ------------------------------------------------------------------ ic

    def _has_excitation(self) -> bool:
        """Yeterli yuk degisimi var mi (rapor 15.1 kalici uyarim kosulu).

        Iki olcut: sozlesmedeki MUTLAK var(I^2) esigi veya olcekten bagimsiz GORELI
        esik (degisim katsayisi). Ikisinden biri yeterlidir; goreli olcut olmadan
        notr nokta hicbir zaman uyarilmis sayilmaz (bkz. modul basindaki olcum).
        """
        if len(self._i2_window) < 3:
            return False
        variance = _variance(self._i2_window)
        if variance >= self._min_var_i2:
            return True
        mean = sum(self._i2_window) / len(self._i2_window)
        if mean <= 0.0:
            return False
        return (variance**0.5) / mean >= self._min_cv_i2

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


# ------------------------------------------------------- sinira kalan sure


def time_to_limit(
    k_now: float,
    k_slope_per_h: float,
    expected_i2: Callable[[float], float],
    limit_k: float,
    horizon_h: float = TTL_HORIZON_H,
    step_h: float = TTL_STEP_H,
) -> float | None:
    """70 K sinirina tahmini kalan saat (rapor 15.1).

        K(t)        ~ K_simdi + Kdot * t
        dT_tahmin(t) = K(t) * I2_profil(t)
        ttl          = dT_tahmin(t) >= limit olan ILK t

    Gelecek yuk SABIT VARSAYILMAZ: `expected_i2` saat ofsetini alip beklenen I^2
    doner (saat-of-hafta profili). Yuk dususe geciyorsa sinir daha gec asilir.

    None doner: sinir buyume yonunde degilse (Kdot <= 0) veya ufuk icinde asilmiyorsa.
    Sema ttl_h alanini nullable tanimlar; "tahmin yok" ile "sifir saat kaldi" ayri seydir.
    """
    if k_now * expected_i2(0.0) >= limit_k:
        return 0.0
    if k_slope_per_h <= 0.0:
        return None

    steps = int(horizon_h / step_h)
    for index in range(1, steps + 1):
        hours = index * step_h
        if (k_now + k_slope_per_h * hours) * expected_i2(hours) >= limit_k:
            return hours
    return None


# ---------------------------------------------------------- faz karsilastirmasi


def phase_compare(points: list[dict], i_ph: list[float]) -> dict[str, float]:
    """Akimla duzeltilmis faz karsilastirmasi (rapor 6.5 L1-3).

        r_i   = dT_i / I_i^2
        sapma = r_i / medyan(r_grup)

    NEDEN HAM dT FARKI DEGIL: dT = K*I^2 oldugu icin iki kat akim tasiyan faz DORT
    kat isinir, ama K'si aynidir — bu anomali degildir. Ham farka bakan bir kural
    dengesiz yukte surekli yanlis alarm verir.

    Gruplama cikis bazlidir (GIRIS, DSYA1..DSYA7); notr disaridadir. Fider akimi
    ana giris akiminin sabit bir kesri oldugu icin, grup icindeki oranlamada o kesir
    sadelesir — bu yuzden fider akimini ayrica bilmeye gerek yoktur.
    """
    ratios: dict[str, float] = {}
    groups: dict[str, list[str]] = {}

    for point in points:
        match = _PHASE_POINT.match(point["pt"])
        if match is None:
            continue
        current = i_ph[int(match["phase"]) - 1]
        if current <= 0.0:
            continue
        ratios[point["pt"]] = point["dt_c"] / (current * current)
        groups.setdefault(match["group"], []).append(point["pt"])

    result: dict[str, float] = {}
    for members in groups.values():
        reference = _median([ratios[pt] for pt in members])
        if reference == 0.0:
            continue
        for pt in members:
            result[pt] = ratios[pt] / reference
    return result
