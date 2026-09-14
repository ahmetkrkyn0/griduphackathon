"""TB1 — MQTT ingestion: dogrulama, uzun formata duzlestirme, karantina, toplu yazma."""

from __future__ import annotations

import copy
import json
import time

import pytest

from app.ingest import IngestPipeline
from helpers import encode, utc
from fakes import MemoryStore

TOPIC = "gridup/pano/ADM-00001/tel"
RX = utc(2026, 9, 13, 10, 0, 2)

# Fixture'daki 5 noktali yukten ELLE cikarilmis beklenen satirlar: etiket -> (deger, q).
# Kural: her sayisal/boolean yaprak bir etiket; null, metin ve risk.contributions yazilmaz;
# nokta kalite bayragi (q) ayri etiket degil, o noktanin satirlarinin q sutunudur.
EXPECTED_ROWS = {
    "t_conn.GIRIS_L1.t_c": (41.5, 0),
    "t_conn.GIRIS_L1.dt_c": (16.5, 0),
    "t_conn.GIRIS_L1.k": (0.000103, 0),
    "t_conn.GIRIS_L1.k_ratio": (1.02, 0),
    "t_conn.GIRIS_L1.tau_s": (910.0, 0),
    "t_conn.GIRIS_L1.excited": (1.0, 0),
    "t_conn.GIRIS_L2.t_c": (78.0, 0),
    "t_conn.GIRIS_L2.dt_c": (53.0, 0),
    "t_conn.GIRIS_L2.k": (0.000171, 0),
    "t_conn.GIRIS_L2.k_ratio": (1.45, 0),
    "t_conn.GIRIS_L2.tau_s": (880.0, 0),
    "t_conn.GIRIS_L2.ttl_h": (150.5, 0),
    "t_conn.GIRIS_L2.excited": (1.0, 0),
    "t_conn.GIRIS_L3.t_c": (40.9, 0),
    "t_conn.GIRIS_L3.dt_c": (15.9, 0),
    "t_conn.GIRIS_L3.k": (0.0001, 0),
    "t_conn.GIRIS_L3.k_ratio": (0.99, 0),
    "t_conn.GIRIS_L3.tau_s": (905.0, 0),
    "t_conn.GIRIS_L3.excited": (1.0, 0),
    "t_conn.GIRIS_N.t_c": (27.1, 4),
    "t_conn.GIRIS_N.dt_c": (2.1, 4),
    "t_conn.DSYA3_L2.t_c": (48.2, 0),
    "t_conn.DSYA3_L2.dt_c": (23.2, 0),
    "t_conn.DSYA3_L2.k": (0.00012, 0),
    "t_conn.DSYA3_L2.k_ratio": (1.1, 0),
    "t_conn.DSYA3_L2.tau_s": (900.0, 0),
    "t_conn.DSYA3_L2.excited": (0.0, 0),
    "elec.i_ph.0": (400.0, 0),
    "elec.i_ph.1": (420.0, 0),
    "elec.i_ph.2": (388.0, 0),
    "elec.i_n": (48.0, 0),
    "elec.u_ph.0": (231.2, 0),
    "elec.u_ph.1": (230.8, 0),
    "elec.u_ph.2": (232.0, 0),
    "elec.thd_i.0": (4.1, 0),
    "elec.thd_i.1": (4.3, 0),
    "elec.thd_i.2": (3.9, 0),
    "elec.cosphi": (0.96, 0),
    "elec.unbal_pct": (4.1, 0),
    "env.t_low_c": (25.0, 0),
    "env.rh_low_pct": (60.0, 0),
    "env.td_low_c": (16.7, 0),
    "env.td_margin_k": (8.3, 0),
    "env.t_up_c": (31.5, 0),
    "env.rh_up_pct": (52.0, 0),
    "env.dt_air_k": (6.5, 0),
    "env.door_open": (0.0, 0),
    "tvoc.state": (1.0, 0),
    "tvoc.trips": (0.0, 0),
    "tvoc.det_bits_low": (0.0, 0),
    "tvoc.det_bits_high": (0.0, 0),
    "tvoc.sensor_x2": (2.0, 0),
    "tvoc.sensor_x3": (2.0, 0),
    "tvoc.amb_light_x2": (12.0, 0),
    "tvoc.amb_light_x3": (15.0, 0),
    "tvoc.prot_health_ok": (1.0, 0),
    "tvoc.comm_ok": (1.0, 0),
    "risk.score": (38.0, 0),
    "risk.ttl_h": (150.5, 0),
    "health.uptime_s": (86400.0, 0),
    "health.nodes_ok": (5.0, 0),
    "health.nodes_total": (5.0, 0),
    "health.rssi_dbm": (-71.0, 0),
    "health.vbak_pct": (100.0, 0),
    "health.buffered": (0.0, 0),
    "health.maint_mode": (0.0, 0),
    "health.baseline_day": (7.0, 0),
}


