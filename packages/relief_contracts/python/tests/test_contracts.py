"""Section 88: the same fixture must validate against every language binding.

This file covers the Pydantic leg; the TypeScript/Zod and JSON Schema legs are
covered by ../../tests/contracts.test.ts (Vitest).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from relief_contracts import (
    FinancialEventV1,
    ForecastRequestV1,
    ForecastResponseV1,
    HouseholdSnapshotV1,
    InterventionSimulationRequestV1,
)

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


@pytest.mark.parametrize(
    "fixture_name,model",
    [
        ("financial_event.v1.example.json", FinancialEventV1),
        ("household_snapshot.v1.example.json", HouseholdSnapshotV1),
        ("forecast_request.v1.example.json", ForecastRequestV1),
        ("forecast_response.v1.example.json", ForecastResponseV1),
        ("intervention_simulation_request.v1.example.json", InterventionSimulationRequestV1),
    ],
)
def test_fixture_validates_against_pydantic(fixture_name: str, model) -> None:
    data = load_fixture(fixture_name)
    instance = model.model_validate(data)
    assert instance is not None


def test_rejects_malformed_contract_version() -> None:
    data = load_fixture("financial_event.v1.example.json")
    data["contract_version"] = "not-a-version"
    with pytest.raises(ValidationError):
        FinancialEventV1.model_validate(data)


def test_rejects_model_metadata_on_non_relieffm_provider() -> None:
    data = load_fixture("forecast_response.v1.example.json")
    data["model_metadata"] = {
        "model_version": "1.0.0",
        "calibration_version": None,
        "inference_latency_ms": 10,
    }
    with pytest.raises(ValidationError):
        ForecastResponseV1.model_validate(data)
