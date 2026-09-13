"""Modbus TCP sunucusu (TB3 Adim 2, Kisi B) — cerceve, fonksiyon kodlari, baglanti politikasi.

Neden pymodbus sunucusu degil: requirements'taki pymodbus 3.7.4 sunucusu her istemci koptugunda
0.0.0.0 uzerinde rastgele bir portta YENI bir dinleme soketi aciyor (13 Eylul'de olculdu: 3 baglanti ->
3 sizan port). SCADA'nin her turda yeniden baglandigi sahada bu hem kaynak sizintisi hem acik port demektir.
Ayrica yazma isteginde degere gore reddetme ve baglanti kabulunde IP filtresi kancasi yok. Protokol kucuk
oldugu icin sunucu asyncio ile burada yazildi; testlerde pymodbus ISTEMCISI bagimsiz dogrulayicidir.

Desteklenen fonksiyonlar: 01/02 bit okuma, 03/04 register okuma, 06/16 register yazma; digerleri 0x01.
Dogrulama sirasi (Modbus Application Protocol v1.1b3 durum diyagramlari): fonksiyon desteklenir mi (0x01)
-> adet/uzunluk (0x03) -> adres uzayi (0x02) -> cihaz modeli. Cihaz modeli (ag gecidi) ModbusError atar;
beklenmeyen hata 0x04 olur ve baglanti acik kalir.

Guvenlik (rapor 7.4 "IP beyaz liste + salt okunur varsayilan"):
  - izinli aglar disindan gelen baglanti kabul edilir edilmez kapatilir,
  - es zamanli baglanti siniri ve bosta kalan baglantinin kapatilmasi (kaynak tuketimi),
  - yazma yetkisi cihaz modelindedir; Session baglanti basina kilit acma durumunu tasir.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import struct
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import IntEnum
from typing import Protocol

from ..config import DEFAULT_MODBUS_ALLOWED_CLIENTS

log = logging.getLogger("gridup.scada")

MBAP = struct.Struct(">HHHB")  # islem no, protokol (0), uzunluk (birim + PDU), birim
MAX_PDU = 253
ADDRESS_SPACE = 0x10000
MAX_READ_BITS = 2000
MAX_READ_REGISTERS = 125
MAX_WRITE_REGISTERS = 123

READ_COILS, READ_DISCRETE_INPUTS, READ_HOLDING_REGISTERS, READ_INPUT_REGISTERS = 1, 2, 3, 4
WRITE_SINGLE_REGISTER, WRITE_MULTIPLE_REGISTERS = 6, 16
BIT_READS = (READ_COILS, READ_DISCRETE_INPUTS)
REGISTER_READS = (READ_HOLDING_REGISTERS, READ_INPUT_REGISTERS)

DEFAULT_ALLOWED_NETWORKS = DEFAULT_MODBUS_ALLOWED_CLIENTS  # MODBUS_ALLOWED_CLIENTS ile daraltilir


class ExceptionCode(IntEnum):
    ILLEGAL_FUNCTION = 0x01
    ILLEGAL_DATA_ADDRESS = 0x02
    ILLEGAL_DATA_VALUE = 0x03
    SLAVE_DEVICE_FAILURE = 0x04
    GATEWAY_PATH_UNAVAILABLE = 0x0A
    GATEWAY_TARGET_FAILED = 0x0B


class ModbusError(Exception):
    def __init__(self, code: ExceptionCode, detail: str = "") -> None:
        super().__init__(f"{code.name}: {detail}" if detail else code.name)
        self.code = code
        self.detail = detail


@dataclass
class Session:
    """Tek TCP baglantisi; `unlocked_until` (monotonik saat) cihaz modelinin yazma yetkisi kararidir."""

    peer: str
    unlocked_until: float | None = None


class DeviceModel(Protocol):
    def read_registers(self, unit: int, address: int, count: int, function: int) -> Sequence[int]: ...

    def read_bits(self, unit: int, address: int, count: int, function: int) -> Sequence[bool]: ...

    async def write_registers(self, unit: int, address: int, values: Sequence[int], session: Session) -> None: ...


Network = ipaddress.IPv4Network | ipaddress.IPv6Network


def parse_networks(specs: Iterable[str]) -> tuple[Network, ...]:
    networks = []
    for spec in specs:
        try:
            networks.append(ipaddress.ip_network(spec.strip(), strict=False))
        except ValueError as exc:
            raise ValueError(f"gecersiz ag tanimi: {spec!r}") from exc
    return tuple(networks)


def normalize_peer(peer: str) -> str:
    """'::ffff:10.1.2.3' -> '10.1.2.3' (cift yigin soketlerde IPv4 istemci boyle gorunur)."""
    try:
        address = ipaddress.ip_address(peer.split("%", 1)[0])
    except ValueError:
        return peer
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        return str(address.ipv4_mapped)
    return str(address)


def client_allowed(peer: str, networks: Sequence[Network]) -> bool:
    try:
        address = ipaddress.ip_address(normalize_peer(peer))
    except ValueError:
        return False
    return any(address in network for network in networks)


class ModbusTcpServer:
    def __init__(
        self,
        device: DeviceModel,
        *,
        host: str = "0.0.0.0",
        port: int = 502,
        allowed_networks: Iterable[str] = DEFAULT_ALLOWED_NETWORKS,
        max_connections: int = 32,
        idle_timeout_s: float = 300.0,
    ) -> None:
        self._device = device
        self._host = host
        self._requested_port = port
        self._networks = parse_networks(allowed_networks)
        self._max_connections = max_connections
        self._idle_timeout_s = idle_timeout_s
        self._server: asyncio.Server | None = None
        self._writers: set[asyncio.StreamWriter] = set()
        self._tasks: set[asyncio.Task] = set()
        self.port: int | None = None
        self.stats = {"accepted": 0, "rejected_clients": 0, "rejected_busy": 0, "requests": 0, "exceptions": 0}

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, self._host, self._requested_port)
        self.port = self._server.sockets[0].getsockname()[1]
        log.info("Modbus TCP ag gecidi %s:%s dinliyor (izinli aglar: %s)", self._host, self.port,
                 ", ".join(str(n) for n in self._networks))

    async def stop(self) -> None:
        if self._server is None:
            return
        self._server.close()
        for writer in list(self._writers):
            writer.close()
        if self._tasks:
            await asyncio.wait(list(self._tasks), timeout=2.0)
        await self._server.wait_closed()
        self._server = None

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = normalize_peer(str((writer.get_extra_info("peername") or ("?",))[0]))
        if not client_allowed(peer, self._networks):
            self.stats["rejected_clients"] += 1
            log.warning("Modbus TCP: izinli aglar disindan baglanti reddedildi: %s", peer)
            await _close(writer)
            return
        if len(self._writers) >= self._max_connections:
            self.stats["rejected_busy"] += 1
            log.warning("Modbus TCP: baglanti siniri (%d) dolu, %s reddedildi", self._max_connections, peer)
            await _close(writer)
            return

        task = asyncio.current_task()
        self._writers.add(writer)
        if task is not None:
            self._tasks.add(task)
        self.stats["accepted"] += 1
        session = Session(peer)
        try:
            while True:
                header = await asyncio.wait_for(reader.readexactly(MBAP.size), self._idle_timeout_s)
                transaction, protocol, length, unit = MBAP.unpack(header)
                if protocol != 0 or not 2 <= length <= MAX_PDU + 1:
                    log.warning("Modbus TCP: gecersiz MBAP (protokol %d, uzunluk %d), %s kapatiliyor", protocol, length, peer)
                    break
                pdu = await asyncio.wait_for(reader.readexactly(length - 1), self._idle_timeout_s)
                response = await self._respond(unit, pdu, session)
                writer.write(MBAP.pack(transaction, 0, len(response) + 1, unit) + response)
                await writer.drain()
        except (asyncio.IncompleteReadError, TimeoutError, ConnectionError):
            pass  # istemci kapatti, bosta kaldi veya sunucu durduruluyor
        finally:
            self._writers.discard(writer)
            if task is not None:
                self._tasks.discard(task)
            await _close(writer)

    async def _respond(self, unit: int, pdu: bytes, session: Session) -> bytes:
        self.stats["requests"] += 1
        function = pdu[0]
        try:
            return bytes([function]) + await self._execute(unit, function, pdu[1:], session)
        except ModbusError as exc:
            code = exc.code
        except Exception:
            log.exception("Modbus TCP: cihaz modeli beklenmeyen hata verdi (birim %d, fonksiyon %d)", unit, function)
            code = ExceptionCode.SLAVE_DEVICE_FAILURE
        self.stats["exceptions"] += 1
        return bytes([function | 0x80, code])

    async def _execute(self, unit: int, function: int, data: bytes, session: Session) -> bytes:
        if function in BIT_READS or function in REGISTER_READS:
            address, count = _two_words(data)
            limit = MAX_READ_BITS if function in BIT_READS else MAX_READ_REGISTERS
            if not 1 <= count <= limit:
                raise ModbusError(ExceptionCode.ILLEGAL_DATA_VALUE, f"adet {count}, sinir 1-{limit}")
            _check_address_space(address, count)
            if function in BIT_READS:
                packed = _pack_bits(self._device.read_bits(unit, address, count, function), count)
                return bytes([len(packed)]) + packed
            values = self._device.read_registers(unit, address, count, function)
            return bytes([2 * count]) + struct.pack(f">{count}H", *values)
        if function == WRITE_SINGLE_REGISTER:
            address, value = _two_words(data)
            await self._device.write_registers(unit, address, [value], session)
            return data
        if function == WRITE_MULTIPLE_REGISTERS:
            if len(data) < 5:
                raise ModbusError(ExceptionCode.ILLEGAL_DATA_VALUE, "kisa PDU")
            address, count, byte_count = struct.unpack(">HHB", data[:5])
            if not 1 <= count <= MAX_WRITE_REGISTERS or byte_count != 2 * count or len(data) != 5 + byte_count:
                raise ModbusError(ExceptionCode.ILLEGAL_DATA_VALUE, f"adet {count}, bayt {byte_count}")
            _check_address_space(address, count)
            values = list(struct.unpack(f">{count}H", data[5:]))
            await self._device.write_registers(unit, address, values, session)
            return data[:4]
        raise ModbusError(ExceptionCode.ILLEGAL_FUNCTION, f"fonksiyon {function} desteklenmiyor")


def _two_words(data: bytes) -> tuple[int, int]:
    if len(data) != 4:
        raise ModbusError(ExceptionCode.ILLEGAL_DATA_VALUE, f"PDU veri uzunlugu {len(data)}, beklenen 4")
    return struct.unpack(">HH", data)


def _check_address_space(address: int, count: int) -> None:
    if address + count > ADDRESS_SPACE:
        raise ModbusError(ExceptionCode.ILLEGAL_DATA_ADDRESS, f"{address} + {count} adres uzayini asar")


def _pack_bits(bits: Sequence[bool], count: int) -> bytes:
    packed = bytearray((count + 7) // 8)
    for index in range(count):
        if bits[index]:
            packed[index // 8] |= 1 << (index % 8)
    return bytes(packed)


async def _close(writer: asyncio.StreamWriter) -> None:
    writer.close()
    try:
        await writer.wait_closed()
    except (ConnectionError, OSError):
        pass
