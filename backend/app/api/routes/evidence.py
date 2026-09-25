from __future__ import annotations

from fastapi import APIRouter

from app.modules.evidence.gap_detector import (
    EvidenceGraphRecord,
    detect_evidence_gaps,
)
from app.schemas.evidence import (
    DetectEvidenceGapsRequest,
    EvidenceGapResponse,
    DetectEvidenceGapsResponse,
)


router = APIRouter(
    prefix="/api/evidence",
    tags=["evidence"],
)


@router.post(
    "/gaps",
    response_model=DetectEvidenceGapsResponse,
)
def detect_gaps(
    request: DetectEvidenceGapsRequest,
) -> DetectEvidenceGapsResponse:

    records = [
        EvidenceGraphRecord(
            graph_id=item.graph_id,
            incident_id=item.incident_id,
            decision_id=item.decision_id,
            source_node=item.source_node,
            source_type=item.source_type,
            relationship=item.relationship,
            target_node=item.target_node,
            target_type=item.target_type,
            confidence=item.confidence,
            state=item.state,
            rationale=item.rationale,
        )
        for item in request.records
    ]

    gaps = detect_evidence_gaps(records)

    return DetectEvidenceGapsResponse(
        gaps=[
            EvidenceGapResponse(
                incident_id=gap.incident_id,
                decision_id=gap.decision_id,
                evidence_id=gap.evidence_id,
                priority=gap.priority.value,
                reason=gap.why_missing,
            )
            for gap in gaps
        ]
    )