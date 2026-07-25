"""Section 79 — tabular baseline (gradient boosted trees) for distress
prediction. Hand-engineered liquidity/recurrence features (section 79),
no learned representation.

**Correctness note (found during the Mini upgrade):** the original version
of this file fed the model `HouseholdParams` fields directly —
`income_reliability`, `income_volatility`, `spending_volatility`,
`debt_burden`, `credit_utilization`, `shock_frequency` — which are the
simulator's *hidden generative parameters*, not anything a real
`HouseholdSnapshotV1` exposes. That inflated its apparent advantage over
ReliefFM Nano in the first evaluation. Feature extraction now goes through
`ml/relieffm/engineered_features.py`, which computes everything from the
compiled snapshot alone — the same function Mini's distress head uses, so
this baseline and that head can never quietly drift out of a fair
comparison again.
"""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from ml.datasets.compile import household_record_to_snapshot
from ml.relieffm.engineered_features import FEATURE_NAMES, compute_engineered_features
from ml.simulator.types import HouseholdRecord

__all__ = ["FEATURE_NAMES", "extract_features", "DistressGBMBaseline"]


def extract_features(record: HouseholdRecord) -> np.ndarray:
    snapshot = household_record_to_snapshot(record)
    return compute_engineered_features(snapshot).astype(np.float64)


class DistressGBMBaseline:
    def __init__(self, **kwargs):
        self.model = HistGradientBoostingClassifier(max_depth=4, max_iter=150, random_state=0, **kwargs)

    def fit(self, records: list[HouseholdRecord], labels: list[bool]) -> "DistressGBMBaseline":
        X = np.stack([extract_features(r) for r in records])
        y = np.array(labels, dtype=np.int64)
        if len(set(y.tolist())) < 2:
            # Degenerate synthetic sample (all one class) — fall back to a
            # constant predictor rather than letting sklearn raise.
            self._constant = float(y.mean())
            self.model = None
        else:
            self._constant = None
            self.model.fit(X, y)
        return self

    def predict_proba(self, records: list[HouseholdRecord]) -> np.ndarray:
        if self.model is None:
            return np.full(len(records), self._constant)
        X = np.stack([extract_features(r) for r in records])
        return self.model.predict_proba(X)[:, 1]
