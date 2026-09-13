"""IEC 60870-5-104 cerceve kodlayicisi (TB3 Adim 8, Could, Kisi B).

Yalnizca kontrollu istasyonun (slave) ihtiyaci olan parca: APCI (I/S/U bicimleri), ASDU basligi ve bu projede kullanilan
tipler. Sunucu ve baglanti durum makinesi: iec104_server.py. Nokta plani (IOA): iec104_points.py, docs/04.

    APDU = 0x68 | uzunluk (4..253, kontrol alani + ASDU) | kontrol alani (4 bayt) | ASDU
    I: N(S) ve N(R) 15 bit, bir sola kaydirilmis, kucuk-endian     S: 01 00 N(R)     U: 07/0B 13/23 43/83 00 00 00
    ASDU = tip | VSQ (SQ bit7, adet 7 bit) | COT (T bit7, P/N bit6, neden 6 bit) | kaynak adres | ortak adres (2) | nesneler
    nesne = IOA (3 bayt, kucuk-endian) + eleman (tipe gore sabit boy)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import IntEnum

START = 0x68
MAX_LENGTH = 253  # uzunluk alani: kontrol alani (4) + ASDU (en cok 249)
MAX_ASDU = MAX_LENGTH - 4
SEQ_MODULO = 1 << 15

# Tip tanimlayicilari (IEC 60870-5-101 §7.2.1)
M_SP_NA_1 = 1  # tek nokta
M_ME_NC_1 = 13  # olculen deger, kisa kayan nokta
M_SP_TB_1 = 30  # tek nokta + CP56Time2a
M_ME_TF_1 = 36  # olculen deger, kisa kayan nokta + CP56Time2a
C_SC_NA_1 = 45  # tek komut
C_DC_NA_1 = 46  # cift komut
M_EI_NA_1 = 70  # baslatma sonu
C_IC_NA_1 = 100  # sorgulama komutu
C_CS_NA_1 = 103  # saat senkronizasyonu

ELEMENT_SIZE = {
    M_SP_NA_1: 1, M_ME_NC_1: 5, M_SP_TB_1: 8, M_ME_TF_1: 12,
    C_SC_NA_1: 1, C_DC_NA_1: 1, M_EI_NA_1: 1, C_IC_NA_1: 1, C_CS_NA_1: 7,
}

# Iletim nedenleri (COT)
COT_SPONTANEOUS = 3
COT_INITIALIZED = 4
COT_ACTIVATION = 6
COT_ACTIVATION_CON = 7
COT_ACTIVATION_TERM = 10
COT_INTERROGATED = 20
COT_UNKNOWN_TYPE = 44
COT_UNKNOWN_CAUSE = 45
COT_UNKNOWN_COMMON_ADDRESS = 46
COT_UNKNOWN_IOA = 47

QOI_STATION = 20  # istasyon (genel) sorgulamasi
BROADCAST_COMMON_ADDRESS = 0xFFFF

# Kalite: QDS (olculen deger) ve SIQ (tek nokta) ortak ust bitleri
QDS_OV = 0x01
QDS_IV = 0x80

ASDU_HEADER = 6
IOA_SIZE = 3


class UFunction(IntEnum):
    STARTDT_ACT = 0x07
    STARTDT_CON = 0x0B
    STOPDT_ACT = 0x13
    STOPDT_CON = 0x23
    TESTFR_ACT = 0x43
    TESTFR_CON = 0x83


@dataclass(frozen=True)
class IFrame:
    send_seq: int
    recv_seq: int
    asdu: bytes


@dataclass(frozen=True)
class SFrame:
    recv_seq: int


@dataclass(frozen=True)
class UFrame:
    function: UFunction


@dataclass(frozen=True)
class Asdu:
    type_id: int
    cot: int
    common_address: int
    objects: tuple[tuple[int, bytes], ...]
    negative: bool = False
    test: bool = False
    originator: int = 0


class UnknownTypeError(ValueError):
    """Bu istasyonun cozmedigi tip; sunucu ASDU'yu COT 44 ile geri doner."""


# ------------------------------------------------------------------ APCI
def _seq(number: int) -> bytes:
    value = (number % SEQ_MODULO) << 1
    return bytes((value & 0xFF, value >> 8))


def encode_u(function: UFunction) -> bytes:
    return bytes((START, 4, int(function), 0, 0, 0))


def encode_s(recv_seq: int) -> bytes:
    return bytes((START, 4, 0x01, 0x00)) + _seq(recv_seq)


def encode_i(send_seq: int, recv_seq: int, asdu: bytes) -> bytes:
    if not 0 < len(asdu) <= MAX_ASDU:
        raise ValueError(f"ASDU boyu {len(asdu)}, sinir 1-{MAX_ASDU}")
    return bytes((START, 4 + len(asdu))) + _seq(send_seq) + _seq(recv_seq) + asdu


