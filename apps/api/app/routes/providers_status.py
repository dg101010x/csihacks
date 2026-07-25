from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import get_request_id
from ..envelope import envelope
from ..dependencies import get_household_id
from ..integration_state import get_plaid_connection
from ..seed import get_provider_status_fixture

router = APIRouter(prefix="/v1/providers", tags=["providers"])


@router.get("/status")
def get_providers_status(
    household_id: str = Depends(get_household_id),
    request_id: str = Depends(get_request_id),
):
    """These describe external institution connectivity (Section 76) rather
    than anything Relief computes — Geico/Capital One/Chase are cosmetic
    connections not yet wired into the forecast, and that's stated
    honestly in each entry's approval_requirements field rather than
    hidden."""
    providers = get_provider_status_fixture()
    connection = get_plaid_connection(household_id)
    if connection is not None:
        plaid = next(provider for provider in providers if provider["provider_id"] == "plaid_sandbox")
        plaid.update(
            connection_status="connected",
            accounts_available=len(connection.accounts),
            last_synced_at=connection.last_synced_at.isoformat(),
            approval_requirements="Connected to Plaid Sandbox; data is simulated and read-only.",
            expected_response_time="Live sandbox synchronization",
        )
    return envelope(request_id, providers)
