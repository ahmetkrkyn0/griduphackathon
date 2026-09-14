"""TB3 Adim 2 — Modbus TCP sunucusu: cerceve, fonksiyon kodlari, istisna yanitlari, baglanti politikasi.

Sunucu (app.scada.modbus_tcp) gercek TCP uzerinde, arka plan thread'indeki olay dongusunde calisir.
Istemci tarafi iki bagimsiz uygulamadir: pymodbus istemcisi (birlikte calisabilirlik) ve elle kurulan
ham cerceveler (spesifikasyon kenar durumlari). Cihaz modeli burada tanimli en basit bellek cihazidir;
gercek ag gecidi politikasi tests/test_scada_gateway.py'de sinanir.

Ham cerceve: MBAP = islem no (2) | protokol 0 (2) | uzunluk = birim + PDU (2) | birim (1), ardindan PDU.
"""

from __future__ import annotations

import socket
import struct
import time

import pytest
from pymodbus.client import ModbusTcpClient

from app.scada.modbus_tcp import ExceptionCode, ModbusError, ModbusTcpServer, client_allowed, parse_networks
from helpers import LoopThread

LOCAL = ("127.0.0.0/8",)


class MemoryDevice:
    """Birim 1: register 0-9 okunur (100..109), 5-9 yazilir; coil 0-3. Birim 99 beklenmedik hata verir."""

    def __init__(self) -> None:
        self.registers = list(range(100, 110))
        self.coils = [True, False, True, True]
        self.calls: list[tuple] = []

    def _check(self, unit: int, address: int, count: int, size: int) -> None:
        if unit == 99:
            raise RuntimeError("cihaz modeli coktu")
        if unit != 1:
            raise ModbusError(ExceptionCode.GATEWAY_PATH_UNAVAILABLE)
        if address + count > size:
            raise ModbusError(ExceptionCode.ILLEGAL_DATA_ADDRESS)

    def read_registers(self, unit: int, address: int, count: int, function: int) -> list[int]:
        self.calls.append(("read_registers", unit, address, count, function))
        self._check(unit, address, count, len(self.registers))
        return self.registers[address : address + count]

    def read_bits(self, unit: int, address: int, count: int, function: int) -> list[bool]:
        self.calls.append(("read_bits", unit, address, count, function))
        self._check(unit, address, count, len(self.coils))
        return self.coils[address : address + count]

    async def write_registers(self, unit: int, address: int, values: list[int], session) -> None:
        self.calls.append(("write_registers", unit, address, list(values), session.peer))
        self._check(unit, address, len(values), len(self.registers))
        if address < 5:
            raise ModbusError(ExceptionCode.ILLEGAL_DATA_ADDRESS)
        self.registers[address : address + len(values)] = values


@pytest.fixture
def loop():
    thread = LoopThread()
    yield thread
    thread.close()


@pytest.fixture
def device() -> MemoryDevice:
    return MemoryDevice()


@pytest.fixture
def start_server(loop, device):
    servers: list[ModbusTcpServer] = []

    def start(**options) -> ModbusTcpServer:
        options.setdefault("allowed_networks", LOCAL)
        server = ModbusTcpServer(device, host="127.0.0.1", port=0, **options)
        loop.run(server.start())
        servers.append(server)
        return server

    yield start
    for server in servers:
        loop.run(server.stop())


@pytest.fixture
def server(start_server) -> ModbusTcpServer:
    return start_server()


@pytest.fixture
def client(server):
    # retries >= 1 sart: pymodbus 3.7.4 senkron istemcisi yanitin MBAP+FC'den sonrasini yalnizca
    # yeniden deneme dongusunde okur (transaction._recv); retries=0 ile her yanit "eksik" sayilir.
    modbus = ModbusTcpClient("127.0.0.1", port=server.port, timeout=2, retries=1)
    assert modbus.connect()
    yield modbus
    modbus.close()


def raw_connect(server) -> socket.socket:
    sock = socket.create_connection(("127.0.0.1", server.port), timeout=2)
    return sock


def frame(tid: int, unit: int, pdu: bytes, protocol: int = 0) -> bytes:
    return struct.pack(">HHHB", tid, protocol, len(pdu) + 1, unit) + pdu


def recv_frame(sock: socket.socket) -> tuple[int, int, bytes]:
    header = recv_exactly(sock, 7)
    tid, protocol, length, unit = struct.unpack(">HHHB", header)
    assert protocol == 0
    return tid, unit, recv_exactly(sock, length - 1)


