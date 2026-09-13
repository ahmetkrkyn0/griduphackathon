"""Kisisel veri azaltma (KVKK): kayit ve denetim izinde telefon numarasi acik yazilmaz."""

from __future__ import annotations

KEEP_PREFIX = 3  # "+90"
KEEP_SUFFIX = 4


def mask_number(number: str) -> str:
    """'+905550000001' -> '+90******0001'. Kisa veya alfanumerik gonderici oldugu gibi kalir."""
    if len(number) <= KEEP_PREFIX + KEEP_SUFFIX or not number.lstrip("+").isdigit():
        return number
    hidden = len(number) - KEEP_PREFIX - KEEP_SUFFIX
    return number[:KEEP_PREFIX] + "*" * hidden + number[-KEEP_SUFFIX:]
