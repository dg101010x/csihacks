from __future__ import annotations

from relief_contracts.shared import ObligationV1, ProviderCapabilityV1

from .models import ObligationElasticityV1
from .table import profile_for


def _has_capability(provider_id: str | None, action_type: str, capabilities: list[ProviderCapabilityV1]) -> bool:
    if provider_id is None:
        return False
    return any(c.provider_id == provider_id and c.action_type == action_type for c in capabilities)


def compute_elasticity(
    obligation: ObligationV1, provider_capabilities: list[ProviderCapabilityV1]
) -> ObligationElasticityV1:
    """Section 40: how much give this obligation has, before the
    intervention optimizer ranks candidate packages against it. A
    consumer-confirmed obligation gets full confidence in its category's
    baseline profile; an unconfirmed (detector-guessed) one is scored more
    cautiously since we can't yet be sure the category classification is
    right."""
    profile = profile_for(obligation.obligation_type)
    available_actions = [
        action
        for action, requires_provider in profile.candidate_actions
        if not requires_provider or _has_capability(obligation.provider_id, action, provider_capabilities)
    ]
    cost_of_delay = round(obligation.scheduled_amount_cents * profile.cost_of_delay_bps_per_day / 10_000)
    confidence = 0.85 if obligation.consumer_confirmed else 0.55

    return ObligationElasticityV1(
        obligation_id=obligation.obligation_id,
        obligation_type=obligation.obligation_type,
        delay_tolerance_days=profile.delay_tolerance_days,
        amount_flexibility_ratio=profile.amount_flexibility_ratio,
        cost_of_delay_cents_per_day=cost_of_delay,
        available_actions=available_actions,
        reversibility=profile.reversibility,
        confidence=confidence,
    )


def compute_elasticity_for_household(
    obligations: list[ObligationV1], provider_capabilities: list[ProviderCapabilityV1]
) -> list[ObligationElasticityV1]:
    return [
        compute_elasticity(o, provider_capabilities)
        for o in obligations
        if o.status == "active"
    ]
