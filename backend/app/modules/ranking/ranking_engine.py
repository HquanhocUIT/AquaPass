from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class RankingWeights:
    decision_value: float
    reliability: float
    feasibility: float
    cost_penalty: float
    time_penalty: float

    def __post_init__(self) -> None:
        values = {
            "decision_value": self.decision_value,
            "reliability": self.reliability,
            "feasibility": self.feasibility,
            "cost_penalty": self.cost_penalty,
            "time_penalty": self.time_penalty,
        }

        for name, value in values.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be between 0.0 and 1.0"
                )


@dataclass(frozen=True)
class EvidenceCandidate:
    evidence_id: str
    candidate_name: str
    decision_value: float
    reliability: float
    feasibility: float
    cost: float
    time: float
    is_feasible: bool = True
    infeasibility_reason: str | None = None


@dataclass(frozen=True)
class RankedEvidence:
    evidence_id: str
    candidate_name: str
    score: float
    rank: int
    decision_value: float
    reliability: float
    feasibility: float
    cost: float
    time: float
    explanation: str
    strengths: tuple[str, ...]
    tradeoffs: tuple[str, ...]
    selected: bool


DEFAULT_WEIGHTS = RankingWeights(
    decision_value=0.40,
    reliability=0.25,
    feasibility=0.15,
    cost_penalty=0.10,
    time_penalty=0.10,
)


def _validate_dimension(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(
            f"{name} must be between 0.0 and 1.0"
        )


def _validate_candidate(candidate: EvidenceCandidate) -> None:
    dimensions = {
        "decision_value": candidate.decision_value,
        "reliability": candidate.reliability,
        "feasibility": candidate.feasibility,
        "cost": candidate.cost,
        "time": candidate.time,
    }

    for name, value in dimensions.items():
        _validate_dimension(name, value)

    if not candidate.evidence_id:
        raise ValueError("evidence_id must not be empty")

    if not candidate.candidate_name:
        raise ValueError("candidate_name must not be empty")


def calculate_score(
    candidate: EvidenceCandidate,
    *,
    weights: RankingWeights = DEFAULT_WEIGHTS,
) -> float:
    """
    Calculate the deterministic prototype ranking score.

    Score =
        w_decision * DecisionValue
        + w_reliability * Reliability
        + w_feasibility * Feasibility
        - w_cost * Cost
        - w_time * Time
    """

    _validate_candidate(candidate)

    return (
        weights.decision_value * candidate.decision_value
        + weights.reliability * candidate.reliability
        + weights.feasibility * candidate.feasibility
        - weights.cost_penalty * candidate.cost
        - weights.time_penalty * candidate.time
    )

def _describe(value: float, dimension: str) -> str:
    if value >= 0.80:
        level = "very high"
    elif value >= 0.60:
        level = "high"
    elif value >= 0.40:
        level = "moderate"
    elif value >= 0.20:
        level = "low"
    else:
        level = "very low"

    return f"{level} {dimension}"


def _describe_inverse(value: float, dimension: str) -> str:
    if value <= 0.20:
        level = "low"
    elif value <= 0.40:
        level = "moderate"
    elif value <= 0.60:
        level = "high"
    else:
        level = "very high"

    return f"{level} {dimension}"


def _build_explanation(
    candidate: EvidenceCandidate,
    score: float,
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    if not candidate.is_feasible:
        reason = candidate.infeasibility_reason or (
            "The candidate does not satisfy the current operational constraints."
        )

        return (
            f"Not selected because it is infeasible under the current "
            f"constraints: {reason}",
            (),
            (reason,),
        )

    strengths: list[str] = []
    tradeoffs: list[str] = []

    if candidate.decision_value >= 0.80:
        strengths.append("very high decision value")
    elif candidate.decision_value >= 0.60:
        strengths.append("high decision value")

    if candidate.reliability >= 0.80:
        strengths.append("very high reliability")
    elif candidate.reliability >= 0.60:
        strengths.append("high reliability")

    if candidate.feasibility >= 0.80:
        strengths.append("high feasibility")
    elif candidate.feasibility >= 0.60:
        strengths.append("good feasibility")

    if candidate.cost <= 0.20:
        strengths.append("low acquisition burden")
    elif candidate.cost >= 0.60:
        tradeoffs.append("high acquisition burden")

    if candidate.time <= 0.20:
        strengths.append("fast turnaround")
    elif candidate.time >= 0.60:
        tradeoffs.append("slow turnaround")

    strength_text = ", ".join(strengths) if strengths else "balanced inputs"

    if tradeoffs:
        tradeoff_text = (
            " Tradeoffs include " + ", ".join(tradeoffs) + "."
        )
    else:
        tradeoff_text = ""

    explanation = (
        "Ranked using "
        f"{_describe(candidate.decision_value, 'decision value')}, "
        f"{_describe(candidate.reliability, 'reliability')}, "
        f"{_describe(candidate.feasibility, 'feasibility')}, "
        f"{_describe_inverse(candidate.cost, 'cost')}, "
        f"{_describe_inverse(candidate.time, 'time')}. "
        f"Prototype score: {score:.4f}."
    )

    return (
        explanation,
        tuple(strengths),
        tuple(tradeoffs),
    )


def rank_evidence(
    candidates: Iterable[EvidenceCandidate],
    *,
    weights: RankingWeights = DEFAULT_WEIGHTS,
) -> list[RankedEvidence]:
    """
    Rank candidate evidence deterministically.

    Candidates that violate hard operational constraints are excluded
    from normal ranking.

    Ties are resolved deterministically using evidence_id.
    """

    validated_candidates: list[EvidenceCandidate] = []

    for candidate in candidates:
        _validate_candidate(candidate)

        if candidate.is_feasible:
            validated_candidates.append(candidate)

    scored = [
        (
            candidate,
            calculate_score(candidate, weights=weights),
        )
        for candidate in validated_candidates
    ]

    scored.sort(
        key=lambda item: (-item[1], item[0].evidence_id)
    )

    results: list[RankedEvidence] = []

    for index, (candidate, score) in enumerate(scored, start=1):
        explanation, strengths, tradeoffs = _build_explanation(
            candidate,
            score,
        )

        results.append(
            RankedEvidence(
                evidence_id=candidate.evidence_id,
                candidate_name=candidate.candidate_name,
                score=score,
                rank=index,
                decision_value=candidate.decision_value,
                reliability=candidate.reliability,
                feasibility=candidate.feasibility,
                cost=candidate.cost,
                time=candidate.time,
                explanation=explanation,
                strengths=strengths,
                tradeoffs=tradeoffs,
                selected=index == 1,
            )
        )

    return results