"""F-19 — HTTP kimlik dogrulama ve rol (app/auth.py).

Maddenin OLCULEBILIR iddiasi tek cumleyle sudur ve bu dosya onu kilitler:

    Onaylayanin kimligi artik istek GOVDESINDEN gelmiyor; govdeye elle yazilan `by`
    YOK SAYILIYOR ve denetim izine dogrulanmis oturum kimligi dusuyor.

Bunun kaniti test_body_by_is_ignored_and_journal_gets_the_token_identity'dedir.

Depoda ayni ilke iki kanalda zaten uygulanmisti (SCADA'da TCP peer, SMS'te beyaz
listeye dogrulanmis numara); burada ucuncu kanal olan HTTP kapatiliyor.
"""

from __future__ import annotations

import copy
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.auth import ANONYMOUS, ROLES, Identity, OperatorTable, parse_operators
from app.config import Settings
from app.main import create_app
from fakes import MemoryStore
from helpers import CONTRACTS_DIR, Clock, encode, utc

T0 = utc(2026, 9, 13, 10, 0, 0)
NOW = T0 + timedelta(seconds=5)
PANELS = [{"pano_id": "ADM-00001", "name": "Efeler TM-14"}]

IZLEYICI = "izleyici-belirteci"
OPERATOR = "operator-belirteci"
MUHENDIS = "muhendis-belirteci"
OPERATORS = f"nobetci:izleyici:{IZLEYICI},vardiya.amiri:operator:{OPERATOR},bas.muhendis:muhendis:{MUHENDIS}"


def make_app(store, clock, operators):
    return create_app(
        Settings(contracts_dir=CONTRACTS_DIR, ingest_enabled=False, central_detector_enabled=False),
        store=store,
        clock=clock,
        operators=operators,
    )


@pytest.fixture
def store() -> MemoryStore:
    return MemoryStore(PANELS)


@pytest.fixture
def secured(store, tel_payload):
    """Kimlik dogrulamasi ACIK bir yigin + bir aktif alarm."""
    clock = Clock(NOW)
    app = make_app(store, clock, parse_operators(OPERATORS))
    with TestClient(app) as client:
        message = copy.deepcopy(tel_payload)
        message["ts"] = T0.isoformat()
        app.state.pipeline.handle_message("gridup/pano/ADM-00001/tel", encode(message))
        assert app.state.pipeline.flush()
        yield client


