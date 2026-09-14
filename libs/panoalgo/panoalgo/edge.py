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

from . import fusion, limits, quality
from .detect import KIndexEstimator, lambda_for_period, load_thresholds
from .profiles import ProfileKind, load_profile

# Beklenen yuk profili icin gecmis I^2 ortalamasinin penceresi (ornek sayisi).
I2_MEAN_WINDOW = 720


class EdgePipeline:
    """Bir veya daha cok panonun telemetrisini zenginlestirir.

    Durum pano_id ile anahtarlanir: tek boru hatti yuk testindeki 1.000 sanal panoyu
    da besleyebilir.
    """

    def __init__(
        self,
        profile: ProfileKind = "karma",
        contracts_dir: Path | None = None,
    ) -> None:
        self._contracts_dir = contracts_dir
        self._profile: ProfileKind = profile
        self._quality = quality.QualityTracker(contracts_dir)
        self._reference_lam = float(load_thresholds(contracts_dir)["rls_lambda"])
        self._estimators: dict[tuple[str, str], KIndexEstimator] = {}
        self._i2_mean: dict[tuple[str, str], list[float]] = {}
        self._previous: dict[str, dict] = {}
        self._last_ts: dict[str, datetime] = {}
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

    # ------------------------------------------------------------------ adim

    def process(self, payload: dict) -> dict:
        """Yuku YERINDE zenginlestirir ve ayni sozlugu doner."""
        pano_id = payload["pano_id"]
        ts = datetime.fromisoformat(payload["ts"])
        period_s = self._period_s(pano_id, ts)

        self._update_points(payload, pano_id, ts, period_s)
        self._update_quality(payload)

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
        if last is None:
            return 0.0
        seconds = (ts - last).total_seconds()
        return seconds if seconds > 0.0 else 0.0

    def _update_points(self, payload: dict, pano_id: str, ts: datetime, period_s: float) -> None:
        for point in payload["t_conn"]:
            key = (pano_id, point["pt"])
            current = self._point_current(payload, point)
            self._remember_i2(key, current * current)

            estimator = self._estimators.get(key)
            if estimator is None:
                if period_s <= 0.0:
                    continue  # ilk ornek: periyot henuz bilinmiyor
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
                continue
            point["k"] = round(state.k, 12)
            point["k_ratio"] = round(state.k_ratio, 4)
            point["tau_s"] = round(state.tau_s, 1)
            point["ttl_h"] = None if state.ttl_h is None else round(state.ttl_h, 1)
            point["excited"] = state.excited

    def _point_current(self, payload: dict, point: dict) -> float:
        """Noktadan gecen akim; dT = K*I^2 iliskisinden K geri cozulur.

        Fider noktalarinda ana giris akiminin sabit bir kesri gecer; kesir bilinmedigi
        icin ana faz akimi kullanilir ve K kestirimi o kesri kendi icine emer. K/K0
        ORANI bundan etkilenmez — taban da ayni kesirle ogrenilir.
        """
        elec = payload["elec"]
        pt = point["pt"]
        if pt.endswith("_N"):
            return float(elec["i_n"])
        phase = int(pt[-1]) - 1
        return float(elec["i_ph"][phase])

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
