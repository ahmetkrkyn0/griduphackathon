"""Prognoz geri testi (F-04, Kisi A): tahmin edilen kalan omur -> olculmus dogruluk.

docs/12 prognoz hakkinda tek bir sayi veriyordu ("S1'de 209 saat one alma") ve o sayi
TESPIT katmanina aitti, tahmine degil. Bu modul tahminin kendisini olcer: koninin
icinde kalma orani, ne zaman guvenilir hale geldigi, yakinsayip yakinsamadigi.

Referans: Saxena ve ark., "Metrics for Offline Evaluation of Prognostic Performance"
(Int. J. Prognostics and Health Management, 2010) ve NASA Prognostics Metrics Library;
ISO 13381-1 prognozun DOGRULANMASINI ve guven ifadesini ister.

GERCEK KALAN OMUR ETIKETTEN TURETILIR, tahminden degil:

    RUL*(t) = t_EOL - t        t_EOL = etiketin `l0_breach_at` alani (70 K ihlali ani)
    RUL^(t) = fixture'in `min_ttl_h` sutunu (kenarin o an yayinladigi ttl_h)

Ikisi ayri kaynaktan gelir: biri enjeksiyonun FIZIKSEL sonucu (dT > 70 K ilk ne zaman
oldu), digeri algoritmanin o andaki ciktisi. validate.py'nin durustluk notuyla ayni
kural: etiket "ne olmaliydi"yi soyler, veri "ne oldu"yu.

Olculen dort sey:

  alfa-lambda   RUL^, [(1-a)RUL*, (1+a)RUL*] konisinin icinde mi? lambda ilk tahmin
                ile t_EOL arasindaki yolun kesridir; lambda=0.5 "omrun yarisinda
                tahmin tutuyor muydu" demektir.
  ufuk (PH)     Tahminin O ANDAN t_EOL'e kadar BIR DAHA konidan cikmadigi ilk an.
                t_EOL'den kac saat once oldugu raporlanir; buyuk = erken guvenilir.
                Hic yoksa None — "tahmin hicbir noktada kalici olarak tutmadi".
  goreli dog.   RA(t) = 1 - |RUL* - RUL^| / RUL* ; ortalamasi CRA. 1.0 = kusursuz,
                0 = hata gercek kalan omur kadar buyuk, negatif = daha da buyuk.
  yakinsama     Saxena ve ark. 2010: mutlak hata egrisi altindaki alanin agirlik
                merkezinin ilk tahmin anina uzakligi. Merkez erkendeyse hata zamanla
                kuculmus, gecteyse buyumus demektir.

SAF STDLIB: panoalgo uretim kodu numpy KULLANMAZ (pyproject.toml bagimlilik notu).
Bu modul yalnizca stdlib'e dayanir; CSV okuma ve zaman damgasi cozumleme cagiranin
isidir (validate.py pandas'i zaten oradan kullaniyor).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

# Saxena ve ark. 2010'un ornek calismalarinda kullandigi koni genisligi. SOZLESME
# DEGILDIR (contracts/alarm-codes.yaml'da prognoz dogrulugu icin esik yoktur);
# olcumun kendisi alfa'ya parametrik birakildi, rapor bu degerle uretilir.
DEFAULT_ALPHA = 0.20

# Omrun ceyreginde / yarisinda / uc ceyreginde bakilir (Saxena ve ark. lambda tanimi).
DEFAULT_LAMBDAS: tuple[float, ...] = (0.25, 0.50, 0.75)

# Kalan omur kovalari (saat). Ikisi depodaki gercek sayilardan gelir, biri turetilmis:
#   336 h - sozlesmedeki ttl_warn_days = 14 gun; ALM-TTL-14D tam burada tetiklenir,
#           yani tahminin ALARMA donustugu esik (contracts/alarm-codes.yaml).
#    48 h - PLAN.md TA2 kabul kriteri: "L0 ihlalinden en az 48 saat once" (satir 961).
#   168 h - TURETILMIS: bir hafta, bakim planlama ufku. Sozlesmede karsiligi yok.
#    12 h - TURETILMIS: bakim ekibinin ayni gun icinde sahaya cikabilecegi pencere.
DEFAULT_BUCKET_EDGES_H: tuple[float, ...] = (12.0, 48.0, 168.0, 336.0)


@dataclass(frozen=True)
class Prediction:
    """Tek bir tahmin ani: o an ne kadar omur kalmisti, algoritma ne dedi."""

    hours_from_start: float  # senaryo baslangicindan itibaren saat
    rul_true_h: float        # t_EOL - t  (pozitif; t_EOL'den sonrasi ayri sayilir)
    rul_pred_h: float        # yukteki ttl_h

    @property
    def error_h(self) -> float:
        """Tahmin - gercek (pozitif = fazla iyimser, omru uzun gosteriyor)."""
        return self.rul_pred_h - self.rul_true_h

    @property
    def ratio(self) -> float:
        """Tahmin / gercek. 1.0 = tam isabet."""
        return self.rul_pred_h / self.rul_true_h


@dataclass(frozen=True)
class AlphaLambdaPoint:
    """Belirli bir lambda anindaki alfa-lambda sonucu."""

    lam: float
    hours_from_start: float
    rul_true_h: float
    rul_pred_h: float
    in_band: bool
    relative_accuracy: float


@dataclass(frozen=True)
class RulBucket:
    """Kalan omur araligina gore ozet: "ne zaman guvenilir hale geldi" sorusu."""

    low_h: float
    high_h: float | None  # None = ust sinir yok
    count: int
    in_band_ratio: float
    median_ratio: float


@dataclass(frozen=True)
class PrognosisResult:
    """Bir yorungenin prognoz geri testi."""

    scenario_id: str
    alpha: float
    count: int                    # t_EOL oncesi tahmin sayisi
    first_prediction_h: float     # ilk tahmin t_EOL'den kac saat once uretildi
    horizon_h: float | None       # prognostic horizon (t_EOL'den kac saat once)
    in_band_ratio: float
    alpha_lambda: tuple[AlphaLambdaPoint, ...]
    cumulative_relative_accuracy: float
    median_relative_accuracy: float
    median_ratio: float
    convergence_h: float | None
    convergence_fraction: float | None  # 0 = hata basta, 1 = hata sonda toplanmis
    buckets: tuple[RulBucket, ...]
    late_count: int               # t_EOL'den SONRA uretilen tahmin sayisi


# ------------------------------------------------------------------ tekil olcutler


def alpha_band(rul_true_h: float, alpha: float = DEFAULT_ALPHA) -> tuple[float, float]:
    """[(1-a)RUL*, (1+a)RUL*] konisi."""
    if rul_true_h <= 0.0:
        raise ValueError(f"rul_true_h pozitif olmali: {rul_true_h}")
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha (0,1) araliginda olmali: {alpha}")
    return (1.0 - alpha) * rul_true_h, (1.0 + alpha) * rul_true_h


def in_alpha_band(rul_true_h: float, rul_pred_h: float, alpha: float = DEFAULT_ALPHA) -> bool:
    """Tahmin koninin icinde mi (sinirlar DAHIL)."""
    low, high = alpha_band(rul_true_h, alpha)
    return low <= rul_pred_h <= high


def relative_accuracy(rul_true_h: float, rul_pred_h: float) -> float:
    """RA = 1 - |RUL* - RUL^| / RUL*.

    KIRPILMAZ: literaturde bazi uygulamalar negatif RA'yi 0'a cekiyor, biz cekmiyoruz.
    Kirpma, iki kat hata ile yirmi kat hatayi ayni gosterir ve kotu sonucu gizler.
    """
    if rul_true_h <= 0.0:
        raise ValueError(f"rul_true_h pozitif olmali: {rul_true_h}")
    return 1.0 - abs(rul_true_h - rul_pred_h) / rul_true_h


# ------------------------------------------------------------------ toplu olcutler


def prognostic_horizon(
    predictions: Sequence[Prediction], alpha: float = DEFAULT_ALPHA
) -> float | None:
    """Tahminin bir daha konidan cikmadigi ilk anin t_EOL'e uzakligi (saat).

    Tanim geriye dogru taranir: son tahminden basa yurunur, koninin disina ilk cikan
    tahmine kadar olan kisim "kalici olarak dogru" bolgedir. Hicbir tahmin tutmuyorsa
    None doner ve rapor bunu "ufuk yok" diye yazar — sifir yazmak yaniltici olurdu,
    sifir "tam ihlal aninda tuttu" demektir.
    """
    horizon: float | None = None
    for prediction in reversed(predictions):
        if not in_alpha_band(prediction.rul_true_h, prediction.rul_pred_h, alpha):
            break
        horizon = prediction.rul_true_h
    return horizon


def alpha_lambda(
    predictions: Sequence[Prediction],
    alpha: float = DEFAULT_ALPHA,
    lambdas: Sequence[float] = DEFAULT_LAMBDAS,
) -> tuple[AlphaLambdaPoint, ...]:
    """Her lambda icin o ana EN YAKIN tahmini degerlendirir.

    lambda, ilk tahmin ile t_EOL arasindaki yolun kesridir. Tam o ana denk gelen bir
    ornek olmayabilir (haberlesme boslugu, uyarim kesilmesi); en yakini secilir ve
    hangi ana bakildigi `hours_from_start` ile raporlanir.
    """
    if not predictions:
        return ()
    start = predictions[0].hours_from_start
    span = predictions[0].rul_true_h  # ilk tahminden t_EOL'e kalan sure
    points = []
    for lam in lambdas:
        target = start + lam * span
        nearest = min(predictions, key=lambda p: abs(p.hours_from_start - target))
        points.append(
            AlphaLambdaPoint(
                lam=lam,
                hours_from_start=nearest.hours_from_start,
                rul_true_h=nearest.rul_true_h,
                rul_pred_h=nearest.rul_pred_h,
                in_band=in_alpha_band(nearest.rul_true_h, nearest.rul_pred_h, alpha),
                relative_accuracy=relative_accuracy(nearest.rul_true_h, nearest.rul_pred_h),
            )
        )
    return tuple(points)


def convergence(predictions: Sequence[Prediction]) -> tuple[float | None, float | None]:
    """(yakinsama uzakligi saat, pencere icindeki kesri) — Saxena ve ark. 2010.

        x_c = 1/2 * SUM (t[i+1]^2 - t[i]^2) M[i] / SUM (t[i+1] - t[i]) M[i]
        y_c = 1/2 * SUM (t[i+1] - t[i]) M[i]^2 / SUM (t[i+1] - t[i]) M[i]
        C   = sqrt((x_c - t_P)^2 + y_c^2)

    M[i] = |hata| (saat). Agirlik merkezi ilk tahmin anina (t_P) yakinsa hata zamanla
    kuculmus, gecteyse buyumus demektir. C tek basina okunmasi zor bir sayidir; bu
    yuzden ikinci deger olarak (x_c - t_P) / (t_EOL - t_P) kesri de donulur
    (TURETILMIS): 0'a yakin = hata basta toplanmis (yakinsiyor), 1'e yakin = sonda.

    TEK BASINA OKUNMAZ: hata her yerde buyukse merkez de ortalarda cikar ve bu
    "yakinsiyor" demek DEGILDIR. Koni icinde kalma orani ile birlikte okunmalidir.

    En az iki tahmin gerekir; yoksa (None, None).
    """
    if len(predictions) < 2:
        return None, None

    t_p = predictions[0].hours_from_start
    t_eol = predictions[0].hours_from_start + predictions[0].rul_true_h

    area = moment_x = moment_y = 0.0
    for current, nxt in zip(predictions, predictions[1:], strict=False):
        width = nxt.hours_from_start - current.hours_from_start
        if width <= 0.0:
            continue
        magnitude = abs(current.error_h)
        area += width * magnitude
        moment_x += (nxt.hours_from_start**2 - current.hours_from_start**2) * magnitude
        moment_y += width * magnitude * magnitude

    span = t_eol - t_p
    if area <= 0.0:  # hic hata yok: kusursuz tahmin, uzaklik sifir
        return 0.0, 0.0

    x_c = 0.5 * moment_x / area
    y_c = 0.5 * moment_y / area
    distance = ((x_c - t_p) ** 2 + y_c**2) ** 0.5
    fraction = (x_c - t_p) / span if span > 0.0 else None
    return distance, fraction


def rul_buckets(
    predictions: Sequence[Prediction],
    alpha: float = DEFAULT_ALPHA,
    edges_h: Sequence[float] = DEFAULT_BUCKET_EDGES_H,
) -> tuple[RulBucket, ...]:
    """Kalan omur araligina gore koni icinde kalma orani ve medyan tahmin/gercek.

    "Tahmin ne zaman guvenilir hale geldi" sorusunun cevabi buradadir: saglikli bir
    prognozda ariza yaklastikca (kucuk RUL*) oran 1'e dogru gitmelidir.
    """
    bounds = [0.0, *sorted(edges_h)]
    buckets = []
    for index, low in enumerate(bounds):
        high = bounds[index + 1] if index + 1 < len(bounds) else None
        members = [
            p
            for p in predictions
            if p.rul_true_h > low and (high is None or p.rul_true_h <= high)
        ]
        if not members:
            buckets.append(RulBucket(low, high, 0, 0.0, 0.0))
            continue
        hits = sum(1 for p in members if in_alpha_band(p.rul_true_h, p.rul_pred_h, alpha))
        buckets.append(
            RulBucket(
                low_h=low,
                high_h=high,
                count=len(members),
                in_band_ratio=hits / len(members),
                median_ratio=_median([p.ratio for p in members]),
            )
        )
    return tuple(buckets)


# ------------------------------------------------------------------ geri test


def predictions_from_series(
    hours_from_start: Sequence[float],
    ttl_h: Sequence[float | None],
    eol_hours: float,
) -> tuple[tuple[Prediction, ...], int]:
    """(t_EOL oncesi tahminler, t_EOL sonrasi tahmin sayisi).

    t_EOL'den SONRA gelen tahminler geri testin disinda birakilir: o noktada gercek
    kalan omur negatiftir, oran ve goreli dogruluk tanimsizdir. Sayilari yine de
    donulur, cunku "sinir zaten asildi ama sistem hala omur var diyor" raporlanmasi
    gereken bir davranistir.
    """
    if len(hours_from_start) != len(ttl_h):
        raise ValueError(
            f"seriler ayni uzunlukta olmali: {len(hours_from_start)} != {len(ttl_h)}"
        )
    before: list[Prediction] = []
    late = 0
    for hours, predicted in zip(hours_from_start, ttl_h, strict=False):
        if predicted is None:
            continue
        rul_true = eol_hours - hours
        if rul_true <= 0.0:
            late += 1
            continue
        before.append(Prediction(float(hours), float(rul_true), float(predicted)))
    return tuple(before), late


def backtest(
    scenario_id: str,
    predictions: Sequence[Prediction],
    late_count: int = 0,
    alpha: float = DEFAULT_ALPHA,
    lambdas: Sequence[float] = DEFAULT_LAMBDAS,
    edges_h: Sequence[float] = DEFAULT_BUCKET_EDGES_H,
) -> PrognosisResult | None:
    """Tum olcutleri tek sonuca toplar. Tahmin yoksa None (olcum yapilamaz)."""
    if not predictions:
        return None

    accuracies = [relative_accuracy(p.rul_true_h, p.rul_pred_h) for p in predictions]
    hits = sum(1 for p in predictions if in_alpha_band(p.rul_true_h, p.rul_pred_h, alpha))
    distance, fraction = convergence(predictions)

    return PrognosisResult(
        scenario_id=scenario_id,
        alpha=alpha,
        count=len(predictions),
        first_prediction_h=predictions[0].rul_true_h,
        horizon_h=prognostic_horizon(predictions, alpha),
        in_band_ratio=hits / len(predictions),
        alpha_lambda=alpha_lambda(predictions, alpha, lambdas),
        cumulative_relative_accuracy=sum(accuracies) / len(accuracies),
        median_relative_accuracy=_median(accuracies),
        median_ratio=_median([p.ratio for p in predictions]),
        convergence_h=distance,
        convergence_fraction=fraction,
        buckets=rul_buckets(predictions, alpha, edges_h),
        late_count=late_count,
    )


def _median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    return ordered[mid] if n % 2 else (ordered[mid - 1] + ordered[mid]) / 2.0
