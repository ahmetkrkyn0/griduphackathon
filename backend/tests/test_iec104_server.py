"""TB3 Adim 8 (Could) — IEC 60870-5-104 kontrollu istasyon sunucusu (app.scada.iec104_server).

Sunucu gercek TCP'de, arka plan dongusunde; istemci ham soket + tests edilmis kodlayici. Kilit cerceveler standarttan elle yazilmis
bayt dizileridir. Istasyon kaynagi basit bir bellek kaynagidir; ag gecidi ile baglanti tests/test_scada_app.py'de sinanir.

Zamanlayicilar (standart varsayilanlar t1 15 s, t2 10 s, t3 20 s, k 12, w 8) testte kisaltilir.
"""

from __future__ import annotations

import socket
import struct
import time

import pytest

from app.scada import iec104
from app.scada.iec104 import IFrame, SFrame, UFrame, UFunction
from app.scada.iec104_points import PointValue
from app.scada.iec104_server import Iec104Server, Timing
from helpers import LoopThread, utc

LOCAL = ("127.0.0.0/8",)
GI_STATION_1 = bytes.fromhex("64 01 06 00 01 00 00 00 00 14")


class Stations:
    """Iki istasyon (ortak adres 1 ve 2); deger listesi test icinde degistirilir."""

    def __init__(self) -> None:
        self.values = {
            1: [
                PointValue(1101, iec104.M_ME_NC_1, 78.0, 0),
                PointValue(1104, iec104.M_ME_NC_1, 0.0, iec104.QDS_IV),
                PointValue(2004, iec104.M_SP_NA_1, True, 0),
            ],
            2: [PointValue(1101, iec104.M_ME_NC_1, 20.0, 0)],
        }
        self.now = utc(2026, 9, 13, 10, 1, 2, 345000)

    def common_addresses(self):
        return sorted(self.values)

    def point_values(self, common_address):
        values = self.values.get(common_address)
        return list(values) if values is not None else None

    def deadband(self, ioa):
        return 1.0

    def clock(self):
        return self.now

    def set_value(self, common_address, ioa, value, quality=0):
        self.values[common_address] = [
            PointValue(v.ioa, v.type_id, value, quality) if v.ioa == ioa else v for v in self.values[common_address]
        ]


class Client:
    def __init__(self, port: int) -> None:
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=2)
        self.send_seq = 0
        self.recv_seq = 0

    def send(self, raw: bytes) -> None:
        self.sock.sendall(raw)

    def startdt(self) -> None:
        self.send(iec104.encode_u(UFunction.STARTDT_ACT))
        assert self.read() == UFrame(UFunction.STARTDT_CON)

    def send_asdu(self, asdu: bytes) -> None:
        self.send(iec104.encode_i(self.send_seq, self.recv_seq, asdu))
        self.send_seq += 1

    def ack(self) -> None:
        self.send(iec104.encode_s(self.recv_seq))

    def read_raw(self, timeout: float = 2.0) -> bytes:
        self.sock.settimeout(timeout)
        head = self._exactly(2)
        return head + self._exactly(head[1])

    def read(self, timeout: float = 2.0):
        frame = iec104.decode_apdu(self.read_raw(timeout))
        if isinstance(frame, IFrame):
            assert frame.send_seq == self.recv_seq, "sunucu sira numarasi atladi"
            self.recv_seq += 1
        return frame

    def read_until_termination(self, timeout: float = 2.0) -> list[iec104.Asdu]:
        asdus = []
        while True:
            frame = self.read(timeout)
            if isinstance(frame, IFrame):
                asdu = iec104.decode_asdu(frame.asdu)
                asdus.append(asdu)
                if asdu.cot == iec104.COT_ACTIVATION_TERM:
                    return asdus

    def silent(self, seconds: float) -> bool:
        self.sock.settimeout(seconds)
        try:
            return self.sock.recv(1) == b"" and False
        except socket.timeout:
            return True

    def closed(self, timeout: float = 2.0) -> bool:
        deadline = time.monotonic() + timeout
        self.sock.settimeout(timeout)
        try:
            while time.monotonic() < deadline:
                if self.sock.recv(4096) == b"":
                    return True
            return False
        except (ConnectionResetError, ConnectionAbortedError):
            return True
        except socket.timeout:
            return False

    def _exactly(self, size: int) -> bytes:
        data = b""
        while len(data) < size:
            chunk = self.sock.recv(size - len(data))
            if not chunk:
                raise ConnectionError("baglanti kapandi")
            data += chunk
        return data

    def close(self) -> None:
        self.sock.close()


