"""Kenar tespit boru hatti testleri — PLAN.md TA2 Adim 6 (birlestirme).

panoalgo'nun katmanlari tek tek test edildi; burasi KENARDA nasil birlestiklerini
dogrular: ham fizik yuku -> K kestirimi -> veri kalitesi -> esik karari -> fuzyon
-> semaya uyan zenginlestirilmis yuk.

Neden kenarda: backend/app/risk.py CentralDetector Protokolu yalnizca list[str]
kabul eder; k_ratio, ttl_h, q, risk.score merkeze SADECE telemetri yukunun
alanlariyla girebilir (mqtt-telemetry.schema.json t_conn[] ve risk bloklari).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from panoalgo.detect import time_to_limit
from panoalgo.edge import EdgePipeline
from panoalgo.generator import PanelSimulator

START = datetime(2026, 9, 14, 0, 0, tzinfo=timezone.utc)
STEP_S = 60.0


def _sim(seed: int = 42) -> PanelSimulator:
    return PanelSimulator(pano_id="SIM-00001", seed=seed, profile="karma", start=START)


def _run(pipeline: EdgePipeline, sim: PanelSimulator, steps: int) -> dict:
    payload = None
    for _ in range(steps):
        payload = pipeline.process(sim.step(STEP_S))
    return payload


def test_enriched_payload_still_matches_the_frozen_schema(assert_valid_telemetry):
    payload = _run(EdgePipeline(), _sim(), 200)
    assert_valid_telemetry(payload)


def test_pipeline_fills_the_thermal_index_for_every_point():
    payload = _run(EdgePipeline(), _sim(), 300)
    assert all(point["k"] > 0.0 for point in payload["t_conn"])


def test_healthy_panel_keeps_the_index_ratio_near_one(thresholds):
    """Taban dondurulduktan sonra saglikli panoda K/K0 uyari esigini gecmemeli."""
    pipeline = EdgePipeline()
    sim = _sim()
    _run(pipeline, sim, 400)
    pipeline.freeze_baselines()
    payload = _run(pipeline, sim, 400)

    worst = max(point["k_ratio"] for point in payload["t_conn"])
    assert worst < thresholds["k_ratio_warn"]


def test_healthy_panel_reports_no_alarms_and_normal_mode():
    pipeline = EdgePipeline()
    sim = _sim()
    _run(pipeline, sim, 400)
    pipeline.freeze_baselines()
    payload = _run(pipeline, sim, 200)

    assert payload["alarms"] == []
    assert payload["risk"]["mode"] == "HYP-NORMAL"
    assert payload["risk"]["score"] == 0


def test_a_degrading_connection_raises_the_index_ratio_and_the_alarm(thresholds):
    """S1'in cekirdegi: K buyur, K/K0 esigi gecer, ALM-K-ALM cikar."""
    pipeline = EdgePipeline()
    sim = _sim()
    _run(pipeline, sim, 400)
    pipeline.freeze_baselines()

    sim.set_k_multiplier("DSYA3_L2", 2.5)
    payload = _run(pipeline, sim, 900)

    point = next(p for p in payload["t_conn"] if p["pt"] == "DSYA3_L2")
    assert point["k_ratio"] > thresholds["k_ratio_alarm"]
    assert "ALM-K-ALM" in payload["alarms"]
    assert payload["risk"]["mode"] == "HYP-LOOSE-CONN"
    assert payload["risk"]["score"] > 0


def test_data_quality_is_reported_through_the_q_bit_field(alarm_codes):
    """Merkez q bitlerini okur (backend/app/risk.py:184-192); DQ kodu alarms[]
    listesine YAZILMAZ, yoksa merkez ayni ariza icin ikinci alarm acar."""
    bit = next(a["bit"] for a in alarm_codes["alarms"] if a["code"] == "ALM-DQ-BELOW-AMBIENT")
    pipeline = EdgePipeline()
    sim = _sim()
    _run(pipeline, sim, 200)

    sim.set_sensor_fault("DSYA6_L1", "dropped")
    payload = _run(pipeline, sim, 20)

    point = next(p for p in payload["t_conn"] if p["pt"] == "DSYA6_L1")
    assert point["q"] & (1 << bit)
    assert not [c for c in payload["alarms"] if c.startswith("ALM-DQ-")]


def test_ttl_is_suppressed_when_the_point_quality_is_suspect():
    """S8 bilinen siniri (docs/05 #10): q biti set olan bir nokta artik canli bir
    ttl_h gostermemeli. time_to_limit'in kendisi (test_detect.py:40-50'deki ayni
    hesap) once gercek, pozitif bir tahmin urettigini kanitlar; bu test o gercek
    degerin q set olunca None'a cekildigini, q=0 iken dokunulmadan kaldigini dogrular."""
    ttl = time_to_limit(k_now=2.0e-4, k_slope_per_h=1.0e-5, expected_i2=lambda _h: 250_000.0, limit_k=70.0, step_h=0.25)
    assert ttl == pytest.approx(8.0, abs=0.3)  # on-kosul: gercekten pozitif bir tahmin

    pipeline = EdgePipeline()
    payload = {"t_conn": [{"pt": "DSYA3_L2", "ttl_h": ttl, "q": 0}]}

    pipeline._suppress_ttl_when_quality_suspect(payload)
    assert payload["t_conn"][0]["ttl_h"] == ttl  # q=0: degismez

    payload["t_conn"][0]["q"] = 1
    pipeline._suppress_ttl_when_quality_suspect(payload)
    assert payload["t_conn"][0]["ttl_h"] is None  # q != 0: ASIL IDDIA


