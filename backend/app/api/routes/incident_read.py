"""Read the incident workspace from the existing Supabase PostgreSQL schema."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.tables import decisions, evidence, incidents
from app.schemas.incident_read import IncidentDetailResponse


router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("/{incident_id}", response_model=IncidentDetailResponse)
def get_incident(incident_id: UUID, db: Session = Depends(get_db)) -> dict:
    """Return one incident with its evidence and pending decisions, or 404."""
    incident = db.execute(
        select(incidents).where(incidents.c.id == incident_id)
    ).mappings().first()

    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    evidence_rows = db.execute(
        select(evidence)
        .where(evidence.c.incident_id == incident_id)
        .order_by(evidence.c.observed_at, evidence.c.id)
    ).mappings().all()

    decision_rows = db.execute(
        select(
            decisions.c.id,
            decisions.c.incident_id,
            decisions.c.question,
            decisions.c.deadline,
            decisions.c.status,
            decisions.c.current_version,
        )
        .where(decisions.c.incident_id == incident_id)
        .order_by(decisions.c.created_at, decisions.c.id)
    ).mappings().all()

    return {
        **dict(incident),
        "evidence": [dict(row) for row in evidence_rows],
        "decisions": [dict(row) for row in decision_rows],
    }
