from __future__ import annotations

import hashlib
import itertools
from typing import Optional

from relief_contracts import HouseholdSnapshotV1
from relief_contracts.shared import ProviderCapabilityV1
from relief_deterministic_forecast import generate_forecast
from relief_elasticity import ObligationElasticityV1, compute_elasticity_for_household

from .actions import build_atomic_actions
from .models import InterventionActionV1, InterventionCandidateV1, RemainingRisk, Reversibility, UserEffort
from .simulate import simulate_package

# Below this the baseline forecast isn't distressed enough to warrant
# recommending anything — matches the reason-factor threshold in
# deterministic_forecast so "is there a problem" is judged consistently.
_RISK_THRESHOLD = 0.15
_MAX_OBLIGATIONS_CONSIDERED = 5
_MAX_SINGLES_FOR_PAIRING = 4
_TOP_N_PACKAGES = 3

_REVERSIBILITY_RANK = {"fully_reversible": 0, "partially_reversible": 1, "irreversible": 2}
_PROVIDER_ACCEPTANCE_BY_EVIDENCE = {
    "confirmed_product_contract": 0.9,
    "provider_structured_policy": 0.85,
    "provider_published_policy_document": 0.8,
    "consumer_supplied_contract_information": 0.7,
    "simulated_demonstration_policy": 0.75,
    "unknown": 0.5,
}


def _package_id(action_ids: tuple) -> str:
    digest = hashlib.sha1(":".join(sorted(action_ids)).encode()).hexdigest()[:10]
    return f"int_{digest}"


def _combined_reversibility(values: list[str]) -> Reversibility:
    worst = max(values, key=lambda r: _REVERSIBILITY_RANK[r]) if values else "fully_reversible"
    return Reversibility(worst)


def _action_cost_cents(action: InterventionActionV1, elasticity: ObligationElasticityV1) -> int:
    # split_payment and delay_payment were both built (in actions.py) using
    # elasticity.delay_tolerance_days as the delay window, so that same
    # figure is the right basis for the cost-of-delay charge here.
    if action.action_type in ("split_payment", "delay_payment"):
        return round(elasticity.cost_of_delay_cents_per_day * elasticity.delay_tolerance_days)
    return 0


def _provider_acceptance(
    actions: list[InterventionActionV1], capabilities: list[ProviderCapabilityV1]
) -> Optional[float]:
    provider_actions = [a for a in actions if a.provider_capability_id is not None]
    if not provider_actions:
        return None
    scores = []
    for a in provider_actions:
        cap = next((c for c in capabilities if f"{c.provider_id}:{c.action_type}" == a.provider_capability_id), None)
        evidence = cap.evidence_source.value if cap else "unknown"
        scores.append(_PROVIDER_ACCEPTANCE_BY_EVIDENCE.get(evidence, 0.5))
    return round(sum(scores) / len(scores), 2)


def _user_effort(actions: list[InterventionActionV1]) -> UserEffort:
    if len(actions) >= 3:
        return UserEffort.high
    if len(actions) == 2 or any(a.execution_mode.value == "draft_only" for a in actions):
        return UserEffort.medium
    return UserEffort.low


def _required_approvals(actions: list[InterventionActionV1]) -> list[str]:
    ordered: list[str] = []
    for a in actions:
        if a.provider_capability_id is not None:
            provider_id = a.provider_capability_id.split(":")[0]
            entry = f"provider:{provider_id}"
            if entry not in ordered:
                ordered.append(entry)
        entry = f"consumer:{a.obligation_id}"
        if entry not in ordered:
            ordered.append(entry)
    return ordered


def _describe(actions: list[InterventionActionV1]) -> str:
    names = [a.display_name[0].lower() + a.display_name[1:] for a in actions]
    sentence = " and ".join(names) + "."
    return sentence[0].upper() + sentence[1:]


def _ranking_reason(cleared: bool, added_cost_cents: int, provider_action_count: int) -> str:
    outcome = "Fully clears the projected reserve violation" if cleared else "Reduces but does not eliminate the projected reserve violation"
    cost = "at zero added cost" if added_cost_cents == 0 else f"for {added_cost_cents / 100:.2f} in added cost"
    provider_note = "" if provider_action_count == 0 else f", pending {provider_action_count} provider approval(s)"
    return f"{outcome}, {cost}{provider_note}."


def _score(cleared: bool, added_cost_cents: int, effort: UserEffort, confidence: float) -> float:
    effort_penalty = {"low": 0, "medium": 5, "high": 12}[effort.value]
    return (1000 if cleared else 0) - added_cost_cents / 100 - effort_penalty + confidence * 5


