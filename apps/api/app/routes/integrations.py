from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from relief_integrations import PlaidAdapter, PlaidClient, PlaidConfigError
from relief_ledger import SqlLedgerStore
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import get_household_id, get_request_id
from ..envelope import envelope
from ..integration_state import PlaidConnection, get_plaid_connection, set_plaid_connection

router = APIRouter(prefix="/v1/integrations", tags=["integrations"])


class PublicTokenExchange(BaseModel):
    public_token: str


class SandboxConnectRequest(BaseModel):
    institution_id: str = "ins_109508"


def _client() -> PlaidClient:
    try:
        return PlaidClient()
    except PlaidConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _sync_connection(
    client: PlaidClient,
    *,
    household_id: str,
    access_token: str,
    item_id: str,
    session: Session,
) -> dict[str, Any]:
    adapter = PlaidAdapter(client, get_access_token=lambda _: access_token)
    accounts = adapter.list_accounts(household_id)
    events = adapter.list_events(
        household_id,
        since=datetime(2000, 1, 1, tzinfo=timezone.utc),
    )
    forecast_input_enabled = client.env == "production" or os.environ.get("RELIEF_USE_PLAID_FOR_FORECAST") == "1"
    if forecast_input_enabled:
        ledger = SqlLedgerStore(session)
        for event in events:
            ledger.append(event)
    now = datetime.now(timezone.utc)
    set_plaid_connection(
        household_id,
        PlaidConnection(
            access_token=access_token,
            item_id=item_id,
            accounts=tuple(accounts),
            last_synced_at=now,
            event_count=len(events),
        ),
    )
    return {
        "provider": "plaid_sandbox" if client.env == "sandbox" else "plaid",
        "connection_status": "connected",
        "accounts_available": len(accounts),
        "events_synchronized": len(events),
        "last_synced_at": now.isoformat(),
        "is_simulated": client.env != "production",
        "forecast_input_enabled": forecast_input_enabled,
    }


def _plaid_call(action):
    try:
        return action()
    except httpx.HTTPStatusError as exc:
        detail = "Plaid rejected the request."
        try:
            payload = exc.response.json()
            detail = payload.get("error_message") or payload.get("error_code") or detail
        except ValueError:
            pass
        raise HTTPException(status_code=502, detail=detail) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail="Plaid is temporarily unreachable.") from exc


@router.get("/status")
def integration_status(
    household_id: str = Depends(get_household_id),
    request_id: str = Depends(get_request_id),
):
    connection = get_plaid_connection(household_id)
    plaid_env = os.environ.get("PLAID_ENV", "sandbox")
    plaid = {
        "provider": "plaid",
        "configured": bool(
            os.environ.get("PLAID_CLIENT_ID")
            or os.environ.get("CLIENT_ID")
        )
        and bool(
            os.environ.get("PLAID_SECRET")
            or os.environ.get("SANDBOX_SECRET")
        ),
        "connection_status": "connected" if connection is not None else "disconnected",
        "accounts_available": len(connection.accounts) if connection is not None else 0,
        "events_synchronized": connection.event_count if connection is not None else 0,
        "last_synced_at": connection.last_synced_at.isoformat() if connection is not None else None,
        "is_simulated": plaid_env != "production",
        "forecast_input_enabled": (
            plaid_env == "production"
            or os.environ.get("RELIEF_USE_PLAID_FOR_FORECAST") == "1"
        ),
    }
    return envelope(request_id, [plaid])


@router.post("/plaid/link_token")
def plaid_link_token(
    household_id: str = Depends(get_household_id),
    request_id: str = Depends(get_request_id),
):
    client = _client()
    try:
        result = _plaid_call(lambda: client.create_link_token(user_id=household_id))
    finally:
        client.close()
    return envelope(
        request_id,
        {
            "link_token": result["link_token"],
            "expiration": result.get("expiration"),
        },
    )


@router.post("/plaid/exchange")
def plaid_exchange(
    body: PublicTokenExchange,
    session: Session = Depends(get_db),
    household_id: str = Depends(get_household_id),
    request_id: str = Depends(get_request_id),
):
    client = _client()
    try:
        exchanged = _plaid_call(lambda: client.exchange_public_token(body.public_token))
        result = _plaid_call(
            lambda: _sync_connection(
                client,
                household_id=household_id,
                access_token=exchanged["access_token"],
                item_id=exchanged["item_id"],
                session=session,
            )
        )
    finally:
        client.close()
    return envelope(request_id, result)


@router.post("/plaid/sandbox/connect")
def plaid_sandbox_connect(
    body: SandboxConnectRequest,
    session: Session = Depends(get_db),
    household_id: str = Depends(get_household_id),
    request_id: str = Depends(get_request_id),
):
    """Demo-only server-side equivalent of a successful Plaid Link flow."""
    client = _client()
    try:
        if client.env != "sandbox":
            raise HTTPException(status_code=409, detail="Sandbox connect is disabled outside Plaid Sandbox.")
        public_token = _plaid_call(
            lambda: client.create_sandbox_public_token(institution_id=body.institution_id)
        )
        exchanged = _plaid_call(lambda: client.exchange_public_token(public_token))
        result = _plaid_call(
            lambda: _sync_connection(
                client,
                household_id=household_id,
                access_token=exchanged["access_token"],
                item_id=exchanged["item_id"],
                session=session,
            )
        )
    finally:
        client.close()
    return envelope(request_id, result)


@router.post("/plaid/webhook")
def plaid_webhook(
    payload: dict[str, Any],
    session: Session = Depends(get_db),
    household_id: str = Depends(get_household_id),
    request_id: str = Depends(get_request_id),
):
    connection = get_plaid_connection(household_id)
    if connection is None or payload.get("item_id") != connection.item_id:
        raise HTTPException(status_code=404, detail="Unknown Plaid item.")
    client = _client()
    try:
        result = _plaid_call(
            lambda: _sync_connection(
                client,
                household_id=household_id,
                access_token=connection.access_token,
                item_id=connection.item_id,
                session=session,
            )
        )
    finally:
        client.close()
    return envelope(request_id, {"acknowledged": True, **result})
