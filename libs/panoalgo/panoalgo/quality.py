"""L-1 veri kalitesi katmani (TA2 Adim 5, Kisi A): bozuk olcumu arizadan ayirir.

Bu katmanin amaci bir ariza bulmak DEGIL, arizaya benzeyen bozuk olcumu ayiklamaktir.
Verilen "Istenen Veriler.xlsx"te 15 dakikada 438 A'lik siciramalar var (rapor 3.4a);
fiziksel olarak imkansiz olan bu degerler L0/L1'e girmeden burada isaretlenir.
Bu yuzden uretilen kodlarin onceligi SYS'tir: "izleme sistemi arizasi", pano arizasi degil.

CIFT ALARM UYARISI — bu modulun ciktisi TEK YOLDAN merkeze girmelidir:
  backend/app/risk.py:184-192 her ornekte t_conn[].q bit alanini tarar ve DQ kodunu
  DOGRU NOKTAYA baglar. Ayni kod bir de CentralDetector.detect() donusunden gelirse
  merkez onu point=None ile kaydeder; AlarmKey (pano, kod, nokta) farkli olur ve AYNI
  ariza icin IKI alarm, iki SMS uretilir (alarm_manager.py:51).
  KARAR: kenar `point_quality()` + `q_bits()` ile t_conn[].q alanini doldurur;
  merkez dedektor ALM-DQ-* DONDURMEZ (bkz. central.py).
`check()` yine de PLAN.md:901'deki imzayla durur — senaryo uretimi ve dogrulama
betigi onu kullanir.

OLU BANT NOTU: "baglanti sicakligi ortamin altinda" kuralinin esigi SOZLESMEDE YOK.
Hafif yuklu noktalar (ozellikle GIRIS_N) fiziksel olarak ortam sicakliginda oturur ve
sigma ~0,2 K olcum gurultusuyle ara ara ortamin altini olcer; olu bant olmadan
saglikli pano surekli SYS alarmi uretirdi. Sozlesmeye eklenmesi
contracts/changes/2026-09-14-eksik-esikler.md ile onerildi; sozlesmede varsa oradan
okunur, yoksa asagidaki turetilmis varsayilan kullanilir.
"""

from __future__ import annotations

import os
import re
from collections import deque
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import yaml

from . import physics

# Turetilmis varsayilan: sensor gurultusu sigma ~0,2 K (rapor 15.2) -> 3 sigma = 0,6 K,
# yuvarlak ve guvenli tarafta 1,0 K. Sozlesmeye eklenirse oradaki deger kazanir.
DEFAULT_BELOW_AMBIENT_DEADBAND_K = 1.0
BELOW_AMBIENT_THRESHOLD_KEY = "dq_below_ambient_deadband_k"

SECONDS_PER_MINUTE = 60.0
_DQ_PREFIX = "ALM-DQ-"

# --- Yuk bagimsiz kayma (F-31) ---------------------------------------------
# Sozlesme anahtarlari; yoksa asagidaki turetilmis varsayilanlar kullanilir.
DRIFT_WINDOW_KEY = "dq_drift_samples"
DRIFT_RISE_KEY = "dq_drift_rise_k"
DRIFT_MAX_SLOPE_GROWTH_KEY = "dq_drift_max_slope_growth"
DRIFT_PERSIST_KEY = "dq_drift_persist_samples"

# Pencere: kayma SAATLER boyunca birikir, tek ornekte gorunmez. 15 dk disa aktarimda
# 192 ornek = 48 saat, yani en az iki gece-gunduz cevrimi. Bir cevrimden az pencerede
# "dusuk yuk tabani" yalnizca gunun saatini olcerdi. TURETILMIS.
DEFAULT_DRIFT_SAMPLES = 192

# Tabanin pencere basindan sonuna yukselmesi bu degeri asarsa kayma ilan edilir.
# 2,0 K: olcum gurultusu sigma ~0,2 K (rapor 15.2), yani 10 sigma. TURETILMIS.
DEFAULT_DRIFT_RISE_K = 2.0

