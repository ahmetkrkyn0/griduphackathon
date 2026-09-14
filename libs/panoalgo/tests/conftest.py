"""Ortak test donatilari.

Sozlesmeler repodaki `contracts/` dizininden okunur — testler de uretim kodu gibi
esikleri ve semalari koda gommez (PLAN.md kural 10).
"""

from __future__ import annotations

import json

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
