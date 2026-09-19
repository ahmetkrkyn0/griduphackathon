"""F-23 — EPDK Kalite Yonetmeligi Madde 8 kesinti kaydi TASLAGI.

Maddenin OLCULEBILIR iddiasi sudur ve bu dosya onu kilitler:

    Kesinti olayi artik mevzuatin saydigi alanlarla doldurulmus bir TASLAGA ceviriliyor —
    ama OLCMEDIGIMIZ hicbir alan doldurulmuyor, sebep ve sinif ONERI olarak kaliyor ve
    cikti her yerinde TASLAK diyor.

En onemli uc kilit:
  * test_sona_erme_ve_sure_ASLA_doldurulmaz — restorasyon ani olculmuyor.
  * test_sebep_ve_sinif_ONERI_olarak_kalir — karar degil, oneri.
  * test_kunyesiz_kesintide_yer_ve_kullanici_elle_doldurulacaga_duser — uydurulmaz.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.epdk import ELLE, OLCULEN, ONERI
from app.main import create_app
from fakes import MemoryStore
from helpers import CONTRACTS_DIR, Clock, utc

T0 = utc(2026, 9, 18, 9, 0, 0)

KUNYELI = [
    {"pano_id": "ADM-00001", "name": "Efeler TM-14", "fider_id": "F-EFELER-03",
     "cbs_kodu": "TR-ADM-DP-000001", "il": "Aydin", "ilce": "Efeler", "abone_sayisi": 400},
    {"pano_id": "ADM-00002", "name": "Nazilli TM-07", "fider_id": "F-EFELER-03",
     "cbs_kodu": "TR-ADM-DP-000002", "il": "Aydin", "ilce": "Nazilli", "abone_sayisi": 100},
    {"pano_id": "GDZ-00001", "name": "Bornova TM-22", "fider_id": "F-EFELER-03",
     "cbs_kodu": "TR-GDZ-DP-000001", "il": "Izmir", "ilce": "Bornova", "abone_sayisi": None},
]

# Ayni filo, ama HICBIR panonun kunyesi ice aktarilmamis — yalnizca fider var ki baginti
# kurulabilsin. Bu, "alan uydurulmaz" kuralinin sinandigi durumdur.
KUNYESIZ = [
    {"pano_id": "ADM-00001", "name": "Efeler TM-14", "fider_id": "F-EFELER-03"},
    {"pano_id": "ADM-00002", "name": "Nazilli TM-07", "fider_id": "F-EFELER-03"},
    {"pano_id": "GDZ-00001", "name": "Bornova TM-22", "fider_id": "F-EFELER-03"},
]


def _kur(panels):
    store = MemoryStore(panels)
    clock = Clock(T0)
    app = create_app(
        Settings(contracts_dir=CONTRACTS_DIR, ingest_enabled=False, central_detector_enabled=False),
        store=store, clock=clock,
    )
    return store, clock, app


def _kesinti(app, clock, pano_ids):
    service = app.state.alarms
    service.load()
    for pano_id in pano_ids:
        service._last_rx[pano_id] = T0
    clock.now = T0 + timedelta(minutes=30)
    service.tick()


@pytest.fixture
def taslak(api_contract):
    store, clock, app = _kur(KUNYELI)
    with TestClient(app) as http:
        _kesinti(app, clock, ["ADM-00001", "ADM-00002", "GDZ-00001"])
        outage_id = http.get("/api/v1/outages").json()[0]["outage_id"]
        body = http.get(f"/api/v1/outages/{outage_id}/epdk-kaydi").json()
        api_contract(body, "EpdkKaydi")
        yield body, http


def alan(body, ad_parcasi: str) -> dict:
    return next(a for a in body["alanlar"] if ad_parcasi.lower() in a["ad"].lower())


# ------------------------------------------------------------------ TASLAK etiketi
def test_cikti_her_yerinde_TASLAK_der(taslak):
    body, _ = taslak

    assert body["taslak"] is True
    assert "TASLAK" in body["uyari"]
    assert "olculmemekte" in body["uyari"].lower() or "olcul" in body["uyari"].lower()


def test_madde8in_on_alani_da_bulunur(taslak):
    """Alan yanittan HICBIR ZAMAN dusurulmez — olcmedigimiz alan da listede durur.

    ON madde, ON BIR alan: mevzuat "baslama/sona erme"yi TEK kalem sayar ama biz IKIYE
    ayirdik, cunku ikisinin DURUMU farkli — baslama olculuyor (yaklasim olarak), sona erme
    OLCULMUYOR. Tek alanda birlestirmek, olculen bir degeri olculmeyenle ayni kefeye
    koyardi ve taslagin butun anlami o ayrimda.
    """
    body, _ = taslak

    assert body["ozet"]["toplam"] == 11
    assert len(body["alanlar"]) == 11
    # Mevzuatin saydigi on alan (backlog §2.1'de birebir dogrulandi).
    adlar = " | ".join(a["ad"].lower() for a in body["alanlar"])
    for beklenen in ("numara", "kademe", "yer", "neden", "sinif", "baslama",
                     "sona erme", "sure", "kullanici", "dagitilmayan enerji"):
        assert beklenen in adlar, beklenen


def test_her_alan_durumunu_ve_gerekcesini_tasir(taslak):
    body, _ = taslak

    for a in body["alanlar"]:
        assert a["durum"] in (OLCULEN, ONERI, ELLE)
        # Olcmedigimiz alan NEDEN olcemedigimizi yazmak zorunda.
        if a["durum"] == ELLE:
            assert a["aciklama"].strip(), a["ad"]
            assert a["deger"] is None, a["ad"]


def test_ozet_kac_alanin_olculdugunu_SAYIYLA_verir(taslak):
    body, _ = taslak
    ozet = body["ozet"]

    assert ozet["olculen"] + ozet["oneri"] + ozet["elle_doldurulacak"] == ozet["toplam"]
    assert ozet["olculen"] == 3      # yer, baslama, etkilenen kullanici
    assert ozet["oneri"] == 2        # neden, sinif
    assert ozet["elle_doldurulacak"] == 6


# --------------------------------------------------- olcmediklerimiz doldurulmaz
def test_sona_erme_ve_sure_ASLA_doldurulmaz(taslak):
    """Maddenin en onemli durustluk siniri: restorasyon ani OLCULMUYOR.

    Elimizdeki tek sey haberlesmenin donusudur ve o da histerezislidir — enerji donusu
    degildir. Sona erme olmayinca sure, toplam etkilenme suresi ve dagitilmayan enerji de
    uretilemez.
    """
    body, _ = taslak

    for ad in ("sona erme", "kesinti suresi", "toplam etkilenme", "dagitilmayan enerji"):
        a = alan(body, ad)
        assert a["durum"] == ELLE, ad
        assert a["deger"] is None, ad

    assert "histerezis" in alan(body, "sona erme")["aciklama"].lower()


def test_sebep_ve_sinif_ONERI_olarak_kalir(taslak):
    """Backlog "Dikkat": sebep sinifi ONERI, karar degil."""
    body, _ = taslak

    for ad in ("neden", "sinif"):
        a = alan(body, ad)
        assert a["durum"] == ONERI, ad
        assert "ONERIDIR" in a["aciklama"] and "KARAR DEGILDIR" in a["aciklama"], ad


def test_sebep_hava_agac_hayvan_gibi_bir_sey_TAHMIN_ETMEZ(taslak):
    body, _ = taslak
    deger = alan(body, "neden")["deger"].lower()

    for uydurma in ("hava", "agac", "hayvan", "kazi", "yildirim", "firtina"):
        assert uydurma not in deger


def test_tazminat_alani_YOKTUR(taslak):
    """GK10: formul parametrelidir, SBSURE literal bir tutar degildir."""
    body, _ = taslak
    metin = " ".join(a["ad"].lower() for a in body["alanlar"])

    assert "tazminat" not in metin
    assert "otmsure" not in metin


# ------------------------------------------------------------------ olculenler
def test_yer_alani_CBS_tekil_kodunu_tasir(taslak):
    """Madde 8/2 "yer" alanindaki tekil sebeke unsuru kodu F-21 kunyesinden gelir."""
    body, _ = taslak
    a = alan(body, "yer")

    assert a["durum"] == OLCULEN
    assert "TR-ADM-DP-000001" in a["deger"]
    assert "Efeler" in a["deger"]


def test_etkilenen_kullanici_eksigi_GIZLEMEZ(taslak):
    body, _ = taslak
    a = alan(body, "kullanici")

    assert a["durum"] == OLCULEN
    assert a["deger"] == 500                       # 400 + 100; ucuncu panonun kunyesi yok
    assert "EKSIKTIR" in a["aciklama"]             # eksiklik yazili


def test_baslama_bir_YAKLASIM_oldugunu_soyler(taslak):
    body, _ = taslak
    a = alan(body, "baslama")

    assert a["durum"] == OLCULEN
    assert a["deger"] is not None
    assert "yaklasim" in a["aciklama"].lower()


# ------------------------------------------------------- kunye yoksa uydurulmaz
def test_kunyesiz_kesintide_yer_ve_kullanici_elle_doldurulacaga_duser(api_contract):
    store, clock, app = _kur(KUNYESIZ)
    with TestClient(app) as http:
        _kesinti(app, clock, ["ADM-00001", "ADM-00002", "GDZ-00001"])
        outage_id = http.get("/api/v1/outages").json()[0]["outage_id"]
        body = http.get(f"/api/v1/outages/{outage_id}/epdk-kaydi").json()
        api_contract(body, "EpdkKaydi")

        assert alan(body, "yer")["durum"] == ELLE
        assert alan(body, "yer")["deger"] is None
        assert alan(body, "kullanici")["durum"] == ELLE
        # SIFIR YAZILMAZ: "abone yok" ile "abone sayisini bilmiyoruz" ayni sey degildir.
        assert alan(body, "kullanici")["deger"] is None
        assert body["ozet"]["olculen"] == 1        # yalnizca baslama


# ------------------------------------------------------------------ kanit paketi
def test_kanit_var_olan_kara_kutuya_baglanir_yeni_cizelge_uretilmez(taslak):
    """F-02 penceresini 336 saate cikardi; F-23 o cizelgeyi YENIDEN YAPMAZ, baglar."""
    body, http = taslak

    assert len(body["kanit"]) == 3
    bagli = [k for k in body["kanit"] if k["event_id"]]
    assert bagli, "kesinti alarmlarinin olay kaydi bekleniyordu"
    for k in bagli:
        assert k["blackbox"] == f"/api/v1/events/{k['event_id']}/blackbox"
        # Baglanti GERCEKTEN calisir: uc var olan kara kutuyu dondurur.
        assert http.get(k["blackbox"]).status_code == 200


def test_bulunamayan_kesinti_icin_404(taslak):
    _, http = taslak
    assert http.get("/api/v1/outages/OUT-YOK-20260918T090000Z/epdk-kaydi").status_code == 404
