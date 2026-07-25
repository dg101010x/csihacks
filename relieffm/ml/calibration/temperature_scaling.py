"""Section 67 — temperature scaling for the distress heads.

Grid search rather than an optimizer dependency: Nano's calibration set is
small (thousands of households, not millions), and T has one degree of
freedom per risk, so a coarse-to-fine grid search converges in a handful
of evaluations without adding scipy as a dependency for one scalar fit.
"""
from __future__ import annotations

import numpy as np


def _bce(probs: np.ndarray, labels: np.ndarray, eps: float = 1e-7) -> float:
    p = np.clip(probs, eps, 1 - eps)
    return float(-np.mean(labels * np.log(p) + (1 - labels) * np.log(1 - p)))


def _apply_temperature(probs: np.ndarray, temperature: float, eps: float = 1e-7) -> np.ndarray:
    p = np.clip(probs, eps, 1 - eps)
    logits = np.log(p / (1 - p))
    scaled = logits / temperature
    return 1.0 / (1.0 + np.exp(-scaled))


def fit_temperature(probs: np.ndarray, labels: np.ndarray, coarse=(0.05, 5.0, 60), refine_steps: int = 2) -> float:
    """Returns the temperature T minimizing BCE. T>1 softens (the model was
    overconfident), T<1 sharpens (the model was underconfident)."""
    lo, hi, n = coarse
    best_t, best_loss = 1.0, _bce(probs, labels)
    for _ in range(refine_steps + 1):
        candidates = np.linspace(lo, hi, n)
        for t in candidates:
            loss = _bce(_apply_temperature(probs, t), labels)
            if loss < best_loss:
                best_loss, best_t = loss, float(t)
        span = (hi - lo) / n * 3
        lo, hi = max(best_t - span, 1e-3), best_t + span
    return best_t


def apply_temperature(probs: np.ndarray, temperature: float) -> np.ndarray:
    return _apply_temperature(probs, temperature)
