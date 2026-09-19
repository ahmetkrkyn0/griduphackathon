"""Dugum ve sensor kutugu (F-31): GET/POST /fleet/nodes, GET /fleet/nodes/blind.

Neyin sinandigi — ayrim kritik:
  OLCUM NOKTASI kimligi ZATEN VARDI (`t_conn[].pt`, nokta bazinda kalite bitleri).
  FIZIKSEL DUGUM kimligi YOKTU: `health` yalnizca nodes_ok / nodes_total SAYILARINI
  tasiyordu. Bu dosya ikincisini kilitler — bir dugum korlestiginde HANGI FIZIKSEL
  PARCANIN degismesi gerektigi soylenebiliyor mu?

Telemetri semasina DOKUNULMADI: dugum kimligi kenardan yayinlanmaz, merkezde nokta
kalite bitlerinden YENIDEN TURETILIR (F-10 `_verify` deseni). Bunu
`test_kor_dugum_telemetriye_alan_eklemeden_bulunur` kilitler.
"""

from __future__ import annotations

import copy
import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.auth import parse_operators
from app.config import Settings
from app.main import create_app
from fakes import MemoryStore
from helpers import CONTRACTS_DIR, Clock, encode, utc

PANELS = [
    {"pano_id": "ADM-00001", "name": "Efeler TM-14"},
    {"pano_id": "ADM-00002", "name": "Nazilli TM-07"},
]
T0 = utc(2026, 9, 13, 10, 0, 0)

TOKENS = {"izleyici": "izleyici-belirteci", "operator": "operator-belirteci", "muhendis": "muhendis-belirteci"}
OPERATORS = (
    f"nobetci:izleyici:{TOKENS['izleyici']},"
    f"vardiya.amiri:operator:{TOKENS['operator']},"
    f"bas.muhendis:muhendis:{TOKENS['muhendis']}"
)

NODE = {
    "node_id": "ND-001",
    "pano_id": "ADM-00001",
    "uretici": "Rittal",
    "model": "CMC III",
    "seri_no": "SN-4471",
    "uretim_partisi": "B-2026-03",
    "sonraki_kalibrasyon_at": (T0 + timedelta(days=10)).isoformat(),
    "points": ["DSYA3_L2", "GIRIS_L2"],
}


class Rig:
    def __init__(self) -> None:
        self.store = MemoryStore(PANELS)
        self.clock = Clock(T0)
        self.app = create_app(
            Settings(contracts_dir=CONTRACTS_DIR, ingest_enabled=False, central_detector_enabled=False),
            store=self.store,
            clock=self.clock,
        )
        self.http = TestClient(self.app)

    def ingest(self, payload: dict) -> None:
        self.app.state.pipeline.handle_message(
            f"gridup/pano/{payload['pano_id']}/tel", encode(payload)
        )
        assert self.app.state.pipeline.flush()
        assert not self.store.quarantined, self.store.quarantined


@pytest.fixture
def rig():
    rig = Rig()
    with rig.http:
        yield rig


def _import(rig: Rig, dugumler=None, kaynak: str = "saha-envanteri-2026-09"):
    return rig.http.post(
        "/api/v1/fleet/nodes",
        json={"kutuk_kaynak": kaynak, "dugumler": dugumler or [NODE]},
    )


# ------------------------------------------------------------------ ice aktarim


def test_kutuk_ice_aktarilir_ve_okunur(rig, api_contract):
    assert _import(rig).json() == {"guncellenen": 1}
    body = rig.http.get("/api/v1/fleet/nodes").json()
    api_contract(body, "NodeFleet")

    assert body["kapsama"]["dugum_toplam"] == 1
    assert body["kapsama"]["kutugu_olan_pano"] == 1
    assert body["kapsama"]["pano_toplam"] == 2
    node = body["dugumler"][0]
    assert (node["node_id"], node["seri_no"], node["uretim_partisi"]) == ("ND-001", "SN-4471", "B-2026-03")
    assert node["kutuk_kaynak"] == "saha-envanteri-2026-09"


def test_kaynagi_olmayan_kutuk_reddedilir(rig):
    """Kaynagi yazilmayan kutuk kabul edilmez (F-21 ile ayni kural)."""
    response = rig.http.post("/api/v1/fleet/nodes", json={"kutuk_kaynak": "", "dugumler": [NODE]})
    assert response.status_code == 422


