"""TB2 Adim 5-7 — bildirim ag gecidi (app.notify.dispatcher.Notifier).

Gercek parcalar: uretim SMS surucusu + sanal GSM modem (gercek TCP; kayit dosyasi okunur), WhatsApp
istemcisi (MockTransport uretilen istegi yakalar), alarm yoneticisinin urettigi degisiklikler. Kanal
kurali contracts/alarm-codes.yaml oncelik tablosundan gelir. Isci thread'i yerine `run_once()` dogrudan
cagrilir: sonuc belirlenimcidir.
"""

from __future__ import annotations

import json
import re
from datetime import date
from types import SimpleNamespace

import httpx
import pytest
import serial

from app.alarm_manager import AlarmManager, Condition
from app.alarm_service import Digest
from app.notify.dispatcher import NotifyConfig, Notifier
from app.notify.pdu import decode_submit, gsm7_septets
from app.notify.sms_modem import SmsModem
from app.notify.templates import SMS_LIMIT, digest_sms, escalation_sms, sms_alarm, whatsapp_alarm
from app.notify.whatsapp import WhatsAppClient
from helpers import utc

T0 = utc(2026, 9, 13, 10, 0, 0)
PANO = "ADM-00001"
# Alarm servisinin urettigi gunluk ozet (icerigi tests/test_digest.py kanitlar).
DIGEST = Digest(
    day=date(2026, 9, 13), hours=24, counts=(("uyari (P3)", 7), ("sistem (SYS)", 2)), panels=3,
    top_pano=PANO, top_count=4, top_text="Isil direnc indeksi K/K0 > 1.3 - baglanti direnci artisi suphesi",
)
FIELD_TEAM = ("+905550000001", "+905550000002")  # ALERT_RECIPIENTS
SUPERVISOR = ("+905550000009",)  # ALERT_ESCALATION


def sent_sms(modem_log) -> list[tuple[str, str]]:
    if not modem_log.exists():
        return []
    pdus = re.findall(r"SMS-GONDER .* pdu=([0-9A-F]+)", modem_log.read_text(encoding="utf-8"))
    return [(sms.number, sms.text) for sms in map(decode_submit, pdus)]


def calls(modem_log) -> list[str]:
    return re.findall(r"ARAMA\s+no=(\S+)", modem_log.read_text(encoding="utf-8")) if modem_log.exists() else []


class WhatsAppStub:
    """Meta API yerine gecen HTTP tasiyicisi: sirayla verilen durum kodlarini dondurur, istekleri saklar."""

    def __init__(self) -> None:
        self.requests: list[dict] = []
        self.statuses: list[int] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(json.loads(request.content))
        status = self.statuses.pop(0) if self.statuses else 200
        if status >= 400:
            return httpx.Response(status, json={"error": {"code": status, "message": "yapay hata"}})
        return httpx.Response(200, json={"messages": [{"id": f"wamid.{len(self.requests)}"}]})


@pytest.fixture
def whatsapp_stub() -> WhatsAppStub:
    return WhatsAppStub()


@pytest.fixture
def gateway(contracts, modem_server, whatsapp_stub):
    sms = SmsModem(f"socket://127.0.0.1:{modem_server.port}", timeout_s=3.0)
    whatsapp = WhatsAppClient("token", "123", transport=httpx.MockTransport(whatsapp_stub))
    deliveries, replies = [], []
    config = NotifyConfig(
        recipients=FIELD_TEAM, escalation=SUPERVISOR, portal_url="http://gridup.local", call_ring_s=0, retry_base_s=0
    )
    notifier = Notifier(
        contracts, config, sms=sms, whatsapp=whatsapp,
        on_delivery=deliveries.append, on_reply=lambda *args: replies.append(args), clock=lambda: T0,
    )
    yield SimpleNamespace(notifier=notifier, deliveries=deliveries, replies=replies)
    sms.close()
    whatsapp.close()


@pytest.fixture
def manager(contracts) -> AlarmManager:
    return AlarmManager(contracts, first_id=42)


def raise_alarm(manager, code: str, point: str | None = None):
    [change] = manager.observe(PANO, T0, [Condition(code, point)], now=T0)
    return change


def text_of(contracts, code: str) -> str:
    return contracts.alarm(code)["text"]


