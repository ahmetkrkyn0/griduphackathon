"""WS /api/v1/stream — sunucudan istemciye tek yonlu canli akis (openapi.yaml x-websocket).

Ingest yazici thread'i `StreamHub.publish` cagirir; mesajlar olay dongusune guvenli
bicimde aktarilir ve her istemcinin kendi sinirli kuyruguna dagitilir. Yavas istemci
kuyrugu dolunca o guncellemeyi kacirir; digerleri ve ingest etkilenmez.
"""

from __future__ import annotations

import asyncio
from typing import Any

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
        sender = asyncio.create_task(_send_updates(ws, queue))
        watcher = asyncio.create_task(_wait_for_disconnect(ws))
        done, pending = await asyncio.wait({sender, watcher}, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        for task in done:
            task.exception()  # istemci koptuysa gonderim hatasi beklenen durumdur
    except WebSocketDisconnect:
        pass
    finally:
        state.hub.unsubscribe(queue)


async def _send_updates(ws: WebSocket, queue: asyncio.Queue) -> None:
    while True:
        await ws.send_json(await queue.get())


async def _wait_for_disconnect(ws: WebSocket) -> None:
    while (await ws.receive())["type"] != "websocket.disconnect":
        pass
