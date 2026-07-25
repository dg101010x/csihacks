from __future__ import annotations

import re
import time
import uuid
from datetime import datetime, timezone

from .models import ApprovalRequirement, ConstitutionRuleV1, RuleStatus

# Keyword -> scope/action heuristics (Section 71). This is the server-side
# home for what previously lived only in the frontend's synthetic adapter
# (parseConstitutionRule) — same regex behavior, so existing UI expectations
# don't shift when this starts backing the real endpoint. A LangChain-backed
# parser (Section 63) is the eventual replacement; this is the deterministic
# fallback it needs to at least match.
_SCOPE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"rent|housing"), "housing"),
    (re.compile(r"grocer"), "groceries"),
    (re.compile(r"medic|health"), "medicine"),
    (re.compile(r"transport|car|auto"), "transportation"),
    (re.compile(r"subscri"), "subscriptions"),
    (re.compile(r"loan|interest"), "loans"),
]

_AMOUNT_RE = re.compile(r"\$?(\d+(?:\.\d{2})?)")
_ALWAYS_ASK_RE = re.compile(r"\bask\b|confirm")


def parse_constitution_rule(raw_text: str) -> ConstitutionRuleV1:
    lower = raw_text.lower()

    scope = [label for pattern, label in _SCOPE_PATTERNS if pattern.search(lower)]

    permitted: list[str] = []
    if "split" in lower:
        permitted.append("split_payment")
    if "pause" in lower:
        permitted.append("pause_subscription")

    prohibited: list[str] = []
    if re.search(r"never.*interest|no.*interest", lower):
        prohibited.append("term_extension_with_interest")
    if re.search(r"never delay rent|never.*rent", lower):
        prohibited.append("delay_rent_without_confirmation")

    amount_match = _AMOUNT_RE.search(lower)
    max_impact = round(float(amount_match.group(1)) * 100) if amount_match else None

    always_ask = bool(_ALWAYS_ASK_RE.search(lower))

    trigger = f"Any candidate intervention touching: {', '.join(scope)}." if scope else "Any candidate intervention."
    confidence = 0.6 + (0.1 if scope else 0.0) + (0.1 if permitted or prohibited else 0.0)

    return ConstitutionRuleV1(
        rule_id=f"draft_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}",
        status=RuleStatus.draft,
        raw_text=raw_text,
        trigger=trigger,
        scope=scope or ["all"],
        permitted_actions=permitted,
        prohibited_actions=prohibited,
        approval_requirement=ApprovalRequirement.always_ask if always_ask else ApprovalRequirement.consumer_confirmation,
        maximum_monetary_impact_cents=max_impact,
        expiration=None,
        priority=5,
        exceptions=[],
        confidence=round(confidence, 2),
        created_at=datetime.now(timezone.utc),
    )