def recv_exactly(sock: socket.socket, size: int) -> bytes:
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ConnectionError("baglanti kapandi")
        data += chunk
    return data


def is_closed(sock: socket.socket, timeout: float = 2.0) -> bool:
    sock.settimeout(timeout)
    try:
        return sock.recv(1) == b""
    except (ConnectionResetError, ConnectionAbortedError):
        return True
    except socket.timeout:
        return False


# ------------------------------------------------------------------ okuma
def test_read_holding_registers(client, device):
    result = client.read_holding_registers(2, count=3, slave=1)
    assert not result.isError()
    assert result.registers == [102, 103, 104]
    assert device.calls[-1] == ("read_registers", 1, 2, 3, 3)


def test_read_input_registers_reaches_device_with_function_code(client, device):
    result = client.read_input_registers(0, count=2, slave=1)
    assert result.registers == [100, 101]
    assert device.calls[-1] == ("read_registers", 1, 0, 2, 4)


def test_read_coils_and_discrete_inputs(client, device):
    assert client.read_coils(0, count=3, slave=1).bits[:3] == [True, False, True]
    assert device.calls[-1] == ("read_bits", 1, 0, 3, 1)
    assert client.read_discrete_inputs(1, count=3, slave=1).bits[:3] == [False, True, True]
    assert device.calls[-1] == ("read_bits", 1, 1, 3, 2)


def test_raw_read_response_bytes(server):
    """FC03, islem no 0x0102, birim 1: yanit ayni islem no ve birimi tasir, uzunluk = 1 + PDU."""
    with raw_connect(server) as sock:
        sock.sendall(bytes.fromhex("0102 0000 0006 01 03 0000 0003"))
        assert recv_exactly(sock, 15) == bytes.fromhex("0102 0000 0009 01 03 06 0064 0065 0066")


def test_coil_response_packs_bits_lsb_first(server, device):
    device.coils = [True, False, True, True]
    with raw_connect(server) as sock:
        sock.sendall(frame(5, 1, bytes.fromhex("01 0000 0004")))
        assert recv_frame(sock) == (5, 1, bytes.fromhex("01 01 0D"))  # 1011b -> 0x0D


# ------------------------------------------------------------------ yazma
def test_write_single_register_echoes_request(server, device):
    with raw_connect(server) as sock:
        sock.sendall(frame(9, 1, bytes.fromhex("06 0006 1234")))
        assert recv_frame(sock) == (9, 1, bytes.fromhex("06 0006 1234"))
    assert device.registers[6] == 0x1234
    assert device.calls[-1] == ("write_registers", 1, 6, [0x1234], "127.0.0.1")


def test_write_multiple_registers(client, device):
    result = client.write_registers(5, [7, 8, 9], slave=1)
    assert not result.isError()
    assert device.registers[5:8] == [7, 8, 9]


def test_device_error_becomes_exception_response(server):
    with raw_connect(server) as sock:
        sock.sendall(frame(1, 1, bytes.fromhex("06 0001 0005")))  # 0-4 yazilamaz
        assert recv_frame(sock) == (1, 1, bytes.fromhex("86 02"))


def test_unmapped_unit_exception_from_device(client):
    result = client.read_holding_registers(0, count=1, slave=3)
    assert result.isError()
    assert result.exception_code == ExceptionCode.GATEWAY_PATH_UNAVAILABLE


def test_unexpected_device_failure_is_slave_failure_and_connection_survives(server):
    with raw_connect(server) as sock:
        sock.sendall(frame(1, 99, bytes.fromhex("03 0000 0001")))
        assert recv_frame(sock) == (1, 99, bytes.fromhex("83 04"))
        sock.sendall(frame(2, 1, bytes.fromhex("03 0000 0001")))
        assert recv_frame(sock) == (2, 1, bytes.fromhex("03 02 0064"))


