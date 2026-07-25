"""Core forecast computation shared by /forecast and /simulate_intervention.

Section 119's pipeline: input contract validation -> feature compiler ->
model execution -> scenario generator -> calibration layer -> output
validator -> ForecastResponseV1. Calibration layer is a no-op pass-through
this session (section 67's temperature scaling exists in ml/calibration
but no fitted temperature is loaded here yet — see the model card).
"""
from __future__ import annotations

import json
import math
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import torch
from safetensors.torch import load_file

from relief_contracts.schemas import (
    DailySummary,
    DistressProbabilities,
    ForecastResponseV1,
    HouseholdSnapshotV1,
    ModelLifecycleState,
    ModelMetadataV1,
    ReasonFactor,
    ScenarioTrajectory,
)
from ml.relieffm.config import NanoConfig
from ml.relieffm.model import ReliefFMNano
from ml.relieffm.reason_factors import FACTOR_NAMES
from ml.relieffm.tokenize import encode_snapshot
from ml.training.dataset import collate
from ml.training.losses import QUANTILE_LEVELS, inverse_transform

from .reconcile import project_known_events
from .runtime import move_batch_to_device, resolve_device

MEDIAN_IDX = QUANTILE_LEVELS.index(0.5)


class LoadedModel:
    def __init__(self, checkpoint_dir: str, device: str | None = None):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.meta = json.loads((self.checkpoint_dir / "checkpoint_meta.json").read_text())
        self.config = NanoConfig(**self.meta["config"])
        self.device = resolve_device(device)
        self.model = ReliefFMNano(self.config)
        state_dict = load_file(str(self.checkpoint_dir / "model.safetensors"))
        self.model.load_state_dict(state_dict)
        self.model.to(self.device)
        self.model.eval()
        self.distress_horizon_index = list(self.config.distress_horizons).index(
            min(self.config.distress_horizons, key=lambda h: abs(h - self.config.forecast_horizon_days))
        )

    def metadata(self, status: ModelLifecycleState = ModelLifecycleState.SHADOW) -> ModelMetadataV1:
        return ModelMetadataV1(
            model_name=self.meta["model_name"],
            model_version=self.meta["model_version"],
            training_data_version=self.meta["dataset_version"],
            calibration_version=self.meta["calibration_version"],
            supported_horizons=[self.config.forecast_horizon_days],
            maximum_scenarios=self.config.scenario_count,
            status=status,
            model_size="nano",
        )


class ForecastError(Exception):
    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


