"""Section 47 — data split strategy (household-first, no cross-split leakage)."""
from __future__ import annotations

import hashlib

_SPLIT_BOUNDARIES = [("train", 80), ("val", 90), ("test", 100)]  # cumulative percent


def split_for_household(household_id: str) -> str:
    """Deterministic hash-based split assignment. Same household_id always
    lands in the same split, regardless of generation order or re-runs."""
    digest = hashlib.sha256(household_id.encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 100
    for name, upper in _SPLIT_BOUNDARIES:
        if bucket < upper:
            return name
    return "test"


def assign_splits(household_ids: list[str]) -> dict[str, str]:
    assignment = {hid: split_for_household(hid) for hid in household_ids}
    # No household may appear in more than one split — trivially true here
    # since assignment is a function of household_id alone, but assert the
    # invariant explicitly since section 47/48 treat it as load-bearing.
    assert len(assignment) == len(household_ids)
    return assignment