# Yuk katsayisi (a) pencerenin ilk yarisindan ikinci yarisina bu orandan fazla
# buyuduyse ortada sensor kaymasi degil GERCEK bir baglanti bozulmasi vardir ve
# kayma ILAN EDILMEZ. 1,10 = %10 buyume payi (gurultu icin). TURETILMIS.
DEFAULT_DRIFT_MAX_SLOPE_GROWTH = 1.10

# Kosulun ARDISIK olarak saglanmasi gereken ornek sayisi. Gecici bir yuk basamagi
# uydurmanin iki yarisini kisa sureligine ayirir; kalici bir kayma ayirmayi surdurur.
# TURETILMIS ve olculmustur (bkz. sozlesmedeki not). 
DEFAULT_DRIFT_PERSIST = 16

_CACHE: dict[str, dict] = {}


@lru_cache(maxsize=1)
def _repo_contracts_dir() -> Path:
    """Repo icindeki contracts/ dizini — dosya sistemi sorgusu bir kez yapilir.

    Onbellek NEDEN gerekli: default_contracts_dir() sicak yolda cagriliyor
    (quality.q_bits her ornekte NOKTA BASINA cagirir, yani ornek basina 25 kez).
    Path.resolve() + is_dir() her seferinde gercek dosya sistemine gidiyordu;
    olcum: uretec+kenar boru hatti 9 mesaj/s, suresinin %80'i bu iki cagrida.
    CONTRACTS_DIR ortam degiskeni onbellege ALINMAZ (asagida her cagride okunur),
    boylece konteynerde /contracts baglama davranisi aynen korunur.
    """
    in_repo = Path(__file__).resolve().parents[3] / "contracts"
    return in_repo if in_repo.is_dir() else Path("/contracts")


def default_contracts_dir() -> Path:
    """CONTRACTS_DIR ortam degiskeni, yoksa repo icindeki contracts/ dizini."""
    env = os.getenv("CONTRACTS_DIR")
    return Path(env) if env else _repo_contracts_dir()


def load_contract(contracts_dir: Path | None = None) -> dict:
    directory = contracts_dir or default_contracts_dir()
    key = str(directory)
    if key not in _CACHE:
        data = yaml.safe_load((directory / "alarm-codes.yaml").read_text(encoding="utf-8"))
        _CACHE[key] = {
            "thresholds": data["thresholds"],
            "bits": {row["code"]: row["bit"] for row in data["alarms"]},
        }
    return _CACHE[key]


def q_bits(codes: list[str], contracts_dir: Path | None = None) -> int:
    """Alarm kodlarini t_conn[].q bit alanina cevirir (0 = temiz).

    Bit numaralari sozlesmeden okunur (alarms[].bit); backend/app/risk.py:184-192
    ayni numaralarla geri cozer.
    """
    bits = load_contract(contracts_dir)["bits"]
    field = 0
    for code in codes:
        bit = bits.get(code)
        if bit is not None:
            field |= 1 << bit
    return field


def codes_from_bits(field: int, contracts_dir: Path | None = None) -> list[str]:
    """q bit alanini alarm kodlarina geri cevirir (backend/app/risk.py:184-192 esi)."""
    bits = load_contract(contracts_dir)["bits"]
    return sorted(code for code, bit in bits.items() if field & (1 << bit))


# ------------------------------------------------------------------ durumsuz