# ------------------------------------------------------------------ gecersiz istekler
@pytest.mark.parametrize(
    "pdu,expected",
    [
        ("05 0000 FF00", "85 01"),  # coil yazma desteklenmez
        ("0F 0000 0001 01 01", "8F 01"),  # coklu coil yazma desteklenmez
        ("2B 0E 01 00", "AB 01"),  # cihaz kimligi (FC43) desteklenmez
        ("03 0000 0000", "83 03"),  # 0 register
        ("03 0000 007E", "83 03"),  # 126 register > 125
        ("01 0000 07D1", "81 03"),  # 2001 bit > 2000
        ("03 0000", "83 03"),  # kisa PDU
        ("03 0000 0001 FF", "83 03"),  # uzun PDU
        ("10 0005 0002 03 0001 0002", "90 03"),  # bayt sayisi 2 x adet degil (veri de tutarsiz)
        ("10 0005 0002 03 000100", "90 03"),  # bayt sayisi 2 x adet degil ama veriyle tutarli
        ("10 0005 0000 00", "90 03"),  # 0 register yazma
        ("03 FFFF 0002", "83 02"),  # 65535 + 2 adres uzayini asar
    ],
)
def test_invalid_requests(server, device, pdu, expected):
    calls_before = len(device.calls)
    with raw_connect(server) as sock:
        sock.sendall(frame(3, 1, bytes.fromhex(pdu)))
        assert recv_frame(sock) == (3, 1, bytes.fromhex(expected))
    assert len(device.calls) == calls_before  # gecersiz istek cihaz modeline ulasmaz


def test_non_modbus_protocol_id_closes_connection(server):
    with raw_connect(server) as sock:
        sock.sendall(frame(1, 1, bytes.fromhex("03 0000 0001"), protocol=1))
        assert is_closed(sock)


def test_invalid_mbap_length_closes_connection(server):
    with raw_connect(server) as sock:
        sock.sendall(struct.pack(">HHHB", 1, 0, 1, 1))  # uzunluk 1: PDU yok
        assert is_closed(sock)


# ------------------------------------------------------------------ akis
def test_pipelined_requests_are_answered_in_order(server):
    with raw_connect(server) as sock:
        sock.sendall(frame(10, 1, bytes.fromhex("03 0000 0001")) + frame(11, 1, bytes.fromhex("03 0001 0001")))
        assert recv_frame(sock) == (10, 1, bytes.fromhex("03 02 0064"))
        assert recv_frame(sock) == (11, 1, bytes.fromhex("03 02 0065"))


def test_request_split_across_segments(server):
    request = frame(12, 1, bytes.fromhex("03 0009 0001"))
    with raw_connect(server) as sock:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        for part in (request[:3], request[3:8], request[8:]):
            sock.sendall(part)
            time.sleep(0.05)
        assert recv_frame(sock) == (12, 1, bytes.fromhex("03 02 006D"))


# ------------------------------------------------------------------ baglanti politikasi
def test_client_outside_allowlist_is_dropped(start_server, device):
    server = start_server(allowed_networks=("10.0.0.0/8",))
    with raw_connect(server) as sock:
        sock.sendall(frame(1, 1, bytes.fromhex("03 0000 0001")))
        assert is_closed(sock)
    assert server.stats["rejected_clients"] == 1
    assert device.calls == []


def test_connection_limit(start_server):
    server = start_server(max_connections=1)
    with raw_connect(server) as first:
        first.sendall(frame(1, 1, bytes.fromhex("03 0000 0001")))
        assert recv_frame(first)[0] == 1
        with raw_connect(server) as second:
            assert is_closed(second)
        first.sendall(frame(2, 1, bytes.fromhex("03 0000 0001")))
        assert recv_frame(first)[0] == 2
    assert server.stats["rejected_busy"] == 1


def test_idle_connection_is_closed(start_server):
    server = start_server(idle_timeout_s=0.3)
    with raw_connect(server) as sock:
        assert is_closed(sock, timeout=3.0)


def test_stop_closes_open_connections(loop, device):
    server = ModbusTcpServer(device, host="127.0.0.1", port=0, allowed_networks=LOCAL)
    loop.run(server.start())
    sock = raw_connect(server)
    sock.sendall(frame(1, 1, bytes.fromhex("03 0000 0001")))
    recv_frame(sock)
    started = time.monotonic()
    loop.run(server.stop(), timeout=5)
    assert time.monotonic() - started < 2.0
    assert is_closed(sock)
    sock.close()


@pytest.mark.parametrize(
    "peer,allowed",
    [
        ("10.1.2.3", True),
        ("::ffff:10.1.2.3", True),  # IPv4 eslemeli IPv6 soketi
        ("192.168.1.10", False),
        ("fe80::1", False),
    ],
)
def test_client_allowed(peer, allowed):
    assert client_allowed(peer, parse_networks(["10.0.0.0/8"])) is allowed


def test_parse_networks_rejects_garbage():
    with pytest.raises(ValueError):
        parse_networks(["10.0.0.0/8", "yerel-ag"])
