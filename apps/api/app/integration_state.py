from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Optional

from relief_contracts.shared import AccountV1


@dataclass(frozen=True)
class PlaidConnection:
    access_token: str
    item_id: str
    accounts: tuple[AccountV1, ...]
    last_synced_at: datetime
    event_count: int


_connections: dict[str, PlaidConnection] = {}
_lock = Lock()


def get_plaid_connection(household_id: str) -> Optional[PlaidConnection]:
    with _lock:
        return _connections.get(household_id)


def set_plaid_connection(household_id: str, connection: PlaidConnection) -> None:
    with _lock:
        _connections[household_id] = connection


def clear_plaid_connections() -> None:
    """Test/demo reset helper. Access tokens never leave this process."""
    with _lock:
        _connections.clear()