@pytest.fixture
def loop():
    thread = LoopThread()
    yield thread
    thread.close()


@pytest.fixture
def stations() -> Stations:
    return Stations()


@pytest.fixture
def start_server(loop, stations):
    servers, clients = [], []

    def start(timing: Timing = Timing(), **options) -> tuple[Iec104Server, Client]:
        options.setdefault("allowed_networks", LOCAL)
        server = Iec104Server(stations, host="127.0.0.1", port=0, timing=timing, **options)
        loop.run(server.start())
        servers.append(server)
        client = Client(server.port)
        clients.append(client)
        return server, client

    yield start
    for client in clients:
        client.close()
    for server in servers:
        loop.run(server.stop())


def send_without_ack(client: Client, asdu: bytes) -> None:
    """N(R) = 0: sunucunun gonderdigi cerceveyi ONAYLAMADAN yeni I cercevesi (pencere dolu kalir)."""
    client.send(iec104.encode_i(client.send_seq, 0, asdu))
    client.send_seq += 1


def objects_by_station(asdus, cot):
    found = {}
    for asdu in asdus:
        if asdu.cot == cot:
            for ioa, element in asdu.objects:
                found[(asdu.common_address, ioa)] = (asdu.type_id, element)
    return found


# ------------------------------------------------------------------ U cerceveleri
def test_startdt_testfr_stopdt(start_server):
    _, client = start_server()
    client.send(bytes.fromhex("68 04 07 00 00 00"))
    assert client.read_raw() == bytes.fromhex("68 04 0B 00 00 00")
    client.send(bytes.fromhex("68 04 43 00 00 00"))
    assert client.read_raw() == bytes.fromhex("68 04 83 00 00 00")
    client.send(bytes.fromhex("68 04 13 00 00 00"))
    assert client.read_raw() == bytes.fromhex("68 04 23 00 00 00")


def test_i_frame_before_startdt_closes_connection(start_server):
    _, client = start_server()
    client.send_asdu(GI_STATION_1)
    assert client.closed()


def test_acknowledging_frames_never_sent_closes_connection(start_server):
    _, client = start_server()
    client.startdt()
    client.send(iec104.encode_s(5))  # sunucu henuz I cercevesi gondermedi
    assert client.closed()


def test_sequence_error_closes_connection(start_server):
    _, client = start_server()
    client.startdt()
    client.send(iec104.encode_i(5, 0, GI_STATION_1))  # beklenen N(S) = 0
    assert client.closed()


# ------------------------------------------------------------------ genel sorgulama
def test_general_interrogation(start_server):
    _, client = start_server()
    client.startdt()
    client.send(bytes.fromhex("68 0E 00 00 00 00 64 01 06 00 01 00 00 00 00 14"))
    client.send_seq = 1
    assert client.read_raw() == bytes.fromhex("68 0E 00 00 02 00 64 01 07 00 01 00 00 00 00 14")  # ACTCON, N(R) = 1
    client.recv_seq = 1
    asdus = client.read_until_termination()
    assert iec104.encode_asdu(asdus[-1]) == bytes.fromhex("64 01 0A 00 01 00 00 00 00 14")  # ACTTERM
    data = objects_by_station(asdus, iec104.COT_INTERROGATED)
    assert data == {
        (1, 1101): (iec104.M_ME_NC_1, struct.pack("<fB", 78.0, 0)),
        (1, 1104): (iec104.M_ME_NC_1, struct.pack("<fB", 0.0, 0x80)),
        (1, 2004): (iec104.M_SP_NA_1, b"\x01"),
    }


