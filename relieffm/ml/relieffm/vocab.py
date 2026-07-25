"""Fixed categorical vocabularies for the Financial Field Encoder (section 13).

Index 0 is reserved for PAD/UNK in every vocabulary so padding tokens and
values unseen at vocab-build time both degrade gracefully instead of
crashing — this matters once real (partner/public) data with categories
the synthetic generator never produced starts flowing through the same
compiler (section 90's robustness expectation).
"""
from __future__ import annotations

PAD = "__pad__"


def _vocab(values: list[str]) -> dict[str, int]:
    return {PAD: 0, **{v: i + 1 for i, v in enumerate(values)}}


def index_of(vocab: dict[str, int], value) -> int:
    key = value.value if hasattr(value, "value") else str(value)
    return vocab.get(key, 0)


EVENT_TYPE = _vocab(
    [
        "paycheck", "rent_payment", "mortgage_payment", "auto_loan_payment",
        "personal_loan_payment", "credit_card_payment", "insurance_premium",
        "utility_bill", "subscription", "bnpl_payment", "medical_payment",
        "transfer", "fee", "refund", "purchase", "deposit", "withdrawal",
        "shock_expense", "other",
    ]
)
EVENT_STATUS = _vocab(["posted", "pending", "scheduled", "cancelled", "failed"])
DIRECTION = _vocab(["inflow", "outflow"])
RECURRENCE_STATE = _vocab(["none", "weekly", "biweekly", "semimonthly", "monthly", "irregular"])
SOURCE_TYPE = _vocab(["bank_feed", "card_feed", "manual", "simulated", "provider_confirmed"])
ACCOUNT_TYPE = _vocab(["checking", "savings", "credit_card", "loan", "brokerage"])
OBLIGATION_TYPE = _vocab(
    [
        "rent", "mortgage", "auto_loan", "personal_loan", "credit_card_minimum",
        "insurance_premium", "utility", "subscription", "bnpl", "medical_payment_plan",
    ]
)
ESSENTIALITY = _vocab(["essential", "discretionary"])
PAYMENT_STATUS = _vocab(["current", "late", "missed", "in_hardship_program"])
KNOWN_FUTURE_SOURCE = _vocab(
    [
        "confirmed_paycheck", "scheduled_loan_payment", "confirmed_rent_payment",
        "confirmed_insurance_premium", "approved_intervention_event",
    ]
)
INTERVENTION_ACTION_TYPE = _vocab(
    [
        "split_payment", "delay_payment", "waive_fee", "pause_subscription",
        "hardship_program", "reduce_payment", "refinance",
    ]
)
MERCHANT_CATEGORY = _vocab(
    [
        "payroll", "housing", "groceries", "fuel", "pharmacy", "utilities_variable",
        "dining", "entertainment", "shopping", "travel", "bank_fee", "refund",
        "rent", "mortgage", "auto_loan", "personal_loan", "credit_card_minimum",
        "insurance_premium", "utility", "subscription", "bnpl", "medical_payment_plan",
        "vehicle_repair", "medical_expense", "duplicate_charge", "utility_spike",
        "unplanned_family_expense", "emergency_travel", "unknown",
    ]
)
