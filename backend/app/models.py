"""Ic veri tipleri: ingest ciktilari ve depodan okunan pano kayitlari."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class TelemetryRow:
    """Uzun format telemetri satiri: (ts, pano_id) Sample'dan gelir."""

    tag: str
    value: float
    q: int = 0


@dataclass(frozen=True)
class Sample:
    """Semadan gecmis, zaman damgasi ayristirilmis tek telemetri mesaji."""

    pano_id: str
    ts: datetime
    seq: int
    received_at: datetime
    topic: str
    payload: dict[str, Any]
    rows: tuple[TelemetryRow, ...]


@dataclass(frozen=True)
class Rejection:
    """Karantinaya giden mesaj: dusurulmez, nedeniyle birlikte saklanir."""

    received_at: datetime
    topic: str
    reason: str
    raw: Any


@dataclass(frozen=True)
class PanelRecord:
    """panels tablosu + son durum. payload None = pano hic veri gondermedi."""

    pano_id: str
    name: str
    pano_type: str
    lat: float | None
    lon: float | None
    installed_at: datetime
    baseline_day: int
    last_rx: datetime | None
    payload: dict[str, Any] | None
