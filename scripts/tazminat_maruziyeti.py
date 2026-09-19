#!/usr/bin/env python3
"""Tazminat maruziyeti ve geri odeme hesaplayicisi (docs/10 §5-§7, GELISTIRME-BACKLOGU F-05).

Uc soruyu ayri ayri cevaplar ve hicbirinde kendi sayisini uydurmaz:

  1. MARUZIYET: "bu pano su kadar kesilirse, EPDK Kalite Yonetmeligi'nin sure (OTMSURE) ve sayi (OTMSAYI)
     kalemlerine gore ne kadar tazminat DOGAR?" Yonetmeligin esik/katsayilari, dagitim bedeli ve ortalama
     talep bu depoda YOKTUR; disaridan verilir, verilmezse hesap "veri yok" der.
  2. BOM FARKI: mevcut enerji analizoru (MPR-53CS) ve ark korumasi (TVOC-2) sensor olarak okundugu icin
     EKLENMEYEN kalemler. Kalem ve adetler contracts/modbus-map.yaml'dan, bunun yerine odenen arayuzun
     fiyati hardware/pano-beyni/bom.csv'den okunur. Kacinilan kalemlerin birim fiyati depoda yoktur;
     onun yerine BASA BAS esigi basilir — bu esik olculur (odenen arayuzun fiyatindan), tahmin edilmez.
  3. PANO BASINA MALIYET VE GERI ODEME: donanim maliyeti uc bom.csv'nin satir kalemlerinden TOPLANIR
     (olculur). Yillik fayda ise olculmez: P(ariza), ariza basi maliyet ve tespit orani disaridan gelir
     ve ucu de VARSAYIMDIR. Verilmezse geri odeme "veri yok" der.

"Su kadar ariza onledik" CIKTISI YOKTUR: onlenen ariza bu teslimde olculemez, iddia edilmez (GK10).

    backend/.venv/Scripts/python scripts/tazminat_maruziyeti.py --help
    backend/.venv/Scripts/python scripts/tazminat_maruziyeti.py \
        --pano ADM-00001 --abone <n> --kesinti-saat <saat> --esik-saat <saat> \
        --ortalama-talep-kw <kW> --dagitim-bedeli <para/kWh> \
        --kesinti-sayisi <n> --esik-sayi <n> --kesinti-basi-tazminat <para>
    backend/.venv/Scripts/python scripts/tazminat_maruziyeti.py --yalniz bom --at-fiyat <USD> --ark-dedektor-fiyat <USD>
    backend/.venv/Scripts/python scripts/tazminat_maruziyeti.py --yalniz maliyet --dugum-sayisi 7
    backend/.venv/Scripts/python scripts/tazminat_maruziyeti.py --parametreler scripts/roi-ornek-parametreler.yaml --duyarlilik

Parametre girilmezse (ornegin hic argumansiz) hicbir sayi uretilmez, eksikler "veri yok" olarak yazilir.
--parametreler ile okunan dosyadaki her girdi UC SUTUN tasir (deger/kaynak/guven); komut satiri
bayraklari dosyayi ezer.

AD CAKISMASI: bu depoda "duyarlilik" baska bir yerde RECALL anlamina gelir (README "duyarlilik 1,00").
--duyarlilik bayragi PARAMETRE DUYARLILIGIDIR: her girdiyi tek tek +-%50 oynatip sonucun araligini basar.
Tespit duyarliligiyla ilgisi yoktur.

Cikis kodu: 0 = maruziyet hesaplandi, 1 = maruziyet OLCULEMEDI (rapor yine de basilir, eksikler
"veri yok" yazar), 2 = kullanim hatasi (taninmayan parametre, sinir disi dugum sayisi).
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.scada.map_loader import load_map  # noqa: E402

MAP = ROOT / "contracts" / "modbus-map.yaml"
BOM = ROOT / "hardware" / "pano-beyni" / "bom.csv"
NO_DATA = "veri yok"

# Pano basina maliyetin uc kaynagi. Adet sutunu her dosyada baska adlanir; kolon adi burada durur ki
# bir BOM yeniden adlandirildiginda hata sessizce 0 USD'ye degil, KeyError'a dussun.
BOM_FILES = {
    "kontrolcu": (ROOT / "hardware" / "pano-beyni" / "bom.csv", "adet_panobasina"),
    "dugum": (ROOT / "hardware" / "sensor-dugumu" / "bom.csv", "adet_dugumbasina"),
    "pd": (ROOT / "hardware" / "pd-karti" / "bom.csv", "adet_kartbasina"),
}
SCALES = {"adet1": "birim_fiyat_usd_adet1", "adet1000": "birim_fiyat_usd_adet1000"}

# Sozlesmenin conn_temp blogu 25 nokta tanimlar; loadtest/fleet.py:720 4-25 arasina izin verir.
# Bu ikisi dugum sayisinin SINIRLARIDIR, varsayilani degil: betik N'i kendi secmez.
NODE_MIN, NODE_MAX = 4, 25

# --parametreler dosyasindaki guven etiketleri. "isletmeci-doldurur" olan girdinin degeri null OLMALIDIR:
# dolu bir degere bu etiketi vermek, uydurulmus bir sayiyi "isletmeci verdi" diye gecirmenin yoludur.
GUVEN = ("olculdu", "turetildi", "varsayim", "ornek", "isletmeci-doldurur")
GUVEN_BOS = "isletmeci-doldurur"

# Sure ve sayi kalemleri ayri hesaplanir: biri icin veri varken digeri icin olmayabilir.
DURATION_ARGS = ("abone", "kesinti_saat", "esik_saat", "ortalama_talep_kw", "dagitim_bedeli")
COUNT_ARGS = ("abone", "kesinti_sayisi", "esik_sayi", "kesinti_basi_tazminat")

# Geri odemenin PAYDASI. Ucu de varsayimdir; biri bile eksikse geri odeme "veri yok" der.
PAYBACK_ARGS = ("ariza_olasiligi_yil", "ariza_basi_maliyet_usd", "tespit_orani")
# Duyarlilikta oynatilanlar: paydaya ek olarak yapilandirma (N) ve isletme gideri de girer.
SENS_PAYBACK_ARGS = ("dugum_sayisi",) + PAYBACK_ARGS + ("opex_yillik_usd",)

# Mevcut cihazdan okunan kanal gruplari -> o yuzden BOM'a eklenmeyen kalem. Adet haritadan sayilir.
AVOIDED_ITEMS = (
    ("Akim trafosu (faz + notr)", "electrical_mirror", r"i_(l\d|n)_a", "at_fiyat"),
    ("Gerilim olcum girisi", "electrical_mirror", r"u_l\d_v", "gerilim_fiyat"),
    ("Ark dedektoru", "arc_mirror", r"sensor_status_x\d", "ark_dedektor_fiyat"),
    ("Ark koruma merkez unitesi", "arc_mirror", r"system_state", "ark_unite_fiyat"),
)
PAID_PART = "RS485"  # mevcut cihazlari okumak icin BOM'da gercekten odenen arayuz (master portu)
PAID_COUNT = 1  # BOM'daki 2 adedin biri SCADA slave portu; yeniden kullanimin bedeli master porttur


# ------------------------------------------------------------------ parametre dosyasi
def load_params(path: Path) -> dict[str, dict[str, Any]]:
    """--parametreler dosyasini okur ve UC SUTUN kuralini denetler.

    Denetim betigin erdemini korur: "isletmeci-doldurur" etiketli bir girdiye deger yazilirsa
    dosya reddedilir. Aksi halde uydurulmus bir sayi, kaynagi "isletmeci" gosterilerek tabloya girebilirdi.
    """
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    params = data.get("parametreler")
    if not isinstance(params, dict):
        raise SystemExit(f"{path.name}: 'parametreler' sozlugu yok")
    for name, entry in params.items():
        if not isinstance(entry, dict) or set(entry) < {"deger", "kaynak", "guven"}:
            raise SystemExit(f"{path.name}: '{name}' uc sutun tasimali (deger, kaynak, guven)")
        if entry["guven"] not in GUVEN:
            raise SystemExit(f"{path.name}: '{name}' guven etiketi taninmiyor: {entry['guven']!r} (gecerli: {', '.join(GUVEN)})")
        if not str(entry["kaynak"] or "").strip():
            raise SystemExit(f"{path.name}: '{name}' kaynaksiz — her sayinin nereden geldigi yazilmali")
        if entry["guven"] == GUVEN_BOS and entry["deger"] is not None:
            raise SystemExit(f"{path.name}: '{name}' '{GUVEN_BOS}' etiketli ama degeri dolu ({entry['deger']!r})")
        if entry["guven"] != GUVEN_BOS and entry["deger"] is None:
            raise SystemExit(f"{path.name}: '{name}' degeri null ama etiketi '{entry['guven']}' — bos deger '{GUVEN_BOS}' olmali")
    return params


def apply_params(args: argparse.Namespace, params: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Dosyadaki degerleri, KOMUT SATIRINDA VERILMEMIS alanlara yazar (acik olan ortuyu ezer).

    Donen sozluk, her dolan alanin guven etiketidir; rapor bunu degerin yanina basar ki bir sayinin
    olcum mu varsayim mi oldugu tabloyu okurken gorulsun.
    """
    labels: dict[str, str] = {}
    for name, entry in params.items():
        if not hasattr(args, name):
            raise SystemExit(f"parametre dosyasinda taninmayan alan: {name!r}")
        if entry["deger"] is None:
            continue
        if getattr(args, name) is None:  # komut satiri bayragi dosyayi ezer
            setattr(args, name, entry["deger"])
            labels[name] = entry["guven"]
        else:
            labels[name] = "komut satiri"
    return labels


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


