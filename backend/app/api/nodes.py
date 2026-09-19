"""Dugum ve sensor kutugu uclari (F-31): GET/POST /api/v1/fleet/nodes.

NE EKSIKTI — ayrimi yapmadan bu uc yazilirsa var olan bir yetenek yeniden insa edilir:
  OLCUM NOKTASI kimligi ZATEN VAR. `t_conn[].pt` donmus semada sabit bir regex'e bagli
  ve kalite bitleri nokta bazinda tutuluyor; docs/05 §10 bir sapmayi nokta ADIYLA
  (DSYA4_L3) teshis edebiliyor. Eksik olan o DEGIL.
  FIZIKSEL DUGUM kimligi YOK. `health` blogu yalnizca nodes_ok / nodes_total SAYILARINI
  tasiyor. "Kac dugum gitti" biliniyor, "HANGI FIZIKSEL PARCA gitti" bilinmiyor.
Bu modulun tek isi ikincisidir.

TELEMETRI SEMASINA DOKUNULMADI. `health` ve `t_conn[]` icin additionalProperties: false
tanimli; kenara dugum kimligi alani acmak mesaji reddettirir ve uc dosyalik donmus
zinciri tetiklerdi. Gerek de yok: eslemeyi kutuk tutar ve "hangi dugum kor" sorusu
MERKEZDE, noktanin kalite bitlerinden YENIDEN TURETILIR (F-10 `_verify` deseni).

"IZLENEBILIR OLCUM" IDDIASI YOKTUR. Metrolojik izlenebilirlik akredite bir kalibrasyon
zinciri ister; bu depoda yok (GK3). Burada yapilan KUTUK VE VADE TAKIBIDIR ve yanit
bunu kendi alan adlariyla soyler.

BOS KUTUK GIZLENMEZ: `GET /fleet/nodes` kapsama oranini SAYIYLA dondurur. Bu teslimde
demo filosunun dugum kutugu BOSTUR ve bu, yanitta acikca gorunur.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..auth import Identity, require
from ..db import UnknownPanel
from .views import point_label

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["nodes"])

# Kalibrasyon vadesine bu kadar gun kala "yaklasiyor" sayilir. TURETILMIS: sozlesmede
# kalibrasyon esigi yoktur ve bu bir alarm degil, planlama rozetidir.
DEFAULT_DUE_WINDOW_DAYS = 30


class NodeRow(BaseModel):
    """Kutuk aktarimindaki tek dugum.

    GONDERILMEYEN alan DEGISTIRILMEZ (`exclude_unset`); bir alani temizlemek icin
    acikca `null` gonderilir. Kismi bir aktarim dolu alanlari silmez — F-21 ile ayni
    kural.

    `points` bir dugumun tasidigi OLCUM NOKTALARIDIR. Cok kanalli sensor kartlari
    birden cok nokta tasir; bir nokta ise tek bir dugume baglidir.
    """

    node_id: str = Field(min_length=1)
    pano_id: str = Field(min_length=1)
    uretici: str | None = None
    model: str | None = None
    # UYDURULMAZ. Aktarim doldurmadiysa null kalir.
    seri_no: str | None = None
    uretim_partisi: str | None = None
    montaj_at: datetime | None = None
    son_kalibrasyon_at: datetime | None = None
    sonraki_kalibrasyon_at: datetime | None = None
    points: list[str] = Field(default_factory=list)


class NodeImport(BaseModel):
    """`kutuk_kaynak` ZORUNLUDUR: kaynagi yazilmayan kutuk kabul edilmez.

    Kokeni istemci satir basina yazamaz — aktarimin kimligi tektir ve depo katmani onu
    her satira kendisi yazar (F-21 ve F-19 ile ayni ilke).
    """

    kutuk_kaynak: str = Field(min_length=1)
    dugumler: list[NodeRow] = Field(min_length=1)


@router.get("/fleet/nodes")
def list_nodes(
    request: Request,
    due_days: int = Query(DEFAULT_DUE_WINDOW_DAYS, ge=1, le=3650),
) -> dict[str, Any]:
    """Dugum kutugu, kapsama orani ve kalibrasyon vadesi. Okuma ucudur, belirtec istemez."""
    state = request.app.state
    now = state.clock()
    nodes = state.store.list_nodes()
    panels = state.store.list_panels()

    kutuklu = {node["pano_id"] for node in nodes}
    vadesi_gecen, vadesi_yaklasan = [], []
    for node in nodes:
        due = node.get("sonraki_kalibrasyon_at")
        if due is None:
            continue
        kalan_gun = (due - now).total_seconds() / 86400.0
        if kalan_gun < 0:
            vadesi_gecen.append(node["node_id"])
        elif kalan_gun <= due_days:
            vadesi_yaklasan.append(node["node_id"])

    return {
        "kapsama": {
            "pano_toplam": len(panels),
            "kutugu_olan_pano": len(kutuklu),
            "dugum_toplam": len(nodes),
            # Seri no'su olmayan dugum sayisi AYRICA verilir: kutuk "var" ama
            # tanimlayici alani bos olabilir ve bu gizlenmemeli.
            "seri_no_bos": sum(1 for node in nodes if not node.get("seri_no")),
            "kalibrasyon_vadesi_bos": sum(
                1 for node in nodes if node.get("sonraki_kalibrasyon_at") is None
            ),
        },
        "kalibrasyon": {
            "pencere_gun": due_days,
            "vadesi_gecen": sorted(vadesi_gecen),
            "vadesi_yaklasan": sorted(vadesi_yaklasan),
        },
        "dugumler": [_node_view(node) for node in nodes],
        # Metrolojik izlenebilirlik IDDIA EDILMIYOR (GK3/GK10).
        "uyari": (
            "Bu kutuk kalibrasyon VADE TAKIBIDIR; akredite bir kalibrasyon zinciri "
            "olmadan 'izlenebilir olcum' iddiasi kurulamaz ve kurulmuyor."
        ),
    }


@router.get("/fleet/nodes/blind")
def blind_nodes(request: Request) -> dict[str, Any]:
    """Hangi FIZIKSEL parca kor: kalite bayragi olan noktalar -> dugum kutugu.

    Bu ucun tamami F-31'in asil sorusudur: bir dugum kayboldugunda hangi fiziksel
    parcanin gittigini soyleyebilmek. `health.nodes_ok` yalnizca SAYI verir; hangi
    parcanin gittigini soylemez.

    KIMLIK SEMADAN GELMEZ, MERKEZDE YENIDEN TURETILIR: kenar zaten nokta basina kalite
    bitlerini (`t_conn[].q`) yayinliyor. Kutuk nokta -> dugum eslemesini tuttugu icin
    "su noktalar bozuk" bilgisi "su fiziksel parca degismeli"ye burada cevrilir. Sema
    `additionalProperties: false` oldugu icin kenara alan acmak mesaji reddettirirdi
    (F-10 `_verify` ile ayni kacis).

    Eslemesi OLMAYAN bozuk nokta gizlenmez: `kutuksuz` listesinde sayiyla doner —
    "esleme yok" ile "sorun yok" ayni sey degildir (GK10).
    """
    state = request.app.state
    mapping = state.store.node_point_map()
    nodes = {node["node_id"]: node for node in state.store.list_nodes()}

    etkilenen: dict[str, dict[str, Any]] = {}
    kutuksuz: list[dict[str, str]] = []
    for record in state.store.list_panel_points():
        for point in (record.payload or {}).get("t_conn") or []:
            if not point.get("q"):
                continue
            name = point["pt"]
            node_id = mapping.get((record.pano_id, name))
            if node_id is None:
                kutuksuz.append({"pano_id": record.pano_id, "point": name})
                continue
            entry = etkilenen.setdefault(
                node_id,
                {"node_id": node_id, **_node_view(nodes.get(node_id, {})), "points": []},
            )
            entry["points"].append({"point": name, "det_label": point_label(name), "q": point["q"]})

    return {
        "kor_dugumler": sorted(etkilenen.values(), key=lambda row: row["node_id"]),
        "kutuksuz_noktalar": kutuksuz,
    }


@router.post("/fleet/nodes")
def import_nodes(
    request: Request,
    body: NodeImport,
    identity: Annotated[Identity, Depends(require("muhendis"))],
) -> dict[str, Any]:
    """Dugum kutugunu ice aktarir. `muhendis` rolu ister (F-19 deseni).

    Kutugu degistirmek "hangi parca degismeli" cevabini degistirir; bu bir bakim
    karari girdisidir ve `operator` degil `muhendis` istenmesinin sebebi budur.
    """
    state = request.app.state
    rows = [row.model_dump(exclude_unset=True) for row in body.dugumler]
    try:
        updated = state.store.import_nodes(rows, kutuk_kaynak=body.kutuk_kaynak, at=state.clock())
    except UnknownPanel as exc:
        # Bu uc YENI PANO YARATMAZ: pano kaydi telemetriyle dogar. Aktarimin tamami geri alindi.
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    # F-20 hash zinciri ALARMA baglidir (alarm_journal.alarm_id NOT NULL). Kutuk aktariminin
    # bagli oldugu bir alarm yoktur ve zincire SAHTE bir alarm satiri uydurulmadi — zincirin
    # anlami bozulurdu. Aktarim kaydin KENDISINDE izlenir: kutuk_kaynak + kutuk_at.
    log.info(
        "dugum kutugu ice aktarildi: %d dugum, kaynak %r, yapan %r",
        updated, body.kutuk_kaynak, identity.user,
    )
    return {"guncellenen": updated}


def _node_view(node: dict) -> dict[str, Any]:
    """Kutuk satirini yanit bicimine cevirir; eksik alan null doner, sifir DEGIL."""
    if not node:
        return {}
    return {
        "node_id": node.get("node_id"),
        "pano_id": node.get("pano_id"),
        "uretici": node.get("uretici"),
        "model": node.get("model"),
        "seri_no": node.get("seri_no"),
        "uretim_partisi": node.get("uretim_partisi"),
        "montaj_at": _iso(node.get("montaj_at")),
        "son_kalibrasyon_at": _iso(node.get("son_kalibrasyon_at")),
        "sonraki_kalibrasyon_at": _iso(node.get("sonraki_kalibrasyon_at")),
        "kutuk_kaynak": node.get("kutuk_kaynak"),
        "kutuk_at": _iso(node.get("kutuk_at")),
    }


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
