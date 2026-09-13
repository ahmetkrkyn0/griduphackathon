"""Analiz uclari (TB3, C'nin TC3 ekranlari bekliyor): /panels/{id}/series, /events/{id}/blackbox, /fleet/kpi.

Sozlesme: contracts/openapi.yaml. Kurulum gercek ingest hatti + gercek alarm servisi + bellek ici depo;
PgStore'un ayni sorgulari tests/test_insight_store.py'de gercek TimescaleDB'ye karsi sinanir.

tel_valid.json ADM-00001: GIRIS_L2 dT 53 K ve K/K0 1,45 -> ALM-THR-TERM-WARN + ALM-K-WARN (P3, ayni olay);
GIRIS_N q = 4 (veri kalitesi bayragi).
"""

from __future__ import annotations

import copy
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.notify.dispatcher import Delivery
from fakes import MemoryStore
from helpers import CONTRACTS_DIR, Clock, encode, utc

PANELS = [
    {"pano_id": "ADM-00001", "name": "Efeler TM-14"},
    {"pano_id": "ADM-00002", "name": "Nazilli TM-07"},
    {"pano_id": "GDZ-00001", "name": "Bornova TM-22"},
]
T0 = utc(2026, 9, 13, 10, 0, 0)
T0_MS = 1789293600000  # 2026-09-13T10:00:00Z


class Rig:
    def __init__(self, store: MemoryStore, clock: Clock) -> None:
        self.store = store
        self.clock = clock
        self.app = create_app(Settings(contracts_dir=CONTRACTS_DIR, ingest_enabled=False), store=store, clock=clock)
        self.http = TestClient(self.app)

    def ingest(self, payload: dict, received_at: datetime | None = None) -> None:
        if received_at is not None:
            self.clock.now = received_at
        self.app.state.pipeline.handle_message(f"gridup/pano/{payload['pano_id']}/tel", encode(payload))
        assert self.app.state.pipeline.flush()
        assert not self.store.quarantined, self.store.quarantined


@pytest.fixture
def rig():
    rig = Rig(MemoryStore(PANELS), Clock(T0 + timedelta(seconds=2)))
    with rig.http:
        yield rig


def sample(tel_payload: dict, ts: datetime, seq: int, **point_dt) -> dict:
    payload = copy.deepcopy(tel_payload)
    payload["ts"] = ts.isoformat()
    payload["seq"] = seq
    for point in payload["t_conn"]:
        if point["pt"] in point_dt:
            point["dt_c"] = point_dt[point["pt"]]
    return payload


def iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def get_series(rig, **params):
    return rig.http.get("/api/v1/panels/ADM-00001/series", params=params)


# ================================================================== series
@pytest.fixture
def three_samples(rig, tel_payload):
    rig.ingest(sample(tel_payload, T0, 1, GIRIS_L2=50.0), received_at=T0 + timedelta(seconds=2))
    rig.ingest(sample(tel_payload, T0 + timedelta(seconds=30), 2, GIRIS_L2=52.0), received_at=T0 + timedelta(seconds=32))
    rig.ingest(sample(tel_payload, T0 + timedelta(minutes=2, seconds=10), 3, GIRIS_L2=60.0), received_at=T0 + timedelta(minutes=2, seconds=12))
    return rig


def test_series_averages_buckets_and_fills_gaps(three_samples):
    response = get_series(three_samples, tags="t_conn.GIRIS_L2.dt_c", **{"from": iso(T0), "to": iso(T0 + timedelta(minutes=4))}, step="1m")
    assert response.status_code == 200
    assert response.json() == {
        "t_conn.GIRIS_L2.dt_c": [
            [T0_MS, 51.0],
            [T0_MS + 60_000, None],
            [T0_MS + 120_000, 60.0],
            [T0_MS + 180_000, None],
        ]
    }


