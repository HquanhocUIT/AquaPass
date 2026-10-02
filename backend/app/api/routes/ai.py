from __future__ import annotations

from fastapi import APIRouter

from app.modules.ai.grounded_insights import (
    explain_ranking,
    suggest_evidence_gaps,
)
from app.modules.evidence.gap_detector import EvidenceGraphRecord
from app.modules.ranking.ranking_engine import EvidenceCandidate
from app.schemas.ai import (
    AiEvidenceGapsRequest,
    AiEvidenceGapsResponse,
    AiEvidenceGapResponse,
    AiRankingExplanationItem,
    AiRankingExplanationRequest,
    AiRankingExplanationResponse,
)


router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/evidence-gaps", response_model=AiEvidenceGapsResponse)
def suggest_evidence_gaps_endpoint(
    request: AiEvidenceGapsRequest,
) -> AiEvidenceGapsResponse:
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
    result = suggest_evidence_gaps(records)

    return AiEvidenceGapsResponse(
        provider=result.metadata.provider,
        model=result.metadata.model,
        fallback_reason=result.metadata.fallback_reason,
        gaps=[
            AiEvidenceGapResponse(
                gap_id=gap.gap_id,
                incident_id=gap.incident_id,
                decision_id=gap.decision_id,
                evidence_id=gap.evidence_id,
                evidence_type=gap.evidence_type,
                target_hypothesis=gap.target_hypothesis,
                reason=gap.why_missing,
                decision_impact=gap.decision_impact,
                priority=gap.priority.value,
            )
            for gap in result.gaps
        ],
    )


@router.post(
    "/ranking-explanations",
    response_model=AiRankingExplanationResponse,
)
def explain_ranking_endpoint(
    request: AiRankingExplanationRequest,
) -> AiRankingExplanationResponse:
    candidates = [
        EvidenceCandidate(
            evidence_id=item.evidence_id,
            candidate_name=item.candidate_name,
            decision_value=item.decision_value,
            reliability=item.reliability,
            feasibility=item.feasibility,
            cost=item.cost,
            time=item.time,
            is_feasible=item.is_feasible,
            infeasibility_reason=item.infeasibility_reason,
        )
        for item in request.candidates
    ]
    result = explain_ranking(candidates)
    ranked_by_id = {item.evidence_id: item for item in result.ranked}

    return AiRankingExplanationResponse(
        provider=result.metadata.provider,
        model=result.metadata.model,
        fallback_reason=result.metadata.fallback_reason,
        results=[
            AiRankingExplanationItem(
                evidence_id=explanation.evidence_id,
                candidate_name=ranked_by_id[explanation.evidence_id].candidate_name,
                rank=ranked_by_id[explanation.evidence_id].rank,
                score=ranked_by_id[explanation.evidence_id].score,
                selected=ranked_by_id[explanation.evidence_id].selected,
                explanation=explanation.explanation,
                strengths=list(explanation.strengths),
                tradeoffs=list(explanation.tradeoffs),
            )
            for explanation in result.explanations
        ],
    )
