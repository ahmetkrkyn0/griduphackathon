"""TB2 — alarm servisi ve API: telemetri -> risk -> ISA-18.2 yoneticisi -> depo -> HTTP/WS.

Uc sozlesmesi contracts/openapi.yaml (Alarm, ack, shelve, PanelDetail.active_alarms, x-websocket).
Duvar saati elle ilerletilir; alarm zamanlayicisi (raf suresi, haberlesme denetimi) arka plan
thread'i yerine dogrudan `app.state.alarms.tick()` ile calistirilir.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from fakes import MemoryStore
from helpers import CONTRACTS_DIR, Clock, encode, receive_json, utc

T0 = utc(2026, 9, 13, 10, 0, 0)  # telemetri olay zamani (fixture ts)
NOW = T0 + timedelta(seconds=5)  # merkezin duvar saati: ag gecikmesi kadar sonra

PANELS = [
    {"pano_id": "ADM-00001", "name": "Efeler TM-14"},
    {"pano_id": "ADM-00002", "name": "Nazilli TM-07"},
]
EDGE_CODES = {"ALM-THR-TERM-WARN", "ALM-K-WARN"}  # tel_valid.json alarms alani


def make_app(store: MemoryStore, clock: Clock):
    return create_app(Settings(contracts_dir=CONTRACTS_DIR, ingest_enabled=False), store=store, clock=clock)


@pytest.fixture
def clock() -> Clock:
    return Clock(NOW)


@pytest.fixture
def store() -> MemoryStore:
    return MemoryStore(PANELS)


@pytest.fixture
def app(store, clock):
    return make_app(store, clock)


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


def send(
    app,
    payload: dict,
    minutes: float = 0.0,
    *,
    alarms: list[str] | None = None,
    pano_id: str = "ADM-00001",
    mutate: Callable[[dict], None] | None = None,
) -> None:
    """Ornegi T0 + `minutes` olay zamaniyla ingest'e verir ve yazar (alici saat = duvar saati)."""
    message = copy.deepcopy(payload)
    message["pano_id"] = pano_id
    message["ts"] = (T0 + timedelta(minutes=minutes)).isoformat()
    message["seq"] = payload["seq"] + int(minutes * 6)
    if alarms is not None:
        message["alarms"] = alarms
    if mutate is not None:
        mutate(message)
    pipeline = app.state.pipeline
    pipeline.handle_message(f"gridup/pano/{pano_id}/tel", encode(message))
    assert pipeline.flush()
    assert pipeline.stats["rejected"] == 0


