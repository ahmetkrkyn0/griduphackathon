"""F-21 — varlik kutugu: CBS tekil kodu, kunye ve bakim takvimi.

Maddenin OLCULEBILIR iddiasi sudur ve bu dosya onu kilitler:

    Pano artik KIMI ETKILEDIGINI soyleyebiliyor (fider, abone sayisi, kritiklik, bakim
    vadesi) — ama bu bilgi UYDURULMUYOR: yalnizca dogrulanmis bir CBS aktarimindan
    geliyor, kaynagi kaydin icinde duruyor ve ice aktarilmamis alan `null` kaliyor.

Iki kilit ozellikle onemli:
  * test_uretici_ve_seri_no_asla_uydurulmaz — backlog F-21'in "Dikkat" satirini kilitler.
  * test_kunyesiz_pano_null_doner_sifir_degil — "veri yok" ile "deger sifir" ayrimini
    kilitler; ekranin bos hucre gostermesini engelleyen sey budur.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.auth import parse_operators
from app.config import Settings
from app.main import create_app
from fakes import MemoryStore
from helpers import CONTRACTS_DIR, Clock, utc

T0 = utc(2026, 9, 18, 9, 0, 0)

PANELS = [
    {"pano_id": "ADM-00001", "name": "Efeler TM-14"},
    {"pano_id": "ADM-00002", "name": "Nazilli TM-07"},
    {"pano_id": "GDZ-00001", "name": "Bornova TM-22"},
]

IZLEYICI = "izleyici-belirteci"
OPERATOR = "operator-belirteci"
MUHENDIS = "muhendis-belirteci"
OPERATORS = (
    f"nobetci:izleyici:{IZLEYICI},"
    f"vardiya.amiri:operator:{OPERATOR},"
    f"bas.muhendis:muhendis:{MUHENDIS}"
)

# Gercek bir CBS disa aktarimi DEGILDIR: alan adlarini ve ice aktarim yolunu sinamak icin
# yazilmis ornek satirlardir (GK3 — sahadan olculmus veri yok).
AKTARIM = {
    "kunye_kaynak": "ADM CBS disa aktarim 2026-09-18 (ornek)",
    "panolar": [
        {
            "pano_id": "ADM-00001",
            "cbs_kodu": "TR-ADM-DP-000001",
            "fider_id": "F-EFELER-03",
            "il": "Aydin",
            "ilce": "Efeler",
            "abone_sayisi": 412,
            "trafo_kva": 1600,
            "kritiklik": "yuksek",
        },
        {
            "pano_id": "ADM-00002",
            "cbs_kodu": "TR-ADM-DP-000002",
            "fider_id": "F-NAZILLI-01",
            "abone_sayisi": 96,
            "kritiklik": "orta",
        },
    ],
}


@pytest.fixture
def store() -> MemoryStore:
    return MemoryStore(PANELS)


@pytest.fixture
def client(store):
    app = create_app(
        Settings(contracts_dir=CONTRACTS_DIR, ingest_enabled=False, central_detector_enabled=False),
        store=store,
        clock=Clock(T0),
        operators=parse_operators(OPERATORS),
    )
    with TestClient(app) as http:
        yield http


def muhendis(client, body):
    return client.post("/api/v1/fleet/assets", json=body, headers={"Authorization": f"Bearer {MUHENDIS}"})


# ------------------------------------------------------------------ ice aktarim
def test_ice_aktarim_kunyeyi_yazar_ve_kapsamayi_bildirir(client, api_contract):
    response = muhendis(client, AKTARIM)

    assert response.status_code == 200
    assert response.json()["guncellenen"] == 2
    # Kapsama SAYIYLA verilir: uc panonun ikisinin kunyesi var, biri BOS ve bu gizlenmiyor.
    assert response.json()["kapsama"] == {"panolar": 3, "kunyeli": 2, "fiderli": 2, "aboneli": 2}

    fleet = client.get("/api/v1/fleet/assets")
    assert fleet.status_code == 200
    api_contract(fleet.json(), "AssetFleet")


def test_kokeni_istemci_degil_sunucu_yazar(client):
    """`kunye_kaynak` ve `kunye_at` satirdan degil AKTARIMDAN gelir (F-19 ile ayni ilke)."""
    muhendis(client, AKTARIM)

    asset = client.get("/api/v1/panels/ADM-00001").json()["asset"]
    assert asset["kunye_kaynak"] == "ADM CBS disa aktarim 2026-09-18 (ornek)"
    assert asset["kunye_at"] == T0.isoformat()


def test_uretici_ve_seri_no_asla_uydurulmaz(client):
    """Backlog F-21 "Dikkat": uretici/seri no uydurulmaz, BOS BIRAKILIR.

    Aktarim bu iki alani gondermedi; sistem onlari kendiliginden doldurmaz ve bir
    yer tutucu ("bilinmiyor", "-", "") de yazmaz.
    """
    muhendis(client, AKTARIM)

    asset = client.get("/api/v1/panels/ADM-00001").json()["asset"]
    assert asset["uretici"] is None
    assert asset["seri_no"] is None


def test_kunyesiz_pano_null_doner_sifir_degil(client):
    """"Veri yok" ile "deger sifir" ayrimi: kunyesiz pano `asset: null` doner.

    Hepsi null olan bir sozluk donseydi ekranda bos hucre olurdu ve bos hucre
    "abone sayisi 0" gibi okunurdu.
    """
    muhendis(client, AKTARIM)

    detail = client.get("/api/v1/panels/GDZ-00001").json()
    assert detail["asset"] is None

    [summary] = [p for p in client.get("/api/v1/panels").json() if p["pano_id"] == "GDZ-00001"]
    assert summary["abone_sayisi"] is None
    assert summary["kritiklik"] is None
    assert summary["sonraki_bakim_at"] is None


def test_ozet_etki_eksenini_tasir(client):
    """Risk matrisinin etki ekseni filo listesinden okunur; ayri istek gerekmez."""
    muhendis(client, AKTARIM)

    [summary] = [p for p in client.get("/api/v1/panels").json() if p["pano_id"] == "ADM-00001"]
    assert summary["abone_sayisi"] == 412
    assert summary["kritiklik"] == "yuksek"


def test_gonderilmeyen_alan_degistirilmez_acik_null_temizler(client):
    """Kismi aktarim dolu alanlari SILMEZ; temizlemek icin acikca null gonderilir."""
    muhendis(client, AKTARIM)
    muhendis(client, {
        "kunye_kaynak": "kismi guncelleme",
        "panolar": [{"pano_id": "ADM-00001", "abone_sayisi": 500}],
    })

    asset = client.get("/api/v1/panels/ADM-00001").json()["asset"]
    assert asset["abone_sayisi"] == 500
    assert asset["fider_id"] == "F-EFELER-03"      # gonderilmedi -> KORUNDU
    assert asset["kunye_kaynak"] == "kismi guncelleme"

    muhendis(client, {
        "kunye_kaynak": "alan temizleme",
        "panolar": [{"pano_id": "ADM-00001", "fider_id": None}],
    })
    assert client.get("/api/v1/panels/ADM-00001").json()["asset"]["fider_id"] is None


# ------------------------------------------------------------------ dogrulama
def test_bilinmeyen_pano_reddedilir_ve_aktarimin_tamami_geri_alinir(client):
    """Uc YENI PANO YARATMAZ ve yarim ice aktarim birakmaz."""
    response = muhendis(client, {
        "kunye_kaynak": "bozuk aktarim",
        "panolar": [
            {"pano_id": "ADM-00001", "cbs_kodu": "TR-ADM-DP-000001"},
            {"pano_id": "YOK-99999", "cbs_kodu": "TR-ADM-DP-999999"},
        ],
    })

    assert response.status_code == 404
    assert "YOK-99999" in response.json()["detail"]
    # ILK satir da yazilmadi: yarim kutuk, hic kutuk olmamasindan kotudur.
    assert client.get("/api/v1/panels/ADM-00001").json()["asset"] is None
    assert client.get("/api/v1/fleet/assets").json()["kapsama"]["kunyeli"] == 0


def test_kunye_kaynaksiz_aktarim_reddedilir(client):
    """Kaynagi yazilmayan kunye kabul edilmez."""
    assert muhendis(client, {"panolar": [{"pano_id": "ADM-00001"}]}).status_code == 422
    assert muhendis(client, {"kunye_kaynak": "", "panolar": [{"pano_id": "ADM-00001"}]}).status_code == 422


def test_sozluk_disi_kritiklik_reddedilir(client):
    response = muhendis(client, {
        "kunye_kaynak": "k",
        "panolar": [{"pano_id": "ADM-00001", "kritiklik": "cok-kritik"}],
    })
    assert response.status_code == 422


def test_negatif_abone_sayisi_reddedilir(client):
    response = muhendis(client, {
        "kunye_kaynak": "k",
        "panolar": [{"pano_id": "ADM-00001", "abone_sayisi": -1}],
    })
    assert response.status_code == 422


# ------------------------------------------------------------------ rol korumasi
def test_ice_aktarim_muhendis_rolu_ister(client):
    """F-19 deseni: yazma ucu rol ister, okuma ucu istemez."""
    assert client.post("/api/v1/fleet/assets", json=AKTARIM).status_code == 401
    assert client.post(
        "/api/v1/fleet/assets", json=AKTARIM, headers={"Authorization": f"Bearer {OPERATOR}"}
    ).status_code == 403
    assert client.post(
        "/api/v1/fleet/assets", json=AKTARIM, headers={"Authorization": f"Bearer {IZLEYICI}"}
    ).status_code == 403
    assert muhendis(client, AKTARIM).status_code == 200


def test_reddedilen_aktarimin_yan_etkisi_yok(client):
    client.post("/api/v1/fleet/assets", json=AKTARIM, headers={"Authorization": f"Bearer {OPERATOR}"})

    assert client.get("/api/v1/fleet/assets").json()["kapsama"]["kunyeli"] == 0


def test_kutuk_okumasi_belirtec_istemez(client):
    """Okuma uclari acik kalir — F-19'un BEYAN EDILMIS sinirlarindan biri."""
    assert client.get("/api/v1/fleet/assets").status_code == 200


# ------------------------------------------------------------------ bakim vadesi
def test_bakim_vadesi_ozete_girer(client):
    due = (T0 + timedelta(days=30)).isoformat()
    muhendis(client, {
        "kunye_kaynak": "bakim takvimi",
        "panolar": [{"pano_id": "ADM-00001", "sonraki_bakim_at": due}],
    })

    [summary] = [p for p in client.get("/api/v1/panels").json() if p["pano_id"] == "ADM-00001"]
    assert summary["sonraki_bakim_at"] is not None
