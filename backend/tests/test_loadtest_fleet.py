"""TB3 Adim 4 — loadtest/fleet.py yuk aracinin saf parcalari (canli olcum docs/09'da).

Yuk araci panoalgo gelene kadar sozlesmeye uyan SABLON yuk uretir (fizik degil, yuk); uretilen her mesajin
telemetri semasina uymasi ve alarm yukunun merkezin risk motorunca gercekten alarm olarak aciklanmasi burada
sinanir. Sayisal beklentiler elle hesaplanmistir.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import timedelta

import pytest
from jsonschema import Draft202012Validator

from app.ingest import IngestPipeline
from app.risk import RiskEngine
from fakes import MemoryStore
from helpers import REPO_ROOT, encode, utc

T0 = utc(2026, 9, 13, 10, 0, 0)


@pytest.fixture(scope="module")
def fleet():
    spec = importlib.util.spec_from_file_location("loadtest_fleet", REPO_ROOT / "loadtest" / "fleet.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclass annotation cozumu modulu sys.modules'ta arar
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(spec.name, None)


@pytest.fixture(scope="module")
def validator(contracts):
    return Draft202012Validator(contracts.telemetry_schema)


@pytest.mark.parametrize("points", [4, 7, 25])
def test_payloads_follow_telemetry_schema(fleet, contracts, validator, points):
    factory = fleet.PayloadFactory(contracts, points=points, seed=7)
    for seq in range(3):
        payload = factory.payload("SIM-00042", seq, T0 + timedelta(seconds=10 * seq))
        assert not list(validator.iter_errors(payload))
        assert (payload["pano_id"], payload["seq"], payload["ts"]) == ("SIM-00042", seq, (T0 + timedelta(seconds=10 * seq)).isoformat())
        assert len(payload["t_conn"]) == points


def test_normal_payloads_vary_without_alarms(fleet, contracts):
    factory = fleet.PayloadFactory(contracts, points=7, seed=1)
    payloads = [factory.payload("SIM-00001", seq, T0 + timedelta(seconds=10 * seq)) for seq in range(60)]
    l2 = [p["t_conn"][1]["dt_c"] for p in payloads]
    assert len(set(l2)) > 30  # donmus deger yok (ALM-DQ-FROZEN tetiklenmesin)
    assert all(0.0 < value < contracts.thresholds["term_rise_warn_k"] for value in l2)
    assert all(p["alarms"] == [] for p in payloads)


def test_alarm_payload_is_explained_as_k_alarm_by_the_risk_engine(fleet, contracts):
    """Yuk testindeki alarm gercek zinciri calistirmali: kenar kodu + esigi asan K/K0 -> P2 ALM-K-ALM @ GIRIS_L2."""
    payload = fleet.PayloadFactory(contracts, points=7, seed=1).payload("SIM-00001", 5, T0, alarm=True)
    store = MemoryStore()
    pipeline = IngestPipeline(contracts, store, clock=lambda: T0 + timedelta(seconds=1))
    pipeline.handle_message("gridup/pano/SIM-00001/tel", encode(payload))
    assert pipeline.flush() and not store.quarantined
    [sample] = store.batches[0][0]
    conditions = {(c.code, c.point) for c in RiskEngine(contracts).evaluate(sample)}
    assert ("ALM-K-ALM", "GIRIS_L2") in conditions
    assert contracts.prio_of("ALM-K-ALM") == "P2"  # SMS kanalini calistiran oncelik


def test_same_seed_same_fleet(fleet, contracts):
    first = fleet.PayloadFactory(contracts, points=7, seed=3).payload("SIM-00001", 0, T0)
    second = fleet.PayloadFactory(contracts, points=7, seed=3).payload("SIM-00001", 0, T0)
    assert first == second


def test_phase_offsets_spread_publishing_over_the_period(fleet):
    offsets = fleet.phase_offsets(1000, period_s=10.0, seed=11)
    assert len(offsets) == 1000 and all(0.0 <= value < 10.0 for value in offsets)
    per_second = [sum(1 for value in offsets if int(value) == second) for second in range(10)]
    assert min(per_second) > 60 and max(per_second) < 140  # beklenen 100/s; ani 1000 mesaj patlamasi yok


@pytest.mark.parametrize(
    "line,expected",
    [
        ('{"Name":"gridup-backend","CPUPerc":"12.34%","MemUsage":"123.4MiB / 7.667GiB"}', ("gridup-backend", 12.34, 123.4)),
        ('{"Name":"gridup-timescaledb","CPUPerc":"101.50%","MemUsage":"1.5GiB / 7.667GiB"}', ("gridup-timescaledb", 101.5, 1536.0)),
        ('{"Name":"gridup-mosquitto","CPUPerc":"0.00%","MemUsage":"512KiB / 7.667GiB"}', ("gridup-mosquitto", 0.0, 0.5)),
    ],
)
def test_parse_docker_stats(fleet, line, expected):
    assert fleet.parse_docker_stats(line) == expected


def test_latency_summary_uses_nearest_rank(fleet):
    values = [float(v) for v in range(1, 101)]  # 1..100 ms
    assert fleet.summarize(values) == {"n": 100, "p50": 50.0, "p95": 95.0, "max": 100.0}
    assert fleet.summarize([]) == {"n": 0}


def test_storage_projection(fleet):
    """100 B/satir, mesaj basina 86 satir, 10 s periyot: 100 pano -> 100 x 8640 x 86 x 100 B = 7,43 GB/gun."""
    projection = fleet.storage_projection(bytes_per_row=100.0, rows_per_message=86.0, period_s=10.0, panels=100)
    assert projection["messages_per_day"] == 864_000
    assert projection["rows_per_day"] == 74_304_000
    assert projection["gb_per_day"] == pytest.approx(7.4304, abs=1e-4)
