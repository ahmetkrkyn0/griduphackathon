"""Esik karsilastirmasi katmani (TA2 Adim 5, Kisi A): yuk -> alarm kodlari.

Bu modul KARAR verir; backend/app/risk.py ise ayni esikleri yalnizca alarmi
ACIKLAMAK icin (hangi nokta, hangi sinyal, hangi birim) tekrar okur. Is bolumu
boyle: A karar verir, B aciklar.

Iki kural bu dosyanin varligini belirler:

1. HICBIR ESIK KODA GOMULU DEGILDIR (PLAN.md kural 10). Her alarm satirinin
   `threshold:` atfi (or. "thresholds.term_rise_warn_k") sozlesmeden okunur ve
   deger `thresholds` blogundan cozulur. Burada yalnizca "hangi alana bakiliyor"
   ve "karsilastirma yonu" yazilidir.

2. KARSILASTIRMA KESIN BUYUKTUR / KESIN KUCUKTUR. backend/app/risk.py:58-59
   `value > limit` kullanir ve backend/tests/test_risk.py tam esikteki degerin
   alarm URETMEDIGINI kilitler. Burada `>=` kullanilsaydi alarm konsolu kirmizi
   kart acarken dijital ikizde ayni nokta yesil kalirdi.

Katman etiketi notu: sozlesme ALM-DEW-*, ALM-K-*, ALM-TTL-14D kodlarini L1 olarak
etiketler, ama KARARLARI yine duz esik karsilastirmasidir (k_ratio ve ttl_h yukte
hazir gelir). Bu alanlari URETEN kestirimciler detect.py'dedir; karsilastirma
burada toplanir — backend/app/risk.py:29-36 POINT_LIMITS tablosu da ayni ayrimi yapar.

KAPSAM DISI (bilerek):
  ALM-COMMS-LOST  merkezin kendi kodu (backend/app/alarm_service.py); buradan
                  donerse iki mekanizma ayni alarmi birbirine karsi yonetir.
  ALM-DQ-*        veri kalitesi quality.py'de; kenar bunu t_conn[].q bitine yazar
                  (bkz. quality.py modul notu — cift alarm riski).
  ALM-NODE-LOST   zaman penceresi ister, tek ornekten karar verilemez.
  ALM-DOOR-UNAUTH is emri baglami ister (door_grace_min); kenarda bilinmez.
  ALM-LASTGASP    besleme kesilme OLAYI, esik degil.
  ALM-NEUTRAL-THD sozlesmede esigi YOK — bkz. contracts/changes/ onerisi.
  ALM-PD-TREND    sozlesmede esigi YOK ve AG panoda pd bloku null (rapor 3.7).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

DAYS_TO_HOURS = 24.0
THRESHOLD_PREFIX = "thresholds."

# risk.py:38 ile AYNI desen: notr (GIRIS_N) faz karsilastirmasina girmez.
_PHASE_POINT = re.compile(r"^(?P<group>GIRIS|DSYA\d)_L[123]$")

# Nokta basina esik karsilastirmalari: kod -> (yukteki alan, yon).
# Esik DEGERI degil, yalnizca ALAN ve YON kodda yazilidir.
POINT_RULES: dict[str, tuple[str, str]] = {
    "ALM-THR-TERM-WARN": ("dt_c", ">"),
    "ALM-THR-TERM-ALM": ("dt_c", ">"),
    "ALM-THR-BUS-ALM": ("dt_c", ">"),
    "ALM-K-WARN": ("k_ratio", ">"),
    "ALM-K-ALM": ("k_ratio", ">"),
    "ALM-TTL-14D": ("ttl_h", "<"),
}

_CACHE: dict[str, dict] = {}


def default_contracts_dir() -> Path:
    """CONTRACTS_DIR ortam degiskeni, yoksa repo icindeki contracts/ dizini."""
    env = os.getenv("CONTRACTS_DIR")
    if env:
        return Path(env)
    in_repo = Path(__file__).resolve().parents[3] / "contracts"
    return in_repo if in_repo.is_dir() else Path("/contracts")


def load_contract(contracts_dir: Path | None = None) -> dict:
    """alarm-codes.yaml'i bir kez okuyup indeksler (esikler, bit sirasi, atiflar)."""
    directory = contracts_dir or default_contracts_dir()
    key = str(directory)
    if key not in _CACHE:
        data = yaml.safe_load((directory / "alarm-codes.yaml").read_text(encoding="utf-8"))
        _CACHE[key] = {
            "thresholds": data["thresholds"],
            "alarms": {row["code"]: row for row in data["alarms"]},
            "bits": {row["code"]: row["bit"] for row in data["alarms"]},
        }
    return _CACHE[key]


