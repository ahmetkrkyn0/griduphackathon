"""Modbus harita basligi ureteci (TA3, Kisi A).

contracts/modbus-map.yaml -> firmware/core/modbus_map_generated.h

Neden uretilir: PLAN.md kural 10 "Modbus adresleri sozlesmeden okunur". Gomulu
tarafta calisma aninda YAML okunamaz, ama adresin ELLE YAZILMASI da yasaktir —
cozum, adresleri DERLEME ZAMANINDA sozlesmeden uretmektir. Sozlesme degisirse
baslik yeniden uretilir ve C tarafi otomatik takip eder.

Uretilen dosya elle duzenlenmez; basinda bunu soyleyen bir uyari vardir.

CLI:
    python -m panoalgo.genmap --out firmware/core/modbus_map_generated.h
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from .detect import default_contracts_dir

BANNER = """/* URETILMIS DOSYA — ELLE DUZENLEMEYIN.
 *
 * Kaynak : contracts/modbus-map.yaml (surum {version})
 * Ureten : python -m panoalgo.genmap --out firmware/core/modbus_map_generated.h
 *
 * PLAN.md kural 10: Modbus adresleri sozlesmeden okunur, koda gomulmez. Gomulu
 * tarafta calisma aninda YAML okunamadigi icin adresler DERLEME ZAMANINDA buraya
 * uretilir. Sozlesme degisirse bu dosyayi yeniden uretin; elle duzeltmeyin.
 */
#ifndef PANO_MODBUS_MAP_GENERATED_H
#define PANO_MODBUS_MAP_GENERATED_H
"""


def render(contracts_dir: Path | None = None) -> str:
    directory = contracts_dir or default_contracts_dir()
    data = yaml.safe_load((directory / "modbus-map.yaml").read_text(encoding="utf-8"))

    lines = [BANNER.format(version=data.get("version", "?")), ""]
    lines.append(f"#define PANO_MAP_VERSION {data.get('version', 0)}")
    lines.append(f"#define PANO_MAP_WORD_ORDER_HIGH_FIRST {1 if data.get('word_order') == 'high_first' else 0}")
    lines.append("")

    lines.append("/* --- Blok baslangiclari ve uzunluklari ------------------------------------ */")
    blocks = data["blocks"]
    for block in blocks:
        name = block["name"].upper()
        lines.append(f"#define PANO_BLK_{name}_START {block['start']}")
        lines.append(f"#define PANO_BLK_{name}_COUNT {block['count']}")
    lines.append("")

    lines.append("/* --- Blok ici oge ofsetleri ----------------------------------------------- */")
    for block in blocks:
        items = block.get("items")
        if not items:
            continue
        name = block["name"].upper()
        for item in items:
            lines.append(f"#define PANO_REG_{name}_{item['name'].upper()} "
                         f"({block['start']} + {item['offset']})")
    lines.append("")

    conn = next(b for b in blocks if b["name"] == "conn_temp")
    lines.append("/* --- Olcum noktalari (conn_temp.points sirasi; conn_dt ve k_index ayni sira) -- */")
    lines.append(f"#define PANO_POINT_COUNT {len(conn['points'])}")
    for index, point in enumerate(conn["points"]):
        lines.append(f"#define PANO_PT_{point} {index}")
    lines.append("")
    lines.append("/* Nokta adlari, tanilama ciktisi ve test icin. Gomulu tarafta string tasimak")
    lines.append(" * zorunlu degildir; bu tablo yalnizca host ikilisinde kullanilir. */")
    lines.append("#define PANO_POINT_NAMES { \\")
    for point in conn["points"]:
        lines.append(f'    "{point}", \\')
    lines.append("}")
    lines.append("")

    lines.append("/* --- Yazilabilir alan (GK6: yazma YALNIZCA command blogunda) -------------- */")
    writable = [b for b in blocks if b.get("access") == "write"]
    if len(writable) != 1 or writable[0]["name"] != "command":
        raise SystemExit(
            f"GK6 ihlali: yazilabilir blok tam olarak ['command'] olmali, bulunan: "
            f"{[b['name'] for b in writable]}"
        )
    block = writable[0]
    lines.append(f"#define PANO_WRITABLE_START {block['start']}")
    lines.append(f"#define PANO_WRITABLE_END   ({block['start']} + {block['count']} - 1)")

    read_only = [b for b in blocks if b.get("access") == "read_only"]
    lines.append("")
    lines.append("/* Sozlesmede ACIKCA salt okunur isaretlenmis bloklar (ark korumasi aynasi). */")
    for block in read_only:
        name = block["name"].upper()
        lines.append(f"#define PANO_READ_ONLY_{name} 1")

    lines.append("")
    lines.append("/* --- Sentineller ---------------------------------------------------------- */")
    lines.append("/* 65535 = 'bilinmiyor'. '0 saat kaldi' ile AYNI SEY DEGILDIR. */")
    lines.append("#define PANO_UNKNOWN_U16 65535u")
    lines.append("")
    lines.append("#endif /* PANO_MODBUS_MAP_GENERATED_H */")
    return "\n".join(lines) + "\n"


def default_output() -> Path:
    return Path(__file__).resolve().parents[3] / "firmware" / "core" / "modbus_map_generated.h"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Modbus harita basligi ureteci (Kisi A)")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    path = Path(args.out) if args.out else default_output()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(), encoding="utf-8", newline="\n")
    print(f"{path} uretildi ({path.stat().st_size} bayt)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