def test_series_bucket_start_is_aligned_to_step(three_samples):
    """from 10:00:40 -> ilk kova 10:00:00'dan baslar; 10:00:30 ornegi o kovadadir ama from'dan once oldugu icin dahil degil."""
    response = get_series(three_samples, tags="t_conn.GIRIS_L2.dt_c", **{"from": iso(T0 + timedelta(seconds=40)), "to": iso(T0 + timedelta(minutes=3))}, step="1m")
    assert response.json()["t_conn.GIRIS_L2.dt_c"] == [[T0_MS, None], [T0_MS + 60_000, None], [T0_MS + 120_000, 60.0]]


def test_series_excludes_bad_quality_samples(three_samples):
    response = get_series(three_samples, tags="t_conn.GIRIS_N.dt_c", **{"from": iso(T0), "to": iso(T0 + timedelta(minutes=1))}, step="1m")
    assert response.json() == {"t_conn.GIRIS_N.dt_c": [[T0_MS, None]]}  # GIRIS_N q = 4


def test_series_multiple_tags_array_element_and_k_index_alias(three_samples):
    response = get_series(three_samples, tags="elec.i_ph.1,k_index.GIRIS_L2", **{"from": iso(T0), "to": iso(T0 + timedelta(minutes=1))}, step="1m")
    assert response.json() == {"elec.i_ph.1": [[T0_MS, 420.0]], "k_index.GIRIS_L2": [[T0_MS, 1.45]]}


def test_series_unknown_tag_is_empty_not_error(three_samples):
    response = get_series(three_samples, tags="env.yok_boyle_alan", **{"from": iso(T0), "to": iso(T0 + timedelta(minutes=2))}, step="1m")
    assert response.json() == {"env.yok_boyle_alan": [[T0_MS, None], [T0_MS + 60_000, None]]}


@pytest.mark.parametrize(
    "params",
    [
        {"tags": "t_conn.GIRIS_L2.dt_c", "from": "2026-09-13T10:05:00Z", "to": "2026-09-13T10:00:00Z"},  # from >= to
        {"tags": "t_conn.GIRIS_L2.dt_c", "from": "2026-09-13T10:00:00Z", "to": "2026-09-13T10:05:00Z", "step": "5x"},
        {"tags": "t_conn.GIRIS_L2.dt_c", "from": "2026-09-13T10:00:00Z", "to": "2026-09-13T10:05:00Z", "step": "1s"},  # < 10 s
        {"tags": "t_conn.GIRIS_L2.dt_c", "from": "2026-08-13T10:00:00Z", "to": "2026-09-13T10:00:00Z", "step": "10s"},  # cok nokta
        {"tags": ",".join(f"elec.i_ph.{n % 3}x{n}" for n in range(13)), "from": "2026-09-13T10:00:00Z", "to": "2026-09-13T10:05:00Z"},
        {"tags": "t_conn.GIRIS_L2.dt_c;DROP", "from": "2026-09-13T10:00:00Z", "to": "2026-09-13T10:05:00Z"},
        {"tags": "", "from": "2026-09-13T10:00:00Z", "to": "2026-09-13T10:05:00Z"},
        {"tags": "t_conn.GIRIS_L2.dt_c", "from": "2026-09-13T10:00:00", "to": "2026-09-13T10:05:00Z"},  # saat dilimi yok
    ],
)
def test_series_rejects_invalid_requests(rig, params):
    assert rig.http.get("/api/v1/panels/ADM-00001/series", params=params).status_code == 422


def test_series_unknown_panel_is_404(rig):
    params = {"tags": "elec.i_n", "from": "2026-09-13T10:00:00Z", "to": "2026-09-13T10:05:00Z"}
    assert rig.http.get("/api/v1/panels/ADM-09999/series", params=params).status_code == 404


def test_series_default_step_is_one_minute(three_samples):
    response = get_series(three_samples, tags="elec.i_n", **{"from": iso(T0), "to": iso(T0 + timedelta(minutes=3))})
    assert [point[0] for point in response.json()["elec.i_n"]] == [T0_MS, T0_MS + 60_000, T0_MS + 120_000]


