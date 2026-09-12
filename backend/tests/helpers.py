"""Testlerde tekrar eden kucuk yardimcilar (conftest'ten import etmek yerine)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"


def encode(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")


def utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)