# -------------------------------------------------------------- kanal kurali
def test_p2_alarm_goes_by_sms_and_whatsapp_to_every_field_recipient(gateway, manager, contracts, modem_log, whatsapp_stub):
    change = raise_alarm(manager, "ALM-THR-TERM-ALM", "DSYA3_L2")

    gateway.notifier([change])
    gateway.notifier.run_once()

    expected_sms = sms_alarm(change.alarm, text_of(contracts, "ALM-THR-TERM-ALM"))
    assert sorted(sent_sms(modem_log)) == [(number, expected_sms) for number in FIELD_TEAM]
    expected_whatsapp = whatsapp_alarm(change.alarm, text_of(contracts, "ALM-THR-TERM-ALM"), "http://gridup.local")
    assert sorted((r["to"], r["text"]["body"]) for r in whatsapp_stub.requests) == [
        ("905550000001", expected_whatsapp), ("905550000002", expected_whatsapp)
    ]
    assert sorted((d.alarm_id, d.channel, d.recipient, d.ok) for d in gateway.deliveries) == [
        (42, "sms", "+90******0001", True), (42, "sms", "+90******0002", True),
        (42, "whatsapp", "+90******0001", True), (42, "whatsapp", "+90******0002", True),
    ]


def test_whatsapp_uses_its_own_verified_recipient_list_when_configured(contracts, manager, whatsapp_stub):
    """Demo SMS alicilari hayali numaralardir (sanal modem); WhatsApp yalnizca Meta'da dogrulanmis numaraya gider."""
    notifier = Notifier(
        contracts,
        NotifyConfig(recipients=FIELD_TEAM, whatsapp_recipients=("+905550000077",)),
        sms=None,
        whatsapp=WhatsAppClient("token", "123", transport=httpx.MockTransport(whatsapp_stub)),
        on_delivery=lambda d: None, on_reply=lambda *a: None, clock=lambda: T0,
    )

    notifier([raise_alarm(manager, "ALM-THR-TERM-ALM", "DSYA3_L2")])
    notifier.run_once()

    assert [r["to"] for r in whatsapp_stub.requests] == ["905550000077"]


@pytest.mark.parametrize("code", ["ALM-K-WARN", "ALM-COMMS-LOST"])
def test_warnings_and_system_alarms_page_nobody(gateway, manager, modem_log, whatsapp_stub, code):
    """P3 gunluk ozete, SYS toplu ozete gider (priorities.*.sms = false / digest_only)."""
    gateway.notifier([raise_alarm(manager, code)])
    gateway.notifier.run_once()

    assert (sent_sms(modem_log), whatsapp_stub.requests, gateway.deliveries) == ([], [], [])


def test_alarm_that_should_not_page_is_not_sent(gateway, manager, modem_log):
    """Ayni olayin esit oncelikli ikinci alarmi (notify=False) telefonu tekrar caldirmaz."""
    raise_alarm(manager, "ALM-K-ALM", "DSYA3_L2")
    [second] = manager.observe(PANO, T0, [Condition("ALM-K-ALM", "DSYA3_L2"), Condition("ALM-THR-PHASE-DIF", "DSYA3_L2")], now=T0)

    gateway.notifier([second])
    gateway.notifier.run_once()

    assert sent_sms(modem_log) == []


def test_p1_escalation_calls_the_field_team_then_texts_the_supervisor(gateway, manager, contracts, modem_log):
    arc = raise_alarm(manager, "ALM-ARC-TRIP")
    schedule = contracts.alarm_codes["priorities"]["P1"]
    [call] = manager.tick(T0.replace(minute=schedule["call_after_min"]))
    [escalate] = manager.tick(T0.replace(minute=schedule["escalate_after_min"]))

    gateway.notifier([call, escalate])
    gateway.notifier.run_once()

    assert calls(modem_log) == ["+90******0001", "+90******0002"]
    assert sent_sms(modem_log) == [
        ("+905550000009", escalation_sms(escalate.alarm, text_of(contracts, "ALM-ARC-TRIP"), schedule["escalate_after_min"]))
    ]
    assert {(d.channel, d.recipient) for d in gateway.deliveries} >= {("call", "+90******0001"), ("sms", "+90******0009")}
    assert arc.alarm.id == escalate.alarm.id


