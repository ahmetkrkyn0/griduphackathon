"""TB3 Adim 2 — Modbus TCP ag gecidinin uygulamaya baglanmasi (create_app yasam dongusu + ayarlar).

PLAN.md TB3 kabul olcutu: "QModMaster localhost:502'den conn_temp blogunu okuyor ve degerler arayuzle ayni".
Burada QModMaster yerine pymodbus istemcisi, arayuz yerine arayuzun okudugu API (GET /api/v1/panels/{id}).
"""

from __future__ import annotations

import socket

import pytest
from fastapi.testclient import TestClient
from pymodbus.client import ModbusTcpClient

from app.config import Settings
from app.main import create_app
from app.scada.modbus_tcp import DEFAULT_ALLOWED_NETWORKS
from fakes import MemoryStore
from helpers import CONTRACTS_DIR, Clock, encode, utc

RX = utc(2026, 9, 13, 10, 0, 2)
MODBUS_ENV = ("MODBUS_ENABLED", "MODBUS_HOST", "MODBUS_TCP_PORT", "MODBUS_WRITE_PASSWORD", "MODBUS_UNITS", "MODBUS_ALLOWED_CLIENTS",
              "IEC104_ENABLED", "IEC104_PORT", "IEC104_ALLOWED_CLIENTS")


def modbus_settings(**overrides) -> Settings:
    fields = {
        "contracts_dir": CONTRACTS_DIR,
        "ingest_enabled": False,
        "modbus_enabled": True,
        "modbus_host": "127.0.0.1",
        "modbus_port": 0,
        "modbus_units": "1=ADM-00001",
    }
    fields.update(overrides)
    return Settings(**fields)


def test_modbus_values_match_the_panel_api(tel_payload):
    app = create_app(modbus_settings(), store=MemoryStore(), clock=Clock(RX))
    with TestClient(app) as http:
        app.state.pipeline.handle_message("gridup/pano/ADM-00001/tel", encode(tel_payload))
        assert app.state.pipeline.flush()

        points = {p["pt"]: p for p in http.get("/api/v1/panels/ADM-00001").json()["points"]}
        client = ModbusTcpClient("127.0.0.1", port=app.state.scada.port, timeout=2, retries=1)
        assert client.connect()
        try:
            conn_temp = client.read_holding_registers(100, count=4, slave=1).registers
            k_index = client.read_holding_registers(200, count=2, slave=1).registers
        finally:
            client.close()

    order = ("GIRIS_L1", "GIRIS_L2", "GIRIS_L3", "GIRIS_N")
    assert conn_temp == [round(points[pt]["t_c"] * 10) for pt in order]
    assert k_index == [round(points[pt]["k_ratio"] * 1000) for pt in order[:2]]


def test_health_reports_gateway_status(tel_payload):
    app = create_app(modbus_settings(), store=MemoryStore(), clock=Clock(RX))
    with TestClient(app) as http:
        scada = http.get("/health").json()["scada"]
        assert scada["listening"] is True
        assert scada["port"] == app.state.scada.port
        assert (scada["units"], scada["writes_enabled"]) == (1, False)


def test_gateway_stops_with_the_application():
    app = create_app(modbus_settings(), store=MemoryStore(), clock=Clock(RX))
    with TestClient(app):
        port = app.state.scada.port
    with pytest.raises(OSError):
        socket.create_connection(("127.0.0.1", port), timeout=1).close()


def test_busy_port_does_not_take_the_backend_down():
    """Modbus portu dolu diye alarm ve bildirim zinciri durmamali: API calisir, /health hatayi gosterir."""
    blocker = socket.socket()
    blocker.bind(("127.0.0.1", 0))
    blocker.listen()
    try:
        app = create_app(modbus_settings(modbus_port=blocker.getsockname()[1]), store=MemoryStore(), clock=Clock(RX))
        with TestClient(app) as http:
            body = http.get("/health").json()
            assert body["ok"] is True
            assert body["scada"]["listening"] is False
            assert body["scada"]["error"]
    finally:
        blocker.close()


def test_gateway_is_off_unless_enabled():
    app = create_app(Settings(contracts_dir=CONTRACTS_DIR, ingest_enabled=False), store=MemoryStore(), clock=Clock(RX))
    with TestClient(app) as http:
        assert http.get("/health").json()["scada"] is None
        assert app.state.scada is None


def test_invalid_unit_map_fails_at_startup():
    with pytest.raises(ValueError, match="MODBUS_UNITS"):
        create_app(modbus_settings(modbus_units="1=adm-1"), store=MemoryStore())


