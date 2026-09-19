"""F-22 — ust sebeke kesintisi bagintisi.

Maddenin OLCULEBILIR iddiasi sudur ve bu dosya onu kilitler:

    Ayni FIDERDEKI panolarin es zamanli susmasi artik N ayri ariza degil TEK bir kesinti
    olayidir — ama TEK PANOLU durumda eski davranis BIREBIR korunur ve hicbir alarm
    bastirilmaz.

En onemli iki kilit:
  * test_tek_pano_susunca_eski_davranis_aynen_korunur — backlog "Dikkat" satirinin sarti.
  * test_baginti_hicbir_alarmi_bastirmaz — baginti TOPLAYICIDIR, susturucu degil.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.outage import SilentPanel, correlate
from fakes import MemoryStore
from helpers import CONTRACTS_DIR, Clock, utc

T0 = utc(2026, 9, 18, 9, 0, 0)
WINDOW = timedelta(minutes=2)


def silent(pano_id: str, minutes_ago: float, fider: str | None = "F-1", abone: int | None = None):
    return SilentPanel(
        pano_id=pano_id,
        last_rx=T0 - timedelta(minutes=minutes_ago),
        fider_id=fider,
        name=pano_id,
        abone_sayisi=abone,
    )


# ====================================================== saf baginti (app/outage.py)
def test_ayni_fiderde_es_zamanli_susan_panolar_tek_olay_olur():
    groups = correlate(
        [silent("A", 10), silent("B", 10.5), silent("C", 11)],
        min_panels=3,
        window=WINDOW,
    )

    assert len(groups) == 1
    assert groups[0].fider_id == "F-1"
    assert [p.pano_id for p in groups[0].panels] == ["A", "B", "C"]
    # Baslangic: kumedeki EN GEC son veri — kesilme aninin olculebilen en iyi yaklasimi.
    assert groups[0].started_at == T0 - timedelta(minutes=10)


def test_tek_pano_susunca_eski_davranis_aynen_korunur():
    """Backlog "Dikkat": tek panolu durumda eski davranis korunmali.

    Esik 3 oldugu icin tek pano (ve iki pano) HICBIR ZAMAN kesinti olayi dogurmaz;
    cagiran taraftaki ALM-COMMS-LOST dongusu bugunku gibi calisir.
    """
    assert correlate([silent("A", 10)], min_panels=3, window=WINDOW) == []
    assert correlate([silent("A", 10), silent("B", 10)], min_panels=3, window=WINDOW) == []


def test_farkli_fiderler_ayri_olaylardir():
    groups = correlate(
        [silent("A", 10, "F-1"), silent("B", 10, "F-1"), silent("C", 10, "F-1"),
         silent("D", 10, "F-2"), silent("E", 10, "F-2"), silent("F", 10, "F-2")],
        min_panels=3,
        window=WINDOW,
    )

    assert {g.fider_id for g in groups} == {"F-1", "F-2"}
    assert len(groups) == 2


def test_fideri_bilinmeyen_pano_GRUPLANMAZ():
    """Kunyesi olmayan pano baginti disinda kalir.

    "Ayni anda sustular, oyleyse ayni fiderdedirler" demek, olcmedigimiz bir topolojiyi
    uydurmak olurdu (GK10). F-21 kunyesi girilmemisse baginti kurulmaz.
    """
    groups = correlate(
        [silent("A", 10, None), silent("B", 10, None), silent("C", 10, None)],
        min_panels=3,
        window=WINDOW,
    )

    assert groups == []


def test_pencere_disinda_susanlar_ayni_olaya_toplanmaz():
    """Gun boyunca teker teker susan panolar tek kesinti sayilmaz — es zamanlilik aranir."""
    groups = correlate(
        [silent("A", 300), silent("B", 200), silent("C", 100)],
        min_panels=3,
        window=WINDOW,
    )

    assert groups == []


def test_kimlik_turetilmistir_ve_ayni_kesinti_icin_ayni_kalir():
    """Zamanlayici her tik'te ayni kesintiyi yeniden tespit eder; kimlik degismemeli."""
    args = dict(min_panels=3, window=WINDOW)
    once = correlate([silent("A", 10), silent("B", 10), silent("C", 11)], **args)
    yine = correlate([silent("C", 11), silent("A", 10), silent("B", 10)], **args)

    assert once[0].outage_id == yine[0].outage_id
    assert once[0].outage_id.startswith("OUT-F-1-")
    assert once[0].outage_id.endswith("Z")  # UTC'ye normalize; makine saat dilimine bagli degil


def test_abone_toplami_yalnizca_bilinenleri_toplar_ve_eksigi_sayar():
    """EPDK Madde 8/2 "etkilenen kullanici sayisi" — bilinmeyen SIFIR sayilmaz."""
    [group] = correlate(
        [silent("A", 10, abone=100), silent("B", 10, abone=50), silent("C", 10, abone=None)],
        min_panels=3,
        window=WINDOW,
    )

    assert group.abone_toplami == 150
    assert group.abone_eksik == 1


def test_hicbir_kunye_yoksa_abone_toplami_NULL_doner_sifir_degil():
    [group] = correlate(
        [silent("A", 10), silent("B", 10), silent("C", 10)],
        min_panels=3,
        window=WINDOW,
    )

    assert group.abone_toplami is None
    assert group.abone_eksik == 3


# ====================================================== uctan uca (alarm servisi + API)
PANELS = [
    {"pano_id": "ADM-00001", "name": "Efeler TM-14", "fider_id": "F-EFELER-03",
     "cbs_kodu": "TR-1", "abone_sayisi": 400},
    {"pano_id": "ADM-00002", "name": "Nazilli TM-07", "fider_id": "F-EFELER-03",
     "cbs_kodu": "TR-2", "abone_sayisi": 100},
    {"pano_id": "GDZ-00001", "name": "Bornova TM-22", "fider_id": "F-EFELER-03",
     "cbs_kodu": "TR-3", "abone_sayisi": None},
]


