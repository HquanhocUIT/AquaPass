from __future__ import annotations

from app.modules.decision.decision_version import (
    DecisionVersion,
    create_next_decision_version,
)


def create_updated_decision(
    previous: DecisionVersion,
    *,
    uncertainty: float,
    uncertainty_level: str,
    hypothesis_summary: str,
    triggering_evidence_id: str,
) -> DecisionVersion:
    """
    Create the next immutable decision version.

    The updater does not mutate the previous version.
    It creates a new version whose number is previous.version + 1.
    """

    if not triggering_evidence_id:
        raise ValueError(
            "triggering_evidence_id must not be empty"
        )

    return create_next_decision_version(
        previous,
        uncertainty=uncertainty,
        uncertainty_level=uncertainty_level,
        hypothesis_summary=hypothesis_summary,
        triggering_evidence_id=triggering_evidence_id,
    )