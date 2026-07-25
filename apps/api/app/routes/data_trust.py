from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import get_request_id
from ..envelope import envelope
from ..seed import get_data_trust_fixture

router = APIRouter(prefix="/v1/data", tags=["data"])


@router.get("/trust")
def get_data_trust(request_id: str = Depends(get_request_id)):
    """forecast_provider: 'deterministic' and relieffm_version: null are
    genuinely accurate today, not placeholder values — no ReliefFM is
    connected (services/model_gateway falls back to the deterministic
    engine whenever it isn't)."""
    return envelope(request_id, get_data_trust_fixture())
