"""TB1 — Panel API v1: contracts/openapi.yaml'a birebir uyum + turetilen alanlarin davranisi."""

from __future__ import annotations

import copy
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.ingest import IngestPipeline
from app.main import create_app
from fakes import DEFAULT_INSTALLED_AT, MemoryStore
from helpers import CONTRACTS_DIR, encode, utc

NOW = utc(2026, 9, 13, 10, 5, 0)

PANELS = [
    {"pano_id": "ADM-00001", "name": "Efeler TM-14", "lat": 37.8450, "lon": 27.8396},
    {"pano_id": "ADM-00002", "name": "Nazilli TM-07", "lat": 37.9150, "lon": 28.3200},
    {"pano_id": "GDZ-00001", "name": "Bornova TM-22", "lat": 38.4700, "lon": 27.2200},
]


def ingest(contracts, store, payload: dict, received_at: datetime) -> None:
    pipeline = IngestPipeline(contracts, store, clock=lambda: received_at)
    pipeline.handle_message(f"gridup/pano/{payload['pano_id']}/tel", encode(payload))
    assert pipeline.flush()


@pytest.fixture
def gdz_payload(tel_payload) -> dict:
    """Yogusma supheli ikinci pano: P2 alarm listede ikinci sirada."""
    payload = copy.deepcopy(tel_payload)
    payload["pano_id"] = "GDZ-00001"
    payload["ts"] = "2026-09-13T09:54:58+00:00"
    payload["risk"] = {"score": 71, "mode": "HYP-CONDENSE", "ttl_h": None, "contributions": {}}
    payload["alarms"] = ["ALM-DEW-WARN", "ALM-DEW-ALM"]
    return payload


@pytest.fixture
def store(contracts, tel_payload, gdz_payload) -> MemoryStore:
    store = MemoryStore(PANELS)
    ingest(contracts, store, tel_payload, received_at=NOW - timedelta(minutes=1))
    ingest(contracts, store, gdz_payload, received_at=NOW - timedelta(minutes=10))
    return store  # ADM-00002 hic veri gondermedi


@pytest.fixture
def client(store):
    app = create_app(
        Settings(contracts_dir=CONTRACTS_DIR, ingest_enabled=False), store=store, clock=lambda: NOW
    )
    with TestClient(app) as test_client:
        yield test_client


def ids(response) -> list[str]:
    return [panel["pano_id"] for panel in response.json()]


# ------------------------------------------------------------------ filo listesi
def test_panel_list_matches_contract_and_is_sorted_by_risk(client, api_contract):
    response = client.get("/api/v1/panels")

    assert response.status_code == 200
    api_contract(response.json(), "PanelSummary", many=True)
    assert ids(response) == ["GDZ-00001", "ADM-00001", "ADM-00002"]


def test_summary_is_derived_from_latest_telemetry(client):
    [panel] = [p for p in client.get("/api/v1/panels").json() if p["pano_id"] == "ADM-00001"]

    assert datetime.fromisoformat(panel.pop("last_seen")) == NOW - timedelta(minutes=1)
    assert panel == {
        "pano_id": "ADM-00001",
        "name": "Efeler TM-14",
        "lat": 37.8450,
        "lon": 27.8396,
        "pano_type": "1600kVA-dahili",
        "risk_score": 38,
        "risk_mode": "HYP-LOOSE-CONN",
        "top_alarm": "ALM-THR-TERM-WARN",  # iki P3 esit: kenarin sirasi korunur
        "top_prio": "P3",
        "ttl_h": 150.5,
        "comms_ok": True,
        "baseline_day": 7,
    }


def test_top_alarm_is_highest_priority_not_first_listed(client):
    [panel] = [p for p in client.get("/api/v1/panels").json() if p["pano_id"] == "GDZ-00001"]

    assert (panel["top_alarm"], panel["top_prio"]) == ("ALM-DEW-ALM", "P2")


@pytest.mark.parametrize(
    "silence, comms_ok",
    [(timedelta(minutes=5), True), (timedelta(minutes=5, seconds=1), False)],
)
def test_comms_ok_follows_contract_heartbeat_timeout(client, store, silence, comms_ok):
    store.set_last_rx("ADM-00001", NOW - silence)  # esik: heartbeat_timeout_min = 5

    [panel] = [p for p in client.get("/api/v1/panels").json() if p["pano_id"] == "ADM-00001"]

    assert panel["comms_ok"] is comms_ok


def test_panel_that_never_reported_is_listed_as_monitoring_fault(client):
    [panel] = [p for p in client.get("/api/v1/panels").json() if p["pano_id"] == "ADM-00002"]

    assert datetime.fromisoformat(panel["last_seen"]) == DEFAULT_INSTALLED_AT
    assert panel["risk_score"] == 0
    assert panel["risk_mode"] == "HYP-SELF-FAULT"
    assert panel["comms_ok"] is False
    assert (panel["top_alarm"], panel["top_prio"], panel["ttl_h"]) == (None, None, None)
    assert panel["baseline_day"] == 0


