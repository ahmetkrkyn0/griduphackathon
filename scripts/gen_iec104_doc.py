#!/usr/bin/env python3
"""docs/04-iec104-haritasi.md tablolarini sozlesme + IEC 104 kodundan uretir (Kisi B, TB3 Adim 8).

Anlati elle yazilir; nokta plani, istasyon parametreleri ve zamanlayicilar isaretli bloklar arasinda uretilir ve ELLE DUZENLENMEZ
(PLAN.md kural 10). IOA plani backend/app/scada/iec104_points.py, zamanlayicilar iec104_server.py, alarm metin ve oncelikleri
contracts/alarm-codes.yaml'dan gelir.

    backend/.venv/Scripts/python scripts/gen_iec104_doc.py            # yeniler
    backend/.venv/Scripts/python scripts/gen_iec104_doc.py --check    # guncel degilse 1 ile cikar
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import load_contracts  # noqa: E402
from app.scada import iec104, iec104_points, iec104_server  # noqa: E402
from app.scada.encoder import PanelEncoder, source_docs  # noqa: E402
from app.scada.map_loader import load_map  # noqa: E402

DOC = ROOT / "docs" / "04-iec104-haritasi.md"


def _load():
    contracts = load_contracts(ROOT / "contracts")
    regmap = load_map(ROOT / "contracts" / "modbus-map.yaml")
    catalog = iec104_points.PointCatalog(regmap, PanelEncoder(regmap, contracts))
    return contracts, regmap, catalog


def _number(value: float) -> str:
    return format(value, "g")


def measured_rows() -> list[dict[str, Any]]:
    _, regmap, catalog = _load()
    sources = source_docs(regmap)
    rows = []
    for point in catalog.measured:
        register = regmap.register(point.name)
        rows.append({
            "ioa": point.ioa,
            "ad": point.name,
            "pdu": point.address,
            "birim": register.unit or "",
            "olcek": _number(point.scale),
            "olu_bant": _number(point.deadband),
            "gecersiz": f"ham 0x{point.na:04X}" if point.na is not None else "-",
            "kaynak": sources[point.name],
        })
    return rows


def single_rows() -> list[dict[str, Any]]:
    contracts, regmap, catalog = _load()
    sources = source_docs(regmap)
    rows = []
    for point in catalog.single:
        if point.kind == "alarm":
            alarm = contracts.alarm(point.name) or {}
            rows.append({"ioa": point.ioa, "ad": point.name, "tur": f"alarm biti {point.index}",
                         "oncelik": alarm.get("prio", "-"), "aciklama": alarm.get("text", "")})
        else:
            rows.append({"ioa": point.ioa, "ad": point.name, "tur": f"coil {point.index}", "oncelik": "-",
                         "aciklama": sources[f"coils.{point.name}"]})
    return rows


def _cell(value: Any) -> str:
    text = "-" if value in (None, "") else str(value)
    return text.replace("|", "\\|")


def table_station() -> str:
    timing = iec104_server.Timing()
    return "\n".join([
        "| Parametre | Deger |",
        "|---|---|",
        "| Rol | Kontrollu istasyon (slave), TCP 2404 |",
        "| Ortak adres (CA) | Modbus birim numarasi (`MODBUS_UNITS` veya otomatik) |",
        f"| Yayin adresi | `0x{iec104.BROADCAST_COMMON_ADDRESS:04X}` = tum istasyonlar; her istasyon KENDI ortak adresiyle cevaplar "
        "(IEC 60870-5-101/104 7.2.4); hic istasyon yoksa hemen ret (COT 46) |",
        "| IOA | 3 bayt |",
        f"| k / w | {timing.k} / {timing.w} |",
        f"| t1 / t2 / t3 | {_number(timing.t1)} s / {_number(timing.t2)} s / {_number(timing.t3)} s |",
        f"| Kendiliginden gonderim taramasi | {_number(timing.spontaneous)} s |",
        f"| Nesne / ASDU | zamansiz en cok {iec104_server.MONITOR_OBJECTS}, zaman etiketli en cok {iec104_server.TIME_TAGGED_OBJECTS} |",
    ])


def table_asdu() -> str:
    rows = [
        (iec104.M_ME_NC_1, "`M_ME_NC_1`", "izleme", "Olculen deger, kisa kayan nokta + QDS", "20 (sorgulama)"),
        (iec104.M_ME_TF_1, "`M_ME_TF_1`", "izleme", "Olculen deger + CP56Time2a (UTC)", "3 (kendiliginden)"),
        (iec104.M_SP_NA_1, "`M_SP_NA_1`", "izleme", "Tek nokta + SIQ", "20"),
        (iec104.M_SP_TB_1, "`M_SP_TB_1`", "izleme", "Tek nokta + CP56Time2a (UTC)", "3"),
        (iec104.C_IC_NA_1, "`C_IC_NA_1`", "komut", "Istasyon sorgulamasi (QOI 20): ACTCON -> veriler -> ACTTERM", "6 -> 7, 20, 10"),
        (iec104.C_CS_NA_1, "`C_CS_NA_1`", "komut", "Saat senkronu: istasyon saatiyle ACTCON (saat disaridan degistirilmez)", "6 -> 7"),
        (f"{iec104.C_SC_NA_1}, {iec104.C_DC_NA_1}, ...", "`C_SC_NA_1`, `C_DC_NA_1` ve diger tum tipler", "komut",
         "**Reddedilir** (istasyon salt okunur, GK6)", f"-> {iec104.COT_UNKNOWN_TYPE} + P/N"),
    ]
    lines = ["| Tip | Ad | Yon | Anlami | COT |", "|---|---|---|---|---|"]
    lines += [f"| {type_id} | {name} | {direction} | {meaning} | {cot} |" for type_id, name, direction, meaning, cot in rows]
    lines.append(f"| - | Bilinmeyen ortak adres | - | Reddedilir | -> {iec104.COT_UNKNOWN_COMMON_ADDRESS} + P/N |")
    lines.append(f"| - | Desteklenmeyen iletim nedeni | - | Reddedilir | -> {iec104.COT_UNKNOWN_CAUSE} + P/N |")
    return "\n".join(lines)


def table_measured() -> str:
    lines = ["| IOA | Ad | Modbus PDU | Birim | Olcek | Olu bant | IV (gecersiz) kosulu | Merkez kaynagi |", "|---|---|---|---|---|---|---|---|"]
    for row in measured_rows():
        lines.append(f"| {row['ioa']} | `{row['ad']}` | {row['pdu']} | {_cell(row['birim'])} | {row['olcek']} | {row['olu_bant']} "
                     f"| {row['gecersiz']} | {_cell(row['kaynak'])} |")
    return "\n".join(lines)


def table_single() -> str:
    lines = ["| IOA | Ad | Tur | Oncelik | Aciklama |", "|---|---|---|---|---|"]
    for row in single_rows():
        lines.append(f"| {row['ioa']} | `{row['ad']}` | {row['tur']} | {row['oncelik']} | {_cell(row['aciklama'])} |")
    return "\n".join(lines)


BLOCKS = {"istasyon": table_station, "asdu": table_asdu, "olculen": table_measured, "tek-nokta": table_single}


def render(doc: str) -> str:
    for name, build in BLOCKS.items():
        pattern = re.compile(rf"(<!-- URETILMIS:{name} -->\n)(?:.*?\n)?(<!-- /URETILMIS:{name} -->)", re.S)
        if not pattern.search(doc):
            raise SystemExit(f"{DOC.name} icinde '{name}' blogu yok")
        table = build()
        doc = pattern.sub(lambda m: m[1] + table + "\n" + m[2], doc)
    return doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="dokuman guncel degilse 1 ile cik")
    args = parser.parse_args(argv)
    current = DOC.read_bytes().decode("utf-8")
    updated = render(current)
    if args.check:
        if updated != current:
            print(f"{DOC.relative_to(ROOT)} guncel degil: python scripts/gen_iec104_doc.py")
            return 1
        print("guncel")
        return 0
    DOC.write_bytes(updated.encode("utf-8"))
    print(f"yenilendi: {DOC.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
