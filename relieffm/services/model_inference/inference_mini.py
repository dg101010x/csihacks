"""Mini's inference path. Unlike Nano's, `/simulate_intervention` here is
real: the model runs coupled baseline + intervention-conditioned decodes
sharing the same sampled scenario latents (section 31), so the returned
forecast reflects both the deterministic known-event change (section 23,
via `reconcile.py` + `intervention.py`, same as Nano) AND a learned
uncertain-component response to the intervention — not just a warning that
conditioning isn't modeled.

Known limitation, disclosed in the model card: the intervention encoder's
original/modified amount features are degenerate in this session's
training data (both always equal the obligation's scheduled amount — see
`ml/datasets/compile.py`'s `InterventionExample`), so the model
differentiates interventions mainly via action type, dates, and added
cost, not amount deltas. Inference-time feature construction mirrors that
same convention rather than "fixing" it one-sidedly, which would just
create a train/inference mismatch.
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
    Intervention,
    ModelLifecycleState,
    ModelMetadataV1,
    ReasonFactor,
    ScenarioTrajectory,
)
from ml.relieffm import vocab
from ml.relieffm.config import MiniConfig
from ml.relieffm.engineered_features import compute_engineered_features
from ml.relieffm.features import amount_transform
from ml.relieffm.mini.model import ReliefFMMini
from ml.relieffm.mini.tokenize import encode_mini_snapshot
from ml.relieffm.reason_factors import FACTOR_NAMES
from ml.simulator.providers import modification_cost_cents
from ml.training.dataset import collate
from ml.training.losses import inverse_transform

from .inference import ForecastError
from .intervention import apply_intervention
from .reconcile import project_known_events
from .runtime import move_batch_to_device, resolve_device


class LoadedMiniModel:
    def __init__(self, checkpoint_dir: str, device: str | None = None):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.meta = json.loads((self.checkpoint_dir / "checkpoint_meta.json").read_text())
        self.config = MiniConfig(**self.meta["config"])
        self.device = resolve_device(device)
        self.model = ReliefFMMini(self.config)
        state_dict = load_file(str(self.checkpoint_dir / "model.safetensors"))
        self.model.load_state_dict(state_dict)
        self.model.to(self.device)
        self.model.eval()

    def metadata(self, status: ModelLifecycleState = ModelLifecycleState.SHADOW) -> ModelMetadataV1:
        return ModelMetadataV1(
            model_name=self.meta["model_name"],
            model_version=self.meta["model_version"],
            training_data_version=self.meta["dataset_version"],
            calibration_version=self.meta["calibration_version"],
            supported_horizons=[self.config.forecast_horizon_days],
            maximum_scenarios=self.config.scenario_count,
            status=status,
            model_size="flash" if self.meta["model_name"] == "relieffm_flash" else "mini",
        )


def _zero_intervention_batch(B: int, device):
    return {
        "intervention_action_idx": torch.zeros(B, dtype=torch.long, device=device),
        "intervention_numeric": torch.zeros(B, 6, dtype=torch.float32, device=device),
    }


def _intervention_batch_from_request(
    snapshot: HouseholdSnapshotV1, intervention: Intervention
) -> tuple[dict[str, torch.Tensor], int]:
    obligation = next((o for o in snapshot.obligations if o.obligation_id == intervention.obligation_id), None)
    if obligation is None:
        raise ForecastError(
            f"unknown intervention obligation_id={intervention.obligation_id}"
        )
    if not any(
        event.obligation_id == intervention.obligation_id
        for event in snapshot.known_future_events
    ):
        raise ForecastError(
            "intervention obligation has no known future event in the snapshot"
        )
    scheduled = obligation.scheduled_amount_cents
    due_offset = (obligation.due_date - snapshot.as_of).total_seconds() / 86400.0
    added_cost = modification_cost_cents(intervention.action_type)
    action_idx = vocab.index_of(vocab.INTERVENTION_ACTION_TYPE, intervention.action_type)
    numeric = np.array(
        [
            amount_transform(scheduled), amount_transform(scheduled), amount_transform(0),
            float(np.clip(due_offset / 30.0, -3.0, 3.0)), float(np.clip(due_offset / 30.0, -3.0, 3.0)),
            float(np.log1p(added_cost / 100.0)),
        ],
        dtype=np.float32,
    )
    return {
        "intervention_action_idx": torch.tensor([action_idx], dtype=torch.long),
        "intervention_numeric": torch.from_numpy(numeric).unsqueeze(0),
    }, added_cost


def run_forecast_mini(
    loaded: LoadedMiniModel,
    snapshot: HouseholdSnapshotV1,
    horizon_days: int,
    scenario_count: int,
    request_id: str,
    forecast_id: str,
    intervention: Intervention | None = None,
) -> ForecastResponseV1:
    config = loaded.config
    warnings: list[str] = []

    if horizon_days != config.forecast_horizon_days:
        raise ForecastError(f"unsupported horizon_days={horizon_days}; this deployment only supports {config.forecast_horizon_days}")

    returned_scenarios = (
        min(scenario_count, config.scenario_count) if scenario_count > 0 else 0
    )
    n_scenarios = max(returned_scenarios, 1)
    if scenario_count > config.scenario_count:
        warnings.append(f"scenario_count capped from {scenario_count} to {config.scenario_count}")

    if snapshot.household_state.snapshot_completeness < 0.5:
        warnings.append("low snapshot_completeness -- confidence reduced")
    if snapshot.household_state.data_freshness_hours > 48:
        warnings.append("stale account data (>48h) -- confidence reduced")
    if len(snapshot.historical_events) < 10:
        warnings.append("sparse event history (<10 events) -- confidence reduced")

    encoded = encode_mini_snapshot(snapshot, config)
    batch = move_batch_to_device(collate([encoded]), loaded.device)

    forecast_snapshot = snapshot
    added_cost_cents = 0
    if intervention is not None:
        forecast_snapshot, added_cost_cents = apply_intervention(snapshot, intervention)
        iv_batch, added_cost_cents = _intervention_batch_from_request(snapshot, intervention)
        batch.update(move_batch_to_device(iv_batch, loaded.device))
        warnings.append(
            "intervention_conditioned: both the deterministic known-event component and the model's "
            "uncertain-component forecast reflect the proposed intervention (coupled scenario sampling, section 31)"
        )
    else:
        batch.update(_zero_intervention_batch(1, batch["household_numeric"].device))

    t0 = time.time()
    with torch.inference_mode():
        out = loaded.model(batch, n_scenarios=n_scenarios, include_intervention=intervention is not None)
    latency_s = time.time() - t0

    known = project_known_events(forecast_snapshot, horizon_days)

    traj = out.intervention_trajectory if intervention is not None else out.baseline_trajectory
    residual_cents = inverse_transform(traj["balance_residual"])[0].detach().cpu().numpy()  # (K, horizon)
    inflow_cents = inverse_transform(traj["inflow"])[0].detach().cpu().numpy()
    essential_cents = inverse_transform(traj["essential_outflow"])[0].detach().cpu().numpy()
    discretionary_cents = inverse_transform(traj["discretionary_outflow"])[0].detach().cpu().numpy()

    balance_scenarios = residual_cents + np.array(known.daily_balance_cents)[None, :]  # (K, horizon)

    daily_summary = []
    for d in range(horizon_days):
        date = snapshot.as_of + timedelta(days=d + 1)
        col = balance_scenarios[:, d]
        daily_summary.append(
            DailySummary(
                date=date,
                balance_p10_cents=int(np.percentile(col, 10)),
                balance_p50_cents=int(np.percentile(col, 50)),
                balance_p90_cents=int(np.percentile(col, 90)),
                inflow_p50_cents=int(known.daily_inflow_cents[d] + max(np.median(inflow_cents[:, d]), 0)),
                outflow_p50_cents=int(
                    known.daily_outflow_cents[d]
                    + max(np.median(essential_cents[:, d]), 0)
                    + max(np.median(discretionary_cents[:, d]), 0)
                ),
            )
        )

    trajectories = [
        ScenarioTrajectory(scenario_id=k, daily_balances_cents=[int(v) for v in balance_scenarios[k]], accounting_valid=True)
        for k in range(returned_scenarios)
    ]

    distress_horizon_idx = min(
        range(len(config.distress_horizons)), key=lambda i: abs(config.distress_horizons[i] - horizon_days)
    )
    distress = out.distress_probabilities[0, distress_horizon_idx].detach().cpu().numpy()
    distress_probs = DistressProbabilities(
        negative_balance=float(np.clip(distress[0], 0.0, 1.0)),
        essential_reserve_violation=float(np.clip(distress[1], 0.0, 1.0)),
        missed_obligation=float(np.clip(distress[2], 0.0, 1.0)),
    )

    reason_factor_values = out.reason_factors[0].detach().cpu().numpy()
    reason_factors = [ReasonFactor(name=name, contribution=float(v)) for name, v in zip(FACTOR_NAMES, reason_factor_values)]

    if intervention is not None:
        baseline_residual_cents = (
            inverse_transform(out.baseline_trajectory["balance_residual"])[0]
            .detach()
            .cpu()
            .numpy()
        )
        baseline_balance = baseline_residual_cents + np.array(
            project_known_events(snapshot, horizon_days).daily_balance_cents
        )[None, :]
        delta_end = float(np.median(balance_scenarios[:, -1]) - np.median(baseline_balance[:, -1]))
        warnings.append(f"predicted_end_of_horizon_delta_cents={delta_end:.0f}")
        warnings.append(f"added_cost_cents={added_cost_cents}")

    confidence = float(np.clip(snapshot.household_state.snapshot_completeness * (1.0 if len(warnings) <= 1 else 0.7), 0.0, 1.0))

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
    _validate_output(response, horizon_days)
    return response


def _validate_output(response: ForecastResponseV1, horizon_days: int) -> None:
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
    for trajectory in response.trajectories:
        if len(trajectory.daily_balances_cents) != horizon_days:
            raise ForecastError("internal error: trajectory length mismatch", status_code=500)
