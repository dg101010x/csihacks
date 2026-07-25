from __future__ import annotations

"""Essentiality scoring (Section 36) — how disruptive missing this payment
is to the household's basic stability. Housing and secured debt score
highest; discretionary subscriptions lowest. Consumer-confirmed overrides
(ObligationV1.consumer_confirmed) always take precedence over this table —
it only supplies the initial estimate for a newly detected obligation.
"""

_CATEGORY_ESSENTIALITY: dict[str, tuple[str, float]] = {
    "rent": ("rent", 0.95),
    "mortgage": ("mortgage", 0.95),
    "housing": ("rent", 0.95),
    "utility": ("utility", 0.85),
    "utilities": ("utility", 0.85),
    "insurance": ("insurance", 0.8),
    "loan_payment": ("loan_payment", 0.75),
    "auto_loan": ("loan_payment", 0.75),
    "medical": ("medical", 0.7),
    "healthcare": ("medical", 0.7),
    "childcare": ("childcare", 0.7),
    "groceries": ("groceries", 0.6),
    "transportation": ("transportation", 0.55),
    "credit_card_minimum": ("credit_card_minimum", 0.4),
    "credit_card": ("credit_card_minimum", 0.4),
    "subscription": ("subscription", 0.05),
    "entertainment": ("subscription", 0.05),
}

_DEFAULT_ESSENTIALITY = 0.3
_DEFAULT_TYPE = "other"


def classify_essentiality(merchant_category: str | None, event_type: str) -> tuple[str, float]:
    """Returns (obligation_type, essentiality_score) for a detected pattern."""
    key = (merchant_category or event_type or "").lower()
    if key in _CATEGORY_ESSENTIALITY:
        return _CATEGORY_ESSENTIALITY[key]
    return (merchant_category or _DEFAULT_TYPE, _DEFAULT_ESSENTIALITY)
