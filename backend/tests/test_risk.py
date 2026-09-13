"""TB2 Adim 4 — risk motoru: telemetri ornegi -> aciklanabilir alarm kosullari (app.risk).

Tespit KENARDA yapilir (firmware/panoalgo) ve yukun `alarms` alaninda gelir; merkez bu kodlari
noktalara baglar ve arayuzun "Neden?" (sinyal + esik), "Ne yapmali?" (hipotez onerisi) ve
"Ne kadar acil?" (ttl_h) bolumlerini doldurur. A'nin algoritmasi yeniden yazilmaz: merkezi
dedektor (panoalgo) varsa yalnizca cagrilir.

Beklenen degerler tests/fixtures/tel_valid.json'dan elle cikarilmistir; esikler sozlesmeden okunur.
"""

from __future__ import annotations

import copy
from datetime import timedelta

import pytest

from app.ingest import IngestPipeline
from app.risk import RiskEngine
from fakes import MemoryStore
from helpers import encode, utc

RX = utc(2026, 9, 13, 10, 0, 2)


def to_sample(contracts, payload: dict):
    """Ornegi uretimdeki gibi ingest ayristiricisindan gecirir (sema + ts denetimi dahil)."""
    store = MemoryStore()
    pipeline = IngestPipeline(contracts, store, clock=lambda: RX)
    pipeline.handle_message(f"gridup/pano/{payload['pano_id']}/tel", encode(payload))
    assert pipeline.flush()
    assert not store.quarantined, f"test yuku semaya uymuyor: {store.quarantined[0][2]}"
    [batch] = store.batches
    [sample] = batch[0]
    return sample


def by_key(conditions) -> dict:
    return {(c.code, c.point): c for c in conditions}


def hypothesis(contracts, code: str) -> dict:
    return next(h for h in contracts.alarm_codes["hypotheses"] if h["code"] == code)


@pytest.fixture
def engine(contracts) -> RiskEngine:
    return RiskEngine(contracts)


def test_edge_alarm_is_attached_to_the_point_that_exceeds_its_threshold(engine, contracts, tel_payload):
    conditions = by_key(engine.evaluate(to_sample(contracts, tel_payload)))

    term = conditions[("ALM-THR-TERM-WARN", "GIRIS_L2")]
    assert term.reason["signals"] == [
        {"tag": "t_conn.GIRIS_L2.dt_c", "value": 53.0, "threshold": contracts.thresholds["term_rise_warn_k"], "unit": "K"}
    ]
    assert (term.reason["layer"], term.reason["point"]) == ("L0", "GIRIS_L2")
    assert term.reason["basis"] == contracts.alarm("ALM-THR-TERM-WARN")["basis"]

    k_warn = conditions[("ALM-K-WARN", "GIRIS_L2")]
    assert k_warn.reason["signals"] == [
        {"tag": "t_conn.GIRIS_L2.k_ratio", "value": 1.45, "threshold": contracts.thresholds["k_ratio_warn"], "unit": "K/K0"}
    ]
    assert k_warn.ttl_h == 150.5
    assert set(conditions) == {("ALM-THR-TERM-WARN", "GIRIS_L2"), ("ALM-K-WARN", "GIRIS_L2")}


def test_every_point_over_the_threshold_gets_its_own_condition(engine, contracts, tel_payload):
    tel_payload["t_conn"][4]["k_ratio"] = 1.52  # DSYA3_L2 (ttl_h tahmini yok)
    tel_payload["t_conn"][0]["k_ratio"] = contracts.thresholds["k_ratio_warn"]  # GIRIS_L1 tam esikte: "ustu" degil

    conditions = by_key(engine.evaluate(to_sample(contracts, tel_payload)))

    assert {point for code, point in conditions if code == "ALM-K-WARN"} == {"GIRIS_L2", "DSYA3_L2"}
    assert conditions[("ALM-K-WARN", "GIRIS_L2")].ttl_h == 150.5
    assert conditions[("ALM-K-WARN", "DSYA3_L2")].ttl_h is None  # panonun ttl_h'si baska noktanin


