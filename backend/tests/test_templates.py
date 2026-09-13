"""TB2 Adim 6 — bildirim metinleri (app.notify.templates).

Kurallar (rapor 6.6c): saha kodu, oncelik, tek satir aciklama, ic portal baglantisi; telemetri, pano adi,
konum veya kisi adi YOK. SMS tek parca GSM-7 (160 karakter) — Turkce karakter UCS-2'ye dusurup 70
karaktere indirmesin diye ASCII'ye katlanir.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.alarm_manager import Alarm
from app.notify.pdu import encode_submit, gsm7_septets
from app.notify.templates import escalation_sms, fold, sms_alarm, whatsapp_alarm

T0 = datetime(2026, 9, 13, 10, 0, tzinfo=timezone.utc)


def make_alarm(**changes) -> Alarm:
    fields = dict(
        id=42, pano_id="ADM-00001", code="ALM-K-ALM", prio="P2", point="DSYA3_L2", event_id="EVT-42",
        raised_at=T0, last_true_at=T0, annunciated_at=T0,
    )
    fields.update(changes)
    return Alarm(**fields)


def test_turkish_and_typographic_characters_fold_to_gsm7():
    assert fold("Isıl direnç — gevşek bağlantı, İzmir ÖĞÜŞ “test”") == "Isil direnc - gevsek baglanti, Izmir OGUS \"test\""


def test_alarm_sms_carries_site_priority_text_and_reply_codes():
    text = sms_alarm(make_alarm(), "Isil direnc indeksi K/K0 > 1.6 — gevsek/oksitlenmis baglanti")

    assert text == (
        "[GRIDUP P2] ADM-00001 DSYA3_L2: Isil direnc indeksi K/K0 > 1.6 - gevsek/oksitlenmis baglanti."
        " Yanit: 1 42=gordum 2 42=ekip yolda"
    )


def test_alarm_sms_always_fits_one_gsm7_part():
    long_text = "Çok uzun bir açıklama " * 20

    text = sms_alarm(make_alarm(point=None, id=123456), long_text)

    assert len(gsm7_septets(text)) <= 160
    assert len(encode_submit("+905550000001", text)) == 1
    assert text.startswith("[GRIDUP P2] ADM-00001: Cok uzun")
    assert text.endswith("... Yanit: 1 123456=gordum 2 123456=ekip yolda")


def test_characters_outside_gsm7_do_not_push_the_sms_into_ucs2():
    text = sms_alarm(make_alarm(), "Пожар ⚡ test")  # Kiril + emoji: katlanamaz

    assert gsm7_septets(text) is not None
    assert "? ? test." in text


def test_whatsapp_text_is_short_and_links_to_the_internal_portal():
    text = whatsapp_alarm(make_alarm(prio="P1", code="ALM-ARC-TRIP", point=None), "TVOC-2 ark tripi", "http://gridup.local")

    assert text == "GRIDUP P1 alarm: ADM-00001 - TVOC-2 ark tripi. Detay (VPN): http://gridup.local/alarmlar/42"


def test_escalation_sms_states_how_long_the_alarm_waited():
    text = escalation_sms(make_alarm(prio="P1", code="ALM-ARC-TRIP", point=None), "TVOC-2 ark tripi", minutes=15)

    assert text == "[GRIDUP P1 ESKALASYON] ADM-00001: TVOC-2 ark tripi. 15 dk onaysiz. Yanit: 1 42=gordum 2 42=ekip yolda"
    assert len(encode_submit("+905550000009", text)) == 1