def test_taninmayan_pano_reddedilir_ve_aktarimin_tamami_geri_alinir(rig):
    """Bu uc YENI PANO YARATMAZ; pano kaydi telemetriyle dogar.

    Ikinci satir bozuk oldugu icin BIRINCI satir da yazilmamali — yarim ice aktarilmis
    bir kutuk, hic ice aktarilmamis olandan daha kotudur.
    """
    bad = {**NODE, "node_id": "ND-002", "pano_id": "YOK-00009"}
    assert _import(rig, [NODE, bad]).status_code == 404
    assert rig.http.get("/api/v1/fleet/nodes").json()["kapsama"]["dugum_toplam"] == 0


def test_gonderilmeyen_alan_degistirilmez(rig):
    """Kismi bir aktarim dolu alanlari silmemeli."""
    _import(rig)
    _import(rig, [{"node_id": "ND-001", "pano_id": "ADM-00001", "model": "CMC III PU"}])
    node = rig.http.get("/api/v1/fleet/nodes").json()["dugumler"][0]
    assert node["model"] == "CMC III PU"
    assert node["seri_no"] == "SN-4471"  # dokunulmadi


def test_seri_no_uydurulmaz(rig):
    """Aktarim doldurmadiysa null kalir ve bu kapsama sayisinda GORUNUR."""
    _import(rig, [{"node_id": "ND-009", "pano_id": "ADM-00002"}])
    body = rig.http.get("/api/v1/fleet/nodes").json()
    assert body["dugumler"][0]["seri_no"] is None
    assert body["kapsama"]["seri_no_bos"] == 1
    assert body["kapsama"]["kalibrasyon_vadesi_bos"] == 1


@pytest.mark.parametrize(
    ("rol", "beklenen"),
    [("izleyici", 403), ("operator", 403), ("muhendis", 200)],
)
def test_yazma_muhendis_rolu_ister(rol, beklenen):
    """F-19 deseni; roller izleyici < operator < muhendis.

    Kutugu degistirmek "hangi parca degismeli" cevabini degistirir — bu bir bakim
    karari girdisidir, bu yuzden `operator` YETMEZ.
    """
    app = create_app(
        Settings(contracts_dir=CONTRACTS_DIR, ingest_enabled=False, central_detector_enabled=False),
        store=MemoryStore(PANELS),
        clock=Clock(T0),
        operators=parse_operators(OPERATORS),
    )
    with TestClient(app) as http:
        response = http.post(
            "/api/v1/fleet/nodes",
            json={"kutuk_kaynak": "saha-envanteri", "dugumler": [NODE]},
            headers={"Authorization": f"Bearer {TOKENS[rol]}"},
        )
    assert response.status_code == beklenen


def test_belirtecsiz_yazma_reddedilir():
    app = create_app(
        Settings(contracts_dir=CONTRACTS_DIR, ingest_enabled=False, central_detector_enabled=False),
        store=MemoryStore(PANELS),
        clock=Clock(T0),
        operators=parse_operators(OPERATORS),
    )
    with TestClient(app) as http:
        response = http.post(
            "/api/v1/fleet/nodes", json={"kutuk_kaynak": "x", "dugumler": [NODE]}
        )
    assert response.status_code == 401


# ------------------------------------------------- kalibrasyon vadesi (izlenebilirlik DEGIL)


def test_kalibrasyon_vadesi_gecen_ve_yaklasan_ayrilir(rig, api_contract):
    gecmis = {"node_id": "ND-010", "pano_id": "ADM-00001",
              "sonraki_kalibrasyon_at": (T0 - timedelta(days=1)).isoformat()}
    uzak = {"node_id": "ND-011", "pano_id": "ADM-00001",
            "sonraki_kalibrasyon_at": (T0 + timedelta(days=200)).isoformat()}
    _import(rig, [NODE, gecmis, uzak])

    body = rig.http.get("/api/v1/fleet/nodes").json()
    api_contract(body, "NodeFleet")
    assert body["kalibrasyon"]["vadesi_gecen"] == ["ND-010"]
    assert body["kalibrasyon"]["vadesi_yaklasan"] == ["ND-001"]  # 10 gun < 30 gun penceresi


def test_izlenebilir_olcum_iddiasi_kurulmaz(rig):
    """Metrolojik izlenebilirlik akredite kalibrasyon ister (GK3). Yanit bunu soyler
    ve sertifika numarasi alani BILEREK acilmadi.
    """
    body = rig.http.get("/api/v1/fleet/nodes").json()
    assert "izlenebilir olcum" in body["uyari"]
    _import(rig)
    assert "sertifika" not in str(rig.http.get("/api/v1/fleet/nodes").json())


