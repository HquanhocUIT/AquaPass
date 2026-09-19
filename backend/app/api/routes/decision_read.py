"""Read a decision and its saved version history."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.tables import decision_versions, decisions
from app.schemas.decision_create import DecisionDetailResponse


router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.get("/{decision_id}", response_model=DecisionDetailResponse)
def get_decision(decision_id: UUID, db: Session = Depends(get_db)) -> dict:
    """Return the decision and every version in version-number order, or 404."""
    decision = db.execute(
        select(decisions).where(decisions.c.id == decision_id)
    ).mappings().first()
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")

    versions = db.execute(
        select(decision_versions)
        .where(decision_versions.c.decision_id == decision_id)
        .order_by(decision_versions.c.version_number)
    ).mappings().all()

    return {
        **dict(decision),
        "versions": [dict(version) for version in versions],
    }