def test_process_wires_the_suppression_into_the_pipeline(monkeypatch):
    """Onceki test _suppress_ttl_when_quality_suspect'i DOGRUDAN cagirir; bu test
    process()'in onu GERCEKTEN cagirdigini kanitlar (edge.py:111). Bu satir
    silinirse (metodun kendisi degil, cagrisi) yukaridaki test hala gecer ama
    S8 korumasi devre disi kalir -- bu test o bosluk icin.

    _update_points de sahtelenir: saglikli simulasyonda K/K0 hicbir zaman surekli
    yukselmez (bkz. detect.py _slope_is_persistent), yani gercek boru hattinda
    ttl_h zaten hep None olur ve line 111 silinse bile bu test yanlislikla YESIL
    kalirdi. Burada her noktaya GERCEK (bastirilmasi gereken) bir ttl_h degeri
    yazdirilir ki test yalnizca bastirmanin CAGRILDIGINI degil, cagrilmadiginda
    GERCEKTEN kirildigini da kanitlasin."""
    pipeline, sim = EdgePipeline(), _sim()
    _run(pipeline, sim, 200)

    def _fake_update_points(self, payload, pano_id, ts, period_s):
        for point in payload["t_conn"]:
            point["ttl_h"] = 5.0

    monkeypatch.setattr(EdgePipeline, "_update_points", _fake_update_points)
    monkeypatch.setattr(
        EdgePipeline,
        "_update_quality",
        lambda self, payload: [p.__setitem__("q", 1) for p in payload["t_conn"]] and None,
    )
    payload = _run(pipeline, sim, 1)
    assert all(p["ttl_h"] is None for p in payload["t_conn"])
    assert payload["risk"]["ttl_h"] is None
    assert "ALM-TTL-14D" not in payload["alarms"]


def test_alarm_codes_are_all_defined_in_the_contract(alarm_codes):
    known = {a["code"] for a in alarm_codes["alarms"]}
    pipeline = EdgePipeline()
    sim = _sim()
    _run(pipeline, sim, 300)
    pipeline.freeze_baselines()
    sim.set_k_multiplier("GIRIS_L1", 4.0)
    payload = _run(pipeline, sim, 600)

    assert set(payload["alarms"]) <= known


def test_pipeline_never_emits_the_centre_owned_comms_alarm():
    pipeline = EdgePipeline()
    payload = _run(pipeline, _sim(), 100)
    assert "ALM-COMMS-LOST" not in payload["alarms"]


def test_pipeline_keeps_state_per_panel():
    """Tek boru hatti birden cok pano besleyebilir (yuk testi 1000 pano)."""
    pipeline = EdgePipeline()
    one, two = _sim(seed=1), PanelSimulator(
        pano_id="SIM-00002", seed=2, profile="konut", start=START
    )
    for _ in range(300):
        a = pipeline.process(one.step(STEP_S))
        b = pipeline.process(two.step(STEP_S))

    assert a["pano_id"] != b["pano_id"]
    assert a["t_conn"][0]["k"] != b["t_conn"][0]["k"]


def test_pipeline_is_deterministic_for_the_same_seed():
    first = _run(EdgePipeline(), _sim(seed=9), 200)
    second = _run(EdgePipeline(), _sim(seed=9), 200)
    assert first == second


def test_payload_remains_json_serialisable_without_nan():
    import json

    payload = _run(EdgePipeline(), _sim(), 300)
    json.dumps(payload, allow_nan=False)


def test_pipeline_can_be_told_its_sampling_period():
    """Kenar kendi periyodunu bilir; damgalardan cikarmak titreme ve backfill'de
    yanlis periyot verir.

    Periyodun gercekten KULLANILDIGI, tau uzerinden olculur: tau = -Ts/ln(a), yani
    ayni veriye farkli periyot denirse tau orantili olarak degisir.

    Bu, C host ikilisiyle esitligin de sartidir — firmware periyodu konfigurasyondan
    alir, damgadan cikarmaz. Olculdu: hizalanmadan once gercek uretec verisinde 25
    noktada K/K0 farki 0,033'e cikiyordu, hizalandiktan sonra 0,0004 (register
    kuantizasyonunun kendisi).
    """
    def tau_after(period_s: float) -> float:
        pipeline = EdgePipeline(period_s=period_s)
        sim = _sim(seed=5)
        for _ in range(200):
            payload = pipeline.process(sim.step(STEP_S))
        return payload["t_conn"][0]["tau_s"]

    assert tau_after(STEP_S * 10.0) > tau_after(STEP_S) * 5.0


def test_pipeline_never_publishes_the_generator_ground_truth():
    """Uretec kendi GERCEK K'sini yuke yazar; kestirim yokken bu deger yukte
    KALMAMALI. Aksi halde kenar, olcemeyecegi bir dogruyu yayinlamis olur —
    demoda da savunmada da kabul edilemez."""
    payload = EdgePipeline().process(_sim().step(STEP_S))
    for point in payload["t_conn"]:
        assert "k" not in point
        assert "k_ratio" not in point
