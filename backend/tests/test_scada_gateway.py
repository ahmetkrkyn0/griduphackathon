"""TB3 Adim 2 — SCADA ag gecidi (app.scada.gateway): birim -> pano, register goruntusu, yazma politikasi.

Kurulum uretimdeki zincirin aynisidir: IngestPipeline -> ScadaGateway.on_samples + AlarmService.on_samples
-> AlarmService dinleyicisi -> ScadaGateway.on_alarm_changes. Sunucu gercek TCP'de, istemci pymodbus.
Esikler ve adresler sozlesmeden okunur; sifre, duvar saati ve monotonik saat test icin enjekte edilir.

Istisna kodlari: 0x01 yazma kapali / kilit acilmamis / IP kilitli · 0x02 komut blogu disina yazma (TVOC-2
aynasi, GK6) · 0x03 yanlis sifre veya gecersiz komut degeri · 0x0A birim eslenmemis · 0x0B hedefin verisi
yok veya komut kenara iletilemedi.

tel_valid.json ADM-00001: GIRIS_L2 dT 53 K ve K/K0 1,45 -> ALM-THR-TERM-WARN (bit 0) + ALM-K-WARN (bit 4), ikisi P3.
"""

from __future__ import annotations

import copy
from datetime import timedelta

import pytest
from pymodbus.client import ModbusTcpClient

from app.alarm_service import AlarmService
from app.api.stream import StreamHub
from app.config import parse_modbus_password as parse_password
from app.db import StoreError
from app.ingest import IngestPipeline
from app.scada.gateway import ScadaGateway, parse_units
from app.scada.map_loader import load_map
from app.scada.modbus_tcp import ExceptionCode, ModbusTcpServer
from fakes import MemoryStore
from helpers import CONTRACTS_DIR, Clock, LoopThread, encode, utc

PASSWORD = 4242
PANO = "ADM-00001"
RX = utc(2026, 9, 13, 10, 0, 2)

ALARM_BITS_LIVE = 800
ALARM_BITS_LATCHED = 810
EVENT_COUNT = 830
MAINT_REGISTER = 903


