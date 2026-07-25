"""Section 36 — synthetic household parameter sampling.

Every parameter is drawn independently per household from continuous
distributions. No demographic personas / archetypes — see section 36's
explicit prohibition on "simplistic demographic personas as predictive
shortcuts".
"""
from __future__ import annotations

import numpy as np

from .types import HouseholdParams

INCOME_FREQUENCIES = [
    "weekly",
    "biweekly",
    "semimonthly",
    "monthly",
    "hourly_variable",
    "freelance",
]
INCOME_FREQUENCY_WEIGHTS = [0.12, 0.38, 0.18, 0.12, 0.12, 0.08]


def sample_household_params(household_id: str, rng: np.random.Generator) -> HouseholdParams:
    income_frequency = rng.choice(INCOME_FREQUENCIES, p=INCOME_FREQUENCY_WEIGHTS)

    # Annualized income drawn log-normally, then converted to a per-paycheck amount downstream.
    annual_income_cents = int(np.clip(rng.lognormal(mean=10.7, sigma=0.45), 15_000_00, 300_000_00))

    income_reliability = float(np.clip(rng.beta(a=8, b=1.5), 0.5, 0.999))
    income_volatility = float(np.clip(rng.gamma(shape=2.0, scale=0.05), 0.01, 0.6))
    if income_frequency in ("hourly_variable", "freelance"):
        income_volatility = float(np.clip(income_volatility * 2.0, 0.05, 0.8))

    fixed_expense_ratio = float(np.clip(rng.beta(a=5, b=4), 0.15, 0.85))
    essential_spending_level = annual_income_cents / 365.0 * float(np.clip(rng.beta(4, 5), 0.1, 0.7))
    discretionary_spending_level = annual_income_cents / 365.0 * float(np.clip(rng.beta(2, 6), 0.02, 0.4))
    spending_volatility = float(np.clip(rng.gamma(shape=2.0, scale=0.08), 0.02, 0.9))

    reserve_level_cents = int(np.clip(rng.lognormal(mean=6.5, sigma=1.3), 0, 50_000_00))
    debt_burden = float(np.clip(rng.beta(2, 6), 0.0, 0.6))
    obligation_count = int(np.clip(rng.poisson(lam=3.5), 1, 9))
    credit_utilization = float(np.clip(rng.beta(2, 3), 0.0, 0.98))

    shock_frequency = float(np.clip(rng.gamma(shape=1.5, scale=1.0), 0.1, 6.0))  # shocks / year
    shock_severity = float(np.clip(rng.beta(2, 5), 0.05, 1.0))
    recovery_duration_days = int(np.clip(rng.gamma(shape=2.0, scale=15.0), 5, 180))

    num_accounts = int(np.clip(rng.poisson(lam=1.8) + 1, 1, 5))

    daily_income_equivalent = annual_income_cents / 365.0
    return HouseholdParams(
        household_id=household_id,
        num_accounts=num_accounts,
        income_amount_cents=int(daily_income_equivalent * _PAY_PERIOD_DAYS[income_frequency]),
        income_frequency=str(income_frequency),
        income_reliability=income_reliability,
        income_volatility=income_volatility,
        fixed_expense_ratio=fixed_expense_ratio,
        essential_spending_level=essential_spending_level,
        discretionary_spending_level=discretionary_spending_level,
        spending_volatility=spending_volatility,
        reserve_level_cents=reserve_level_cents,
        debt_burden=debt_burden,
        obligation_count=obligation_count,
        credit_utilization=credit_utilization,
        shock_frequency=shock_frequency,
        shock_severity=shock_severity,
        recovery_duration_days=recovery_duration_days,
    )


_PAY_PERIOD_DAYS = {
    "weekly": 7,
    "biweekly": 14,
    "semimonthly": 15,
    "monthly": 30,
    "hourly_variable": 14,
    "freelance": 21,
}
