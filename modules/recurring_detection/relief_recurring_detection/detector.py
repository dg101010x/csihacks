from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from relief_contracts import FinancialEventV1

# Tolerance bands (in days) for classifying a median interval into an RFC5545
# FREQ. Chosen wide enough to absorb weekend/holiday posting drift without
# collapsing distinct frequencies into each other.
_FREQUENCY_BANDS: list[tuple[str, float, float]] = [
    ("FREQ=WEEKLY", 5.5, 8.5),
    ("FREQ=BIWEEKLY", 12.5, 16.0),
    ("FREQ=MONTHLY", 26.0, 33.0),
    ("FREQ=QUARTERLY", 80.0, 100.0),
    ("FREQ=YEARLY", 350.0, 380.0),
]

# The inverse mapping — a FREQ rule's typical period in days. Used by any
# consumer (deterministic_forecast, resilience) that needs to project an
# obligation's next occurrence or convert a scheduled amount to a daily rate.
FREQ_PERIOD_DAYS: dict[str, float] = {rule: (low + high) / 2 for rule, low, high in _FREQUENCY_BANDS}


@dataclass
class RecurringPattern:
    """One detected recurring group of posted events (Section 36)."""

    account_id: str
    direction: str
    event_type: str
    merchant_name: Optional[str]
    merchant_category: Optional[str]
    event_ids: list[str] = field(default_factory=list)
    average_amount_cents: int = 0
    amount_variation_ratio: float = 0.0
    average_interval_days: float = 0.0
    interval_variation_ratio: float = 0.0
    recurrence_rule: Optional[str] = None
    confidence: float = 0.0
    last_effective_at: Optional[datetime] = None
    next_predicted_at: Optional[datetime] = None

    @property
    def display_key(self) -> str:
        return self.merchant_name or self.merchant_category or self.event_type


def _group_key(event: FinancialEventV1) -> tuple:
    label = event.merchant_name or event.merchant_category or event.event_type
    return (event.account_id, event.direction.value, label)


def _classify_frequency(median_interval_days: float) -> Optional[str]:
    for rule, low, high in _FREQUENCY_BANDS:
        if low <= median_interval_days <= high:
            return rule
    return None


def _variation_ratio(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = statistics.mean(values)
    if mean == 0:
        return 0.0
    return statistics.pstdev(values) / abs(mean)


def detect_recurring_patterns(
    events: list[FinancialEventV1], *, min_occurrences: int = 2
) -> list[RecurringPattern]:
    """Groups posted events by (account, direction, merchant/category/type) and
    scores each group's regularity. Only ``posted`` events are considered —
    scheduled/pending events haven't happened yet and can't confirm a pattern.
    """
    groups: dict[tuple, list[FinancialEventV1]] = {}
    for event in events:
        if event.event_status.value != "posted":
            continue
        groups.setdefault(_group_key(event), []).append(event)

    patterns: list[RecurringPattern] = []
    for (account_id, direction, _label), group_events in groups.items():
        if len(group_events) < min_occurrences:
            continue
        ordered = sorted(group_events, key=lambda e: e.effective_at)
        amounts = [float(e.amount_cents) for e in ordered]
        intervals = [
            (ordered[i].effective_at - ordered[i - 1].effective_at).total_seconds() / 86400
            for i in range(1, len(ordered))
        ]
        median_interval = statistics.median(intervals) if intervals else 0.0
        interval_ratio = _variation_ratio(intervals)
        amount_ratio = _variation_ratio(amounts)
        rule = _classify_frequency(median_interval) if intervals else None

        # Confidence rewards more occurrences and penalizes irregular timing
        # or amount; capped at 0.98 since detection is never certain without
        # the consumer confirming (ObligationV1.consumer_confirmed).
        occurrence_score = min(1.0, len(ordered) / 6)
        regularity_score = max(0.0, 1.0 - interval_ratio) if rule else 0.2
        amount_score = max(0.0, 1.0 - amount_ratio)
        confidence = round(min(0.98, 0.5 * regularity_score + 0.3 * occurrence_score + 0.2 * amount_score), 2)

        last = ordered[-1]
        next_predicted = last.effective_at + timedelta(days=median_interval) if rule else None

        patterns.append(
            RecurringPattern(
                account_id=account_id,
                direction=direction,
                event_type=last.event_type,
                merchant_name=last.merchant_name,
                merchant_category=last.merchant_category,
                event_ids=[e.event_id for e in ordered],
                average_amount_cents=round(statistics.mean(amounts)),
                amount_variation_ratio=round(amount_ratio, 3),
                average_interval_days=round(median_interval, 1),
                interval_variation_ratio=round(interval_ratio, 3),
                recurrence_rule=rule,
                confidence=confidence,
                last_effective_at=last.effective_at,
                next_predicted_at=next_predicted,
            )
        )

    return sorted(patterns, key=lambda p: p.confidence, reverse=True)
