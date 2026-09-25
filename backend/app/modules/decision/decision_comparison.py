from __future__ import annotations

from dataclasses import dataclass

from app.modules.decision.decision_version import (
    DecisionVersion,
)


@dataclass(frozen=True)
class DecisionComparison:
    decision_id: str
    from_version: int
    to_version: int
    triggering_evidence_id: str | None
    uncertainty_before: float
    uncertainty_after: float
    uncertainty_change: float
    hypothesis_changed: bool


def compare_decision_versions(
    before: DecisionVersion,
    after: DecisionVersion,
) -> DecisionComparison:
    if before.decision_id != after.decision_id:
        raise ValueError(
            "decision versions must belong to the same decision"
        )

    if after.version <= before.version:
        raise ValueError(
            "after version must be greater than before version"
        )

    return DecisionComparison(
        decision_id=before.decision_id,
        from_version=before.version,
        to_version=after.version,
        triggering_evidence_id=after.triggering_evidence_id,
        uncertainty_before=before.uncertainty,
        uncertainty_after=after.uncertainty,
        uncertainty_change=round(
            before.uncertainty - after.uncertainty,
            10,
        ),
        hypothesis_changed=(
            before.hypothesis_summary
            != after.hypothesis_summary
        ),
    )