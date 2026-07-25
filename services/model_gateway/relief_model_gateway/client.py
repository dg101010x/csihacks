from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional

import httpx
from relief_contracts import HouseholdSnapshotV1
from relief_deterministic_forecast.reserve import compute_essential_reserve_cents

from .errors import ModelServiceUnavailableError

_LIQUID_ACCOUNT_TYPES = {"checking", "savings"}
_ACCOUNT_TYPES = {"checking", "savings", "credit_card", "loan", "brokerage"}
_OBLIGATION_TYPES = {
    "rent": "rent",
    "mortgage": "mortgage",
    "loan_payment": "auto_loan",
    "auto_loan": "auto_loan",
    "personal_loan": "personal_loan",
    "credit_card_minimum": "credit_card_minimum",
    "insurance_premium": "insurance_premium",
    "utility": "utility",
    "subscription": "subscription",
    "bnpl": "bnpl",
    "medical_payment_plan": "medical_payment_plan",
}


def _freshness_hours(value: datetime, *, as_of: datetime) -> float:
    return max(0.0, (as_of - value).total_seconds() / 3600)


def _recurrence(value: str | None, *, recurring: bool = False) -> str:
    normalized = (value or "").upper()
    if "WEEKLY" in normalized:
        return "weekly"
    if "BIWEEKLY" in normalized:
        return "biweekly"
    if "SEMIMONTHLY" in normalized:
        return "semimonthly"
    if "MONTHLY" in normalized or recurring:
        return "monthly"
    return "none"


def _event_type(event) -> str:
    value = event.event_type.lower()
    category = (event.merchant_category or "").lower()
    if value == "paycheck":
        return "paycheck"
    if category == "rent":
        return "rent_payment"
    if category == "loan_payment":
        return "auto_loan_payment"
    if category == "subscription":
        return "subscription"
    if value in {
        "mortgage_payment",
        "auto_loan_payment",
        "personal_loan_payment",
        "credit_card_payment",
        "insurance_premium",
        "utility_bill",
        "subscription",
        "bnpl_payment",
        "medical_payment",
        "transfer",
        "fee",
        "refund",
        "purchase",
        "deposit",
        "withdrawal",
        "shock_expense",
    }:
        return value
    return "purchase" if event.direction.value == "outflow" else "deposit"


def _event_status(value: str) -> str:
    if value in {"posted", "pending", "scheduled", "cancelled", "failed"}:
        return value
    return "posted"


def _source_type(event) -> str:
    if event.metadata.get("is_simulated") or event.source.startswith("synthetic_"):
        return "simulated"
    return "bank_feed"


def _known_source(event) -> str:
    if event.direction.value == "inflow" or event.event_type.lower() == "paycheck":
        return "confirmed_paycheck"
    if (event.merchant_category or "").lower() == "rent":
        return "confirmed_rent_payment"
    if (event.merchant_category or "").lower() == "insurance":
        return "confirmed_insurance_premium"
    return "scheduled_loan_payment"


