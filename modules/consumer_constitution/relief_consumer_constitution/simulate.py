from __future__ import annotations

from relief_interventions import InterventionCandidateV1

from .models import ConstitutionRuleV1, ConstitutionSimulationResult, RuleConflict


def simulate_constitution_rule(
    rule: ConstitutionRuleV1,
    packages: list[InterventionCandidateV1],
    existing_rules: list[ConstitutionRuleV1] = (),
) -> ConstitutionSimulationResult:
    """Section 71: which candidate packages this rule would allow/block, and
    whether it conflicts with an already-active rule over the same action
    type. Port of the frontend's simulateConstitutionRule (synthetic-
    adapter.ts) — moved server-side now that a real endpoint exists."""
    allowed: list[str] = []
    blocked: list[str] = []
    for package in packages:
        touches_prohibited = any(a.action_type in rule.prohibited_actions for a in package.actions)
        if touches_prohibited or not package.constitution_compatible:
            blocked.append(package.package_id)
        else:
            allowed.append(package.package_id)

    conflicts: list[RuleConflict] = []
    for existing in existing_rules:
        if existing.rule_id == rule.rule_id:
            continue
        permitted_but_prohibited = [a for a in rule.permitted_actions if a in existing.prohibited_actions]
        prohibited_but_permitted = [a for a in rule.prohibited_actions if a in existing.permitted_actions]
        overlap = permitted_but_prohibited + prohibited_but_permitted
        if overlap:
            conflicts.append(
                RuleConflict(
                    with_rule_id=existing.rule_id,
                    description=f"Conflicts with an existing rule over: {', '.join(overlap)}.",
                )
            )

    return ConstitutionSimulationResult(
        rule=rule, allowed_package_ids=allowed, blocked_package_ids=blocked, conflicts=conflicts
    )