def threshold_for(code: str, contract: dict) -> float:
    """Alarm satirindaki `threshold:` atfini cozer; *_days atiflari saate cevrilir.

    backend/app/risk.py:136-139 ile ayni cozum — iki taraf ayni sayiyi gormeli.
    """
    name = contract["alarms"][code]["threshold"].removeprefix(THRESHOLD_PREFIX)
    value = float(contract["thresholds"][name])
    return value * DAYS_TO_HOURS if name.endswith("_days") else value


def evaluate(
    sample: dict,
    previous: dict | None = None,
    contracts_dir: Path | None = None,
) -> list[str]:
    """Bir telemetri yukunden O AN gecerli alarm kodlarini uretir.

    MANDALLAMAZ: her cagri yalnizca o anki durumu yansitir. Merkezdeki
    AlarmManager "listede olmayan kod o an yok" semantigi ile calisir ve
    temizlemeyi histerezis yonetir (alarm_manager.py:196).

    ASLA ISTISNA ATMAZ: backend/app/risk.py:95 bu cagriyi try/except ile sarmiyor,
    bir istisna TUM ingest partisini dusururdu. Bozuk yukte bos liste doner.
    """
    try:
        contract = load_contract(contracts_dir)
        codes = set()
        codes |= _point_codes(sample, contract)
        codes |= _phase_difference(sample, contract)
        codes |= _electrical(sample, contract)
        codes |= _environment(sample, contract)
        codes |= _protection(sample, previous)
        return sorted(codes, key=lambda c: contract["bits"][c])
    except Exception:  # noqa: BLE001 - bkz. docstring: istisna sizdirmak yasak
        return []


# ------------------------------------------------------------------ nokta bazli


def _point_codes(sample: dict, contract: dict) -> set[str]:
    found = set()
    for point in sample["t_conn"]:
        for code, (field, direction) in POINT_RULES.items():
            value = point.get(field)
            if value is None:  # alan yok veya "tahmin yok" (ttl_h: null)
                continue
            limit = threshold_for(code, contract)
            if (value > limit) if direction == ">" else (value < limit):
                found.add(code)
    return found


def _phase_difference(sample: dict, contract: dict) -> set[str]:
    """Ayni cikisin fazlari arasindaki en buyuk fark esigi asiyor mu?

    Gruplama cikis bazlidir: DSYA1 sicak, DSYA5 soguk olabilir — farkli fiderler
    farkli yuk tasir, aralarindaki fark anomali degildir.
    """
    groups: dict[str, list[float]] = {}
    for point in sample["t_conn"]:
        match = _PHASE_POINT.match(point["pt"])
        if match is None:  # notr ve bilinmeyen noktalar disarida
            continue
        groups.setdefault(match["group"], []).append(point["dt_c"])

    limit = threshold_for("ALM-THR-PHASE-DIF", contract)
    for rises in groups.values():
        if len(rises) >= 2 and (max(rises) - min(rises)) > limit:
            return {"ALM-THR-PHASE-DIF"}
    return set()


def _electrical(sample: dict, contract: dict) -> set[str]:
    """Asiri akim: limit = current_alarm_ratio * anma akimi (ana giris).

    elec.i_ph sozlesme geregi YALNIZCA ana giris akimidir; fider bazli akim
    telemetride yoktur. backend/app/risk.py:198-203 de main_input kullanir —
    fider anma degeri kullanilsaydi merkez yanlis fideri isaret ederdi.
    """
    ratio = threshold_for("ALM-I-OVER", contract)
    rated = float(contract["thresholds"]["rated_current_a"]["main_input"])
    return {"ALM-I-OVER"} if max(sample["elec"]["i_ph"]) > ratio * rated else set()


def _environment(sample: dict, contract: dict) -> set[str]:
    env = sample["env"]
    found = set()

    margin = env.get("td_margin_k")
    if margin is not None:
        for code in ("ALM-DEW-WARN", "ALM-DEW-ALM"):
            if margin < threshold_for(code, contract):
                found.add(code)

    t_up = env.get("t_up_c")
    if t_up is not None and t_up > threshold_for("ALM-PANEL-TEMP", contract):
        found.add("ALM-PANEL-TEMP")
    return found


def _protection(sample: dict, previous: dict | None) -> set[str]:
    """Ark korumasi: saglik biti (durum) ve trip sayaci (degisim).

    tvoc null olmasi "koruma arizali" demek DEGILDIR — o panoda TVOC-2 yok.
    """
    tvoc = sample.get("tvoc")
    if not tvoc:
        return set()

    found = set()
    if tvoc.get("prot_health_ok") is False or tvoc.get("comm_ok") is False:
        found.add("ALM-PROT-HEALTH")

    # Trip sayaci sifirlanmaz; "trips > 0" kurali alarmi sonsuza kadar mandallardi.
    trips = tvoc.get("trips")
    prev_tvoc = (previous or {}).get("tvoc") or {}
    prev_trips = prev_tvoc.get("trips")
    if trips is not None and prev_trips is not None and trips > prev_trips:
        found.add("ALM-ARC-TRIP")
    return found