def breakeven(items: list[dict[str, Any]], paid: dict[str, Any]) -> dict[str, float]:
    """Kacinilan kalemlerin ORTALAMA birim fiyati bu esigi gectigi an yeniden kullanim kendini oder.

    Esigin tamami OLCULUR: pay odenen arayuzun bom.csv'deki fiyati, payda sozlesmeden sayilan kalem
    adedi. Hicbir tedarikci fiyatina ihtiyac duymaz — bilinmeyen bir sayiyi tahmin etmek yerine,
    okuyucunun kendi bilgisiyle karsilastirabilecegi bir ESIGE cevirir.
    """
    adet = sum(item["adet"] for item in items)
    return {"adet": adet,
            "adet1": paid["adet1"] * paid["adet"] / adet,
            "adet1000": paid["adet1000"] * paid["adet"] / adet}


def render_bom(args: argparse.Namespace) -> list[str]:
    paid = paid_interface()
    lines = ["BOM FARKI - mevcut cihazlar sensor olarak okundugu icin EKLENMEYEN kalemler",
             "Kaynak: contracts/modbus-map.yaml (hangi kanal hangi cihazdan okunuyor) + hardware/pano-beyni/bom.csv",
             "",
             f"  {'Kalem':<34}{'Adet':>5}  {'Okundugu cihaz':<14}{'Birim fiyat':>14}{'Tutar':>14}"]
    items = avoided_items()
    total, complete = 0.0, True
    for item in items:
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
    be = breakeven(items, paid)
    lines.append("")
    lines.append(f"  BASA BAS ESIGI (fiyat gerektirmez, tamami olculur): {be['adet']} kalemin ORTALAMA birim fiyati")
    lines.append(f"    {_number(round(be['adet1'], 2))} USD (adet 1) / {_number(round(be['adet1000'], 2))} USD (adet 1.000)")
    lines.append("    degerini gectigi anda mevcut cihazi okumak kendini oder. Esigin payi odenen arayuzun")
    lines.append("    bom.csv'deki fiyati, paydasi sozlesmeden sayilan kalem adedidir; tedarikci fiyatina ihtiyac yoktur.")
    lines.append("  Not: ark korumasina yazma yolu yoktur (GK6); TVOC-2 yalnizca okunur.")
    return lines


