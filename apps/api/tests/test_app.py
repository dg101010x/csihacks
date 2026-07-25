from __future__ import annotations

import uuid

import pytest
from app.db import SessionLocal, create_all_tables, engine
from app.main import app
from app.seed import seed_demo_household
from fastapi.testclient import TestClient
from sqlalchemy import text


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Fresh SQLite file per test so seeding/state doesn't leak across tests.
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    import importlib

    import app.db as db_module

    importlib.reload(db_module)
    db_module.create_all_tables()
    session = db_module.SessionLocal()
    seed_demo_household(session)
    session.close()

    import app.main as main_module

    importlib.reload(main_module)

    with TestClient(main_module.app) as test_client:
        yield test_client


def test_health_check(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_household_snapshot_has_expected_shape(client):
    res = client.get("/v1/households/current/snapshot")
    assert res.status_code == 200
    body = res.json()
    assert body["data"]["household_id"] == "hh_01"
    assert len(body["data"]["accounts"]) == 1
    assert len(body["data"]["obligations"]) == 4
    assert body["metadata"]["contract_version"] == "1.0.0"
    assert "x-request-id" in res.headers


def test_forecast_reconciles_and_has_no_model_metadata(client):
    res = client.post("/v1/forecasts")
    assert res.status_code == 200
    forecast = res.json()["data"]
    assert forecast["provider"] == "deterministic"
    assert forecast["model_metadata"] is None
    for point in forecast["trajectories"]:
        assert point["starting_balance_cents"] + point["inflow_cents"] - point["outflow_cents"] == point["ending_balance_cents"]


def test_healthy_baseline_has_no_interventions(client):
    res = client.post("/v1/interventions/generate")
    assert res.status_code == 200
    assert res.json()["data"] == []


def test_demo_shock_creates_risk_and_interventions_respond(client):
    shock_res = client.post("/v1/demo/shock")
    assert shock_res.status_code == 200

    forecast_res = client.post("/v1/forecasts")
    forecast = forecast_res.json()["data"]
    assert forecast["distress_probabilities"]["essential_reserve_violation"] > 0

    packages_res = client.post("/v1/interventions/generate")
    packages = packages_res.json()["data"]
    assert len(packages) >= 1
    assert any(p["label"] == "Recommended balance" for p in packages)

    client.post("/v1/demo/reset")
    reset_forecast = client.post("/v1/forecasts").json()["data"]
    assert reset_forecast["distress_probabilities"]["essential_reserve_violation"] < 0.15


def test_full_approval_flow_reaches_executed_and_is_audited(client):
    client.post("/v1/demo/shock")
    packages = client.post("/v1/interventions/generate").json()["data"]
    assert packages, "expected at least one package on the shocked household"

    with_provider = next((p for p in packages if any(a["provider_capability_id"] for a in p["actions"])), None)
    target = with_provider or packages[0]

    approve_res = client.post(f"/v1/interventions/{target['package_id']}/approve")
    assert approve_res.status_code == 200
    provider_case = approve_res.json()["data"]["provider_case"]

    if provider_case is not None:
        case_res = client.post(f"/v1/provider/cases/{provider_case['case_id']}/approve")
        assert case_res.status_code == 200
        assert case_res.json()["data"]["stage"] == "executed"

    audit_res = client.get(f"/v1/audit/{target['package_id']}")
    events = audit_res.json()["data"]
    assert len(events) >= 1
    assert events[0]["event_type"] == "intervention_submitted"


def test_constitution_rules_are_seeded(client):
    res = client.get("/v1/constitution/rules")
    body = res.json()["data"]
    assert len(body["rules"]) == 1
    assert len(body["starter_rules"]) == 2


def test_providers_status_and_data_trust_are_served(client):
    providers = client.get("/v1/providers/status").json()["data"]
    assert any(p["provider_id"] == "synthetic_wells_fargo" for p in providers)

    trust = client.get("/v1/data/trust").json()["data"]
    assert trust[0]["forecast_provider"] == "deterministic"


def test_approving_unknown_package_returns_404(client):
    res = client.post(f"/v1/interventions/does_not_exist/approve")
    assert res.status_code == 404
