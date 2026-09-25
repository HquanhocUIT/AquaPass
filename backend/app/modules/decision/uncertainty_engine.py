from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


VALID_STATES = {
    "available",
    "missing",
    "conflicting",
    "stale",
    "unreliable",
}

VALID_LEVELS = {
    "LOW",
    "MEDIUM",
    "HIGH",
}


@dataclass(frozen=True)
class DecisionEvidence:
    evidence_id: str
    state: str
    reliability: float
    supports_decision: bool = True


@dataclass(frozen=True)
class UncertaintyResult:
    score: float
    level: str
    previous_score: float | None
    previous_level: str | None
    explanation: str


def _validate_evidence(evidence: DecisionEvidence) -> None:
    if not evidence.evidence_id:
        raise ValueError("evidence_id must not be empty")

    if evidence.state not in VALID_STATES:
        raise ValueError(
            f"invalid evidence state: {evidence.state}"
        )

    if not 0.0 <= evidence.reliability <= 1.0:
        raise ValueError(
            "reliability must be between 0.0 and 1.0"
        )


def _contribution(evidence: DecisionEvidence) -> float:
    if not evidence.supports_decision:
        return 0.0

    if evidence.state == "available":
        return evidence.reliability

    if evidence.state == "conflicting":
        return evidence.reliability * 0.25

    if evidence.state == "stale":
        return evidence.reliability * 0.25

    if evidence.state == "unreliable":
        return evidence.reliability * 0.10

    return 0.0


def calculate_uncertainty(
    evidence: Iterable[DecisionEvidence],
) -> float:
    evidence_list = list(evidence)

    for item in evidence_list:
        _validate_evidence(item)

    if not evidence_list:
        return 1.0

    contributions = [
        _contribution(item)
        for item in evidence_list
    ]

    coverage = sum(contributions) / len(evidence_list)

    uncertainty = 1.0 - coverage

    return round(
        max(0.0, min(1.0, uncertainty)),
        4,
    )


def classify_uncertainty(score: float) -> str:
    if not 0.0 <= score <= 1.0:
        raise ValueError(
            "uncertainty score must be between 0.0 and 1.0"
        )

    if score >= 0.70:
        return "HIGH"

    if score >= 0.40:
        return "MEDIUM"

    return "LOW"


def evaluate_uncertainty(
    evidence: Iterable[DecisionEvidence],
    *,
    previous_score: float | None = None,
    previous_level: str | None = None,
) -> UncertaintyResult:
    score = calculate_uncertainty(evidence)
    level = classify_uncertainty(score)

    if previous_score is None:
        explanation = (
            "Prototype uncertainty index calculated from "
            "decision-relevant evidence states and reliability."
        )
    else:
        change = round(previous_score - score, 4)

        if change > 0:
            explanation = (
                f"Prototype uncertainty decreased by {change:.4f} "
                f"after considering the current evidence."
            )
        elif change < 0:
            explanation = (
                f"Prototype uncertainty increased by "
                f"{abs(change):.4f}."
            )
        else:
            explanation = (
                "Prototype uncertainty did not change."
            )

    return UncertaintyResult(
        score=score,
        level=level,
        previous_score=previous_score,
        previous_level=previous_level,
        explanation=explanation,
    )