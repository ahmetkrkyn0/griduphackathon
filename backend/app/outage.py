"""Ust sebeke kesintisi bagintisi (F-22).

NE YAPAR
Ayni FIDERDEKI panolarin es zamanli susmasini N ayri ariza degil TEK bir kesinti olayina
cevirir. Bir fider acildiginda merkez bugun bunu N ayri pano arizasi olarak goruyor; dogru
yorum tersidir — panolarin degil UST SEBEKENIN arizasi.

Bunun olculebilir bedeli sozlesmede yazili: bir fider dustugunde konsola IKI kod birden
duser — ALM-COMMS-LOST (SYS, sms: digest_only) ve ALM-LASTGASP (P2, sms: true). Yani sel
yalnizca gunluk ozete dusen SYS akisi degil, GERCEK SMS ureten P2 akisidir: ALM-LASTGASP
kenarin gonderdigi "son nefes" olayidir (limits.py: "besleme kesilme OLAYI, esik degil"),
yani her pano kendi basina bir P2 uretir.

FIDER BILGISI YOKSA BAGINTI KURULMAZ
Gruplama `panels.fider_id` uzerinden yapilir ve bu alan F-21'in ice aktardigi kunyeden gelir.
Kunyesi olmayan pano GRUPLANMAZ: "ayni anda sustular, oyleyse ayni fiderdedirler" demek,
olcmedigimiz bir topolojiyi uydurmak olurdu. Beyan edilmis risk: YANLIS fider eslemesi,
N panoyu YANLIS tek olaya toplar. Baginti gercek bir sebeke topolojisinden degil, ICE
AKTARILMIS bir etiketten turer.

NE YAPMAZ
  1. **Alarm BASTIRMAZ.** Alt alarmlar aynen uretilir ve bildirim davranisi DEGISMEZ; olay
     onlari yalnizca `outage_id` ile baglar. Bastirma bir ISA-18.2 kararidir (kimin, hangi
     kosulda bastirdigi denetlenebilir olmali) ve en yuksek oncelikli alarmin asla
     bastirilmadigi bir durum makinesi ister — F-25'in konusu. Burada baginti TOPLAYICIDIR,
     susturucu degil.
  2. **Kesme anini GORMEZ.** `started_at`, kumedeki en gec `last_rx`'tir: enerjinin kesildigi
     anin olculebilen en iyi yaklasimi. Kesme aninin kendisi gozlemlenmiyor.
  3. **Restorasyonu GORMEZ.** `ended_at` haberlesmenin geri donusudur ve histerezislidir;
     enerjinin geri geldigi an bu depoda olculmuyor (F-23 bunu acikca isaretler).

Bu modul SAF'tir: veritabani ve saat bilmez, boylece baginti karari testte birebir
kurulabilir (journal_chain.py ile ayni gerekce).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class SilentPanel:
    """Haberlesmesi kopmus tek pano. `fider_id` None ise baginti disinda kalir."""

    pano_id: str
    last_rx: datetime
    fider_id: str | None = None
    name: str | None = None
    abone_sayisi: int | None = None


@dataclass(frozen=True)
class OutageGroup:
    """Tek bir ust sebeke kesintisi: ayni fiderde es zamanli susan panolar."""

    fider_id: str
    started_at: datetime
    panels: tuple[SilentPanel, ...]

    @property
    def outage_id(self) -> str:
        """Fider + baslangic anindan TURETILMIS kimlik.

        Zamanlayici her tik'te (5 s) ayni kesintiyi yeniden tespit eder. Kimlik rastgele
        olsaydi her tik yeni bir kesinti kaydi acardi; turetilmis kimlik yazmayi
        kendiliginden fikirli (idempotent) yapar.
        """
        # UTC'ye normalize edilir: aksi halde ayni kesinti, makinenin saat dilimine gore
        # FARKLI bir kimlik alirdi ve merkez ile bagimsiz bir arac ayni olayi ayni adla
        # anamazdi (journal_chain._field ile ayni gerekce).
        damga = self.started_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return f"OUT-{self.fider_id}-{damga}"

    @property
    def abone_toplami(self) -> int | None:
        """Etkilenen abone TOPLAMI (EPDK Madde 8/2).

        Yalnizca kunyesi olan panolar toplanir. Hicbirinin kunyesi yoksa None doner —
        SIFIR YAZILMAZ: "abone yok" ile "abone sayisini bilmiyoruz" ayni sey degildir.
        """
        bilinen = [p.abone_sayisi for p in self.panels if p.abone_sayisi is not None]
        return sum(bilinen) if bilinen else None

    @property
    def abone_eksik(self) -> int:
        """Abone sayisi bilinmedigi icin toplama giremeyen pano sayisi — gizlenmez."""
        return sum(1 for p in self.panels if p.abone_sayisi is None)


def correlate(
    silent: list[SilentPanel],
    *,
    min_panels: int,
    window: timedelta,
) -> list[OutageGroup]:
    """Es zamanli susan panolari fider bazinda kesinti olaylarina toplar.

    `min_panels` ve `window` contracts/alarm-codes.yaml'dan gelir (outage_min_panels,
    outage_window_min) — koda GOMULMEZ (PLAN.md kural 10).

    TEK PANOLU DURUM: `min_panels` >= 2 oldugu surece tek bir panonun susmasi hicbir zaman
    kesinti olayi dogurmaz ve cagiran taraftaki eski davranis (her pano icin ayri
    ALM-COMMS-LOST) aynen isler. Bu, adi konmus bir regresyon testiyle kilitlidir.
    """
    by_feeder: dict[str, list[SilentPanel]] = {}
    for panel in silent:
        # Fideri bilinmeyen pano BAGINTI DISINDA kalir (bkz. modul basligi).
        if panel.fider_id is None:
            continue
        by_feeder.setdefault(panel.fider_id, []).append(panel)

    groups: list[OutageGroup] = []
    for fider_id, panels in by_feeder.items():
        for cluster in _cluster_by_time(panels, window):
            if len(cluster) >= min_panels:
                groups.append(
                    OutageGroup(
                        fider_id=fider_id,
                        # Kumedeki EN GEC son veri: enerjinin kesildigi anin olculebilen
                        # en iyi yaklasimi.
                        started_at=max(p.last_rx for p in cluster),
                        panels=tuple(sorted(cluster, key=lambda p: p.pano_id)),
                    )
                )
    groups.sort(key=lambda g: (g.started_at, g.fider_id), reverse=True)
    return groups


def _cluster_by_time(panels: list[SilentPanel], window: timedelta) -> list[list[SilentPanel]]:
    """`last_rx` degerlerini `window` genisliginde kumelere ayirir.

    Kume, ilk uyesinden itibaren `window` kadar uzar; bu sinir ASILDIGINDA yeni kume baslar.
    Boylece gun boyunca teker teker susan panolar (her biri farkli sebeple) tek bir kesintiye
    toplanmaz — es zamanlilik gercekten aranir.
    """
    ordered = sorted(panels, key=lambda p: p.last_rx)
    clusters: list[list[SilentPanel]] = []
    current: list[SilentPanel] = []
    for panel in ordered:
        if current and panel.last_rx - current[0].last_rx > window:
            clusters.append(current)
            current = []
        current.append(panel)
    if current:
        clusters.append(current)
    return clusters
