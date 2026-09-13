"""SCADA ag gecidinin yasam dongusu (TB3, Kisi B): Modbus TCP + IEC 60870-5-104 sunuculari + depodan periyodik tazeleme.

Uygulamanin olay dongusunde calisir. Iki protokol ayni ag gecidini (birim eslemesi, bellek goruntusu) paylasir. Port acilamazsa
(baska surec, yetki) backend DURMAZ: alarm ve bildirim zinciri SCADA aynasindan onemlidir. Hata /health'te gorunur.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any

from ..db import StoreError
from .gateway import ScadaGateway
from .iec104_points import PointCatalog, PointValue
from .iec104_server import Iec104Server
from .modbus_tcp import ModbusTcpServer

log = logging.getLogger("gridup.scada")


class GatewayStations:
    """IEC 104 istasyon kaynagi: ortak adres = Modbus birimi; degerler ag gecidinin goruntusunden (Modbus ile ayni)."""

    def __init__(self, gateway: ScadaGateway, catalog: PointCatalog, clock: Callable[[], datetime]) -> None:
        self._gateway = gateway
        self._catalog = catalog
        self._clock = clock
        self._deadbands = {point.ioa: point.deadband for point in catalog.measured}

    def common_addresses(self) -> Sequence[int]:
        return sorted(self._gateway.units())

    def point_values(self, common_address: int) -> Sequence[PointValue] | None:
        try:
            image = self._gateway.panel_image(common_address)
        except KeyError:
            return None
        return self._catalog.values(image)

    def deadband(self, ioa: int) -> float:
        return self._deadbands.get(ioa, 0.0)

    def clock(self) -> datetime:
        return self._clock()


class _Listener:
    """Bir protokol sunucusunun baslatma durumu."""

    def __init__(self, name: str, server: ModbusTcpServer | Iec104Server) -> None:
        self.name = name
        self.server = server
        self.listening = False
        self.error: str | None = None

    async def start(self) -> None:
        try:
            await self.server.start()
            self.listening = True
        except OSError as exc:
            self.error = f"{self.name} portu acilamadi: {exc}"
            log.error("%s — bu protokol kapali, backend calismaya devam ediyor", self.error)

    async def stop(self) -> None:
        if self.listening:
            await self.server.stop()
            self.listening = False

    def status(self) -> dict[str, Any]:
        return {"listening": self.listening, "port": self.server.port, "error": self.error, "stats": dict(self.server.stats)}


class ScadaService:
    def __init__(
        self,
        gateway: ScadaGateway,
        modbus: ModbusTcpServer | None,
        *,
        refresh_s: float,
        iec104: Iec104Server | None = None,
    ) -> None:
        self.gateway = gateway
        self._modbus = _Listener("Modbus TCP", modbus) if modbus is not None else None
        self._iec104 = _Listener("IEC 104", iec104) if iec104 is not None else None
        self._refresh_s = refresh_s
        self._task: asyncio.Task | None = None

    @property
    def port(self) -> int | None:
        return self._modbus.server.port if self._modbus is not None else None

    @property
    def iec104_port(self) -> int | None:
        return self._iec104.server.port if self._iec104 is not None else None

    @property
    def error(self) -> str | None:
        return self._modbus.error if self._modbus is not None else None

    async def start(self) -> None:
        listeners = [listener for listener in (self._modbus, self._iec104) if listener is not None]
        for listener in listeners:
            await listener.start()
        if any(listener.listening for listener in listeners):
            self._task = asyncio.create_task(self._refresh_loop(), name="scada-refresh")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        for listener in (self._modbus, self._iec104):
            if listener is not None:
                await listener.stop()

    def status(self) -> dict[str, Any]:
        modbus = self._modbus
        return {
            "listening": bool(modbus and modbus.listening),
            "port": self.port,
            "error": self.error,
            **self.gateway.status(),
            "connections": dict(modbus.server.stats) if modbus is not None else {},
            "iec104": self._iec104.status() if self._iec104 is not None else None,
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
