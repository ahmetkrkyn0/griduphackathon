"""SMS PDU kodlayici (3GPP TS 23.040 / 23.038) — uretim SMS surucusunun parcasi.

GSM modemler PDU modunda (AT+CMGF=0) ham TPDU'yu onaltilik metin olarak alir. Metin modu
(AT+CMGF=1) Turkce karakterleri ve birlesik (uzun) SMS'i modemden modeme farkli isler; PDU modu
her modemde ayni sonucu verir ve gonderilen her mesajin bayt bayt kaydini tutmayi saglar.

Kodlama secimi: metin GSM-7 alfabesine (temel + uzanti tablosu) sigiyorsa GSM-7 (160 septet),
sigmiyorsa UCS-2 (70 karakter). Uzun metin 8 bit referansli birlesik SMS parcalarina bolunur
(GSM-7: 153 septet, UCS-2: 67 karakter).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

# 3GPP TS 23.038 GSM-7 temel alfabe; indeks = septet degeri. 0x1B uzanti tablosuna kacis.
GSM7_BASIC = (
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)
GSM7_EXTENSION = {"\f": 0x0A, "^": 0x14, "{": 0x28, "}": 0x29, "\\": 0x2F, "[": 0x3C, "~": 0x3D, "]": 0x3E, "|": 0x40, "€": 0x65}
ESCAPE = 0x1B
assert len(GSM7_BASIC) == 128

_BASIC_INDEX = {char: index for index, char in enumerate(GSM7_BASIC)}
_EXTENSION_CHAR = {code: char for char, code in GSM7_EXTENSION.items()}

DCS_GSM7 = 0x00
DCS_UCS2 = 0x08
VALIDITY_4_DAYS = 0xAA  # goreli gecerlilik suresi (TP-VP)

MTI_DELIVER = 0x00
MTI_SUBMIT = 0x01
FLAG_VPF_RELATIVE = 0x10
FLAG_UDHI = 0x40
FLAG_MMS = 0x04  # SMS-DELIVER: 1 = bekleyen baska mesaj yok

GSM7_SINGLE, GSM7_PART = 160, 153
UCS2_SINGLE, UCS2_PART = 70, 67

TYPE_INTERNATIONAL = 0x91
TYPE_UNKNOWN = 0x81
TON_MASK, TON_ALPHANUMERIC = 0x70, 0x50


@dataclass(frozen=True)
class SubmitPart:
    pdu: str  # "00" (varsayilan SMSC) + TPDU, onaltilik
    tpdu_length: int  # AT+CMGS=<tpdu_length>


@dataclass(frozen=True)
class Sms:
    number: str
    text: str
    timestamp: datetime | None = None
    concat: tuple[int, int, int] | None = None  # (referans, toplam parca, sira)


# ------------------------------------------------------------------ kodlama
def gsm7_septets(text: str) -> list[int] | None:
    """Metin GSM-7'ye sigmiyorsa None."""
    septets: list[int] = []
    for char in text:
        if char in _BASIC_INDEX and char != "\x1b":
            septets.append(_BASIC_INDEX[char])
        elif char in GSM7_EXTENSION:
            septets += [ESCAPE, GSM7_EXTENSION[char]]
        else:
            return None
    return septets


def encode_submit(number: str, text: str, *, reference: int = 0) -> list[SubmitPart]:
    septets = gsm7_septets(text)
    if septets is not None:
        chunks = _split_septets(septets)
        payloads = [(DCS_GSM7, chunk) for chunk in chunks]
    else:
        units = text.encode("utf-16-be")
        chars = [units[i : i + 2] for i in range(0, len(units), 2)]  # BMP disi karakter ~ yok say
        size = UCS2_SINGLE if len(chars) <= UCS2_SINGLE else UCS2_PART
        payloads = [(DCS_UCS2, b"".join(chars[i : i + size])) for i in range(0, len(chars), size)] or [(DCS_UCS2, b"")]

    total = len(payloads)
    parts = []
    for sequence, (dcs, chunk) in enumerate(payloads, start=1):
        udh = bytes([0x05, 0x00, 0x03, reference & 0xFF, total, sequence]) if total > 1 else b""
        first = MTI_SUBMIT | FLAG_VPF_RELATIVE | (FLAG_UDHI if udh else 0)
        header = bytes([first, 0x00]) + _encode_address(number) + bytes([0x00, dcs, VALIDITY_4_DAYS])
        user_data = _gsm7_user_data(chunk, udh) if dcs == DCS_GSM7 else bytes([len(udh) + len(chunk)]) + udh + chunk
        tpdu = header + user_data
        parts.append(SubmitPart(pdu="00" + tpdu.hex().upper(), tpdu_length=len(tpdu)))
    return parts


