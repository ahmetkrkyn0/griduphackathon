"""L2 degisim noktasi: bozulma NE ZAMAN basladi (F-32, Kisi A).

Esik tabanli tespit "simdi kotu" der, "ne zaman kotulesti" demez. Operatorun bakim
karari ve olay kara kutusunun penceresi icin gereken sayi ikincisidir: K/K0 esigi
dun asildi diye bozulma dun baslamadi.

YONTEM — CUSUM (birikimli toplam). Referans penceresinden ortalama ve sapma alinir,
sonraki her ornegin bu tabandan SAPMASI biriktirilir:

    S[k] = max(0, S[k-1] + (x[k] - mu0)/sigma0 - slack)

`slack` (yarim kayma payi) gurultunun birikmesini engeller: sapma slack'in altinda
kaldigi surece S sifira geri duser. S esigi asinca "degisim var" denir ve BASLANGIC
ANI olarak S'nin en son SIFIRLANDIGI ornek raporlanir — klasik CUSUM baslangic
kestirimi. Esigin asildigi an degil, birikimin basladigi andir.

NEDEN CUSUM (ve neden Kalman degil): kucuk ve KALICI bir kaymayi en hizli yakalayan
ardisik testtir; tam olarak bizim vakamiz — gevseyen baglanti K'yi yavasca ve geri
donmemek uzere buyutur. Genisletilmis Kalman filtresi GELISTIRME-BACKLOGU.md §6'da
gerekcesiyle elendi (durum uzayi modeli kurmak icin olcmedigimiz parametreler gerekir);
bu modul onun yerine gecmez, ayri bir sey yapar: model kurmaz, tabandan sapmayi sayar.

SAF STDLIB: panoalgo uretim kodu numpy KULLANMAZ (prognostics.py ile ayni kural).

ESIKLER SOZLESMEDE YOKTUR. contracts/alarm-codes.yaml'da degisim noktasi icin esik
tanimli degildir ve bu modul alarm KODU URETMEZ — yalnizca bir zaman damgasi doner.
Asagidaki iki sayi CUSUM'un ders kitabi ayarindan gelir ve TURETILMISTIR.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

# Yarim kayma payi: "yakalamak istedigimiz en kucuk kaymanin yarisi" klasik CUSUM
# ayaridir (kayma sigma cinsinden 1.0 ise slack 0.5). Bunun altindaki sapmalar
# birikmez. TURETILMIS — sozlesmede degisim noktasi esigi yoktur.
DEFAULT_SLACK_SIGMA = 0.5

# Karar esigi: S bu degeri asinca degisim ilan edilir. Buyuk esik = gec ama emin
# tespit. 5 sigma ders kitabi baslangic degeridir. TURETILMIS.
DEFAULT_THRESHOLD_SIGMA = 5.0

# Referans penceresinin sapmasi sifira cok yakinsa (sabit seri) z bolmesi patlar.
# Taban serisi tamamen duzse en kucuk sapma bile sonsuz z uretirdi; bu alt sinir
# onu engeller ve "degisim yok" tarafinda hata yapar.
MIN_SIGMA = 1.0e-12


@dataclass(frozen=True)
class Onset:
    """Bir degisim noktasi kestirimi.

    changed : referans tabandan kalici sapma bulundu mu
    onset_index : bozulmanin BASLADIGI ornek (S'nin son sifirlandigi yer); yoksa None
    alarm_index : CUSUM esiginin ASILDIGI ornek; yoksa None
    lead_samples : esigin asilmasindan kac ornek ONCE basladigi (alarm - onset)
    peak_cusum : serinin tamaminda ulasilan en yuksek birikim (esikle kiyaslanabilir)
    """

    changed: bool
    onset_index: int | None
    alarm_index: int | None
    lead_samples: int | None
    peak_cusum: float


def detect_onset(
    values: Sequence[float],
    reference_n: int,
    slack_sigma: float = DEFAULT_SLACK_SIGMA,
    threshold_sigma: float = DEFAULT_THRESHOLD_SIGMA,
) -> Onset:
    """Tek yonlu (yukari) CUSUM ile bozulmanin baslangic anini kestirir.

    `reference_n` ilk kac ornegin TABAN sayilacagidir; mu0 ve sigma0 oradan alinir.
    Tipik kullanim taban ogrenme penceresidir (contracts: baseline_learning_days),
    yani "kestirimin saglikli oldugunu varsaydigimiz" bolum.

    Yalnizca YUKARI yon izlenir: K'nin dusmesi bozulma degildir (temizlenen veya
    yeniden sikilan baglanti). Iki yonlu bir test burada yanlis pozitif uretirdi.
    """
    if reference_n < 2:
        raise ValueError(f"reference_n en az 2 olmali: {reference_n}")
    if len(values) <= reference_n:
        return Onset(changed=False, onset_index=None, alarm_index=None, lead_samples=None, peak_cusum=0.0)

    reference = list(values[:reference_n])
    mu0 = sum(reference) / len(reference)
    sigma0 = max(_stdev(reference, mu0), MIN_SIGMA)

    cusum = 0.0
    peak = 0.0
    # Birikimin en son SIFIR oldugu ornek. Bir sonraki ornek, birikime katki yapan
    # ILK ornektir; baslangic ani odur.
    last_zero = reference_n - 1
    onset_index: int | None = None
    alarm_index: int | None = None

    for index in range(reference_n, len(values)):
        z = (values[index] - mu0) / sigma0
        cusum = max(0.0, cusum + z - slack_sigma)
        peak = max(peak, cusum)
        if cusum <= 0.0:
            last_zero = index
            continue
        if alarm_index is None and cusum >= threshold_sigma:
            alarm_index = index
            onset_index = last_zero + 1

    if alarm_index is None or onset_index is None:
        return Onset(changed=False, onset_index=None, alarm_index=None, lead_samples=None, peak_cusum=peak)
    return Onset(
        changed=True,
        onset_index=onset_index,
        alarm_index=alarm_index,
        lead_samples=alarm_index - onset_index,
        peak_cusum=peak,
    )


def baseline_window_is_stable(
    values: Sequence[float],
    reference_n: int,
    slack_sigma: float = DEFAULT_SLACK_SIGMA,
    threshold_sigma: float = DEFAULT_THRESHOLD_SIGMA,
) -> bool:
    """Taban ogrenme penceresinin KENDI ICINDE kararli olup olmadigini soyler.

    NEDEN AYRI BIR SORU: ISO 17359 baz cizgisinin "makine kararliyken" alinmasini
    ister; docs/18 §(b) bu sartin DOGRULANMADIGINI itiraf ediyordu — 7 gunluk pencere
    dolunca taban kosulsuz donuyordu. Pencerenin ilk yarisi ile ikinci yarisi arasinda
    kalici bir kayma varsa, o pencerede makine kararli DEGILDIR ve medyani saglikli
    bir taban sayilamaz: bozulma taban ogrenilirken basladi.

    Pencerenin ilk yarisi referans alinir, ikinci yarisi ayni CUSUM ile sinanir.
    """
    window = list(values[:reference_n])
    half = len(window) // 2
    if half < 2:
        return True  # sinayacak kadar ornek yok; "kararsiz" demek kanitsiz olurdu
    return not detect_onset(window, half, slack_sigma, threshold_sigma).changed


def _stdev(values: Sequence[float], mean: float) -> float:
    return math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))
