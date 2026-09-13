"""Testlerde tekrar eden kucuk yardimcilar (conftest'ten import etmek yerine)."""

from __future__ import annotations

import json
import queue
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"


def encode(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")


def utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


def receive_json(ws, timeout_s: float = 3.0) -> dict:
    """Uygulama bozuksa test sonsuza dek beklemesin diye zaman asimli WebSocket okumasi."""
    box: queue.Queue = queue.Queue()
    threading.Thread(target=lambda: box.put(ws.receive_json()), daemon=True).start()
    return box.get(timeout=timeout_s)


class Clock:
    """Elle ilerletilen duvar saati (create_app(clock=...))."""

    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance(self, minutes: float) -> None:
        self.now += timedelta(minutes=minutes)
