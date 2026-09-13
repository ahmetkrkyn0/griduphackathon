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


@dataclass(frozen=True)
class EventRecord:
    """events tablosu: olayi acan ilk alarm (kara kutu bu andan geriye bakar)."""

    event_id: str
    pano_id: str
    occurred_at: datetime
    code: str
    det_label: str | None = None
    point: str | None = None
    prio: str | None = None


@dataclass(frozen=True)
class JournalEntry:
    """alarm_journal satiri + ait oldugu alarmin kimligi (kara kutu zaman cizelgesi)."""

    at: datetime
    action: str
    state: str
    by_user: str | None
    note: str | None
    alarm_id: int
    code: str
    prio: str
    point: str | None
