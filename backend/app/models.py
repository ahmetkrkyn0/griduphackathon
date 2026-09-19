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


#: Varlik kutugu sutunlari (F-21), `panels` tablosundaki adlariyla. Tek liste olarak durur
#: cunku UC yerde birden ayni sirada gerekiyor: PanelRecord alanlari, db.py _PANEL_COLUMNS
#: ve ice aktarim ucunun kabul ettigi alanlar. Ayrisirlarsa psycopg `class_row` calisma
#: zamaninda patlar; tek kaynak tutmak bunu imkansiz kilar.
ASSET_FIELDS = (
    "cbs_kodu",
    "fider_id",
    "il",
    "ilce",
    "abone_sayisi",
    "trafo_kva",
    "kritiklik",
    "uretici",
    "seri_no",
    "son_bakim_at",
    "sonraki_bakim_at",
    "kunye_kaynak",
    "kunye_at",
)


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
    # --- varlik kutugu (F-21, goc 008). HEPSI VARSAYILANLI: bilinmeyen pano ilk telemetri
    # mesajinda yalnizca (pano_id, name) ile kaydolur (db.py _REGISTER_PANEL) ve kunyesi
    # hic girilmemis olabilir. None = "CBS aktarimi yapilmadi", sifir DEGIL.
    cbs_kodu: str | None = None
    fider_id: str | None = None
    il: str | None = None
    ilce: str | None = None
    abone_sayisi: int | None = None
    trafo_kva: int | None = None
    kritiklik: str | None = None
    uretici: str | None = None
    seri_no: str | None = None
    son_bakim_at: datetime | None = None
    sonraki_bakim_at: datetime | None = None
    kunye_kaynak: str | None = None
    kunye_at: datetime | None = None

    @property
    def has_asset(self) -> bool:
        """Kunye ice aktarildi mi. Olcut CBS kodudur: kaynagin tekil kimligi odur."""
        return self.cbs_kodu is not None


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
