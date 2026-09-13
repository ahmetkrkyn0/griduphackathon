"""Calisma ayarlari ve sozlesme yukleyici (Kisi B).

Esik, topic ve oncelik bilgisi ASLA koda gomulmez; hepsi `contracts/` dizininden
okunur (PLAN.md kural 10). Konteynerde /contracts salt okunur baglidir, bu yuzden
bir esik degisince yeniden build gerekmez — backend'i yeniden baslatmak yeter.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# x-topics icinde telemetri semasini tasiyan topic turleri (tel = periyodik, evt = olay aninda).
# hb ve cmd farkli icerik tasir; heartbeat TB2'de alarm yoneticisiyle birlikte eklenir.
INGEST_TOPIC_KINDS = ("tel", "evt")

PANO_ID_PLACEHOLDER = "{pano_id}"

# Yuksekten dusuge. SYS (izleme sistemi) is emri acar, INFO yalnizca ekrana duser.
PRIO_ORDER = ("P1", "P2", "P3", "SYS", "INFO")


@dataclass(frozen=True)
class Settings:
    contracts_dir: Path
    mqtt_host: str = "mosquitto"
    mqtt_port: int = 1883
    db_dsn: str = ""
    ingest_enabled: bool = True

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            contracts_dir=Path(os.getenv("CONTRACTS_DIR", "/contracts")),
            mqtt_host=os.getenv("MQTT_HOST", "mosquitto"),
            mqtt_port=int(os.getenv("MQTT_PORT", "1883")),
            db_dsn=os.getenv("DB_DSN", ""),
            ingest_enabled=os.getenv("INGEST_ENABLED", "1").lower() not in ("0", "false", "no"),
        )


class Contracts:
    """Backend'in okudugu sozlesmelerin tek, onceden indekslenmis gorunumu."""

    def __init__(self, telemetry_schema: dict, alarm_codes: dict, openapi: dict) -> None:
        self.telemetry_schema = telemetry_schema
        self.alarm_codes = alarm_codes
        self.api_version: str = openapi["info"]["version"]
        self.pano_id_re = re.compile(openapi["components"]["parameters"]["PanoId"]["schema"]["pattern"])
        self.thresholds: dict[str, Any] = alarm_codes["thresholds"]
        self._alarms = {alarm["code"]: alarm for alarm in alarm_codes["alarms"]}
        self.hypothesis_codes = {h["code"] for h in alarm_codes["hypotheses"]}
        self.ingest_topics: dict[str, int] = _ingest_topics(telemetry_schema)

    def alarm(self, code: str) -> dict | None:
        return self._alarms.get(code)

    def prio_of(self, code: str) -> str | None:
        alarm = self._alarms.get(code)
        return alarm["prio"] if alarm else None


def _ingest_topics(schema: dict) -> dict[str, int]:
    """x-topics -> {topic sablonu: QoS}; yalnizca telemetri semasini tasiyanlar."""
    topics = {
        template: int(spec.get("qos", 0))
        for template, spec in schema["x-topics"].items()
        if template.rsplit("/", 1)[-1] in INGEST_TOPIC_KINDS
    }
    if len(topics) != len(INGEST_TOPIC_KINDS):
        raise ValueError(f"x-topics icinde {INGEST_TOPIC_KINDS} topic'leri bulunamadi: {list(topics)}")
    return topics


def topic_filter(template: str) -> str:
    """'gridup/pano/{pano_id}/tel' -> MQTT abonelik filtresi 'gridup/pano/+/tel'."""
    return template.replace(PANO_ID_PLACEHOLDER, "+")


def topic_regex(template: str) -> re.Pattern[str]:
    """'gridup/pano/{pano_id}/tel' -> pano_id grubunu yakalayan tam eslesme deseni."""
    escaped = re.escape(template).replace(re.escape(PANO_ID_PLACEHOLDER), "(?P<pano_id>[^/]+)")
    return re.compile(f"^{escaped}$")


def load_contracts(contracts_dir: Path) -> Contracts:
    def read(name: str) -> str:
        return (contracts_dir / name).read_text(encoding="utf-8")

    return Contracts(
        telemetry_schema=json.loads(read("mqtt-telemetry.schema.json")),
        alarm_codes=yaml.safe_load(read("alarm-codes.yaml")),
        openapi=yaml.safe_load(read("openapi.yaml")),
    )