def test_edge_alarm_without_an_offending_point_goes_to_the_closest_point(engine, contracts, tel_payload):
    """Kenar 1 s veriyle karar verir; 10 s ozette esik altinda kalsa da alarm kimligi kaymaz."""
    tel_payload["t_conn"][1]["k_ratio"] = 1.28  # GIRIS_L2, esigin hemen alti
    tel_payload["alarms"] = ["ALM-K-WARN"]

    [condition] = engine.evaluate(to_sample(contracts, tel_payload))

    assert (condition.code, condition.point) == ("ALM-K-WARN", "GIRIS_L2")
    assert condition.reason["signals"][0]["value"] == 1.28


def test_time_to_limit_threshold_is_converted_from_days_to_hours(engine, contracts, tel_payload):
    tel_payload["alarms"] = ["ALM-TTL-14D"]

    [condition] = engine.evaluate(to_sample(contracts, tel_payload))

    assert condition.point == "GIRIS_L2"
    assert condition.reason["signals"] == [
        {"tag": "t_conn.GIRIS_L2.ttl_h", "value": 150.5, "threshold": contracts.thresholds["ttl_warn_days"] * 24, "unit": "h"}
    ]


def test_time_to_limit_without_offending_point_goes_to_the_soonest_point(engine, contracts, tel_payload):
    tel_payload["t_conn"][1]["ttl_h"] = 400.0  # GIRIS_L2
    tel_payload["t_conn"][4]["ttl_h"] = 520.0  # DSYA3_L2
    tel_payload["alarms"] = ["ALM-TTL-14D"]

    [condition] = engine.evaluate(to_sample(contracts, tel_payload))

    assert (condition.point, condition.ttl_h) == ("GIRIS_L2", 400.0)


def test_panel_level_alarm_uses_environment_signal_without_point(engine, contracts, tel_payload):
    tel_payload["env"]["td_margin_k"] = 2.1
    tel_payload["alarms"] = ["ALM-DEW-WARN"]

    [condition] = engine.evaluate(to_sample(contracts, tel_payload))

    assert condition.point is None
    assert condition.reason["signals"] == [
        {"tag": "env.td_margin_k", "value": 2.1, "threshold": contracts.thresholds["dew_margin_warn_k"], "unit": "K"}
    ]
    assert condition.ttl_h == 150.5  # pano duzeyinde alarm: kenarin risk.ttl_h tahmini


def test_overcurrent_threshold_is_the_rated_main_input_current(engine, contracts, tel_payload):
    tel_payload["elec"]["i_ph"] = [2350.0, 2290.0, 2410.0]
    tel_payload["alarms"] = ["ALM-I-OVER"]

    [condition] = engine.evaluate(to_sample(contracts, tel_payload))

    limit = contracts.thresholds["current_alarm_ratio"] * contracts.thresholds["rated_current_a"]["main_input"]
    assert condition.reason["signals"] == [
        {"tag": "elec.i_ph.0", "value": 2350.0, "threshold": limit, "unit": "A"},
        {"tag": "elec.i_ph.2", "value": 2410.0, "threshold": limit, "unit": "A"},
    ]


def test_phase_difference_names_the_hot_phase_against_the_coldest_one(engine, contracts, tel_payload):
    tel_payload["t_conn"] = [
        {"pt": "DSYA3_L1", "t_c": 46.0, "dt_c": 21.0},
        {"pt": "DSYA3_L2", "t_c": 63.0, "dt_c": 38.0},
        {"pt": "DSYA3_L3", "t_c": 47.5, "dt_c": 22.5},
        {"pt": "GIRIS_L1", "t_c": 45.0, "dt_c": 20.0},
        {"pt": "GIRIS_L2", "t_c": 47.0, "dt_c": 22.0},
        {"pt": "GIRIS_N", "t_c": 27.0, "dt_c": 2.0},  # notr faz degildir: 22 - 2 = 20 K "fark" sayilmamali
    ]
    tel_payload["alarms"] = ["ALM-THR-PHASE-DIF"]

    [condition] = engine.evaluate(to_sample(contracts, tel_payload))

    assert condition.point == "DSYA3_L2"
    assert condition.reason["signals"] == [
        {"tag": "t_conn.DSYA3_L2.dt_c", "value": 38.0, "threshold": 21.0 + contracts.thresholds["phase_diff_alarm_k"], "unit": "K"},
        {"tag": "t_conn.DSYA3_L1.dt_c", "value": 21.0, "unit": "K"},
    ]


