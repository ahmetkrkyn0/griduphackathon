"""SCADA ag gecidinin yasam dongusu (TB3, Kisi B): Modbus TCP sunucusu + depodan periyodik tazeleme.

Uygulamanin olay dongusunde calisir. Port acilamazsa (baska surec, yetki) backend DURMAZ: alarm ve bildirim
zinciri SCADA aynasindan onemlidir. Hata /health'te `scada.error` olarak gorunur.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from ..db import StoreError
from .gateway import ScadaGateway
from .modbus_tcp import ModbusTcpServer

log = logging.getLogger("gridup.scada")


class ScadaService:
    def __init__(self, gateway: ScadaGateway, server: ModbusTcpServer, *, refresh_s: float) -> None:
        self.gateway = gateway
        self._server = server
        self._refresh_s = refresh_s
        self._task: asyncio.Task | None = None
        self.error: str | None = None

    @property
    def port(self) -> int | None:
        return self._server.port

    async def start(self) -> None:
        try:
            await self._server.start()
        except OSError as exc:
            self.error = f"Modbus TCP portu acilamadi: {exc}"
            log.error("%s — ag gecidi kapali, backend calismaya devam ediyor", self.error)
            return
        self._task = asyncio.create_task(self._refresh_loop(), name="scada-refresh")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        await self._server.stop()

    def status(self) -> dict[str, Any]:
        return {
            "listening": self._task is not None,
            "port": self.port,
            "error": self.error,
            **self.gateway.status(),
            "connections": dict(self._server.stats),
        }

    async def _refresh_loop(self) -> None:
        while True:
            try:
                await asyncio.to_thread(self.gateway.refresh)
            except StoreError as exc:
                log.warning("SCADA: depodan tazeleme basarisiz, tekrar denenecek: %s", exc)
            except Exception:
                log.exception("SCADA: tazeleme hatasi")
            await asyncio.sleep(self._refresh_s)