def test_broadcast_interrogation_is_answered_by_each_station_with_its_own_address(start_server):
    # IEC 60870-5-101/104 7.2.4: global adrese (FFFF) gelen komut izleme yonunde istasyonun KENDI ortak adresiyle cevaplanir.
    # Istasyon basina GI izleyen ana istasyon ACTCON/ACTTERM'i kendi adresinde bekler.
    server, client = start_server()
    client.startdt()
    client.send_asdu(bytes.fromhex("64 01 06 00 FF FF 00 00 00 14"))
    station_1 = client.read_until_termination()
    station_2 = client.read_until_termination()
    assert iec104.encode_asdu(station_1[0]) == bytes.fromhex("64 01 07 00 01 00 00 00 00 14")  # ACTCON, CA 1
    assert iec104.encode_asdu(station_1[-1]) == bytes.fromhex("64 01 0A 00 01 00 00 00 00 14")  # ACTTERM, CA 1
    assert iec104.encode_asdu(station_2[0]) == bytes.fromhex("64 01 07 00 02 00 00 00 00 14")
    assert iec104.encode_asdu(station_2[-1]) == bytes.fromhex("64 01 0A 00 02 00 00 00 00 14")
    assert {key[0] for key in objects_by_station(station_1, iec104.COT_INTERROGATED)} == {1}
    assert set(objects_by_station(station_2, iec104.COT_INTERROGATED)) == {(2, 1101)}
    assert server.stats["interrogations"] == 1
    assert client.silent(0.3)


def test_broadcast_interrogation_without_any_station_is_rejected_at_once(start_server, stations):
    stations.values = {}  # henuz veri gelmemis merkez: ana istasyon zaman asimini beklemesin
    _, client = start_server()
    client.startdt()
    client.send_asdu(bytes.fromhex("64 01 06 00 FF FF 00 00 00 14"))
    assert iec104.decode_apdu(client.read_raw()).asdu == bytes.fromhex("64 01 6E 00 FF FF 00 00 00 14")  # P/N + 46


def test_station_removed_during_broadcast_interrogation_is_rejected_with_its_own_address(start_server, stations):
    stations.common_addresses = lambda: [1, 2, 3]  # birim 3 listelendi ama degeri istenirken eslemeden cikmisti
    _, client = start_server()
    client.startdt()
    client.send_asdu(bytes.fromhex("64 01 06 00 FF FF 00 00 00 14"))
    client.read_until_termination()
    client.read_until_termination()
    assert client.read().asdu == bytes.fromhex("64 01 6E 00 03 00 00 00 00 14")  # P/N + 46, CA 3


def test_interrogation_of_unknown_station_is_rejected(start_server):
    _, client = start_server()
    client.startdt()
    client.send_asdu(bytes.fromhex("64 01 06 00 09 00 00 00 00 14"))
    assert iec104.decode_apdu(client.read_raw()).asdu == bytes.fromhex("64 01 6E 00 09 00 00 00 00 14")  # P/N + 46


def test_group_interrogation_is_not_supported(start_server):
    _, client = start_server()
    client.startdt()
    client.send_asdu(bytes.fromhex("64 01 06 00 01 00 00 00 00 15"))  # QOI 21 = grup 1
    reply = iec104.decode_asdu(client.read().asdu)
    assert (reply.cot, reply.negative) == (iec104.COT_ACTIVATION_CON, True)
    assert client.silent(0.3)


def test_broadcast_group_interrogation_is_refused_by_each_station(start_server):
    _, client = start_server()
    client.startdt()
    client.send_asdu(bytes.fromhex("64 01 06 00 FF FF 00 00 00 15"))
    assert client.read().asdu == bytes.fromhex("64 01 47 00 01 00 00 00 00 15")  # ACTCON + P/N, CA 1
    assert client.read().asdu == bytes.fromhex("64 01 47 00 02 00 00 00 00 15")
    assert client.silent(0.3)


def test_interrogation_with_wrong_cause_is_rejected(start_server):
    _, client = start_server()
    client.startdt()
    client.send_asdu(bytes.fromhex("64 01 03 00 01 00 00 00 00 14"))  # COT 3 (spontane) ile komut
    reply = iec104.decode_asdu(client.read().asdu)
    assert (reply.cot, reply.negative) == (iec104.COT_UNKNOWN_CAUSE, True)


# ------------------------------------------------------------------ komutlar
def test_control_commands_are_rejected_because_the_station_is_read_only(start_server):
    server, client = start_server()
    client.startdt()
    command = bytes.fromhex("2D 01 06 00 01 00 D0 07 00 01")  # C_SC_NA_1: IOA 2000'e "ac"
    client.send_asdu(command)
    assert iec104.decode_apdu(client.read_raw()).asdu == bytes.fromhex("2D 01 6C 00 01 00 D0 07 00 01")  # P/N + 44
    assert server.stats["rejected_commands"] == 1


