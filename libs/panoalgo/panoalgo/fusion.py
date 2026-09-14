"""L3 hipotez fuzyonu (TA2 Adim 6, Kisi A): alarm kodlari -> baskin hipotez + risk.

Rapor 6.5 L3 formulu tarif eder ama SAYILARI VERMEZ:
    "her hipotez icin normalize kanit skorlari x ariza modunun ciddiyet agirligi;
     surekli artis hizina ek puan; en yuksek hipotez + toplam risk gosterilir.
     Basit, aciklanabilir, juriye formul olarak gosterilebilir."

Bu dosyadaki secim:

    S_h   = (h'nin kanitlarindan KACI var / h'nin toplam kanit sayisi) * severity_w[h]
    skor  = round(100 * max_h S_h) + artis_bonusu        (0-100'e kirpilir)
    mod   = argmax_h S_h

NEDEN IKILI KANIT: rapor "normalize kanit skoru"nun tanimini vermiyor. Esikli kodlar
icin dereceli bir skor (or. (k_ratio-1)/(1.6-1)) turetilebilirdi, ama esiksiz kodlarda
(ALM-ARC-TRIP, ALM-PROT-HEALTH, ALM-NEUTRAL-THD ...) karsiligi yok ve iki tur kanit
karisik olcekte toplanirdi. Ikili kanit hem tekdüze hem de juriye tek cumlede
aciklanabilir: "hipotezin bes kanitindan dordu var, ciddiyeti 1.0, risk 80".

Kanit sayisinin hipoteze gore degismesi BILINCLIDIR: HYP-ARC'in tek kaniti vardir
(ALM-ARC-TRIP) ve ciddiyeti 1.0'dir, yani tek trip aninda risk 100 olur — dogru
davranis. HYP-LOOSE-CONN'un bes kaniti vardir ve risk kanit biriktikce yukselir;
filo siralamasinda "dort sinyali olan pano" "tek sinyali olan panonun" onune gecer.

RISK SKORU ALARMIN YERINI TUTMAZ: SMS/arama karari alarm ONCELIGINDEN (P1/P2/P3)
cikar, bu skordan degil. Skor filo siralamasi ve triyaj icindir.

Agirliklar, kanit listeleri ve ayirt ediciler contracts/alarm-codes.yaml'dan okunur;
bu dosyada gomulu hipotez sabiti YOKTUR (PLAN.md kural 10).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, NamedTuple

import yaml

NORMAL_MODE = "HYP-NORMAL"
OVERLOAD_MODE = "HYP-OVERLOAD"

# "Surekli artis hizina ek puan" (rapor 6.5 L3). Sayi RAPORDA YOK — TURETILMIS:
# bir kademe yukselmeye yetecek kadar, baskin hipotezi degistirmeyecek kadar kucuk.
RATE_BONUS_POINTS = 10

_CACHE: dict[str, dict] = {}


class RiskResult(NamedTuple):
    """Telemetri yukundeki `risk` blogunun kaynagi."""

    score: int                          # 0-100 tamsayi (sema kisiti)
    mode: str                           # hypotheses[].code
    ttl_h: float | None                 # pano duzeyi sinira kalan sure
    contributions: dict[str, float]     # alarm kodu -> katki (0-1), toplami 1.0


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
            "hypotheses": data["hypotheses"],
            "thresholds": data["thresholds"],
            "codes": {row["code"] for row in data["alarms"]},
        }
    return _CACHE[key]


def score(
    alarm_codes: list[str] | None,
    features: dict[str, Any] | None,
    contracts_dir: Path | None = None,
) -> RiskResult:
    """Aktif alarm kodlarindan baskin hipotezi ve 0-100 risk skorunu uretir.

    `features` icinde tanidigi anahtarlar (hepsi opsiyonel):
      k_ratio   : HYP-OVERLOAD ayirt edicisi icin (K normal mi?)
      k_rising  : egim surekli pozitif mi (artis hizi bonusu)
      ttl_h     : pano duzeyi sinira kalan sure, oldugu gibi aktarilir

    ASLA ISTISNA ATMAZ: ciktisi dogrudan MQTT yukune girer; burada patlamak
    telemetri yayinini durdururdu.
    """
    try:
        contract = load_contract(contracts_dir)
        present = {c for c in (alarm_codes or []) if c in contract["codes"]}
        feats = features or {}
        ttl_h = feats.get("ttl_h")

        best_hypothesis, best_value = None, 0.0
        for hypothesis in contract["hypotheses"]:
            evidence = hypothesis.get("evidence") or []
            if not evidence or not _discriminator_holds(hypothesis, feats, contract):
                continue
            matched = present & set(evidence)
            if not matched:
                continue
            value = (len(matched) / len(evidence)) * float(hypothesis["severity_w"])
            if value > best_value:
                best_hypothesis, best_value = hypothesis, value

        if best_hypothesis is None:
            return RiskResult(score=0, mode=NORMAL_MODE, ttl_h=ttl_h, contributions={})

        points = round(100.0 * best_value)
        if feats.get("k_rising"):
            points += RATE_BONUS_POINTS

        matched = sorted(present & set(best_hypothesis["evidence"]))
        share = 1.0 / len(matched)
        return RiskResult(
            score=int(min(100, max(0, points))),
            mode=best_hypothesis["code"],
            ttl_h=ttl_h,
            contributions={code: share for code in matched},
        )
    except Exception:  # noqa: BLE001 - bkz. docstring
        return RiskResult(score=0, mode=NORMAL_MODE, ttl_h=None, contributions={})


def _discriminator_holds(hypothesis: dict, features: dict, contract: dict) -> bool:
    """Sozlesmedeki `discriminator` kosulunu uygular.

    Su an yalnizca HYP-OVERLOAD'da var: "tum fazlarda uniform dT artisi VE K normal".
    Asiri akim tek basina "asiri yuk" TESHISI koydurmaz — K tirmaniyorsa bu gercek
    bir baglanti bozulmasidir ve "yuk transferi" onerisi yanlis olurdu (rapor 6.5 L3:
    "K normal (ariza degil!)").
    """
    if hypothesis["code"] != OVERLOAD_MODE or "discriminator" not in hypothesis:
        return True
    k_ratio = features.get("k_ratio")
    if k_ratio is None:
        return True
    return k_ratio < float(contract["thresholds"]["k_ratio_warn"])