class FakeMonotonic:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class EdgeCommands:
    """Kenara komut kanalinin test cifti: gonderilenleri kaydeder; accept=False broker'a iletilemedi demektir."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str, dict]] = []
        self.accept = True

    def __call__(self, pano_id: str, cmd: str, args: dict) -> bool:
        self.sent.append((pano_id, cmd, args))
        return self.accept


class Rig:
    def __init__(self, contracts, loop: LoopThread, *, units, password, sink, wire_alarms, store) -> None:
        self.loop = loop
        self.store = store or MemoryStore()
        self.clock = Clock(RX)
        self.monotonic = FakeMonotonic()
        self.alarms = AlarmService(contracts, self.store, StreamHub(), clock=self.clock)
        self.pipeline = IngestPipeline(contracts, self.store, clock=self.clock)
        self.commands = EdgeCommands()
        self.gateway = ScadaGateway(
            load_map(CONTRACTS_DIR / "modbus-map.yaml"),
            contracts,
            alarms=self.alarms,
            store=self.store,
            clock=self.clock,
            units=units,
            password=password,
            command_sink=self.commands if sink else None,
            monotonic=self.monotonic,
        )
        self.pipeline.add_listener(self.gateway.on_samples)
        if wire_alarms:
            self.pipeline.add_listener(self.alarms.on_samples)
        self.alarms.add_listener(self.gateway.on_alarm_changes)
        self.server = ModbusTcpServer(self.gateway, host="127.0.0.1", port=0, allowed_networks=("127.0.0.0/8",))
        loop.run(self.server.start())
        self.clients: list[ModbusTcpClient] = []

    def ingest(self, payload: dict) -> None:
        self.pipeline.handle_message(f"gridup/pano/{payload['pano_id']}/tel", encode(payload))
        assert self.pipeline.flush()
        assert not self.store.quarantined, self.store.quarantined

    def client(self) -> ModbusTcpClient:
        client = ModbusTcpClient("127.0.0.1", port=self.server.port, timeout=2, retries=1)
        assert client.connect()
        self.clients.append(client)
        return client

    def close(self) -> None:
        for client in self.clients:
            client.close()
        self.loop.run(self.server.stop())


@pytest.fixture
def loop():
    thread = LoopThread()
    yield thread
    thread.close()


DEFAULT_UNITS = {1: PANO}


@pytest.fixture
def make_rig(contracts, loop):
    rigs: list[Rig] = []

    def make(*, units=DEFAULT_UNITS, password=PASSWORD, sink=True, wire_alarms=True, store=None) -> Rig:
        """units=None -> otomatik esleme (pano kimligi sirasi)."""
        rig = Rig(contracts, loop, units=units, password=password, sink=sink, wire_alarms=wire_alarms, store=store)
        rigs.append(rig)
        return rig

    yield make
    for rig in rigs:
        rig.close()


@pytest.fixture
def rig(make_rig, tel_payload) -> Rig:
    rig = make_rig()
    rig.ingest(tel_payload)
    return rig


def exception_code(result) -> int | None:
    return result.exception_code if result.isError() and hasattr(result, "exception_code") else None


def registers(client, address: int, count: int = 1, unit: int = 1) -> list[int]:
    result = client.read_holding_registers(address, count=count, slave=unit)
    assert not result.isError(), result
    return result.registers


def acked_codes(rig: Rig) -> set[str]:
    return {a.code for a in rig.alarms.open_alarms(PANO) if a.state == "acked"}


def unlock(client) -> None:
    assert not client.write_register(900, PASSWORD, slave=1).isError()


# ------------------------------------------------------------------ okuma
def test_reads_live_measurements_of_mapped_panel(rig):
    client = rig.client()
    assert registers(client, 100, 5) == [415, 780, 409, 271, 0x8000]  # GIRIS_L1..N, DSYA1_L1 yok
    assert client.read_input_registers(150, count=2, slave=1).registers == [165, 530]  # FC04 aynasi


def test_alarm_bits_and_summary_coils_after_ingest(rig):
    client = rig.client()
    assert registers(client, ALARM_BITS_LIVE, 2) == [0b10001, 0]
    coils = client.read_coils(0, count=6, slave=1).bits[:6]
    # kritik yok, uyari var, haberlesme var, bakim yok, koruma sagligi var, veri kalitesi yok (GIRIS_N q=4)
    assert coils == [False, True, True, False, True, False]
    assert client.read_discrete_inputs(0, count=6, slave=1).bits[:6] == coils


def test_unmapped_unit_is_gateway_path_unavailable(rig):
    assert exception_code(rig.client().read_holding_registers(100, count=1, slave=2)) == ExceptionCode.GATEWAY_PATH_UNAVAILABLE


def test_mapped_panel_without_data_is_target_failed(make_rig):
    rig = make_rig(units={1: "ADM-00002"})
    assert exception_code(rig.client().read_holding_registers(100, count=1, slave=1)) == ExceptionCode.GATEWAY_TARGET_FAILED


def test_panel_without_loaded_alarm_state_is_target_failed(make_rig, tel_payload):
    """Alarm yoneticisi yuklenmeden alarm bitleri 0 okunursa SCADA 'alarm yok' sanar: veri verilmez."""
    rig = make_rig(wire_alarms=False)
    rig.ingest(tel_payload)
    assert exception_code(rig.client().read_holding_registers(100, count=1, slave=1)) == ExceptionCode.GATEWAY_TARGET_FAILED


@pytest.mark.parametrize("address,count", [(40, 1), (148, 4), (905, 10)])
def test_address_outside_blocks_is_illegal_address(rig, address, count):
    result = rig.client().read_holding_registers(address, count=count, slave=1)
    assert exception_code(result) == ExceptionCode.ILLEGAL_DATA_ADDRESS


def test_address_check_comes_before_unit_data(make_rig):
    """Harita statiktir: hedefin verisi olmasa da gecersiz adres 0x02'dir (0x0B degil)."""
    rig = make_rig(units={1: "ADM-00002"})
    assert exception_code(rig.client().read_holding_registers(40, count=1, slave=1)) == ExceptionCode.ILLEGAL_DATA_ADDRESS


def test_coil_range_is_limited_to_contract_coils(rig):
    assert exception_code(rig.client().read_coils(0, count=7, slave=1)) == ExceptionCode.ILLEGAL_DATA_ADDRESS


def test_older_sample_does_not_overwrite_newer_state(rig, tel_payload):
    older = copy.deepcopy(tel_payload)
    older["ts"] = "2026-09-13T09:59:00+00:00"
    older["seq"] = 41
    older["t_conn"][0]["t_c"] = 99.9
    rig.ingest(older)
    assert registers(rig.client(), 100) == [415]


def test_comms_coil_follows_wall_clock(rig, contracts):
    client = rig.client()
    rig.clock.advance(contracts.thresholds["heartbeat_timeout_min"] + 1)
    assert client.read_coils(2, count=1, slave=1).bits[0] is False


