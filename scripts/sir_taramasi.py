#!/usr/bin/env python3
"""Ozel anahtar ve sertifika sizintisi taramasi (F-27, Kisi B).

    python scripts/sir_taramasi.py             # izlenen butun dosyalari tarar
    python scripts/sir_taramasi.py --staged    # yalnizca hazirlanmis (staged) degisiklikler

Cikis kodu: 0 temiz, 1 sizinti bulundu, 2 git calistirilamadi.

NEDEN VAR: F-27 depoya bir yerel sertifika otoritesi sokar. PLAN.md GK9 sertifika ve
anahtarin commit'lenmesini yasaklar ve sizan bir dosyayi gecmisten temizlemek
`filter-repo` + force-push demektir — yarisma teslimi sirasinda yapilacak en son sey.
Depoda CI ve pre-commit kancasi YOKTUR (`.git/hooks` tamami `.sample`) ve kancalar
klonla gelmez; bu yuzden asil kilit backend/tests/test_sir_sizintisi.py icindeki
pytest testidir, bu betik de onun mantigini tasir.

IKI YONLU TARAR:
  1. `.gitignore` gercekten tutuyor mu (ignore sozlesmesi kilidi) — bu, dosyayi
     dogru uzantiyla ureten normal durumu kapatir.
  2. IZLENEN dosyalarin ICINDE PEM govdesi var mi — bu, `.gitignore`'un ASLA
     yakalayamayacagi durumu kapatir: bir anahtarin `docs/notlar.md` icine
     yapistirilmasi. Uzanti bazli koruma tek basina yetmez.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#: PEM govde imzalari. Sertifika (CERTIFICATE) sir DEGILDIR ama repoda da isi yoktur:
#: ayri, daha yumusak bir uyari olarak raporlanir.
GIZLI_IMZALAR = (
    "-----BEGIN PRIVATE KEY-----",
    "-----BEGIN RSA PRIVATE KEY-----",
    "-----BEGIN EC PRIVATE KEY-----",
    "-----BEGIN DSA PRIVATE KEY-----",
    "-----BEGIN OPENSSH PRIVATE KEY-----",
    "-----BEGIN ENCRYPTED PRIVATE KEY-----",
    "PuTTY-User-Key-File",
)
SERTIFIKA_IMZASI = "-----BEGIN CERTIFICATE-----"

#: Uretim betiginin urettigi (ya da uretebilecegi) ve GIT DISINDA olmasi gereken yollar.
IGNORE_SOZLESMESI = (
    "deploy/certs/ca.key",
    "deploy/certs/ca.crt",
    "deploy/certs/ca.srl",
    "deploy/certs/broker/broker.key",
    "deploy/certs/broker/broker.crt",
    "deploy/certs/backend/gridup-backend.key",
    "deploy/certs/pano/ADM-00001/ADM-00001.key",
    "deploy/certs/pano/ADM-00001/ADM-00001.crt",
    # openssl'in yan urunleri ve baska bicimler: bugun uretilmiyorlar ama
    # uretilseler de sizmamalilar.
    "deploy/certs/index.txt",
    "deploy/certs/serial",
    "deploy/certs/openssl.cnf",
    "deploy/certs/backend.p12",
    "deploy/certs/newcerts/01.pem",
    "deploy/.env",
)

#: Ilk bu kadar bayt taranir: PEM basligi dosyanin basinda ya da ortasinda olur,
#: ama tum depoyu bastan sona okumak testi yavaslatir.
TARAMA_SINIRI = 64 * 1024


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )


def ignore_disinda_kalanlar(yollar=IGNORE_SOZLESMESI) -> list[str]:
    """`.gitignore` bu yollari tutmuyorsa listeler. Bos liste = sozlesme saglam."""
    disarida = []
    for yol in yollar:
        if git("check-ignore", "-q", yol).returncode != 0:
            disarida.append(yol)
    return disarida


def izlenen_dosyalar(staged: bool) -> list[str]:
    komut = ("diff", "--cached", "--name-only", "--diff-filter=ACM") if staged else ("ls-files",)
    sonuc = git(*komut)
    if sonuc.returncode != 0:
        raise RuntimeError(sonuc.stderr.strip() or "git calistirilamadi")
    return [satir for satir in sonuc.stdout.splitlines() if satir.strip()]


def govdede_pem_arayanlar(yollar: list[str]) -> tuple[list[tuple[str, str]], list[str]]:
    """IZLENEN dosyalarda PEM govdesi arar. Donus: (anahtarlar, sertifikalar)."""
    anahtarlar: list[tuple[str, str]] = []
    sertifikalar: list[str] = []
    for yol in yollar:
        tam = REPO_ROOT / yol
        try:
            if not tam.is_file():
                continue
            with tam.open("rb") as dosya:
                ham = dosya.read(TARAMA_SINIRI)
        except OSError:
            continue
        metin = ham.decode("utf-8", errors="replace")
        for imza in GIZLI_IMZALAR:
            if imza in metin:
                anahtarlar.append((yol, imza))
                break
        else:
            if SERTIFIKA_IMZASI in metin:
                sertifikalar.append(yol)
    return anahtarlar, sertifikalar


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--staged", action="store_true", help="yalnizca hazirlanmis degisiklikleri tara")
    parser.add_argument("--sessiz", action="store_true", help="yalnizca cikis kodu")
    args = parser.parse_args(argv)
    say = (lambda *a: None) if args.sessiz else print

    try:
        yollar = izlenen_dosyalar(args.staged)
    except RuntimeError as exc:
        print(f"git calistirilamadi: {exc}", file=sys.stderr)
        return 2

    kaldi = 0
    disarida = ignore_disinda_kalanlar()
    if disarida:
        kaldi += len(disarida)
        print("IGNORE SOZLESMESI BOZULMUS — bu yollar git disinda DEGIL:", file=sys.stderr)
        for yol in disarida:
            print(f"  {yol}", file=sys.stderr)
        print("  Once deploy/certs/.gitignore ve kok .gitignore'a bakin.", file=sys.stderr)

    anahtarlar, sertifikalar = govdede_pem_arayanlar(yollar)
    if anahtarlar:
        kaldi += len(anahtarlar)
        print("OZEL ANAHTAR GOVDESI IZLENEN DOSYADA:", file=sys.stderr)
        for yol, imza in anahtarlar:
            print(f"  {yol}  ({imza})", file=sys.stderr)
    if sertifikalar:
        kaldi += len(sertifikalar)
        print("SERTIFIKA GOVDESI IZLENEN DOSYADA (sir degil ama repoda durmamali):", file=sys.stderr)
        for yol in sertifikalar:
            print(f"  {yol}", file=sys.stderr)

    if kaldi:
        print(f"\n{kaldi} bulgu. Sizan materyal `bash scripts/sertifika-uret.sh` ile "
              "YENILENEBILIR: yerel CA atilabilir, sizan anahtarin degeri sifirlanir.", file=sys.stderr)
        return 1

    say(f"temiz — {len(yollar)} izlenen dosya tarandi, {len(IGNORE_SOZLESMESI)} ignore kurali dogrulandi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