# ------------------------------------------------------------------ ortam degiskenleri
@pytest.fixture
def clean_env(monkeypatch):
    for name in MODBUS_ENV:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_settings_read_modbus_environment(clean_env):
    clean_env.setenv("MODBUS_ENABLED", "1")
    clean_env.setenv("MODBUS_TCP_PORT", "1502")
    clean_env.setenv("MODBUS_WRITE_PASSWORD", "4242")
    clean_env.setenv("MODBUS_UNITS", "1=ADM-00001,2=ADM-00002")
    clean_env.setenv("MODBUS_ALLOWED_CLIENTS", "10.20.0.0/16, 192.168.1.5/32")
    settings = Settings.from_env()
    assert settings.modbus_enabled is True
    assert settings.modbus_port == 1502
    assert settings.modbus_password == 4242
    assert settings.modbus_units == "1=ADM-00001,2=ADM-00002"
    assert settings.modbus_allowed_clients == ("10.20.0.0/16", "192.168.1.5/32")


def test_settings_modbus_defaults_are_read_only_on_private_networks(clean_env):
    settings = Settings.from_env()
    assert settings.modbus_enabled is True
    assert (settings.modbus_host, settings.modbus_port) == ("0.0.0.0", 502)
    assert settings.modbus_password is None
    assert settings.modbus_units == ""
    assert settings.modbus_allowed_clients == DEFAULT_ALLOWED_NETWORKS


def test_settings_reject_invalid_password(clean_env):
    clean_env.setenv("MODBUS_WRITE_PASSWORD", "sifre")
    with pytest.raises(ValueError, match="MODBUS_WRITE_PASSWORD"):
        Settings.from_env()


# ------------------------------------------------------------------ IEC 60870-5-104
def iec104_interrogate(port: int, common_address: int) -> dict[int, tuple[int, bytes]]:
    """STARTDT + istasyon sorgulamasi; COT 20 nesneleri IOA -> (tip, eleman)."""
    from app.scada import iec104

    sock = socket.create_connection(("127.0.0.1", port), timeout=3)
    try:
        def exactly(size: int) -> bytes:
            data = b""
            while len(data) < size:
                chunk = sock.recv(size - len(data))
                if not chunk:
                    raise ConnectionError("IEC 104 baglantisi kapandi")
                data += chunk
            return data

        def read():
            head = exactly(2)
            return iec104.decode_apdu(head + exactly(head[1]))

        sock.sendall(iec104.encode_u(iec104.UFunction.STARTDT_ACT))
        assert read() == iec104.UFrame(iec104.UFunction.STARTDT_CON)
        command = iec104.encode_asdu(iec104.Asdu(iec104.C_IC_NA_1, iec104.COT_ACTIVATION, common_address, ((0, bytes([20])),)))
        sock.sendall(iec104.encode_i(0, 0, command))
        objects = {}
        while True:
            frame = read()
            if not isinstance(frame, iec104.IFrame):
                continue
            asdu = iec104.decode_asdu(frame.asdu)
            if asdu.cot == iec104.COT_INTERROGATED:
                objects.update({ioa: (asdu.type_id, element) for ioa, element in asdu.objects})
            if asdu.cot == iec104.COT_ACTIVATION_TERM:
                return objects
    finally:
        sock.close()


def test_iec104_interrogation_matches_the_panel_api(tel_payload):
    import struct

    app = create_app(modbus_settings(iec104_enabled=True, iec104_host="127.0.0.1", iec104_port=0), store=MemoryStore(), clock=Clock(RX))
    with TestClient(app) as http:
        app.state.pipeline.handle_message("gridup/pano/ADM-00001/tel", encode(tel_payload))
        assert app.state.pipeline.flush()
        points = {p["pt"]: p for p in http.get("/api/v1/panels/ADM-00001").json()["points"]}
        objects = iec104_interrogate(app.state.scada.iec104_port, 1)
        health = http.get("/health").json()["scada"]["iec104"]

    value, quality = struct.unpack("<fB", objects[1101][1])  # conn_temp.GIRIS_L2
    assert (round(value, 1), quality) == (points["GIRIS_L2"]["t_c"], 0)
    assert objects[2004] == (1, b"\x01")  # ALM-K-WARN canli (M_SP_NA_1)
    assert (health["listening"], health["port"]) == (True, app.state.scada.iec104_port)


def test_iec104_can_run_without_modbus(tel_payload):
    app = create_app(
        modbus_settings(modbus_enabled=False, iec104_enabled=True, iec104_host="127.0.0.1", iec104_port=0),
        store=MemoryStore(),
        clock=Clock(RX),
    )
    with TestClient(app) as http:
        app.state.pipeline.handle_message("gridup/pano/ADM-00001/tel", encode(tel_payload))
        assert app.state.pipeline.flush()
        assert 1101 in iec104_interrogate(app.state.scada.iec104_port, 1)
        scada = http.get("/health").json()["scada"]
    assert (scada["listening"], scada["iec104"]["listening"]) == (False, True)


def test_settings_read_iec104_environment(clean_env):
    clean_env.setenv("IEC104_PORT", "12404")
    clean_env.setenv("IEC104_ALLOWED_CLIENTS", "10.20.0.0/16")
    settings = Settings.from_env()
    assert (settings.iec104_enabled, settings.iec104_port, settings.iec104_allowed_clients) == (True, 12404, ("10.20.0.0/16",))
    clean_env.setenv("IEC104_ENABLED", "0")
    assert Settings.from_env().iec104_enabled is False
