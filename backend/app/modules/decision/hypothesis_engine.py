from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


VALID_STATUSES = {
    "weaker",
    "unchanged",
    "stronger",
}

VALID_DIRECTIONS = {
    "supports",
    "corroborates",
    "contradicts",
}


@dataclass(frozen=True)
class Hypothesis:
    hypothesis_id: str
    name: str
    status: str = "unchanged"


@dataclass(frozen=True)
class EvidenceImpact:
    evidence_id: str
    hypothesis_id: str
    direction: str
    rationale: str


@dataclass(frozen=True)
class UpdatedHypothesis:
    hypothesis_id: str
    name: str
    previous_status: str
    new_status: str
    triggering_evidence_id: str
    rationale: str


def _validate_hypothesis(hypothesis: Hypothesis) -> None:
    if not hypothesis.hypothesis_id:
        raise ValueError("hypothesis_id must not be empty")

    if not hypothesis.name:
        raise ValueError("hypothesis name must not be empty")

    if hypothesis.status not in VALID_STATUSES:
        raise ValueError(
            f"invalid hypothesis status: {hypothesis.status}"
        )


def _validate_impact(impact: EvidenceImpact) -> None:
    if not impact.evidence_id:
        raise ValueError("evidence_id must not be empty")

    if not impact.hypothesis_id:
        raise ValueError("hypothesis_id must not be empty")

    if impact.direction not in VALID_DIRECTIONS:
        raise ValueError(
            f"invalid evidence direction: {impact.direction}"
        )

    if not impact.rationale:
        raise ValueError("rationale must not be empty")


def _apply_direction(
    current_status: str,
    direction: str,
) -> str:
    if direction in {"supports", "corroborates"}:
        return "stronger"

    if direction == "contradicts":
        return "weaker"

    return current_status


def update_hypotheses(
    hypotheses: Iterable[Hypothesis],
    impacts: Iterable[EvidenceImpact],
) -> list[UpdatedHypothesis]:
    """
    Update hypothesis states from newly observed evidence.

    The update is deterministic and evidence-traceable.

    Supports/corroborates -> stronger
    Contradicts -> weaker

    Hypotheses without a related evidence impact remain unchanged.

    If multiple impacts target the same hypothesis, impacts are processed
    deterministically by evidence_id.
    """

    hypothesis_list = list(hypotheses)
    impact_list = list(impacts)

    for hypothesis in hypothesis_list:
        _validate_hypothesis(hypothesis)

    for impact in impact_list:
        _validate_impact(impact)

    hypothesis_map = {
        hypothesis.hypothesis_id: hypothesis
        for hypothesis in hypothesis_list
    }

    unknown_hypothesis_ids = {
        impact.hypothesis_id
        for impact in impact_list
        if impact.hypothesis_id not in hypothesis_map
    }

    if unknown_hypothesis_ids:
        unknown = ", ".join(sorted(unknown_hypothesis_ids))
        raise ValueError(
            f"impact references unknown hypothesis_id: {unknown}"
        )

    grouped_impacts: dict[str, list[EvidenceImpact]] = {}

    for impact in impact_list:
        grouped_impacts.setdefault(
            impact.hypothesis_id,
            [],
        ).append(impact)

    results: list[UpdatedHypothesis] = []

    for hypothesis in sorted(
        hypothesis_list,
        key=lambda item: item.hypothesis_id,
    ):
        related_impacts = sorted(
            grouped_impacts.get(
                hypothesis.hypothesis_id,
                [],
            ),
            key=lambda item: item.evidence_id,
        )

        if not related_impacts:
            results.append(
                UpdatedHypothesis(
                    hypothesis_id=hypothesis.hypothesis_id,
                    name=hypothesis.name,
                    previous_status=hypothesis.status,
                    new_status=hypothesis.status,
                    triggering_evidence_id="",
                    rationale="No new evidence linked to this hypothesis.",
                )
            )
            continue

        current_status = hypothesis.status

        for impact in related_impacts:
            current_status = _apply_direction(
                current_status,
                impact.direction,
            )

        primary_impact = related_impacts[-1]

        results.append(
            UpdatedHypothesis(
                hypothesis_id=hypothesis.hypothesis_id,
                name=hypothesis.name,
                previous_status=hypothesis.status,
                new_status=current_status,
                triggering_evidence_id=primary_impact.evidence_id,
                rationale=primary_impact.rationale,
            )
        )

    return results