# --------------------------------------------------------- cift yonlu onay
def test_sms_reply_acknowledges_the_alarm(gateway, manager, modem_server):
    gateway.notifier([raise_alarm(manager, "ALM-THR-TERM-ALM", "DSYA3_L2")])
    gateway.notifier.run_once()

    modem_server.inject("+905550000001", "1 42")
    modem_server.inject("+905550000002", "2")  # kimliksiz: o numaraya en son giden alarm
    gateway.notifier.run_once(wait_s=1.0)
    gateway.notifier.run_once(wait_s=0.5)

    assert sorted(gateway.replies) == [
        (42, "sms:+90******0001", "gordum"),
        (42, "sms:+90******0002", "ekip yonlendirildi"),
    ]


def test_reply_from_an_unregistered_number_is_ignored(gateway, manager, modem_server):
    gateway.notifier([raise_alarm(manager, "ALM-THR-TERM-ALM", "DSYA3_L2")])
    gateway.notifier.run_once()

    modem_server.inject("+905550000099", "1 42")  # kayitli olmayan demo numarasi
    gateway.notifier.run_once(wait_s=1.0)

    assert gateway.replies == []


# ------------------------------------------------------------- dayaniklilik
def test_temporary_whatsapp_failure_is_retried(gateway, manager, whatsapp_stub):
    whatsapp_stub.statuses = [503]
    gateway.notifier([raise_alarm(manager, "ALM-DEW-ALM")])

    gateway.notifier.run_once()
    gateway.notifier.run_once()

    outcomes = [(d.recipient, d.ok) for d in gateway.deliveries if d.channel == "whatsapp"]
    assert outcomes.count(("+90******0001", False)) + outcomes.count(("+90******0002", False)) == 1
    assert sorted(o for o in outcomes if o[1]) == [("+90******0001", True), ("+90******0002", True)]


def test_permanent_whatsapp_failure_is_recorded_once_and_not_retried(gateway, manager, whatsapp_stub):
    whatsapp_stub.statuses = [401, 401]
    gateway.notifier([raise_alarm(manager, "ALM-DEW-ALM")])

    gateway.notifier.run_once()
    gateway.notifier.run_once()

    assert len(whatsapp_stub.requests) == 2
    assert [(d.channel, d.ok) for d in gateway.deliveries if d.channel == "whatsapp"] == [("whatsapp", False)] * 2


def test_modem_failure_reconnects_and_the_sms_still_goes_out(gateway, manager, modem_server, modem_log):
    modem_server.fail_next(1)
    change = raise_alarm(manager, "ALM-DEW-ALM")
    gateway.notifier([change])

    gateway.notifier.run_once()
    gateway.notifier.run_once()

    assert sorted(number for number, _ in sent_sms(modem_log)) == list(FIELD_TEAM)
    sms_outcomes = [d.ok for d in gateway.deliveries if d.channel == "sms"]
    assert sms_outcomes.count(False) == 1 and sms_outcomes.count(True) == 2


def test_lost_modem_connection_is_reestablished(gateway, manager, modem_server, modem_log):
    """Modem resetlendi / terminal sunucusu yeniden basladi: ag gecidi yeniden baglanip gonderir."""
    gateway.notifier([raise_alarm(manager, "ALM-DEW-ALM")])
    gateway.notifier.run_once()
    modem_server.disconnect_host()

    gateway.notifier([raise_alarm(manager, "ALM-THR-TERM-ALM", "DSYA3_L2")])
    gateway.notifier.run_once()

    # ayni turda: ilk alici kopuk baglantiya denk gelir, ikinci alici yeniden kurulan baglantiyla gider
    assert len(sent_sms(modem_log)) == 3
    gateway.notifier.run_once()
    assert len(sent_sms(modem_log)) == 4  # 2 alarm x 2 alici


def test_unreachable_modem_is_not_hammered_while_waiting_for_replies(contracts):
    """Modem konteyneri yok: yanit okuma dongusu her 0,5 sn'de baglanip log sellemez, geri cekilir."""
    attempts: list[str] = []

    def refuse(url: str, **options):
        attempts.append(url)
        raise serial.SerialException("baglanti reddedildi")

    notifier = Notifier(
        contracts, NotifyConfig(recipients=FIELD_TEAM), sms=SmsModem("socket://gsm-modem:7000", open_port=refuse),
        whatsapp=None, on_delivery=lambda d: None, on_reply=lambda *a: None, clock=lambda: T0,
    )

    for _ in range(5):
        notifier.run_once()

    assert len(attempts) == 1