def point_quality(
    sample: dict,
    previous: dict | None,
    contracts_dir: Path | None = None,
) -> dict[str, list[str]]:
    """Nokta basina veri kalitesi kodlari: {nokta adi: [kod, ...]}.

    Yalnizca IKI ornekten karar verilebilen kurallar: degisim hizi ve ortam alti.
    Donmus sensor N ornek ister, o QualityTracker'dadir.
    """
    try:
        contract = load_contract(contracts_dir)
        ambient = sample["env"]["t_low_c"]
        deadband = float(
            contract["thresholds"].get(
                BELOW_AMBIENT_THRESHOLD_KEY, DEFAULT_BELOW_AMBIENT_DEADBAND_K
            )
        )
        max_rate = float(contract["thresholds"]["dq_max_rate_k_per_min"])
        minutes = _elapsed_minutes(sample, previous)
        prev_points = _by_point(previous) if previous else {}

        result: dict[str, list[str]] = {}
        for point in sample["t_conn"]:
            codes: list[str] = []
            t_c = point["t_c"]

            if t_c < ambient - deadband:
                codes.append("ALM-DQ-BELOW-AMBIENT")

            prev = prev_points.get(point["pt"])
            if prev is not None and minutes is not None:
                if abs(t_c - prev["t_c"]) / minutes > max_rate:
                    codes.append("ALM-DQ-JUMP")

            result[point["pt"]] = codes
        return result
    except Exception:  # noqa: BLE001 - istisna ingest partisini dusururdu
        return {}


def check(
    sample: dict,
    prev: dict | None,
    contracts_dir: Path | None = None,
) -> list[str]:
    """PLAN.md:901 imzasi: pano duzeyinde veri kalitesi kodlari (nokta bilgisi yok).

    ASLA ISTISNA ATMAZ; bozuk yukte bos liste doner.
    """
    try:
        contract = load_contract(contracts_dir)
        codes = {c for per_point in point_quality(sample, prev, contracts_dir).values() for c in per_point}

        health = sample.get("health") or {}
        nodes_total = health.get("nodes_total")
        nodes_ok = health.get("nodes_ok")
        if nodes_total is not None and nodes_ok is not None and nodes_ok < nodes_total:
            codes.add("ALM-NODE-LOST")

        return sorted(codes, key=lambda c: contract["bits"][c])
    except Exception:  # noqa: BLE001
        return []


# ------------------------------------------------------------------- durumlu


