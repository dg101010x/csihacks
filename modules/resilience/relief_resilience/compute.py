from __future__ import annotations

from typing import Optional

from relief_contracts import ForecastResponseV1, HouseholdSnapshotV1
from relief_deterministic_forecast import essential_daily_burn_rate_cents
from relief_recurring_detection import detect_recurring_patterns

from .models import ResilienceComponentV1, ResilienceScoreV1, Trend

_DISCLOSURE = (
    "The Financial Resilience Score estimates short term liquidity capacity. "
    "It is not a credit score and does not determine eligibility for financial products."
)

_TREND_NOISE_FLOOR = 2.0


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _liquidity_component(
    key: str, label: str, weight: float, forecast: ForecastResponseV1, window_days: int, reserve_cents: float
) -> ResilienceComponentV1:
    window_points = [p for p in forecast.trajectories if _days_from_start(forecast, p) <= window_days]
    if window_points:
        min_balance = min(p.ending_balance_cents for p in window_points)
    else:
        min_balance = forecast.trajectories[0].starting_balance_cents if forecast.trajectories else 0
    ratio = (min_balance / reserve_cents) if reserve_cents > 0 else 1.0
    return ResilienceComponentV1(
        key=key, label=label, weight=weight, score=_clamp(ratio * 50), confidence=forecast.confidence
    )


def _days_from_start(forecast: ForecastResponseV1, point) -> int:
    if not forecast.trajectories:
        return 0
    return (point.event_date - forecast.trajectories[0].event_date).days


def _collision_component(forecast: ForecastResponseV1) -> ResilienceComponentV1:
    if not forecast.trajectories:
        return ResilienceComponentV1(
            key="obligation_collision_risk", label="Obligation collision risk", weight=0.2, score=100, confidence=0.5
        )
    liquidity = max(1, forecast.trajectories[0].starting_balance_cents)
    max_single_day_outflow = max((p.outflow_cents for p in forecast.trajectories), default=0)
    ratio = max_single_day_outflow / liquidity
    return ResilienceComponentV1(
        key="obligation_collision_risk",
        label="Obligation collision risk",
        weight=0.2,
        score=_clamp(100 * (1 - ratio)),
        confidence=forecast.confidence,
    )


def _income_stability_component(snapshot: HouseholdSnapshotV1) -> ResilienceComponentV1:
    inflow_patterns = [
        p for p in detect_recurring_patterns(snapshot.recent_events) if p.direction == "inflow" and p.recurrence_rule
    ]
    if not inflow_patterns:
        return ResilienceComponentV1(
            key="income_stability", label="Income stability", weight=0.15, score=40, confidence=0.4
        )
    primary = max(inflow_patterns, key=lambda p: len(p.event_ids))
    variation = 0.5 * primary.amount_variation_ratio + 0.5 * primary.interval_variation_ratio
    return ResilienceComponentV1(
        key="income_stability",
        label="Income stability",
        weight=0.15,
        score=_clamp(100 * (1 - variation)),
        confidence=primary.confidence,
    )


def _emergency_reserve_component(snapshot: HouseholdSnapshotV1) -> ResilienceComponentV1:
    total_balance = sum(a.current_balance_cents for a in snapshot.accounts)
    daily_burn = essential_daily_burn_rate_cents(snapshot.obligations)
    target_30d = daily_burn * 30
    ratio = (total_balance / target_30d) if target_30d > 0 else 1.0
    confidence = 0.85 if target_30d > 0 else 0.5
    return ResilienceComponentV1(
        key="emergency_reserve_coverage",
        label="Emergency reserve coverage",
        weight=0.1,
        score=_clamp(ratio * 50),
        confidence=confidence,
    )


def _trend(overall: float, previous_overall: Optional[float]) -> Trend:
    if previous_overall is None:
        return Trend.stable
    delta = overall - previous_overall
    if delta > _TREND_NOISE_FLOOR:
        return Trend.improving
    if delta < -_TREND_NOISE_FLOOR:
        return Trend.declining
    return Trend.stable


def compute_resilience_score(
    snapshot: HouseholdSnapshotV1,
    forecast: ForecastResponseV1,
    *,
    previous_overall: Optional[float] = None,
) -> ResilienceScoreV1:
    """Weighted blend of five components (Section 22): two liquidity-coverage
    windows, obligation timing collision risk, income stability, and a
    30-day emergency reserve check. Reuses the forecast's own trajectories
    and essential_reserve_cents rather than recomputing projection —
    resilience is a lens on the forecast, not an independent model."""
    reserve_cents = forecast.trajectories[0].essential_reserve_cents if forecast.trajectories else 0

    components = [
        _liquidity_component(
            "seven_day_liquidity_coverage", "Seven day liquidity coverage", 0.3, forecast, 7, reserve_cents
        ),
        _liquidity_component(
            "fourteen_day_essential_coverage",
            "Fourteen day essential coverage",
            0.25,
            forecast,
            14,
            essential_daily_burn_rate_cents(snapshot.obligations) * 14,
        ),
        _collision_component(forecast),
        _income_stability_component(snapshot),
        _emergency_reserve_component(snapshot),
    ]

    overall = round(sum(c.score * c.weight for c in components))
    confidence = round(sum(c.confidence * c.weight for c in components), 2)

    weakest = min(components, key=lambda c: c.score)
    strongest = max(components, key=lambda c: c.score)

    if any(a.data_status == "unavailable" for a in snapshot.accounts):
        data_freshness = "unavailable"
    elif forecast.is_stale:
        data_freshness = "stale"
    else:
        data_freshness = "current"

    return ResilienceScoreV1(
        version="resilience-v1.0.0",
        overall=overall,
        confidence=confidence,
        trend=_trend(overall, previous_overall),
        components=components,
        primary_weakness=weakest.key if weakest.score < 60 else None,
        primary_stabilizing_factor=strongest.key,
        data_freshness=data_freshness,
        disclosure=_DISCLOSURE,
    )