# ------------------------------------------------- pano basina maliyet ve geri odeme
def bom_total(path: Path, qty_column: str, scale: str) -> float:
    """Bir bom.csv'nin SATIR KALEMLERINI toplar (adet x birim fiyat).

    CSV'nin son "Toplam" satirindaki metin OKUNMAZ: o satir elle yazilmistir ve bu depoda bir kez
    satir toplamindan sapmisti (56/37 yazarken gercek 70,73/47,68'di). Kaynak satirlarin kendisidir.
    """
    column = SCALES[scale]
    total = 0.0
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["kategori"] == "Toplam" or not row.get(qty_column):
                continue
            total += float(row[qty_column]) * float(row[column])
    return total


def panel_cost(dugum_sayisi: int | None, pd_karti: bool, scale: str) -> dict[str, Any]:
    """Pano basina donanim maliyeti. Birim fiyatlar OLCULUR, yapilandirma (N, PD) disaridan gelir.

    Kurulum isciligi, SIM/veri aboneligi, montaj malzemesi ve tip test/sertifikasyon BU TOPLAMDA YOKTUR
    (docs/19 §3.1: bu kalemlerin BOM satiri yok, dolayisiyla adet olarak bile sayilamiyorlar).
    """
    kontrolcu = bom_total(*BOM_FILES["kontrolcu"], scale)
    dugum_birim = bom_total(*BOM_FILES["dugum"], scale)
    pd = bom_total(*BOM_FILES["pd"], scale) if pd_karti else 0.0
    dugum_toplam = None if dugum_sayisi is None else dugum_sayisi * dugum_birim
    toplam = None if dugum_toplam is None else kontrolcu + dugum_toplam + pd
    return {"kontrolcu": kontrolcu, "dugum_birim": dugum_birim, "dugum_sayisi": dugum_sayisi,
            "dugum_toplam": dugum_toplam, "pd": pd, "pd_karti": pd_karti, "olcek": scale, "toplam": toplam}


