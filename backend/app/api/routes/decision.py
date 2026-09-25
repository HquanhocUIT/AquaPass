from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.modules.decision.decision_comparison import (
    compare_decision_versions,
)
from app.modules.decision.decision_store import (
    DecisionStore,
)
from app.modules.decision.demo_loader import (
    load_demo_decision,
)
from app.schemas.decision import (
    DecisionComparisonResponse,
    DecisionVersionResponse,
)


router = APIRouter(
    prefix="/api/decisions",
    tags=["decisions"],
)


decision_store = DecisionStore()

load_demo_decision(
    decision_store,
    "data/demo/decision_seed.json",
)


@router.get(
    "/{decision_id}",
    response_model=DecisionVersionResponse,
)
def get_latest_decision(
    decision_id: str,
) -> DecisionVersionResponse:

    try:
        decision = decision_store.get_latest(
            decision_id
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Decision not found",
        )

    return DecisionVersionResponse(
        decision_id=decision.decision_id,
        version=decision.version,
        incident_id=decision.incident_id,
        uncertainty=decision.uncertainty,
        uncertainty_level=decision.uncertainty_level,
        hypothesis_summary=decision.hypothesis_summary,
        triggering_evidence_id=(
            decision.triggering_evidence_id
        ),
    )


@router.get(
    "/{decision_id}/comparison",
    response_model=DecisionComparisonResponse,
)
def compare_latest_decisions(
    decision_id: str,
) -> DecisionComparisonResponse:

    try:
        versions = decision_store.get_versions(
            decision_id
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Decision not found",
        )

    if len(versions) < 2:
        raise HTTPException(
            status_code=404,
            detail="At least two decision versions are required",
        )

    comparison = compare_decision_versions(
        versions[-2],
        versions[-1],
    )

    return DecisionComparisonResponse(
        decision_id=comparison.decision_id,
        from_version=comparison.from_version,
        to_version=comparison.to_version,
        triggering_evidence_id=(
            comparison.triggering_evidence_id
        ),
        uncertainty_before=(
            comparison.uncertainty_before
        ),
        uncertainty_after=(
            comparison.uncertainty_after
        ),
        uncertainty_change=(
            comparison.uncertainty_change
        ),
        hypothesis_changed=(
            comparison.hypothesis_changed
        ),
    )