def encode_deliver(sender: str, text: str, timestamp: datetime) -> str:
    """Gelen SMS (sanal modem icin). Yalnizca tek parca."""
    septets = gsm7_septets(text)
    if septets is not None:
        if len(septets) > GSM7_SINGLE:
            raise ValueError("SMS-DELIVER tek parcaya sigmiyor")
        dcs, user_data = DCS_GSM7, _gsm7_user_data(septets, b"")
    else:
        body = text.encode("utf-16-be")
        if len(body) // 2 > UCS2_SINGLE:
            raise ValueError("SMS-DELIVER tek parcaya sigmiyor")
        dcs, user_data = DCS_UCS2, bytes([len(body)]) + body
    tpdu = (
        bytes([MTI_DELIVER | FLAG_MMS])
        + _encode_address(sender)
        + bytes([0x00, dcs])
        + _encode_timestamp(timestamp)
        + user_data
    )
    return "00" + tpdu.hex().upper()


def _split_septets(septets: list[int]) -> list[list[int]]:
    if len(septets) <= GSM7_SINGLE:
        return [septets]
    chunks, start = [], 0
    while start < len(septets):
        end = min(start + GSM7_PART, len(septets))
        if septets[end - 1] == ESCAPE and end < len(septets):  # kacis ile uzanti karakteri bolunmez
            end -= 1
        chunks.append(septets[start:end])
        start = end
    return chunks


