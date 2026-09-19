"""L2 filo akran karsilastirmasi ve taban gecerliligi (F-32, Kisi A).

K/K0'IN KOR NOKTASI — bu modulun varlik sebebi:
detect.py K0'i devreye almadan sonraki ogrenme penceresinin MEDYANI olarak dondurur,
sonrasinda k_ratio = K / K0 izlenir. Bu, bozulmanin TABANDAN SONRA basladigini
varsayar. Devreye alma gununde zaten gevsek olan bir baglantida taban BOZUK degeri
dondurur: K yuksek, K0 ayni oranda yuksek, k_ratio 1,0. O nokta omru boyunca
"saglikli" gorunur; L1 esigi (k_ratio_warn 1,3) hicbir zaman tetiklenmez. Nokta kendi
gecmisiyle karsilastirildigi surece bu hata GORULEMEZ.

Goren tek sey AKRANLARDIR: ayni tip panoda ayni gorevi goren, ayni anma akimindaki bir
baglantinin K0'i fiziksel olarak benzer olmalidir (K = dT / I^2; generator.py:349
K0'i anma akimindan turetir). Filo medyanindan belirgin sapan bir K0, "bu nokta
digerlerinden YAPISAL olarak farkli" demektir — gecmisi ne derse desin.

AKRAN GRUBU NOKTA ADIDIR. `DSYA4_L3` yalnizca baska panolarin `DSYA4_L3`'u ile
karsilastirilir. Neden: sema nokta adini sabit bir regex'e baglar
(mqtt-telemetry.schema.json `t_conn[].pt`) ve TEDAS tipi panoda ayni ad ayni cikis
boyunu, yani ayni anma akimini gosterir. `GIRIS_L1` ile `DSYA1_L1`'i ayni torbaya
koymak 2312 A ile 250 A'i karsilastirmak olurdu; K0'lari mertebe farkliligindadir.

YONTEM — MAD tabanli modifiye z (robust z):
    median -> merkez;  MAD = median(|x - median|);  z = (x - median) / (1.4826 * MAD)
1,4826 carpani MAD'i normal dagilimda standart sapmaya esitler. Ortalama/standart
sapma KULLANILMAZ: bozuk panonun kendisi ortalamaya ve sapmaya girer, yani aradigimiz
seyi saklar. Medyan ve MAD %50'ye kadar bozuk veriye dayanir.

GK10 — SENTETIK FILODA "MUKEMMEL AYRIM" BIR URETEC ARTEFAKTIDIR:
generator.py:342 saglikli K0'i SINIRLI DUZGUN dagilimdan cekiyor
(`spread = 1.0 + rng.uniform(-K_SPREAD, K_SPREAD)`, K_SPREAD = 0.15). Duzgun dagilimin
KUYRUGU YOKTUR: saglikli bir pano yapisal olarak aykiri CIKAMAZ. Sinir analitiktir —
U(-0,15, +0,15) icin medyan ~1,0 ve MAD ~0,075, yani olceklenmis sapma 1,4826 x 0,075
= 0,111 ve saglikli bir panonun ulasabilecegi en buyuk |z| = 0,15 / 0,111 = 1,35'tir.
OLCULDU (tests/test_fleet.py, 500 saglikli pano, seed 20260918): en buyuk |z| = 1,534
— sonlu orneklemde MAD gercek degerinin biraz altinda ciktigi icin analitik sinirin
biraz uzerinde. Aykirilik esigi 3,5; yani saglikli pano esigin YARISINA bile ulasmiyor.
Sonucu sudur: 1,6'nin ustundeki HER esik sentetik filoda kusursuz ayrim verir ve bu,
yontemin degil URETECIN ozelligidir.
Gercek filoda K0 dagilimi kuyrukludur (montaj torku, oksitlenme gecmisi, kablo kesiti
toleransi) ve ayrim bu kadar temiz olmaz. Bu modulun sentetik veriden cikardigi hicbir
sayi saha basarimi olarak sunulamaz.

SAF STDLIB: panoalgo uretim kodu numpy KULLANMAZ (prognostics.py ile ayni kural).

ALARM KODU URETMEZ. contracts/alarm-codes.yaml'da `layer: L2` etiketli kod yoktur ve
bu modul bir tane ACMAZ; ciktisi bir alarm degil bir ONERIDIR (operator onayina gider).
Asagidaki esikler sozlesmede olmadigi icin TURETILMISTIR ve cagiran tarafindan
degistirilebilir.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from .onset import baseline_window_is_stable

# MAD'i normal dagilimda standart sapmaya esitleyen carpan (1 / 0.6745).
MAD_TO_SIGMA = 1.4826

# Aykiri sayilma esigi. Modifiye z icin yaygin kullanilan deger 3,5'tir. TURETILMIS —
# sozlesmede L2 esigi yoktur. Sentetik filoda bu esigin ANLAMSIZ oldugunu modul
# basligindaki GK10 notu soyluyor: saglikli panonun tavani zaten 1,35.
DEFAULT_OUTLIER_Z = 3.5

# Altinda medyan ve MAD'in anlamli olmadigi akran sayisi. MAD ucuncu bir degerle
# tamamen degisir; 8 akran medyanin her iki yaninda en az dorder deger birakir.
# TURETILMIS. Bunun altinda karsilastirma YAPILMAZ — az akranla uretilen bir z,
# olcmedigimiz bir dagilimdan emin gorunmek olurdu.
MIN_PEERS = 8

# Taban ogrenme penceresinde uyarilmis (excited) ornek orani bunun altindaysa taban
# guvenilmezdir: RLS uyarim yokken GUNCELLENMEZ (detect.py update()), yani K0 fiziksel
# baglantiyi degil onselin kendisini kodlar. TURETILMIS.
MIN_EXCITED_RATIO = 0.10


@dataclass(frozen=True)
class PeerScore:
    """Bir noktanin akranlari icindeki konumu."""

    pano_id: str
    point: str
    k0: float
    peer_median: float
    peer_mad: float
    robust_z: float | None   # akran sayisi yetersiz veya MAD sifirsa None
    n_peers: int
    outlier: bool


@dataclass(frozen=True)
class BaselineVerdict:
    """Bir noktanin K0 tabaninin GUVENILIR olup olmadigi ve gerekcesi.

    `trustworthy` False ise k_ratio o nokta icin yorumlanmamalidir: 1,0 civarinda
    olmasi saglikli oldugunu DEGIL, tabanin bozuk deger uzerine kurulmus olabilecegini
    gosterir.
    """

    pano_id: str
    point: str
    trustworthy: bool
    reasons: list[str] = field(default_factory=list)
    peer: PeerScore | None = None
    rebaseline_suggested: bool = False


def robust_z_scores(values: Sequence[float]) -> list[float | None]:
    """Bir akran grubunun modifiye z skorlari. MAD sifirsa hepsi None.

    MAD sifir demek "akranlarin yarisindan fazlasi birebir ayni deger" demektir;
    boyle bir grupta sapma olcusu yoktur ve her farki sonsuz z yapmak yaniltici olur.
    """
    if len(values) < 2:
        return [None] * len(values)
    center = _median(values)
    mad = _median([abs(value - center) for value in values])
    if mad <= 0.0:
        return [None] * len(values)
    scale = MAD_TO_SIGMA * mad
    return [(value - center) / scale for value in values]


def peer_scores(
    k0_by_panel: dict[str, dict[str, float]],
    outlier_z: float = DEFAULT_OUTLIER_Z,
    min_peers: int = MIN_PEERS,
) -> list[PeerScore]:
    """Filo capinda akran karsilastirmasi.

    Girdi: {pano_id: {nokta: K0}}. Cikti her (pano, nokta) icin bir PeerScore.
    Gruplama NOKTA ADINA gore yapilir (modul basligindaki gerekce).

    Akran sayisi `min_peers` altinda kalan gruplar da DONER ama `robust_z` None ve
    `outlier` False olur: "olcemedik" ile "aykiri degil" ayni sey degildir, ikincisini
    iddia etmek olcmedigimiz bir seyi soylemek olurdu (GK10).
    """
    by_point: dict[str, list[tuple[str, float]]] = {}
    for pano_id, points in k0_by_panel.items():
        for point, k0 in points.items():
            by_point.setdefault(point, []).append((pano_id, k0))

    scores: list[PeerScore] = []
    for point in sorted(by_point):
        members = sorted(by_point[point])
        values = [k0 for _, k0 in members]
        center = _median(values) if values else 0.0
        mad = _median([abs(value - center) for value in values]) if values else 0.0
        enough = len(members) >= min_peers
        zs = robust_z_scores(values) if enough else [None] * len(members)
        for (pano_id, k0), z in zip(members, zs):
            scores.append(
                PeerScore(
                    pano_id=pano_id,
                    point=point,
                    k0=k0,
                    peer_median=center,
                    peer_mad=mad,
                    robust_z=z,
                    n_peers=len(members),
                    # Yalnizca YUKARI sapma bozulmadir: akranlarindan belirgin DUSUK
                    # K0 iyi bir baglantidir, alarm konusu degil.
                    outlier=bool(enough and z is not None and z >= outlier_z),
                )
            )
    return scores


def baseline_verdict(
    pano_id: str,
    point: str,
    k_history: Sequence[float],
    reference_n: int,
    excited_ratio: float,
    peer: PeerScore | None = None,
    min_excited_ratio: float = MIN_EXCITED_RATIO,
) -> BaselineVerdict:
    """Bir noktanin tabaninin guvenilir olup olmadigina UC ayri kanitla bakar.

    1. UYARIM: taban ogrenilirken yeterince yuk degisimi gorulduse RLS gercekten
       calisti. Gorulmediyse K0 onselin kendisidir (detect.py: uyarim yokken
       parametreler GUNCELLENMEZ).
    2. KARARLILIK: ogrenme penceresinin kendi icinde kalici bir kayma varsa makine
       o pencerede kararli DEGILDI — ISO 17359'un baz cizgi sarti saglanmiyor
       (docs/18 §(b) bunun sinanmadigini itiraf ediyordu).
    3. AKRANLAR: K0 akranlarindan yukari dogru aykirysa taban zaten bozuk bir
       baglantinin uzerine kurulmus olabilir — K/K0'in goremedigi tek durum budur.

    Ucunden HERHANGI BIRI dusukse taban guvenilmez sayilir ve yeniden baz alma
    ONERILIR. Oneri uygulanmaz: otomatik yeniden baz alma gercek bozulmayi susturur
    (docs/07b Y11). Karar operatorundur.
    """
    reasons: list[str] = []

    if excited_ratio < min_excited_ratio:
        reasons.append(
            f"taban ogrenme penceresinde uyarim orani dusuk ({excited_ratio:.1%} < {min_excited_ratio:.0%}): "
            "RLS guncellenmedi, K0 fiziksel baglantiyi degil onseli yansitiyor olabilir"
        )

    if len(k_history) >= reference_n and not baseline_window_is_stable(k_history, reference_n):
        reasons.append(
            "taban ogrenme penceresi kendi icinde kararsiz: pencerenin ikinci yarisi "
            "birinciden kalici olarak sapiyor, bozulma taban ogrenilirken basladi"
        )

    if peer is not None and peer.outlier:
        reasons.append(
            f"K0 akranlarindan yukari aykiri (robust z = {peer.robust_z:.2f}, "
            f"{peer.n_peers} akran, akran medyani {peer.peer_median:.3e}): "
            "devreye alma aninda zaten bozuk bir baglantinin tabani olabilir"
        )

    return BaselineVerdict(
        pano_id=pano_id,
        point=point,
        trustworthy=not reasons,
        reasons=reasons,
        peer=peer,
        rebaseline_suggested=bool(reasons),
    )


def _median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    count = len(ordered)
    mid = count // 2
    return ordered[mid] if count % 2 else (ordered[mid - 1] + ordered[mid]) / 2.0
