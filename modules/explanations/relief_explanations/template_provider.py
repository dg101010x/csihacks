from __future__ import annotations

from relief_contracts import ForecastResponseV1
from relief_interventions import InterventionCandidateV1
from relief_resilience import ResilienceScoreV1

from .models import ExplanationV1
from .provider import ExplanationProvider

_RISK_THRESHOLD = 0.15

_GENERIC_DISCLOSURE = "This explanation describes a simulated estimate, not financial or legal advice."


class TemplateExplanationProvider(ExplanationProvider):
    """The deterministic fallback (Section 63) — rule-based composition of
    fields other modules already computed. A LangChainExplanationProvider
    can implement the same ExplanationProvider interface once that
    infrastructure exists; nothing calling this interface needs to change."""

    def explain_forecast_risk(self, forecast: ForecastResponseV1) -> ExplanationV1:
        reserve_prob = forecast.distress_probabilities.essential_reserve_violation
        negative_prob = forecast.distress_probabilities.negative_balance

        if reserve_prob < _RISK_THRESHOLD and negative_prob < _RISK_THRESHOLD:
            return ExplanationV1(
                headline="No near-term liquidity risk detected.",
                summary=(
                    f"The forecast puts the chance of dropping below the essential reserve at "
                    f"{reserve_prob:.0%} over this window, well within a comfortable range."
                ),
                supporting_points=[],
                disclosure=_GENERIC_DISCLOSURE,
                confidence=forecast.confidence,
                generated_by="template",
            )

        top_factors = sorted(forecast.reason_factors, key=lambda f: f.weight, reverse=True)
        return ExplanationV1(
            headline=f"{reserve_prob:.0%} chance of falling below the essential reserve in this window.",
            summary=(
                top_factors[0].description
                if top_factors
                else "Projected cash flow crosses the essential reserve threshold at least once in this window."
            ),
            supporting_points=[f.description for f in top_factors],
            disclosure=_GENERIC_DISCLOSURE,
            confidence=forecast.confidence,
            generated_by="template",
        )

    def explain_resilience_score(self, score: ResilienceScoreV1) -> ExplanationV1:
        strongest = next((c for c in score.components if c.key == score.primary_stabilizing_factor), None)
        weakest = next((c for c in score.components if c.key == score.primary_weakness), None)

        summary_parts = []
        if strongest is not None:
            summary_parts.append(f"{strongest.label} is the strongest contributor at {strongest.score:.0f}/100.")
        if weakest is not None:
            summary_parts.append(f"{weakest.label} is the weakest at {weakest.score:.0f}/100.")
        if not summary_parts:
            summary_parts.append("All components are contributing evenly, with no single standout factor.")

        ranked_components = sorted(score.components, key=lambda c: c.score)
        return ExplanationV1(
            headline=f"Resilience score: {score.overall:.0f}/100 ({score.trend.value}).",
            summary=" ".join(summary_parts),
            supporting_points=[f"{c.label}: {c.score:.0f}/100" for c in ranked_components],
            disclosure=score.disclosure,
            confidence=score.confidence,
            generated_by="template",
        )

    def explain_intervention_package(self, package: InterventionCandidateV1) -> ExplanationV1:
        return ExplanationV1(
            headline=package.label,
            summary=package.ranking_reason,
            supporting_points=[a.display_name for a in package.actions],
            disclosure=_GENERIC_DISCLOSURE,
            confidence=package.confidence,
            generated_by="template",
        )