@pytest.mark.parametrize(
    "query, expected",
    [
        ("sort=pano_id", ["ADM-00001", "ADM-00002", "GDZ-00001"]),
        ("sort=last_seen", ["ADM-00001", "GDZ-00001", "ADM-00002"]),
        ("min_risk=38", ["GDZ-00001", "ADM-00001"]),
        ("min_risk=39", ["GDZ-00001"]),
        ("limit=1", ["GDZ-00001"]),
    ],
)
def test_panel_list_query_parameters(client, query, expected):
    assert ids(client.get(f"/api/v1/panels?{query}")) == expected


@pytest.mark.parametrize("query", ["sort=renk", "limit=2001", "min_risk=101"])
def test_panel_list_rejects_values_outside_contract(client, query):
    assert client.get(f"/api/v1/panels?{query}").status_code == 422


def test_unavailable_database_is_reported_as_503(client, store, api_contract):
    store.unavailable = True

    response = client.get("/api/v1/panels")

    assert response.status_code == 503
    api_contract(response.json(), "Error")


# ------------------------------------------------------------------- pano detayi
def test_panel_detail_matches_contract(client, api_contract, tel_payload):
    response = client.get("/api/v1/panels/ADM-00001")

    assert response.status_code == 200
    body = response.json()
    api_contract(body, "PanelDetail")
    assert datetime.fromisoformat(body["ts"]) == utc(2026, 9, 13, 10, 0, 0)
    assert (body["name"], body["pano_type"]) == ("Efeler TM-14", "1600kVA-dahili")
    assert (body["risk_score"], body["risk_mode"]) == (38, "HYP-LOOSE-CONN")
    assert body["risk_contributions"] == {"ALM-K-WARN": 0.6, "ALM-THR-TERM-WARN": 0.4}
    assert body["env"] == tel_payload["env"]
    assert body["elec"] == tel_payload["elec"]
    assert body["tvoc"] == tel_payload["tvoc"]
    assert body["pd"] is None
    assert body["health"] == {**tel_payload["health"], "fw": "0.1.0"}
    assert body["active_alarms"] == []


def test_panel_detail_points_carry_labels_states_and_measurements(client):
    points = client.get("/api/v1/panels/ADM-00001").json()["points"]

    assert [(p["pt"], p["label"], p["state"]) for p in points] == [
        ("GIRIS_L1", "Giriş L1", "normal"),
        ("GIRIS_L2", "Giriş L2", "warn"),
        ("GIRIS_L3", "Giriş L3", "normal"),
        ("GIRIS_N", "Giriş N", "stale"),  # q = 4: kalite bayragi dolu
        ("DSYA3_L2", "DSYA-3 L2", "normal"),
    ]
    assert points[1] == {
        "pt": "GIRIS_L2",
        "label": "Giriş L2",
        "t_c": 78.0,
        "dt_c": 53.0,
        "k": 0.000171,
        "k_ratio": 1.45,
        "tau_s": 880.0,
        "ttl_h": 150.5,
        "excited": True,
        "q": 0,
        "state": "warn",
        "gecerlilik": "tahmin_gecerli",
    }
    assert points[3] == {
        "pt": "GIRIS_N",
        "label": "Giriş N",
        "t_c": 27.1,
        "dt_c": 2.1,
        "k": None,
        "k_ratio": None,
        "tau_s": None,
        "ttl_h": None,
        "q": 4,
        "state": "stale",
        "gecerlilik": "sensor_supheli",
    }


@pytest.mark.parametrize(
    "dt_c, k_ratio, q, state",
    [
        (50.0, 1.0, 0, "normal"),  # esikler "ustu": 50 K tam sinirda uyari degil
        (50.1, 1.0, 0, "warn"),  # term_rise_warn_k
        (20.0, 1.31, 0, "warn"),  # k_ratio_warn
        (70.1, 1.0, 0, "alarm"),  # term_rise_alarm_k
        (20.0, 1.61, 0, "alarm"),  # k_ratio_alarm
        (105.1, 1.0, 0, "critical"),  # bus_rise_alarm_k (P1)
        (20.0, None, 0, "normal"),  # K kestirimi yoksa yalnizca dT'ye bakilir
        (106.0, 1.0, 3, "stale"),  # kalite bayragi olcume guvenilmez kilar
    ],
)
def test_point_state_uses_contract_thresholds(contracts, tel_payload, dt_c, k_ratio, q, state):
    point = tel_payload["t_conn"][0]
    point.update({"dt_c": dt_c, "t_c": 25.0 + dt_c, "q": q, "k_ratio": k_ratio})
    if k_ratio is None:
        del point["k_ratio"]
    store = MemoryStore(PANELS)
    ingest(contracts, store, tel_payload, received_at=NOW)
    app = create_app(Settings(contracts_dir=CONTRACTS_DIR, ingest_enabled=False), store=store, clock=lambda: NOW)

    with TestClient(app) as client:
        points = client.get("/api/v1/panels/ADM-00001").json()["points"]

    assert points[0]["state"] == state


