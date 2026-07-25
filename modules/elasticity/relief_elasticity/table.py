from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ElasticityProfile:
    delay_tolerance_days: int
    amount_flexibility_ratio: float
    cost_of_delay_bps_per_day: int  # basis points of scheduled_amount_cents, per day late
    reversibility: str
    # (action_type, requires_provider_capability)
    candidate_actions: tuple[tuple[str, bool], ...]


# Baseline elasticity by obligation category (Section 40). requires_provider
# actions only ever surface in ObligationElasticityV1.available_actions when
# a matching ProviderCapabilityV1 exists (Section 52's evidence hierarchy) —
# a consumer-side action like pausing a subscription never needs that check.
_PROFILES: dict[str, ElasticityProfile] = {
    "rent": ElasticityProfile(
        delay_tolerance_days=3,
        amount_flexibility_ratio=0.0,
        cost_of_delay_bps_per_day=10,
        reversibility="irreversible",
        candidate_actions=(("delay_payment", True),),
    ),
    "mortgage": ElasticityProfile(
        delay_tolerance_days=15,
        amount_flexibility_ratio=0.0,
        cost_of_delay_bps_per_day=5,
        reversibility="irreversible",
        candidate_actions=(("delay_payment", True), ("term_extension_with_interest", True)),
    ),
    "loan_payment": ElasticityProfile(
        delay_tolerance_days=10,
        amount_flexibility_ratio=0.5,
        cost_of_delay_bps_per_day=3,
        reversibility="partially_reversible",
        candidate_actions=(("split_payment", True), ("delay_payment", True), ("term_extension_with_interest", True)),
    ),
    "credit_card_minimum": ElasticityProfile(
        delay_tolerance_days=25,
        amount_flexibility_ratio=1.0,
        cost_of_delay_bps_per_day=8,
        reversibility="partially_reversible",
        candidate_actions=(("delay_payment", True),),
    ),
    "utility": ElasticityProfile(
        delay_tolerance_days=14,
        amount_flexibility_ratio=0.2,
        cost_of_delay_bps_per_day=4,
        reversibility="partially_reversible",
        candidate_actions=(("delay_payment", True),),
    ),
    "insurance": ElasticityProfile(
        delay_tolerance_days=10,
        amount_flexibility_ratio=0.1,
        cost_of_delay_bps_per_day=2,
        reversibility="irreversible",
        candidate_actions=(("delay_payment", True),),
    ),
    "subscription": ElasticityProfile(
        delay_tolerance_days=30,
        amount_flexibility_ratio=1.0,
        cost_of_delay_bps_per_day=0,
        reversibility="fully_reversible",
        candidate_actions=(("pause_subscription", False), ("cancel_subscription", False)),
    ),
}

_DEFAULT_PROFILE = ElasticityProfile(
    delay_tolerance_days=7,
    amount_flexibility_ratio=0.1,
    cost_of_delay_bps_per_day=5,
    reversibility="partially_reversible",
    candidate_actions=(("delay_payment", True),),
)


def profile_for(obligation_type: str) -> ElasticityProfile:
    return _PROFILES.get(obligation_type, _DEFAULT_PROFILE)
