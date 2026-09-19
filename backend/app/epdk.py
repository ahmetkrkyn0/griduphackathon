"""EPDK Madde 8 kesinti kaydi TASLAGI (F-23).

NE YAPAR
F-22'nin urettigi kesinti olayini, EPDK Kalite Yonetmeligi (RG 29/12/2020, 31349 muk.)
Madde 8/2'nin saydigi alanlarla doldurulmus bir TASLAGA cevirir. Alan listesi backlog
§2.1'de birebir dogrulanmistir:

    numara · kademe · yer (il/ilce ve TEKIL SEBEKE UNSURU KODU) · neden · sinif ·
    baslama/sona erme · sure · etkilenen kullanici sayisi · toplam etkilenme suresi ·
    dagitilmayan enerji

CIKTI TASLAKTIR — ve bu, yanitin yanina ilistirilmis bir uyari degil, YAPININ KENDISIDIR:
her alan bir `durum` tasir (olculen / oneri / elle_doldurulacak) ve alan yanittan HICBIR
ZAMAN DUSURULMEZ. Olcmedigimiz alani cikarmak, "bu alani olcmuyoruz" bilgisini de
kaybettirirdi (panel_health'in null dondurup alani satirda tutmasiyla ayni kural).

ON MADDE, ON BIR ALAN
Mevzuat "baslama/sona erme"yi TEK kalem sayar; biz IKIYE ayirdik cunku ikisinin DURUMU
farklidir — baslama olculuyor (yaklasim olarak), sona erme OLCULMUYOR. Tek alanda
birlestirmek, olculen bir degeri olculmeyenle ayni kefeye koyardi ve taslagin butun anlami
tam o ayrimdadir.

UCU OLCULUYOR, IKISI ONERI, ALTISI ELLE DOLDURULACAK
Olculenler F-21 kunyesinden (yer) ve F-22 bagintisindan (etkilenen kullanici, baslama) gelir.
Baslama bile bir YAKLASIMDIR: panolarin sustugu andir, enerjinin kesildigi anin kendisi
gozlemlenmiyor.

SONA ERME NEDEN YOK — maddenin en onemli durustluk sinirir
Restorasyon ani bu depoda OLCULMUYOR. Elimizdeki tek sey haberlesmenin donusudur ve o da
5 dk histerezislidir; enerji donusu DEGILDIR. Sona erme olmayinca sure, toplam etkilenme
suresi ve dagitilmayan enerji de uretilemez — uretmek, olcmedigimiz bir seyi olcmus gibi
gostermek olurdu.

TAZMINAT HESABINA GIRILMEZ (GK10)
Formul (OTMSURE = SBSURE + (TKSURE - ESURE) x K x DB x OT) parametrelidir ve SBSURE bir
literal tutar degildir. scripts/tazminat_maruziyeti.py zaten var ve parametresiz
calistirildiginda hesap yapmaz, uydurmaz. Bu taslakta tazminat alani YOKTUR.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

OLCULEN = "olculen"
ONERI = "oneri"
ELLE = "elle_doldurulacak"

TASLAK_UYARISI = (
    "TASLAKTIR — resmi bir kesinti kaydi degildir. 'elle_doldurulacak' isaretli alanlar bu "
    "sistemde OLCULMEMEKTEDIR; 'oneri' isaretli alanlar karar degil oneridir ve sorumlu "
    "kisi tarafindan onaylanmalidir."
)


def _alan(ad: str, durum: str, deger: Any = None, aciklama: str = "") -> dict[str, Any]:
    return {"ad": ad, "deger": deger, "durum": durum, "aciklama": aciklama}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _yer(panolar: list[dict]) -> dict[str, Any]:
    """Madde 8/2 "yer": il/ilce ve TEKIL SEBEKE UNSURU KODU.

    Tekil kod F-21 kunyesinden (`cbs_kodu`) gelir — EPDK CBS usul ve esaslarinin panoyu
    zaten tekil kodla tutmasi bu alani dogrudan besler. Kunye ice aktarilmamissa alan
    UYDURULMAZ, `elle_doldurulacak`'a duser.
    """
    kodlu = [p for p in panolar if p.get("cbs_kodu")]
    if not kodlu:
        return _alan(
            "Yer (il/ilce ve tekil sebeke unsuru kodu)", ELLE,
            aciklama="Panolarin CBS kunyesi ice aktarilmadigi icin tekil sebeke unsuru kodu "
                     "ve il/ilce bilinmiyor (F-21). Pano kimliginden il/ilce TURETILMEZ.",
        )
    yerler = sorted({f"{p.get('il') or '?'}/{p.get('ilce') or '?'}" for p in kodlu})
    kodlar = sorted(p["cbs_kodu"] for p in kodlu)
    eksik = len(panolar) - len(kodlu)
    aciklama = f"F-21 varlik kunyesinden ({len(kodlu)} pano)."
    if eksik:
        aciklama += f" {eksik} panonun kunyesi yok ve listede GORUNMUYOR."
    return _alan(
        "Yer (il/ilce ve tekil sebeke unsuru kodu)", OLCULEN,
        deger="; ".join(yerler) + " — " + ", ".join(kodlar),
        aciklama=aciklama,
    )


def _etkilenen_kullanici(abone_toplami: int | None, abone_eksik: int, pano_sayisi: int) -> dict[str, Any]:
    if abone_toplami is None:
        return _alan(
            "Etkilenen kullanici sayisi", ELLE,
            aciklama=f"Kesintideki {pano_sayisi} panonun HICBIRINDE abone sayisi kunyesi yok "
                     "(F-21 ice aktarimi yapilmamis). SIFIR YAZILMAZ: 'abone yok' ile "
                     "'abone sayisini bilmiyoruz' ayni sey degildir.",
        )
    aciklama = "F-21 kunyesindeki abone sayilarinin toplami."
    if abone_eksik:
        aciklama += (f" DIKKAT: {abone_eksik} panonun kunyesi olmadigi icin toplam BU KADAR "
                     "EKSIKTIR; gercek sayi daha yuksektir.")
    return _alan("Etkilenen kullanici sayisi", OLCULEN, deger=abone_toplami, aciklama=aciklama)


def kesinti_kaydi(outage: dict, *, kanit: list[dict] | None = None) -> dict[str, Any]:
    """Kesinti olayindan Madde 8/2 taslagi uretir.

    `outage` api/outages.outage_view ciktisidir; `kanit` her pano icin MEVCUT kara kutu
    olayina baglantidir (yeni cizelge uretilmez).
    """
    panolar: list[dict] = list(outage.get("panolar") or [])
    pano_sayisi = len(panolar)

    alanlar = [
        _alan(
            "Kesinti numarasi", ELLE,
            aciklama="Dagitim sirketinin kendi kayit numarasi; bu sistemde karsiligi yok.",
        ),
        _alan(
            "Kademe", ELLE,
            aciklama="Panolarimiz AG tarafindadir, kesinti ise UST SEBEKEDEDIR ve hangi "
                     "kademede oldugu olculmuyor. 'AG' yazmak yanlis olurdu.",
        ),
        _yer(panolar),
        _alan(
            "Kesinti nedeni", ONERI,
            deger="Pano ici degil, UST SEBEKE kaynakli",
            aciklama=f"ONERIDIR, KARAR DEGILDIR. Ayni fiderdeki {pano_sayisi} pano es zamanli "
                     "sustu; bu, arizanin panolarin YUKARISINDA oldugunu gosterir. Hava, agac, "
                     "hayvan, kazi gibi bir sebep TAHMIN EDILMEZ — sorumlu kisi doldurur.",
        ),
        _alan(
            "Kesinti sinifi", ONERI,
            deger="Plansiz (ust sebeke)",
            aciklama="ONERIDIR, KARAR DEGILDIR. Mevzuatin sinif sozluguine erisimimiz yok; "
                     "GK10 geregi erisemedigimiz bir metnin sinif adi/kodu yazilmaz. Oneri "
                     "kavramsaldir: planli bir kesinti duyurusu bu sistemde bulunmadigi icin "
                     "olay plansiz VARSAYILMISTIR.",
        ),
        _alan(
            "Baslama zamani", OLCULEN, deger=outage.get("started_at"),
            aciklama="YAKLASIMDIR: panolarin sustugu (son veri) andir. Enerjinin kesildigi "
                     "anin kendisi gozlemlenmiyor; gercek kesme bu andan biraz ONCEDIR.",
        ),
        _alan(
            "Sona erme zamani", ELLE,
            aciklama="RESTORASYON ANI OLCULMUYOR. Elimizdeki tek sey haberlesmenin donusudur "
                     "ve o da 5 dk histerezislidir — enerji donusu DEGILDIR. Bu depodan "
                     "sona erme turetmek, olcmedigimiz bir seyi olcmus gibi gostermek olurdu.",
        ),
        _alan(
            "Kesinti suresi", ELLE,
            aciklama="Sona erme olculmedigi icin sure de uretilemez.",
        ),
        _etkilenen_kullanici(outage.get("abone_toplami"), outage.get("abone_eksik") or 0, pano_sayisi),
        _alan(
            "Toplam etkilenme suresi", ELLE,
            aciklama="Sure x etkilenen kullanici; sure olmadigi icin uretilemez.",
        ),
        _alan(
            "Dagitilmayan enerji", ELLE,
            aciklama="Sure gerektirir. Kesinti ONCESI yuk telemetride vardir ve kanit "
                     "paketindeki kara kutu cizelgesinde gorunur, ama enerji HESAPLANMAZ. "
                     "Tazminat formulune de girilmez (GK10).",
        ),
    ]

    sayim = {durum: sum(1 for a in alanlar if a["durum"] == durum) for durum in (OLCULEN, ONERI, ELLE)}
    return {
        "taslak": True,
        "uyari": TASLAK_UYARISI,
        "outage_id": outage["outage_id"],
        "alanlar": alanlar,
        "ozet": {
            "toplam": len(alanlar),
            "olculen": sayim[OLCULEN],
            "oneri": sayim[ONERI],
            "elle_doldurulacak": sayim[ELLE],
        },
        "kanit": kanit or [],
    }
