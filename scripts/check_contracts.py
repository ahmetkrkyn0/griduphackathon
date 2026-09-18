#!/usr/bin/env python3
"""Sozlesme denetimi — contracts/ dizini kendi kendini dogrular.

Neden var: esikler, Modbus adresleri ve alarm kodlari UC KULVARDA birden okunuyor
(PLAN.md kural 10). Sessiz bir tutarsizlik (cakisan adres, tanimsiz esik atfi,
hipotezde olmayan alarm kodu) en kotu anda, M2/M3 kapisinda ortaya cikar.
Bu betik onu commit aninda yakalar.

Kullanim:
    python scripts/check_contracts.py

Cikis kodu 0 = temiz, 1 = hata. Her PR oncesi ve sozlesme degisikliginden sonra kosun.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"

errors: list[str] = []
notes: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def load_json(name: str):
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


def load_yaml(name: str):
    return yaml.safe_load((CONTRACTS / name).read_text(encoding="utf-8"))


# --------------------------------------------------------------- 1) ayristirma
try:
    tel_schema = load_json("mqtt-telemetry.schema.json")
    scn_schema = load_json("scenario-labels.schema.json")
    modbus = load_yaml("modbus-map.yaml")
    alarms = load_yaml("alarm-codes.yaml")
    openapi = load_yaml("openapi.yaml")
except Exception as exc:  # noqa: BLE001
    print(f"HATA sozlesme okunamadi: {exc}")
    sys.exit(1)

notes.append("5 sozlesme dosyasi ayristirildi")

# ------------------------------------------------------ 2) JSON semalari gecerli
try:
    from jsonschema import Draft202012Validator

    for name, schema in (("mqtt-telemetry", tel_schema), ("scenario-labels", scn_schema)):
        Draft202012Validator.check_schema(schema)
    notes.append("JSON semalari draft 2020-12'e gore gecerli")
except ImportError:
    notes.append("! jsonschema kurulu degil -> sema dogrulamasi atlandi")

# ------------------------------------------------------------- 3) Modbus haritasi
owner: dict[int, str] = {}
for block in modbus["blocks"]:
    start, count, name = block["start"], block["count"], block["name"]
    for reg in range(start, start + count):
        if reg in owner:
            fail(f"Modbus adres cakismasi {reg}: '{owner[reg]}' <-> '{name}'")
            break
        owner[reg] = name

    points = block.get("points")
    if points and len(points) > count:
        fail(f"Modbus blok '{name}': {len(points)} nokta, yalnizca {count} register var")

    for item in block.get("items", []):
        if item["offset"] >= count:
            fail(f"Modbus blok '{name}': '{item['name']}' offset {item['offset']} >= count {count}")

block_names = {b["name"] for b in modbus["blocks"]}
for block in modbus["blocks"]:
    ref = block.get("points_ref")
    if ref and ref not in block_names:
        fail(f"Modbus blok '{block['name']}': points_ref '{ref}' diye blok yok")

conn = next(b for b in modbus["blocks"] if b["name"] == "conn_temp")
notes.append(
    f"Modbus: {len(modbus['blocks'])} blok, {len(owner)} register, "
    f"{len(conn['points'])} izleme noktasi, cakisma yok"
)

# Koruma devresine yazma olmamali (PLAN.md GK6)
arc = next(b for b in modbus["blocks"] if b["name"] == "arc_mirror")
if arc.get("access") != "read_only":
    fail("arc_mirror blogu read_only degil — TVOC-2'ye yazma riski (GK6 ihlali)")

write_blocks = [b["name"] for b in modbus["blocks"] if b.get("access") == "write"]
if write_blocks != ["command"]:
    fail(f"Yazilabilir blok yalnizca 'command' olmali, bulunan: {write_blocks}")

# -------------------------------------------------------------- 4) Alarm kodlari
bits: dict[int, str] = {}
codes: set[str] = set()
prios = set(alarms["priorities"])
thresholds = alarms["thresholds"]

for item in alarms["alarms"]:
    code, bit = item["code"], item["bit"]
    if bit in bits:
        fail(f"Alarm bit cakismasi {bit}: '{bits[bit]}' <-> '{code}'")
    bits[bit] = code
    codes.add(code)

    if item["prio"] not in prios:
        fail(f"{code}: tanimsiz oncelik '{item['prio']}'")

    # Tek esik bir dize, cok kosullu kural (or. ALM-NEUTRAL-THD: notr orani VE THD)
    # bir liste yazar. Liste kabul edilir ama HER UYESI ayri ayri denetlenir —
    # aksi halde ikinci esik sozlesmede gorunur, hicbir yerde dogrulanmazdi.
    refs = item.get("threshold")
    if refs:
        for ref in [refs] if isinstance(refs, str) else refs:
            if not isinstance(ref, str) or not ref.startswith("thresholds."):
                fail(f"{code}: esik atfi 'thresholds.' ile baslamali, bulunan '{ref}'")
            elif ref.split(".", 1)[1] not in thresholds:
                fail(f"{code}: tanimsiz esige atif '{ref}'")

max_bit = max(bits)
live_regs = len(alarms["bitmap"]["live_registers"])
if max_bit >= live_regs * 16:
    fail(f"Alarm biti {max_bit}, {live_regs} register'a ({live_regs * 16} bit) sigmiyor")

for hyp in alarms["hypotheses"]:
    for ev in hyp["evidence"]:
        if ev not in codes:
            fail(f"Hipotez {hyp['code']}: tanimsiz alarm koduna atif '{ev}'")

hyp_codes = {h["code"] for h in alarms["hypotheses"]}
for action in alarms["auto_actions"]:
    if action["trigger"] not in codes:
        fail(f"auto_actions: tanimsiz alarm koduna atif '{action['trigger']}'")
    if action["approval"] not in {"none", "human"}:
        fail(f"auto_actions '{action['trigger']}': approval 'none' veya 'human' olmali")

# P1 bastirilamaz olmali (rapor 2.4.3 / 6.6b)
if alarms["priorities"]["P1"].get("suppressible") is not False:
    fail("P1 oncelik suppressible=false olmali — kritik alarm bastirilamaz")

notes.append(
    f"Alarm: {len(codes)} kod (bit 0-{max_bit}), {len(hyp_codes)} hipotez, "
    f"{len(thresholds)} esik, {len(alarms['auto_actions'])} otomatik aksiyon"
)

# ------------------------------------------- 5) Sozlesmeler arasi capraz tutarlilik
pt_pattern = tel_schema["properties"]["t_conn"]["items"]["properties"]["pt"]["pattern"]
for point in conn["points"]:
    if not re.match(pt_pattern, point):
        fail(f"Modbus noktasi '{point}' MQTT semasindaki pt desenine uymuyor: {pt_pattern}")

max_points = tel_schema["properties"]["t_conn"]["maxItems"]
if len(conn["points"]) > max_points:
    fail(f"Modbus {len(conn['points'])} nokta tanimliyor, MQTT semasi en fazla {max_points} kabul ediyor")

alarm_pattern = tel_schema["properties"]["alarms"]["items"]["pattern"]
for code in sorted(codes):
    if not re.match(alarm_pattern, code):
        fail(f"Alarm kodu '{code}' MQTT semasindaki desene uymuyor: {alarm_pattern}")

risk_mode_codes = hyp_codes
expected_modes = {"HYP-NORMAL"}
if not expected_modes <= risk_mode_codes:
    fail("alarm-codes.yaml icinde HYP-NORMAL hipotezi tanimli olmali (risk.mode varsayilani)")

scn_expect_pattern = (
    scn_schema["properties"]["labels"]["items"]["properties"]["expect"]["items"]["pattern"]
)
for code in sorted(codes):
    if not re.match(scn_expect_pattern, code):
        fail(f"Alarm kodu '{code}' senaryo etiketi desenine uymuyor: {scn_expect_pattern}")

notes.append(f"Capraz tutarlilik: nokta adlari, alarm kodlari ve risk modlari uyumlu")

# --------------------------------------------------------------- 6) OpenAPI temel
required_paths = [
    "/health",
    "/api/v1/panels",
    "/api/v1/panels/{pano_id}",
    "/api/v1/panels/{pano_id}/series",
    "/api/v1/alarms",
    "/api/v1/alarms/{alarm_id}/ack",
    "/api/v1/alarms/{alarm_id}/shelve",
    "/api/v1/events/{event_id}/blackbox",
    "/api/v1/fleet/kpi",
    # v1.1.0'da eklenmis ama BU LISTEYE yazilmasi atlanmisti: sozlesmede vardi, denetleyici
    # kaybolmasini yakalamazdi. F-21 ile birlikte duzeltildi.
    "/api/v1/fleet/health",
    "/api/v1/fleet/assets",
    "/api/v1/fleet/peers",
    "/api/v1/outages",
]
for path in required_paths:
    if path not in openapi["paths"]:
        fail(f"OpenAPI: '{path}' ucu eksik (frontend buna guveniyor)")

if "x-websocket" not in openapi:
    fail("OpenAPI: x-websocket bolumu eksik (canli akis sozlesmesi)")

notes.append(f"OpenAPI: {len(openapi['paths'])} uc + WebSocket sozlesmesi")

# ------------------------------------------------------------------- 7) surumler
for name, doc in (("modbus-map.yaml", modbus), ("alarm-codes.yaml", alarms)):
    if "version" not in doc:
        fail(f"{name}: 'version' alani yok (degisiklik surecinde artirilmasi gerekir)")

# ----------------------------------------------------------------------- sonuc
for note in notes:
    print(f"OK   {note}")

if errors:
    print()
    for err in errors:
        print(f"HATA {err}")
    print(f"\n=== {len(errors)} HATA — sozlesmeler tutarsiz ===")
    sys.exit(1)

print("\n=== SOZLESMELER TUTARLI ===")
sys.exit(0)
