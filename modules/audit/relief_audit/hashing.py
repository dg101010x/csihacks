from __future__ import annotations

import hashlib
import json
from typing import Optional


def compute_payload_hash(before_state: Optional[str], after_state: Optional[str]) -> str:
    """A verifiable fingerprint of what an audit event claims changed. Replay
    (Section 17) recomputes this from the stored before/after state and
    compares it to the stored hash — a mismatch means the row was altered
    after the fact, since the hash is a function of the states, not stored
    independently of them."""
    canonical = json.dumps({"before": before_state, "after": after_state}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
