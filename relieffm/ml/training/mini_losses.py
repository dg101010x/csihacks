"""Mini's training objectives.

Both the trajectory heads and the event-set decoder are scenario-batched
((B, K, ...) — K = scenarios per household, section 22's global latent).
There is only one real future per household, so training uses a
winner-takes-all selection: pick the scenario with the lowest trajectory
error (the more directly measurable signal) and backprop the trajectory,
event-set-matching, accounting, and intervention-delta losses all through
that one selected scenario. This is the same "let z specialize into a
plausible mode" principle DETR-style set losses use for the event slots
themselves, applied consistently across the whole decoder output.

Section 57's accounting-consistency term and section 26's per-risk BCE
distress loss are carried over from Nano's `ml/training/losses.py`
(reused directly — `transform_cents`/`inverse_transform` are generic).
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn.functional as F
from scipy.optimize import linear_sum_assignment

from ml.training.losses import inverse_transform, transform_cents

TRAJECTORY_SERIES = ("inflow", "essential_outflow", "discretionary_outflow", "balance_residual")

# Renormalized from section 60's weights across the objectives Mini actually
# trains: trajectory, event-set, distress, accounting, intervention-delta.
TRAJECTORY_WEIGHT = 0.30
EVENT_SET_WEIGHT = 0.25
DISTRESS_WEIGHT = 0.25
ACCOUNTING_WEIGHT = 0.08
INTERVENTION_DELTA_WEIGHT = 0.12
MASKED_RECON_WEIGHT = 0.10  # only nonzero when config.use_masked_pretraining is set (Flash)


def select_best_scenario(pred_trajectory: dict[str, torch.Tensor], batch: dict[str, torch.Tensor]) -> tuple[torch.Tensor, torch.Tensor]:
    """Returns (best_idx (B,), per_series_target dict already amount-transformed)."""
    targets = {
        "inflow": transform_cents(batch["target_uncertain_inflow_cents"]),
        "essential_outflow": transform_cents(batch["target_uncertain_essential_outflow_cents"]),
        "discretionary_outflow": transform_cents(batch["target_uncertain_discretionary_outflow_cents"]),
        "balance_residual": transform_cents(batch["target_full_balance_cents"] - batch["target_known_balance_cents"]),
    }
    per_scenario_error = 0.0
    for series in TRAJECTORY_SERIES:
        err = (pred_trajectory[series] - targets[series].unsqueeze(1)).abs().mean(dim=-1)  # (B, K)
        per_scenario_error = per_scenario_error + err
    best_idx = per_scenario_error.argmin(dim=1)  # (B,)
    return best_idx, targets


def _gather_scenario(x: torch.Tensor, best_idx: torch.Tensor) -> torch.Tensor:
    """x: (B, K, ...) -> (B, ...) selecting each row's winning scenario."""
    idx = best_idx.view(-1, *([1] * (x.dim() - 1))).expand(-1, 1, *x.shape[2:])
    return x.gather(1, idx).squeeze(1)


def trajectory_loss(selected_trajectory: dict[str, torch.Tensor], targets: dict[str, torch.Tensor]) -> torch.Tensor:
    losses = [F.l1_loss(selected_trajectory[s], targets[s]) for s in TRAJECTORY_SERIES]
    return sum(losses) / len(losses)


def accounting_consistency_loss(selected_trajectory: dict[str, torch.Tensor]) -> torch.Tensor:
    inflow = inverse_transform(selected_trajectory["inflow"])
    essential = inverse_transform(selected_trajectory["essential_outflow"])
    discretionary = inverse_transform(selected_trajectory["discretionary_outflow"])
    balance = inverse_transform(selected_trajectory["balance_residual"])
    implied = torch.cumsum(inflow - essential - discretionary, dim=1)
    return F.mse_loss(implied / 1e5, balance / 1e5)


_MATCH_WEIGHTS = dict(exist=1.0, type=1.0, time=2.0, amount=1.0, direction=0.5, account=0.5, recurrence=0.25, obligation=0.25)