# --------------------------------------------------- hangi fiziksel parca kor


def test_kor_dugum_telemetriye_alan_eklemeden_bulunur(rig, tel_payload, api_contract):
    """F-31'in ASIL sorusu: bir dugum korlestiginde hangi parca degismeli?

    Telemetri dugum kimligi TASIMAZ ve tasimasi da gerekmez: kenar zaten nokta basina
    kalite bitlerini yayinliyor (`t_conn[].q`), kutuk nokta -> dugum eslemesini tutuyor.
    Merkez ikisini birlestirip fiziksel parcayi adlandiriyor.
    """
    _import(rig)
    payload = copy.deepcopy(tel_payload)
    payload["pano_id"] = "ADM-00001"
    payload["ts"] = T0.isoformat()
    for point in payload["t_conn"]:
        point["q"] = 4 if point["pt"] == "DSYA3_L2" else 0
    rig.ingest(payload)

    body = rig.http.get("/api/v1/fleet/nodes/blind").json()
    api_contract(body, "BlindNodes")

    assert len(body["kor_dugumler"]) == 1
    kor = body["kor_dugumler"][0]
    # Yalnizca "bir dugum gitti" degil, HANGI parca oldugu:
    assert (kor["node_id"], kor["seri_no"], kor["uretim_partisi"]) == ("ND-001", "SN-4471", "B-2026-03")
    assert [p["point"] for p in kor["points"]] == ["DSYA3_L2"]
    assert body["kutuksuz_noktalar"] == []

    # Kimlik TELEMETRIDEN GELMEDI: kutuktaki seri no yukun hicbir yerinde gecmiyor.
    # `health` yalnizca nodes_ok / nodes_total SAYILARINI tasiyor.
    assert "SN-4471" not in json.dumps(payload)
    assert set(payload["health"]) >= {"nodes_ok", "nodes_total"}


def test_eslemesi_olmayan_bozuk_nokta_gizlenmez(rig, tel_payload, api_contract):
    """"Esleme yok" ile "sorun yok" ayni sey degildir (GK10)."""
    payload = copy.deepcopy(tel_payload)
    payload["pano_id"] = "ADM-00001"
    payload["ts"] = T0.isoformat()
    for point in payload["t_conn"]:
        point["q"] = 4 if point["pt"] == "GIRIS_L1" else 0
    rig.ingest(payload)

    body = rig.http.get("/api/v1/fleet/nodes/blind").json()
    api_contract(body, "BlindNodes")
    assert body["kor_dugumler"] == []
    assert body["kutuksuz_noktalar"] == [{"pano_id": "ADM-00001", "point": "GIRIS_L1"}]


def test_temiz_filoda_kor_dugum_yok(rig, tel_payload):
    _import(rig)
    payload = copy.deepcopy(tel_payload)
    payload["pano_id"] = "ADM-00001"
    payload["ts"] = T0.isoformat()
    for point in payload["t_conn"]:
        point["q"] = 0
    rig.ingest(payload)
    body = rig.http.get("/api/v1/fleet/nodes/blind").json()
    assert body["kor_dugumler"] == []
    assert body["kutuksuz_noktalar"] == []


def test_nokta_eslemesi_tamamen_degistirilir(rig, tel_payload):
    """Kart degisince eski kartin noktalari yeni kayitta KALMAMALI."""
    _import(rig)
    _import(rig, [{**NODE, "points": ["GIRIS_L3"]}])

    payload = copy.deepcopy(tel_payload)
    payload["pano_id"] = "ADM-00001"
    payload["ts"] = T0.isoformat()
    for point in payload["t_conn"]:
        point["q"] = 4 if point["pt"] == "DSYA3_L2" else 0
    rig.ingest(payload)

    body = rig.http.get("/api/v1/fleet/nodes/blind").json()
    assert body["kor_dugumler"] == []
    assert body["kutuksuz_noktalar"] == [{"pano_id": "ADM-00001", "point": "DSYA3_L2"}]


def test_bos_kutuk_kapsama_sayisiyla_gorunur(rig, api_contract):
    """Bu teslimde demo filosunun dugum kutugu BOSTUR ve bu gizlenmiyor (GK3)."""
    body = rig.http.get("/api/v1/fleet/nodes").json()
    api_contract(body, "NodeFleet")
    assert body["kapsama"]["dugum_toplam"] == 0
    assert body["kapsama"]["kutugu_olan_pano"] == 0
    assert body["dugumler"] == []
