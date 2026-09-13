"""TB2 Adim 5 — SMS PDU kodlayici (3GPP TS 23.040 / 23.038): app.notify.pdu.

Gercek GSM modem PDU modunda (AT+CMGF=0) calisir; bu kodlayici uretim surucusunun parcasidir.
Beklenen degerler kodlayicidan bagimsiz elde edildi:
  - "hellohello" SMS-SUBMIT/SMS-DELIVER: yaygin kullanilan PDU ornekleri (AT+CMGS=23)
  - UCS-2, GSM-7 uzanti tablosu (EUR isareti) ve birlesik SMS dolgu bitleri: elle hesaplandi
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.notify.pdu import decode_deliver, decode_submit, encode_deliver, encode_submit

TR = timezone(timedelta(hours=3))


def test_gsm7_text_matches_the_reference_submit_pdu():
    [part] = encode_submit("+46708251358", "hellohello")

    assert part.pdu == "0011000B916407281553F80000AA0AE8329BFD4697D9EC37"
    assert part.tpdu_length == 23  # AT+CMGS=23


def test_reference_deliver_pdu_is_decoded():
    sms = decode_deliver("07917283010010F5040BC87238880900F10000993092516195800AE8329BFD4697D9EC37")

    assert (sms.number, sms.text) == ("27838890001", "hellohello")


def test_turkish_characters_are_sent_as_ucs2():
    [part] = encode_submit("+905550000001", "Şebeke")

    assert part.pdu == "0011000C910955050000100008AA0C015E006500620065006B0065"
    assert part.tpdu_length == 26


def test_gsm7_extension_characters_take_two_septets():
    [part] = encode_submit("+905550000001", "a€")

    assert part.pdu.endswith("0000AA03E14D19")  # DCS=00, UDL=3 septet (a, ESC, e)


def test_text_that_fits_160_septets_stays_a_single_part():
    [part] = encode_submit("+905550000001", "a" * 160)

    assert part.pdu.startswith("0011000C91095505000010" + "0000AA" + "A0")


def test_long_gsm7_text_is_split_with_concatenation_header_and_fill_bits():
    parts = encode_submit("+905550000001", "a" * 161, reference=1)

    assert len(parts) == 2
    first, second = parts
    assert first.pdu.startswith("0051000C91095505000010" + "0000AA" + "A0" + "050003010201")  # 153 + 7 septet
    assert first.tpdu_length == 154
    # 6 sekizli UDH = 48 bit -> 1 dolgu biti; 8 x "a" (0x61) elle paketlendi
    assert second.pdu == "0051000C91095505000010" + "0000AA" + "0F" + "050003010202" + "C2E170381C0E8701"
    assert second.tpdu_length == 28


def test_escape_and_extension_character_are_never_split_across_parts():
    text = "a" * 152 + "€" + "b" * 10  # ESC 153. septete, 0x65 154. septete duser

    parts = encode_submit("+905550000001", text, reference=3)

    decoded = [decode_submit(p.pdu).text for p in parts]
    assert decoded == ["a" * 152, "€" + "b" * 10]


def test_long_ucs2_text_is_split_into_67_character_parts():
    parts = encode_submit("+905550000001", "ş" * 71, reference=7)

    assert [p.tpdu_length for p in parts] == [14 + 6 + 134, 14 + 6 + 8]
    assert [decode_submit(p.pdu).concat for p in parts] == [(7, 2, 1), (7, 2, 2)]
    assert "".join(decode_submit(p.pdu).text for p in parts) == "ş" * 71


def test_submit_pdu_round_trips_number_text_and_parts():
    text = "[GRIDUP P2] ADM-00001 GIRIS_L2: Isil direnc indeksi K/K0 > 1.6 {test} " * 3
    parts = encode_submit("+905550000001", text, reference=42)

    decoded = [decode_submit(p.pdu) for p in parts]

    assert {d.number for d in decoded} == {"+905550000001"}
    assert "".join(d.text for d in decoded) == text
    assert [d.concat for d in decoded] == [(42, len(parts), i + 1) for i in range(len(parts))]


def test_alphanumeric_sender_and_timestamp_are_decoded():
    """Elle kodlandi: OA 0B D0 'GRIDUP' (6 septet), SCTS 26-09-13 12:41:05 +12 ceyrek, UD '1 42'."""
    sms = decode_deliver("0004" + "0BD0476992588502" + "0000" + "62903121145021" + "04" + "31104D06")

    assert (sms.number, sms.text, sms.timestamp) == ("GRIDUP", "1 42", datetime(2026, 9, 13, 12, 41, 5, tzinfo=TR))


@pytest.mark.parametrize("tz", [TR, timezone(timedelta(hours=-4, minutes=-30))])
def test_deliver_pdu_round_trips_sender_text_and_timestamp(tz):
    sent = datetime(2026, 9, 13, 12, 41, 5, tzinfo=tz)

    sms = decode_deliver(encode_deliver("+905550000001", "1 42", sent))

    assert (sms.number, sms.text, sms.timestamp) == ("+905550000001", "1 42", sent)


def test_deliver_encoding_refuses_text_that_needs_more_than_one_part():
    with pytest.raises(ValueError):
        encode_deliver("+905550000001", "a" * 161, datetime(2026, 9, 13, tzinfo=TR))
