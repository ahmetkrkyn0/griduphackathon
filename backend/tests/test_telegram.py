"""Telegram Bot API gondericisi birim testleri (app.notify.telegram)."""

from __future__ import annotations

import json
import httpx
import pytest

from app.notify.telegram import TelegramClient, TelegramError
from app.notify.templates import telegram_alarm


SUCCESS = {
    "ok": True,
    "result": {
        "message_id": 998877,
        "chat": {"id": 123456789, "type": "private"},
        "text": "test",
    },
}


def recording_transport(requests: list[httpx.Request], status: int = 200, body: dict | None = None) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status, json=SUCCESS if body is None else body)

    return httpx.MockTransport(handler)


def test_telegram_send_success():
    requests: list[httpx.Request] = []
    client = TelegramClient("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "987654321", transport=recording_transport(requests))

    msg_id = client.send("<b>GRIDUP ALARM</b>\nPano: ADM-00001")

    assert msg_id == "998877"
    assert len(requests) == 1
    req = requests[0]
    assert req.method == "POST"
    assert str(req.url) == "https://api.telegram.org/bot123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11/sendMessage"
    payload = json.loads(req.content)
    assert payload == {
        "chat_id": "987654321",
        "text": "<b>GRIDUP ALARM</b>\nPano: ADM-00001",
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }


@pytest.mark.parametrize("status,retryable", [(400, False), (401, False), (404, False), (429, True), (500, True), (503, True)])
def test_telegram_error_retryability(status: int, retryable: bool):
    err_body = {"ok": False, "error_code": status, "description": "Error details"}
    client = TelegramClient("dummy-token", "dummy-chat", transport=recording_transport([], status, err_body))

    with pytest.raises(TelegramError) as caught:
        client.send("test")

    assert caught.value.retryable is retryable


def test_telegram_network_error_is_retryable():
    def offline(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Baglanti reddedildi", request=request)

    client = TelegramClient("dummy-token", "dummy-chat", transport=httpx.MockTransport(offline))

    with pytest.raises(TelegramError) as caught:
        client.send("test")

    assert caught.value.retryable is True


def test_telegram_template_formatting():
    class DummyAlarm:
        priority = "P1"
        panel_id = "ADM-00001"
        code = "E-TH-001"
        state = "RAISED"
        ttl_h = 12.5

    msg = telegram_alarm(DummyAlarm(), "Bara baglanti asiri sicaklik", "http://gridup.local")
    assert "🔴 <b>[GRIDUP P1 ALARM]</b>" in msg
    assert "ADM-00001" in msg
    assert "E-TH-001" in msg
    assert "12.5 saat" in msg
    assert "http://gridup.local/alarmlar" in msg


def test_telegram_omits_rul_line_when_ttl_h_is_none():
    """P1 Task 1 (S8 bilinen siniri): kalite bayragi set olan bir noktada ttl_h artik
    panoalgo'da kaynaginda None'a cekiliyor (EdgePipeline._suppress_ttl_when_quality_
    suspect) ve bu deger risk.py _condition() uzerinden dogrudan Alarm.ttl_h'e akiyor.
    templates.py:99-100'deki `if ttl_h is not None` korumasi ZATEN dogru calisiyordu;
    bu test gercek Alarm dataclass'ini ttl_h=None ile kurup mesajda "Kalan Omur (RUL)"
    satirinin hic basilmadigini kilitler -- koruma kaldirilirsa (veya bicimleme None'a
    uygulanirsa) bu test TypeError'la veya beklenmeyen metinle kirilir."""
    from app.alarm_manager import Alarm
    from helpers import utc

    t = utc(2026, 9, 13, 9, 0)
    alarm = Alarm(
        id=7,
        pano_id="ADM-00001",
        code="ALM-K-WARN",
        prio="P3",
        point="GIRIS_L2",
        event_id="EVT-7",
        raised_at=t,
        last_true_at=t,
        annunciated_at=t,
        ttl_h=None,
    )

    msg = telegram_alarm(alarm, "K/K0 esigi asildi", "http://gridup.local")

    assert "Kalan Ömür (RUL)" not in msg
    assert "ADM-00001" in msg
    assert "ALM-K-WARN" in msg


def test_notifier_dispatches_telegram_alarm(contracts):
    from app.alarm_manager import AlarmManager, Condition
    from app.notify.dispatcher import NotifyConfig, Notifier
    from helpers import utc

    t0 = utc(2026, 9, 13, 10, 0, 0)
    requests: list[httpx.Request] = []
    telegram = TelegramClient("dummy-token", "12345678", transport=recording_transport(requests))

    deliveries = []
    config = NotifyConfig(
        recipients=("+905550000001",), escalation=(), portal_url="http://gridup.local", call_ring_s=0, retry_base_s=0
    )
    notifier = Notifier(
        contracts,
        config,
        sms=None,
        whatsapp=None,
        telegram=telegram,
        on_delivery=deliveries.append,
        on_reply=lambda *args: None,
        clock=lambda: t0,
    )

    manager = AlarmManager(contracts, first_id=42)
    [change] = manager.observe("ADM-00001", t0, [Condition("ALM-THR-TERM-ALM", "DSYA3_L2")], now=t0)

    notifier([change])
    notifier.run_once()

    assert len(requests) == 1
    req = requests[0]
    assert req.method == "POST"
    payload = json.loads(req.content)
    assert payload["chat_id"] == "12345678"
    assert "ALM-THR-TERM-ALM" in payload["text"]
    assert "ADM-00001" in payload["text"]

    assert len(deliveries) == 1
    d = deliveries[0]
    assert d.alarm_id == 42
    assert d.channel == "telegram"
    assert d.recipient == "123*5678"
    assert d.ok is True

