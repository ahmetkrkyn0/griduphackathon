"""Risk motoru (TB2 Adim 4, Kisi B): telemetri ornegi -> aciklanabilir alarm kosullari.

Katmanlar (rapor 6.5):
  L-1..L3 tespit  -> KENAR (firmware C cekirdegi / panoalgo). Sonuc yukun `alarms` alaninda ve
                     nokta `q` veri kalitesi bitlerinde gelir. Merkez algoritmayi yeniden yazmaz;
                     merkezi dedektor (panoalgo) varsa yalnizca cagirir ve kodlari birlestirir.
  L4 aciklama     -> BURASI. Her kod icin: hangi nokta, hangi sinyal hangi esigi asti ("Neden?"),
                     hangi hipotezin onerisi ("Ne yapmali?"), sinira kalan sure ("Ne kadar acil?"),
                     o hipotezin HENUZ GORULMEYEN kaniti ("Ne dogrulanmali?" — karsi-olgusal aciklama).

Esik degerleri contracts/alarm-codes.yaml'dan okunur (`alarms[].threshold` -> `thresholds.*`);
burada yalnizca kodun yukteki HANGI alana baktigi yazilidir.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from typing import Any, Protocol

from .alarm_manager import Condition
from .api.views import point_state, point_validity
from .config import Contracts
from .models import Sample

DQ_PREFIX = "ALM-DQ-"  # nokta q bitleri yalnizca veri kalitesi kodlarini tasir (mqtt semasi t_conn[].q)
POINT_UNITS = {"dt_c": "K", "k_ratio": "K/K0", "ttl_h": "h"}
DAYS_TO_HOURS = 24.0

# kod -> (nokta alani, karsilastirma). Esik adi sozlesmede; *_days esikleri saate cevrilir.
POINT_LIMITS: dict[str, tuple[str, str]] = {
    "ALM-THR-TERM-WARN": ("dt_c", ">"),
    "ALM-THR-TERM-ALM": ("dt_c", ">"),
    "ALM-THR-BUS-ALM": ("dt_c", ">"),
    "ALM-K-WARN": ("k_ratio", ">"),
    "ALM-K-ALM": ("k_ratio", ">"),
    "ALM-TTL-14D": ("ttl_h", "<"),
}

_PHASE_POINT = re.compile(r"^(GIRIS|DSYA\d)_L[123]$")

Signal = dict[str, Any]


class CentralDetector(Protocol):
    """Merkezde calisan tespit (or. panoalgo.quality.check + limits.evaluate)."""

    def detect(self, payload: dict[str, Any], previous: dict[str, Any] | None) -> list[str]: ...


def signal(tag: str, value: float, threshold: float | None = None, unit: str | None = None) -> Signal:
    item: Signal = {"tag": tag, "value": float(value)}
    if threshold is not None:
        item["threshold"] = threshold
    if unit:
        item["unit"] = unit
    return item


def _exceeds(value: float, limit: float, op: str) -> bool:
    return value > limit if op == ">" else value < limit


class RiskEngine:
    def __init__(self, contracts: Contracts, detector: CentralDetector | None = None) -> None:
        self._contracts = contracts
        self._thresholds = contracts.thresholds
        self._detector = detector
        self._previous: dict[str, dict[str, Any]] = {}
        self._dq_bits = {
            alarm["bit"]: alarm["code"] for alarm in contracts.alarm_codes["alarms"] if alarm["code"].startswith(DQ_PREFIX)
        }
        hypotheses = contracts.alarm_codes["hypotheses"]
        self._hypothesis = {h["code"]: h for h in hypotheses}
        self._evidence_of: dict[str, list[dict[str, Any]]] = {}
        for hypothesis in hypotheses:
            for code in hypothesis["evidence"]:
                self._evidence_of.setdefault(code, []).append(hypothesis)
        self._panel_rules: dict[str, Callable[[dict[str, Any]], list[Signal]]] = {
            "ALM-DEW-WARN": lambda p: self._env_limit(p, "ALM-DEW-WARN", "td_margin_k", "<", "K"),
            "ALM-DEW-ALM": lambda p: self._env_limit(p, "ALM-DEW-ALM", "td_margin_k", "<", "K"),
            "ALM-PANEL-TEMP": lambda p: self._env_limit(p, "ALM-PANEL-TEMP", "t_up_c", ">", "degC"),
            "ALM-I-OVER": self._overcurrent,
            "ALM-NEUTRAL-THD": _neutral_harmonics,
            "ALM-ARC-TRIP": lambda p: _present(p, "tvoc", [("trips", None)]),
            "ALM-PROT-HEALTH": lambda p: _present(p, "tvoc", [("prot_health_ok", None), ("sensor_x2", None), ("sensor_x3", None)]),
            "ALM-PD-TREND": lambda p: _present(p, "pd", [("pps", None), ("amp_dbmv", "dBmV"), ("trend", None)]),
            "ALM-DOOR-UNAUTH": lambda p: _present(p, "env", [("door_open", None)]),
            "ALM-LASTGASP": lambda p: _present(p, "health", [("vbak_pct", "%")]),
            "ALM-NODE-LOST": _nodes,
        }

    def evaluate(self, sample: Sample) -> list[Condition]:
        payload = sample.payload
        codes = list(dict.fromkeys(payload.get("alarms") or []))
        if self._detector is not None:
            detected = self._detector.detect(payload, self._previous.get(sample.pano_id))
            codes.extend(code for code in detected if code not in codes)
        self._previous[sample.pano_id] = payload

        # "Ne dogrulanmali?" bu ornekte GORULEN kodlara gore hesaplanir: kenar listesi +
        # merkezi dedektor + nokta q bitlerinden cikan veri kalitesi kodlari.
        quality = self._dq_hits(payload)
        active = frozenset(codes) | {code for code, _ in quality}

        conditions: dict[tuple[str, str | None], Condition] = {}

        def add(items: Iterable[Condition]) -> None:
            for condition in items:
                conditions.setdefault((condition.code, condition.point), condition)

        add(self._quality_conditions(quality, payload, active))
        for code in codes:
            add(self._explain(code, payload, active))
        return list(conditions.values())

    def center_condition(self, code: str, signals: list[Signal]) -> Condition:
        """Merkezde uretilen kosul (or. ALM-COMMS-LOST): ayni aciklama ve oneri kurallariyla."""
        return self._condition(code, {}, point=None, signals=signals, active=frozenset({code}))

    # ------------------------------------------------------------- aciklama
    def _explain(self, code: str, payload: dict[str, Any], active: frozenset[str]) -> list[Condition]:
        if self._contracts.alarm(code) is None:
            return [Condition(code=code)]  # alarm yoneticisi sayar ve yok sayar
        if code in POINT_LIMITS:
            return self._point_limit(code, payload, active)
        if code == "ALM-THR-PHASE-DIF":
            return self._phase_difference(code, payload, active)
        if code.startswith(DQ_PREFIX):
            return [self._condition(code, payload, point=None, signals=[], active=active)]  # q biti olan nokta yoksa
        rule = self._panel_rules.get(code)
        return [self._condition(code, payload, point=None, signals=rule(payload) if rule else [], active=active)]

    def _condition(
        self,
        code: str,
        payload: dict[str, Any],
        point: dict[str, Any] | None,
        signals: list[Signal],
        active: frozenset[str],
    ) -> Condition:
        alarm = self._contracts.alarm(code)
        point_name = point["pt"] if point else None
        reason: dict[str, Any] = {"signals": signals, "layer": alarm["layer"], "point": point_name}
        if "basis" in alarm:
            reason["basis"] = alarm["basis"]
        hypothesis = self._dominant_hypothesis(code, payload)
        verify = _verify(hypothesis, active)
        if verify is not None:
            reason["verify"] = verify
        if point is not None:
            state = point_state(point, self._thresholds, comms_ok=True)
            baseline_day = (payload.get("health") or {}).get("baseline_day")
            reason["gecerlilik"] = point_validity(point, state, True, self._thresholds, baseline_day)
        ttl_h = point.get("ttl_h") if point else (payload.get("risk") or {}).get("ttl_h")
        advice = hypothesis["advice"] if hypothesis else None
        return Condition(code=code, point=point_name, reason=reason, advice=advice, ttl_h=ttl_h)

    def _threshold(self, code: str) -> float:
        name = self._contracts.alarm(code)["threshold"].removeprefix("thresholds.")
        value = self._thresholds[name]
        return value * DAYS_TO_HOURS if name.endswith("_days") else value

    def _point_limit(self, code: str, payload: dict[str, Any], active: frozenset[str]) -> list[Condition]:
        field, op = POINT_LIMITS[code]
        limit = self._threshold(code)
        candidates = [p for p in payload["t_conn"] if p.get(field) is not None]
        offending = [p for p in candidates if _exceeds(p[field], limit, op)]
        if not offending and candidates:  # kenar 1 s veriyle karar verdi: en yakin nokta
            offending = [(max if op == ">" else min)(candidates, key=lambda p: p[field])]
        if not offending:
            return [self._condition(code, payload, point=None, signals=[], active=active)]
        return [
            self._condition(
                code,
                payload,
                point,
                [signal(f"t_conn.{point['pt']}.{field}", point[field], limit, POINT_UNITS[field])],
                active,
            )
            for point in offending
        ]

    def _phase_difference(self, code: str, payload: dict[str, Any], active: frozenset[str]) -> list[Condition]:
        """Ayni grubun (GIRIS, DSYAn) L1/L2/L3 fazlari: en sicak faz, en soguk faz + esik ile kiyaslanir."""
        limit = self._threshold(code)
        groups: dict[str, list[dict[str, Any]]] = {}
        for point in payload["t_conn"]:
            match = _PHASE_POINT.match(point["pt"])
            if match:
                groups.setdefault(match[1], []).append(point)
        spreads = []
        for points in groups.values():
            if len(points) >= 2:
                hot, cold = max(points, key=lambda p: p["dt_c"]), min(points, key=lambda p: p["dt_c"])
                spreads.append((hot["dt_c"] - cold["dt_c"], hot, cold))
        if not spreads:
            return [self._condition(code, payload, point=None, signals=[], active=active)]
        offending = [s for s in spreads if s[0] > limit] or [max(spreads, key=lambda s: s[0])]
        return [
            self._condition(
                code,
                payload,
                hot,
                [
                    signal(f"t_conn.{hot['pt']}.dt_c", hot["dt_c"], cold["dt_c"] + limit, "K"),
                    signal(f"t_conn.{cold['pt']}.dt_c", cold["dt_c"], unit="K"),
                ],
                active,
            )
            for _, hot, cold in offending
        ]

    def _dq_hits(self, payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
        """Nokta q bitlerinden cikan veri kalitesi kodlari: (kod, nokta) ciftleri."""
        hits = []
        for point in payload["t_conn"]:
            q = point.get("q", 0)
            for bit, code in self._dq_bits.items():
                if q & (1 << bit):
                    hits.append((code, point))
        return hits

    def _quality_conditions(
        self, hits: list[tuple[str, dict[str, Any]]], payload: dict[str, Any], active: frozenset[str]
    ) -> list[Condition]:
        return [
            self._condition(code, payload, point, [signal(f"t_conn.{point['pt']}.t_c", point["t_c"], unit="degC")], active)
            for code, point in hits
        ]

    def _env_limit(self, payload: dict[str, Any], code: str, field: str, op: str, unit: str) -> list[Signal]:
        value = (payload.get("env") or {}).get(field)
        return [] if value is None else [signal(f"env.{field}", value, self._threshold(code), unit)]

    def _overcurrent(self, payload: dict[str, Any]) -> list[Signal]:
        rated = self._thresholds["rated_current_a"]["main_input"]  # MPR-53CS giris fiderinde
        limit = self._thresholds["current_alarm_ratio"] * rated
        phases = list(enumerate(payload["elec"]["i_ph"]))
        offending = [(i, a) for i, a in phases if a > limit] or [max(phases, key=lambda item: item[1])]
        return [signal(f"elec.i_ph.{i}", amps, limit, "A") for i, amps in offending]

    # ------------------------------------------------- oneri ve karsi-olgu
    def _dominant_hypothesis(self, code: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        """Kodun "Ne yapmali?" ve "Ne dogrulanmali?" bloklarinin dayandigi TEK hipotez.

        Kodun kaniti oldugu hipotezlerden kenarin baskin modu; yoksa en agir olani.
        Hicbir hipotezin kaniti olmayan kodda (or. 50 K terminal) baskin arizali mod.
        Iki blok ayni hipotezden turer: oneri bir hipoteze, eksik kanit baskasina ait olsaydi
        operator celiskili iki cumle okurdu."""
        mode = (payload.get("risk") or {}).get("mode")
        hypotheses = self._evidence_of.get(code)
        if hypotheses:
            dominant = next((h for h in hypotheses if h["code"] == mode), None)
            return dominant or max(hypotheses, key=lambda h: h["severity_w"])
        dominant = self._hypothesis.get(mode)
        return dominant if dominant and dominant["severity_w"] > 0 else None


def _verify(hypothesis: dict[str, Any] | None, active: frozenset[str]) -> dict[str, Any] | None:
    """'Ne dogrulanmali?': hipotezin sozlesmedeki kanitlarindan bu ornekte GORULMEYENLER.

    Karsi-olgusal aciklama (ISO 13379-1 semptom-ariza izinin ikinci yonu): eslesen kanit
    "neden" sorusunu, eksik kanit "neyi dogrularsam teshis kesinlesir" sorusunu cevaplar.
    Fuzyon skoru kanit orani uzerinden hesaplandigi icin (panoalgo.fusion.score) eksik kanit
    ayni zamanda skorun neden 100 olmadiginin aciklamasidir.

    Kenara EK ALAN ACILMAZ: mqtt-telemetry.schema.json additionalProperties: false, yeni alan
    mesaji reddettirirdi. Liste burada, hipotez tanimindan yeniden turetilir.
    `total` gonderilir, eslesen sayisi `total - len(missing)` ile arayuzde hesaplanir.
    """
    evidence = hypothesis.get("evidence") if hypothesis else None
    if not evidence:
        return None
    return {
        "hypothesis": hypothesis["code"],
        "missing": [code for code in evidence if code not in active],
        "total": len(evidence),
    }


def _present(payload: dict[str, Any], section: str, fields: list[tuple[str, str | None]]) -> list[Signal]:
    block = payload.get(section) or {}
    return [signal(f"{section}.{name}", block[name], unit=unit) for name, unit in fields if block.get(name) is not None]


def _neutral_harmonics(payload: dict[str, Any]) -> list[Signal]:
    elec = payload["elec"]
    signals = [signal("elec.i_n", elec["i_n"], unit="A")]
    signals += [signal(f"elec.thd_i.{i}", thd, unit="%") for i, thd in enumerate(elec.get("thd_i") or [])]
    return signals


def _nodes(payload: dict[str, Any]) -> list[Signal]:
    health = payload["health"]
    return [signal("health.nodes_ok", health["nodes_ok"], health.get("nodes_total"))]
