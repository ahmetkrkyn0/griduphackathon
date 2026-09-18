#!/usr/bin/env python3
"""Denetim izi hash zincirini BAGIMSIZ olarak dogrular (F-20, Kisi B).

    python scripts/verify_journal.py                       # DB_DSN / TEST_DB_DSN ortamdan
    python scripts/verify_journal.py --dsn postgresql://...
    python scripts/verify_journal.py --quiet               # yalnizca cikis kodu

Cikis kodu: 0 zincir saglam, 1 zincir kopuk, 2 baglanti/kullanim hatasi.

NEDEN AYRI BIR BETIK: dogrulama, kaydi YAZAN servisin icinden yapilirsa "kendi kendini
onaylayan" bir kanit olurdu. Bu betik backend'i calistirmaz, yalnizca veritabanini okur
ve ozeti backend/app/journal_chain.py'deki AYNI saf fonksiyonla yeniden hesaplar.

NE KANITLAR: bir satirin icerigi degistirildiyse veya aradan bir satir silindiyse,
zincir o noktada kopar ve asagida KACINCI halkada koptugu yazar.

NE KANITLAMAZ (docs/15 §3.3 ve backend/app/journal_chain.py basligi):
  * Kuyruk kesme: zincirin SON satirlari silinirse kalan zincir kendi icinde tutarlidir.
  * Ozet anahtarsizdir (HMAC degil): yazma yetkisi olan biri satiri degistirip zinciri
    bastan yeniden hesaplayabilir. Hedef "sessizce bir satir silen yetkili", "zinciri
    yeniden kuran saldirgan" degil.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.journal_chain import ChainBreak, verify  # noqa: E402

_SELECT = (
    "SELECT id, alarm_id, at, action, state, by_user, note, prev_hash, hash "
    "FROM alarm_journal ORDER BY id"
)
_CHAIN_START = "SELECT started_at, from_row_id, note FROM journal_chain_start ORDER BY started_at LIMIT 1"


def load_rows(dsn: str) -> tuple[list[dict], dict | None]:
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        rows = conn.execute(_SELECT).fetchall()
        try:
            start = conn.execute(_CHAIN_START).fetchone()
        except psycopg.Error:
            # Goc uygulanmamis: tablo yok. Zincir de yoktur, asagida sayilarla anlasilir.
            conn.rollback()
            start = None
    return rows, start


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dsn", default=None, help="varsayilan: DB_DSN, yoksa TEST_DB_DSN")
    parser.add_argument("--quiet", action="store_true", help="yalnizca cikis kodu")
    args = parser.parse_args(argv)

    dsn = args.dsn or os.getenv("DB_DSN") or os.getenv("TEST_DB_DSN")
    if not dsn:
        print("DSN yok: --dsn verin ya da DB_DSN / TEST_DB_DSN tanimlayin", file=sys.stderr)
        return 2

    try:
        rows, start = load_rows(dsn)
    except Exception as exc:  # baglanti, yetki, eksik tablo
        print(f"veritabani okunamadi: {exc}", file=sys.stderr)
        return 2

    say = (lambda *a: None) if args.quiet else print

    total = len(rows)
    before_chain = sum(1 for row in rows if row["hash"] is None)

    try:
        checked = verify(rows)
    except ChainBreak as exc:
        # Sessiz kipte bile KIRILMA basilir: cikis kodu 1'in sebebi gorunmeli.
        print(f"ZINCIR KOPUK — {exc}", file=sys.stderr)
        print(f"  tur       : {exc.kind}", file=sys.stderr)
        print(f"  saglam    : {exc.position - 1 - before_chain} halka (bu satirdan oncesi)", file=sys.stderr)
        print(f"  toplam    : {total} denetim izi satiri", file=sys.stderr)
        return 1

    say(f"ZINCIR SAGLAM — {checked} halka dogrulandi")
    if before_chain:
        say(f"  zincir disi: {before_chain} satir (goc oncesi, hash'i bilerek uretilmedi)")
        if start is not None and start["from_row_id"]:
            say(f"  zincir baslangici: alarm_journal.id > {start['from_row_id']} ({start['started_at']:%Y-%m-%d %H:%M})")
    if checked == 0:
        say("  UYARI: dogrulanan halka YOK. Zincir henuz hic satir uretmedi ya da")
        say("         007_journal_chain.sql uygulanmamis olabilir.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
