"""Ortak test donatilari.

Sozlesmeler repodaki `contracts/` dizininden okunur — testler de uretim kodu gibi
esikleri ve semalari koda gommez (PLAN.md kural 10).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
import yaml

from helpers import CONTRACTS_DIR


@pytest.fixture(scope="session")
def alarm_codes() -> dict:
    """contracts/alarm-codes.yaml tamami."""
    return yaml.safe_load((CONTRACTS_DIR / "alarm-codes.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def thresholds(alarm_codes: dict) -> dict:
    """Esik blogu: 70 K, 1.6, 0.998 gibi sayilar testlerde de elle yazilmaz."""
    return alarm_codes["thresholds"]


@pytest.fixture(scope="session")
def telemetry_schema() -> dict:
    """contracts/mqtt-telemetry.schema.json — DONMUS sozlesme."""
    return json.loads((CONTRACTS_DIR / "mqtt-telemetry.schema.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def assert_valid_telemetry(telemetry_schema: dict):
    """Bir yukun semaya uydugunu dogrular; ihlalleri okunur bicimde raporlar.

    sim/hello_publisher.py:140-145 'sozlesme kapisi' kalibinin test tarafindaki esi.
    """
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(telemetry_schema)

    def check(payload: dict) -> None:
        errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
        assert not errors, "sozlesme ihlali:\n" + "\n".join(
            f"  {list(e.absolute_path)}: {e.message}" for e in errors[:5]
        )

    return check


@pytest.fixture
def sample() -> dict:
    """TA1 uretecinden gelen sema-gecerli, saglikli bir telemetri yuku.

    Testler bunu yerinde degistirir, bu yuzden fonksiyon kapsamli (her testte taze).
    Isinma bitmis olsun diye birkac yuz adim atilir: soguk baslangicta dt_c ~ 0'dir
    ve L0 testleri anlamsizlasir.
    """
    from panoalgo.generator import PanelSimulator

    sim = PanelSimulator(
        pano_id="SIM-00001",
        seed=42,
        profile="karma",
        start=datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc),
    )
    for _ in range(400):
        payload = sim.step(10.0)
    return payload


@pytest.fixture(scope="session")
def label_schema() -> dict:
    """contracts/scenario-labels.schema.json — DONMUS sozlesme."""
    return json.loads((CONTRACTS_DIR / "scenario-labels.schema.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def assert_valid_labels(label_schema: dict):
    """Etiket nesnesinin donmus semaya uydugunu dogrular."""
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(label_schema)

    def check(labels: dict) -> None:
        errors = sorted(validator.iter_errors(labels), key=lambda e: list(e.absolute_path))
        assert not errors, "etiket sozlesme ihlali:\n" + "\n".join(
            f"  {list(e.absolute_path)}: {e.message}" for e in errors[:5]
        )

    return check