def decode_apdu(apdu: bytes) -> IFrame | SFrame | UFrame:
    if len(apdu) < 6 or apdu[0] != START:
        raise ValueError("APDU 0x68 ile baslamali ve en az 6 bayt olmali")
    length = apdu[1]
    if not 4 <= length <= MAX_LENGTH or len(apdu) != length + 2:
        raise ValueError(f"gecersiz APDU uzunlugu {length}")
    c1, c2, c3, c4 = apdu[2:6]
    body = bytes(apdu[6:])
    if c1 & 0x01 == 0:
        return IFrame((c1 | (c2 << 8)) >> 1, (c3 | (c4 << 8)) >> 1, body)
    if c1 & 0x03 == 0x01:
        if body or c2:
            raise ValueError("S cercevesi ASDU tasiyamaz")
        return SFrame((c3 | (c4 << 8)) >> 1)
    if body or c2 or c3 or c4:
        raise ValueError("U cercevesi ASDU tasiyamaz")
    try:
        return UFrame(UFunction(c1))
    except ValueError:
        raise ValueError(f"gecersiz U islevi {c1:#04x}") from None


# ------------------------------------------------------------------ ASDU
def encode_asdu(asdu: Asdu) -> bytes:
    if not 1 <= len(asdu.objects) <= 127:
        raise ValueError(f"ASDU nesne sayisi {len(asdu.objects)}, sinir 1-127")
    cause = (0x80 if asdu.test else 0) | (0x40 if asdu.negative else 0) | asdu.cot
    header = bytes((asdu.type_id, len(asdu.objects), cause, asdu.originator)) + asdu.common_address.to_bytes(2, "little")
    body = b"".join(ioa.to_bytes(IOA_SIZE, "little") + element for ioa, element in asdu.objects)
    data = header + body
    if len(data) > MAX_ASDU:
        raise ValueError(f"ASDU boyu {len(data)} > {MAX_ASDU}")
    return data


def decode_asdu(data: bytes) -> Asdu:
    if len(data) < ASDU_HEADER + IOA_SIZE:
        raise ValueError("ASDU kisa")
    type_id, vsq, cause, originator = data[0], data[1], data[2], data[3]
    size = ELEMENT_SIZE.get(type_id)
    if size is None:
        raise UnknownTypeError(f"desteklenmeyen tip {type_id}")
    count, sequence, body = vsq & 0x7F, bool(vsq & 0x80), data[ASDU_HEADER:]
    if count == 0:
        raise ValueError("ASDU nesne icermiyor")
    if sequence:
        if len(body) != IOA_SIZE + count * size:
            raise ValueError("ASDU nesne dizisi eksik veya fazla")
        base = int.from_bytes(body[:IOA_SIZE], "little")
        objects = tuple((base + i, bytes(body[IOA_SIZE + i * size : IOA_SIZE + (i + 1) * size])) for i in range(count))
    else:
        step = IOA_SIZE + size
        if len(body) != count * step:
            raise ValueError("ASDU nesneleri eksik veya fazla")
        objects = tuple(
            (int.from_bytes(body[i * step : i * step + IOA_SIZE], "little"), bytes(body[i * step + IOA_SIZE : (i + 1) * step]))
            for i in range(count)
        )
    return Asdu(
        type_id=type_id,
        cot=cause & 0x3F,
        common_address=int.from_bytes(data[4:6], "little"),
        objects=objects,
        negative=bool(cause & 0x40),
        test=bool(cause & 0x80),
        originator=originator,
    )


def reply_with_cause(asdu: bytes, cot: int, *, negative: bool) -> bytes:
    """Gelen ASDU'yu aynen, yalnizca iletim nedeni degismis olarak geri doner (onay / ret)."""
    cause = (asdu[2] & 0x80) | (0x40 if negative else 0) | cot
    return asdu[:2] + bytes((cause,)) + asdu[3:]


# ------------------------------------------------------------------ elemanlar
def float_element(value: float, quality: int = 0) -> bytes:
    return struct.pack("<fB", value, quality)


def single_point_element(on: bool, quality: int = 0) -> bytes:
    return bytes(((1 if on else 0) | (quality & 0xF0),))


def cp56time2a(moment: datetime) -> bytes:
    """CP56Time2a, UTC (yaz saati biti 0): ms (2) | dakika | saat | gun + haftanin gunu << 5 | ay | yil % 100."""
    t = moment.astimezone(timezone.utc)
    ms = t.second * 1000 + t.microsecond // 1000
    return bytes((ms & 0xFF, ms >> 8, t.minute, t.hour, t.day | (t.isoweekday() << 5), t.month, t.year % 100))


def parse_cp56time2a(data: bytes) -> datetime:
    ms = data[0] | (data[1] << 8)
    return datetime(
        2000 + (data[6] & 0x7F), data[5] & 0x0F, data[4] & 0x1F, data[3] & 0x1F, data[2] & 0x3F,
        ms // 1000, (ms % 1000) * 1000, tzinfo=timezone.utc,
    )
