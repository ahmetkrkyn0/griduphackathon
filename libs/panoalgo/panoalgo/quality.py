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
from pathlib import Path

import yaml

# Turetilmis varsayilan: sensor gurultusu sigma ~0,2 K (rapor 15.2) -> 3 sigma = 0,6 K,
# yuvarlak ve guvenli tarafta 1,0 K. Sozlesmeye eklenirse oradaki deger kazanir.
DEFAULT_BELOW_AMBIENT_DEADBAND_K = 1.0
BELOW_AMBIENT_THRESHOLD_KEY = "dq_below_ambient_deadband_k"

SECONDS_PER_MINUTE = 60.0
_DQ_PREFIX = "ALM-DQ-"

_CACHE: dict[str, dict] = {}


def default_contracts_dir() -> Path:
    """CONTRACTS_DIR ortam degiskeni, yoksa repo icindeki contracts/ dizini."""
    env = os.getenv("CONTRACTS_DIR")
    if env:
        return Path(env)
    in_repo = Path(__file__).resolve().parents[3] / "contracts"
    return in_repo if in_repo.is_dir() else Path("/contracts")


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
        self._window = int(contract["thresholds"]["dq_frozen_samples"])
        self._contracts_dir = contracts_dir
        self._history: dict[tuple[str, str], deque[float]] = {}
        self._last_ts: dict[str, datetime] = {}

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
                if len(window) == self._window and len(set(window)) == 1:
                    result.setdefault(point["pt"], []).append("ALM-DQ-FROZEN")
            return result
        except Exception:  # noqa: BLE001
            return {}


# ------------------------------------------------------------------- ic


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