def payback_months(maliyet_usd: float, ariza_olasiligi: float, ariza_basi_usd: float,
                   tespit_orani: float, opex_yillik_usd: float) -> float | None:
    """Basit geri odeme (ay). Fayda tarafi OLCUM DEGILDIR — ucu de varsayimdir, cagiran oyle yazar.

    Net yillik fayda sifir veya negatifse None doner: "hicbir zaman" bir sayiyla gizlenmez.
    """
    brut = ariza_olasiligi * ariza_basi_usd * tespit_orani
    net = brut - opex_yillik_usd
    if net <= 0:
        return None
    return 12.0 * maliyet_usd / net


def _cost_args_missing(args: argparse.Namespace) -> tuple[str, ...]:
    return tuple(f"--{n.replace('_', '-')}" for n in PAYBACK_ARGS if getattr(args, n) is None)


def render_cost(args: argparse.Namespace, labels: dict[str, str]) -> list[str]:
    scale = args.olcek or "adet1000"
    cost = panel_cost(args.dugum_sayisi, bool(args.pd_karti), scale)
    etiket = {"adet1": "adet 1 (prototip)", "adet1000": "adet 1.000"}[scale]
    lines = ["PANO BASINA MALIYET VE GERI ODEME",
             f"Kaynak: uc bom.csv'nin SATIR KALEMLERI (olculur) + yapilandirma (disaridan). Olcek: {etiket}",
             "",
             f"  {'Kalem':<40}{'Adet':>5}{'Birim':>12}{'Tutar':>14}",
             f"  {'Pano Beyni kontrolcu karti':<40}{1:>5}{_number(round(cost['kontrolcu'], 2)) + ' USD':>12}{_amount(cost['kontrolcu']) + ' USD':>14}"]
    if cost["dugum_sayisi"] is None:
        lines.append(f"  {'Sensor dugumu x N':<40}{'?':>5}{_number(round(cost['dugum_birim'], 2)) + ' USD':>12}{NO_DATA:>14}")
    else:
        lines.append(f"  {'Sensor dugumu':<40}{cost['dugum_sayisi']:>5}"
                     f"{_number(round(cost['dugum_birim'], 2)) + ' USD':>12}{_amount(cost['dugum_toplam']) + ' USD':>14}")
    if cost["pd_karti"]:
        lines.append(f"  {'PD karti (yalnizca OG)':<40}{1:>5}{_number(round(cost['pd'], 2)) + ' USD':>12}{_amount(cost['pd']) + ' USD':>14}")
    else:
        lines.append(f"  {'PD karti (yalnizca OG)':<40}{'-':>5}{'-':>12}{'kapsam disi':>14}")
    for kalem in ("Kurulum isciligi", "SIM / veri aboneligi", "Montaj malzemesi (kablo, braket)", "Tip test ve sertifikasyon"):
        lines.append(f"  {kalem:<40}{'?':>5}{NO_DATA:>12}{NO_DATA:>14}")
    lines.append("    (bu dort kalemin BOM satiri yok - docs/19 bolum 3.1; adet olarak bile sayilamadilar)")
    lines.append("")
    if cost["toplam"] is None:
        lines.append(f"  TOPLAM: {NO_DATA} - dugum sayisi girilmedi (--dugum-sayisi).")
        lines.append(f"    Sozlesme (contracts/modbus-map.yaml conn_temp) {NODE_MAX} nokta tanimlar, loadtest varsayilani {NODE_MIN + 3}'dir;")
        lines.append("    betik ikisi arasindan kendi secmez.")
    else:
        lines.append(f"  TOPLAM (olculen kalemler): {_amount(cost['toplam'])} USD/pano")
        pay = 100.0 * (cost["dugum_toplam"] or 0.0) / cost["toplam"]
        lines.append(f"    Bunun %{pay:.1f}'si sensor dugumleridir; kontrolcu karti %{100.0 * cost['kontrolcu'] / cost['toplam']:.1f}.")
    lines.append("")
    missing = _cost_args_missing(args)
    if cost["toplam"] is None or missing:
        eksik = ", ".join(sorted(set(missing + (() if cost["toplam"] is not None else ("--dugum-sayisi",)))))
        lines.append(f"  GERI ODEME: {NO_DATA} - {eksik} girilmedi.")
        lines.append("  Yillik fayda bu depoda OLCULMEZ: P(ariza), ariza basi maliyet ve tespit orani isletmecinin")
        lines.append("  saha istatistigindedir. Betik bunlari uydurmaz.")
        return lines
    opex = args.opex_yillik_usd
    brut = args.ariza_olasiligi_yil * args.ariza_basi_maliyet_usd * args.tespit_orani
    ay = payback_months(cost["toplam"], args.ariza_olasiligi_yil, args.ariza_basi_maliyet_usd,
                        args.tespit_orani, opex or 0.0)
    guven_not = {n: labels.get(n, "komut satiri") for n in SENS_PAYBACK_ARGS}
    lines += [
        "  Yillik fayda (VARSAYIM - olcum degil)",
        f"    P(ariza)/yil                    {_number(args.ariza_olasiligi_yil)}   [{guven_not['ariza_olasiligi_yil']}]",
        f"    ariza basi maliyet              {_number(args.ariza_basi_maliyet_usd)} USD   [{guven_not['ariza_basi_maliyet_usd']}]",
        f"    tespit orani                    {_number(args.tespit_orani)}   [{guven_not['tespit_orani']}]"
        "  (olculen: docs/12 bolum 1 ESLESEN blokta 1,00, UYUMSUZ blokta 0,50'ye kadar)",
        f"    brut yillik fayda = {_number(args.ariza_olasiligi_yil)} x {_number(args.ariza_basi_maliyet_usd)}"
        f" x {_number(args.tespit_orani)} = {_amount(brut)} USD/pano/yil",
    ]
    if opex is None:
        lines.append(f"    yillik OPEX                     {NO_DATA} - hucresel tarife depoda yok (docs/09 bolum 6.1 HACMI olcer: 632 MB/pano/ay)")
        if ay is None:
            # Carpanlardan biri sifir: brut fayda sifirdir. OPEX olmasa bile geri odeme DOGMAZ;
            # burada bir sayi basmak (ornegin "0 ay" ya da "sonsuz") uydurma olurdu.
            lines.append("  GERI ODEME: HICBIR ZAMAN - brut yillik fayda sifir (carpanlardan biri 0).")
            return lines
        lines.append(f"  GERI ODEME (OPEX HARIC): {ay:.1f} ay ({ay / 12:.2f} yil)")
        lines.append("    OPEX girilmedigi icin bu sayi BIR ALT SINIRDIR: isletme gideri eklendikce uzar.")
    else:
        lines.append(f"    yillik OPEX                     {_number(opex)} USD/pano/yil   [{guven_not['opex_yillik_usd']}]")
        if ay is None:
            lines.append("  GERI ODEME: HICBIR ZAMAN — yillik OPEX brut faydayi asiyor, net fayda negatif.")
            return lines
        lines.append(f"  GERI ODEME (OPEX DAHIL): {ay:.1f} ay ({ay / 12:.2f} yil)")
    lines.append("  Bu sayinin PAYI olculur (BOM satir kalemleri), PAYDASI varsayimdir. --duyarlilik hangi")
    lines.append("  girdinin sonucu belirledigini olcer.")
    return lines


