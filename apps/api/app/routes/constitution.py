from __future__ import annotations

from fastapi import APIRouter, Depends
from relief_consumer_constitution.store import SqlConstitutionRuleStore
from sqlalchemy.orm import Session

from ..dependencies import get_household_id, get_request_id
from ..db import get_db
from ..envelope import envelope

router = APIRouter(prefix="/v1/constitution", tags=["constitution"])


@router.get("/rules")
def get_constitution_rules(
    session: Session = Depends(get_db),
    household_id: str = Depends(get_household_id),
    request_id: str = Depends(get_request_id),
):
    store = SqlConstitutionRuleStore(session)
    rules = store.list_for_household(household_id, status="active")
    starter_rules = store.list_for_household(household_id, status="draft")
    return envelope(
        request_id,
        {
            "rules": [r.model_dump(mode="json") for r in rules],
            "starter_rules": [r.model_dump(mode="json") for r in starter_rules],
        },
    )