def _set(payload: dict, path: str, value) -> None:
    *parents, leaf = path.split(".")
    node = payload
    for part in parents:
        node = node[int(part)] if part.isdigit() else node[part]
    node[int(leaf) if leaf.isdigit() else leaf] = value


@pytest.mark.parametrize(
    "code,changes,point,signals",
    [
        ("ALM-THR-TERM-ALM", {"t_conn.1.dt_c": 75.0}, "GIRIS_L2",
         [{"tag": "t_conn.GIRIS_L2.dt_c", "value": 75.0, "threshold": 70, "unit": "K"}]),
        ("ALM-THR-BUS-ALM", {"t_conn.1.dt_c": 110.0}, "GIRIS_L2",
         [{"tag": "t_conn.GIRIS_L2.dt_c", "value": 110.0, "threshold": 105, "unit": "K"}]),
        ("ALM-K-ALM", {"t_conn.1.k_ratio": 1.7}, "GIRIS_L2",
         [{"tag": "t_conn.GIRIS_L2.k_ratio", "value": 1.7, "threshold": 1.6, "unit": "K/K0"}]),
        ("ALM-DEW-ALM", {"env.td_margin_k": 0.6}, None,
         [{"tag": "env.td_margin_k", "value": 0.6, "threshold": 1.0, "unit": "K"}]),
        ("ALM-PANEL-TEMP", {"env.t_up_c": 46.5}, None,
         [{"tag": "env.t_up_c", "value": 46.5, "threshold": 45, "unit": "degC"}]),
        ("ALM-ARC-TRIP", {"tvoc.trips": 1}, None, [{"tag": "tvoc.trips", "value": 1.0}]),
        ("ALM-PROT-HEALTH", {"tvoc.prot_health_ok": False, "tvoc.sensor_x2": 0}, None,
         [{"tag": "tvoc.prot_health_ok", "value": 0.0}, {"tag": "tvoc.sensor_x2", "value": 0.0},
          {"tag": "tvoc.sensor_x3", "value": 2.0}]),
        ("ALM-NEUTRAL-THD", {"elec.i_n": 160.0}, None,
         [{"tag": "elec.i_n", "value": 160.0, "unit": "A"}, {"tag": "elec.thd_i.0", "value": 4.1, "unit": "%"},
          {"tag": "elec.thd_i.1", "value": 4.3, "unit": "%"}, {"tag": "elec.thd_i.2", "value": 3.9, "unit": "%"}]),
        ("ALM-PD-TREND", {"pd": {"pps": 140.0, "amp_dbmv": 31.0, "trend": 2.4}}, None,
         [{"tag": "pd.pps", "value": 140.0}, {"tag": "pd.amp_dbmv", "value": 31.0, "unit": "dBmV"},
          {"tag": "pd.trend", "value": 2.4}]),
        ("ALM-NODE-LOST", {"health.nodes_ok": 3}, None,
         [{"tag": "health.nodes_ok", "value": 3.0, "threshold": 5.0}]),
        ("ALM-DOOR-UNAUTH", {"env.door_open": True}, None, [{"tag": "env.door_open", "value": 1.0}]),
        ("ALM-LASTGASP", {"health.vbak_pct": 97.0}, None, [{"tag": "health.vbak_pct", "value": 97.0, "unit": "%"}]),
        ("ALM-DQ-JUMP", {}, None, []),  # kenar listesinde ama hicbir noktanin q biti yok
    ],
)
def test_signals_explaining_each_edge_alarm(engine, contracts, tel_payload, code, changes, point, signals):
    """Esik degerleri alarm-codes.yaml ile elle eslestirildi (70/105/1.6/1.0/45 ...)."""
    tel_payload["alarms"] = [code]
    tel_payload["health"]["nodes_total"] = 5
    for path, value in changes.items():
        _set(tel_payload, path, value)

    [condition] = engine.evaluate(to_sample(contracts, tel_payload))

    assert (condition.code, condition.point) == (code, point)
    assert condition.reason["signals"] == signals
    assert condition.reason["layer"] == contracts.alarm(code)["layer"]


