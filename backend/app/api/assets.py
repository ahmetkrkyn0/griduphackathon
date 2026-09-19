"""Varlik kutugu uclari (F-21): GET /api/v1/fleet/assets, POST /api/v1/fleet/assets.

NEDEN AYRI BIR VARLIK ANA KAYDI YOK
EPDK CBS usul ve esaslari dagitim panosunu ZATEN tekil kodla ve kullanici tesisleriyle
eslestirilmis tutmayi zorunlu kiliyor: panonun kimligi musteride var, biz KAYNAK DEGIL
TUKETICIYIZ. Bu yuzden kunye `panels` tablosuna sutun olarak girdi, ayri bir tabloya
degil; `pano_id` birincil anahtar olarak kaldi, `cbs_kodu` UNIQUE ikinci kimliktir.

BOS KUNYE GIZLENMEZ
`GET /fleet/assets` kapsama oranini SAYIYLA dondurur. Bu teslimde demo filosunun kunyesi
bostur (GK3: gercek bir CBS aktarimina erisim yok) ve bu, yanitin `kapsama` alaninda
acikca gorunur. Ekranin "veri yok" ile "deger sifir"i karistirmamasi icin kunyesiz pano
`asset: null` doner.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..auth import Identity, require
from ..db import UnknownPanel
from .views import asset_coverage, asset_view

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["assets"])

#: Sozlesmedeki AssetRegistry.kritiklik sozlugu. CBS/varlik yonetiminden ICE AKTARILAN bir
#: etikettir; bizim tanimladigimiz bir siniflandirma DEGILDIR (erisilebilir bir standart
#: bulunamadi, GK10 geregi erisilemeyen metnin madde numarasi yazilmaz). Sinir, uydurma
#: veri uretmek icin degil AKTARIMI DOGRULAMAK icindir.
Kritiklik = Literal["kritik", "yuksek", "orta", "dusuk"]


class AssetRow(BaseModel):
    """CBS aktarimindaki tek satir.

    GONDERILMEYEN alan DEGISTIRILMEZ: `model_dump(exclude_unset=True)` ile yalnizca
    istemcinin ACIKCA yazdigi alanlar depoya gider. Bir alani temizlemek icin acikca
    `null` gonderilir. Boylece kismi bir CBS aktarimi dolu alanlari silmez.
    """

    pano_id: str
    cbs_kodu: str | None = None
    fider_id: str | None = None
    il: str | None = None
    ilce: str | None = None
    abone_sayisi: int | None = Field(default=None, ge=0)
    trafo_kva: int | None = Field(default=None, ge=0)
    kritiklik: Kritiklik | None = None
    # UYDURULMAZ. Aktarim doldurmadiysa null kalir (backlog F-21 "Dikkat" satiri).
    uretici: str | None = None
    seri_no: str | None = None
    son_bakim_at: datetime | None = None
    sonraki_bakim_at: datetime | None = None


class AssetImport(BaseModel):
    """`kunye_kaynak` ZORUNLUDUR: kaynagi yazilmayan kunye kabul edilmez.

    Kokeni istemci satir basina yazamaz — aktarimin kimligi tektir ve depo katmani onu
    her satira kendisi yazar. Bu, F-19'un "kimlik govdeden okunmaz" ilkesinin ayni
    uygulamasidir: bir alanin dogrulanabilir tek bir kaynagi olmali.
    """

    kunye_kaynak: str = Field(min_length=1)
    panolar: list[AssetRow] = Field(min_length=1)


@router.get("/fleet/assets")
def list_assets(request: Request) -> dict[str, Any]:
    """Filonun kunyesi + kapsama ozeti. Okuma ucudur, belirtec istemez (F-19 sinirlari)."""
    records = request.app.state.store.list_panels()
    return {
        "kapsama": asset_coverage(records),
        "panolar": [
            {"pano_id": record.pano_id, "name": record.name, "asset": asset_view(record)}
            for record in records
        ],
    }


@router.post("/fleet/assets")
def import_assets(
    request: Request,
    body: AssetImport,
    identity: Annotated[Identity, Depends(require("muhendis"))],
) -> dict[str, Any]:
    """CBS aktarimindan kunye ice aktarir. `muhendis` rolu ister (F-19 deseni).

    Varlik kutugunu degistirmek filo genelinde etki ekseni ve F-22'nin fider eslemesi
    demektir; `operator` degil `muhendis` istenmesinin sebebi budur.
    """
    state = request.app.state
    rows = [row.model_dump(exclude_unset=True) for row in body.panolar]
    try:
        updated = state.store.import_assets(rows, kunye_kaynak=body.kunye_kaynak, at=state.clock())
    except UnknownPanel as exc:
        # Bu uc YENI PANO YARATMAZ: pano kaydi telemetriyle dogar, kutuk yalnizca var olan
        # panoyu zenginlestirir. Aktarimin tamami geri alindi.
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    # Denetim izi (alarm_journal) ALARMA baglidir: alarm_id NOT NULL REFERENCES alarms(id)
    # (003_alarms.sql). Kunye aktariminin bagli oldugu bir alarm yoktur, bu yuzden F-20 hash
    # zincirine SAHTE bir alarm satiri uydurulmadi — zincirin anlami bozulurdu. Aktarim
    # bunun yerine kaydin KENDISINDE izlenir: `kunye_kaynak` + `kunye_at` her satirda durur.
    # Kim yaptigi ayrica loglanir; bu bir kurcalama kaniti DEGILDIR ve oyle sunulmuyor.
    log.info(
        "varlik kutugu ice aktarildi: %d pano, kaynak %r, yapan %r",
        updated, body.kunye_kaynak, identity.user,
    )
    return {"guncellenen": updated, "kapsama": asset_coverage(state.store.list_panels())}