class QualityTracker:
    """Pencere gerektiren veri kalitesi kurallari (su an: donmus sensor).

    Durum (pano_id, nokta) ikilisiyle anahtarlanir. Sebep: merkezde TEK dedektor
    ornegi TUM panolar icin paylasilir (backend/app/risk.py:63); pano ayrimi
    yapilmazsa panolar birbirinin gecmisini bozar.

    Backfill korumasi: ts geriye giden ornek pencereyi kirletmeden atlanir
    (backend/app/alarm_manager.py:199 ayni korumayi merkezde yapar).
    """

    def __init__(self, contracts_dir: Path | None = None) -> None:
        contract = load_contract(contracts_dir)
        thresholds = contract["thresholds"]
        self._window = int(thresholds["dq_frozen_samples"])
        self._contracts_dir = contracts_dir
        self._history: dict[tuple[str, str], deque[float]] = {}
        self._last_ts: dict[str, datetime] = {}
        # Yuk bagimsiz kayma (F-31): nokta basina (I^2, dT) penceresi.
        self._drift_window = int(thresholds.get(DRIFT_WINDOW_KEY, DEFAULT_DRIFT_SAMPLES))
        self._drift_rise_k = float(thresholds.get(DRIFT_RISE_KEY, DEFAULT_DRIFT_RISE_K))
        # Regresyonun kosullanmasi icin gereken I^2 degisimi; detect.py kalici
        # uyarim kosuluyla ayni olcut ve ayni sozlesme anahtari.
        self._drift_min_cv = float(thresholds.get("excitation_min_cv_i2", 0.02))
        self._drift_max_slope_growth = float(
            thresholds.get(DRIFT_MAX_SLOPE_GROWTH_KEY, DEFAULT_DRIFT_MAX_SLOPE_GROWTH)
        )
        self._drift_persist = int(thresholds.get(DRIFT_PERSIST_KEY, DEFAULT_DRIFT_PERSIST))
        self._drift_streak: dict[tuple[str, str], int] = {}
        self._load_history: dict[tuple[str, str], deque[tuple[float, float]]] = {}

    def check(self, sample: dict) -> dict[str, list[str]]:
        """Nokta basina kodlar; durumsuz kurallar da dahil edilir."""
        try:
            pano_id = sample["pano_id"]
            ts = datetime.fromisoformat(sample["ts"])
            last = self._last_ts.get(pano_id)
            if last is not None and ts < last:
                return {point["pt"]: [] for point in sample["t_conn"]}
            self._last_ts[pano_id] = ts

            result = point_quality(sample, None, self._contracts_dir)
            for point in sample["t_conn"]:
                key = (pano_id, point["pt"])
                window = self._history.setdefault(key, deque(maxlen=self._window))
                window.append(point["t_c"])
                frozen = len(window) == self._window and len(set(window)) == 1
                if frozen:
                    result.setdefault(point["pt"], []).append("ALM-DQ-FROZEN")
                # Kayma penceresi HER ZAMAN beslenir (arizali donem bitince gecmis
                # eksik kalmasin), ama DAHA OZGUL bir tanisi olan nokta icin kayma
                # ILAN EDILMEZ. Donmus sensorun dT'si ortam degistikce kendiliginden
                # oynar; yerinden dusmus sensor ortami olcer ve yuke hic tepki
                # vermez — ikisi de uydurmanin ofset terimini kaydirir. Olculdu
                # (S8, seed 42): bastirma olmadan donmus DSYA5_L2 97 kez, yerinden
                # dusmus DSYA6_L1 49 kez sahte ALM-DQ-DRIFT uretiyordu.
                more_specific = frozen or "ALM-DQ-BELOW-AMBIENT" in result.get(point["pt"], [])
                streak = self._drift_streak.get(key, 0) + 1 if self._drifting(key, sample, point) else 0
                self._drift_streak[key] = streak
                if streak >= self._drift_persist and not more_specific:
                    result.setdefault(point["pt"], []).append("ALM-DQ-DRIFT")
            return result
        except Exception:  # noqa: BLE001
            return {}


    # -------------------------------------------------- yuk bagimsiz kayma (F-31)

    def _drifting(self, key: tuple[str, str], sample: dict, point: dict) -> bool:
        """Sensorun YUKTEN BAGIMSIZ bir kayma biriktirip biriktirmedigi.

        FIZIK AYRACI — bu kuralin tamami buna dayanir. Isil model:

            dT = a * I^2 + b

        Fizik b = 0 der (yuk yoksa isinma yok). Iki bozulma bu iki katsayiyi AYRI
        AYRI bozar ve ayirt edici olan budur:
          - BAGLANTI bozulursa (gevseme, oksitlenme) isil direnc buyur: `a` buyur,
            `b` sifirda kalir. dT her yukte ORANTILI artar.
          - SENSOR kayarsa olcume sabit bir ofset eklenir: `b` buyur, `a` degismez.
            dT yuk sifira gitse bile dusmez.

        Kural penceredeki (I^2, dT) ciftlerine en kucuk kareler uydurur ve YALNIZCA
        `b`'nin buyumesine bakar. Pencerenin ilk yarisinin b'si ile ikinci yarisinin
        b'si karsilastirilir; fark esigi asarsa kayma ilan edilir.

        NEDEN TABAN (dusuk yuk dT'si) YETMEZ — olculdu: ilk surum dusuk yuk tabaninin
        yukselisine bakiyordu ve S1_loose_conn'da (GERCEK gevsek baglanti) 96 kez
        sahte ALM-DQ-DRIFT uretti. Cunku K uc katina cikinca dusuk yuk tabani da uc
        katina cikar. Gercek bir arizayi "kalibrasyon supheli" diye raporlamak, en
        kotu yanlis yondur. Kesisim ayracinda S1 SIFIR kez isaretleniyor.

        UYARIM SARTI: I^2 pencerede yeterince degismezse regresyon kotu kosullanir ve
        b ile a birbirinden ayrilamaz (detect.py'nin kalici uyarim kosuluyla ayni
        sebep). Boyle bir pencerede karar VERILMEZ — "kayma yok" denmez, olculmedi.

        NEDEN MEVCUT DORT KURAL BUNU KACIRIYORDU (docs/12 §4.3):
          - ALM-DQ-JUMP: kayma ornek basina 0,025 K; 10 K/dk esiginin cok altinda.
          - ALM-DQ-FROZEN: deger her ornekte degisiyor, donmus degil.
          - ALM-DQ-BELOW-AMBIENT: kayma YUKARI; olcum ortamin altina hic inmiyor.
          - ALM-NODE-LOST: dugum susmuyor, veri geliyor.

        SYS onceligindedir (L-1): bu bir pano arizasi degil OLCUM arizasidir.
        """
        if "dt_c" not in point:
            return False
        try:
            i2 = physics.point_current(sample, point["pt"]) ** 2
        except (KeyError, IndexError, TypeError, ValueError):
            return False

        window = self._load_history.setdefault(key, deque(maxlen=self._drift_window))
        window.append((i2, float(point["dt_c"])))
        if len(window) < self._drift_window:
            return False

        pairs = list(window)
        half = len(pairs) // 2
        early = _fit(pairs[:half], self._drift_min_cv)
        late = _fit(pairs[half:], self._drift_min_cv)
        if early is None or late is None:
            return False

        slope_early, offset_early = early
        slope_late, offset_late = late
        if (offset_late - offset_early) < self._drift_rise_k:
            return False
        # EGIM DE BUYUDUYSE bu bir sensor kaymasi DEGILDIR: gercek bir baglanti
        # bozulmasi isil direnci buyutur ve yuk katsayisi artar. Yalnizca ofsetin
        # buyudugu durum sensore ozgudur. Olculdu (seed 42, 168 sa): bu kosul olmadan
        # S1_loose_conn'da (GERCEK gevsek baglanti) 20 kez sahte kayma ilan ediliyordu.
        if slope_early > 0.0 and (slope_late / slope_early) > self._drift_max_slope_growth:
            return False
        return True