def alarm_id(client) -> str:
    alarms = client.get("/api/v1/alarms").json()
    assert alarms, "test bir aktif alarm bekliyor"
    return alarms[0]["id"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------------ tablo ayristirma
def test_parse_operators_reads_user_role_token_triples():
    table = parse_operators(OPERATORS)

    assert table.enabled
    assert table.users == ("bas.muhendis", "nobetci", "vardiya.amiri")
    assert table.lookup(OPERATOR) == Identity(user="vardiya.amiri", role="operator")
    assert table.lookup("yanlis-belirtec") is None


def test_parse_operators_accepts_newlines_and_spaces():
    table = parse_operators(f"\n  nobetci : izleyici : {IZLEYICI} \n\n")
    assert table.lookup(IZLEYICI) == Identity(user="nobetci", role="izleyici")


def test_empty_table_means_auth_disabled():
    assert parse_operators("").enabled is False
    assert parse_operators("   \n  ").enabled is False


@pytest.mark.parametrize(
    "raw",
    [
        "nobetci:izleyici",                      # belirtec yok
        "nobetci:izleyici:tok:fazla",            # fazla alan
        "nobetci:kral:tok",                      # bilinmeyen rol
        ":izleyici:tok",                         # kullanici bos
        "nobetci:izleyici:",                     # belirtec bos
        f"a:izleyici:{IZLEYICI},b:operator:{IZLEYICI}",  # ayni belirtec iki kisiye
    ],
)
def test_broken_operator_line_raises_instead_of_being_skipped(raw):
    """Bozuk satir SESSIZCE ATLANMAMALI.

    Atlansaydi yanlis yazilmis bir satir yuzunden bir operator sessizce yetkisiz
    kalirdi ve bunu ancak alarmi onaylamaya calistiginda ogrenirdi.
    """
    with pytest.raises(ValueError):
        parse_operators(raw)


def test_roles_are_ordered_from_least_to_most_privileged():
    assert ROLES == ("izleyici", "operator", "muhendis")
    assert Identity("x", "muhendis").can("operator")
    assert Identity("x", "operator").can("operator")
    assert not Identity("x", "izleyici").can("operator")


# ------------------------------------------------------------------ ASIL KILIT
def test_body_by_is_ignored_and_journal_gets_the_token_identity(secured):
    """F-19'un olculebilir iddiasi.

    Istemci govdeye BASKA birinin adini yaziyor; kayda giren, belirtecin sahibi olmali.
    """
    target = alarm_id(secured)

    response = secured.post(
        f"/api/v1/alarms/{target}/ack",
        json={"by": "baskasinin.adi", "note": "ekip yolda"},
        headers=auth(OPERATOR),
    )

    assert (response.status_code, response.json()) == (200, {"ok": True})
    [acked] = secured.get("/api/v1/alarms", params={"state": "acked"}).json()
    assert acked["acked_by"] == "vardiya.amiri"      # belirtecin sahibi
    assert acked["acked_by"] != "baskasinin.adi"     # govdedeki ad HICBIR yere gitmedi


def test_shelve_also_takes_its_identity_from_the_token(secured, store):
    """Raf kimligi de belirtecten gelir.

    Alarm gorunumu `shelved_by` alani TASIMAZ (yalnizca `shelved_until`); rafa kimin
    aldigi ISA-18.2 denetim izindedir (`alarm_journal.by_user`) ve kara kutu zaman
    cizelgesi oradan beslenir. Bu yuzden dogrulama izden yapilir.
    """
    target = alarm_id(secured)
    body = {"by": "baskasinin.adi", "minutes": 30, "reason": "planli bakim bekleniyor"}

    assert secured.post(f"/api/v1/alarms/{target}/shelve", json=body, headers=auth(OPERATOR)).status_code == 200

    shelved = [entry for entry in store.journal if entry[2] == "shelved"]
    assert len(shelved) == 1
    assert shelved[0][4] == "vardiya.amiri"      # by_user: belirtecin sahibi
    assert shelved[0][4] != "baskasinin.adi"


# ------------------------------------------------------------------- 401 / 403
def test_write_without_a_token_is_401(secured):
    target = alarm_id(secured)

    response = secured.post(f"/api/v1/alarms/{target}/ack", json={})

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    # Alarm ONAYLANMAMIS olmali: reddedilen istek yan etki birakmamali.
    assert secured.get("/api/v1/alarms", params={"state": "acked"}).json() == []


@pytest.mark.parametrize(
    "header",
    [
        {"Authorization": "Bearer yanlis-belirtec"},
        {"Authorization": "Basic dXNlcjpwYXNz"},   # desteklenmeyen bicim
        {"Authorization": "Bearer"},                # belirtec yok
        {"Authorization": "Bearer   "},             # bosluk
        {"Authorization": ""},                      # bos baslik
    ],
)
def test_invalid_authorization_headers_are_401(secured, header):
    target = alarm_id(secured)
    assert secured.post(f"/api/v1/alarms/{target}/ack", json={}, headers=header).status_code == 401


def test_viewer_role_cannot_acknowledge(secured):
    """izleyici okur ama ONAYLAMAZ — 401 degil 403: kimlik dogru, yetki yok."""
    target = alarm_id(secured)

    response = secured.post(f"/api/v1/alarms/{target}/ack", json={}, headers=auth(IZLEYICI))

    assert response.status_code == 403
    assert "izleyici" in response.json()["detail"]
    assert secured.get("/api/v1/alarms", params={"state": "acked"}).json() == []


def test_engineer_role_can_acknowledge(secured):
    """muhendis, operator'un ustundedir; rol siralamasi tek yonlu calismali."""
    target = alarm_id(secured)
    assert secured.post(f"/api/v1/alarms/{target}/ack", json={}, headers=auth(MUHENDIS)).status_code == 200
    assert secured.get("/api/v1/alarms", params={"state": "acked"}).json()[0]["acked_by"] == "bas.muhendis"


def test_reads_stay_open_and_this_is_a_declared_limit(secured):
    """Bu dilimde YALNIZCA yazma uclari korunuyor; okuma uclari belirtec istemez.

    Bu bir eksiklik degil, BEYAN EDILMIS bir sinirdir (docs/15 §5). Test onu
    kilitliyor ki ileride yanlislikla degisirse fark edilsin.
    """
    for path in ("/api/v1/panels", "/api/v1/alarms", "/api/v1/fleet/kpi", "/api/v1/fleet/health"):
        assert secured.get(path).status_code == 200, path


# ---------------------------------------------------- kapali kip (demo yolu)
def test_disabled_auth_keeps_the_demo_path_working(store, tel_payload):
    """Operator tablosu bos -> belirtecsiz onay calisir, kayda 'anonim' duser.

    GK4: yigin internet kablosu cikarilmis halde tek komutla ayaga kalkmali.
    Sertifika/belirtec dagitmadan calisan bir demo yolu bu yuzden korunuyor.
    """
    clock = Clock(NOW)
    app = make_app(store, clock, OperatorTable())
    with TestClient(app) as client:
        message = copy.deepcopy(tel_payload)
        message["ts"] = T0.isoformat()
        app.state.pipeline.handle_message("gridup/pano/ADM-00001/tel", encode(message))
        assert app.state.pipeline.flush()

        target = alarm_id(client)
        assert client.post(f"/api/v1/alarms/{target}/ack", json={}).status_code == 200

        [acked] = client.get("/api/v1/alarms", params={"state": "acked"}).json()
        assert acked["acked_by"] == ANONYMOUS.user
        assert "kimlik dogrulama kapali" in acked["acked_by"]  # kayda bakan biri anlamali


def test_health_reports_whether_auth_is_on(store, tel_payload):
    """Kapali olmak SESSIZ bir varsayilan olmamali: /health tek istekte soylemeli."""
    clock = Clock(NOW)

    with TestClient(make_app(store, clock, OperatorTable())) as client:
        body = client.get("/health").json()
        assert body["auth"]["enabled"] is False
        assert body["auth"]["users"] == []

    with TestClient(make_app(store, clock, parse_operators(OPERATORS))) as client:
        body = client.get("/health").json()
        assert body["auth"]["enabled"] is True
        assert body["auth"]["users"] == ["bas.muhendis", "nobetci", "vardiya.amiri"]
        # Neyin korundugu da gorunmeli; "auth acik" tek basina yaniltici olurdu.
        assert body["auth"]["protects"] == [
            "POST /api/v1/alarms/{id}/ack",
            "POST /api/v1/alarms/{id}/shelve",
        ]
