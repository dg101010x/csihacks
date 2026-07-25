from __future__ import annotations

import calendar
from datetime import datetime, timedelta

from relief_contracts import FinancialEventV1, HouseholdSnapshotV1
from relief_recurring_detection import detect_recurring_patterns


def _add_months(dt: datetime, months: int) -> datetime:
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _advance(dt: datetime, rule: str) -> datetime:
    """Calendar-correct next occurrence for an RFC5545-style FREQ rule."""
    if rule == "FREQ=WEEKLY":
        return dt + timedelta(days=7)
    if rule == "FREQ=BIWEEKLY":
        return dt + timedelta(days=14)
    if rule == "FREQ=MONTHLY":
        return _add_months(dt, 1)
    if rule == "FREQ=QUARTERLY":
        return _add_months(dt, 3)
    if rule == "FREQ=YEARLY":
        return _add_months(dt, 12)
    return dt + timedelta(days=30)


def _event_key(event: FinancialEventV1) -> tuple:
    label = event.obligation_id or event.merchant_name or event.event_type
    direction = event.direction.value if hasattr(event.direction, "value") else event.direction
    return (event.effective_at.date(), label, direction)


def _projected_event(
    *, household_id: str, account_id: str, currency: str, when: datetime,
    amount_cents: int, direction: str, merchant_name: str, merchant_category: str,
    obligation_id: str | None,
) -> FinancialEventV1:
    marker = f"proj_{obligation_id or merchant_category}_{when.date().isoformat()}"
    return FinancialEventV1(
        contract_version="1.0.0",
        event_id=marker,
        household_id=household_id,
        account_id=account_id,
        source="relief_projection",
        source_event_id=marker,
        event_type="projected_payment" if direction == "outflow" else "projected_income",
        event_status="scheduled",
        occurred_at=when,
        effective_at=when,
        amount_cents=amount_cents,
        currency=currency,
        direction=direction,
        merchant_name=merchant_name,
        merchant_category=merchant_category,
        obligation_id=obligation_id,
        is_recurring=True,
        is_pending=False,
        metadata={"projected": True},
    )


def project_events(snapshot: HouseholdSnapshotV1, *, horizon_end: datetime) -> list[FinancialEventV1]:
    """Explicit known_future_events, extended by rolling active obligations
    and detected recurring income forward to `horizon_end` — so a forecast
    horizon isn't limited to whatever the snapshot happened to enumerate.
    Explicit events always win over a projected one on the same
    (date, label, direction) key.
    """
    account_id = snapshot.accounts[0].account_id if snapshot.accounts else "unknown"
    events: dict[tuple, FinancialEventV1] = {}

    for event in snapshot.known_future_events:
        if event.effective_at <= horizon_end:
            events[_event_key(event)] = event

    for obligation in snapshot.obligations:
        if obligation.status != "active" or not obligation.recurrence_rule or not obligation.next_due_at:
            continue
        explicit_dates = [e.effective_at for e in snapshot.known_future_events if e.obligation_id == obligation.obligation_id]
        occurrences: list[datetime] = []
        if explicit_dates:
            cursor = max(explicit_dates)
        else:
            occurrences.append(obligation.next_due_at)
            cursor = obligation.next_due_at
        while True:
            cursor = _advance(cursor, obligation.recurrence_rule)
            if cursor > horizon_end:
                break
            occurrences.append(cursor)
        for occ in occurrences:
            synthetic = _projected_event(
                household_id=snapshot.household_id, account_id=account_id, currency=snapshot.currency,
                when=occ, amount_cents=obligation.scheduled_amount_cents, direction="outflow",
                merchant_name=obligation.display_name, merchant_category=obligation.obligation_type,
                obligation_id=obligation.obligation_id,
            )
            events.setdefault(_event_key(synthetic), synthetic)

    income_patterns = [
        p for p in detect_recurring_patterns(snapshot.recent_events)
        if p.direction == "inflow" and p.recurrence_rule
    ]
    for pattern in income_patterns:
        explicit_dates = [
            e.effective_at for e in snapshot.known_future_events
            if e.direction == "inflow" and e.merchant_name == pattern.merchant_name
        ]
        cursor = max(explicit_dates) if explicit_dates else pattern.last_effective_at
        occurrences = []
        while True:
            cursor = _advance(cursor, pattern.recurrence_rule)
            if cursor > horizon_end:
                break
            occurrences.append(cursor)
        for occ in occurrences:
            synthetic = _projected_event(
                household_id=snapshot.household_id, account_id=account_id, currency=snapshot.currency,
                when=occ, amount_cents=pattern.average_amount_cents, direction="inflow",
                merchant_name=pattern.merchant_name or "recurring_income",
                merchant_category=pattern.merchant_category or "income",
                obligation_id=None,
            )
            events.setdefault(_event_key(synthetic), synthetic)

    return sorted(events.values(), key=lambda e: e.effective_at)
