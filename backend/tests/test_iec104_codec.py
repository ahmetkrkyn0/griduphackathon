"""TB3 Adim 8 (Could) — IEC 60870-5-104 cerceve kodlayicisi (app.scada.iec104).

Beklenen baytlar standarttan (IEC 60870-5-104 APCI, IEC 60870-5-101 ASDU, CP56Time2a) ELLE cikarilmistir:
  APCI = 0x68 | uzunluk (kontrol alani + ASDU) | 4 bayt kontrol alani
  I bicimi: N(S) ve N(R) 15 bit, bir sola kaydirilmis kucuk-endian (bit0 = 0)
  S bicimi: 01 00 | N(R);  U bicimi: STARTDT act 07 / con 0B, STOPDT act 13 / con 23, TESTFR act 43 / con 83
  ASDU = tip | VSQ (SQ bit7 + adet) | COT (T bit7, P/N bit6, neden) + kaynak adres | ortak adres (2 bayt) | IOA (3 bayt) + eleman
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.scada import iec104
from app.scada.iec104 import Asdu, IFrame, SFrame, UFrame, UFunction


# ------------------------------------------------------------------ APCI
@pytest.mark.parametrize(
    "function,wire",
    [
        (UFunction.STARTDT_ACT, "68 04 07 00 00 00"),
        (UFunction.STARTDT_CON, "68 04 0B 00 00 00"),
        (UFunction.STOPDT_ACT, "68 04 13 00 00 00"),
        (UFunction.STOPDT_CON, "68 04 23 00 00 00"),
        (UFunction.TESTFR_ACT, "68 04 43 00 00 00"),
        (UFunction.TESTFR_CON, "68 04 83 00 00 00"),
    ],
)
def test_u_frames(function, wire):
    assert iec104.encode_u(function) == bytes.fromhex(wire)
    assert iec104.decode_apdu(bytes.fromhex(wire)) == UFrame(function)


def test_s_frame():
    assert iec104.encode_s(5) == bytes.fromhex("68 04 01 00 0A 00")
    assert iec104.decode_apdu(bytes.fromhex("68 04 01 00 0A 00")) == SFrame(5)


def test_i_frame_sequence_numbers():
    asdu = bytes.fromhex("64 01 06 00 01 00 00 00 00 14")
    wire = iec104.encode_i(0x1234, 5, asdu)
    assert wire[:6] == bytes.fromhex("68 0E 68 24 0A 00")  # 0x1234 << 1 = 0x2468
    assert iec104.decode_apdu(wire) == IFrame(0x1234, 5, asdu)


def test_sequence_numbers_are_15_bit():
    asdu = bytes.fromhex("46 01 04 00 01 00 00 00 00 00")
    assert iec104.encode_i(32767, 32767, asdu)[2:6] == bytes.fromhex("FE FF FE FF")
    assert iec104.encode_i(32768, 32769, asdu)[2:6] == bytes.fromhex("00 00 02 00")  # 32768 -> 0


@pytest.mark.parametrize(
    "wire",
    [
        "67 04 07 00 00 00",  # yanlis baslangic bayti
        "68 03 07 00 00",  # uzunluk < 4
        "68 04 0F 00 00 00",  # U biciminde birden cok islev biti
        "68 05 01 00 0A 00 00",  # S cercevesi ASDU tasiyamaz
        "68 04 07 00 00",  # eksik bayt
        "68 04 07 01 00 00",  # U kontrol alaninin kalan baytlari sifir olmali
        "68 05 07 00 00 00",  # uzunluk alani gercek boydan buyuk
    ],
)
def test_malformed_apdu_is_rejected(wire):
    with pytest.raises(ValueError):
        iec104.decode_apdu(bytes.fromhex(wire))


# ------------------------------------------------------------------ ASDU
def test_decode_general_interrogation_command():
    asdu = iec104.decode_asdu(bytes.fromhex("64 01 06 00 01 00 00 00 00 14"))
    assert (asdu.type_id, asdu.cot, asdu.negative, asdu.common_address) == (100, 6, False, 1)
    assert asdu.objects == ((0, b"\x14"),)  # IOA 0, QOI 20 (istasyon sorgulamasi)


def test_encode_measured_values_short_float():
    asdu = Asdu(
        type_id=iec104.M_ME_NC_1,
        cot=iec104.COT_INTERROGATED,
        common_address=1,
        objects=((1101, iec104.float_element(78.0)), (1102, iec104.float_element(-2.5, iec104.QDS_IV))),
    )
    assert iec104.encode_asdu(asdu) == bytes.fromhex("0D 02 14 00 01 00  4D 04 00 00 00 9C 42 00  4E 04 00 00 00 20 C0 80")


def test_decode_rejects_truncated_objects():
    with pytest.raises(ValueError):
        iec104.decode_asdu(bytes.fromhex("0D 02 14 00 01 00  4D 04 00 00 00 9C 42 00  4E 04"))


def test_decode_rejects_trailing_bytes():
    with pytest.raises(ValueError):
        iec104.decode_asdu(bytes.fromhex("0D 01 14 00 01 00  4D 04 00 00 00 9C 42 00  FF"))


def test_negative_reply_rewrites_cause_only():
    command = bytes.fromhex("2D 01 06 00 01 00 D0 07 00 01")  # C_SC_NA_1, IOA 2000, SCO on
    reply = iec104.reply_with_cause(command, iec104.COT_UNKNOWN_TYPE, negative=True)
    assert reply == bytes.fromhex("2D 01 6C 00 01 00 D0 07 00 01")  # 0x40 | 44


def test_single_point_element():
    assert iec104.single_point_element(True) == b"\x01"
    assert iec104.single_point_element(False, iec104.QDS_IV) == b"\x80"


# ------------------------------------------------------------------ CP56Time2a
def test_cp56time2a():
    moment = datetime(2026, 9, 13, 10, 1, 2, 345000, tzinfo=timezone.utc)  # Pazar
    wire = bytes.fromhex("29 09 01 0A ED 09 1A")  # ms 2345 | dk 1 | saat 10 | gun 13 + haftanin gunu 7 | ay 9 | yil 26
    assert iec104.cp56time2a(moment) == wire
    assert iec104.parse_cp56time2a(wire) == moment


def test_cp56time2a_is_utc():
    from datetime import timedelta

    local = datetime(2026, 9, 13, 13, 1, 2, 345000, tzinfo=timezone(timedelta(hours=3)))
    assert iec104.cp56time2a(local) == bytes.fromhex("29 09 01 0A ED 09 1A")
