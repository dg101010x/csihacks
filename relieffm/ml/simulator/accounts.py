"""Account generation. One primary checking account always exists; savings,
credit card, and loan accounts are added based on household parameters.
"""
from __future__ import annotations

import numpy as np

from relief_contracts.schemas import AccountState, AccountType

from .types import HouseholdParams


def generate_accounts(
    params: HouseholdParams, rng: np.random.Generator
) -> tuple[list[AccountState], dict[str, int], dict[str, str]]:
    """Returns (accounts, starting_balance_cents by account_id, role -> account_id)."""

    roles: dict[str, str] = {}
    accounts: list[AccountState] = []
    balances: dict[str, int] = {}

    checking_id = f"{params.household_id}_acct_checking"
    # median ~= exp(11.5) cents =~ $987; log-space mean chosen in cents, not
    # dollars -- section 43's realism check is what caught this the first
    # time (99% of households were going negative within days regardless
    # of income, because starting balances were drawing a median of $13).
    checking_balance = int(np.clip(rng.lognormal(mean=11.5, sigma=0.9), 50_00, 40_000_00))
    accounts.append(
        AccountState(
            account_id=checking_id,
            account_type=AccountType.CHECKING,
            account_subtype="checking",
            current_balance_cents=checking_balance,
            available_balance_cents=checking_balance,
            data_freshness_hours=float(rng.uniform(0.5, 12.0)),
        )
    )
    balances[checking_id] = checking_balance
    roles["checking"] = checking_id

    if params.num_accounts >= 2:
        savings_id = f"{params.household_id}_acct_savings"
        savings_balance = int(params.reserve_level_cents * float(rng.uniform(0.6, 1.3)))
        accounts.append(
            AccountState(
                account_id=savings_id,
                account_type=AccountType.SAVINGS,
                account_subtype="savings",
                current_balance_cents=savings_balance,
                available_balance_cents=savings_balance,
                data_freshness_hours=float(rng.uniform(0.5, 24.0)),
            )
        )
        balances[savings_id] = savings_balance
        roles["savings"] = savings_id

    if params.num_accounts >= 3:
        cc_id = f"{params.household_id}_acct_credit_card"
        credit_limit = int(np.clip(rng.lognormal(mean=8.2, sigma=0.6), 50_000, 2_000_000))
        cc_balance = -int(credit_limit * params.credit_utilization)
        accounts.append(
            AccountState(
                account_id=cc_id,
                account_type=AccountType.CREDIT_CARD,
                account_subtype="credit_card",
                current_balance_cents=cc_balance,
                available_balance_cents=credit_limit + cc_balance,
                credit_limit_cents=credit_limit,
                data_freshness_hours=float(rng.uniform(0.5, 24.0)),
            )
        )
        balances[cc_id] = cc_balance
        roles["credit_card"] = cc_id

    if params.num_accounts >= 4:
        loan_id = f"{params.household_id}_acct_loan"
        principal = -int(np.clip(rng.lognormal(mean=9.5, sigma=0.7), 200_000, 5_000_000))
        accounts.append(
            AccountState(
                account_id=loan_id,
                account_type=AccountType.LOAN,
                account_subtype="auto_loan",
                current_balance_cents=principal,
                available_balance_cents=0,
                data_freshness_hours=float(rng.uniform(1.0, 48.0)),
            )
        )
        balances[loan_id] = principal
        roles["loan"] = loan_id

    return accounts, balances, roles
