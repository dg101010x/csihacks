"""Section 60's combined loss, trimmed to what ReliefFM Nano actually
trains this session (see ml/model_cards/relieffm_nano.md "Known
limitations" for what's dropped and why):

  trajectory_loss   pinball loss on the four uncertain-component quantile
                     series (section 25) against amount-transformed targets
  distress_loss      BCE on the three risks x three horizons (section 26)
  accounting_loss    consistency between the balance-residual head and the
                     balance implied by cumsum(inflow - outflows) from the
                     other three heads (section 57, adapted for Nano's
                     aggregate-quantile heads instead of an event decoder)

known_event_preservation_loss (section 58) has no soft-loss term here: Nano
never predicts known events at all (they're clamped in deterministically,
section 23), so the omission rate this loss exists to reduce is
structurally zero rather than merely penalized. masked_field / next_event /
past_reconstruction / recurrence / contrastive (Stage One's self-supervised
objectives) are out of scope for this session.

Weights are section 60's trajectory/distress/accounting weights (0.12,
0.10, 0.04) renormalized over just these three terms.
"""
from __future__ import annotations

import torch
import torch.nn.functional as F

from ml.relieffm.features import amount_transform
from ml.relieffm.model import ReliefFMOutput

QUANTILE_LEVELS = (0.1, 0.5, 0.9)

TRAJECTORY_WEIGHT = 0.46
DISTRESS_WEIGHT = 0.38
ACCOUNTING_WEIGHT = 0.15


def pinball_loss(pred_quantiles: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """pred_quantiles: (..., n_quantiles), target: (...) -> scalar mean loss."""
    target = target.unsqueeze(-1)
    errors = target - pred_quantiles
    taus = torch.tensor(QUANTILE_LEVELS, device=pred_quantiles.device, dtype=pred_quantiles.dtype)
    losses = torch.maximum(taus * errors, (taus - 1) * errors)
    return losses.mean()


def transform_cents(x_cents: torch.Tensor) -> torch.Tensor:
    dollars = x_cents / 100.0
    sign = torch.sign(dollars)
    return sign * torch.log1p(torch.abs(dollars))


def inverse_transform(x: torch.Tensor) -> torch.Tensor:
    sign = torch.sign(x)
    return sign * torch.expm1(torch.abs(x)) * 100.0


def compute_loss(output: ReliefFMOutput, batch: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    inflow_target = transform_cents(batch["target_uncertain_inflow_cents"])
    essential_target = transform_cents(batch["target_uncertain_essential_outflow_cents"])
    discretionary_target = transform_cents(batch["target_uncertain_discretionary_outflow_cents"])
    balance_residual_target = transform_cents(
        batch["target_full_balance_cents"] - batch["target_known_balance_cents"]
    )

    trajectory_loss = (
        pinball_loss(output.inflow_quantiles, inflow_target)
        + pinball_loss(output.essential_outflow_quantiles, essential_target)
        + pinball_loss(output.discretionary_outflow_quantiles, discretionary_target)
        + pinball_loss(output.balance_residual_quantiles, balance_residual_target)
    ) / 4.0

    distress_loss = F.binary_cross_entropy(output.distress_probabilities, batch["target_distress"])

    median_idx = QUANTILE_LEVELS.index(0.5)
    inflow_med = inverse_transform(output.inflow_quantiles[..., median_idx])
    essential_med = inverse_transform(output.essential_outflow_quantiles[..., median_idx])
    discretionary_med = inverse_transform(output.discretionary_outflow_quantiles[..., median_idx])
    balance_med = inverse_transform(output.balance_residual_quantiles[..., median_idx])

    implied_balance = torch.cumsum(inflow_med - essential_med - discretionary_med, dim=1)
    accounting_loss = F.mse_loss(implied_balance / 1e5, balance_med / 1e5)

    total = (
        TRAJECTORY_WEIGHT * trajectory_loss
        + DISTRESS_WEIGHT * distress_loss
        + ACCOUNTING_WEIGHT * accounting_loss
    )
    return {
        "total": total,
        "trajectory_loss": trajectory_loss.detach(),
        "distress_loss": distress_loss.detach(),
        "accounting_loss": accounting_loss.detach(),
    }
