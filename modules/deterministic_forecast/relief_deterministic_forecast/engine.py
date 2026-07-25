from __future__ import annotations

import statistics
import uuid
from datetime import datetime, timedelta
from typing import Optional

from relief_contracts import (
    DailySummaryEntryV1,
    ForecastResponseV1,
    HouseholdSnapshotV1,
    ReasonFactorV1,
    TrajectoryPointV1,
)

from .projection import project_events
from .reserve import compute_essential_reserve_cents

# 80% central interval — wide enough to be informative, narrow enough that
# "lower/upper" reads as a real band rather than a worst case.
_BAND_Z = 1.28

# A day's reserve-violation probability below this isn't worth citing a
# specific obligation for — matches the empty reason_factors on a healthy
# baseline forecast (Section 67).
_REASON_FACTOR_THRESHOLD = 0.15
_MAX_REASON_FACTORS = 5


def _normalize_to_midnight(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _daily_volatility_cents(snapshot: HouseholdSnapshotV1) -> float:
    """Base day-1 standard deviation for the balance random walk. Scaled off
    the largest single scheduled obligation amount — a household with bigger
    payments has more single-day swing to be uncertain about. Floors at a
    small flat amount so a household with no obligations yet isn't treated
    as perfectly certain."""
    amounts = [o.scheduled_amount_cents for o in snapshot.obligations if o.status == "active"]
    largest = max(amounts) if amounts else 0
    return max(500.0, largest * 0.05)


def _confidence_and_warnings(snapshot: HouseholdSnapshotV1) -> tuple[float, bool, list[str]]:
    warnings: list[str] = []
    confidence = 0.95
    is_stale = False

    stale_accounts = [a for a in snapshot.accounts if a.data_status != "current"]
    if stale_accounts:
        is_stale = True
        confidence -= 0.03 * len(stale_accounts)
        warnings.append(f"{len(stale_accounts)} account(s) have stale or unavailable balance data.")

    unconfirmed = [o for o in snapshot.obligations if not o.consumer_confirmed]
    if unconfirmed:
        confidence -= 0.02 * len(unconfirmed)
        warnings.append(f"{len(unconfirmed)} obligation(s) are not yet consumer-confirmed.")

    return max(0.5, round(confidence, 2)), is_stale, warnings


def _build(
    snapshot: HouseholdSnapshotV1,
    *,
    provider: str,
    horizon_days: int,
    as_of: Optional[datetime],
    request_id: Optional[str],
    project_forward: bool,
    model_uncertainty: bool,
) -> ForecastResponseV1:
    as_of = _normalize_to_midnight(as_of or snapshot.generated_at)
    horizon_end = as_of + timedelta(days=horizon_days)

    events = (
        project_events(snapshot, horizon_end=horizon_end)
        if project_forward
        else sorted(snapshot.known_future_events, key=lambda e: e.effective_at)
    )
    future_events = [e for e in events if e.effective_at > as_of and e.effective_at <= horizon_end]

    by_date: dict = {}
    for event in future_events:
        by_date.setdefault(event.effective_at.date(), []).append(event)

    essential_reserve = compute_essential_reserve_cents(snapshot.obligations)
    daily_vol = _daily_volatility_cents(snapshot) if model_uncertainty else 0.0

    running_balance = sum(a.current_balance_cents for a in snapshot.accounts)
    trajectories: list[TrajectoryPointV1] = []
    daily_summary: list[DailySummaryEntryV1] = []
    reason_candidates: dict[str, ReasonFactorV1] = {}
    max_reserve_violation = 0.0
    max_negative_balance = 0.0
    max_missed_obligation = 0.0

    for event_date in sorted(by_date.keys()):
        day_events = by_date[event_date]
        starting_balance = running_balance
        inflow = sum(e.amount_cents for e in day_events if e.direction == "inflow")
        outflow = sum(e.amount_cents for e in day_events if e.direction == "outflow")
        ending_balance = starting_balance + inflow - outflow

        days_elapsed = max(1, (event_date - as_of.date()).days)
        std = daily_vol * (days_elapsed ** 0.5)

        if std > 0:
            dist = statistics.NormalDist(ending_balance, std)
            reserve_prob = dist.cdf(essential_reserve)
            negative_prob = dist.cdf(0)
            lower = round(ending_balance - _BAND_Z * std)
            upper = round(ending_balance + _BAND_Z * std)
        else:
            reserve_prob = 1.0 if ending_balance < essential_reserve else 0.0
            negative_prob = 1.0 if ending_balance < 0 else 0.0
            lower = upper = ending_balance

        max_reserve_violation = max(max_reserve_violation, reserve_prob)
        max_negative_balance = max(max_negative_balance, negative_prob)

        # Missed-obligation risk: check each obligation-linked outflow against
        # the balance available immediately before it, walking the day's
        # events in order rather than using the day's net change.
        intra_day_balance = starting_balance
        for event in sorted(day_events, key=lambda e: e.effective_at):
            if event.direction == "inflow":
                intra_day_balance += event.amount_cents
                continue
            pre_event_balance = intra_day_balance
            if std > 0:
                missed_prob = statistics.NormalDist(pre_event_balance, std).cdf(event.amount_cents)
            else:
                missed_prob = 1.0 if pre_event_balance < event.amount_cents else 0.0
            if event.obligation_id:
                max_missed_obligation = max(max_missed_obligation, missed_prob)
            intra_day_balance -= event.amount_cents

            if reserve_prob >= _REASON_FACTOR_THRESHOLD and event.obligation_id:
                label = event.merchant_name or event.obligation_id
                candidate = ReasonFactorV1(
                    factor=f"obligation:{event.obligation_id}",
                    weight=round(min(1.0, reserve_prob), 2),
                    description=(
                        f"{label} ({event.currency} {event.amount_cents / 100:.2f}) due "
                        f"{event_date.isoformat()} reduces balance toward the essential reserve."
                    ),
                )
                existing = reason_candidates.get(event.obligation_id)
                if existing is None or candidate.weight > existing.weight:
                    reason_candidates[event.obligation_id] = candidate

        trajectories.append(
            TrajectoryPointV1(
                scenario_index=0,
                event_date=event_date,
                starting_balance_cents=starting_balance,
                inflow_cents=inflow,
                outflow_cents=outflow,
                ending_balance_cents=ending_balance,
                essential_reserve_cents=essential_reserve,
            )
        )
        daily_summary.append(
            DailySummaryEntryV1(
                event_date=event_date,
                median_ending_balance_cents=ending_balance,
                lower_ending_balance_cents=lower,
                upper_ending_balance_cents=upper,
                reserve_violation_probability=round(reserve_prob, 4),
            )
        )
        running_balance = ending_balance

    reason_factors = sorted(reason_candidates.values(), key=lambda r: r.weight, reverse=True)[:_MAX_REASON_FACTORS]
    confidence, is_stale, warnings = _confidence_and_warnings(snapshot)
    generated_at = snapshot.generated_at

    return ForecastResponseV1(
        contract_version="1.0.0",
        request_id=request_id or f"req_{uuid.uuid4().hex[:12]}",
        forecast_id=f"forecast_{uuid.uuid4().hex[:12]}",
        provider=provider,
        provider_version="1.0.0",
        generated_at=generated_at,
        valid_until=generated_at + timedelta(hours=1),
        confidence=confidence,
        is_stale=is_stale,
        warnings=warnings,
        daily_summary=daily_summary,
        trajectories=trajectories,
        distress_probabilities={
            "negative_balance": round(max_negative_balance, 4),
            "essential_reserve_violation": round(max_reserve_violation, 4),
            "missed_obligation": round(max_missed_obligation, 4),
        },
        reason_factors=reason_factors,
        model_metadata=None,
    )


def generate_forecast(
    snapshot: HouseholdSnapshotV1,
    *,
    horizon_days: int = 30,
    as_of: Optional[datetime] = None,
    request_id: Optional[str] = None,
) -> ForecastResponseV1:
    """The deterministic provider (Section 8/11) — projects obligations and
    detected recurring income forward, models day-by-day balance uncertainty
    as a random walk, and derives distress probabilities from it. This is the
    ForecastProviderName.deterministic path; ReliefFM (services/model_gateway)
    is a drop-in replacement behind the same ForecastResponseV1 shape."""
    return _build(
        snapshot,
        provider="deterministic",
        horizon_days=horizon_days,
        as_of=as_of,
        request_id=request_id,
        project_forward=True,
        model_uncertainty=True,
    )


def generate_mock_forecast(
    snapshot: HouseholdSnapshotV1,
    *,
    horizon_days: int = 30,
    as_of: Optional[datetime] = None,
    request_id: Optional[str] = None,
) -> ForecastResponseV1:
    """The trivial provider: only the snapshot's explicit known_future_events,
    no projection, no uncertainty band. Used for health checks and tests
    where the deterministic engine's obligation/income projection would add
    noise to what's being tested."""
    return _build(
        snapshot,
        provider="mock",
        horizon_days=horizon_days,
        as_of=as_of,
        request_id=request_id,
        project_forward=False,
        model_uncertainty=False,
    )
