#!/usr/bin/env python3
"""Tazminat maruziyeti hesaplayicisi (docs/10 §5, GELISTIRME-BACKLOGU F-05).

Iki soruyu ayri ayri cevaplar ve hicbirinde kendi sayisini uydurmaz:

  1. MARUZIYET: "bu pano su kadar kesilirse, EPDK Kalite Yonetmeligi'nin sure (OTMSURE) ve sayi (OTMSAYI)
     kalemlerine gore ne kadar tazminat DOGAR?" Yonetmeligin esik/katsayilari, dagitim bedeli ve ortalama
     talep bu depoda YOKTUR; disaridan verilir, verilmezse hesap "veri yok" der.
  2. BOM FARKI: mevcut enerji analizoru (MPR-53CS) ve ark korumasi (TVOC-2) sensor olarak okundugu icin
     EKLENMEYEN kalemler. Kalem ve adetler contracts/modbus-map.yaml'dan, bunun yerine odenen arayuzun
     fiyati hardware/pano-beyni/bom.csv'den okunur. Kacinilan kalemlerin birim fiyati depoda yoktur.

"Su kadar ariza onledik" CIKTISI YOKTUR: onlenen ariza bu teslimde olculemez, iddia edilmez (GK10).

    backend/.venv/Scripts/python scripts/tazminat_maruziyeti.py --help
    backend/.venv/Scripts/python scripts/tazminat_maruziyeti.py \
        --pano ADM-00001 --abone <n> --kesinti-saat <saat> --esik-saat <saat> \
        --ortalama-talep-kw <kW> --dagitim-bedeli <para/kWh> \
        --kesinti-sayisi <n> --esik-sayi <n> --kesinti-basi-tazminat <para>
    backend/.venv/Scripts/python scripts/tazminat_maruziyeti.py --yalniz bom --at-fiyat <USD> --ark-dedektor-fiyat <USD>

Parametre girilmezse (ornegin hic argumansiz) hicbir sayi uretilmez, eksikler "veri yok" olarak yazilir
ve betik 1 ile cikar.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.scada.map_loader import load_map  # noqa: E402

MAP = ROOT / "contracts" / "modbus-map.yaml"
BOM = ROOT / "hardware" / "pano-beyni" / "bom.csv"
NO_DATA = "veri yok"

# Sure ve sayi kalemleri ayri hesaplanir: biri icin veri varken digeri icin olmayabilir.
DURATION_ARGS = ("abone", "kesinti_saat", "esik_saat", "ortalama_talep_kw", "dagitim_bedeli")
COUNT_ARGS = ("abone", "kesinti_sayisi", "esik_sayi", "kesinti_basi_tazminat")

# Mevcut cihazdan okunan kanal gruplari -> o yuzden BOM'a eklenmeyen kalem. Adet haritadan sayilir.
AVOIDED_ITEMS = (
    ("Akim trafosu (faz + notr)", "electrical_mirror", r"i_(l\d|n)_a", "at_fiyat"),
    ("Gerilim olcum girisi", "electrical_mirror", r"u_l\d_v", "gerilim_fiyat"),
    ("Ark dedektoru", "arc_mirror", r"sensor_status_x\d", "ark_dedektor_fiyat"),
    ("Ark koruma merkez unitesi", "arc_mirror", r"system_state", "ark_unite_fiyat"),
)
PAID_PART = "RS485"  # mevcut cihazlari okumak icin BOM'da gercekten odenen arayuz (master portu)
PAID_COUNT = 1  # BOM'daki 2 adedin biri SCADA slave portu; yeniden kullanimin bedeli master porttur


# ------------------------------------------------------------------ maruziyet
def exposure(
    abone: int, kesinti_saat: float, esik_saat: float, ortalama_talep_kw: float, dagitim_bedeli: float,
    kesinti_sayisi: int, esik_sayi: int, kesinti_basi_tazminat: float,
) -> dict[str, float]:
    """Esigi asan sure ve sayi uzerinden dogan tazminat. Birim: dagitim bedeli hangi para biriminde ise o."""
    asilan_saat = max(0.0, kesinti_saat - esik_saat)
    asilan_sayi = max(0, kesinti_sayisi - esik_sayi)
    sure = abone * ortalama_talep_kw * dagitim_bedeli * asilan_saat
    sayi = abone * asilan_sayi * kesinti_basi_tazminat
    return {"asilan_saat": asilan_saat, "asilan_sayi": asilan_sayi, "sure": sure, "sayi": sayi, "toplam": sure + sayi}


def _missing(args: argparse.Namespace, names: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(f"--{name.replace('_', '-')}" for name in names if getattr(args, name) is None)


def _amount(value: float) -> str:
    return f"{value:,.2f}".replace(",", " ")


def _number(value: float) -> str:
    return format(value, "g")


def render_exposure(args: argparse.Namespace) -> tuple[list[str], bool]:
    lines = ["TAZMINAT MARUZIYETI - EPDK Kalite Yonetmeligi, sure (OTMSURE) ve sayi (OTMSAYI) kalemleri",
             f"Pano: {args.pano or NO_DATA}   Para birimi: {args.para_birimi}"]
    missing_duration, missing_count = _missing(args, DURATION_ARGS), _missing(args, COUNT_ARGS)
    if missing_duration and missing_count:
        lines.append(f"  {NO_DATA}: hesap icin gereken parametreler girilmedi ({', '.join(sorted(set(missing_duration + missing_count)))})")
        lines.append("  Yonetmeligin esikleri, dagitim bedeli ve ortalama talep bu depoda yoktur; betik bunlari uydurmaz.")
        return lines, False
    values = exposure(
        args.abone or 0, args.kesinti_saat or 0.0, args.esik_saat or 0.0, args.ortalama_talep_kw or 0.0,
        args.dagitim_bedeli or 0.0, args.kesinti_sayisi or 0, args.esik_sayi or 0, args.kesinti_basi_tazminat or 0.0,
    )
    birim = args.para_birimi
    lines.append("")
    lines.append("  Sure kalemi (OTMSURE)")
    if missing_duration:
        lines.append(f"    {NO_DATA}: {', '.join(missing_duration)}")
    else:
        lines += [
            f"    abone sayisi                    {args.abone}",
            f"    kesinti suresi                  {_number(args.kesinti_saat)} saat",
            f"    yonetmelik esigi                {_number(args.esik_saat)} saat",
            f"    esigi asan sure                 {_number(values['asilan_saat'])} saat",
            f"    abone basina ortalama talep     {_number(args.ortalama_talep_kw)} kW",
            f"    dagitim bedeli                  {_number(args.dagitim_bedeli)} {birim}/kWh",
            f"    OTMSURE = {args.abone} x {_number(args.ortalama_talep_kw)} kW x {_number(args.dagitim_bedeli)} {birim}/kWh"
            f" x {_number(values['asilan_saat'])} saat = {_amount(values['sure'])} {birim}",
        ]
    lines.append("")
    lines.append("  Sayi kalemi (OTMSAYI)")
    if missing_count:
        lines.append(f"    {NO_DATA}: {', '.join(missing_count)}")
    else:
        lines += [
            f"    kesinti sayisi                  {args.kesinti_sayisi}",
            f"    yonetmelik esigi                {args.esik_sayi}",
            f"    esigi asan kesinti              {values['asilan_sayi']}",
            f"    kesinti basina tazminat         {_number(args.kesinti_basi_tazminat)} {birim}/abone",
            f"    OTMSAYI = {args.abone} x {values['asilan_sayi']} x {_number(args.kesinti_basi_tazminat)} {birim}"
            f" = {_amount(values['sayi'])} {birim}",
        ]
    lines.append("")
    if missing_duration or missing_count:
        lines.append(f"  TOPLAM (yalnizca verisi girilen kalemler): {_amount(values['toplam'])} {birim}")
    else:
        lines.append(f"  TOPLAM MARUZIYET: {_amount(values['toplam'])} {birim}")
    lines.append(f"  Okunusu: bu pano {_number(args.kesinti_saat or 0.0)} saat kesilirse, yonetmelige gore bu tutarda tazminat DOGAR.")
    lines.append("  Betik onlenen ariza saymaz: onlenen ariza bu teslimde olculemez (GK10).")
    return lines, True


# ------------------------------------------------------------------ BOM farki
def avoided_items() -> list[dict[str, Any]]:
    """Mevcut cihazdan okundugu icin BOM'a eklenmeyen kalemler; adetler modbus haritasindan sayilir."""
    regmap = load_map(MAP)
    blocks = {block.name: block for block in regmap.blocks}
    items = []
    for label, block_name, pattern, option in AVOIDED_ITEMS:
        block = blocks[block_name]
        count = sum(1 for register in block.registers if re.fullmatch(pattern, register.name.split(".", 1)[1]))
        items.append({"kalem": label, "adet": count, "blok": block_name, "cihaz": block.source or NO_DATA, "secenek": option})
    return items


