from __future__ import annotations

from relief_contracts.shared import ObligationV1
from relief_recurring_detection import FREQ_PERIOD_DAYS

# Obligations at or above this essentiality are counted toward the reserve
# burn rate — housing, utilities, insurance, secured debt, medical. Below
# this line (credit cards, subscriptions) is discretionary enough that
# missing a reserve buffer for it isn't a safety concern.
_ESSENTIAL_THRESHOLD = 0.6

# How many days of essential burn the reserve should cover. A week is
# enough runway to react to a missed paycheck or a shock without the
# household needing to touch discretionary spending immediately.
_RESERVE_WINDOW_DAYS = 7

# Never let the reserve collapse to near-zero just because a household has
# no detected essential obligations yet (e.g. day one, before detection has
# run) — a small floor keeps downstream reserve-violation checks meaningful.
_RESERVE_FLOOR_CENTS = 20_000

_DEFAULT_PERIOD_DAYS = 30.0


def _daily_rate_cents(obligation: ObligationV1) -> float:
    period_days = FREQ_PERIOD_DAYS.get(obligation.recurrence_rule or "", _DEFAULT_PERIOD_DAYS)
    return obligation.scheduled_amount_cents / period_days


def essential_daily_burn_rate_cents(obligations: list[ObligationV1]) -> float:
    """Sum of essential (housing/utilities/insurance/secured-debt/medical)
    obligations prorated to a daily rate. Shared with modules/resilience so
    both derive "how much essential spending per day" from the same
    essentiality threshold instead of duplicating the cutoff."""
    essential = [o for o in obligations if o.essentiality_score >= _ESSENTIAL_THRESHOLD and o.status == "active"]
    return sum(_daily_rate_cents(o) for o in essential)


def compute_essential_reserve_cents(obligations: list[ObligationV1]) -> int:
    """A week of essential burn rate — the minimum cushion the forecast
    treats as "safe" (Section 45's essential_reserve_cents)."""
    daily_rate = essential_daily_burn_rate_cents(obligations)
    return max(_RESERVE_FLOOR_CENTS, round(daily_rate * _RESERVE_WINDOW_DAYS))