# ================================================================== blackbox
@pytest.fixture
def incident(rig, tel_payload):
    """09:00 K uyarisi (P3), 09:50 ark tripi (P1, yeni olay), 09:52 operator onayi."""
    warn = sample(tel_payload, T0 - timedelta(hours=1), 10)
    rig.ingest(warn, received_at=T0 - timedelta(hours=1) + timedelta(seconds=2))
    trip = sample(tel_payload, T0 - timedelta(minutes=10), 11)
    trip["alarms"] = ["ALM-THR-TERM-WARN", "ALM-K-WARN", "ALM-ARC-TRIP"]  # P3 kosullari suruyor: temizlenmez
    trip["tvoc"]["trips"] = 1
    rig.ingest(trip, received_at=T0 - timedelta(minutes=10) + timedelta(seconds=2))
    alarms = rig.http.get("/api/v1/alarms", params={"state": "active,acked"}).json()
    arc = next(a for a in alarms if a["code"] == "ALM-ARC-TRIP")
    rig.clock.now = T0 - timedelta(minutes=8)
    assert rig.http.post(f"/api/v1/alarms/{arc['id']}/ack", json={"by": "vardiya-amiri", "note": "ekip yolda"}).status_code == 200
    return arc


def test_blackbox_of_arc_trip(rig, incident, api_contract):
    response = rig.http.get(f"/api/v1/events/{incident['event_id']}/blackbox", params={"window_h": 2})
    assert response.status_code == 200
    body = response.json()
    api_contract(body, "Blackbox")
    assert (body["event_id"], body["pano_id"], body["code"], body["window_h"]) == (incident["event_id"], "ADM-00001", "ALM-ARC-TRIP", 2)
    assert datetime.fromisoformat(body["occurred_at"]) == T0 - timedelta(minutes=10)

    kinds = [(entry["kind"], entry["text"]) for entry in body["timeline"]]
    assert [kind for kind, _ in kinds] == ["alarm", "alarm", "trip", "ack"]
    assert "ALM-K-WARN" in " ".join(text for _, text in kinds[:2])
    assert "vardiya-amiri" in kinds[3][1] and "ekip yolda" in kinds[3][1]

    trips = [value for _, value in body["series"]["tvoc.trips"] if value is not None]
    assert trips == [0.0, 1.0]  # 09:00 orneginde 0, 09:50 orneginde 1
    assert "elec.i_ph.0" in body["series"] and "env.td_margin_k" in body["series"]


def test_blackbox_includes_event_point_signals(rig, tel_payload):
    rig.ingest(sample(tel_payload, T0, 1), received_at=T0 + timedelta(seconds=2))
    alarm = next(a for a in rig.http.get("/api/v1/alarms").json() if a["code"] == "ALM-K-WARN")
    body = rig.http.get(f"/api/v1/events/{alarm['event_id']}/blackbox").json()
    assert body["window_h"] == 72
    assert {"t_conn.GIRIS_L2.t_c", "t_conn.GIRIS_L2.dt_c", "t_conn.GIRIS_L2.k_ratio"} <= set(body["series"])
    assert body["det_label"] == "Giriş L2"
    assert [value for _, value in body["series"]["t_conn.GIRIS_L2.dt_c"] if value is not None] == [53.0]


def test_blackbox_unknown_event_is_404(rig):
    assert rig.http.get("/api/v1/events/EVT-999/blackbox").status_code == 404


@pytest.mark.parametrize("window_h", [0, 169])
def test_blackbox_window_limits(rig, window_h):
    assert rig.http.get("/api/v1/events/EVT-1/blackbox", params={"window_h": window_h}).status_code == 422


