"""WS /api/v1/stream — sunucudan istemciye tek yonlu canli akis (openapi.yaml x-websocket).

Ingest yazici thread'i `StreamHub.publish` cagirir; mesajlar olay dongusune guvenli
bicimde aktarilir ve her istemcinin kendi sinirli kuyruguna dagitilir. Yavas istemci
kuyrugu dolunca o guncellemeyi kacirir; digerleri ve ingest etkilenmez.
"""

from __future__ import annotations

import asyncio
from typing import Any

import anyio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/api/v1", tags=["stream"])


class StreamHub:
    def __init__(self, max_queue: int = 1000) -> None:
        self._clients: set[asyncio.Queue] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._max_queue = max_queue

    @property
    def has_clients(self) -> bool:
        return bool(self._clients)

    def subscribe(self) -> asyncio.Queue:
        """Olay dongusu icinden cagrilir."""
        self._loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._max_queue)
        self._clients.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._clients.discard(queue)

    def publish(self, message: dict[str, Any]) -> None:
        """Herhangi bir thread'den cagrilabilir."""
        loop = self._loop
        if loop is None or not self._clients:
            return
        try:
            loop.call_soon_threadsafe(self._fanout, message)
        except RuntimeError:  # dongu kapandi (uygulama duruyor)
            pass

    def _fanout(self, message: dict[str, Any]) -> None:
        for queue in list(self._clients):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                pass


@router.websocket("/stream")
async def stream(ws: WebSocket) -> None:
    state = ws.app.state
    await ws.accept()
    queue = state.hub.subscribe()
    try:
        await ws.send_json(
            {
                "type": "hello",
                "payload": {
                    "server_time": state.clock().isoformat(),
                    "api_version": state.contracts.api_version,
                },
            }
        )
        # Ham asyncio gorevleri DEGIL, anyio gorev grubu: biri bitince digeri iptal edilir,
        # distan gelen iptal (sunucu kapanisi) de etiketiyle yukari tasinir. Eski
        # asyncio.gather temizligi bu iptali etiketsiz bir CancelledError ile degistiriyordu.
        async with anyio.create_task_group() as tg:
            tg.start_soon(_send_updates, ws, queue, tg.cancel_scope)
            tg.start_soon(_wait_for_disconnect, ws, tg.cancel_scope)
    except WebSocketDisconnect:
        pass
    finally:
        state.hub.unsubscribe(queue)


async def _send_updates(ws: WebSocket, queue: asyncio.Queue, scope: anyio.CancelScope) -> None:
    try:
        while True:
            await ws.send_json(await queue.get())
    except Exception:  # istemci koptuysa gonderim hatasi beklenen durumdur
        pass
    scope.cancel()


async def _wait_for_disconnect(ws: WebSocket, scope: anyio.CancelScope) -> None:
    try:
        while (await ws.receive())["type"] != "websocket.disconnect":
            pass
    except Exception:  # kopmus baglantida receive hatasi da kopus demektir
        pass
    scope.cancel()
