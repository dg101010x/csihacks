"""Sections 84/85/88 (subset) — trajectory, distress, and calibration metrics."""
from __future__ import annotations

import numpy as np


def pinball_loss(pred_quantiles: np.ndarray, target: np.ndarray, quantile_levels=(0.1, 0.5, 0.9)) -> float:
    """pred_quantiles: (..., n_quantiles), target: (...)."""
    target = target[..., None]
    taus = np.array(quantile_levels)
    errors = target - pred_quantiles
    losses = np.maximum(taus * errors, (taus - 1) * errors)
    return float(losses.mean())


def balance_mae(pred_balance: np.ndarray, true_balance: np.ndarray) -> float:
    return float(np.mean(np.abs(pred_balance - true_balance)))


def min_balance_error(pred_traj: np.ndarray, true_traj: np.ndarray) -> float:
    """pred_traj/true_traj: (N, horizon_days)."""
    return float(np.mean(np.abs(pred_traj.min(axis=1) - true_traj.min(axis=1))))


def end_balance_error(pred_traj: np.ndarray, true_traj: np.ndarray) -> float:
    return float(np.mean(np.abs(pred_traj[:, -1] - true_traj[:, -1])))


def negative_balance_probability_error(pred_prob_negative: np.ndarray, true_traj: np.ndarray) -> float:
    true_frac_negative = (true_traj.min(axis=1) < 0).astype(np.float64)
    return float(np.mean(np.abs(pred_prob_negative - true_frac_negative)))


def brier_score(probs: np.ndarray, labels: np.ndarray) -> float:
    return float(np.mean((probs - labels) ** 2))


def expected_calibration_error(probs: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> float:
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(probs)
    if n == 0:
        return 0.0
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (probs >= lo) & (probs < hi) if hi < 1.0 else (probs >= lo) & (probs <= hi)
        if mask.sum() == 0:
            continue
        bin_conf = probs[mask].mean()
        bin_acc = labels[mask].mean()
        ece += (mask.sum() / n) * abs(bin_conf - bin_acc)
    return float(ece)


def false_reassurance_rate(probs: np.ndarray, labels: np.ndarray, threshold: float = 0.2) -> float:
    """Fraction of actual-distress cases the model called low-risk (section 86:
    "the model predicts safety when distress occurs"). Weighted more heavily
    than plain accuracy per section 86."""
    distressed = labels.astype(bool)
    if distressed.sum() == 0:
        return 0.0
    return float(np.mean(probs[distressed] < threshold))


def bootstrap_ci(values: np.ndarray, n_resamples: int = 1000, seed: int = 0) -> tuple[float, float, float]:
    """Section 92: bootstrap over households (the caller must pass one value
    per household, not per event) -> (mean, ci_lo, ci_hi)."""
    rng = np.random.default_rng(seed)
    n = len(values)
    if n == 0:
        return 0.0, 0.0, 0.0
    means = np.array(
        [values[rng.integers(0, n, size=n)].mean() for _ in range(n_resamples)]
    )
    return float(values.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))