# ================================================================== fleet kpi
def test_fleet_kpi(rig, tel_payload, api_contract):
    now = T0 + timedelta(minutes=5)
    rig.ingest(sample(tel_payload, T0 + timedelta(minutes=4), 1), received_at=now - timedelta(minutes=1))  # ADM-00001: 2 x P3
    other = sample(tel_payload, T0 - timedelta(minutes=6), 1)
    other["pano_id"] = "GDZ-00001"
    other["alarms"] = []
    rig.ingest(other, received_at=now - timedelta(minutes=10))  # haberlesme koptu (> 5 dk)
    rig.clock.now = now

    alarms = sorted(rig.http.get("/api/v1/alarms").json(), key=lambda a: int(a["id"]))
    raised = datetime.fromisoformat(alarms[0]["raised_at"])
    deliveries = [
        Delivery(int(alarms[0]["id"]), "sms", "+90*****0001", raised + timedelta(seconds=1.5), True, "ok"),
        Delivery(int(alarms[0]["id"]), "whatsapp", "+90*****0001", raised + timedelta(seconds=4), True, "ok"),  # ilk degil
        Delivery(int(alarms[1]["id"]), "sms", "+90*****0002", raised + timedelta(seconds=2), False, "modem yok"),  # basarisiz
        Delivery(int(alarms[1]["id"]), "call", "+90*****0002", raised + timedelta(seconds=2.5), True, "ok"),  # telefona mesaj degil
        Delivery(int(alarms[1]["id"]), "sms", "+90*****0002", raised + timedelta(seconds=3), True, "ok"),
    ]
    for delivery in deliveries:
        rig.store.record_notification(delivery)

    body = rig.http.get("/api/v1/fleet/kpi").json()
    api_contract(body, "FleetKpi")
    assert body["panels_total"] == 3
    assert body["comms_ok_pct"] == pytest.approx(33.3, abs=0.05)  # 3 panodan 1'i
    assert body["alarms_per_100_panels_per_day"] == pytest.approx(66.67, abs=0.005)  # 2 alarm / 3 pano x 100
    assert body["active_by_prio"] == {"P1": 0, "P2": 0, "P3": 2, "SYS": 0, "INFO": 0}
    assert body["distribution_pct"] == {"P1": 0.0, "P2": 0.0, "P3": 100.0}
    assert body["p95_end_to_end_ms"] == 3000.0  # alarm basina ilk basarili sms/whatsapp: [1500, 3000], en yakin sira
    assert body["ingest_msgs_per_s"] == pytest.approx(2 / 60, abs=0.005)


def test_fleet_kpi_without_deliveries_omits_latency(rig):
    body = rig.http.get("/api/v1/fleet/kpi").json()
    assert "p95_end_to_end_ms" not in body  # 0 ms demek yanlis olurdu; sozlesmede alan zorunlu degil
    assert body["alarms_per_100_panels_per_day"] == 0.0
    assert body["distribution_pct"] == {"P1": 0.0, "P2": 0.0, "P3": 0.0}


def test_fleet_kpi_counts_only_last_day(rig, tel_payload):
    rig.ingest(sample(tel_payload, T0, 1), received_at=T0 + timedelta(seconds=2))
    rig.clock.now = T0 + timedelta(hours=25)
    body = rig.http.get("/api/v1/fleet/kpi").json()
    assert body["alarms_per_100_panels_per_day"] == 0.0
    assert body["distribution_pct"]["P3"] == 100.0  # dagilim 7 gunluk pencerede


def test_fleet_kpi_empty_fleet():
    rig = Rig(MemoryStore(), Clock(T0))
    with rig.http:
        body = rig.http.get("/api/v1/fleet/kpi").json()
    assert (body["panels_total"], body["comms_ok_pct"], body["alarms_per_100_panels_per_day"]) == (0, 0.0, 0.0)


def test_fleet_kpi_active_count_excludes_shelved(rig, tel_payload):
    """Rafa alinmis alarm etkin sayilmaz (konsolun varsayilan filtresi ve SCADA canli bitleriyle ayni kural)."""
    rig.ingest(sample(tel_payload, T0, 1), received_at=T0 + timedelta(seconds=2))
    k_warn = next(a for a in rig.http.get("/api/v1/alarms").json() if a["code"] == "ALM-K-WARN")
    shelve = {"by": "operator", "minutes": 30, "reason": "planli bakim bekleniyor"}
    assert rig.http.post(f"/api/v1/alarms/{k_warn['id']}/shelve", json=shelve).status_code == 200
    assert rig.http.get("/api/v1/fleet/kpi").json()["active_by_prio"]["P3"] == 1
