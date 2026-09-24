from __future__ import annotations

from fastapi import APIRouter

from app.modules.ranking.ranking_engine import (
    EvidenceCandidate,
    rank_evidence,
)
from app.schemas.intelligence import (
    RankEvidenceRequest,
    RankEvidenceResponse,
    RankedEvidenceResponse,
)


router = APIRouter(
    prefix="/api/ranking",
    tags=["ranking"],
)


@router.post(
    "/evidence",
    response_model=RankEvidenceResponse,
)
def rank_evidence_candidates(
    request: RankEvidenceRequest,
) -> RankEvidenceResponse:
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

    ranked = rank_evidence(candidates)

    return RankEvidenceResponse(
        results=[
            RankedEvidenceResponse(
                evidence_id=item.evidence_id,
                candidate_name=item.candidate_name,
                score=item.score,
                rank=item.rank,
                decision_value=item.decision_value,
                reliability=item.reliability,
                feasibility=item.feasibility,
                cost=item.cost,
                time=item.time,
                explanation=item.explanation,
                strengths=list(item.strengths),
                tradeoffs=list(item.tradeoffs),
                selected=item.selected,
            )
            for item in ranked
        ]
    )