@pytest.mark.parametrize(
    "dt_c, k_ratio, q, excited, ttl_h, baseline_day, expected",
    [
        (106.0, 1.0, 3, True, 12.0, 7, "sensor_supheli"),  # kalite bayragi her seyden once gelir
        (70.1, 1.0, 0, True, 5.0, 7, "sinir_asildi"),  # zaten alarm/kritik ise sure onemsiz
        (16.5, 1.02, 0, True, None, 3, "ogreniyor"),  # taban ogrenme tamamlanmadi (7 gunden az)
        (16.5, 1.02, 0, False, None, 7, "veri_yetersiz"),  # ogrenme bitti ama bu pencerede uyarim yok
        (16.5, 1.02, 0, True, None, 7, "model_kapsami_disi"),  # veri yeterli, egilim sinira dogru degil
        (16.5, 1.02, 0, True, 150.5, 7, "tahmin_gecerli"),  # her sey saglikli, sayi guvenilir
    ],
)
def test_point_validity_prioritises_sensor_suspicion_over_everything_else(
    contracts, tel_payload, dt_c, k_ratio, q, excited, ttl_h, baseline_day, expected
):
    point = tel_payload["t_conn"][0]
    point.update({"dt_c": dt_c, "t_c": 25.0 + dt_c, "q": q, "k_ratio": k_ratio, "excited": excited, "ttl_h": ttl_h})
    tel_payload["health"]["baseline_day"] = baseline_day
    store = MemoryStore(PANELS)
    ingest(contracts, store, tel_payload, received_at=NOW)
    app = create_app(Settings(contracts_dir=CONTRACTS_DIR, ingest_enabled=False), store=store, clock=lambda: NOW)

    with TestClient(app) as client:
        points = client.get("/api/v1/panels/ADM-00001").json()["points"]

    assert points[0]["gecerlilik"] == expected


def test_all_points_are_stale_when_panel_is_silent(client):
    points = client.get("/api/v1/panels/GDZ-00001").json()["points"]

    assert {p["state"] for p in points} == {"stale"}


def test_panel_without_telemetry_returns_empty_detail(client, api_contract):
    response = client.get("/api/v1/panels/ADM-00002")

    assert response.status_code == 200
    body = response.json()
    api_contract(body, "PanelDetail")
    assert datetime.fromisoformat(body["ts"]) == DEFAULT_INSTALLED_AT
    assert (body["points"], body["env"], body["elec"], body["health"]) == ([], {}, {}, {})
    assert (body["risk_score"], body["risk_mode"]) == (0, "HYP-SELF-FAULT")


def test_unknown_panel_returns_404(client, api_contract):
    response = client.get("/api/v1/panels/XYZ-99999")

    assert response.status_code == 404
    api_contract(response.json(), "Error")


def test_malformed_panel_id_is_rejected(client):
    assert client.get("/api/v1/panels/adm-1").status_code == 422


# ---------------------------------------------------------------------- alarmlar
def test_alarm_list_accepts_contract_filters(client, api_contract):
    response = client.get("/api/v1/alarms?state=active,acked&prio=P1,P2&pano_id=ADM-00001&limit=10")

    assert response.status_code == 200
    api_contract(response.json(), "Alarm", many=True)


# ------------------------------------------------------------------------ saglik
def test_health_reports_database_and_ingest_counters(client, store):
    client.app.state.pipeline.handle_message("gridup/pano/ADM-00001/tel", b"{bozuk")
    client.app.state.pipeline.flush()

    body = client.get("/health").json()
    assert body["ok"] is True
    assert body["db"] is True
    assert body["mqtt"] is False  # ingest kapali
    assert body["ingest"]["received"] == 1
    assert body["ingest"]["rejected"] == 1

    store.unavailable = True
    assert client.get("/health").json()["db"] is False


def test_fleet_health_endpoint(client):
    response = client.get("/api/v1/fleet/health?limit=10")
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    assert len(items) > 0
    item = items[0]
    for key in ("pano_id", "nodes_ok", "nodes_total", "rssi_dbm", "vbak_pct", "buffered", "fw", "comms_ok", "last_seen"):
        assert key in item


def test_panel_power_quality_endpoint(client):
    response = client.get("/api/v1/panels/ADM-00001/power-quality")
    assert response.status_code == 200
    data = response.json()
    assert data["pano_id"] == "ADM-00001"
    pq = data["power_quality"]
    assert "compliant" in pq
    assert "score" in pq
    assert "phases" in pq
    assert len(pq["phases"]) == 3