def list_alarms(client, **params) -> list[dict]:
    response = client.get("/api/v1/alarms", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def by_code(alarms: list[dict]) -> dict[str, dict]:
    return {alarm["code"]: alarm for alarm in alarms}


def hypothesis_advice(contracts, code: str) -> str:
    return next(h["advice"] for h in contracts.alarm_codes["hypotheses"] if h["code"] == code)


# ------------------------------------------------------------------ liste
def test_edge_alarms_become_explained_console_alarms(client, app, api_contract, contracts, tel_payload):
    send(app, tel_payload)

    body = list_alarms(client)

    api_contract(body, "Alarm", many=True)
    alarms = by_code(body)
    assert set(alarms) == EDGE_CODES
    k_warn = alarms["ALM-K-WARN"]
    assert (k_warn["pano_id"], k_warn["prio"], k_warn["state"]) == ("ADM-00001", "P3", "active")
    assert datetime.fromisoformat(k_warn["raised_at"]) == T0
    assert k_warn["text"] == contracts.alarm("ALM-K-WARN")["text"]
    assert k_warn["reason"]["signals"][0]["tag"] == "t_conn.GIRIS_L2.k_ratio"
    assert k_warn["advice"] == hypothesis_advice(contracts, "HYP-LOOSE-CONN")
    assert k_warn["ttl_h"] == 150.5
    assert alarms["ALM-THR-TERM-WARN"]["event_id"] == k_warn["event_id"]  # ayni baglanti noktasi


def test_list_filters_by_priority_and_panel(client, app, tel_payload):
    send(app, tel_payload)
    send(app, tel_payload, pano_id="ADM-00002", alarms=["ALM-DEW-ALM"])

    assert {a["pano_id"] for a in list_alarms(client, prio="P2")} == {"ADM-00002"}
    assert {a["code"] for a in list_alarms(client, pano_id="ADM-00001")} == EDGE_CODES
    assert len(list_alarms(client, limit=1)) == 1


@pytest.mark.parametrize("params", [{"state": "active,bogus"}, {"prio": "P9"}, {"state": ""}])
def test_list_filter_values_are_validated(client, params):
    assert client.get("/api/v1/alarms", params=params).status_code == 422


def test_panel_in_maintenance_mode_raises_only_p1(client, app, tel_payload):
    """Kapak acik + planli is emri: bakim modu. Bastirilabilir alarmlar olusmaz, ark tripi olusur."""

    def maintenance_with_arc(message: dict) -> None:
        message["health"]["maint_mode"] = True
        message["tvoc"]["trips"] = 1

    send(app, tel_payload, alarms=["ALM-THR-TERM-WARN", "ALM-K-WARN", "ALM-ARC-TRIP"], mutate=maintenance_with_arc)

    assert [a["code"] for a in list_alarms(client)] == ["ALM-ARC-TRIP"]


def test_panel_detail_lists_its_active_alarms(client, app, api_contract, tel_payload):
    send(app, tel_payload)

    body = client.get("/api/v1/panels/ADM-00001").json()

    api_contract(body, "PanelDetail")
    assert {a["code"] for a in body["active_alarms"]} == EDGE_CODES
    assert client.get("/api/v1/panels/ADM-00002").json()["active_alarms"] == []


def test_alarm_changes_are_streamed_to_websocket_clients(client, app, api_contract, tel_payload):
    with client.websocket_connect("/api/v1/stream") as ws:
        assert receive_json(ws)["type"] == "hello"
        send(app, tel_payload)
        messages = [receive_json(ws) for _ in range(3)]

    assert sorted(m["type"] for m in messages) == ["alarm", "alarm", "tel"]
    streamed = [m["payload"] for m in messages if m["type"] == "alarm"]
    api_contract(streamed, "Alarm", many=True)
    assert {a["code"] for a in streamed} == EDGE_CODES


# ------------------------------------------------------------------- onay
def test_ack_records_the_operator(client, app, clock, tel_payload):
    send(app, tel_payload)
    k_warn = by_code(list_alarms(client))["ALM-K-WARN"]
    clock.advance(2)

    response = client.post(f"/api/v1/alarms/{k_warn['id']}/ack", json={"by": "vardiya.amiri", "note": "ekip yolda"})

    assert (response.status_code, response.json()) == (200, {"ok": True})
    [acked] = list_alarms(client, state="acked")
    assert (acked["id"], acked["acked_by"]) == (k_warn["id"], "vardiya.amiri")
    assert datetime.fromisoformat(acked["acked_at"]) == NOW + timedelta(minutes=2)
    assert [a["code"] for a in list_alarms(client, state="active")] == ["ALM-THR-TERM-WARN"]


def test_ack_error_statuses(client, app, tel_payload):
    send(app, tel_payload)
    alarm_id = list_alarms(client)[0]["id"]
    assert client.post(f"/api/v1/alarms/{alarm_id}/ack", json={"by": "op"}).status_code == 200

    assert client.post(f"/api/v1/alarms/{alarm_id}/ack", json={"by": "op"}).status_code == 409
    assert client.post("/api/v1/alarms/999999/ack", json={"by": "op"}).status_code == 404
    assert client.post("/api/v1/alarms/abc/ack", json={"by": "op"}).status_code == 404
    assert client.post(f"/api/v1/alarms/{alarm_id}/ack", json={}).status_code == 422


def test_ack_of_an_already_cleared_alarm_is_a_conflict(client, app, contracts, tel_payload):
    send(app, tel_payload)
    alarm_id = list_alarms(client)[0]["id"]

    send(app, tel_payload, minutes=contracts.thresholds["hysteresis_clear_min"], alarms=[])

    assert list_alarms(client) == []
    assert alarm_id in [a["id"] for a in list_alarms(client, state="cleared")]
    assert client.post(f"/api/v1/alarms/{alarm_id}/ack", json={"by": "op"}).status_code == 409


# -------------------------------------------------------------------- raf
def test_shelved_alarm_is_hidden_until_its_time_is_up(client, app, clock, tel_payload):
    send(app, tel_payload)
    k_warn = by_code(list_alarms(client))["ALM-K-WARN"]

    response = client.post(
        f"/api/v1/alarms/{k_warn['id']}/shelve", json={"by": "op", "minutes": 30, "reason": "bakim ekibi sahada"}
    )

    assert (response.status_code, response.json()) == (200, {"ok": True})
    assert k_warn["id"] not in [a["id"] for a in list_alarms(client)]
    [shelved] = list_alarms(client, state="shelved")
    assert datetime.fromisoformat(shelved["shelved_until"]) == NOW + timedelta(minutes=30)

    clock.advance(30)
    app.state.alarms.tick()

    assert k_warn["id"] in [a["id"] for a in list_alarms(client, state="active")]


@pytest.mark.parametrize(
    "body",
    [
        {"by": "op", "minutes": 0, "reason": "gecerli gerekce"},
        {"by": "op", "minutes": "SHELVE_MAX+1", "reason": "gecerli gerekce"},
        {"by": "op", "minutes": 30, "reason": "ab"},
        {"by": "op", "minutes": 30},
    ],
)
def test_shelve_rejects_invalid_requests(client, app, contracts, tel_payload, body):
    send(app, tel_payload)
    alarm_id = list_alarms(client)[0]["id"]
    if body.get("minutes") == "SHELVE_MAX+1":
        body = {**body, "minutes": contracts.thresholds["shelve_max_min"] + 1}

    assert client.post(f"/api/v1/alarms/{alarm_id}/shelve", json=body).status_code == 422
    assert list_alarms(client, state="shelved") == []


def test_p1_alarm_cannot_be_shelved(client, app, tel_payload):
    send(app, tel_payload, alarms=["ALM-ARC-TRIP"], mutate=lambda m: m["tvoc"].update(trips=1))
    [arc] = list_alarms(client, prio="P1")

    response = client.post(f"/api/v1/alarms/{arc['id']}/shelve", json={"by": "op", "minutes": 30, "reason": "deneme amacli"})

    assert response.status_code == 403
    assert list_alarms(client, state="shelved") == []


# --------------------------------------------------- haberlesme denetimi
def test_silent_panel_raises_comms_lost_and_clears_after_data_returns(client, app, clock, contracts, tel_payload):
    timeout = contracts.thresholds["heartbeat_timeout_min"]
    hyst = contracts.thresholds["hysteresis_clear_min"]
    send(app, tel_payload, alarms=[])
    clock.advance(timeout + 1)

    app.state.alarms.tick()

    [comms] = list_alarms(client)
    assert (comms["code"], comms["pano_id"], comms["prio"]) == ("ALM-COMMS-LOST", "ADM-00001", contracts.prio_of("ALM-COMMS-LOST"))
    assert comms["reason"]["signals"][0]["value"] == pytest.approx(timeout + 1)
    assert comms["advice"] == hypothesis_advice(contracts, "HYP-SELF-FAULT")

    send(app, tel_payload, minutes=timeout + 1, alarms=[])  # veri geri geldi
    app.state.alarms.tick()
    assert [a["code"] for a in list_alarms(client)] == ["ALM-COMMS-LOST"]  # histerezis dolmadi

    clock.advance(hyst + 0.5)
    send(app, tel_payload, minutes=timeout + 1 + hyst + 0.5, alarms=[])
    assert list_alarms(client) == []

    app.state.alarms.tick()  # pano konusuyor: zamanlayici kopuklugu yeniden acmamali
    assert list_alarms(client) == []


def test_panel_that_never_reported_does_not_raise_comms_lost(client, app, clock, contracts):
    clock.advance(contracts.thresholds["heartbeat_timeout_min"] + 1)

    app.state.alarms.tick()

    assert list_alarms(client) == []


# ------------------------------------------------------------- dayaniklilik
def test_alarms_survive_a_backend_restart(store, clock, tel_payload):
    first = make_app(store, clock)
    with TestClient(first) as client:
        send(first, tel_payload)
        before = list_alarms(client)

    second = make_app(store, clock)
    with TestClient(second) as client:
        assert list_alarms(client) == before
        k_warn = by_code(before)["ALM-K-WARN"]
        assert client.post(f"/api/v1/alarms/{k_warn['id']}/ack", json={"by": "op"}).status_code == 200

        send(second, tel_payload, minutes=1, alarms=[*EDGE_CODES, "ALM-DEW-ALM"])

        after = by_code(list_alarms(client))
        assert {code: after[code]["id"] for code in EDGE_CODES} == {code: by_code(before)[code]["id"] for code in EDGE_CODES}
        assert after["ALM-DEW-ALM"]["id"] not in {a["id"] for a in before}  # yeni kimlik eskisinin ustune yazmaz


def test_backend_starts_while_database_is_down_and_alarms_work_once_it_is_up(store, clock, tel_payload):
    """TB1 davranisi korunur: DB kapaliyken backend yine ayaga kalkar (API 503)."""
    store.unavailable = True
    app = make_app(store, clock)
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/api/v1/alarms").status_code == 503

        store.unavailable = False
        send(app, tel_payload)

        assert set(by_code(list_alarms(client))) == EDGE_CODES


def test_failed_alarm_save_is_retried_on_tick_without_duplicates(client, app, store, tel_payload):
    store.fail_alarm_saves = 1
    send(app, tel_payload)
    assert list_alarms(client) == []  # yazilamadi; alarm bellekte duruyor

    app.state.alarms.tick()

    assert set(by_code(list_alarms(client))) == EDGE_CODES
    assert [entry[2] for entry in store.journal].count("raised") == 2