def paid_interface() -> dict[str, Any]:
    """Mevcut cihazlari okumak icin BOM'da gercekten odenen kalem (izoleli RS485 arayuzu)."""
    with BOM.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if PAID_PART in row["parca"]:
                return {"parca": row["parca"], "bom_adet": int(row["adet_panobasina"]), "adet": PAID_COUNT,
                        "adet1": float(row["birim_fiyat_usd_adet1"]), "adet1000": float(row["birim_fiyat_usd_adet1000"])}
    raise SystemExit(f"{BOM.name} icinde '{PAID_PART}' kalemi yok")


def render_bom(args: argparse.Namespace) -> list[str]:
    paid = paid_interface()
    lines = ["BOM FARKI - mevcut cihazlar sensor olarak okundugu icin EKLENMEYEN kalemler",
             "Kaynak: contracts/modbus-map.yaml (hangi kanal hangi cihazdan okunuyor) + hardware/pano-beyni/bom.csv",
             "",
             f"  {'Kalem':<34}{'Adet':>5}  {'Okundugu cihaz':<14}{'Birim fiyat':>14}{'Tutar':>14}"]
    total, complete = 0.0, True
    for item in avoided_items():
        price = getattr(args, item["secenek"])
        if price is None:
            complete = False
            price_text, amount_text = NO_DATA, NO_DATA
        else:
            amount = item["adet"] * price
            total += amount
            price_text, amount_text = f"{_number(price)} USD", f"{_amount(amount)} USD"
        lines.append(f"  {item['kalem']:<34}{item['adet']:>5}  {item['cihaz']:<14}{price_text:>14}{amount_text:>14}")
    lines.append(f"  {'Ek kablaj ve isciligi':<34}{'-':>5}  {'-':<14}{NO_DATA:>14}{NO_DATA:>14}")
    lines.append("    (kablo boyu ve iscilik depoda kayitli degil: adet olarak bile sayilamadi)")
    lines.append("")
    lines.append(f"  Kacinilan toplam: {_amount(total) + ' USD' if complete else NO_DATA}"
                 f"{'' if complete else ' (kacinilan kalemlerin birim fiyati depoda yok; --at-fiyat vb. ile girilir)'}")
    lines.append(f"  Bunun yerine odenen (bom.csv): {paid['parca']} x{paid['adet']} = {_number(paid['adet1'])} USD (adet 1)"
                 f" / {_number(paid['adet1000'])} USD (adet 1000)")
    lines.append(f"    BOM'da {paid['bom_adet']} adet var; ikincisi SCADA ag gecidinin slave portudur, yeniden kullanimin bedeli degildir.")
    if complete:
        lines.append(f"  Net fark: {_amount(total - paid['adet1'] * paid['adet'])} USD (adet 1) /"
                     f" {_amount(total - paid['adet1000'] * paid['adet'])} USD (adet 1000)")
    else:
        lines.append(f"  Net fark: {NO_DATA}")
    lines.append("  Not: ark korumasina yazma yolu yoktur (GK6); TVOC-2 yalnizca okunur.")
    return lines


