from __future__ import annotations

from .models import PackageStage

# Explicit state graph (Section 62) rather than free-form status flags, so
# every transition is checkable independent of which caller drives it — a
# LangGraph-backed agent (the eventual Section 62 implementation) would walk
# this same graph rather than replacing it; only the *decision* of which
# edge to take could become model-driven, never an edge that isn't listed
# here.
ALLOWED_TRANSITIONS: dict[PackageStage, set[PackageStage]] = {
    PackageStage.review: {PackageStage.confirmed},
    PackageStage.confirmed: {PackageStage.submitted},
    PackageStage.submitted: {PackageStage.pending_provider, PackageStage.accepted},
    PackageStage.pending_provider: {PackageStage.accepted, PackageStage.rejected},
    PackageStage.accepted: {PackageStage.executed},
    PackageStage.rejected: set(),
    PackageStage.executed: set(),
}


class InvalidTransitionError(Exception):
    pass


def validate_transition(current: PackageStage, target: PackageStage) -> None:
    if target not in ALLOWED_TRANSITIONS.get(current, set()):
        raise InvalidTransitionError(f"cannot move from {current.value} to {target.value}")