def run_forecast(
    loaded: LoadedModel,
    snapshot: HouseholdSnapshotV1,
    horizon_days: int,
    scenario_count: int,
    request_id: str,
    forecast_id: str,
    extra_warnings: list[str] | None = None,
) -> ForecastResponseV1:
    config = loaded.config
    warnings: list[str] = list(extra_warnings or [])

    if horizon_days != config.forecast_horizon_days:
        raise ForecastError(
            f"unsupported horizon_days={horizon_days}; this deployment only supports {config.forecast_horizon_days}"
        )

    capped_scenarios = min(scenario_count, config.scenario_count) if scenario_count > 0 else 0
    if scenario_count > config.scenario_count:
        warnings.append(f"scenario_count capped from {scenario_count} to {config.scenario_count}")

    if snapshot.household_state.snapshot_completeness < 0.5:
        warnings.append("low snapshot_completeness -- confidence reduced")
    if snapshot.household_state.data_freshness_hours > 48:
        warnings.append("stale account data (>48h) -- confidence reduced")
    if len(snapshot.historical_events) < 10:
        warnings.append("sparse event history (<10 events) -- confidence reduced")

    encoded = encode_snapshot(snapshot, config)
    batch = move_batch_to_device(collate([encoded]), loaded.device)

    t0 = time.time()
    with torch.inference_mode():
        out = loaded.model(batch)
    latency_s = time.time() - t0

    known = project_known_events(snapshot, horizon_days)

    residual_q = out.balance_residual_quantiles[0].detach().cpu().numpy()  # (horizon, 3)
    inflow_q = out.inflow_quantiles[0].detach().cpu().numpy()
    essential_q = out.essential_outflow_quantiles[0].detach().cpu().numpy()
    discretionary_q = out.discretionary_outflow_quantiles[0].detach().cpu().numpy()

    residual_cents = inverse_transform(torch.from_numpy(residual_q)).numpy()
    inflow_cents = inverse_transform(torch.from_numpy(inflow_q)).numpy()
    essential_cents = inverse_transform(torch.from_numpy(essential_q)).numpy()
    discretionary_cents = inverse_transform(torch.from_numpy(discretionary_q)).numpy()

    balance_by_quantile = residual_cents + np.array(known.daily_balance_cents)[:, None]

    daily_summary = []
    for d in range(horizon_days):
        date = snapshot.as_of + timedelta(days=d + 1)
        daily_summary.append(
            DailySummary(
                date=date,
                balance_p10_cents=int(balance_by_quantile[d, 0]),
                balance_p50_cents=int(balance_by_quantile[d, MEDIAN_IDX]),
                balance_p90_cents=int(balance_by_quantile[d, 2]),
                inflow_p50_cents=int(known.daily_inflow_cents[d] + max(inflow_cents[d, MEDIAN_IDX], 0)),
                outflow_p50_cents=int(
                    known.daily_outflow_cents[d]
                    + max(essential_cents[d, MEDIAN_IDX], 0)
                    + max(discretionary_cents[d, MEDIAN_IDX], 0)
                ),
            )
        )

    trajectories = _sample_scenarios(balance_by_quantile, capped_scenarios)

    distress = out.distress_probabilities[0, loaded.distress_horizon_index].detach().cpu().numpy()
    distress_probs = DistressProbabilities(
        negative_balance=float(np.clip(distress[0], 0.0, 1.0)),
        essential_reserve_violation=float(np.clip(distress[1], 0.0, 1.0)),
        missed_obligation=float(np.clip(distress[2], 0.0, 1.0)),
    )

    reason_factor_values = out.reason_factors[0].detach().cpu().numpy()
    reason_factors = [
        ReasonFactor(name=name, contribution=float(v)) for name, v in zip(FACTOR_NAMES, reason_factor_values)
    ]

    confidence = float(np.clip(
        snapshot.household_state.snapshot_completeness * (1.0 if len(warnings) == 0 else 0.7), 0.0, 1.0
    ))

    now = datetime.now(timezone.utc)
    response = ForecastResponseV1(
        contract_version="1.0.0",
        request_id=request_id,
        forecast_id=forecast_id,
        provider="relieffm",
        provider_version=f"{loaded.meta['model_name']}_{loaded.meta['model_version']}",
        generated_at=now,
        valid_until=now + timedelta(hours=1),
        confidence=confidence,
        is_stale=False,
        warnings=warnings,
        daily_summary=daily_summary,
        trajectories=trajectories,
        distress_probabilities=distress_probs,
        reason_factors=reason_factors,
        model_metadata=loaded.metadata(),
    )
    _validate_output(response, snapshot, horizon_days)
    return response


def _sample_scenarios(balance_by_quantile: np.ndarray, n_scenarios: int, seed: int = 0) -> list[ScenarioTrajectory]:
    """Nano has no learned scenario generator (that's Mini's global trajectory
    latent, section 22). This approximates correlated-across-days scenarios
    by drawing one latent z per scenario and interpolating each day's
    p10/p50/p90 at the matching normal-CDF quantile level -- a sampling
    trick at inference time, not a trained generative model."""
    if n_scenarios <= 0:
        return []
    rng = np.random.default_rng(seed)
    horizon_days = balance_by_quantile.shape[0]
    trajectories = []
    quantile_levels = np.array(QUANTILE_LEVELS)
    for k in range(n_scenarios):
        z = rng.normal()
        level = float(np.clip(0.5 * (1 + math.erf(z / math.sqrt(2))), 0.01, 0.99))
        daily = [
            int(np.interp(level, quantile_levels, balance_by_quantile[d])) for d in range(horizon_days)
        ]
        trajectories.append(ScenarioTrajectory(scenario_id=k, daily_balances_cents=daily, accounting_valid=True))
    return trajectories


def _validate_output(response: ForecastResponseV1, snapshot: HouseholdSnapshotV1, horizon_days: int) -> None:
    if len(response.daily_summary) != horizon_days:
        raise ForecastError("internal error: daily_summary length mismatch", status_code=500)
    for d in response.daily_summary:
        for v in (d.balance_p10_cents, d.balance_p50_cents, d.balance_p90_cents, d.inflow_p50_cents, d.outflow_p50_cents):
            if not math.isfinite(v):
                raise ForecastError("internal error: non-finite value in daily_summary", status_code=500)
    for p in (
        response.distress_probabilities.negative_balance,
        response.distress_probabilities.essential_reserve_violation,
        response.distress_probabilities.missed_obligation,
    ):
        if not (0.0 <= p <= 1.0):
            raise ForecastError("internal error: distress probability out of range", status_code=500)
    for t in response.trajectories:
        if len(t.daily_balances_cents) != horizon_days:
            raise ForecastError("internal error: trajectory length mismatch", status_code=500)