def test_unknown_type_is_rejected(start_server):
    _, client = start_server()
    client.startdt()
    client.send_asdu(bytes.fromhex("3A 01 06 00 01 00 D0 07 00 01 00 00 00 00 00 00 00"))  # C_SC_TA_1 (58)
    reply = client.read().asdu
    assert reply[2] == 0x40 | iec104.COT_UNKNOWN_TYPE


def test_clock_sync_is_confirmed_with_station_time(start_server, stations):
    _, client = start_server()
    client.startdt()
    requested = iec104.cp56time2a(utc(2030, 1, 1))
    client.send_asdu(bytes.fromhex("67 01 06 00 01 00 00 00 00") + requested)
    reply = iec104.decode_asdu(client.read().asdu)
    assert (reply.type_id, reply.cot, reply.negative) == (iec104.C_CS_NA_1, iec104.COT_ACTIVATION_CON, False)
    assert reply.objects == ((0, iec104.cp56time2a(stations.now)),)  # istasyon saatini disaridan degistirmeyiz


def test_clock_sync_with_wrong_cause_is_rejected(start_server):
    _, client = start_server()
    client.startdt()
    requested = iec104.cp56time2a(utc(2030, 1, 1))
    client.send_asdu(bytes.fromhex("67 01 03 00 01 00 00 00 00") + requested)  # COT 3 (spontane) ile komut
    assert client.read().asdu == bytes.fromhex("67 01 6D 00 01 00 00 00 00") + requested  # P/N + 45


def test_clock_sync_of_unknown_station_is_rejected(start_server):
    _, client = start_server()
    client.startdt()
    requested = iec104.cp56time2a(utc(2030, 1, 1))
    client.send_asdu(bytes.fromhex("67 01 06 00 09 00 00 00 00") + requested)
    assert client.read().asdu == bytes.fromhex("67 01 6E 00 09 00 00 00 00") + requested  # P/N + 46


def test_broadcast_clock_sync_is_confirmed_by_each_station(start_server, stations):
    _, client = start_server()
    client.startdt()
    client.send_asdu(bytes.fromhex("67 01 06 00 FF FF 00 00 00") + iec104.cp56time2a(utc(2030, 1, 1)))
    station_time = iec104.cp56time2a(stations.now)
    assert client.read().asdu == bytes.fromhex("67 01 07 00 01 00 00 00 00") + station_time
    assert client.read().asdu == bytes.fromhex("67 01 07 00 02 00 00 00 00") + station_time
    assert client.silent(0.3)


# ------------------------------------------------------------------ akis denetimi ve zamanlayicilar
def test_k_window_waits_for_acknowledgement(start_server):
    _, client = start_server(Timing(k=2))
    client.startdt()
    client.send_asdu(bytes.fromhex("64 01 06 00 FF FF 00 00 00 14"))
    first, second = client.read(), client.read()
    assert isinstance(first, IFrame) and isinstance(second, IFrame)
    assert client.silent(0.4)  # 2 onaysiz cercevede durdu
    client.ack()
    assert isinstance(client.read(), IFrame)


def test_received_frames_are_acknowledged_after_t2_when_nothing_can_be_sent(start_server):
    _, client = start_server(Timing(k=1, t2=0.3))
    client.startdt()
    sync = bytes.fromhex("67 01 06 00 01 00 00 00 00") + iec104.cp56time2a(utc(2030, 1, 1))
    client.send_asdu(sync)
    assert isinstance(client.read(), IFrame)  # ACTCON; pencere doldu
    send_without_ack(client, sync)  # cevabi gonderilemez: pencere dolu ve onay yok
    assert client.read(timeout=2.0) == SFrame(2)


def test_w_received_frames_trigger_immediate_acknowledgement(start_server):
    _, client = start_server(Timing(k=1, w=2, t2=30.0))
    client.startdt()
    sync = bytes.fromhex("67 01 06 00 01 00 00 00 00") + iec104.cp56time2a(utc(2030, 1, 1))
    client.send_asdu(sync)
    assert isinstance(client.read(), IFrame)  # ACTCON ilk komutu N(R) ile onayladi; pencere doldu
    send_without_ack(client, sync)
    send_without_ack(client, sync)  # onaysiz alinan 2 = w
    assert client.read(timeout=1.0) == SFrame(3)


