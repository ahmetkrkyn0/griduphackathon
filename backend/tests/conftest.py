"""Ortak test donatilari.

Sozlesmeler repodaki `contracts/` dizininden okunur — testler de uretim kodu gibi
esikleri ve semalari koda gommez (PLAN.md kural 10).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from helpers import CONTRACTS_DIR

FIXTURES_DIR = Path(__file__).parent / "fixtures"

OPENAPI_URI = "urn:gridup:openapi"


@pytest.fixture(scope="session")
def contracts():
    from app.config import load_contracts

    return load_contracts(CONTRACTS_DIR)


@pytest.fixture
def tel_payload() -> dict:
    """Semaya uyan, elle hesaplanmis 5 noktali telemetri yuku (her testte taze kopya)."""
    return json.loads((FIXTURES_DIR / "tel_valid.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def api_contract():
    """contracts/openapi.yaml semalarina gore yanit dogrulayici.

    Kullanim: api_contract(instance, "PanelSummary") veya api_contract(liste, "PanelSummary", many=True)
    """
    doc = yaml.safe_load((CONTRACTS_DIR / "openapi.yaml").read_text(encoding="utf-8"))
    registry = Registry().with_resource(
        OPENAPI_URI, Resource.from_contents(doc, default_specification=DRAFT202012)
    )

    def validate(instance, schema_name: str, many: bool = False) -> None:
        ref = {"$ref": f"{OPENAPI_URI}#/components/schemas/{schema_name}"}
        schema = {"type": "array", "items": ref} if many else ref
        validator = Draft202012Validator(schema, registry=registry)
        errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))
        assert not errors, "sozlesme ihlali:\n" + "\n".join(
            f"  {e.json_path}: {e.message}" for e in errors
        )

    return validate