# ------------------------------------------------------------------- ic


def _fit(pairs: list[tuple[float, float]], min_cv: float) -> tuple[float, float] | None:
    """dT = a * I^2 + b uydurmasi; (a, b) doner. Olculemezse None.

    En kucuk kareler kapali formu:
        a = cov(I^2, dT) / var(I^2)
        b = ort(dT) - a * ort(I^2)

    I^2 yeterince degismiyorsa (degisim katsayisi min_cv altinda) var(I^2) sifira
    yaklasir, a patlar ve b anlamsizlasir. Boyle bir pencerede None doner: kayma
    YOK demek ile OLCEMEDIK demek ayni sey degildir (GK10).
    """
    if len(pairs) < 3:
        return None
    i2s = [i2 for i2, _dt in pairs]
    dts = [dt for _i2, dt in pairs]
    mean_i2 = sum(i2s) / len(i2s)
    mean_dt = sum(dts) / len(dts)
    if mean_i2 <= 0.0:
        return None
    var_i2 = sum((value - mean_i2) ** 2 for value in i2s) / len(i2s)
    if var_i2 <= 0.0 or (var_i2**0.5) / mean_i2 < min_cv:
        return None
    cov = sum((i2 - mean_i2) * (dt - mean_dt) for i2, dt in pairs) / len(pairs)
    slope = cov / var_i2
    return slope, mean_dt - slope * mean_i2


def _by_point(sample: dict) -> dict[str, dict]:
    return {point["pt"]: point for point in sample["t_conn"]}


def _elapsed_minutes(sample: dict, previous: dict | None) -> float | None:
    """Iki ornek arasindaki dakika; geriye giden veya sifir sure icin None.

    Negatif sure ile bolunurse backfill ornekleri sahte sicrama uretirdi.
    """
    if previous is None:
        return None
    try:
        delta = datetime.fromisoformat(sample["ts"]) - datetime.fromisoformat(previous["ts"])
    except (KeyError, TypeError, ValueError):
        return None
    seconds = delta.total_seconds()
    return seconds / SECONDS_PER_MINUTE if seconds > 0.0 else None