def _to_model_snapshot(snapshot: HouseholdSnapshotV1) -> dict:
    as_of = snapshot.generated_at
    liquid_accounts = [account for account in snapshot.accounts if account.account_type in _LIQUID_ACCOUNT_TYPES]
    total_liquid = sum(account.current_balance_cents for account in liquid_accounts)
    available_liquid = sum(
        account.available_balance_cents
        if account.available_balance_cents is not None
        else account.current_balance_cents
        for account in liquid_accounts
    )
    reserve = compute_essential_reserve_cents(snapshot.obligations)
    freshness = max(
        (_freshness_hours(account.balance_updated_at, as_of=as_of) for account in snapshot.accounts),
        default=0.0,
    )
    completeness_inputs = [
        *(1.0 if account.data_status.value == "current" else 0.5 if account.data_status.value == "stale" else 0.0
          for account in snapshot.accounts),
        *(1.0 if obligation.consumer_confirmed else obligation.source_confidence for obligation in snapshot.obligations),
    ]
    completeness = sum(completeness_inputs) / len(completeness_inputs) if completeness_inputs else 1.0
    fallback_account_id = snapshot.accounts[0].account_id if snapshot.accounts else "unassigned"
    known_provider_ids = {capability.provider_id for capability in snapshot.provider_capabilities}

    return {
        "household_id": snapshot.household_id,
        "currency": snapshot.currency,
        "as_of": as_of.isoformat(),
        "household_state": {
            "total_liquid_balance_cents": total_liquid,
            "available_balance_cents": available_liquid,
            "num_accounts": len(snapshot.accounts),
            "num_obligations": len(snapshot.obligations),
            "essential_reserve_cents": reserve,
            "data_freshness_hours": freshness,
            "snapshot_completeness": completeness,
        },
        "accounts": [
            {
                "account_id": account.account_id,
                "account_type": account.account_type if account.account_type in _ACCOUNT_TYPES else "checking",
                "account_subtype": account.account_subtype or "",
                "current_balance_cents": account.current_balance_cents,
                "available_balance_cents": (
                    account.available_balance_cents
                    if account.available_balance_cents is not None
                    else account.current_balance_cents
                ),
                "credit_limit_cents": None,
                "data_freshness_hours": _freshness_hours(account.balance_updated_at, as_of=as_of),
                "institution_ref": account.provider,
            }
            for account in snapshot.accounts
        ],
        "obligations": [
            {
                "obligation_id": obligation.obligation_id,
                "obligation_type": _OBLIGATION_TYPES.get(obligation.obligation_type, "personal_loan"),
                "scheduled_amount_cents": obligation.scheduled_amount_cents,
                "due_date": (obligation.next_due_at or as_of + timedelta(days=30)).isoformat(),
                "recurrence": _recurrence(obligation.recurrence_rule),
                "remaining_principal_cents": obligation.principal_balance_cents,
                "essentiality_category": "essential" if obligation.essentiality_score >= 0.6 else "discretionary",
                "payment_status": "in_hardship_program" if obligation.status.value == "paused" else "current",
                "provider_capability_known": obligation.provider_id in known_provider_ids,
                "account_id": fallback_account_id,
            }
            for obligation in snapshot.obligations
            if obligation.status.value != "closed" and obligation.scheduled_amount_cents > 0
        ],
        "historical_events": [
            {
                "event_id": event.event_id,
                "event_type": _event_type(event),
                "event_status": _event_status(event.event_status.value),
                "amount_cents": event.amount_cents,
                "direction": event.direction.value,
                "account_id": event.account_id,
                "merchant_category": event.merchant_category or "unknown",
                "recurrence_state": _recurrence(None, recurring=event.is_recurring),
                "transaction_confidence": 1.0,
                "source_type": _source_type(event),
                "occurrence_time": event.occurred_at.isoformat(),
                "effective_time": event.effective_at.isoformat(),
            }
            for event in snapshot.recent_events
            if event.occurred_at <= as_of
        ],
        "known_future_events": [
            {
                "event_id": event.event_id,
                "event_type": _event_type(event),
                "amount_cents": event.amount_cents,
                "direction": event.direction.value,
                "account_id": event.account_id,
                "effective_time": event.effective_at.isoformat(),
                "source": _known_source(event),
                "obligation_id": event.obligation_id,
            }
            for event in snapshot.known_future_events
            if event.event_status.value != "cancelled"
        ],
    }


def _to_platform_inference(
    response: dict,
    *,
    snapshot: HouseholdSnapshotV1,
    requested_horizon: int,
    latency_ms: float,
) -> dict:
    reserve = compute_essential_reserve_cents(snapshot.obligations)
    initial_balance = sum(
        account.current_balance_cents
        for account in snapshot.accounts
        if account.account_type in _LIQUID_ACCOUNT_TYPES
    )
    summaries = response["daily_summary"][:requested_horizon]
    scenarios = response.get("trajectories", [])

    daily_summary = []
    for day_index, day in enumerate(summaries):
        scenario_balances = [
            scenario["daily_balances_cents"][day_index]
            for scenario in scenarios
            if len(scenario.get("daily_balances_cents", [])) > day_index
        ]
        violation_probability = (
            sum(balance < reserve for balance in scenario_balances) / len(scenario_balances)
            if scenario_balances
            else float(day["balance_p50_cents"] < reserve)
        )
        daily_summary.append(
            {
                "event_date": day["date"][:10],
                "median_ending_balance_cents": day["balance_p50_cents"],
                "lower_ending_balance_cents": day["balance_p10_cents"],
                "upper_ending_balance_cents": day["balance_p90_cents"],
                "reserve_violation_probability": violation_probability,
            }
        )

    trajectories = []
    for scenario in scenarios:
        prior = initial_balance
        for day_index, ending in enumerate(scenario["daily_balances_cents"][:requested_horizon]):
            delta = ending - prior
            trajectories.append(
                {
                    "scenario_index": scenario["scenario_id"],
                    "event_date": summaries[day_index]["date"][:10],
                    "starting_balance_cents": prior,
                    "inflow_cents": max(delta, 0),
                    "outflow_cents": max(-delta, 0),
                    "ending_balance_cents": ending,
                    "essential_reserve_cents": reserve,
                }
            )
            prior = ending

    metadata = response["model_metadata"]
    return {
        "model_version": response.get("provider_version", metadata["model_version"]),
        "calibration_version": metadata.get("calibration_version"),
        "inference_latency_ms": latency_ms,
        "confidence": response["confidence"],
        "warnings": [
            *response.get("warnings", []),
            "shadow_only: ReliefFM output is visible for comparison but does not drive financial actions.",
        ],
        "daily_summary": daily_summary,
        "trajectories": trajectories,
        "distress_probabilities": response["distress_probabilities"],
        "reason_factors": [
            {
                "factor": factor["name"],
                "weight": max(0.0, min(1.0, factor["contribution"])),
                "description": f"ReliefFM diagnostic contribution: {factor['name'].replace('_', ' ')}.",
            }
            for factor in response.get("reason_factors", [])
        ],
    }


