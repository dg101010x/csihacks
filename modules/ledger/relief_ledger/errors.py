from __future__ import annotations


class DuplicateEventError(Exception):
    """Raised when (source, source_event_id, account_id) already exists (Section 32.5)."""


class ImmutableEventError(Exception):
    """Raised on any attempt to mutate or delete a posted ledger event."""