def _gsm7_user_data(septets: list[int], udh: bytes) -> bytes:
    """UDL (septet) + UDH + dolgu bitleri + paketlenmis septetler."""
    header_bits = len(udh) * 8
    fill = (7 - header_bits % 7) % 7 if udh else 0
    header_septets = (header_bits + fill) // 7
    value = 0
    for byte_index, byte in enumerate(udh):
        value |= byte << (8 * byte_index)
    bits = header_bits + fill
    for septet in septets:
        value |= septet << bits
        bits += 7
    body = value.to_bytes((bits + 7) // 8, "little") if bits else b""
    return bytes([header_septets + len(septets)]) + body


def _encode_address(number: str) -> bytes:
    digits = number.lstrip("+")
    if not digits.isdigit():
        raise ValueError(f"telefon numarasi yalnizca rakam icermeli: {number!r}")
    kind = TYPE_INTERNATIONAL if number.startswith("+") else TYPE_UNKNOWN
    return bytes([len(digits), kind]) + _semi_octets(digits)


def _semi_octets(digits: str) -> bytes:
    padded = digits + ("F" if len(digits) % 2 else "")
    return bytes.fromhex("".join(padded[i + 1] + padded[i] for i in range(0, len(padded), 2)))


def _encode_timestamp(when: datetime) -> bytes:
    offset = when.utcoffset() or timedelta(0)
    quarters = int(abs(offset.total_seconds()) // 900)
    fields = [when.year % 100, when.month, when.day, when.hour, when.minute, when.second]
    octets = _semi_octets("".join(f"{field:02d}" for field in fields) + f"{quarters:02d}")
    if offset < timedelta(0):
        octets = octets[:-1] + bytes([octets[-1] | 0x08])
    return octets


# ------------------------------------------------------------------ cozme
def decode_submit(pdu: str) -> Sms:
    data, index = _strip_smsc(pdu)
    first = data[index]
    if first & 0x03 != MTI_SUBMIT:
        raise ValueError("SMS-SUBMIT degil")
    index += 2  # ilk sekizli + TP-MR
    number, index = _decode_address(data, index)
    dcs = data[index + 1]
    index += 2
    vpf = (first >> 3) & 0x03
    index += {0: 0, 2: 1, 1: 7, 3: 7}[vpf]
    text, concat = _decode_user_data(data, index, dcs, bool(first & FLAG_UDHI))
    return Sms(number=number, text=text, concat=concat)


def decode_deliver(pdu: str) -> Sms:
    data, index = _strip_smsc(pdu)
    first = data[index]
    if first & 0x03 != MTI_DELIVER:
        raise ValueError("SMS-DELIVER degil")
    index += 1
    number, index = _decode_address(data, index)
    dcs = data[index + 1]
    index += 2
    timestamp = _decode_timestamp(data[index : index + 7])
    index += 7
    text, concat = _decode_user_data(data, index, dcs, bool(first & FLAG_UDHI))
    return Sms(number=number, text=text, timestamp=timestamp, concat=concat)


def _strip_smsc(pdu: str) -> tuple[bytes, int]:
    data = bytes.fromhex(pdu.strip())
    return data, 1 + data[0]


def _decode_address(data: bytes, index: int) -> tuple[str, int]:
    length, kind = data[index], data[index + 1]
    octets = (length + 1) // 2
    raw = data[index + 2 : index + 2 + octets]
    if kind & TON_MASK == TON_ALPHANUMERIC:
        number = _unpack_gsm7(raw, (length * 4) // 7, 0)
    else:
        swapped = "".join(f"{b:02X}"[1] + f"{b:02X}"[0] for b in raw)
        number = ("+" if kind == TYPE_INTERNATIONAL else "") + swapped[:length]
    return number, index + 2 + octets


def _decode_timestamp(octets: bytes) -> datetime:
    digits = "".join(f"{b:02X}"[1] + f"{b:02X}"[0] for b in octets)
    tz_octet = octets[6]
    negative = bool(tz_octet & 0x08)
    tz_digits = f"{tz_octet & 0xF7:02X}"
    quarters = int(tz_digits[1] + tz_digits[0])
    offset = timedelta(minutes=15 * quarters) * (-1 if negative else 1)
    year, month, day, hour, minute, second = (int(digits[i : i + 2]) for i in range(0, 12, 2))
    return datetime(2000 + year, month, day, hour, minute, second, tzinfo=timezone(offset))


def _decode_user_data(data: bytes, index: int, dcs: int, has_udh: bool) -> tuple[str, tuple[int, int, int] | None]:
    length = data[index]
    body = data[index + 1 :]
    udh = body[: body[0] + 1] if has_udh else b""
    concat = _concat_info(udh[1:]) if udh else None
    alphabet = (dcs >> 2) & 0x03 if dcs & 0xC0 == 0 else 0
    if alphabet == 2:  # UCS-2: UDL sekizli sayisi
        return body[len(udh) : length].decode("utf-16-be"), concat
    if alphabet == 1:  # 8 bit veri
        return body[len(udh) : length].decode("latin-1"), concat
    header_bits = len(udh) * 8
    fill = (7 - header_bits % 7) % 7 if udh else 0
    skip = (header_bits + fill) // 7
    return _unpack_gsm7(body, length, skip), concat


def _unpack_gsm7(body: bytes, septet_count: int, skip: int) -> str:
    value = int.from_bytes(body, "little")
    chars: list[str] = []
    escaped = False
    for position in range(skip, septet_count):
        septet = (value >> (7 * position)) & 0x7F
        if escaped:
            chars.append(_EXTENSION_CHAR.get(septet, " "))
            escaped = False
        elif septet == ESCAPE:
            escaped = True
        else:
            chars.append(GSM7_BASIC[septet])
    return "".join(chars)


def _concat_info(elements: bytes) -> tuple[int, int, int] | None:
    index = 0
    while index + 1 < len(elements):
        ie_id, ie_len = elements[index], elements[index + 1]
        payload = elements[index + 2 : index + 2 + ie_len]
        if ie_id == 0x00 and ie_len == 3:
            return payload[0], payload[1], payload[2]
        if ie_id == 0x08 and ie_len == 4:
            return (payload[0] << 8) | payload[1], payload[2], payload[3]
        index += 2 + ie_len
    return None
