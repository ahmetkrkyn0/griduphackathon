"""Merkez dedektor adaptoru (TA2, Kisi A): panoalgo -> backend kancasi.

backend/app/risk.py:43-46 su Protocol'u bekliyor:

    class CentralDetector(Protocol):
        \"\"\"Merkezde calisan tespit (or. panoalgo.quality.check + limits.evaluate).\"\"\"
        def detect(self, payload: dict[str, Any], previous: dict[str, Any] | None) -> list[str]: ...

Bu dosya o kancaya takilan tek nesnedir. libs/ altinda oldugu icin B'nin hicbir
dosyasi degismeden calisir (PLAN.md kural 2: bir dosya = bir sahip).

Kullanimi (Kisi B tarafinda, backend/app/main.py):

    from panoalgo.central import CentralDetector
    AlarmService(..., detector=CentralDetector())

MERKEZ NEYI DEGERLENDIRIR, NEYI DEGERLENDIRMEZ
----------------------------------------------
Asil tespit KENARDA calisir (panoalgo tam yigin: RLS + limits + quality + fusion,
ciktisi telemetri yukundeki `alarms`, `risk` ve `t_conn[].q` alanlari). Bu adaptor
merkezdeki EMNIYET AGIDIR: eski veya gudulu bir firmware kenar tespitini yapamazsa
esik ihlalleri yine de yakalanir. Ayni kodu ikisi de uretirse merkez dedup eder
(risk.py:93-96).

Bilerek DISARIDA birakilanlar:

  ALM-DQ-*        Veri kalitesi kodlari merkeze t_conn[].q bit alanindan girer ve
                  risk.py:184-192 onlari DOGRU NOKTAYA baglar. Ayni kodu buradan da
                  dondurursek merkez onu point=None ile kaydeder; AlarmKey
                  (pano, kod, nokta) farkli olur ve AYNI ariza icin IKI alarm, iki SMS
                  uretilir (alarm_manager.py:51). Kenar `quality.point_quality()` +
                  `quality.q_bits()` ile q alanini doldurur; burasi susar.

  ALM-COMMS-LOST  Merkezin kendi kodu (alarm_service.py:41, 120-127). Buradan da
                  gelirse observe() "listede yok" mantigiyla merkezin alarmini
                  histerezis sonrasi temizlemeye calisir; iki mekanizma kavga eder.

MANDALLAMA YOK: detect() her ornekte cagrilir ve yalnizca O AN dogru olan kodlari
doner. Temizlemeyi merkez histerezisi yonetir (alarm_manager.py:196).

ISTISNA SIZDIRMA YOK: risk.py:95 bu cagriyi try/except ile sarmiyor; buradan cikan
bir istisna TUM ingest partisini dusururdu.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import limits

# Merkezde uretilmemesi gereken kodlar (gerekceler modul docstring'inde).
EXCLUDED_PREFIXES = ("ALM-DQ-",)
EXCLUDED_CODES = frozenset({"ALM-COMMS-LOST"})


class CentralDetector:
    """backend/app/risk.py CentralDetector Protocol'unun panoalgo uygulamasi."""

    def __init__(self, contracts_dir: Path | None = None) -> None:
        self._contracts_dir = contracts_dir

    def detect(self, payload: dict[str, Any], previous: dict[str, Any] | None) -> list[str]:
        """Yukun O AN ihlal ettigi sozlesme alarm kodlari."""
        try:
            codes = limits.evaluate(payload, previous, self._contracts_dir)
            return [code for code in codes if _is_central(code)]
        except Exception:  # noqa: BLE001 - bkz. modul docstring
            return []


def _is_central(code: str) -> bool:
    if code in EXCLUDED_CODES:
        return False
    return not any(code.startswith(prefix) for prefix in EXCLUDED_PREFIXES)