@pytest.fixture
def store() -> MemoryStore:
    return MemoryStore()


@pytest.fixture
def pipeline(contracts, store) -> IngestPipeline:
    return IngestPipeline(contracts, store, clock=lambda: RX)


def test_valid_telemetry_is_flattened_into_long_format_rows(pipeline, store, tel_payload):
    pipeline.handle_message(TOPIC, encode(tel_payload))
    pipeline.flush()

    assert len(store.telemetry) == 67  # tekrar eden etiket yok
    got = {tag: (value, q) for (_, _, tag, value, q) in store.telemetry}
    assert got == EXPECTED_ROWS
    assert {(ts, pano) for (ts, pano, *_rest) in store.telemetry} == {
        (utc(2026, 9, 13, 10, 0, 0), "ADM-00001")
    }


def test_accepted_sample_carries_payload_and_receive_time(pipeline, store, tel_payload):
    pipeline.handle_message(TOPIC, encode(tel_payload))
    pipeline.flush()

    [(samples, rejections)] = store.batches
    assert rejections == []
    [sample] = samples
    assert sample.pano_id == "ADM-00001"
    assert sample.seq == 42
    assert sample.received_at == RX
    assert sample.payload == tel_payload
    assert pipeline.stats["written"] == 1


def test_event_topic_uses_same_schema(pipeline, store, tel_payload):
    pipeline.handle_message("gridup/pano/ADM-00001/evt", encode(tel_payload))
    pipeline.flush()

    assert len(store.telemetry) == 67
    assert store.quarantined == []


def test_schema_violation_is_quarantined_not_dropped(pipeline, store, tel_payload):
    del tel_payload["elec"]

    pipeline.handle_message(TOPIC, encode(tel_payload))
    pipeline.flush()

    assert store.telemetry == []
    [(received, topic, reason, raw)] = store.quarantined
    assert (received, topic, raw) == (RX, TOPIC, tel_payload)
    assert "elec" in reason
    assert pipeline.stats["rejected"] == 1


def test_malformed_json_is_quarantined_with_raw_text(pipeline, store):
    pipeline.handle_message(TOPIC, b"{bozuk json")
    pipeline.flush()

    [(_, _, reason, raw)] = store.quarantined
    assert "JSON" in reason
    assert raw == {"raw_text": "{bozuk json"}


def test_nan_is_rejected_because_api_cannot_serialize_it(pipeline, store, tel_payload):
    text = json.dumps(tel_payload).replace('"k_ratio": 1.45', '"k_ratio": NaN')
    assert "NaN" in text

    pipeline.handle_message(TOPIC, text.encode())
    pipeline.flush()

    assert store.telemetry == []
    [(_, _, reason, _)] = store.quarantined
    assert "NaN" in reason


def test_payload_pano_id_must_match_topic(pipeline, store, tel_payload):
    pipeline.handle_message("gridup/pano/ADM-00002/tel", encode(tel_payload))
    pipeline.flush()

    assert store.telemetry == []
    [(_, _, reason, _)] = store.quarantined
    assert "ADM-00002" in reason and "ADM-00001" in reason


def test_timestamp_without_timezone_is_quarantined(pipeline, store, tel_payload):
    tel_payload["ts"] = "2026-09-13T10:00:00"

    pipeline.handle_message(TOPIC, encode(tel_payload))
    pipeline.flush()

    assert store.telemetry == []
    [(_, _, reason, _)] = store.quarantined
    assert "ts" in reason


def test_oversized_message_is_quarantined_without_parsing(contracts, store):
    pipeline = IngestPipeline(contracts, store, clock=lambda: RX, max_message_bytes=100)

    pipeline.handle_message(TOPIC, b"x" * 101)
    pipeline.flush()

    [(_, _, reason, raw)] = store.quarantined
    assert "101" in reason
    assert raw == {"raw_text": "x" * 100, "truncated": True}


