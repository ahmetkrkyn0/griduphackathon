"""TB3 Adim 6 — loadtest/storage.py veri butcesi hesaplari (olcum docs/09'da).

Beklentiler elle hesaplanmistir. MQTT 3.1.1 QoS 1 PUBLISH: sabit baslik 1 bayt + kalan uzunluk (<16384 icin 2 bayt)
+ topic uzunluk alani 2 bayt + topic + paket kimligi 2 bayt + yuk.
"""

from __future__ import annotations

import importlib.util
import sys

import pytest

from helpers import REPO_ROOT


@pytest.fixture(scope="module")
def storage():
    spec = importlib.util.spec_from_file_location("loadtest_storage", REPO_ROOT / "loadtest" / "storage.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(spec.name, None)


def test_mqtt_publish_bytes(storage):
    """1000 baytlik yuk, 25 karakterlik topic: 1 + 2 + 2 + 25 + 2 + 1000 = 1032."""
    assert storage.mqtt_publish_bytes(payload_bytes=1000, topic="gridup/pano/SIM-00001/tel") == 1032


def test_mqtt_remaining_length_grows_with_large_payload(storage):
    """Kalan uzunluk 16384 ve ustunde 3 bayttir: 1 + 3 + 2 + 25 + 2 + 20000 = 20033."""
    assert storage.mqtt_publish_bytes(payload_bytes=20000, topic="gridup/pano/SIM-00001/tel") == 20033


def test_monthly_megabytes(storage):
    """30 gun / 10 s = 259.200 mesaj x 1032 B = 267,4944 MB."""
    assert storage.monthly_mb(bytes_per_message=1032, period_s=10.0) == pytest.approx(267.4944)


def test_steady_state_storage(storage):
    """Gunde 1.000.000 satir; 7 gun sikistirmasiz (100 B), 83 gun sikistirilmis (10 B), 1 dk ozet 730 gun (10 B, satir/6).

    sicak  = 1e6 x 7 x 100    = 0,7 GB
    ilik   = 1e6 x 83 x 10    = 0,83 GB
    ozet   = 1e6 / 6 x 730 x 10 = 1,21667 GB
    """
    result = storage.steady_state_gb(rows_per_day=1_000_000, raw_bytes_per_row=100.0, compressed_bytes_per_row=10.0,
                                     hot_days=7, raw_retention_days=90, rollup_days=730, rollup_factor=6)
    assert result["hot_gb"] == pytest.approx(0.7)
    assert result["warm_gb"] == pytest.approx(0.83)
    assert result["rollup_gb"] == pytest.approx(1.216667, abs=1e-6)
    assert result["total_gb"] == pytest.approx(2.746667, abs=1e-6)


def test_mqtt_remaining_length_boundary(storage):
    """Kalan uzunluk 16383 -> 2 bayt, 16384 -> 3 bayt (25 karakterlik topic: kalan = yuk + 29)."""
    topic = "gridup/pano/SIM-00001/tel"
    assert storage.mqtt_publish_bytes(payload_bytes=16354, topic=topic) == 1 + 2 + 16383
    assert storage.mqtt_publish_bytes(payload_bytes=16355, topic=topic) == 1 + 3 + 16384
