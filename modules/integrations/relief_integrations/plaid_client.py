from __future__ import annotations

import os
from typing import Optional

import httpx

_BASE_URLS = {
    "sandbox": "https://sandbox.plaid.com",
    "development": "https://development.plaid.com",
    "production": "https://production.plaid.com",
}


class PlaidConfigError(Exception):
    pass


class PlaidClient:
    """Thin wrapper over Plaid's REST API — sandbox by default, matching
    apps/api/.env.local.example (Section 15). Deliberately doesn't pull in
    the official plaid-python SDK: the handful of endpoints Relief needs
    (link token, token exchange, accounts, transaction sync) are stable
    enough that a direct httpx client keeps one fewer heavy dependency and
    stays fully mockable in tests via httpx.MockTransport — no live network
    access or real credentials needed to test the request/response mapping.
    """

    def __init__(
        self,
        *,
        client_id: Optional[str] = None,
        secret: Optional[str] = None,
        env: Optional[str] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        # The hackathon starter environment used Plaid's dashboard names
        # (`CLIENT_ID`/`SANDBOX_SECRET`). Accept those aliases so the checked-in
        # example and existing local credentials both work without copying a
        # secret into another file.
        self.client_id = client_id or os.environ.get("PLAID_CLIENT_ID") or os.environ.get("CLIENT_ID")
        self.secret = secret or os.environ.get("PLAID_SECRET") or os.environ.get("SANDBOX_SECRET")
        self.env = env or os.environ.get("PLAID_ENV", "sandbox")
        if not self.client_id or not self.secret:
            raise PlaidConfigError(
                "PLAID_CLIENT_ID and PLAID_SECRET must be set (see apps/api/.env.local.example)."
            )
        base_url = _BASE_URLS.get(self.env, _BASE_URLS["sandbox"])
        self._http = httpx.Client(base_url=base_url, transport=transport, timeout=10.0)

    def _post(self, path: str, payload: dict) -> dict:
        body = {"client_id": self.client_id, "secret": self.secret, **payload}
        response = self._http.post(path, json=body)
        response.raise_for_status()
        return response.json()

    def create_link_token(self, *, user_id: str, client_name: str = "Relief") -> dict:
        return self._post(
            "/link/token/create",
            {
                "user": {"client_user_id": user_id},
                "client_name": client_name,
                "products": ["transactions"],
                "country_codes": ["US"],
                "language": "en",
            },
        )

    def create_sandbox_public_token(self, *, institution_id: str = "ins_109508") -> str:
        """Sandbox-only helper — lets the demo simulate the Link flow end to
        end without a browser, per Plaid's own sandbox testing pattern."""
        result = self._post(
            "/sandbox/public_token/create",
            {"institution_id": institution_id, "initial_products": ["transactions"]},
        )
        return result["public_token"]

    def exchange_public_token(self, public_token: str) -> dict:
        return self._post("/item/public_token/exchange", {"public_token": public_token})

    def get_accounts(self, access_token: str) -> list[dict]:
        result = self._post("/accounts/get", {"access_token": access_token})
        return result["accounts"]

    def sync_transactions(self, access_token: str, *, cursor: Optional[str] = None) -> dict:
        payload: dict = {"access_token": access_token}
        if cursor is not None:
            payload["cursor"] = cursor
        return self._post("/transactions/sync", payload)

    def close(self) -> None:
        self._http.close()
