from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import get_request_id
from ..envelope import envelope
from ..seed import get_provider_status_fixture

router = APIRouter(prefix="/v1/providers", tags=["providers"])


@router.get("/status")
def get_providers_status(request_id: str = Depends(get_request_id)):
    """These describe external institution connectivity (Section 76) rather
    than anything Relief computes — Geico/Capital One/Chase are cosmetic
    connections not yet wired into the forecast, and that's stated
    honestly in each entry's approval_requirements field rather than
    hidden."""
    return envelope(request_id, get_provider_status_fixture())