@pytest.fixture
def rig():
    store = MemoryStore(PANELS)
    clock = Clock(T0)
    app = create_app(
        Settings(contracts_dir=CONTRACTS_DIR, ingest_enabled=False, central_detector_enabled=False),
        store=store,
        clock=clock,
    )
    with TestClient(app) as http:
        yield http, app, store, clock


def _sustur(app, store, clock, pano_ids, *, after_min=30):
    """Verilen panolari susmus gosterip bir tik attirir."""
    service = app.state.alarms
    service.load()
    for pano_id in pano_ids:
        service._last_rx[pano_id] = T0
    clock.now = T0 + timedelta(minutes=after_min)
    service.tick()


def test_uc_pano_susunca_tek_kesinti_olayi_acilir(rig, api_contract):
    http, app, store, clock = rig
    _sustur(app, store, clock, ["ADM-00001", "ADM-00002", "GDZ-00001"])

    body = http.get("/api/v1/outages").json()

    assert len(body) == 1
    api_contract(body, "OutageEvent", many=True)
    assert body[0]["fider_id"] == "F-EFELER-03"
    assert body[0]["state"] == "acik"
    assert {p["pano_id"] for p in body[0]["panolar"]} == {"ADM-00001", "ADM-00002", "GDZ-00001"}
    # Kunyesi olan iki pano toplanir, ucuncusu EKSIK olarak sayilir — sifir yazilmaz.
    assert body[0]["abone_toplami"] == 500
    assert body[0]["abone_eksik"] == 1


def test_tik_tekrarlaninca_ikinci_kesinti_kaydi_acilmaz(rig):
    """Kimlik turetilmis oldugu icin yazma kendiliginden fikirlidir."""
    http, app, store, clock = rig
    _sustur(app, store, clock, ["ADM-00001", "ADM-00002", "GDZ-00001"])
    app.state.alarms.tick()
    app.state.alarms.tick()

    assert len(http.get("/api/v1/outages").json()) == 1


def test_baginti_hicbir_alarmi_bastirmaz(rig):
    """Baginti TOPLAYICIDIR, susturucu degil: her pano kendi ALM-COMMS-LOST'unu alir."""
    http, app, store, clock = rig
    _sustur(app, store, clock, ["ADM-00001", "ADM-00002", "GDZ-00001"])

    alarms = http.get("/api/v1/alarms?state=active").json()
    comms = [a for a in alarms if a["code"] == "ALM-COMMS-LOST"]

    assert {a["pano_id"] for a in comms} == {"ADM-00001", "ADM-00002", "GDZ-00001"}
    # ...ve hepsi ayni kesintiye BAGLANMIS olur.
    assert {a.get("outage_id") for a in comms} == {http.get("/api/v1/outages").json()[0]["outage_id"]}


def test_tek_pano_susunca_kesinti_acilmaz_ama_alarm_yine_uretilir(rig):
    """Eski davranisin uctan uca regresyonu."""
    http, app, store, clock = rig
    _sustur(app, store, clock, ["ADM-00001"])

    assert http.get("/api/v1/outages").json() == []
    alarms = [a for a in http.get("/api/v1/alarms?state=active").json() if a["code"] == "ALM-COMMS-LOST"]
    assert [a["pano_id"] for a in alarms] == ["ADM-00001"]
    assert "outage_id" not in alarms[0]


def test_haberlesme_donunce_kesinti_kapanir(rig):
    http, app, store, clock = rig
    _sustur(app, store, clock, ["ADM-00001", "ADM-00002", "GDZ-00001"])
    service = app.state.alarms

    donus = clock() + timedelta(minutes=1)
    for pano_id in ("ADM-00001", "ADM-00002", "GDZ-00001"):
        service._last_rx[pano_id] = donus
    clock.now = donus + timedelta(seconds=5)
    service.tick()

    assert http.get("/api/v1/outages").json() == []            # acik kesinti kalmadi
    hepsi = http.get("/api/v1/outages?state=hepsi").json()
    assert hepsi[0]["state"] == "kapandi"
    assert hepsi[0]["ended_at"] is not None


def test_kesinti_bulunamazsa_404(rig):
    http, _, _, _ = rig
    assert http.get("/api/v1/outages/OUT-YOK-20260918T090000Z").status_code == 404


def test_kunyesiz_filoda_baginti_hic_tetiklenmez(api_contract):
    """Demo veritabaninda kunye BOS oldugu icin kesinti olayi hic acilmaz — gizlenmiyor."""
    store = MemoryStore([{"pano_id": "ADM-00001", "name": "A"}, {"pano_id": "ADM-00002", "name": "B"},
                         {"pano_id": "GDZ-00001", "name": "C"}])
    clock = Clock(T0)
    app = create_app(
        Settings(contracts_dir=CONTRACTS_DIR, ingest_enabled=False, central_detector_enabled=False),
        store=store, clock=clock,
    )
    with TestClient(app) as http:
        _sustur(app, store, clock, ["ADM-00001", "ADM-00002", "GDZ-00001"])
        assert http.get("/api/v1/outages").json() == []


def test_esikler_sozlesmeden_okunur(contracts):
    """Esik koda GOMULMEZ (PLAN.md kural 10); test de sayiyi tekrar yazmaz."""
    assert contracts.thresholds["outage_min_panels"] >= 2   # tek panolu durum korunur
    assert contracts.thresholds["outage_window_min"] > 0
