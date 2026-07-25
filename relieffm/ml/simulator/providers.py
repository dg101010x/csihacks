"""Simulated provider capability rules (section 12.4, section 39, section 41).

ReliefFM only ever sees *whether* capability information exists — never a
recommendation. This module is Tier Two synthetic ground truth for the
intervention pair generator, not a real provider integration, and every
obligation touched by it is labeled `provider_capability_known=True` with
`source_type=simulated` so nothing here is mistaken for authoritative
provider policy (that stays owned by Plan Two).
"""
from __future__ import annotations

from relief_contracts.schemas import ObligationType

_CAPABILITIES: dict[ObligationType, set[str]] = {
    ObligationType.RENT: {"delay_payment", "hardship_program"},
    ObligationType.MORTGAGE: {"delay_payment", "hardship_program", "refinance"},
    ObligationType.AUTO_LOAN: {"delay_payment", "split_payment", "hardship_program", "refinance"},
    ObligationType.PERSONAL_LOAN: {"delay_payment", "split_payment", "hardship_program"},
    ObligationType.CREDIT_CARD_MINIMUM: {"reduce_payment", "hardship_program"},
    ObligationType.INSURANCE_PREMIUM: {"delay_payment", "waive_fee"},
    ObligationType.UTILITY: {"delay_payment", "waive_fee", "split_payment"},
    ObligationType.SUBSCRIPTION: {"pause_subscription"},
    ObligationType.BNPL: {"delay_payment", "split_payment"},
    ObligationType.MEDICAL_PAYMENT_PLAN: {"split_payment", "reduce_payment", "hardship_program"},
}

_BASE_COST_CENTS: dict[str, int] = {
    "delay_payment": 500,
    "split_payment": 0,
    "waive_fee": 0,
    "pause_subscription": 0,
    "hardship_program": 0,
    "reduce_payment": 0,
    "refinance": 2500,
}


def available_actions(obligation_type: ObligationType) -> set[str]:
    return set(_CAPABILITIES.get(obligation_type, set()))


def modification_cost_cents(action_type: str) -> int:
    return _BASE_COST_CENTS.get(action_type, 0)
