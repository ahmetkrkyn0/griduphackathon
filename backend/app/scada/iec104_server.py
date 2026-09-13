"""IEC 60870-5-104 kontrollu istasyon (slave) sunucusu (TB3 Adim 8, Could, Kisi B).

Dagitim SCADA'larinda yaygin protokolle ayni veri: her pano bir ortak adres (= Modbus birimi), nokta plani iec104_points.py,
dokuman docs/04. Istasyon SALT OKUNURDUR: kontrol komutlari (C_SC, C_DC ...) COT 44 ile reddedilir (GK6).

Desteklenen:
  - U: STARTDT / STOPDT / TESTFR (act ve con)
  - C_IC_NA_1 istasyon sorgulamasi (QOI 20): ACTCON -> tum noktalar COT 20 -> ACTTERM; ortak adres 0xFFFF tum istasyonlar
  - C_CS_NA_1 saat senkronu: istasyon saatiyle ACTCON (merkez saati disaridan degistirilmez, NTP'nin isidir)
  - Kendiliginden gonderim (COT 3): olculen deger olu banti asinca M_ME_TF_1, tek nokta degisince M_SP_TB_1 (CP56Time2a)
Akis denetimi ve zamanlayicilar standart varsayilanlarla: t1 15 s (onay / TESTFR cevabi beklenir, yoksa baglanti kapanir),
t2 10 s (alinan cercevelerin S ile onayi), t3 20 s (bosta TESTFR), k 12 (onaysiz gonderilen), w 8 (onaysiz alinan).
Protokol hatasi (STARTDT oncesi I cercevesi, sira hatasi, gecersiz N(R), bozuk cerceve) baglantiyi kapatir.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from . import iec104
from .iec104 import Asdu, IFrame, SFrame, UFrame, UFunction
from .iec104_points import PointValue, group_objects
from .modbus_tcp import DEFAULT_ALLOWED_NETWORKS, client_allowed, normalize_peer, parse_networks

log = logging.getLogger("gridup.scada.iec104")

MONITOR_OBJECTS = 30  # zamansiz: 6 + 30 x 8 = 246 bayt
TIME_TAGGED_OBJECTS = 16  # M_ME_TF_1: 6 + 16 x 15 = 246 bayt


class ProtocolError(Exception):
    """Baglantiyi kapatmayi gerektiren IEC 104 ihlali."""


class StationSource(Protocol):
    def common_addresses(self) -> Sequence[int]: ...

    def point_values(self, common_address: int) -> Sequence[PointValue] | None: ...

    def deadband(self, ioa: int) -> float: ...

    def clock(self) -> datetime: ...


@dataclass(frozen=True)
class Timing:
    t1: float = 15.0
    t2: float = 10.0
    t3: float = 20.0
    k: int = 12
    w: int = 8
    spontaneous: float = 1.0
    tick: float = 0.05


class Iec104Server:
    def __init__(
        self,
        stations: StationSource,
        *,
        host: str = "0.0.0.0",
        port: int = 2404,
        allowed_networks: Iterable[str] = DEFAULT_ALLOWED_NETWORKS,
        max_connections: int = 8,
        timing: Timing = Timing(),
    ) -> None:
        self.stations = stations
        self.timing = timing
        self._host = host
        self._requested_port = port
        self._networks = parse_networks(allowed_networks)
        self._max_connections = max_connections
        self._server: asyncio.Server | None = None
        self._connections: set[_Connection] = set()
        self.port: int | None = None
        self.stats = {"accepted": 0, "rejected_clients": 0, "rejected_busy": 0, "interrogations": 0,
                      "rejected_commands": 0, "spontaneous_objects": 0, "protocol_errors": 0}

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, self._host, self._requested_port)
        self.port = self._server.sockets[0].getsockname()[1]
        log.info("IEC 104 istasyonu %s:%s dinliyor (salt okunur)", self._host, self.port)

    async def stop(self) -> None:
        if self._server is None:
            return
        self._server.close()
        connections = list(self._connections)
        for connection in connections:
            connection.close()
        if connections:
            await asyncio.wait([c.task for c in connections if c.task is not None], timeout=2.0)
        await self._server.wait_closed()
        self._server = None

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = normalize_peer(str((writer.get_extra_info("peername") or ("?",))[0]))
        if not client_allowed(peer, self._networks):
            self.stats["rejected_clients"] += 1
            log.warning("IEC 104: izinli aglar disindan baglanti reddedildi: %s", peer)
            writer.close()
            return
        if len(self._connections) >= self._max_connections:
            self.stats["rejected_busy"] += 1
            writer.close()
            return
        connection = _Connection(self, reader, writer, peer)
        self._connections.add(connection)
        self.stats["accepted"] += 1
        try:
            await connection.run()
        finally:
            self._connections.discard(connection)


class _Connection:
    def __init__(self, server: Iec104Server, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, peer: str) -> None:
        self.server = server
        self.timing = server.timing
        self.stations = server.stations
        self.reader = reader
        self.writer = writer
        self.peer = peer
        self.task: asyncio.Task | None = None
        self.started = False
        self.send_seq = 0
        self.recv_seq = 0
        self.unacked: deque[tuple[int, float]] = deque()  # gonderilmis, onay bekleyen (seq, zaman)
        self.pending: deque[bytes] = deque()  # k penceresi dolu oldugu icin bekleyen ASDU'lar
        self.unacked_received = 0
        self.first_unacked_received = 0.0
        self.last_received = time.monotonic()
        self.test_sent_at: float | None = None
        self.last_spontaneous = 0.0
        self.last_sent: dict[int, dict[int, PointValue]] = {}

    # ------------------------------------------------------------ yasam
    async def run(self) -> None:
        self.task = asyncio.current_task()
        timers = asyncio.create_task(self._timers())
        try:
            while True:
                head = await self.reader.readexactly(2)
                if head[0] != iec104.START:
                    raise ProtocolError("baslangic bayti 0x68 degil")
                body = await self.reader.readexactly(head[1])
                try:
                    frame = iec104.decode_apdu(head + body)
                except ValueError as exc:
                    raise ProtocolError(str(exc)) from exc
                self.last_received = time.monotonic()
                self._on_frame(frame)
        except ProtocolError as exc:
            self.server.stats["protocol_errors"] += 1
            log.warning("IEC 104: %s protokol hatasi, baglanti kapatiliyor: %s", self.peer, exc)
        except (asyncio.IncompleteReadError, ConnectionError, OSError):
            pass
        finally:
            timers.cancel()
            self.close()

    def close(self) -> None:
        if not self.writer.is_closing():
            self.writer.close()

    def _write(self, data: bytes) -> None:
        if not self.writer.is_closing():
            self.writer.write(data)

    # ------------------------------------------------------------ cerceveler
    def _on_frame(self, frame: IFrame | SFrame | UFrame) -> None:
        if isinstance(frame, UFrame):
            self._on_u(frame.function)
            return
        if isinstance(frame, SFrame):
            self._acknowledge(frame.recv_seq)
            return
        if not self.started:
            raise ProtocolError("STARTDT oncesi I cercevesi")
        if frame.send_seq != self.recv_seq:
            raise ProtocolError(f"sira hatasi: N(S) {frame.send_seq}, beklenen {self.recv_seq}")
        self.recv_seq = (self.recv_seq + 1) % iec104.SEQ_MODULO
        if self.unacked_received == 0:
            self.first_unacked_received = time.monotonic()
        self.unacked_received += 1
        self._acknowledge(frame.recv_seq)
        self._on_asdu(frame.asdu)
        if self.unacked_received >= self.timing.w:
            self._send_s()

    def _on_u(self, function: UFunction) -> None:
        if function == UFunction.STARTDT_ACT:
            # Taban CON'dan ONCE: istemci CON'u alip hemen bir degeri degistirirse degisiklik tabana karismamali
            self.last_sent = {ca: {v.ioa: v for v in values} for ca, values in self._all_values()}
            self.started = True
            self._write(iec104.encode_u(UFunction.STARTDT_CON))
            self._flush()
        elif function == UFunction.STOPDT_ACT:
            if self.unacked_received:
                self._send_s()
            self.started = False
            self._write(iec104.encode_u(UFunction.STOPDT_CON))
        elif function == UFunction.TESTFR_ACT:
            self._write(iec104.encode_u(UFunction.TESTFR_CON))
        elif function == UFunction.TESTFR_CON:
            self.test_sent_at = None

    def _acknowledge(self, recv_seq: int) -> None:
        still_unacked = (self.send_seq - recv_seq) % iec104.SEQ_MODULO
        if still_unacked > len(self.unacked):
            raise ProtocolError(f"gecersiz N(R) {recv_seq}")
        while len(self.unacked) > still_unacked:
            self.unacked.popleft()
        self._flush()

    def _send_s(self) -> None:
        self._write(iec104.encode_s(self.recv_seq))
        self.unacked_received = 0

    def _send_asdu(self, asdu: bytes) -> None:
        self.pending.append(asdu)
        self._flush()

    def _flush(self) -> None:
        while self.started and self.pending and len(self.unacked) < self.timing.k:
            asdu = self.pending.popleft()
            self._write(iec104.encode_i(self.send_seq, self.recv_seq, asdu))
            self.unacked.append((self.send_seq, time.monotonic()))
            self.send_seq = (self.send_seq + 1) % iec104.SEQ_MODULO
            self.unacked_received = 0  # N(R) ile alinanlar da onaylandi

    # ------------------------------------------------------------ uygulama katmani
    def _on_asdu(self, raw: bytes) -> None:
        try:
            asdu = iec104.decode_asdu(raw)
        except iec104.UnknownTypeError:
            self._reject(raw, iec104.COT_UNKNOWN_TYPE, command=True)
            return
        except ValueError as exc:
            raise ProtocolError(f"bozuk ASDU: {exc}") from exc
        if asdu.type_id == iec104.C_IC_NA_1:
            self._interrogate(asdu, raw)
        elif asdu.type_id == iec104.C_CS_NA_1:
            self._clock_sync(asdu, raw)
        else:
            self._reject(raw, iec104.COT_UNKNOWN_TYPE, command=True)

    def _reject(self, raw: bytes, cot: int, *, command: bool = False) -> None:
        if command:
            self.server.stats["rejected_commands"] += 1
            log.warning("IEC 104: %s tip %d komutu reddedildi (istasyon salt okunur)", self.peer, raw[0])
        self._send_asdu(iec104.reply_with_cause(raw, cot, negative=True))

    def _targets(self, common_address: int) -> list[int] | None:
        """Komutu cevaplayacak istasyonlar. Yayin adresi hepsi demektir; hic istasyon yoksa da None (ret 46, bekletme yok)."""
        known = list(self.stations.common_addresses())
        if common_address == iec104.BROADCAST_COMMON_ADDRESS:
            return known or None
        return [common_address] if common_address in known else None

    # IEC 60870-5-101/104 7.2.4: yayin adresine gelen komutu her istasyon izleme yonunde KENDI ortak adresiyle cevaplar.
    def _interrogate(self, asdu: Asdu, raw: bytes) -> None:
        if asdu.cot != iec104.COT_ACTIVATION:
            self._reject(raw, iec104.COT_UNKNOWN_CAUSE)
            return
        targets = self._targets(asdu.common_address)
        if targets is None:
            self._reject(raw, iec104.COT_UNKNOWN_COMMON_ADDRESS)
            return
        station_wide = asdu.objects[0][1] == bytes((iec104.QOI_STATION,))
        if station_wide:
            self.server.stats["interrogations"] += 1
        for common_address in targets:
            request = _addressed(raw, common_address)
            if not station_wide:
                self._send_asdu(iec104.reply_with_cause(request, iec104.COT_ACTIVATION_CON, negative=True))
                continue
            values = self.stations.point_values(common_address)
            if values is None:  # birim sorgu sirasinda kaldirildi
                self._reject(request, iec104.COT_UNKNOWN_COMMON_ADDRESS)
                continue
            self._send_asdu(iec104.reply_with_cause(request, iec104.COT_ACTIVATION_CON, negative=False))
            for type_id, group in group_objects(values, MONITOR_OBJECTS):
                objects = tuple((value.ioa, _element(value)) for value in group)
                self._send_asdu(iec104.encode_asdu(Asdu(type_id, iec104.COT_INTERROGATED, common_address, objects)))
            self.last_sent[common_address] = {value.ioa: value for value in values}
            self._send_asdu(iec104.reply_with_cause(request, iec104.COT_ACTIVATION_TERM, negative=False))

    def _clock_sync(self, asdu: Asdu, raw: bytes) -> None:
        if asdu.cot != iec104.COT_ACTIVATION:
            self._reject(raw, iec104.COT_UNKNOWN_CAUSE)
            return
        targets = self._targets(asdu.common_address)
        if targets is None:
            self._reject(raw, iec104.COT_UNKNOWN_COMMON_ADDRESS)
            return
        element = iec104.cp56time2a(self.stations.clock())
        for common_address in targets:
            reply = Asdu(iec104.C_CS_NA_1, iec104.COT_ACTIVATION_CON, common_address, ((asdu.objects[0][0], element),))
            self._send_asdu(iec104.encode_asdu(reply))

    def _all_values(self) -> list[tuple[int, Sequence[PointValue]]]:
        pairs = []
        for common_address in self.stations.common_addresses():
            values = self.stations.point_values(common_address)
            if values is not None:
                pairs.append((common_address, values))
        return pairs

    def _spontaneous(self) -> None:
        time_tag = None
        for common_address, values in self._all_values():
            previous = self.last_sent.setdefault(common_address, {})
            changed = [v for v in values if _changed(previous.get(v.ioa), v, self.stations.deadband(v.ioa))]
            if not changed:
                continue
            time_tag = time_tag or iec104.cp56time2a(self.stations.clock())
            for value in changed:
                previous[value.ioa] = value
            for type_id, group in group_objects(changed, TIME_TAGGED_OBJECTS):
                tagged = iec104.M_ME_TF_1 if type_id == iec104.M_ME_NC_1 else iec104.M_SP_TB_1
                objects = tuple((value.ioa, _element(value) + time_tag) for value in group)
                self._send_asdu(iec104.encode_asdu(Asdu(tagged, iec104.COT_SPONTANEOUS, common_address, objects)))
                self.server.stats["spontaneous_objects"] += len(objects)

    # ------------------------------------------------------------ zamanlayicilar
    async def _timers(self) -> None:
        timing = self.timing
        while True:
            await asyncio.sleep(timing.tick)
            now = time.monotonic()
            if self.unacked and now - self.unacked[0][1] > timing.t1:
                log.warning("IEC 104: %s t1 icinde onay gelmedi, baglanti kapatiliyor", self.peer)
                self.close()
                return
            if self.test_sent_at is not None and now - self.test_sent_at > timing.t1:
                log.warning("IEC 104: %s TESTFR cevapsiz, baglanti kapatiliyor", self.peer)
                self.close()
                return
            if self.unacked_received and now - self.first_unacked_received >= timing.t2:
                self._send_s()
            if self.test_sent_at is None and now - self.last_received >= timing.t3:
                self._write(iec104.encode_u(UFunction.TESTFR_ACT))
                self.test_sent_at = now
            if self.started and now - self.last_spontaneous >= timing.spontaneous:
                self.last_spontaneous = now
                self._spontaneous()


def _addressed(asdu: bytes, common_address: int) -> bytes:
    """Gelen komut ASDU'su, ortak adresi (bayt 4-5) belirli istasyonunkiyle degistirilmis olarak."""
    return asdu[:4] + common_address.to_bytes(2, "little") + asdu[6:]


def _element(value: PointValue) -> bytes:
    if value.type_id == iec104.M_ME_NC_1:
        return iec104.float_element(float(value.value), value.quality)
    return iec104.single_point_element(bool(value.value), value.quality)


def _changed(previous: PointValue | None, current: PointValue, deadband: float) -> bool:
    if previous is None or previous.quality != current.quality:
        return True
    if current.type_id == iec104.M_SP_NA_1:
        return previous.value != current.value
    return abs(float(current.value) - float(previous.value)) >= deadband
