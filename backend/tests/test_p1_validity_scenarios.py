"""P1 kabul senaryolari — INOVASYON-UYGULAMA-PLANI.md #4 "Kabul senaryolari" tablosunun
birebir kodu. Bu dosya PLANIN KENDISI degisirse guncellenir; baska hicbir yerden import
edilmez (tamami uctan uca dogrulama, bkz. "Teslim kapisi": bu senaryolar gecmeden yeni
demo surumune alinmaz).

`ingest()` test_api_panels.py:26'daki ile AYNI govdedir — orada da paylasilan bir
helpers.py fonksiyonu degil, o dosyaya ozel bir yerel yardimcidir (helpers.py yalnizca
dusuk seviyeli `encode(payload) -> bytes` ve `utc(y, m, d, h, mi, s) -> datetime` tasir);
bu yuzden burada da yerel olarak tanimlanir, ithal edilmez."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.config import Settings
from app.ingest import IngestPipeline
from app.main import create_app
from fakes import MemoryStore
from helpers import CONTRACTS_DIR, encode, utc

PANELS = [{"pano_id": "ADM-00001", "name": "Test Pano", "lat": 37.8450, "lon": 27.8396}]  # test_api_panels.py PANELS ile ayni sekil (4 anahtar)
NOW = utc(2026, 9, 18, 12, 0, 0)


def ingest(contracts, store, payload: dict, received_at: datetime) -> None:
    pipeline = IngestPipeline(contracts, store, clock=lambda: received_at)
    pipeline.handle_message(f"gridup/pano/{payload['pano_id']}/tel", encode(payload))
    assert pipeline.flush()


def _ingest_and_get_point(contracts, tel_payload, overrides: dict) -> dict:
    point = tel_payload["t_conn"][0]
    point.update(overrides.get("point", {}))
    if "baseline_day" in overrides:
        tel_payload["health"]["baseline_day"] = overrides["baseline_day"]
    store = MemoryStore(PANELS)
    ingest(contracts, store, tel_payload, received_at=NOW)
    app = create_app(Settings(contracts_dir=CONTRACTS_DIR, ingest_enabled=False), store=store, clock=lambda: NOW)
    with TestClient(app) as client:
        return client.get("/api/v1/panels/ADM-00001").json()["points"][0]


def test_healthy_measurement_still_learning_shows_no_unverified_duration(contracts, tel_payload):
    """Satir 1: Saglikli olcum, ogrenme tamamlanmamis -> Ogrenme bilgisi; dogrulanmamis
    sure tahmini yok."""
    point = _ingest_and_get_point(
        contracts, tel_payload,
        {"point": {"dt_c": 16.5, "t_c": 41.5, "q": 0, "k_ratio": 1.02, "excited": True, "ttl_h": None}, "baseline_day": 3},
    )
    assert point["gecerlilik"] == "ogreniyor"
    assert point["ttl_h"] is None


def test_loose_connection_signature_keeps_early_warning_with_evidence(contracts, tel_payload):
    """Satir 2: Gevsek baglanti belirtisi, yeterli veri -> Erken uyari korunur, dayanaklar gorunur."""
    point = _ingest_and_get_point(
        contracts, tel_payload,
        {"point": {"dt_c": 53.0, "t_c": 78.0, "q": 0, "k_ratio": 1.45, "excited": True, "ttl_h": 150.5}, "baseline_day": 7},
    )
    assert point["state"] == "warn"  # esik henuz asilmadi, erken uyari asamasi
    assert point["gecerlilik"] == "tahmin_gecerli"
    assert point["ttl_h"] == 150.5  # dayanak (sayi) gorunur kaliyor


def test_sensor_drift_shows_suspicion_and_no_misleading_countdown(contracts, tel_payload):
    """Satir 3: Sensor sapmasi -> Supheli nedeni ve gecersiz tahmin durumu; yaniltici
    geri sayim yok (docs/05 #10, S8). NOT: bu test backend'in point_validity()'sini
    dogrular — girdi olarak DOGRU calisan bir kenarin (Task 1'den sonra) gonderecegi
    ttl_h=None + q!=0 kombinasyonunu verir. Task 1'in KENDI davranisi (q set olunca
    ttl_h'i gercekten None'a cekmesi) test_edge.py::test_ttl_is_suppressed_when_the_
    point_quality_is_suspect'te ayrica ve dogrudan test edilir; bu backend testi onu
    tekrar etmez, panoalgo'nun ciktisina zaten guvenir (sinir: bu test IngestPipeline'a
    dogrudan yazar, EdgePipeline'i hic calistirmaz)."""
    point = _ingest_and_get_point(
        contracts, tel_payload,
        {"point": {"dt_c": 16.5, "t_c": 41.5, "q": 1, "k_ratio": 1.02, "excited": True, "ttl_h": None}, "baseline_day": 7},
    )
    assert point["gecerlilik"] == "sensor_supheli"
    assert point["ttl_h"] is None


def test_data_loss_shows_last_seen_not_a_live_looking_value(contracts, tel_payload):
    """Satir 4: Veri kopmasi -> Son veri zamani ve izleme kaybi; son deger canli gibi
    gorunmez. NOT: comms_ok, payload["ts"]'den degil store'un last_rx'inden turer
    (bkz. test_api_panels.py:103-108 test_comms_ok_follows_contract_heartbeat_timeout);
    bu yuzden _ingest_and_get_point yerine last_rx'i acikca geri iten bir akis kullanilir."""
    store = MemoryStore(PANELS)
    ingest(contracts, store, tel_payload, received_at=NOW)
    store.set_last_rx("ADM-00001", NOW - timedelta(minutes=10))  # esik: heartbeat_timeout_min = 5
    app = create_app(Settings(contracts_dir=CONTRACTS_DIR, ingest_enabled=False), store=store, clock=lambda: NOW)

    with TestClient(app) as client:
        point = client.get("/api/v1/panels/ADM-00001").json()["points"][0]

    assert point["state"] == "stale"
    assert point["gecerlilik"] == "veri_yetersiz"  # comms koptu: q'dan degil, haberlesme kaybindan gelir


def test_breached_limit_keeps_critical_alarm_independent_of_validity(contracts, tel_payload):
    """Satir 5: Sinir asilmis -> "Sinir asildi"; kritik olcum alarmi bagimsiz kalir."""
    point = _ingest_and_get_point(
        contracts, tel_payload,
        {"point": {"dt_c": 70.1, "t_c": 95.1, "q": 0, "k_ratio": 1.0, "excited": True, "ttl_h": 2.0}, "baseline_day": 7},
    )
    assert point["state"] == "alarm"
    assert point["gecerlilik"] == "sinir_asildi"
