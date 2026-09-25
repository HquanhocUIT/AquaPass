from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DecisionVersion:
    decision_id: str
    version: int
    incident_id: str
    uncertainty: float
    uncertainty_level: str
    hypothesis_summary: str
    triggering_evidence_id: str | None = None
    created_at: datetime | None = None


def _validate_decision_version(
    decision: DecisionVersion,
) -> None:
    if not decision.decision_id:
        raise ValueError("decision_id must not be empty")

    if not decision.incident_id:
        raise ValueError("incident_id must not be empty")

    if decision.version < 1:
        raise ValueError("version must be at least 1")

    if not 0.0 <= decision.uncertainty <= 1.0:
        raise ValueError(
            "uncertainty must be between 0.0 and 1.0"
        )

    if decision.uncertainty_level not in {
        "low",
        "medium",
        "high",
    }:
        raise ValueError(
            "uncertainty_level must be one of: low, medium, high"
        )

    if not decision.hypothesis_summary:
        raise ValueError(
            "hypothesis_summary must not be empty"
        )


def create_decision_version(
    *,
    decision_id: str,
    version: int,
    incident_id: str,
    uncertainty: float,
    uncertainty_level: str,
    hypothesis_summary: str,
    triggering_evidence_id: str | None = None,
    created_at: datetime | None = None,
) -> DecisionVersion:
    decision = DecisionVersion(
        decision_id=decision_id,
        version=version,
        incident_id=incident_id,
        uncertainty=uncertainty,
        uncertainty_level=uncertainty_level,
        hypothesis_summary=hypothesis_summary,
        triggering_evidence_id=triggering_evidence_id,
        created_at=created_at,
    )

    _validate_decision_version(decision)

    return decision


def create_next_decision_version(
    previous: DecisionVersion,
    *,
    uncertainty: float,
    uncertainty_level: str,
    hypothesis_summary: str,
    triggering_evidence_id: str | None = None,
    created_at: datetime | None = None,
) -> DecisionVersion:
    _validate_decision_version(previous)

    return create_decision_version(
        decision_id=previous.decision_id,
        version=previous.version + 1,
        incident_id=previous.incident_id,
        uncertainty=uncertainty,
        uncertainty_level=uncertainty_level,
        hypothesis_summary=hypothesis_summary,
        triggering_evidence_id=triggering_evidence_id,
        created_at=created_at,
    )