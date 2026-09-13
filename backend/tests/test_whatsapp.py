"""TB2 Adim 6 — WhatsApp Cloud API gondericisi (app.notify.whatsapp).

Istek bicimi Meta'nin guncel belgesinden (developers.facebook.com/documentation/business-messaging/whatsapp):
POST https://graph.facebook.com/<surum>/<PHONE_NUMBER_ID>/messages, Bearer token. Serbest metin yalnizca
kullanicinin son 24 saatte yazdigi pencerede teslim edilir; pencere disinda onayli SABLON gerekir.
Gercek API'ye gidilmez: httpx.MockTransport uretilen istegin kendisini dogrular.
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.notify.whatsapp import WhatsAppClient, WhatsAppError

SUCCESS = {
    "messaging_product": "whatsapp",
    "contacts": [{"input": "905550000001", "wa_id": "905550000001"}],
    "messages": [{"id": "wamid.HBgMOTA1NTUwMDAwMDAxFQIAERgSQzA"}],
}


def recording_transport(requests: list[httpx.Request], status: int = 200, body: dict | None = None) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status, json=SUCCESS if body is None else body)

    return httpx.MockTransport(handler)


def test_free_text_message_request_matches_the_cloud_api():
    requests: list[httpx.Request] = []
    client = WhatsAppClient("gizli-token", "123456789", transport=recording_transport(requests))

    message_id = client.send("+90 555 000 00 01", "GRIDUP P2 alarm: ADM-00001 - test")

    [request] = requests
    assert message_id == "wamid.HBgMOTA1NTUwMDAwMDAxFQIAERgSQzA"
    assert (request.method, str(request.url)) == ("POST", "https://graph.facebook.com/v25.0/123456789/messages")
    assert request.headers["authorization"] == "Bearer gizli-token"
    assert json.loads(request.content) == {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": "905550000001",
        "type": "text",
        "text": {"preview_url": False, "body": "GRIDUP P2 alarm: ADM-00001 - test"},
    }


def test_template_message_is_used_when_a_template_is_configured():
    requests: list[httpx.Request] = []
    client = WhatsAppClient(
        "gizli-token", "123456789", template="gridup_alarm", language="tr", transport=recording_transport(requests)
    )

    client.send("+905550000001", "gorunmez", template_params=["P1", "ADM-00001", "TVOC-2 ark tripi"])

    assert json.loads(requests[0].content) == {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": "905550000001",
        "type": "template",
        "template": {
            "name": "gridup_alarm",
            "language": {"code": "tr"},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": "P1"},
                        {"type": "text", "text": "ADM-00001"},
                        {"type": "text", "text": "TVOC-2 ark tripi"},
                    ],
                }
            ],
        },
    }


@pytest.mark.parametrize("status,retryable", [(400, False), (401, False), (429, True), (500, True), (503, True)])
def test_api_errors_say_whether_retrying_can_help(status, retryable):
    error = {"error": {"message": "Re-engagement message", "type": "OAuthException", "code": 131047}}
    client = WhatsAppClient("gizli-token", "123456789", transport=recording_transport([], status, error))

    with pytest.raises(WhatsAppError) as caught:
        client.send("+905550000001", "test")

    assert caught.value.retryable is retryable
    assert "131047" in str(caught.value) and "Re-engagement message" in str(caught.value)
    assert "gizli-token" not in str(caught.value)


def test_network_failure_is_retryable():
    def offline(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("internet yok", request=request)

    client = WhatsAppClient("gizli-token", "123456789", transport=httpx.MockTransport(offline))

    with pytest.raises(WhatsAppError) as caught:
        client.send("+905550000001", "test")

    assert caught.value.retryable is True
