"""Ust sebeke kesintisi uclari (F-22): GET /api/v1/outages, GET /api/v1/outages/{id}.

Kesinti bir ALARM DEGILDIR — alarmlari aciklayan bir olaydir. Bu yuzden sozlesmeye yeni bir
alarm kodu eklenmedi: alt alarmlar (ALM-LASTGASP, ALM-COMMS-LOST) zaten var ve DOGRU
(panolar gercekten sustu); ustlerine bir kod daha koymak konsola bir satir daha eklerdi,
oysa madde konsoldaki satir sayisini AZALTMAYI hedefliyor.

Baginti TOPLAYICIDIR, SUSTURUCU DEGIL: hicbir alarm bastirilmaz, bildirim davranisi
degismez. Bkz. backend/app/outage.py modul basligi.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request

from ..epdk import kesinti_kaydi

router = APIRouter(prefix="/api/v1", tags=["events"])


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def outage_view(row: dict) -> dict[str, Any]:
    """Depo satirini OutageEvent semasina cevirir."""
    panolar = list(row["panolar"])
    bilinen = [p["abone_sayisi"] for p in panolar if p.get("abone_sayisi") is not None]
    return {
        "outage_id": row["outage_id"],
        "fider_id": row["fider_id"],
        "started_at": _iso(row["started_at"]),
        "detected_at": _iso(row["detected_at"]),
        "ended_at": _iso(row["ended_at"]),
        "state": "acik" if row["ended_at"] is None else "kapandi",
        "panolar": [
            {
                "pano_id": p["pano_id"],
                "name": p.get("name"),
                "last_rx": _iso(p["last_rx"]) if isinstance(p["last_rx"], datetime) else p["last_rx"],
                "abone_sayisi": p.get("abone_sayisi"),
            }
            for p in panolar
        ],
        # EPDK Madde 8/2 "etkilenen kullanici sayisi". Yalnizca kunyesi olan panolar
        # toplanir; HICBIRI yoksa null doner — SIFIR YAZILMAZ, cunku "abone yok" ile
        # "abone sayisini bilmiyoruz" ayni sey degildir.
        "abone_toplami": sum(bilinen) if bilinen else None,
        # Kac panonun sayilamadigi GIZLENMEZ: toplam bu sayi kadar eksiktir.
        "abone_eksik": sum(1 for p in panolar if p.get("abone_sayisi") is None),
    }


class OutageIndex:
    """Alarm -> kesinti baglantisini TURETIR (saklanmaz).

    Bir alarm, panosu kesintiye dahilse VE olayin baslangicindan sonra acildiysa o
    kesintinin parcasidir. Baglanti zaten pano + zaman penceresinin bir SONUCUDUR; ayri bir
    sutunda saklamak ayni bilgiyi iki yerde tutup ayrisma riski yaratirdi ve alarm yazma
    yoluna (F-20 hash zincirinin de gectigi sicak yol) yeni bir alan sokardi.
    """

    def __init__(self, rows: list[dict]) -> None:
        self._by_panel: dict[str, list[tuple[datetime, datetime | None, str]]] = {}
        for row in rows:
            for panel in row["panolar"]:
                self._by_panel.setdefault(panel["pano_id"], []).append(
                    (row["started_at"], row["ended_at"], row["outage_id"])
                )

    def of(self, pano_id: str, raised_at: datetime) -> str | None:
        for started_at, ended_at, outage_id in self._by_panel.get(pano_id, ()):
            if raised_at >= started_at and (ended_at is None or raised_at <= ended_at):
                return outage_id
        return None


@router.get("/outages")
def list_outages(
    request: Request,
    state: Literal["acik", "hepsi"] = Query("acik"),
) -> list[dict[str, Any]]:
    rows = request.app.state.store.list_outages(only_open=state == "acik")
    return [outage_view(row) for row in rows]


@router.get("/outages/{outage_id}")
def get_outage(request: Request, outage_id: str) -> dict[str, Any]:
    row = request.app.state.store.get_outage(outage_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"kesinti bulunamadi: {outage_id}")
    return outage_view(row)


# Kanit paketinde aranan alarm durumlari: kesinti alarmi TEMIZLENMIS de olabilir ve
# kanit yine gecerlidir.
_ALL_STATES = ("active", "acked", "shelved", "cleared")


def _kanit(store, outage: dict) -> list[dict[str, Any]]:
    """Kesintiye dahil her pano icin MEVCUT kara kutu olayina baglanti (F-23).

    YENI ZAMAN CIZELGESI URETILMEZ: GET /events/{event_id}/blackbox sozlesmede zaten var,
    OlayAnalizi.tsx yazdirilabilir cizelgeyi uretiyor ve F-02 pencereyi 336 saate cikardi.
    Burada yapilan tek sey, var olan cizelgeyi Madde 8 kaydina BAGLAMAKTIR.
    """
    kanit: list[dict[str, Any]] = []
    for panel in outage["panolar"]:
        alarms = store.list_alarms(_ALL_STATES, None, panel["pano_id"], 50)
        # Kesintinin baslangicindan SONRA acilan ilk olay: oncesindeki alarmlar bu
        # kesintinin kaniti degildir.
        event_id = next(
            (a.event_id for a in sorted(alarms, key=lambda a: a.raised_at)
             if a.event_id and a.raised_at >= outage["started_at"]),
            None,
        )
        kanit.append({
            "pano_id": panel["pano_id"],
            "name": panel.get("name"),
            "event_id": event_id,
            "blackbox": f"/api/v1/events/{event_id}/blackbox" if event_id else None,
        })
    return kanit


@router.get("/outages/{outage_id}/epdk-kaydi")
def epdk_kaydi(request: Request, outage_id: str) -> dict[str, Any]:
    """EPDK Madde 8 kesinti kaydi TASLAGI. Resmi bir kayit DEGILDIR."""
    store = request.app.state.store
    row = store.get_outage(outage_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"kesinti bulunamadi: {outage_id}")

    # Kunye (il/ilce/cbs_kodu) pano kayitlarindan okunur: outage_panels yalnizca kesinti
    # anindaki last_rx ve abone sayisini kopyalar (kunye sonradan degisirse gecmis kesinti
    # kaydinin abone sayisi degismemeli).
    kunye = {r.pano_id: r for r in store.list_panels([p["pano_id"] for p in row["panolar"]])}
    view = outage_view(row)
    for panel in view["panolar"]:
        record = kunye.get(panel["pano_id"])
        if record is not None:
            panel["il"] = record.il
            panel["ilce"] = record.ilce
            panel["cbs_kodu"] = record.cbs_kodu
    return kesinti_kaydi(view, kanit=_kanit(store, row))
