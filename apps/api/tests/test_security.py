from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test_security.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    import app.db as db_module

    importlib.reload(db_module)
    db_module.create_all_tables()
    session = db_module.SessionLocal()
    from app.seed import seed_demo_household

    seed_demo_household(session)
    session.close()

    import app.main as main_module

    importlib.reload(main_module)

    with TestClient(main_module.app) as test_client:
        yield test_client


def test_routes_are_open_when_no_api_key_is_configured(client, monkeypatch):
    monkeypatch.delenv("RELIEF_API_KEY", raising=False)
    res = client.get("/v1/providers/status")
    assert res.status_code == 200


def test_routes_reject_missing_key_when_configured(client, monkeypatch):
    monkeypatch.setenv("RELIEF_API_KEY", "secret-key-123")
    res = client.get("/v1/providers/status")
    assert res.status_code == 401


def test_routes_reject_wrong_key_when_configured(client, monkeypatch):
    monkeypatch.setenv("RELIEF_API_KEY", "secret-key-123")
    res = client.get("/v1/providers/status", headers={"X-API-Key": "wrong-key"})
    assert res.status_code == 401


def test_routes_accept_the_correct_key(client, monkeypatch):
    monkeypatch.setenv("RELIEF_API_KEY", "secret-key-123")
    res = client.get("/v1/providers/status", headers={"X-API-Key": "secret-key-123"})
    assert res.status_code == 200


def test_health_never_requires_a_key(client, monkeypatch):
    monkeypatch.setenv("RELIEF_API_KEY", "secret-key-123")
    res = client.get("/health")
    assert res.status_code == 200


def test_unhandled_exception_returns_generic_500_with_request_id(client, monkeypatch):
    import app.routes.providers_status as providers_status_module

    def _boom():
        raise RuntimeError("simulated failure with a secret path /etc/whatever")

    monkeypatch.setattr(providers_status_module, "get_provider_status_fixture", _boom)

    res = client.get("/v1/providers/status")
    assert res.status_code == 500
    body = res.json()
    assert body["detail"] == "Internal server error."
    assert "simulated failure" not in res.text
    assert "request_id" in body


@pytest.mark.parametrize("limit", [3])
def test_rate_limit_returns_429_after_the_configured_threshold(tmp_path, monkeypatch, limit):
    db_path = tmp_path / "test_rate_limit.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("RELIEF_RATE_LIMIT_PER_MINUTE", str(limit))
    monkeypatch.delenv("RELIEF_API_KEY", raising=False)

    import app.db as db_module

    importlib.reload(db_module)
    db_module.create_all_tables()
    session = db_module.SessionLocal()
    from app.seed import seed_demo_household

    seed_demo_household(session)
    session.close()

    import app.main as main_module

    importlib.reload(main_module)

    with TestClient(main_module.app) as test_client:
        statuses = [test_client.get("/v1/providers/status").status_code for _ in range(limit + 2)]

    assert statuses[:limit] == [200] * limit
    assert 429 in statuses[limit:]