# ------------------------------------------------------------------ CLI
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pano", help="rapora yazilacak pano kimligi")
    parser.add_argument("--para-birimi", default="TL", help="tazminat kaleminin para birimi (varsayilan TL)")
    parser.add_argument("--abone", type=int, help="panonun besledigi kullanici sayisi")
    parser.add_argument("--kesinti-saat", type=float, help="degerlendirme donemindeki toplam kesinti suresi (saat)")
    parser.add_argument("--esik-saat", type=float, help="yonetmeligin ilgili kullanici grubu icin sure esigi (saat)")
    parser.add_argument("--ortalama-talep-kw", type=float, help="abone basina ortalama talep (kW)")
    parser.add_argument("--dagitim-bedeli", type=float, help="dagitim bedeli birim fiyati (para/kWh)")
    parser.add_argument("--kesinti-sayisi", type=int, help="degerlendirme donemindeki kesinti sayisi")
    parser.add_argument("--esik-sayi", type=int, help="yonetmeligin kesinti sayisi esigi")
    parser.add_argument("--kesinti-basi-tazminat", type=float, help="esigi asan her kesinti icin abone basina tazminat")
    parser.add_argument("--at-fiyat", type=float, help="eklenmeyen akim trafosunun birim fiyati (USD)")
    parser.add_argument("--gerilim-fiyat", type=float, help="eklenmeyen gerilim olcum girisinin birim fiyati (USD)")
    parser.add_argument("--ark-dedektor-fiyat", type=float, help="eklenmeyen ark dedektorunun birim fiyati (USD)")
    parser.add_argument("--ark-unite-fiyat", type=float, help="eklenmeyen ark koruma merkez unitesinin fiyati (USD)")
    parser.add_argument("--yalniz", choices=("maruziyet", "bom"), help="yalnizca bir bolumu yaz")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    lines, computed = [], True
    if args.yalniz != "bom":
        block, computed = render_exposure(args)
        lines += block
    if args.yalniz != "maruziyet":
        lines += ([""] if lines else []) + render_bom(args)
    print("\n".join(lines))
    return 0 if computed else 1


if __name__ == "__main__":
    sys.exit(main())