def test_gateway_without_channels_accepts_changes_and_does_nothing(contracts, manager):
    notifier = Notifier(
        contracts, NotifyConfig(recipients=FIELD_TEAM), sms=None, whatsapp=None,
        on_delivery=lambda d: pytest.fail("kanal yokken teslim kaydi olmamali"), on_reply=lambda *a: None, clock=lambda: T0,
    )

    notifier([raise_alarm(manager, "ALM-ARC-TRIP")])
    notifier.run_once()


# ---------------------------------------------------------- gunluk ozet yolu
def test_daily_digest_goes_to_the_field_team_as_a_single_sms(gateway, modem_log):
    """P3/SYS alarmlari aninda kimseyi aramaz ama gunde bir kez tek parca SMS olarak gider."""
    assert gateway.notifier.digest(DIGEST) is True
    gateway.notifier.run_once()

    text = digest_sms(DIGEST, "http://gridup.local")
    assert sorted(sent_sms(modem_log)) == [(number, text) for number in FIELD_TEAM]
    septets = gsm7_septets(text)
    assert septets is not None and len(septets) <= SMS_LIMIT


def test_digest_is_not_written_to_the_alarm_audit_trail(gateway):
    """Ozet tek bir alarma ait degildir: notifications satiri yazilmaz (uctan uca gecikme KPI'si bozulmaz)."""
    gateway.notifier.digest(DIGEST)
    gateway.notifier.run_once()

    assert gateway.deliveries == []


def test_digest_does_not_disturb_the_instant_p2_path(gateway, manager, contracts, modem_log):
    """Ayni turda hem P2 alarmi hem ozet: iki mesaj da gider, alarmin denetim izi degismez."""
    change = raise_alarm(manager, "ALM-THR-TERM-ALM", "DSYA3_L2")

    gateway.notifier([change])
    gateway.notifier.digest(DIGEST)
    gateway.notifier.run_once()

    alarm_sms = sms_alarm(change.alarm, text_of(contracts, "ALM-THR-TERM-ALM"))
    assert sorted(sent_sms(modem_log)) == sorted(
        [(number, alarm_sms) for number in FIELD_TEAM]
        + [(number, digest_sms(DIGEST, "http://gridup.local")) for number in FIELD_TEAM]
    )
    sms_trail = [(d.alarm_id, d.recipient, d.ok) for d in gateway.deliveries if d.channel == "sms"]
    assert sorted(sms_trail) == [(42, "+90******0001", True), (42, "+90******0002", True)]


def test_digest_does_not_steal_the_reply_target(gateway, manager, modem_server):
    """Kimliksiz '1' yaniti hala son ALARM SMS'ini onaylar; ozet yanit hedefini degistirmez."""
    gateway.notifier([raise_alarm(manager, "ALM-THR-TERM-ALM", "DSYA3_L2")])
    gateway.notifier.run_once()
    gateway.notifier.digest(DIGEST)
    gateway.notifier.run_once()

    modem_server.inject("+905550000001", "1")
    gateway.notifier.run_once(wait_s=1.0)

    assert gateway.replies == [(42, "sms:+90******0001", "gordum")]


@pytest.mark.parametrize("config", [NotifyConfig(recipients=FIELD_TEAM), NotifyConfig(recipients=())])
def test_digest_without_an_sms_channel_or_recipient_is_not_queued(contracts, config, modem_server):
    """False doner: alarm servisi ozetlenen alarmlari 'gonderildi' diye isaretlemez."""
    sms = SmsModem(f"socket://127.0.0.1:{modem_server.port}") if not config.recipients else None
    notifier = Notifier(
        contracts, config, sms=sms, whatsapp=None,
        on_delivery=lambda d: pytest.fail("gonderilmeyen ozet kayit birakmamali"),
        on_reply=lambda *a: None, clock=lambda: T0,
    )

    assert notifier.digest(DIGEST) is False
    notifier.run_once()