def test_quality_bits_raise_data_quality_alarms_on_that_point(engine, contracts, tel_payload):
    frozen, below = contracts.alarm("ALM-DQ-FROZEN")["bit"], contracts.alarm("ALM-DQ-BELOW-AMBIENT")["bit"]
    tel_payload["alarms"] = []
    tel_payload["t_conn"][3]["q"] = (1 << frozen) | (1 << below)  # GIRIS_N, t_c 27.1
    tel_payload["t_conn"][0]["q"] = 1 << contracts.alarm("ALM-THR-BUS-ALM")["bit"]  # veri kalitesi biti degil

    conditions = by_key(engine.evaluate(to_sample(contracts, tel_payload)))

    assert set(conditions) == {("ALM-DQ-FROZEN", "GIRIS_N"), ("ALM-DQ-BELOW-AMBIENT", "GIRIS_N")}
    assert conditions[("ALM-DQ-FROZEN", "GIRIS_N")].reason["signals"] == [
        {"tag": "t_conn.GIRIS_N.t_c", "value": 27.1, "unit": "degC"}
    ]
    assert conditions[("ALM-DQ-FROZEN", "GIRIS_N")].reason["layer"] == "L-1"


def test_advice_prefers_the_dominant_hypothesis_reported_by_the_edge(engine, contracts, tel_payload):
    """ALM-PD-TREND iki hipotezin kaniti: kenarin baskin modu hangisiyse onun onerisi."""
    tel_payload["pd"] = {"pps": 140.0, "amp_dbmv": 31.0, "trend": 2.4}
    tel_payload["alarms"] = ["ALM-PD-TREND"]
    tel_payload["risk"] = {"score": 44, "mode": "HYP-CONDENSE", "ttl_h": None, "contributions": {}}

    [condensation] = engine.evaluate(to_sample(contracts, tel_payload))

    tel_payload["risk"]["mode"] = "HYP-NORMAL"
    tel_payload["seq"] += 1
    [no_mode] = engine.evaluate(to_sample(contracts, tel_payload))

    assert condensation.advice == hypothesis(contracts, "HYP-CONDENSE")["advice"]
    assert no_mode.advice == hypothesis(contracts, "HYP-PD")["advice"]  # en yuksek severity_w


def test_alarm_that_is_evidence_of_no_hypothesis_takes_the_dominant_mode_advice(engine, contracts, tel_payload):
    tel_payload["alarms"] = ["ALM-THR-TERM-WARN"]

    [condition] = engine.evaluate(to_sample(contracts, tel_payload))
    assert condition.advice == hypothesis(contracts, "HYP-LOOSE-CONN")["advice"]

    tel_payload["risk"] = {"score": 5, "mode": "HYP-NORMAL", "ttl_h": None, "contributions": {}}
    [condition] = engine.evaluate(to_sample(contracts, tel_payload))
    assert condition.advice is None


def test_central_detector_codes_are_merged_with_edge_codes(contracts, tel_payload):
    calls = []

    class Detector:
        def detect(self, payload: dict, previous: dict | None) -> list[str]:
            calls.append((payload["seq"], previous and previous["seq"]))
            return ["ALM-K-WARN", "ALM-DEW-ALM"]

    engine = RiskEngine(contracts, detector=Detector())
    tel_payload["env"]["td_margin_k"] = 0.6
    engine.evaluate(to_sample(contracts, tel_payload))
    tel_payload["seq"] += 1
    tel_payload["ts"] = (utc(2026, 9, 13, 10, 0, 0) + timedelta(seconds=10)).isoformat()

    conditions = by_key(engine.evaluate(to_sample(contracts, tel_payload)))

    assert set(conditions) == {("ALM-THR-TERM-WARN", "GIRIS_L2"), ("ALM-K-WARN", "GIRIS_L2"), ("ALM-DEW-ALM", None)}
    assert calls == [(42, None), (43, 42)]


def test_payload_without_edge_alarms_and_clean_quality_yields_nothing(engine, contracts, tel_payload):
    payload = copy.deepcopy(tel_payload)
    del payload["alarms"]
    for point in payload["t_conn"]:
        point["q"] = 0

    assert engine.evaluate(to_sample(contracts, payload)) == []
