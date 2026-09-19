"""Kenar tespit boru hatti (TA2 Adim 6, Kisi A): ham fizik yuku -> zengin telemetri.

Tespitin NEREDE calistigi bir tercih degil, sozlesmenin sonucudur:
backend/app/risk.py CentralDetector Protokolu yalnizca `list[str]` kabul eder.
K indeksi, tau, sinira kalan sure, veri kalitesi bitleri ve risk skoru merkeze
SADECE telemetri yukunun alanlariyla girebilir (mqtt-telemetry.schema.json
`t_conn[].k/k_ratio/tau_s/ttl_h/excited/q` ve `risk` bloklari). Dolayisiyla bu boru
hatti KENARDA (panosim ve Faz 3'te firmware icinde) calisir; merkez yalnizca
aciklama ve ISA-18.2 yasam dongusu yapar.

Zincir:

    PanelSimulator.step()              ham fizik (sicaklik, akim, ortam)
        |
        +-- KIndexEstimator (nokta basina)   -> k, k_ratio, tau_s, ttl_h, excited
        +-- quality.point_quality / Tracker  -> t_conn[].q bit alani
        +-- limits.evaluate                  -> alarms[] (L0/L1 esik kodlari)
        +-- fusion.score                     -> risk{score, mode, ttl_h, contributions}
        |
        v
    sema-gecerli zenginlestirilmis yuk

VERI KALITESI TEK YOLDAN: DQ kodlari `alarms[]` listesine YAZILMAZ, yalnizca
`t_conn[].q` bitine yazilir. Merkez q bitlerini okuyup alarmi DOGRU NOKTAYA baglar
(backend/app/risk.py:184-192); ayni kod bir de alarms[] icinden gelseydi merkez onu
point=None ile ikinci kez kaydeder, ayni ariza icin iki alarm ve iki SMS uretilirdi.

TABAN OGRENME: K/K0 ancak K0 sabitlendikten sonra anlamlidir (sozlesme:
baseline_learning_days = 7). freeze_baselines() cagrilmadan k_ratio 1.0 doner ve
K esikleri tetiklenmez — devreye alma gununde sahte alarm yagmuru olmaz.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from . import fusion, limits, physics, quality
from .detect import BaselineEvidence, KIndexEstimator, lambda_for_period, load_thresholds
from .profiles import ProfileKind, load_profile

# Beklenen yuk profili icin gecmis I^2 ortalamasinin penceresi (ornek sayisi).
I2_MEAN_WINDOW = 720

# Kestirime AIT alanlar. Kestirim yoksa bunlar yukten silinir; uretecin kendi
# gercek degerleri orada kalirsa kenar, olcemeyecegi bir dogruyu yayinlamis olur.
ESTIMATED_FIELDS = ("k", "k_ratio", "tau_s", "ttl_h")

# BEYAN EDILEN periyot ile GOZLENEN aralik bu kesirden fazla ayrisirsa sayilir.
# Titremeye (network jitter, planlayici kaymasi) genis pay birakir; amaci tek bir
# ornegi yakalamak degil, YAPISAL bir kaymayi gorunur kilmaktir.
PERIOD_TOLERANCE = 0.25


def _forget_estimates(point: dict) -> None:
    for name in ESTIMATED_FIELDS:
        point.pop(name, None)


class EdgePipeline:
    """Bir veya daha cok panonun telemetrisini zenginlestirir.

    Durum pano_id ile anahtarlanir: tek boru hatti yuk testindeki 1.000 sanal panoyu
    da besleyebilir.
    """

    def __init__(
        self,
        profile: ProfileKind = "karma",
        contracts_dir: Path | None = None,
        period_s: float | None = None,
    ) -> None:
        """period_s verilirse ornekleme periyodu zaman damgalarindan TURETILMEZ.

        Kenar kendi periyodunu bilir; damgalardan cikarmak (a) ilk ornegi harcar,
        (b) titreme ve backfill'de yanlis periyot verir. Firmware tarafi periyodu
        konfigurasyondan alir; iki uygulamanin ayni sonucu vermesi icin Python da
        alabilmeli — olculdu: bir orneklik kayma K/K0'da 0,03'e varan fark yapiyordu.
        """
        self._contracts_dir = contracts_dir
        self._fixed_period_s = period_s
        self._profile: ProfileKind = profile
        self._quality = quality.QualityTracker(contracts_dir)
        self._reference_lam = float(load_thresholds(contracts_dir)["rls_lambda"])
        self._estimators: dict[tuple[str, str], KIndexEstimator] = {}
        self._i2_mean: dict[tuple[str, str], list[float]] = {}
        self._previous: dict[str, dict] = {}
        self._last_ts: dict[str, datetime] = {}
        self._period_mismatch: dict[str, int] = {}
        self._frozen = False

    # ------------------------------------------------------------------ taban

    def freeze_baselines(self) -> None:
        """Tum noktalarin K0 tabanini sabitler (devreye almadan 7 gun sonra)."""
        for estimator in self._estimators.values():
            try:
                estimator.freeze_baseline()
            except ValueError:  # henuz kestirim yok; bu nokta bir sonraki turda
                continue
        self._frozen = True

    @property
    def baseline_frozen(self) -> bool:
        return self._frozen

    @property
    def period_mismatch(self) -> dict[str, int]:
        """{pano_id: beyan edilen periyoda uymayan ornek sayisi} (bkz. _note_mismatch).

        Bos sozluk = islemenin ritmi beyan edildigi gibi. Sabit periyot
        verilmemisse (periyot damgalardan turetiliyorsa) her zaman bostur.
        """
        return dict(self._period_mismatch)

    def baseline_report(self) -> dict[str, dict[str, BaselineEvidence]]:
        """Donmus tabanlarin kaniti: {pano_id: {nokta: BaselineEvidence}} (F-32).

        Filo akran karsilastirmasi (fleet.peer_scores) ve taban gecerliligi karari
        (fleet.baseline_verdict) bunu okur. Tabani DONMAMIS nokta listede YER ALMAZ:
        K0'i olmayan bir nokta akranlariyla kiyaslanamaz ve "aykiri degil" demek
        olcmedigimiz bir seyi iddia etmek olurdu (GK10).
        """
        report: dict[str, dict[str, BaselineEvidence]] = {}
        for (pano_id, point), estimator in self._estimators.items():
            evidence = estimator.baseline_evidence
            if evidence is not None:
                report.setdefault(pano_id, {})[point] = evidence
        return report

    def k_histories(self) -> dict[str, dict[str, tuple[float, ...]]]:
        """Nokta basina saklanan K kestirimleri: {pano_id: {nokta: (K, ...)}} (F-32).

        Taban ogrenme penceresinin KENDI ICINDE kararli olup olmadigi
        (onset.baseline_window_is_stable) ve bozulmanin baslangic ani
        (onset.detect_onset) bu seriden hesaplanir.
        """
        histories: dict[str, dict[str, tuple[float, ...]]] = {}
        for (pano_id, point), estimator in self._estimators.items():
            histories.setdefault(pano_id, {})[point] = estimator.k_history
        return histories

    # ------------------------------------------------------------------ adim

    def process(self, payload: dict) -> dict:
        """Yuku YERINDE zenginlestirir ve ayni sozlugu doner."""
        pano_id = payload["pano_id"]
        ts = datetime.fromisoformat(payload["ts"])
        period_s = self._period_s(pano_id, ts)

        self._update_points(payload, pano_id, ts, period_s)
        self._update_quality(payload)
        self._suppress_ttl_when_quality_suspect(payload)

        previous = self._previous.get(pano_id)
        codes = [
            code
            for code in limits.evaluate(payload, previous, self._contracts_dir)
            if not code.startswith("ALM-DQ-")
        ]
        payload["alarms"] = codes
        payload["risk"] = self._risk_block(payload, codes)

        self._previous[pano_id] = {"tvoc": dict(payload.get("tvoc") or {}), "ts": payload["ts"]}
        return payload

    # ------------------------------------------------------------------ ic

    def _period_s(self, pano_id: str, ts: datetime) -> float:
        """Ornekleme periyodunu ardisik zaman damgalarindan cikarir."""
        last = self._last_ts.get(pano_id)
        self._last_ts[pano_id] = ts
        if self._fixed_period_s is not None:
            if last is not None:
                self._note_mismatch(pano_id, (ts - last).total_seconds())
            return self._fixed_period_s
        if last is None:
            return 0.0
        seconds = (ts - last).total_seconds()
        return seconds if seconds > 0.0 else 0.0

    def _note_mismatch(self, pano_id: str, observed_s: float) -> None:
        """Beyan edilen periyot ile gercek aralik ayrisirsa sayar (F-36 emniyeti).

        Sabit periyot bir BEYANDIR ve yuk oyle islenir; beyan yanlissa hicbir
        istisna cikmaz, yalnizca tau, k_slope ve unutma faktorunun etkin hafizasi
        sessizce kayar. Uyarlanabilir raporlamanin sessizce yanlis yapilabilecegi
        tek yer burasi oldugu icin sayac ekli: "yayinlamiyorsak islemeye de gerek
        yok" diye process() cagrisi seyreltilirse sayac artar.

        NEREDE SILAHLI, NEREDE DEGIL (durustluk notu):
          * loadtest/veri_butcesi.py sifir olmasini SART kosar ve aksi halde
            sayi yazmadan patlar. F-36'nin olculen iddiasi oradan cikar.
          * sim/panosim.py sabit periyot VERMEZ (damgalardan turetir), bu yuzden
            sayac orada her zaman bostur - yanlis alarm da uretmez.
          * sim/panobeyni_sim.py'de sayac SATURE OLUR ve bu BEKLENEN bir
            sonuctur: o kabuk 1 s'de bir isler ama periyodu 10 s beyan eder
            (period x report_every). Bu tutarsizlik F-36'DAN ONCE de vardi;
            madde bilincli olarak DOKUNMADI, cunku duzeltmek yayinlanan
            tau_s/ttl_h degerlerini degistirir ve ayri bir madde gerektirir.
            Sayac burada bir REGRESYON sinyali degil, var olan bir sapmanin
            olculebilir hale gelmesidir.
        """
        declared = self._fixed_period_s
        if not declared or observed_s <= 0.0:
            return
        if abs(observed_s - declared) / declared > PERIOD_TOLERANCE:
            self._period_mismatch[pano_id] = self._period_mismatch.get(pano_id, 0) + 1

    def _update_points(self, payload: dict, pano_id: str, ts: datetime, period_s: float) -> None:
        for point in payload["t_conn"]:
            key = (pano_id, point["pt"])
            current = physics.point_current(payload, point["pt"])
            self._remember_i2(key, current * current)

            estimator = self._estimators.get(key)
            if estimator is None:
                if period_s <= 0.0:
                    # Ilk ornek: periyot henuz bilinmiyor, kestirim yapilamaz.
                    # Alanlari SILMEK sart: uretec kendi GERCEK K'sini yaza yaza
                    # gelir ve burada birakilirsa kenar, bilemeyecegi bir dogruyu
                    # yayinlamis olur. Demo icin de savunma icin de kabul edilemez.
                    _forget_estimates(point)
                    continue
                estimator = KIndexEstimator(
                    ts=period_s,
                    # Unutma faktoru ornekleme periyoduna tasinir: ayni lam farkli
                    # periyotta farkli ZAMAN hafizasi demektir (bkz. detect.py notu).
                    lam=lambda_for_period(period_s, self._reference_lam),
                    contracts_dir=self._contracts_dir,
                    expected_i2=self._expected_i2(key, ts),
                )
                self._estimators[key] = estimator

            state = estimator.update(i_a=current, dt_c=point["dt_c"])
            if state.k <= 0.0:
                # Henuz hicbir RLS guncellemesi olmadi. "K = 0" fiziksel olarak
                # "sifir isil direnc" demek olurdu; sema bu alanlari opsiyonel
                # tanimladigi icin dogrusu HIC YAZMAMAK.
                _forget_estimates(point)
                continue
            point["k"] = round(state.k, 12)
            point["k_ratio"] = round(state.k_ratio, 4)
            point["tau_s"] = round(state.tau_s, 1)
            point["ttl_h"] = None if state.ttl_h is None else round(state.ttl_h, 1)
            point["excited"] = state.excited

    def _remember_i2(self, key: tuple[str, str], i2: float) -> None:
        window = self._i2_mean.setdefault(key, [])
        window.append(i2)
        if len(window) > I2_MEAN_WINDOW:
            del window[: len(window) - I2_MEAN_WINDOW]

    def _expected_i2(self, key: tuple[str, str], start: datetime):
        """Gelecek I^2 tahmini: gecmis ortalama x saat-of-hafta profil orani.

        Rapor 15.1 gelecek yuk icin "I2_profil(t)" der; sabit akim varsayimi degil.
        """
        from datetime import timedelta

        def expected(hours: float) -> float:
            window = self._i2_mean.get(key) or [0.0]
            mean_i2 = sum(window) / len(window)
            now = self._last_ts.get(key[0], start)
            here = load_profile(self._profile, now)
            there = load_profile(self._profile, now + timedelta(hours=hours))
            ratio = (there / here) if here > 0.0 else 1.0
            return mean_i2 * ratio * ratio

        return expected

    def _update_quality(self, payload: dict) -> None:
        per_point = self._quality.check(payload)
        for point in payload["t_conn"]:
            codes = per_point.get(point["pt"], [])
            point["q"] = quality.q_bits(codes, self._contracts_dir)

    def _suppress_ttl_when_quality_suspect(self, payload: dict) -> None:
        """_update_points, _update_quality'den ONCE calisir, yani TTL kestirimi q'yu
        hic gormeden yapilir. Zaten varolan bir kalite kurali tarafindan isaretlenmis
        bir nokta (q != 0) hicbir durumda da TTL tahmini tasimasin — bu metod bu
        kontrati garanti eder.

        Not: S8 bilinen siniri (docs/05 #10) surunen sensoru tespiti icerir, ama
        drift varolan ALM-DQ-* kurallari tarafindan yakalanmaz (q asla set olmaz).
        Bu metod zaten-isaretli noktalar icin kontrati garantiler, drift tespitini
        degil. Drift tespiti ayri, ozel bir kalite kurali gerekir (henuz eklenmedi)."""
        for point in payload["t_conn"]:
            if point.get("q", 0) != 0:
                point["ttl_h"] = None

    def _risk_block(self, payload: dict, codes: list[str]) -> dict:
        worst_ratio = max((p.get("k_ratio") or 1.0) for p in payload["t_conn"])
        ttl_values = [p["ttl_h"] for p in payload["t_conn"] if p.get("ttl_h") is not None]
        rising = any(
            est.k_slope_per_h > 0.0
            for (pano_id, _), est in self._estimators.items()
            if pano_id == payload["pano_id"]
        )
        result = fusion.score(
            codes,
            {
                "k_ratio": worst_ratio,
                "k_rising": rising and self._frozen,
                "ttl_h": min(ttl_values) if ttl_values else None,
            },
            self._contracts_dir,
        )
        return {
            "score": result.score,
            "mode": result.mode,
            "ttl_h": result.ttl_h,
            "contributions": result.contributions,
        }
