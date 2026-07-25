from __future__ import annotations

from relief_contracts import HouseholdSnapshotV1

# In-process, household-scoped scenario override for the demo-only shock
# simulator (Section 16.3) — applied on top of real ledger/obligation data
# at snapshot-assembly time, never written back to the ledger (the ledger
# is append-only real history). Session-only by design: restarting apps/api
# clears it, same as the frontend's own "reset demo" semantics.
_shocked_households: set[str] = set()

# Matches sarah_income_shock.json's trigger_event: the most recent paycheck
# was retroactively corrected from $2,100.00 to $1,720.00 — a $380.00
# reduction to an already-posted event, which is why it shows up as a lower
# *current* balance ($2,480.00 -> $2,100.00), not a smaller future paycheck.
SHOCK_BALANCE_DELTA_CENTS = -38000


def trigger_shock(household_id: str) -> None:
    _shocked_households.add(household_id)


def reset_demo(household_id: str) -> None:
    _shocked_households.discard(household_id)


def is_shocked(household_id: str) -> bool:
    return household_id in _shocked_households


def apply_scenario(snapshot: HouseholdSnapshotV1, household_id: str) -> HouseholdSnapshotV1:
    if household_id not in _shocked_households or not snapshot.accounts:
        return snapshot

    modified_accounts = [
        a.model_copy(
            update={
                "current_balance_cents": max(0, a.current_balance_cents + SHOCK_BALANCE_DELTA_CENTS),
                "available_balance_cents": (
                    max(0, a.available_balance_cents + SHOCK_BALANCE_DELTA_CENTS)
                    if a.available_balance_cents is not None
                    else None
                ),
            }
        )
        if i == 0
        else a
        for i, a in enumerate(snapshot.accounts)
    ]
    return snapshot.model_copy(update={"accounts": modified_accounts})