def test_event_block_counts_alarm_openings(rig, contracts):
    newest = max(rig.alarms.open_alarms(PANO), key=lambda a: a.id)
    count, last_code, ts_hi, ts_lo = registers(rig.client(), EVENT_COUNT, 4)
    assert count == 2
    assert last_code == contracts.alarm(newest.code)["bit"]
    assert (ts_hi << 16) | ts_lo == int(utc(2026, 9, 13, 10, 0, 0).timestamp())  # olay zamani = telemetri ts


# ------------------------------------------------------------------ otomatik birim eslemesi
def test_auto_units_follow_sorted_panel_ids(make_rig, tel_payload):
    rig = make_rig(units=None)
    for pano_id, t_c in (("GDZ-00001", 30.0), ("ADM-00002", 20.0), ("ADM-00001", 10.0)):
        payload = copy.deepcopy(tel_payload)
        payload["pano_id"] = pano_id
        payload["t_conn"][0]["t_c"] = t_c
        rig.ingest(payload)
    assert rig.gateway.units() == {1: "ADM-00001", 2: "ADM-00002", 3: "GDZ-00001"}
    client = rig.client()
    assert [registers(client, 100, unit=unit)[0] for unit in (1, 2, 3)] == [100, 200, 300]


def test_auto_units_are_capped_at_247(make_rig):
    rig = make_rig(units=None)
    for n in range(250):
        rig.store.add_panel(pano_id=f"SIM-{n:05d}", name=f"SIM-{n:05d}")
    rig.gateway.refresh()
    units = rig.gateway.units()
    assert len(units) == 247
    assert (units[1], units[247]) == ("SIM-00000", "SIM-00246")


# ------------------------------------------------------------------ yeniden baslatma
def test_refresh_restores_last_state_from_store(make_rig, tel_payload):
    """Backend yeniden basladiginda panonun son durumu ve acik alarmlari, yeni telemetri gelmeden sunulur."""
    first = make_rig()
    first.ingest(tel_payload)
    restarted = make_rig(store=first.store)  # ayni veritabani, bos bellek
    restarted.alarms.load()  # uygulama acilisinda oldugu gibi
    restarted.gateway.refresh()
    client = restarted.client()
    assert registers(client, 100, 2) == [415, 780]
    assert registers(client, ALARM_BITS_LIVE) == [0b10001]
    assert registers(client, 4) == [1]  # device_info.pano_type: panels tablosundan (1600kVA-dahili)


def test_explicit_units_ignore_other_panels(make_rig, tel_payload):
    rig = make_rig(units={5: "GDZ-00123"})
    rig.ingest(tel_payload)  # ADM-00001 eslenmemis
    assert rig.gateway.units() == {5: "GDZ-00123"}


def test_refresh_propagates_store_errors(make_rig):
    rig = make_rig(units=None)
    rig.store.unavailable = True
    with pytest.raises(StoreError):
        rig.gateway.refresh()


# ------------------------------------------------------------------ yazma politikasi
def test_writes_are_disabled_without_password(make_rig, tel_payload):
    rig = make_rig(password=None)
    rig.ingest(tel_payload)
    result = rig.client().write_register(900, 1234, slave=1)
    assert exception_code(result) == ExceptionCode.ILLEGAL_FUNCTION


@pytest.mark.parametrize(
    "address,values",
    [
        (501, [0]),  # TVOC-2 trip sayaci aynasi (GK6)
        (500, [PASSWORD, 0]),
        (899, [0, PASSWORD]),  # komut blogunun disindan baslayan yazma
        (100, [1]),
    ],
)
def test_write_outside_command_block_is_illegal_address(rig, address, values):
    client = rig.client()
    unlock(client)
    result = client.write_registers(address, values, slave=1)
    assert exception_code(result) == ExceptionCode.ILLEGAL_DATA_ADDRESS
    assert acked_codes(rig) == set()


def test_command_without_unlock_is_rejected(rig):
    result = rig.client().write_register(901, 0xFFFF, slave=1)
    assert exception_code(result) == ExceptionCode.ILLEGAL_FUNCTION
    assert acked_codes(rig) == set()


def test_wrong_password_is_illegal_value(rig):
    client = rig.client()
    assert exception_code(client.write_register(900, 1111, slave=1)) == ExceptionCode.ILLEGAL_DATA_VALUE
    assert exception_code(client.write_registers(900, [1111, 0xFFFF], slave=1)) == ExceptionCode.ILLEGAL_DATA_VALUE
    assert acked_codes(rig) == set()