def event_set_matching_loss(selected_event_set: dict[str, torch.Tensor], batch: dict[str, torch.Tensor]) -> torch.Tensor:
    """DETR-style bipartite matching loss. Loops over the batch in Python
    (variable true-event counts per household don't vectorize cleanly);
    `scipy.optimize.linear_sum_assignment` runs on tiny (<=max_event_slots)
    matrices so this stays fast relative to the decoder forward pass."""
    existence_logit = selected_event_set["existence_logit"]
    B, S = existence_logit.shape
    valid_mask = batch["event_set_valid_mask"]
    device = existence_logit.device
    total = existence_logit.new_zeros(())

    for b in range(B):
        n_true = int(valid_mask[b].sum().item())
        exist_logit_b = existence_logit[b]

        if n_true == 0:
            total = total + F.binary_cross_entropy_with_logits(exist_logit_b, torch.zeros_like(exist_logit_b))
            continue

        with torch.no_grad():
            exist_prob = torch.sigmoid(exist_logit_b)
            type_logp = F.log_softmax(selected_event_set["event_type_logits"][b], dim=-1)
            true_type = batch["event_set_type_idx"][b, :n_true]
            type_cost = -type_logp[:, true_type]

            time_cost = (selected_event_set["time_fraction"][b].unsqueeze(1) - batch["event_set_time_fraction"][b, :n_true].unsqueeze(0)).abs()
            amount_cost = (selected_event_set["amount"][b].unsqueeze(1) - batch["event_set_amount"][b, :n_true].unsqueeze(0)).abs()

            dir_logp = F.log_softmax(selected_event_set["direction_logits"][b], dim=-1)
            true_dir = batch["event_set_direction_idx"][b, :n_true]
            dir_cost = -dir_logp[:, true_dir]

            acct_logp = F.log_softmax(selected_event_set["account_logits"][b], dim=-1)
            true_acct = batch["event_set_account_idx"][b, :n_true]
            acct_cost = -acct_logp[:, true_acct]

            cost = (
                _MATCH_WEIGHTS["exist"] * (-exist_prob.unsqueeze(1))
                + _MATCH_WEIGHTS["type"] * type_cost
                + _MATCH_WEIGHTS["time"] * time_cost
                + _MATCH_WEIGHTS["amount"] * amount_cost
                + _MATCH_WEIGHTS["direction"] * dir_cost
                + _MATCH_WEIGHTS["account"] * acct_cost
            )
            row_idx, col_idx = linear_sum_assignment(cost.cpu().numpy())

        matched_pred = torch.as_tensor(row_idx, device=device, dtype=torch.long)
        matched_true = torch.as_tensor(col_idx, device=device, dtype=torch.long)

        exist_target = torch.zeros(S, device=device)
        exist_target[matched_pred] = 1.0
        exist_loss = F.binary_cross_entropy_with_logits(exist_logit_b, exist_target)

        type_loss = F.cross_entropy(selected_event_set["event_type_logits"][b][matched_pred], batch["event_set_type_idx"][b][matched_true])
        time_loss = F.l1_loss(selected_event_set["time_fraction"][b][matched_pred], batch["event_set_time_fraction"][b][matched_true])
        amount_loss = F.l1_loss(selected_event_set["amount"][b][matched_pred], batch["event_set_amount"][b][matched_true])
        dir_loss = F.cross_entropy(selected_event_set["direction_logits"][b][matched_pred], batch["event_set_direction_idx"][b][matched_true])
        acct_loss = F.cross_entropy(selected_event_set["account_logits"][b][matched_pred], batch["event_set_account_idx"][b][matched_true])
        rec_loss = F.cross_entropy(selected_event_set["recurrence_logits"][b][matched_pred], batch["event_set_recurrence_idx"][b][matched_true])
        obl_loss = F.binary_cross_entropy_with_logits(
            selected_event_set["obligation_linked_logit"][b][matched_pred], batch["event_set_obligation_linked"][b][matched_true]
        )

        total = total + (
            _MATCH_WEIGHTS["exist"] * exist_loss
            + _MATCH_WEIGHTS["type"] * type_loss
            + _MATCH_WEIGHTS["time"] * time_loss
            + _MATCH_WEIGHTS["amount"] * amount_loss
            + _MATCH_WEIGHTS["direction"] * dir_loss
            + _MATCH_WEIGHTS["account"] * acct_loss
            + _MATCH_WEIGHTS["recurrence"] * rec_loss
            + _MATCH_WEIGHTS["obligation"] * obl_loss
        )

    return total / max(B, 1)


def intervention_delta_loss(
    selected_baseline: dict[str, torch.Tensor], selected_intervention: dict[str, torch.Tensor], batch: dict[str, torch.Tensor]
) -> torch.Tensor:
    """Section 30: the model should learn the difference directly. Predicted
    delta = intervention balance-residual minus baseline balance-residual
    (same selected scenario, i.e. same z — coupled sampling, section 31),
    both inverse-transformed to cents before comparing to the true delta.
    Masked to households that actually have a valid synthetic intervention
    pair (`has_intervention`); the rest contribute zero."""
    pred_baseline_cents = inverse_transform(selected_baseline["balance_residual"])
    pred_intervention_cents = inverse_transform(selected_intervention["balance_residual"])
    pred_delta = pred_intervention_cents - pred_baseline_cents  # (B, horizon)

    true_delta = batch["intervention_delta_balance_cents"]
    mask = batch["has_intervention"].unsqueeze(-1)

    per_example = (pred_delta - true_delta).abs().mean(dim=-1, keepdim=True) / 1e4  # dollars-ish scale
    weighted = per_example * mask
    denom = mask.sum().clamp(min=1.0)
    return weighted.sum() / denom