class ReliefFMClient:
    """Translate Plan Two's public contract to the deployed ReliefFM model API."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        model: str = "mini",
        timeout: float = 30.0,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        if model not in {"mini", "flash"}:
            raise ValueError("model must be 'mini' or 'flash'")
        env_name = "RELIEFFM_MINI_URL" if model == "mini" else "RELIEFFM_FLASH_URL"
        self.base_url = base_url or os.environ.get(env_name) or (
            os.environ.get("RELIEFFM_INFERENCE_URL") if model == "mini" else None
        )
        self.model = model
        self._timeout = timeout
        self._transport = transport

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        if not self.base_url:
            raise ModelServiceUnavailableError(f"ReliefFM {self.model} is not configured.")
        try:
            with httpx.Client(base_url=self.base_url, transport=self._transport, timeout=self._timeout) as client:
                response = client.request(method, path, **kwargs)
                response.raise_for_status()
                return response
        except httpx.HTTPError as exc:
            raise ModelServiceUnavailableError(f"ReliefFM {self.model} call failed: {exc}") from exc

    def status(self) -> dict:
        if not self.base_url:
            return {
                "id": self.model,
                "name": f"ReliefFM {self.model.title()}",
                "status": "training" if self.model == "flash" else "unavailable",
                "selectable": False,
                "lifecycle": "shadow",
                "version": None,
            }
        try:
            health = self._request("GET", "/model/v1/health").json()
            available = health.get("status") == "ok"
            return {
                "id": self.model,
                "name": f"ReliefFM {self.model.title()}",
                "status": "available" if available else "unavailable",
                "selectable": available,
                "lifecycle": health.get("lifecycle_status", "shadow"),
                "version": health.get("model_version"),
            }
        except ModelServiceUnavailableError:
            return {
                "id": self.model,
                "name": f"ReliefFM {self.model.title()}",
                "status": "unavailable",
                "selectable": False,
                "lifecycle": "shadow",
                "version": None,
            }

    def infer(self, snapshot: HouseholdSnapshotV1, *, horizon_days: int) -> dict:
        metadata = self._request("GET", "/model/v1/metadata").json()
        supported = sorted(int(value) for value in metadata.get("supported_horizons", []))
        model_horizon = next((value for value in supported if value >= horizon_days), None)
        if model_horizon is None:
            raise ModelServiceUnavailableError(
                f"ReliefFM {self.model} does not support a horizon of at least {horizon_days} days."
            )
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        started = time.perf_counter()
        response = self._request(
            "POST",
            "/model/v1/forecast",
            json={
                "contract_version": "1.0.0",
                "request_id": request_id,
                "snapshot": _to_model_snapshot(snapshot),
                "horizon_days": model_horizon,
                "scenario_count": min(8, int(metadata.get("maximum_scenarios", 8))),
                "requested_outputs": ["daily_balance_trajectories", "distress_probabilities"],
            },
        ).json()
        latency_ms = (time.perf_counter() - started) * 1000
        return _to_platform_inference(
            response,
            snapshot=snapshot,
            requested_horizon=horizon_days,
            latency_ms=latency_ms,
        )
