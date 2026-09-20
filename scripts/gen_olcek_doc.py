#!/usr/bin/env python3
"""docs/09-olceklenebilirlik.md icindeki KANIT DOSYALI tablolari uretir.

    python scripts/gen_olcek_doc.py            # tablolari yeniler
    python scripts/gen_olcek_doc.py --check    # guncel degilse 1 ile cikar (PR oncesi)

NEDEN VAR (20 Eylul):
    docs/12 bir betikle uretiliyor ve klonlayan herkes `validate.py` ile ayni
    sayiyi geri alabiliyor. docs/09 ayni muameleyi GORMEMISTI: icindeki her yuk
    olcumu ELLE yazilmisti ve `loadtest/results/` .gitignore ile tamamen disarida
    oldugu icin klonda tek bir kanit dosyasi yoktu. Yani depoyu klonlayan biri
    docs/09'daki hicbir sayiyi dogrulayamiyordu.

    Bu betik o bosluğu kapatir: tablolar artik `loadtest/results/` altinda
    COMMIT'LI JSON eserlerinden uretilir. Yeni bir kosum yapilip eseri
    commit'lenince tablo kendiliginden buyur; eser silinirse satir kaybolur ve
    --check kirmizi yanar.

SINIR — BUNU SOYLEMEK ZORUNDAYIZ:
    docs/09 §4.1'deki ELLE yazilmis tarihsel tablo (100 / 1.000 / 3.000 / 5.000 /
    10.000 pano) bu betikle URETILMEZ, cunku o kosumlarin eserleri hicbir zaman
    surum kontrolune alinmamisti ve bugun geri uretilemezler. O tablo kendi
    basliginda kanitsiz oldugunu SOYLER. Asagidaki uretilmis tablo yalnizca
    eseri klonda DURAN kosumlari listeler. Iki tabloyu birlestirmek, kanitli ile
    kanitsizi ayirt edilemez hale getirirdi.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "09-olceklenebilirlik.md"
RESULTS = ROOT / "loadtest" / "results"


def _sayi(deger: float | int | None, basamak: int = 1) -> str:
    """Turkce ondalik ayirici ve binlik nokta — dokumanin geri kalaniyla ayni."""
    if deger is None:
        return "—"
    if isinstance(deger, int) or float(deger).is_integer():
        return f"{int(deger):,}".replace(",", ".")
    return f"{float(deger):.{basamak}f}".replace(".", ",")


def filo_kosumlari() -> list[dict]:
    """loadtest/fleet.py ozet eserleri: <run_id>-<N>p.json."""
    kosumlar = []
    for yol in sorted(RESULTS.glob("*p.json")):
        veri = json.loads(yol.read_text(encoding="utf-8"))
        if "publish" not in veri or "ingest" not in veri:
            continue  # veri-butcesi eseri; asagidaki blokta islenir
        veri["_dosya"] = yol.name
        kosumlar.append(veri)
    return kosumlar


def filo_tablosu() -> str:
    kosumlar = filo_kosumlari()
    satirlar = [
        "| Filo | Nokta | Süre | Mesaj | Alım p50 / p95 / maks. | Görünme p50 / p95 / maks. | Red / düş / hata | Kanıt dosyası |",
        "|---|---|---|---|---|---|---|---|",
    ]
    if not kosumlar:
        satirlar.append(
            "| — | — | — | — | — | — | — | **Hiç kanıt dosyası commit'li değil** |"
        )
        return "\n".join(satirlar)
    for k in sorted(kosumlar, key=lambda x: (x["config"]["panels"], x["config"]["points"])):
        c, g, a = k["config"], k["ingest"], k["ingest"]
        al = g["receive_latency_ms"]
        gor = g["visible_latency_ms"]
        satirlar.append(
            f"| {_sayi(c['panels'])} | {c['points']} | {_sayi(c['duration_s'])} s "
            f"| {_sayi(k['publish']['sent'])} "
            f"| {_sayi(al['p50'])} / {_sayi(al['p95'])} / {_sayi(al['max'])} ms "
            f"| {_sayi(gor['p50'])} / {_sayi(gor['p95'])} / {_sayi(gor['max'])} ms "
            f"| {a['rejected']} / {a['dropped']} / {a['write_errors']} "
            f"| [`{k['_dosya']}`](../loadtest/results/{k['_dosya']}) |"
        )
    return "\n".join(satirlar)


def butce_tablosu() -> str:
    satirlar = [
        "| Kanıt dosyası | Pencere | Pano | Nokta | Politika | Mesaj | Bastırma | Pano başına aylık |",
        "|---|---|---|---|---|---|---|---|",
    ]
    dosyalar = sorted(RESULTS.glob("veri-butcesi-*.json"))
    if not dosyalar:
        satirlar.append("| **Hiç kanıt dosyası commit'li değil** | — | — | — | — | — | — | — |")
        return "\n".join(satirlar)
    for yol in dosyalar:
        veri = json.loads(yol.read_text(encoding="utf-8"))
        n = veri["normal_rejim"]
        for i, p in enumerate(n["politikalar"]):
            satirlar.append(
                f"| {f'[`{yol.name}`](../loadtest/results/{yol.name})' if i == 0 else '↳'} "
                f"| {_sayi(n['olcum_penceresi_saat'])} sa | {n['panolar']} | {n['nokta_sayisi']} "
                f"| `{p['ad']}` | {_sayi(p['mesaj'])} "
                f"| %{_sayi(round(p['bastirilan_oran'] * 100, 1))} "
                f"| {_sayi(p['pano_basina_aylik_mb'])} MB |"
            )
    return "\n".join(satirlar)


def render(doc: str) -> str:
    bloklar = {"kanitli-kosumlar": filo_tablosu(), "veri-butcesi": butce_tablosu()}
    for ad, tablo in bloklar.items():
        desen = re.compile(rf"(<!-- URETILMIS:{ad} -->\n)(?:.*?\n)?(<!-- /URETILMIS:{ad} -->)", re.S)
        if not desen.search(doc):
            raise SystemExit(f"{DOC.name} icinde '{ad}' blogu yok")
        doc = desen.sub(lambda m: m[1] + tablo + "\n" + m[2], doc)
    return doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="dokuman guncel degilse 1 ile cik")
    args = parser.parse_args(argv)

    mevcut = DOC.read_text(encoding="utf-8")
    yeni = render(mevcut)
    if args.check:
        if yeni != mevcut:
            print(f"{DOC.relative_to(ROOT)} guncel degil: python scripts/gen_olcek_doc.py")
            return 1
        print("guncel")
        return 0
    DOC.write_bytes(yeni.encode("utf-8"))
    n = len(filo_kosumlari())
    print(f"yenilendi: {DOC.relative_to(ROOT)} ({n} filo kosumu + veri butcesi eserleri)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