def _build_candidate(
    snapshot: HouseholdSnapshotV1,
    actions: list[InterventionActionV1],
    capabilities: list[ProviderCapabilityV1],
    elasticity_by_obligation: dict,
    horizon_days: int,
) -> tuple[InterventionCandidateV1, float]:
    result = simulate_package(snapshot, actions, horizon_days=horizon_days)
    starting_total = sum(a.current_balance_cents for a in snapshot.accounts)
    new_min_balance = min((p.ending_balance_cents for p in result.trajectories), default=starting_total)
    reserve = result.trajectories[0].essential_reserve_cents if result.trajectories else 0
    remaining_risk = RemainingRisk(
        negative_balance=new_min_balance < 0,
        essential_reserve_violation=new_min_balance < reserve,
    )
    cleared = not remaining_risk.negative_balance and not remaining_risk.essential_reserve_violation

    added_cost = sum(_action_cost_cents(a, elasticity_by_obligation[a.obligation_id]) for a in actions)
    effort = _user_effort(actions)
    reversibility_values = [
        "fully_reversible" if a.action_type == "hardship_request" else elasticity_by_obligation[a.obligation_id].reversibility.value
        for a in actions
    ]
    confidence = round(sum(elasticity_by_obligation[a.obligation_id].confidence for a in actions) / len(actions), 2)
    provider_action_count = sum(1 for a in actions if a.provider_capability_id is not None)

    candidate = InterventionCandidateV1(
        package_id=_package_id(tuple(a.action_id for a in actions)),
        label="",
        description=_describe(actions),
        actions=actions,
        added_cost_cents=added_cost,
        new_minimum_balance_cents=new_min_balance,
        remaining_risk=remaining_risk,
        required_approvals=_required_approvals(actions),
        user_effort=effort,
        provider_acceptance_probability=_provider_acceptance(actions, capabilities),
        reversibility=_combined_reversibility(reversibility_values),
        constitution_compatible=True,
        confidence=confidence,
        ranking_reason=_ranking_reason(cleared, added_cost, provider_action_count),
    )
    return candidate, _score(cleared, added_cost, effort, confidence)


def generate_intervention_packages(
    snapshot: HouseholdSnapshotV1, *, horizon_days: int = 30
) -> list[InterventionCandidateV1]:
    """Section 60-61: builds atomic actions from elasticity, combines them
    into candidate packages (singles, then pairs across distinct
    obligations), simulates each through the deterministic forecast engine,
    and ranks by whether it clears the projected risk, added cost, and
    effort. Returns [] on a healthy baseline — there's nothing to
    recommend against.
    """
    baseline = generate_forecast(snapshot, horizon_days=horizon_days)
    if (
        baseline.distress_probabilities.essential_reserve_violation < _RISK_THRESHOLD
        and baseline.distress_probabilities.negative_balance < _RISK_THRESHOLD
    ):
        return []

    elasticities = compute_elasticity_for_household(snapshot.obligations, snapshot.provider_capabilities)
    elasticity_by_obligation = {e.obligation_id: e for e in elasticities}

    obligations_considered = sorted(
        (o for o in snapshot.obligations if o.obligation_id in elasticity_by_obligation),
        key=lambda o: o.essentiality_score * o.scheduled_amount_cents,
        reverse=True,
    )[:_MAX_OBLIGATIONS_CONSIDERED]

    atomic_actions: list[InterventionActionV1] = []
    for obligation in obligations_considered:
        atomic_actions.extend(build_atomic_actions(obligation, elasticity_by_obligation[obligation.obligation_id]))

    if not atomic_actions:
        return []

    singles = [
        _build_candidate(snapshot, [action], snapshot.provider_capabilities, elasticity_by_obligation, horizon_days)
        for action in atomic_actions
    ]
    singles.sort(key=lambda pair: pair[1], reverse=True)

    pairable_actions = [candidate.actions[0] for candidate, _score_value in singles[:_MAX_SINGLES_FOR_PAIRING]]
    scored: list[tuple[InterventionCandidateV1, float]] = list(singles)
    for action_a, action_b in itertools.combinations(pairable_actions, 2):
        if action_a.obligation_id == action_b.obligation_id:
            continue  # alternatives on the same obligation, not stackable
        scored.append(
            _build_candidate(
                snapshot, [action_a, action_b], snapshot.provider_capabilities, elasticity_by_obligation, horizon_days
            )
        )

    scored.sort(key=lambda pair: pair[1], reverse=True)
    ranked = [candidate for candidate, _score_value in scored]

    selected: list[InterventionCandidateV1] = [ranked[0].model_copy(update={"label": "Recommended balance"})]
    remaining = ranked[1:]

    if remaining:
        lowest_cost = min(remaining, key=lambda c: c.added_cost_cents)
        if lowest_cost.package_id != selected[0].package_id:
            selected.append(lowest_cost.model_copy(update={"label": "Lowest added cost"}))

    if len(selected) < _TOP_N_PACKAGES and remaining:
        chosen_ids = {c.package_id for c in selected}
        candidates_left = [c for c in remaining if c.package_id not in chosen_ids]
        if candidates_left:
            lowest_provider_mod = min(
                candidates_left, key=lambda c: sum(1 for a in c.actions if a.provider_capability_id is not None)
            )
            selected.append(lowest_provider_mod.model_copy(update={"label": "Lowest provider modification"}))

    return selected[:_TOP_N_PACKAGES]