def test_failed_write_keeps_batch_for_retry(pipeline, store, tel_payload):
    store.fail_writes = 1
    pipeline.handle_message(TOPIC, encode(tel_payload))

    assert pipeline.flush() is False
    assert store.telemetry == []
    assert pipeline.stats["write_errors"] == 1

    assert pipeline.flush() is True
    assert len(store.telemetry) == 67
    assert pipeline.stats["written"] == 1


def test_data_error_is_isolated_to_the_offending_message(pipeline, store, tel_payload):
    """Veri hatasi tekrar denemekle gecmez; tek bozuk mesaj tum partiyi (tum filoyu) yakmamali."""
    bad = copy.deepcopy(tel_payload)
    bad["pano_id"] = "ADM-00002"
    store.poison_pano = "ADM-00002"
    pipeline.handle_message(TOPIC, encode(tel_payload))
    pipeline.handle_message("gridup/pano/ADM-00002/tel", encode(bad))

    assert pipeline.flush() is True  # yeniden denenecek bir sey kalmadi

    assert {pano for (_, pano, *_rest) in store.telemetry} == {"ADM-00001"}
    assert (pipeline.stats["written"], pipeline.stats["dropped"]) == (1, 1)


def test_nul_character_is_quarantined_in_storable_form(pipeline, store, tel_payload):
    """PostgreSQL text/JSONB NUL kabul etmez: ham yuk bile karantinaya yazilamazdi."""
    tel_payload["fw"] = "0.1\u0000"

    pipeline.handle_message(TOPIC, encode(tel_payload))
    pipeline.flush()

    assert store.telemetry == []
    [(_, _, reason, raw)] = store.quarantined
    assert "NUL" in reason
    assert "\x00" not in json.dumps(raw, ensure_ascii=False)


def test_raw_nul_bytes_never_reach_quarantine(pipeline, store):
    pipeline.handle_message(TOPIC, b'{"v": \x00}')
    pipeline.flush()

    [(_, _, _, raw)] = store.quarantined
    assert "\x00" not in raw["raw_text"]


def test_full_queue_drops_new_messages_and_counts_them(contracts, store, tel_payload):
    pipeline = IngestPipeline(contracts, store, clock=lambda: RX, max_queue=1)

    pipeline.handle_message(TOPIC, encode(tel_payload))
    pipeline.handle_message(TOPIC, encode(tel_payload))
    pipeline.flush()

    assert pipeline.stats["dropped"] == 1
    assert len(store.telemetry) == 67


def test_listeners_are_notified_after_successful_write(pipeline, store, tel_payload):
    seen: list[list[str]] = []
    pipeline.add_listener(lambda samples: seen.append([s.pano_id for s in samples]))
    store.fail_writes = 1
    pipeline.handle_message(TOPIC, encode(tel_payload))

    pipeline.flush()
    assert seen == []  # yazilamayan veri yayinlanmaz

    pipeline.flush()
    assert seen == [["ADM-00001"]]


def test_background_writer_flushes_without_explicit_call(contracts, store, tel_payload):
    pipeline = IngestPipeline(contracts, store, clock=lambda: RX, flush_interval_s=0.05)
    pipeline.start()
    try:
        pipeline.handle_message(TOPIC, encode(tel_payload))
        deadline = time.monotonic() + 3.0
        while not store.telemetry and time.monotonic() < deadline:
            time.sleep(0.01)
    finally:
        pipeline.stop()

    assert len(store.telemetry) == 67


def test_rate_meter_averages_the_last_window():
    """/fleet/kpi ingest_msgs_per_s: son 60 s'de alinan mesaj / 60 (1 s kovalari, eskiyen kovalar duser)."""
    from app.ingest import RateMeter

    clock = [1000.0]
    meter = RateMeter(window_s=60, clock=lambda: clock[0])
    for second in range(30):  # 1000..1029 arasi saniyede bir mesaj
        clock[0] = 1000.0 + second
        meter.add()
    assert meter.per_second() == 0.5
    clock[0] = 1059.5  # hepsi hala son 60 s icinde
    assert meter.per_second() == 0.5
    clock[0] = 1075.0  # 1000..1015 dustu, 14 kova kaldi
    assert meter.per_second() == pytest.approx(14 / 60)
    clock[0] = 2000.0
    assert meter.per_second() == 0.0


def test_pipeline_reports_receive_rate(contracts, tel_payload):
    pipeline = IngestPipeline(contracts, MemoryStore(), clock=lambda: RX)
    for _ in range(3):
        pipeline.handle_message("gridup/pano/ADM-00001/tel", encode(tel_payload))
    assert pipeline.msgs_per_s() == pytest.approx(3 / 60)