# ------------------------------------------------------------------ duyarlilik
# Tam sayili ve sinirli girdiler: duz +-%50 oynatma bunlari kirar. 7 dugumun -%50'si 3,5 dugumdur;
# ne 3,5 dugum vardir ne de betik 4'un altini kabul eder (main() SystemExit atar). Oynatilan deger
# once YUVARLANIR, sonra sozlesmenin sinirlarina KIRPILIR ve tabloda hangi degerin kullanildigi
# yazilir — aksi halde rapor, betigin kendi gecersiz saydigi bir yapilandirmadan sayi turetirdi.
INT_ARGS = ("abone", "kesinti_sayisi", "esik_sayi", "dugum_sayisi")
BOUNDS = {"dugum_sayisi": (NODE_MIN, NODE_MAX)}


def perturbed_value(name: str, value: float, factor: float) -> float:
    out = value * factor
    if name in INT_ARGS:
        # round() BANKACI YUVARLAMASI yapar: round(3.5)=4 ama round(10.5)=10. Ayni tabloda 7'nin
        # -%50'si yukari, +%50'si asagi yuvarlanirdi ve okuyan bunu gerekce olmadan gorurdu.
        # Yariyi hep yukari alinca aralik simetrik kalir: 3,5 -> 4 ve 10,5 -> 11.
        out = math.floor(out + 0.5)
    low, high = BOUNDS.get(name, (None, None))
    if low is not None:
        out = min(max(out, low), high)
    return out


