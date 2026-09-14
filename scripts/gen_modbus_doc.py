#!/usr/bin/env python3
"""docs/03-modbus-haritasi.md tablolarini ve CSV'sini contracts/modbus-map.yaml + ag gecidi kodundan uretir (Kisi B).

Dokumandaki anlati elle yazilir; adres, kodlama, komut, istisna ve hat butcesi tablolari isaretli bloklar
arasinda uretilir ve ELLE DUZENLENMEZ (PLAN.md kural 10). Merkez kaynagi sutunu backend/app/scada/encoder.py
kaynak tablosundan, komut ve istisna sayilari gateway.py / modbus_tcp.py sabitlerinden gelir: kod degisirse
dokuman da degisir.

    backend/.venv/Scripts/python scripts/gen_modbus_doc.py            # yeniler
    backend/.venv/Scripts/python scripts/gen_modbus_doc.py --check    # guncel degilse 1 ile cikar (PR oncesi)
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.scada import encoder, gateway, modbus_tcp  # noqa: E402  (backend paketi yukaridaki yoldan)
from app.scada.map_loader import RegisterMap, load_map  # noqa: E402

CONTRACT = ROOT / "contracts" / "modbus-map.yaml"
DOC = ROOT / "docs" / "03-modbus-haritasi.md"
CSV_PATH = ROOT / "docs" / "03-modbus-haritasi.csv"

HOLDING_BASE, INPUT_BASE, COIL_BASE, DISCRETE_BASE = 40001, 30001, 1, 10001
RTU_REQUEST_CHARS = 8  # adres 1 + fonksiyon 1 + baslangic 2 + adet 2 + CRC 2
RTU_RESPONSE_OVERHEAD = 5  # adres 1 + fonksiyon 1 + bayt sayisi 1 + CRC 2 (+ 2 x register)
RTU_SILENCE_CHARS = 7  # iki cerceve arasi 3,5 karakter sessizlik x 2
CSV_COLUMNS = ("pdu", "holding", "input", "ad", "blok", "tip", "olcek", "birim", "erisim", "tvoc2_pdu", "merkez_kaynagi", "not")


def _cell(value: Any) -> str:
    text = "-" if value in (None, "") else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def _range(start: int, end: int) -> str:
    return str(start) if start == end else f"{start}-{end}"


def line_budget(*, baud: int, bits_per_char: int, counts: Iterable[int] = (10, 50, 100, 125)) -> list[tuple[int, int, float]]:
    """FC03 RTU okumasi: (register adedi, karakter, ms). Istek + yanit + iki 3,5 karakterlik sessizlik."""
    rows = []
    for count in counts:
        chars = RTU_REQUEST_CHARS + RTU_RESPONSE_OVERHEAD + 2 * count
        rows.append((count, chars, (chars + RTU_SILENCE_CHARS) * bits_per_char / baud * 1000.0))
    return rows


def register_rows(regmap: RegisterMap) -> list[dict[str, Any]]:
    sources = encoder.source_docs(regmap)
    rows = []
    for block in regmap.blocks:
        for register in block.registers:
            rows.append(
                {
                    "pdu": register.address,
                    "holding": HOLDING_BASE + register.address,
                    "input": INPUT_BASE + register.address,
                    "ad": register.name,
                    "blok": block.name,
                    "tip": register.type,
                    "olcek": format(register.scale, "g") if register.scale is not None else "",
                    "birim": register.unit or "",
                    "erisim": register.access,
                    "tvoc2_pdu": str(register.src_pdu) if register.src_pdu is not None else "",
                    "merkez_kaynagi": sources[register.name],
                    "not": register.note or "",
                }
            )
    return rows


def csv_bytes(rows: Sequence[dict[str, Any]]) -> bytes:
    """Turkce Excel: ';' liste ayiraci + UTF-8 BOM. Satir sonu LF (repo eol=lf; --check bayt bayt karsilastirir)."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, delimiter=";", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8")


# ------------------------------------------------------------------ uretilen bloklar
def table_summary(regmap: RegisterMap, raw: dict) -> str:
    registers = sum(len(block.registers) for block in regmap.blocks)
    return "\n".join(
        [
            "| Alan | Deger |",
            "|---|---|",
            f"| Harita surumu | {regmap.version} |",
            f"| Bayt sirasi | {raw.get('endianness', '-')} |",
            f"| 32 bit deger word sirasi | {raw.get('word_order', '-')} |",
            f"| FC03 / FC04 aynasi | {'evet' if regmap.mirror_fc03_fc04 else 'hayir'} |",
            f"| Blok / tanimli register / coil | {len(regmap.blocks)} / {registers} / {len(regmap.coils)} |",
            f"| Izleme noktasi (conn_temp, conn_dt, k_index ayni sira) | {len(regmap.points)} |",
            f"| Birim (unit id) | 1-{gateway.MAX_UNIT}, her birim bir pano |",
        ]
    )


