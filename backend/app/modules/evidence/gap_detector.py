from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class GapPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class EvidenceGap:
    gap_id: str
    incident_id: str
    decision_id: str
    evidence_id: str
    evidence_type: str
    target_hypothesis: str
    why_missing: str
    decision_impact: str
    priority: GapPriority


@dataclass(frozen=True)
class EvidenceGraphRecord:
    graph_id: str
    incident_id: str
    decision_id: str
    source_node: str
    source_type: str
    relationship: str
    target_node: str
    target_type: str
    confidence: float
    state: str
    rationale: str


def _validate_graph_record(record: EvidenceGraphRecord) -> None:
    if not record.graph_id:
        raise ValueError("graph_id must not be empty")

    if not record.incident_id:
        raise ValueError("incident_id must not be empty")

    if not record.decision_id:
        raise ValueError("decision_id must not be empty")

    if not record.source_node:
        raise ValueError("source_node must not be empty")

    if not record.target_node:
        raise ValueError("target_node must not be empty")

    if not 0.0 <= record.confidence <= 1.0:
        raise ValueError(
            f"confidence must be between 0.0 and 1.0: {record.graph_id}"
        )


def _priority_from_confidence(confidence: float) -> GapPriority:
    if confidence >= 0.75:
        return GapPriority.HIGH

    if confidence >= 0.50:
        return GapPriority.MEDIUM

    return GapPriority.LOW


def detect_evidence_gaps(
    graph_records: Iterable[EvidenceGraphRecord],
) -> list[EvidenceGap]:
    """
    Detect explicit, decision-relevant evidence gaps.

    A graph record becomes an EvidenceGap only when:
    1. its relationship is explicitly "missing_for";
    2. its target is a hypothesis or decision;
    3. the source represents the missing evidence.

    This function does not infer new evidence requirements.
    It only materializes gaps already represented in the evidence graph.

    Results are deterministic and ordered by gap_id.
    """

    gaps: list[EvidenceGap] = []

    for record in graph_records:
        _validate_graph_record(record)

        if record.relationship != "missing_for":
            continue

        if record.source_type != "evidence":
            continue

        if record.target_type not in {"hypothesis", "decision"}:
            continue

        if record.state != "missing":
            continue

        if record.target_type == "hypothesis":
            target_hypothesis = record.target_node
            decision_impact = (
                "Collecting this evidence may change the assessment "
                "of the linked hypothesis and therefore inform the "
                "pending decision."
            )
        else:
            target_hypothesis = "decision-level evidence requirement"
            decision_impact = (
                "Collecting this evidence may provide information "
                "needed for the pending decision."
            )

        gaps.append(
            EvidenceGap(
                gap_id=f"GAP-{record.graph_id}",
                incident_id=record.incident_id,
                decision_id=record.decision_id,
                evidence_id=record.source_node,
                evidence_type="evidence",
                target_hypothesis=target_hypothesis,
                why_missing=(
                    record.rationale
                    or (
                        "The evidence graph explicitly marks this "
                        "evidence as missing for the decision."
                    )
                ),
                decision_impact=decision_impact,
                priority=_priority_from_confidence(record.confidence),
            )
        )

    return sorted(gaps, key=lambda gap: gap.gap_id)