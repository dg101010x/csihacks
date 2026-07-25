from __future__ import annotations

from abc import ABC, abstractmethod

from relief_contracts import ForecastResponseV1
from relief_interventions import InterventionCandidateV1
from relief_resilience import ResilienceScoreV1

from .models import ExplanationV1


class ExplanationProvider(ABC):
    """Section 63: the seam a real LLM-backed explainer plugs into. Every
    method here takes structured output some other module already computed
    and returns prose describing it — this class never sees raw ledger data,
    so a langchain-backed implementation can't invent numbers that don't
    trace back to a contract field."""

    @abstractmethod
    def explain_forecast_risk(self, forecast: ForecastResponseV1) -> ExplanationV1: ...

    @abstractmethod
    def explain_resilience_score(self, score: ResilienceScoreV1) -> ExplanationV1: ...

    @abstractmethod
    def explain_intervention_package(self, package: InterventionCandidateV1) -> ExplanationV1: ...
