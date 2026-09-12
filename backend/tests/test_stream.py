"""TB1 — WS /api/v1/stream: hello + ingest edilen panolarin ozetleri (x-websocket sozlesmesi)."""

from __future__ import annotations

import queue
import threading
from datetime import datetime

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from fakes import MemoryStore
from helpers import CONTRACTS_DIR, encode, utc

NOW = utc(2026, 9, 13, 10, 5, 0)


def receive_json(ws, timeout_s: float = 3.0) -> dict:
    """Uygulama bozuksa test sonsuza dek beklemesin diye zaman asimli okuma."""
    box: queue.Queue = queue.Queue()
    threading.Thread(target=lambda: box.put(ws.receive_json()), daemon=True).start()
    return box.get(timeout=timeout_s)


def test_stream_sends_hello_then_summaries_of_ingested_panels(api_contract, tel_payload):
    store = MemoryStore([{"pano_id": "ADM-00001", "name": "Efeler TM-14"}])
    app = create_app(
        Settings(contracts_dir=CONTRACTS_DIR, ingest_enabled=False), store=store, clock=lambda: NOW
    )

    with TestClient(app) as client, client.websocket_connect("/api/v1/stream") as ws:
        hello = receive_json(ws)
        assert hello["type"] == "hello"
        assert hello["payload"]["api_version"] == "1.0.0"
        assert datetime.fromisoformat(hello["payload"]["server_time"]) == NOW

        app.state.pipeline.handle_message("gridup/pano/ADM-00001/tel", encode(tel_payload))
        assert app.state.pipeline.flush()

        update = receive_json(ws)
        assert update["type"] == "tel"
        api_contract(update["payload"], "PanelSummary")
        assert (update["payload"]["pano_id"], update["payload"]["risk_score"]) == ("ADM-00001", 38)


def test_every_connected_client_receives_updates(tel_payload):
    store = MemoryStore([{"pano_id": "ADM-00001", "name": "Efeler TM-14"}])
    app = create_app(
        Settings(contracts_dir=CONTRACTS_DIR, ingest_enabled=False), store=store, clock=lambda: NOW
    )

    with (
        TestClient(app) as client,
        client.websocket_connect("/api/v1/stream") as ws1,
        client.websocket_connect("/api/v1/stream") as ws2,
    ):
        receive_json(ws1)
        receive_json(ws2)

        app.state.pipeline.handle_message("gridup/pano/ADM-00001/tel", encode(tel_payload))
        assert app.state.pipeline.flush()

        assert receive_json(ws1)["payload"]["pano_id"] == "ADM-00001"
        assert receive_json(ws2)["payload"]["pano_id"] == "ADM-00001"