def _perturb(args: argparse.Namespace, name: str, factor: float) -> argparse.Namespace:
    clone = argparse.Namespace(**vars(args))
    setattr(clone, name, perturbed_value(name, getattr(args, name), factor))
    return clone


def _exposure_total(args: argparse.Namespace) -> float:
    """Eksik kalem 0 sayilir — render_exposure ile ayni davranis: verisi olmayan kalem toplama girmez."""
    return exposure(args.abone or 0, args.kesinti_saat or 0.0, args.esik_saat or 0.0, args.ortalama_talep_kw or 0.0,
                    args.dagitim_bedeli or 0.0, args.kesinti_sayisi or 0, args.esik_sayi or 0,
                    args.kesinti_basi_tazminat or 0.0)["toplam"]


def _payback_of(args: argparse.Namespace) -> float | None:
    cost = panel_cost(args.dugum_sayisi, bool(args.pd_karti), args.olcek or "adet1000")
    return payback_months(cost["toplam"], args.ariza_olasiligi_yil, args.ariza_basi_maliyet_usd,
                          args.tespit_orani, args.opex_yillik_usd or 0.0)


def sensitivity(args: argparse.Namespace, names: tuple[str, ...], metric, span: float = 0.5) -> dict[str, Any]:
    """Her girdiyi TEK TEK +-%50 oynatir (digerleri sabit) ve metrigin araligini olcer.

    Tek tek oynatmak (OAT) bilincli bir secimdir: birlesik tarama daha genis bir aralik verirdi ama
    hangi girdinin sorumlu oldugunu kaybederdi. Buradaki soru "sonuc ne kadar kotulesebilir" degil,
    "SONUCU HANGI VARSAYIM BELIRLIYOR" sorusudur.
    """
    taban = metric(args)
    rows = []
    for name in names:
        value = getattr(args, name)
        if value is None or not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        alt, ust = perturbed_value(name, value, 1.0 - span), perturbed_value(name, value, 1.0 + span)
        low = metric(_perturb(args, name, 1.0 - span))
        high = metric(_perturb(args, name, 1.0 + span))
        finite = [v for v in (low, high) if v is not None]
        genislik = None if len(finite) < 2 or taban in (None, 0) else abs(high - low) / taban
        # Kirpildiysa gercek aralik +-%50 degildir; rapor bunu yazar, yoksa kaldirac yaniltir.
        kirpildi = (alt, ust) != (value * (1.0 - span), value * (1.0 + span))
        rows.append({"girdi": name, "deger": value, "dusuk": low, "yuksek": high, "genislik": genislik,
                     "alt_deger": alt, "ust_deger": ust, "kirpildi": kirpildi})
    rows.sort(key=lambda r: (r["genislik"] is None, -(r["genislik"] or 0.0)))
    return {"taban": taban, "satirlar": rows}