def test_repeated_wrong_passwords_lock_out_the_client(rig):
    client = rig.client()
    for _ in range(3):
        client.write_register(900, 1111, slave=1)
    assert exception_code(client.write_register(900, PASSWORD, slave=1)) == ExceptionCode.ILLEGAL_FUNCTION
    assert not rig.client().read_holding_registers(100, count=1, slave=1).isError()  # okuma surer
    rig.monotonic.now += 301
    assert not client.write_register(900, PASSWORD, slave=1).isError()


def test_successful_login_resets_failure_count(rig):
    client = rig.client()
    for _ in range(2):
        client.write_register(900, 1111, slave=1)
    unlock(client)
    for _ in range(2):
        client.write_register(900, 1111, slave=1)
    assert not client.write_register(900, PASSWORD, slave=1).isError()


def test_unlock_expires(rig):
    client = rig.client()
    unlock(client)
    rig.monotonic.now += 61
    assert exception_code(client.write_register(902, 1, slave=1)) == ExceptionCode.ILLEGAL_FUNCTION


def test_unlock_is_per_connection(rig):
    unlock(rig.client())
    assert exception_code(rig.client().write_register(901, 0xFFFF, slave=1)) == ExceptionCode.ILLEGAL_FUNCTION


def test_password_register_reads_zero(rig):
    client = rig.client()
    unlock(client)
    assert registers(client, 900) == [0]


# ------------------------------------------------------------------ komutlar
def test_ack_all_with_password_in_same_request(rig):
    result = rig.client().write_registers(900, [PASSWORD, 0xFFFF], slave=1)
    assert not result.isError()
    assert acked_codes(rig) == {"ALM-THR-TERM-WARN", "ALM-K-WARN"}
    acked = rig.alarms.open_alarms(PANO)[0]
    assert acked.acked_by == "SCADA Modbus 127.0.0.1 (birim 1)"


def test_ack_single_alarm_by_bit(rig):
    client = rig.client()
    unlock(client)
    assert not client.write_register(901, 4 + 1, slave=1).isError()  # deger = bit + 1
    assert acked_codes(rig) == {"ALM-K-WARN"}


def test_ack_value_zero_is_no_op(rig):
    client = rig.client()
    assert not client.write_registers(900, [PASSWORD, 0], slave=1).isError()
    assert acked_codes(rig) == set()


@pytest.mark.parametrize(
    "values",
    [
        [PASSWORD, 0xFFFF, 7],  # reset_latch yalnizca 0/1
        [PASSWORD, 0xFFFF, 0, 3],  # maint_mode yalnizca 0/1/2
        [PASSWORD, 0xFFFF, 0, 0, 2],  # test_alarm yalnizca 0/1
        [PASSWORD, 33],  # 32'den buyuk bit yok
        [PASSWORD, 0xFFFF, 0, 0, 0, 1],  # 905 yedek register: yalnizca 0
    ],
)
def test_invalid_command_value_rejects_whole_request(rig, values):
    result = rig.client().write_registers(900, values, slave=1)
    assert exception_code(result) == ExceptionCode.ILLEGAL_DATA_VALUE
    assert acked_codes(rig) == set()
    assert rig.commands.sent == []


def test_reset_latch_clears_bits_of_alarms_that_are_gone(rig, tel_payload):
    cleared = copy.deepcopy(tel_payload)
    cleared["ts"] = "2026-09-13T10:06:00+00:00"
    cleared["seq"] = 43
    cleared["alarms"] = []  # kenar kosullari artik bildirmiyor
    rig.clock.now = utc(2026, 9, 13, 10, 6, 2)
    rig.ingest(cleared)  # histerezis (5 dk) doldu: iki P3 temizlendi
    client = rig.client()
    assert registers(client, ALARM_BITS_LIVE) == [0]
    assert registers(client, ALARM_BITS_LATCHED) == [0b10001]  # mandal suruyor
    assert not client.write_registers(900, [PASSWORD, 0, 1], slave=1).isError()
    assert registers(client, ALARM_BITS_LATCHED) == [0]


def test_maintenance_and_test_alarm_are_forwarded_to_edge(rig):
    client = rig.client()
    assert not client.write_registers(900, [PASSWORD, 0, 0, 1, 1], slave=1).isError()
    assert not client.write_register(903, 2, slave=1).isError()
    assert rig.commands.sent == [
        (PANO, "maint_mode", {"on": True}),
        (PANO, "test_alarm", {}),
        (PANO, "maint_mode", {"on": False}),
    ]


def test_edge_command_without_channel_is_target_failed_and_nothing_runs(make_rig, tel_payload):
    rig = make_rig(sink=False)
    rig.ingest(tel_payload)
    result = rig.client().write_registers(900, [PASSWORD, 0xFFFF, 0, 1], slave=1)
    assert exception_code(result) == ExceptionCode.GATEWAY_TARGET_FAILED
    assert acked_codes(rig) == set()  # ayni istekteki onay da calismadi


