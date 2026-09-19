"""Denetim izinde kurcalama kanidi — hash zinciri (F-20).

NE YAPAR
`alarm_journal`'daki her satir, bir oncekinin ozetini icine alarak ozetlenir:

    hash_n = sha256( prev_hash || alarm_id || at || action || state || by_user || note )

Boylece bir satir DEGISTIRILIRSE kendi ozeti tutmaz; bir satir SILINIRSE kendinden
sonraki satirin `prev_hash`'i artik oncekinin ozetine denk gelmez. Ikisi de bagimsiz
bir dogrulayiciyla (`scripts/verify_journal.py`) bulunabilir ve dogrulayici KACINCI
halkada durdugunu soyler.

NEDEN F-19'DAN SONRA GELDI
Zincir yalnizca "kayit DEGISMEDI"yi kanitlar, "kim yapti"yi degil. `by_user` alani
dogrulanmamis serbest metinken kurcalamaya karsi korunan sey de dogrulanmamis bir
metindi. F-19 o alani kimlik belirtecine bagladi; zincir ancak ondan sonra anlamli.

NE YAPMAZ — durust sinirlar, docs/15 §3.3'te de yazili
  1. **Kuyruk kesmeyi goremez.** Zincirin SON satirlari silinirse kalan zincir kendi
     icinde tutarlidir. Bunun karsiligi zincir basini disariya (WORM depo, ayri makine,
     zaman damgasi otoritesi) yayinlamaktir ve bu YAPILMADI.
  2. **Imzali degildir.** Ozet anahtarsizdir (HMAC degil): veritabanina YAZMA yetkisi
     olan biri satiri degistirip zinciri bastan yeniden hesaplayabilir. Bu tasarim
     "sessizce bir satir silen yetkili kullanici"yi hedefler, "zinciri yeniden kuran
     saldirgan"i degil. Anahtarli surum icin anahtarin veritabani disinda durmasi gerekir.
  3. **Geriye donuk uretilemez.** Goc, zinciri o andan baslatir: goc oncesi satirlarin
     `hash` alani NULL kalir ve dogrulayici onlari "zincir oncesi" olarak sayar.
     Eski satirlara hash uretmek, olmayan bir butunluk iddiasi olurdu.

Bu modul SAF'tir: veritabani bilmez, boylece hem PgStore hem bellek ici test deposu
AYNI hesabi kullanir ve ikisi ayrisirsa testler bunu yakalar.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

#: Zincirin ilk halkasinin `prev_hash` degeri. Bos dize DEGIL: "hash yok" (NULL,
#: goc oncesi satir) ile "zincirin basi" ayirt edilebilmeli.
GENESIS = "0" * 64

#: Alanlari ayiran bayt. Kayitlarin icinde gecemeyecek bir ayirici secildi ki
#: ("ab","c") ile ("a","bc") AYNI ozeti uretmesin (uzunluk-kaydirma saldirisi).
_SEP = b"\x1f"


def _field(value: object) -> bytes:
    if value is None:
        # None ile bos dize AYNI seye ozetlenmemeli: birincisi "not yok",
        # ikincisi "operator bos not girdi" demektir.
        return b"\x00"
    if isinstance(value, datetime):
        # Saat dilimi normalize edilir: ayni an, saklandigi ofsete gore farkli
        # ozet uretmemeli (psycopg okurken sunucu saat dilimini uygulayabilir).
        return value.astimezone(timezone.utc).isoformat().encode("utf-8")
    return str(value).encode("utf-8")


def link_hash(
    prev_hash: str,
    *,
    alarm_id: int,
    at: datetime,
    action: str,
    state: str,
    by_user: str | None,
    note: str | None,
) -> str:
    """Bir denetim izi satirinin zincir ozeti (64 karakter, onaltilik).

    `id` ozete GIRMEZ: degeri veritabani atar ve ozet hesaplanirken henuz bilinmiyor.
    Sira zaten `prev_hash` ile zincirlenir; `id` yalnizca okuma sirasini verir.
    """
    digest = hashlib.sha256()
    for value in (prev_hash, alarm_id, at, action, state, by_user, note):
        digest.update(_field(value))
        digest.update(_SEP)
    return digest.hexdigest()


class ChainBreak(Exception):
    """Zincirde ilk kopan halka."""

    def __init__(self, position: int, row_id: int, kind: str, detail: str) -> None:
        super().__init__(f"halka {position} (alarm_journal.id={row_id}): {detail}")
        self.position = position
        self.row_id = row_id
        self.kind = kind  # "degismis" | "kopuk"
        self.detail = detail


def verify(rows) -> int:
    """Satirlari sirayla dogrular; dogrulanan halka sayisini doner.

    `rows`, `id` sirasina gore dizilmis kayitlardir ve her biri su alanlari tasir:
    id, alarm_id, at, action, state, by_user, note, prev_hash, hash.

    `hash` alani None olan satirlar GOC ONCESIDIR: zincire dahil degildirler ve
    sayilmazlar. Ilk hash'li satirdan sonra gelen bir hash'siz satir ise kurcalama
    belirtisidir (zincir baslamis, sonra kesilmis) ve hata olarak bildirilir.
    """
    prev = GENESIS
    checked = 0
    started = False

    for position, row in enumerate(rows, start=1):
        if row["hash"] is None:
            if started:
                raise ChainBreak(
                    position, row["id"], "kopuk",
                    "zincir baslamisken hash'siz satir bulundu (araya satir eklenmis olabilir)",
                )
            continue  # goc oncesi satir

        if not started:
            started = True
            prev = row["prev_hash"] or GENESIS
        elif row["prev_hash"] != prev:
            raise ChainBreak(
                position, row["id"], "kopuk",
                f"prev_hash oncekinin hash'ine denk gelmiyor "
                f"(beklenen {prev[:12]}…, bulunan {(row['prev_hash'] or 'NULL')[:12]}…) "
                f"— arada bir satir SILINMIS olabilir",
            )

        expected = link_hash(
            row["prev_hash"] or GENESIS,
            alarm_id=row["alarm_id"],
            at=row["at"],
            action=row["action"],
            state=row["state"],
            by_user=row["by_user"],
            note=row["note"],
        )
        if expected != row["hash"]:
            raise ChainBreak(
                position, row["id"], "degismis",
                f"satirin icerigi ozetine uymuyor (beklenen {expected[:12]}…, "
                f"bulunan {row['hash'][:12]}…) — satir DEGISTIRILMIS",
            )

        prev = row["hash"]
        checked += 1

    return checked