def test_unacknowledged_frames_close_the_connection_after_t1(start_server):
    _, client = start_server(Timing(t1=0.4, t3=30.0))
    client.startdt()
    client.send_asdu(GI_STATION_1)
    client.read_until_termination()
    assert client.closed(timeout=3.0)


def test_idle_connection_is_tested_after_t3_and_stays_open_while_answered(start_server):
    _, client = start_server(Timing(t3=0.2, t1=0.5))
    client.startdt()
    answered = 0
    deadline = time.monotonic() + 1.5  # t1'in uc kati: cevap temizlenmeseydi baglanti kapanirdi
    while time.monotonic() < deadline:
        frame = client.read(timeout=1.0)
        assert frame == UFrame(UFunction.TESTFR_ACT)
        client.send(iec104.encode_u(UFunction.TESTFR_CON))
        answered += 1
    assert answered >= 3


def test_unanswered_test_frame_closes_the_connection(start_server):
    _, client = start_server(Timing(t3=0.2, t1=0.4))
    client.startdt()
    assert client.read(timeout=2.0) == UFrame(UFunction.TESTFR_ACT)
    assert client.closed(timeout=3.0)


# ------------------------------------------------------------------ kendiliginden gonderim
def test_changes_beyond_deadband_are_sent_spontaneously_with_time_tag(start_server, stations):
    _, client = start_server(Timing(spontaneous=0.05))
    client.startdt()
    stations.set_value(1, 1101, 78.5)  # olu bant (1,0) altinda
    assert client.silent(0.3)
    stations.set_value(1, 1101, 79.0)  # tam olu bant kadar: gonderilir
    frame = client.read()
    asdu = iec104.decode_asdu(frame.asdu)
    assert (asdu.type_id, asdu.cot, asdu.common_address) == (iec104.M_ME_TF_1, iec104.COT_SPONTANEOUS, 1)
    assert asdu.objects == ((1101, struct.pack("<fB", 79.0, 0) + iec104.cp56time2a(stations.now)),)


def test_alarm_bit_change_is_sent_spontaneously(start_server, stations):
    _, client = start_server(Timing(spontaneous=0.05))
    client.startdt()
    stations.set_value(1, 2004, False)
    asdu = iec104.decode_asdu(client.read().asdu)
    assert (asdu.type_id, asdu.cot) == (iec104.M_SP_TB_1, iec104.COT_SPONTANEOUS)
    assert asdu.objects == ((2004, b"\x00" + iec104.cp56time2a(stations.now)),)


def test_quality_change_is_sent_even_without_value_change(start_server, stations):
    _, client = start_server(Timing(spontaneous=0.05))
    client.startdt()
    stations.set_value(1, 1101, 78.0, iec104.QDS_IV)
    asdu = iec104.decode_asdu(client.read().asdu)
    assert asdu.objects[0][1][4] == iec104.QDS_IV


def test_no_spontaneous_data_after_stopdt(start_server, stations):
    _, client = start_server(Timing(spontaneous=0.05))
    client.startdt()
    client.send(iec104.encode_u(UFunction.STOPDT_ACT))
    assert client.read() == UFrame(UFunction.STOPDT_CON)
    stations.set_value(1, 1101, 90.0)
    assert client.silent(0.4)


# ------------------------------------------------------------------ baglanti politikasi
def test_client_outside_allowlist_is_dropped(loop, stations):
    server = Iec104Server(stations, host="127.0.0.1", port=0, allowed_networks=("10.0.0.0/8",))
    loop.run(server.start())
    try:
        client = Client(server.port)
        client.send(iec104.encode_u(UFunction.STARTDT_ACT))
        assert client.closed()
        client.close()
        assert server.stats["rejected_clients"] == 1
    finally:
        loop.run(server.stop())


def test_stop_closes_open_connections(loop, stations):
    server = Iec104Server(stations, host="127.0.0.1", port=0, allowed_networks=LOCAL)
    loop.run(server.start())
    client = Client(server.port)
    client.startdt()
    started = time.monotonic()
    loop.run(server.stop(), timeout=5)
    assert time.monotonic() - started < 2.0
    assert client.closed()
    client.close()
