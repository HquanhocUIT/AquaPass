from __future__ import annotations

from fastapi import APIRouter

from app.api.routes.evidence import detect_gaps
from app.api.routes.ranking import rank_evidence_candidates
from app.schemas.evidence import DetectEvidenceGapsRequest
from app.schemas.intelligence import RankEvidenceRequest
from app.schemas.workflow import (
    IntelligenceOverviewRequest,
    IntelligenceOverviewResponse,
    IntelligenceStateResponse,
)


router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])


@router.post("/overview", response_model=IntelligenceOverviewResponse)
def intelligence_overview(payload: IntelligenceOverviewRequest) -> IntelligenceOverviewResponse:
    """Return graph, state, gap and ranking data in one frontend call.

    Sang's deterministic graph and ranking modules remain the source of truth;
    this route only composes their existing contracts for the decision workspace.
    """
    gap_response = detect_gaps(
        DetectEvidenceGapsRequest(records=payload.records)
    )
    ranking_response = rank_evidence_candidates(
        RankEvidenceRequest(candidates=payload.candidates)
    )

    states_by_id: dict[str, IntelligenceStateResponse] = {}
    for record in payload.records:
        states_by_id[record.source_node] = IntelligenceStateResponse(
            evidence_id=record.source_node,
            state=record.state,
            reason=record.rationale,
        )

    return IntelligenceOverviewResponse(
        graph=[record.model_dump() for record in payload.records],
        states=list(states_by_id.values()),
        gaps=[gap.model_dump() for gap in gap_response.gaps],
        ranking=ranking_response.model_dump(),
    )
