from __future__ import annotations

import json

import httpx
import pytest
from relief_integrations import PlaidClient, PlaidConfigError


def test_missing_credentials_raise_config_error(monkeypatch):
    monkeypatch.delenv("PLAID_CLIENT_ID", raising=False)
    monkeypatch.delenv("PLAID_SECRET", raising=False)
    with pytest.raises(PlaidConfigError):
        PlaidClient()


def _client_with_transport(handler) -> PlaidClient:
    return PlaidClient(client_id="test_id", secret="test_secret", env="sandbox", transport=httpx.MockTransport(handler))


def test_create_link_token_sends_expected_payload_and_parses_response():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["json"] = json.loads(request.content)
        return httpx.Response(200, json={"link_token": "link-sandbox-abc", "expiration": "2026-08-01T00:00:00Z"})

    client = _client_with_transport(handler)
    result = client.create_link_token(user_id="hh_01")
    assert result["link_token"] == "link-sandbox-abc"
    assert captured["url"].endswith("/link/token/create")
    assert captured["json"]["client_id"] == "test_id"
    assert captured["json"]["secret"] == "test_secret"
    assert captured["json"]["user"]["client_user_id"] == "hh_01"


def test_sync_transactions_round_trips_cursor():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"added": [], "modified": [], "removed": [], "next_cursor": "abc", "has_more": False})

    client = _client_with_transport(handler)
    result = client.sync_transactions("access-sandbox-token", cursor="prev-cursor")
    assert result["next_cursor"] == "abc"
    assert result["has_more"] is False


def test_http_error_status_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error_code": "INVALID_ACCESS_TOKEN"})

    client = _client_with_transport(handler)
    with pytest.raises(httpx.HTTPStatusError):
        client.get_accounts("bad-token")
