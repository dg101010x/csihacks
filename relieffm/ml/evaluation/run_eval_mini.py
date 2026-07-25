"""Evaluates a trained Mini checkpoint: trajectory (both realistic
median-of-scenarios serving output and oracle best-of-scenarios, labeled
separately — no averaging the two together), 30-day distress vs a GBM
trained on an independent population, event-set detection quality, and
intervention-delta accuracy on synthetic matched pairs.

    python -m ml.evaluation.run_eval_mini --checkpoint_dir runs/mini_v1/checkpoint --n_households 1000 --out_path runs/mini_v1/eval_report.json
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from safetensors.torch import load_file
from torch.utils.data import DataLoader

from ml.baselines.gradient_boosted import DistressGBMBaseline
from ml.baselines.seasonal_median import predict_daily_balance
from ml.datasets.compile import household_record_to_targets
from ml.evaluation import metrics as M
from ml.relieffm.config import MiniConfig
from ml.relieffm.mini.model import ReliefFMMini
from ml.simulator.population import generate_population
from ml.training.dataset_mini import MiniTensorDataset, collate_mini
from ml.training.losses import inverse_transform
from ml.training.mini_losses import TRAJECTORY_SERIES, select_best_scenario


def load_model(checkpoint_dir: Path) -> tuple[ReliefFMMini, MiniConfig, dict]:
    meta = json.loads((checkpoint_dir / "checkpoint_meta.json").read_text())
    config = MiniConfig(**meta["config"])
    model = ReliefFMMini(config)
    state_dict = load_file(str(checkpoint_dir / "model.safetensors"))
    model.load_state_dict(state_dict)
    model.eval()
    return model, config, meta


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint_dir", type=str, required=True)
    p.add_argument("--n_households", type=int, default=1000)
    p.add_argument("--seed", type=int, default=88881)
    p.add_argument("--history_days", type=int, default=120)
    p.add_argument("--baseline_train_households", type=int, default=3000)
    p.add_argument("--n_scenarios", type=int, default=None)  # defaults to config.scenario_count
    p.add_argument("--out_path", type=str, default=None)
    args = p.parse_args()

    checkpoint_dir = Path(args.checkpoint_dir)
    model, config, meta = load_model(checkpoint_dir)
    n_scenarios = args.n_scenarios or config.scenario_count

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    as_of = datetime.now(timezone.utc).replace(microsecond=0)
    records = generate_population(
        args.n_households, seed=args.seed, as_of=as_of,
        history_days=args.history_days, horizon_days=config.forecast_horizon_days,
    )

    dataset = MiniTensorDataset(records, config, seed=args.seed + 1)
    loader = DataLoader(dataset, batch_size=32, shuffle=False, collate_fn=collate_mini)

    all_median_balance, all_best_balance, all_true_balance = [], [], []
    all_distress, all_existence_pred, all_existence_true_count, all_pred_count = [], [], [], []
    all_delta_pred, all_delta_true, all_has_intervention = [], [], []
    forward_seconds = 0.0

    horizon_days = config.forecast_horizon_days
    with torch.no_grad():
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            t0 = time.time()
            out = model(batch, n_scenarios=n_scenarios, include_intervention=True)
            forward_seconds += time.time() - t0

            residual_cents = inverse_transform(out.baseline_trajectory["balance_residual"]).cpu()  # (B,K,H)
            known = batch["target_known_balance_cents"].unsqueeze(1).cpu()  # (B,1,H)
            balance_scenarios = (residual_cents + known).numpy()  # (B,K,H)
            median_balance = np.median(balance_scenarios, axis=1)  # (B,H) -- realistic serving output
            true_balance = batch["target_full_balance_cents"].cpu().numpy()

            best_idx, _ = select_best_scenario(out.baseline_trajectory, batch)
            best_idx = best_idx.cpu()
            best_balance = np.take_along_axis(balance_scenarios, best_idx.numpy()[:, None, None], axis=1)[:, 0, :]

            all_median_balance.append(median_balance)
            all_best_balance.append(best_balance)
            all_true_balance.append(true_balance)

            distress_horizon_idx = list(config.distress_horizons).index(30) if 30 in config.distress_horizons else 0
            all_distress.append(out.distress_probabilities[:, distress_horizon_idx, 0].cpu().numpy())

            exist_prob = torch.sigmoid(out.baseline_event_set["existence_logit"]).mean(dim=1).cpu().numpy()  # avg over scenarios, (B,S)
            all_existence_pred.append((exist_prob > 0.5).sum(axis=1))
            all_existence_true_count.append(batch["event_set_valid_mask"].sum(dim=1).cpu().numpy())

            baseline_residual_cpu = out.baseline_trajectory["balance_residual"].cpu().numpy()
            intervention_residual_cpu = out.intervention_trajectory["balance_residual"].cpu().numpy()
            selected_intervention_residual = np.take_along_axis(intervention_residual_cpu, best_idx.numpy()[:, None, None], axis=1)[:, 0, :]
            pred_intervention_balance = inverse_transform(torch.from_numpy(selected_intervention_residual)).numpy()
            pred_baseline_balance_best = inverse_transform(
                torch.from_numpy(np.take_along_axis(baseline_residual_cpu, best_idx.numpy()[:, None, None], axis=1)[:, 0, :])
            ).numpy()
            pred_delta = pred_intervention_balance - pred_baseline_balance_best
            all_delta_pred.append(pred_delta)
            all_delta_true.append(batch["intervention_delta_balance_cents"].cpu().numpy())
            all_has_intervention.append(batch["has_intervention"].cpu().numpy())

    median_balance = np.concatenate(all_median_balance)
    best_balance = np.concatenate(all_best_balance)
    true_balance = np.concatenate(all_true_balance)
    distress30 = np.concatenate(all_distress)
    pred_event_count = np.concatenate(all_existence_pred)
    true_event_count = np.concatenate(all_existence_true_count)
    delta_pred = np.concatenate(all_delta_pred)
    delta_true = np.concatenate(all_delta_true)
    has_intervention = np.concatenate(all_has_intervention).astype(bool)

    targets = [household_record_to_targets(r) for r in records]
    true_distress30 = np.array([t.distress_negative_balance.get(30, False) for t in targets], dtype=np.float64)

    seasonal_pred_balance = np.array(
        [predict_daily_balance(r, t.known_daily_balance_cents) for r, t in zip(records, targets)]
    )

    baseline_seed = args.seed + 1_000_003
    baseline_records = generate_population(
        args.baseline_train_households, seed=baseline_seed, as_of=as_of,
        history_days=args.history_days, horizon_days=config.forecast_horizon_days,
    )
    baseline_targets = [household_record_to_targets(r) for r in baseline_records]
    gbm = DistressGBMBaseline().fit(
        baseline_records,
        [t.distress_negative_balance.get(30, False) for t in baseline_targets],
    )
    gbm_probs = gbm.predict_proba(records)

    delta_end_err = (
        np.abs(delta_pred[has_intervention, -1] - delta_true[has_intervention, -1]).mean()
        if has_intervention.any() else float("nan")
    )
    delta_trajectory_err = (
        np.abs(delta_pred[has_intervention] - delta_true[has_intervention]).mean()
        if has_intervention.any() else float("nan")
    )
    delta_direction_acc = float(np.mean(
        np.sign(delta_pred[has_intervention][:, -1]) == np.sign(delta_true[has_intervention][:, -1])
    )) if has_intervention.any() else float("nan")
    zero_baseline_end_err = (
        np.abs(delta_true[has_intervention, -1]).mean()
        if has_intervention.any() else float("nan")
    )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checkpoint_meta": {k: meta[k] for k in ("model_name", "model_version", "num_parameters", "training_steps", "dataset_version")},
        "n_eval_households": len(records),
        "eval_seed": args.seed,
        "baseline_train_households": len(baseline_records),
        "baseline_train_seed": baseline_seed,
        "n_scenarios": n_scenarios,
        "horizon_days": horizon_days,
        "avg_forward_seconds_per_batch": forward_seconds / max(len(loader), 1),
        "trajectory": {
            "median_of_scenarios_balance_mae_cents": M.balance_mae(median_balance, true_balance),
            "best_of_scenarios_balance_mae_cents_ORACLE": M.balance_mae(best_balance, true_balance),
            "seasonal_baseline_balance_mae_cents": M.balance_mae(seasonal_pred_balance, true_balance),
            "median_min_balance_error_cents": M.min_balance_error(median_balance, true_balance),
            "seasonal_min_balance_error_cents": M.min_balance_error(seasonal_pred_balance, true_balance),
        },
        "distress_30d": {
            "mini_brier": M.brier_score(distress30, true_distress30),
            "mini_ece": M.expected_calibration_error(distress30, true_distress30),
            "mini_false_reassurance_rate": M.false_reassurance_rate(distress30, true_distress30),
            "gbm_baseline_brier": M.brier_score(gbm_probs, true_distress30),
            "gbm_baseline_ece": M.expected_calibration_error(gbm_probs, true_distress30),
            "positive_rate": float(true_distress30.mean()),
        },
        "event_set": {
            "mean_predicted_event_count": float(pred_event_count.mean()),
            "mean_true_event_count": float(true_event_count.mean()),
            "event_count_mae": float(np.abs(pred_event_count - true_event_count).mean()),
            "note": "existence threshold 0.5, averaged over scenarios; not a matched precision/recall (would need per-scenario re-matching at eval time)",
        },
        "intervention_delta": {
            "n_examples_with_intervention": int(has_intervention.sum()),
            "end_of_horizon_delta_mae_cents_ORACLE": float(delta_end_err),
            "trajectory_delta_mae_cents_ORACLE": float(delta_trajectory_err),
            "end_of_horizon_direction_accuracy_ORACLE": delta_direction_acc,
            "zero_delta_baseline_end_of_horizon_mae_cents": float(zero_baseline_end_err),
            "note": "ORACLE = best-of-scenarios selection using ground truth, matching the training objective's winner-takes-all selection -- not a blind-inference number. zero_delta_baseline is 'predict no effect from the intervention', the naive comparison point.",
        },
        "known_event_preservation": {
            "preserved_by_construction": True,
            "note": "same construction as Nano: known_daily_balance_cents is a deterministic ledger replay, never model output.",
        },
    }

    print(json.dumps(report, indent=2))
    if args.out_path:
        Path(args.out_path).write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
