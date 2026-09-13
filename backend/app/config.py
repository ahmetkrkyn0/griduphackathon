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
COMMAND_TOPIC_KIND = "cmd"  # merkez -> kenar komutu (SCADA bakim modu / test alarmi)

# OT aglari ozel adreslerdir; sahada SCADA on-uc sunucusunun adresine daraltilir (rapor 7.4 "IP beyaz liste").
DEFAULT_MODBUS_ALLOWED_CLIENTS = ("127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "::1/128")

PANO_ID_PLACEHOLDER = "{pano_id}"

# Yuksekten dusuge. SYS (izleme sistemi) is emri acar, INFO yalnizca ekrana duser.
PRIO_ORDER = ("P1", "P2", "P3", "SYS", "INFO")


@dataclass(frozen=True)
class Settings:
    contracts_dir: Path
    mqtt_host: str = "mosquitto"
    mqtt_port: int = 1883
    db_dsn: str = ""
    ingest_enabled: bool = True  # False: MQTT abonesi ve arka plan isleri (yazici, alarm zamanlayicisi) calismaz
    alarm_tick_s: float = 5.0  # raf suresi + haberlesme denetimi araligi
    # --- SCADA Modbus TCP ag gecidi (TB3). Varsayilan: salt okunur, yalnizca ozel aglardan. ---
    modbus_enabled: bool = False
    modbus_host: str = "0.0.0.0"
    modbus_port: int = 502
    modbus_password: int | None = None  # None -> hicbir yazma kabul edilmez
    modbus_units: str = ""  # "1=ADM-00001,2=ADM-00002"; bos -> otomatik (yalnizca demo)
    modbus_allowed_clients: tuple[str, ...] = DEFAULT_MODBUS_ALLOWED_CLIENTS
    modbus_refresh_s: float = 30.0

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            contracts_dir=Path(os.getenv("CONTRACTS_DIR", "/contracts")),
            mqtt_host=os.getenv("MQTT_HOST", "mosquitto"),
            mqtt_port=int(os.getenv("MQTT_PORT", "1883")),
            db_dsn=os.getenv("DB_DSN", ""),
            ingest_enabled=os.getenv("INGEST_ENABLED", "1").lower() not in ("0", "false", "no"),
            alarm_tick_s=float(os.getenv("ALARM_TICK_S", "5")),
            modbus_enabled=os.getenv("MODBUS_ENABLED", "1").lower() not in ("0", "false", "no"),
            modbus_host=os.getenv("MODBUS_HOST", "0.0.0.0"),
            modbus_port=int(os.getenv("MODBUS_TCP_PORT", "502")),
            modbus_password=parse_modbus_password(os.getenv("MODBUS_WRITE_PASSWORD", "")),
            modbus_units=os.getenv("MODBUS_UNITS", "").strip(),
            modbus_allowed_clients=_csv(os.getenv("MODBUS_ALLOWED_CLIENTS", "")) or DEFAULT_MODBUS_ALLOWED_CLIENTS,
            modbus_refresh_s=float(os.getenv("MODBUS_REFRESH_S", "30")),
        )


def parse_modbus_password(value: str) -> int | None:
    """MODBUS_WRITE_PASSWORD: bos -> None (salt okunur); aksi halde 1-65535 (0, register'in bos halidir)."""
    value = value.strip()
    if not value:
        return None
    if not value.isdigit() or not 1 <= int(value) <= 0xFFFF:
        raise ValueError("MODBUS_WRITE_PASSWORD 1-65535 arasinda bir tam sayi olmali")
    return int(value)


def _csv(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


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
        self.command_topic, self.command_qos = _command_topic(telemetry_schema)

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


def _command_topic(schema: dict) -> tuple[str, int]:
    for template, spec in schema["x-topics"].items():
        if template.rsplit("/", 1)[-1] == COMMAND_TOPIC_KIND:
            return template, int(spec.get("qos", 0))
    raise ValueError(f"x-topics icinde '{COMMAND_TOPIC_KIND}' topic'i bulunamadi")


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