def masked_reconstruction_loss(mlm_out: dict[str, torch.Tensor] | None, batch: dict[str, torch.Tensor]) -> torch.Tensor:
    """Section 49, Objective One: reconstruct every categorical financial
    field and the normalized numeric feature vector at masked event positions.
    Mini never enables this path; Flash does."""
    if mlm_out is None or not mlm_out["mask"].any():
        return torch.zeros(())
    mask = mlm_out["mask"]
    categorical_losses = [
        F.cross_entropy(logits[mask], batch["event_cat"][..., field_idx][mask])
        for field_idx, logits in enumerate(mlm_out["categorical_logits"])
    ]
    categorical_loss = torch.stack(categorical_losses).mean()
    numeric_loss = F.smooth_l1_loss(
        mlm_out["numeric_prediction"][mask],
        batch["event_numeric"][mask],
    )
    return 0.75 * categorical_loss + 0.25 * numeric_loss


def _to_fp32(output):
    """Under bf16 mixed precision (Accelerate autocasts the forward pass),
    every raw model output is bf16 while batch targets loaded from the
    DataLoader stay fp32. Some loss kernels (`binary_cross_entropy`) refuse
    to implicitly promote mismatched dtypes and raise; loss computation
    should run in fp32 regardless of the forward pass's dtype anyway, so
    cast everything here rather than scattering `.float()` calls through
    every loss function."""
    from dataclasses import replace

    return replace(
        output,
        distress_probabilities=output.distress_probabilities.float(),
        reason_factors=output.reason_factors.float(),
        baseline_trajectory={k: v.float() for k, v in output.baseline_trajectory.items()},
        baseline_event_set={k: v.float() for k, v in output.baseline_event_set.items()},
        intervention_trajectory=(
            {k: v.float() for k, v in output.intervention_trajectory.items()}
            if output.intervention_trajectory is not None else None
        ),
        masked_reconstruction=(
            {
                **output.masked_reconstruction,
                "categorical_logits": [
                    logits.float() for logits in output.masked_reconstruction["categorical_logits"]
                ],
                "numeric_prediction": output.masked_reconstruction["numeric_prediction"].float(),
            }
            if output.masked_reconstruction is not None else None
        ),
    )


def compute_mini_loss(output, batch: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    output = _to_fp32(output)
    best_idx, targets = select_best_scenario(output.baseline_trajectory, batch)
    selected_baseline = {s: _gather_scenario(output.baseline_trajectory[s], best_idx) for s in TRAJECTORY_SERIES}
    selected_event_set = {k: _gather_scenario(v, best_idx) for k, v in output.baseline_event_set.items()}

    traj_loss = trajectory_loss(selected_baseline, targets)
    event_loss = event_set_matching_loss(selected_event_set, batch)
    accounting_loss = accounting_consistency_loss(selected_baseline)
    distress_loss = F.binary_cross_entropy(output.distress_probabilities, batch["target_distress"])

    intervention_loss = torch.zeros((), device=traj_loss.device)
    if output.intervention_trajectory is not None:
        selected_intervention = {s: _gather_scenario(output.intervention_trajectory[s], best_idx) for s in TRAJECTORY_SERIES}
        intervention_loss = intervention_delta_loss(selected_baseline, selected_intervention, batch)

    masked_recon_loss = masked_reconstruction_loss(output.masked_reconstruction, batch).to(traj_loss.device)

    total = (
        TRAJECTORY_WEIGHT * traj_loss
        + EVENT_SET_WEIGHT * event_loss
        + DISTRESS_WEIGHT * distress_loss
        + ACCOUNTING_WEIGHT * accounting_loss
        + INTERVENTION_DELTA_WEIGHT * intervention_loss
        + MASKED_RECON_WEIGHT * masked_recon_loss
    )
    return {
        "total": total,
        "trajectory_loss": traj_loss.detach(),
        "event_set_loss": event_loss.detach(),
        "distress_loss": distress_loss.detach(),
        "accounting_loss": accounting_loss.detach(),
        "intervention_delta_loss": intervention_loss.detach(),
        "masked_recon_loss": masked_recon_loss.detach(),
    }