def table_blocks(regmap: RegisterMap, raw: dict) -> str:
    rows = ["| Blok | PDU adresi | Holding (FC03) | Adet | Erisim | Kaynak cihaz | Not |", "|---|---|---|---|---|---|---|"]
    for block in regmap.blocks:
        end = block.end - 1
        rows.append(
            f"| `{block.name}` | {_range(block.start, end)} | {_range(HOLDING_BASE + block.start, HOLDING_BASE + end)} "
            f"| {block.count} | {block.access} | {_cell(block.source)} | {_cell(block.note)} |"
        )
    return "\n".join(rows)


def table_registers(regmap: RegisterMap, raw: dict) -> str:
    rows = [
        "| PDU | 4xxxx | 3xxxx | Ad | Tip | Olcek | Birim | Erisim | TVOC-2 PDU | Merkez kaynagi | Not |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in register_rows(regmap):
        rows.append(
            f"| {row['pdu']} | {row['holding']} | {row['input']} | `{row['ad']}` | {row['tip']} | {_cell(row['olcek'])} "
            f"| {_cell(row['birim'])} | {row['erisim']} | {_cell(row['tvoc2_pdu'])} | {_cell(row['merkez_kaynagi'])} "
            f"| {_cell(row['not'])} |"
        )
    return "\n".join(rows)


def table_coils(regmap: RegisterMap, raw: dict) -> str:
    sources = encoder.source_docs(regmap)
    rows = ["| Adres | Coil (FC01) | Discrete input (FC02) | Ad | Merkez kaynagi | Not |", "|---|---|---|---|---|---|"]
    for coil in regmap.coils:
        rows.append(
            f"| {coil.address} | {COIL_BASE + coil.address:05d} | {DISCRETE_BASE + coil.address} | `{coil.name}` "
            f"| {_cell(sources[f'coils.{coil.name}'])} | {_cell(coil.note)} |"
        )
    return "\n".join(rows)


def table_encoding(regmap: RegisterMap, raw: dict) -> str:
    return "\n".join(
        [
            "| Kural | Deger |",
            "|---|---|",
            "| Olcek | ham = fiziksel / `scale`, yarim yukari yuvarlanir (4,35 x 10 -> 44) |",
            "| Negatif int16 | ikiye tumleyen uint16 (-2,5 K x 10 = -25 -> 65511) |",
            f"| Aralik disi olcum | DOYAR: int16 +-{encoder.INT16_LIMIT}, uint16 0-{encoder.UINT16_LIMIT} (sarmaz) |",
            "| Sayac ve bit alani | 16 bit sarar (heartbeat, trip sayaci, olay sayaci) |",
            f"| 'Yok' int16 | 0x{encoder.NA_INT16:04X} ({encoder.NA_INT16}) |",
            f"| 'Yok' uint16 | 0x{encoder.NA_UINT16:04X} ({encoder.NA_UINT16}); sozlesme notu farkliysa not kazanir (voc_idx, pd blogu) |",
            "| Tanimsiz (yedek) register | 0 |",
            f"| 32 bit deger | iki register, `word_order` = {raw.get('word_order', '-')} (event.ts_hi / ts_lo) |",
            f"| Canli alarm biti | durum {' / '.join(encoder.LIVE_STATES)} ve kosul suruyor; rafa alinmis alarm duyurulmaz |",
            "| Mandalli alarm biti | canli + onaysiz + saklanan mandal; `reset_latch` komutuyla silinir |",
            "| Haberlesme | son veri `heartbeat_timeout_min` icindeyse `comms_ok` = 1; aksi halde son degerler sunulur |",
        ]
    )


def table_commands(regmap: RegisterMap, raw: dict) -> str:
    command = regmap.block("command")
    by_name = {register.name.split(".", 1)[1]: register.address for register in command.registers}
    reserved = [address for address in range(command.start, command.end) if address not in by_name.values()]
    unlock = f"{gateway.UNLOCK_S:.0f} s"
    rows = [
        "| PDU | Ad | Yazilabilir deger | Etki |",
        "|---|---|---|---|",
        f"| {by_name['password']} | `password` | 1-65535 | Dogruysa bu TCP baglantisi {unlock} acilir (ayni FC16 istegindeki komutlar da calisir). "
        f"Yanlissa 0x03; ayni IP'den {gateway.MAX_PASSWORD_FAILURES} yanlis -> {gateway.LOCKOUT_S:.0f} s yazma kilidi. Okumada hep 0. |",
        f"| {by_name['ack_alarm']} | `ack_alarm` | 0 / 1-{gateway.ACK_MAX_BIT_VALUE} / {gateway.ACK_ALL} | yok / bit numarasi + 1 olan koddaki "
        "alarmlar / panonun tum onaylanabilir alarmlari. Merkez alarm yoneticisinde onaylanir; denetim izine "
        "`SCADA Modbus <ip> (birim N)` yazilir. |",
        f"| {by_name['reset_latch']} | `reset_latch` | 0 / 1 | yok / mandalli bitleri sil (kosulu suren ve onaysiz alarmlarin biti yine gorunur) |",
        f"| {by_name['maint_mode']} | `maint_mode` | 0 / {gateway.MAINT_ON} / {gateway.MAINT_OFF} | yok / bakim modu ac / kapat -> MQTT `cmd` ile KENARA. "
        "Okumada kenarin bildirdigi `health.maint_mode`. P1 bakim modunda da bastirilmaz. |",
        f"| {by_name['test_alarm']} | `test_alarm` | 0 / 1 | yok / sentetik test alarmi -> MQTT `cmd` ile kenara |",
    ]
    if reserved:
        rows.append(f"| {_range(reserved[0], reserved[-1])} | (yedek) | 0 | baska deger 0x03 |")
    return "\n".join(rows)


EXCEPTION_MEANINGS = {
    modbus_tcp.ExceptionCode.ILLEGAL_FUNCTION: "Desteklenmeyen fonksiyon (FC05/15 coil yazma, FC43 vb.); yazma kapali (sifre tanimsiz); "
    "baglanti kilidi acilmamis veya suresi dolmus; istemci yanlis sifre kilidinde",
    modbus_tcp.ExceptionCode.ILLEGAL_DATA_ADDRESS: "Aralik harita bloklarinin disinda veya iki bloga tasiyor; tanimsiz coil; "
    "komut blogu disina yazma (TVOC-2 aynasi dahil, GK6)",
    modbus_tcp.ExceptionCode.ILLEGAL_DATA_VALUE: f"Adet siniri (okuma 1-{modbus_tcp.MAX_READ_REGISTERS} register / 1-{modbus_tcp.MAX_READ_BITS} bit, "
    f"yazma 1-{modbus_tcp.MAX_WRITE_REGISTERS}), bozuk PDU; yanlis sifre; gecersiz komut degeri",
    modbus_tcp.ExceptionCode.SLAVE_DEVICE_FAILURE: "Ag gecidinde beklenmeyen hata (kayda duser, baglanti acik kalir)",
    modbus_tcp.ExceptionCode.GATEWAY_PATH_UNAVAILABLE: "Birim (unit id) bir panoya eslenmemis",
    modbus_tcp.ExceptionCode.GATEWAY_TARGET_FAILED: "Panonun merkezde verisi yok; alarm durumu henuz yuklenmedi (alarm bitleri 0 okunup "
    "'alarm yok' sanilmasin); komut kenara iletilemedi (MQTT kopuk)",
}


def table_exceptions(regmap: RegisterMap, raw: dict) -> str:
    rows = ["| Kod | Modbus adi | Ag gecidinde ne zaman |", "|---|---|---|"]
    for code in modbus_tcp.ExceptionCode:
        rows.append(f"| 0x{code.value:02X} | {code.name} | {EXCEPTION_MEANINGS[code]} |")
    return "\n".join(rows)


def table_line_budget(regmap: RegisterMap, raw: dict) -> str:
    budget = raw["line_budget"]
    baud, bits = int(budget["baud"]), int(budget["bits_per_char"])
    rows = [
        f"Hat: {baud} baud, {budget.get('framing', '-')} = {bits} bit/karakter; hedef tur suresi "
        f"{budget.get('poll_cycle_target_ms', '-')} ms.",
        "",
        "| FC03 okuma | Karakter (istek + yanit) | Hat suresi |",
        "|---|---|---|",
    ]
    for count, chars, ms in line_budget(baud=baud, bits_per_char=bits):
        rows.append(f"| {count} register | {chars} | ~{ms:.0f} ms |")
    return "\n".join(rows)


BLOCKS = {
    "ozet": table_summary,
    "bloklar": table_blocks,
    "kodlama": table_encoding,
    "registerler": table_registers,
    "coiller": table_coils,
    "komutlar": table_commands,
    "istisnalar": table_exceptions,
    "hat-butcesi": table_line_budget,
}


def render(doc: str, regmap: RegisterMap, raw: dict, only: Sequence[str] | None = None) -> str:
    for name in only or tuple(BLOCKS):
        pattern = re.compile(rf"(<!-- URETILMIS:{name} -->\n)(?:.*?\n)?(<!-- /URETILMIS:{name} -->)", re.S)
        if not pattern.search(doc):
            raise SystemExit(f"{DOC.name} icinde '{name}' blogu yok")
        table = BLOCKS[name](regmap, raw)
        doc = pattern.sub(lambda m: m[1] + table + "\n" + m[2], doc)
    return doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="dokuman veya CSV guncel degilse 1 ile cik")
    args = parser.parse_args(argv)

    regmap = load_map(CONTRACT)
    raw = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    current = DOC.read_bytes().decode("utf-8")
    updated = render(current, regmap, raw)
    table_csv = csv_bytes(register_rows(regmap))
    if args.check:
        stale = [path for path, fresh in ((DOC, updated.encode("utf-8")), (CSV_PATH, table_csv))
                 if not path.exists() or path.read_bytes() != fresh]
        if stale:
            print("guncel degil:", ", ".join(str(p.relative_to(ROOT)) for p in stale), "-> python scripts/gen_modbus_doc.py")
            return 1
        print("guncel")
        return 0
    DOC.write_bytes(updated.encode("utf-8"))
    CSV_PATH.write_bytes(table_csv)
    print(f"yenilendi: {DOC.relative_to(ROOT)} + {CSV_PATH.name} (harita v{regmap.version})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
