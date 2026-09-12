"""Merkez API — Faz 0 iskeleti (Kisi B).

Faz 0'da amac tek sey: yigin ayakta ve sozlesmeler okunabiliyor.
Faz 1'de (TB1) buraya ingestion, TimescaleDB yazimi ve gercek uclar gelir.
Uc sozlesmesi: contracts/openapi.yaml — alan adlari oradan degismez.
"""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__

CONTRACTS_DIR = Path(os.getenv("CONTRACTS_DIR", "/contracts"))
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
DB_DSN = os.getenv("DB_DSN", "")

app = FastAPI(
    title="Grid Up — Pano Beyni Merkez API",
    version=__version__,
    description="On-prem izleme platformu. Sozlesme: contracts/openapi.yaml",
)

# Gelistirmede frontend ayri portta (3000); uretimde nginx arkasinda ayni koken.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _tcp_ok(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _db_ok() -> bool:
    if not DB_DSN:
        return False
    try:
        import psycopg

        with psycopg.connect(DB_DSN, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


def load_contract(name: str) -> Any:
    """Sozlesmeyi diskten okur. Esik/adres sabitleri ASLA koda gomulmez (kural 10)."""
    path = CONTRACTS_DIR / name
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(text)
    return yaml.safe_load(text)


@app.get("/health")
def health() -> dict:
    contracts_ok = True
    loaded: dict[str, int] = {}
    try:
        alarms = load_contract("alarm-codes.yaml")
        modbus = load_contract("modbus-map.yaml")
        load_contract("mqtt-telemetry.schema.json")
        loaded = {
            "alarm_codes": len(alarms.get("alarms", [])),
            "hypotheses": len(alarms.get("hypotheses", [])),
            "modbus_blocks": len(modbus.get("blocks", [])),
        }
    except Exception:
        contracts_ok = False

    return {
        "ok": True,
        "version": __version__,
        "mqtt": _tcp_ok(MQTT_HOST, MQTT_PORT),
        "db": _db_ok(),
        "contracts": contracts_ok,
        "contracts_loaded": loaded,
    }


@app.get("/api/v1/panels")
def list_panels() -> list[dict]:
    """Faz 0: bos liste (frontend 404 almasin). Faz 1'de DB'den doldurulur."""
    return []


@app.get("/api/v1/alarms")
def list_alarms() -> list[dict]:
    """Faz 0: bos liste. Faz 2'de alarm yoneticisinden doldurulur."""
    return []