def test_edge_channel_refusal_is_target_failed(rig):
    rig.commands.accept = False
    result = rig.client().write_registers(900, [PASSWORD, 0, 0, 0, 1], slave=1)
    assert exception_code(result) == ExceptionCode.GATEWAY_TARGET_FAILED


def test_maintenance_register_reads_edge_state(rig, tel_payload):
    in_maintenance = copy.deepcopy(tel_payload)
    in_maintenance["ts"] = "2026-09-13T10:00:10+00:00"
    in_maintenance["seq"] = 43
    in_maintenance["health"]["maint_mode"] = True
    rig.ingest(in_maintenance)
    assert registers(rig.client(), MAINT_REGISTER) == [1]


def test_command_to_unmapped_unit_is_gateway_path_unavailable(rig):
    result = rig.client().write_registers(900, [PASSWORD, 0xFFFF], slave=9)
    assert exception_code(result) == ExceptionCode.GATEWAY_PATH_UNAVAILABLE


# ------------------------------------------------------------------ yapilandirma
def test_parse_units(contracts):
    assert parse_units("1=ADM-00001, 2=GDZ-00123", contracts.pano_id_re) == {1: "ADM-00001", 2: "GDZ-00123"}
    assert parse_units("", contracts.pano_id_re) == {}


@pytest.mark.parametrize(
    "spec",
    ["0=ADM-00001", "248=ADM-00001", "1=adm-1", "1=ADM-00001,1=ADM-00002", "1=ADM-00001,2=ADM-00001", "ADM-00001", "x=ADM-00001"],
)
def test_parse_units_rejects_invalid(contracts, spec):
    with pytest.raises(ValueError):
        parse_units(spec, contracts.pano_id_re)


def test_parse_password():
    assert parse_password("") is None
    assert parse_password("4242") == 4242
    for bad in ("0", "65536", "sifre", "-1"):
        with pytest.raises(ValueError):
            parse_password(bad)


def test_ack_includes_shelved_alarms(rig):
    """Rafa alinmis alarm da onaylanabilir (alarm_manager.ack ile ayni kural)."""
    k_warn = next(a for a in rig.alarms.open_alarms(PANO) if a.code == "ALM-K-WARN")
    rig.alarms.shelve(k_warn.id, by="operator", minutes=30, reason="planli bakim bekleniyor")
    assert not rig.client().write_registers(900, [PASSWORD, 0xFFFF], slave=1).isError()
    assert acked_codes(rig) == {"ALM-THR-TERM-WARN", "ALM-K-WARN"}


def test_ack_before_alarm_state_is_loaded_is_target_failed(make_rig, tel_payload):
    rig = make_rig(wire_alarms=False)
    rig.ingest(tel_payload)
    result = rig.client().write_registers(900, [PASSWORD, 0xFFFF], slave=1)
    assert exception_code(result) == ExceptionCode.GATEWAY_TARGET_FAILED


def test_new_sample_advances_last_receive_time(rig, tel_payload, contracts):
    timeout = contracts.thresholds["heartbeat_timeout_min"]
    newer = copy.deepcopy(tel_payload)
    newer["ts"] = "2026-09-13T10:04:00+00:00"
    newer["seq"] = 43
    rig.clock.advance(4)
    rig.ingest(newer)
    rig.clock.advance(timeout - 1)  # ilk ornekten timeout+3 dk, son ornekten timeout-1 dk sonra
    assert rig.client().read_coils(2, count=1, slave=1).bits[0] is True


def test_refresh_sets_type_of_panels_already_live(rig):
    client = rig.client()
    assert registers(client, 4) == [0]  # ingest'te pano tipi yok: bilinmiyor
    rig.gateway.refresh()
    assert registers(client, 4) == [1]  # panels tablosu: 1600kVA-dahili


def test_fixed_units_do_not_track_unmapped_panels(rig, tel_payload):
    other = copy.deepcopy(tel_payload)
    other["pano_id"] = "ADM-00002"
    rig.ingest(other)
    assert rig.gateway.status() == {"units": 1, "auto_units": False, "tracked_panels": 1, "writes_enabled": True, "locked_clients": 0}


def test_status_counts_locked_clients(rig):
    client = rig.client()
    for _ in range(3):
        client.write_register(900, 1111, slave=1)
    assert rig.gateway.status()["locked_clients"] == 1
    rig.monotonic.now += 301
    assert rig.gateway.status()["locked_clients"] == 0
