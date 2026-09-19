"""Telegram Bot API gondericisi (Hizli ve ucretsiz anlik bildirim kanali).

POST https://api.telegram.org/bot<TOKEN>/sendMessage
    chat_id: kullanici veya grup sohbet kimligi
    text: HTML formatli zengin mesaj
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

log = logging.getLogger("gridup.notify.telegram")
DEFAULT_BASE_URL = "https://api.telegram.org"


class TelegramError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


class TelegramClient:
    def __init__(
        self,
        token: str,
        chat_id: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout_s: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._token = token.strip()
        self._chat_id = chat_id.strip()
        self._http = httpx.Client(
            base_url=f"{base_url.rstrip('/')}/bot{self._token}",
            timeout=timeout_s,
            transport=transport,
        )

    @property
    def chat_id(self) -> str:
        return self._chat_id

    def send(self, text: str) -> str:
        """Mesaj kimligini dondurur; basarisizlikta TelegramError."""
        payload: dict[str, Any] = {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            res = self._http.post("/sendMessage", json=payload)
        except httpx.RequestError as exc:
            raise TelegramError(f"Telegram baglanti hatasi: {exc}", retryable=True) from exc

        if res.status_code == 429 or 500 <= res.status_code < 600:
            raise TelegramError(f"Telegram gecici hata ({res.status_code}): {res.text}", retryable=True)
        if not res.is_success:
            raise TelegramError(f"Telegram istek reddi ({res.status_code}): {res.text}", retryable=False)

        data = res.json()
        if not data.get("ok"):
            raise TelegramError(f"Telegram API ok=False: {data}", retryable=False)
        msg_id = str((data.get("result") or {}).get("message_id", "ok"))
        log.info("Telegram bildirimi gonderildi -> chat_id: %s (msg_id: %s)", self._chat_id, msg_id)
        return msg_id

    def close(self) -> None:
        self._http.close()
