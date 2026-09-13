"""WhatsApp Cloud API gondericisi (TB2 Adim 6, Kisi B) — IKINCIL kanal.

On-Premises API 23 Ekim 2025'te kapatildi; yalnizca Meta Cloud API var. Bu yuzden sirket disina cikan
TEK kanaldir (PLAN.md GK4): yalnizca hassas olmayan kisa metin (notify/templates.py), telemetri asla.

    POST https://graph.facebook.com/<surum>/<PHONE_NUMBER_ID>/messages     (Bearer token, .env'den)

Teslim kurali (Meta): serbest metin yalnizca kullanicinin son 24 saatte isletme numarasina yazdigi
"musteri hizmeti penceresi" icinde teslim edilir; pencere disinda yalnizca onayli SABLON gonderilebilir.
WHATSAPP_TEMPLATE tanimliysa sablon, degilse serbest metin gonderilir (demo: alici once test numarasina
bir mesaj atar). Ag yoksa / 5xx / 429 tekrar denenebilir; diger 4xx (yetki, pencere disi) denenmez.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://graph.facebook.com"
DEFAULT_API_VERSION = "v25.0"
RATE_LIMITED = 429


class WhatsAppError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


class WhatsAppClient:
    def __init__(
        self,
        token: str,
        phone_number_id: str,
        *,
        api_version: str = DEFAULT_API_VERSION,
        template: str | None = None,
        language: str = "tr",
        base_url: str = DEFAULT_BASE_URL,
        timeout_s: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._path = f"/{api_version}/{phone_number_id}/messages"
        self._template = template or None
        self._language = language
        self._http = httpx.Client(
            base_url=base_url,
            timeout=timeout_s,
            transport=transport,
            headers={"Authorization": f"Bearer {token}"},
        )

    def send(self, to: str, text: str, template_params: Sequence[str] = ()) -> str:
        """Mesaj kimligini (wamid) dondurur; basarisizlikta WhatsAppError."""
        body: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": "".join(char for char in to if char.isdigit()),
        }
        if self._template:
            body["type"] = "template"
            body["template"] = {
                "name": self._template,
                "language": {"code": self._language},
                "components": [
                    {"type": "body", "parameters": [{"type": "text", "text": value} for value in template_params]}
                ],
            }
        else:
            body["type"] = "text"
            body["text"] = {"preview_url": False, "body": text}

        try:
            response = self._http.post(self._path, json=body)
        except httpx.HTTPError as exc:
            raise WhatsAppError(f"WhatsApp API erisilemedi: {exc.__class__.__name__}: {exc}", retryable=True) from exc
        if response.status_code >= 400:
            raise WhatsAppError(
                f"WhatsApp API {response.status_code}: {_error_detail(response)}",
                retryable=response.status_code >= 500 or response.status_code == RATE_LIMITED,
            )
        return response.json()["messages"][0]["id"]

    def close(self) -> None:
        self._http.close()


def _error_detail(response: httpx.Response) -> str:
    try:
        error = response.json().get("error", {})
    except ValueError:
        return response.text[:200]
    return f"({error.get('code')}) {error.get('message', '')}".strip()
