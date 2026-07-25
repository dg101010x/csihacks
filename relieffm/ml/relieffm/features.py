"""Section 14 (amount transform) and section 15 (time representation).

Shared by the tokenizer (encoding inputs) and the training/inference code
(transforming and inverse-transforming trajectory-head targets), so both
sides agree on the exact same scale.
"""
from __future__ import annotations

import math
from datetime import datetime

DOLLARS_PER_UNIT = 100.0  # cents -> dollars before the log, keeps magnitudes sane


def amount_transform(amount_cents: float) -> float:
    """Section 14: x = sign(a) * log(1 + |a|), applied in dollars."""
    dollars = amount_cents / DOLLARS_PER_UNIT
    return math.copysign(math.log1p(abs(dollars)), dollars) if dollars != 0 else 0.0


def amount_inverse_transform(x: float) -> float:
    dollars = math.copysign(math.expm1(abs(x)), x)
    return dollars * DOLLARS_PER_UNIT


def relative_to_income(amount_cents: float, income_cents: float) -> float:
    return amount_cents / max(abs(income_cents), 1.0)


def relative_to_balance(amount_cents: float, balance_cents: float) -> float:
    return amount_cents / max(abs(balance_cents), 100.0)


def calendar_features(t: datetime) -> tuple[float, float, float, float]:
    """Section 15's Fourier calendar embedding, as raw sin/cos features fed
    into the numeric projection (cheaper than a learned calendar embedding
    table for Nano's scale)."""
    dow = t.weekday() / 7.0
    dom = (t.day - 1) / 31.0
    return (
        math.sin(2 * math.pi * dow),
        math.cos(2 * math.pi * dow),
        math.sin(2 * math.pi * dom),
        math.cos(2 * math.pi * dom),
    )


def time_offset_days(t: datetime, as_of: datetime) -> float:
    return (t - as_of).total_seconds() / 86400.0