def _fmt(value: float | None, birim: str) -> str:
    return NO_DATA if value is None else f"{_amount(value)} {birim}".strip()


def render_sensitivity(args: argparse.Namespace, labels: dict[str, str]) -> list[str]:
    lines = ["DUYARLILIK - her girdi TEK TEK +-%50 oynatildi, digerleri sabit tutuldu",
             "Soru: 'sonuc ne kadar kotulesir' degil, 'SONUCU HANGI GIRDI BELIRLIYOR'."]
    basildi = False
    for baslik, names, metric, birim, hazir in (
        ("Maruziyet toplami", DURATION_ARGS + COUNT_ARGS[1:], _exposure_total, args.para_birimi,
         not _missing(args, DURATION_ARGS) or not _missing(args, COUNT_ARGS)),
        ("Geri odeme (ay)", SENS_PAYBACK_ARGS, _payback_of, "",
         args.dugum_sayisi is not None and not _cost_args_missing(args)),
    ):
        lines.append("")
        if not hazir:
            lines.append(f"  {baslik}: {NO_DATA} - bu metrigin girdileri tam degil, oynatilacak bir sey yok.")
            continue
        basildi = True
        table = sensitivity(args, tuple(n for n in names if getattr(args, n) is not None), metric)
        lines += [f"  {baslik} - taban: {_fmt(table['taban'], birim)}", "",
                  f"    {'Girdi':<26}{'Deger':>12}{'-%50':>16}{'+%50':>16}{'Kaldirac':>10}  Guven"]
        for row in table["satirlar"]:
            kaldirac = NO_DATA if row["genislik"] is None else f"{row['genislik']:.2f}x"
            guven = labels.get(row["girdi"], "komut satiri")
            if row["kirpildi"]:
                guven += f"  [oynatilan deger: {_number(row['alt_deger'])} / {_number(row['ust_deger'])}]"
            lines.append(f"    {row['girdi']:<26}{_number(row['deger']):>12}{_fmt(row['dusuk'], ''):>16}"
                         f"{_fmt(row['yuksek'], ''):>16}{kaldirac:>10}  {guven}")
        lines.append("")
        lines.append(f"    Kaldirac = |(+%50 sonucu) - (-%50 sonucu)| / taban. Buyuk olan sonucu belirler.")
        # Berabere kalan girdileri TEK TEK saymak sart: carpimsal bir modelde butun carpanlarin kaldiraci
        # ayni cikar ve "sonucu su girdi belirliyor" demek, rastgele birini one cikarmak olurdu.
        spans = [r["genislik"] for r in table["satirlar"] if r["genislik"] is not None]
        if spans:
            tepe = [r["girdi"] for r in table["satirlar"] if r["genislik"] is not None
                    and abs(r["genislik"] - spans[0]) < 1e-9]
            if len(tepe) == len(spans) > 1:
                lines.append(f"    OKUNUSU: butun kaldiraclar ESIT ({spans[0]:.2f}x). Model carpimsaldir; sonucu tek bir")
                lines.append("    girdi degil CARPIMIN KENDISI belirler. Iyilestirilecek yer en zayif kaynakli girdidir.")
            elif len(tepe) > 1:
                lines.append(f"    OKUNUSU: {len(tepe)} girdi BERABERE en cok belirliyor ({spans[0]:.2f}x): {', '.join(tepe)}.")
                lines.append(f"    Carpimsal girdilerin kaldiraci ayni olur; en az etkili girdi "
                             f"'{table['satirlar'][-1]['girdi']}' ({spans[-1]:.2f}x).")
            else:
                lines.append(f"    OKUNUSU: sonucu '{tepe[0]}' belirliyor ({spans[0]:.2f}x), en az etkili girdi "
                             f"'{table['satirlar'][-1]['girdi']}' ({spans[-1]:.2f}x).")
    if args.dugum_sayisi is not None and not _cost_args_missing(args):
        lines += ["", "  Yapilandirma araligi (DUYARLILIK DEGIL, SECIM) - dugum sayisi sozlesmeyle sinirlidir", ""]
        lines.append(f"    {'Dugum sayisi':<26}{'Pano maliyeti':>18}{'Geri odeme':>16}")
        for n in (NODE_MIN, NODE_MIN + 3, NODE_MAX):
            clone = argparse.Namespace(**vars(args))
            clone.dugum_sayisi = n
            cost = panel_cost(n, bool(args.pd_karti), args.olcek or "adet1000")
            ay = _payback_of(clone)
            etiket = {NODE_MIN: " (loadtest alt siniri)", NODE_MIN + 3: " (loadtest varsayilani)", NODE_MAX: " (sozlesmenin tamami)"}[n]
            lines.append(f"    {str(n) + etiket:<26}{_amount(cost['toplam']) + ' USD':>18}{(f'{ay:.1f} ay' if ay else NO_DATA):>16}")
        lines.append("    N bir olcum degil, bir YAPILANDIRMA SECIMIDIR: kac baglanti noktasi izlenecek.")
    if not basildi:
        lines.append("")
        lines.append(f"  {NO_DATA}: oynatilacak girdi yok. --parametreler veya tek tek bayraklarla deger verin.")
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
    parser.add_argument("--dugum-sayisi", type=int, help=f"pano basina sensor dugumu sayisi ({NODE_MIN}-{NODE_MAX}); betik kendi secmez")
    parser.add_argument("--pd-karti", action="store_true", default=None, help="PD kartini maliyete ekle (yalnizca OG)")
    parser.add_argument("--olcek", choices=tuple(SCALES), help="bom.csv fiyat sutunu (varsayilan adet1000)")
    parser.add_argument("--ariza-olasiligi-yil", type=float, help="pano basina yillik ariza olasiligi (VARSAYIM, olcum degil)")
    parser.add_argument("--ariza-basi-maliyet-usd", type=float, help="ariza basina ortalama maliyet (USD, VARSAYIM)")
    parser.add_argument("--tespit-orani", type=float, help="sistemin tespit orani (VARSAYIM; olculen degerler docs/12 §1, iki blok)")
    parser.add_argument("--opex-yillik-usd", type=float, help="pano basina yillik isletme gideri (USD); verilmezse geri odeme OPEX HARIC yazilir")
    parser.add_argument("--parametreler", type=Path, help="uc sutunlu (deger/kaynak/guven) YAML parametre dosyasi")
    parser.add_argument("--duyarlilik", action="store_true",
                        help="her girdiyi tek tek +-%%50 oynat, araligi tablo bas (PARAMETRE duyarliligi; recall degil)")
    parser.add_argument("--yalniz", choices=("maruziyet", "bom", "maliyet"), help="yalnizca bir bolumu yaz")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    labels: dict[str, str] = {}
    if args.parametreler is not None:
        labels = apply_params(args, load_params(args.parametreler))
    if args.dugum_sayisi is not None and not NODE_MIN <= args.dugum_sayisi <= NODE_MAX:
        raise SystemExit(f"--dugum-sayisi {NODE_MIN}-{NODE_MAX} araliginda olmali (sozlesme conn_temp {NODE_MAX} nokta tanimlar)")
    lines, computed = [], True
    if args.yalniz != "bom" and args.yalniz != "maliyet":
        block, computed = render_exposure(args)
        lines += block
    if args.yalniz != "maruziyet" and args.yalniz != "maliyet":
        lines += ([""] if lines else []) + render_bom(args)
    if args.yalniz != "maruziyet" and args.yalniz != "bom":
        lines += ([""] if lines else []) + render_cost(args, labels)
    if args.duyarlilik:
        lines += ([""] if lines else []) + render_sensitivity(args, labels)
    print("\n".join(lines))
    return 0 if computed else 1


if __name__ == "__main__":
    sys.exit(main())
