"""Compiles ReliefSim's internal `HouseholdRecord` into:
  * a canonical `HouseholdSnapshotV1` (section 12's six token classes, as-of
    state only — this is what a real Plan Two snapshot looks like)
  * `NanoTargets` — ground truth for the direct trajectory + distress heads
    that ReliefFM Nano actually trains (section 25, section 26). Nano does
    not do individual event generation (that's Mini's horizon event
    decoder, section 21), so targets here are aggregate daily series, not
    per-event labels.

This is the boundary the spec calls out in section 44 ("each adapter must
produce the canonical event representation") — applied here to our own
simulator instead of a public dataset.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from relief_contracts.schemas import (
    AccountType,
    Direction,
    EventStatus,
    EventType,
    HistoricalEvent,
    HouseholdSnapshotV1,
    HouseholdState,
    KnownFutureEvent,
    KnownFutureEventSource,
    RecurrenceState,
    SourceType,
)

from ml.simulator.ledger import daily_balances, day_bucket
from ml.simulator.types import HouseholdRecord, SimEvent

_ESSENTIAL_EVENT_TYPES = {
    "rent_payment",
    "mortgage_payment",
    "auto_loan_payment",
    "personal_loan_payment",
    "credit_card_payment",
    "insurance_premium",
    "utility_bill",
    "bnpl_payment",
    "medical_payment",
    "shock_expense",
}
_ESSENTIAL_MERCHANT_CATEGORIES = {"groceries", "fuel", "pharmacy", "utilities_variable"}
_DISTRESS_HORIZONS = (7, 14, 30, 60, 90)


def household_record_to_snapshot(record: HouseholdRecord) -> HouseholdSnapshotV1:
    liquid_accounts = [
        a for a in record.accounts if a.account_type in (AccountType.CHECKING, AccountType.SAVINGS)
    ]
    total_liquid = sum(a.current_balance_cents for a in liquid_accounts)
    available_liquid = sum(a.available_balance_cents for a in liquid_accounts)

    state = HouseholdState(
        total_liquid_balance_cents=total_liquid,
        available_balance_cents=available_liquid,
        num_accounts=len(record.accounts),
        num_obligations=len(record.obligations),
        essential_reserve_cents=record.params.reserve_level_cents,
        data_freshness_hours=max((a.data_freshness_hours for a in record.accounts), default=0.0),
        snapshot_completeness=1.0,
    )

    historical = [_to_historical_event(e) for e in record.historical_events()]
    known_future = [_to_known_future_event(e) for e in record.known_future_events()]

    return HouseholdSnapshotV1(
        household_id=record.params.household_id,
        currency="USD",
        as_of=record.as_of,
        household_state=state,
        accounts=record.accounts,
        obligations=record.obligations,
        historical_events=historical,
        known_future_events=known_future,
    )


def _to_historical_event(e: SimEvent) -> HistoricalEvent:
    return HistoricalEvent(
        event_id=e.event_id,
        event_type=EventType(e.event_type),
        event_status=EventStatus(e.event_status),
        amount_cents=e.amount_cents,
        direction=Direction(e.direction),
        account_id=e.account_id,
        merchant_category=e.merchant_category,
        recurrence_state=RecurrenceState(e.recurrence_state),
        transaction_confidence=e.transaction_confidence,
        source_type=SourceType(e.source_type),
        occurrence_time=e.occurrence_time,
        effective_time=e.effective_time,
    )


def _to_known_future_event(e: SimEvent) -> KnownFutureEvent:
    assert e.known_source is not None
    return KnownFutureEvent(
        event_id=e.event_id,
        event_type=EventType(e.event_type),
        amount_cents=e.amount_cents,
        direction=Direction(e.direction),
        account_id=e.account_id,
        effective_time=e.effective_time,
        source=KnownFutureEventSource(e.known_source),
        obligation_id=e.obligation_id,
    )


@dataclass
class NanoTargets:
    """Section 23's known-event clamping, applied at target-construction time
    rather than only at inference: `known_daily_balance_cents` is the
    deterministic projection from `as_of` using ONLY known-future events —
    Nano never predicts it. The model's regression targets
    (`uncertain_daily_*`) cover only the residual driven by uncertain
    events. `daily_balance_cents` (full ledger, all events) is the actual
    ground truth, used for evaluation and distress labels, and — since
    known ∪ uncertain partitions the future event set exactly —
    known_daily_balance_cents[-1] plus the cumulative uncertain deltas
    reconstructs it exactly, which is the accounting-consistency check
    (section 57) for this architecture.
    """

    horizon_days: int
    daily_balance_cents: list[int]
    known_daily_balance_cents: list[int]
    uncertain_daily_inflow_cents: list[int]
    uncertain_daily_essential_outflow_cents: list[int]
    uncertain_daily_discretionary_outflow_cents: list[int]
    distress_negative_balance: dict[int, bool] = field(default_factory=dict)
    distress_reserve_violation: dict[int, bool] = field(default_factory=dict)
    distress_missed_obligation: dict[int, bool] = field(default_factory=dict)


def household_record_to_targets(record: HouseholdRecord) -> NanoTargets:
    checking_id = record.accounts[0].account_id
    horizon_days = (record.horizon_end - record.as_of).days
    start_balance = record.account_starting_balances_cents[checking_id]

    balances = daily_balances(record.events, start_balance, record.as_of, record.horizon_end, checking_id)
    assert len(balances) == horizon_days

    known_events_only = [e for e in record.events if e.known or e.occurrence_time <= record.as_of]
    known_balances = daily_balances(known_events_only, start_balance, record.as_of, record.horizon_end, checking_id)

    inflow = [0] * horizon_days
    essential_outflow = [0] * horizon_days
    discretionary_outflow = [0] * horizon_days
    obligation_day_has_shortfall: dict[int, bool] = {}

    for e in record.events:
        if e.account_id != checking_id or e.occurrence_time <= record.as_of:
            continue
        day_idx = day_bucket(e.occurrence_time, record.as_of)
        if not (0 <= day_idx < horizon_days):
            continue
        if e.obligation_id is not None and balances[day_idx] < 0:
            obligation_day_has_shortfall[day_idx] = True
        if e.known:
            continue  # deterministic component — not a model target
        if e.direction == "inflow":
            inflow[day_idx] += e.amount_cents
        else:
            if _is_essential(e):
                essential_outflow[day_idx] += e.amount_cents
            else:
                discretionary_outflow[day_idx] += e.amount_cents

    reserve = record.params.reserve_level_cents
    distress_negative: dict[int, bool] = {}
    distress_reserve: dict[int, bool] = {}
    distress_missed: dict[int, bool] = {}
    for h in _DISTRESS_HORIZONS:
        if h > horizon_days:
            continue
        window = balances[:h]
        distress_negative[h] = any(b < 0 for b in window)
        distress_reserve[h] = any(b < reserve for b in window)
        distress_missed[h] = any(obligation_day_has_shortfall.get(d, False) for d in range(h))

    return NanoTargets(
        horizon_days=horizon_days,
        daily_balance_cents=balances,
        known_daily_balance_cents=known_balances,
        uncertain_daily_inflow_cents=inflow,
        uncertain_daily_essential_outflow_cents=essential_outflow,
        uncertain_daily_discretionary_outflow_cents=discretionary_outflow,
        distress_negative_balance=distress_negative,
        distress_reserve_violation=distress_reserve,
        distress_missed_obligation=distress_missed,
    )


def _is_essential(e: SimEvent) -> bool:
    if e.event_type in _ESSENTIAL_EVENT_TYPES:
        return True
    if e.event_type == "purchase":
        return e.merchant_category in _ESSENTIAL_MERCHANT_CATEGORIES
    return False


# --------------------------------------------------------------------------
# Mini-only additions: horizon event-set targets (section 21) and
# intervention-pair training examples (section 41/65). Nano doesn't use
# either of these.
# --------------------------------------------------------------------------

@dataclass
class EventSetTargets:
    """Ground truth for the horizon event-set decoder's matching loss.
    Padded/truncated to `config.max_event_slots`; `valid_mask` marks the
    first `n_true_events` slots as real, the rest as padding."""

    n_true_events: int
    event_type_idx: list[int]
    time_fraction: list[float]
    amount_transformed: list[float]
    direction_idx: list[int]
    account_idx: list[int]
    recurrence_idx: list[int]
    obligation_linked: list[float]
    valid_mask: list[float]


def household_record_to_event_set_targets(record: HouseholdRecord, config) -> EventSetTargets:
    from ml.relieffm import vocab
    from ml.relieffm.features import amount_transform

    checking_id = record.accounts[0].account_id
    account_type_by_id = {a.account_id: a.account_type.value for a in record.accounts}
    horizon_days = config.forecast_horizon_days
    slots = config.max_event_slots

    uncertain = sorted(
        (e for e in record.uncertain_future_events() if e.account_id == checking_id),
        key=lambda e: e.occurrence_time,
    )
    uncertain = [e for e in uncertain if 0 <= (e.occurrence_time - record.as_of).days < horizon_days]
    n = min(len(uncertain), slots)

    event_type_idx = [0] * slots
    time_fraction = [0.0] * slots
    amount_transformed = [0.0] * slots
    direction_idx = [0] * slots
    account_idx = [0] * slots
    recurrence_idx = [0] * slots
    obligation_linked = [0.0] * slots
    valid_mask = [0.0] * slots

    for i, e in enumerate(uncertain[:n]):
        signed = e.amount_cents if e.direction == "inflow" else -e.amount_cents
        offset_days = (e.occurrence_time - record.as_of).total_seconds() / 86400.0
        event_type_idx[i] = vocab.index_of(vocab.EVENT_TYPE, e.event_type)
        time_fraction[i] = float(min(max(offset_days / horizon_days, 0.0), 1.0))
        amount_transformed[i] = amount_transform(signed)
        direction_idx[i] = vocab.index_of(vocab.DIRECTION, e.direction)
        account_idx[i] = vocab.index_of(vocab.ACCOUNT_TYPE, account_type_by_id.get(e.account_id))
        recurrence_idx[i] = vocab.index_of(vocab.RECURRENCE_STATE, e.recurrence_state)
        obligation_linked[i] = 1.0 if e.obligation_id is not None else 0.0
        valid_mask[i] = 1.0

    return EventSetTargets(
        n_true_events=n,
        event_type_idx=event_type_idx,
        time_fraction=time_fraction,
        amount_transformed=amount_transformed,
        direction_idx=direction_idx,
        account_idx=account_idx,
        recurrence_idx=recurrence_idx,
        obligation_linked=obligation_linked,
        valid_mask=valid_mask,
    )


@dataclass
class InterventionExample:
    """One synthetic intervention-pair training example for a household, or
    a zeroed placeholder (`has_intervention=False`) when the household has
    no obligation with known provider capability (section 41's eligibility
    requirement). Delta targets are in the same amount-transformed daily
    space as the trajectory heads."""

    has_intervention: bool
    action_type: str
    obligation_id: str
    original_amount_cents: int
    modified_amount_cents: int
    original_date_offset_days: float
    modified_date_offset_days: float
    added_cost_cents: int
    delta_daily_balance_cents: list[int]  # length forecast_horizon_days


def household_record_to_intervention_example(record: HouseholdRecord, config, rng) -> InterventionExample:
    from ml.simulator.interventions import generate_intervention_pairs

    horizon_days = config.forecast_horizon_days
    # generate_intervention_pairs' balance arrays span [history_start,
    # horizon_end] (ml/simulator/ledger.py's day_bucket convention), so the
    # forecast-horizon slice starts at offset `history_days_actual`, NOT 0 —
    # index 0 is the day after history_start, deep in the historical
    # window. Indexing from 0 silently compared history-window balances
    # (identical between baseline/intervention, since interventions only
    # touch future events) and produced an all-zero delta target.
    history_days_actual = (record.as_of - record.history_start).days
    pairs = [
        p for p in generate_intervention_pairs(record, rng)
        if len(p.baseline_daily_balances_cents) >= history_days_actual + horizon_days
    ]
    if not pairs:
        return InterventionExample(
            has_intervention=False, action_type="split_payment", obligation_id="",
            original_amount_cents=0, modified_amount_cents=0,
            original_date_offset_days=0.0, modified_date_offset_days=0.0,
            added_cost_cents=0, delta_daily_balance_cents=[0] * horizon_days,
        )

    pair = pairs[int(rng.integers(0, len(pairs)))]
    obligation = next(o for o in record.obligations if o.obligation_id == pair.obligation_id)
    delta = [
        pair.intervention_daily_balances_cents[history_days_actual + d] - pair.baseline_daily_balances_cents[history_days_actual + d]
        for d in range(horizon_days)
    ]
    due_offset = (obligation.due_date - record.as_of).total_seconds() / 86400.0
    return InterventionExample(
        has_intervention=True,
        action_type=pair.action_type,
        obligation_id=pair.obligation_id,
        original_amount_cents=obligation.scheduled_amount_cents,
        modified_amount_cents=obligation.scheduled_amount_cents,  # exact split amounts vary per-slot; original obligation amount is the encoder-relevant scale
        original_date_offset_days=due_offset,
        modified_date_offset_days=due_offset,
        added_cost_cents=pair.added_cost_cents,
        delta_daily_balance_cents=delta,
    )
