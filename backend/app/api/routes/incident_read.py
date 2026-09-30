"""Read the incident workspace from the existing Supabase PostgreSQL schema."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.tables import decisions, evidence, incidents
from app.schemas.incident_read import IncidentDetailResponse, IncidentListItemResponse


router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentListItemResponse])
def list_incidents(db: Session = Depends(get_db)) -> list[dict]:
    """Return the most recently updated incidents for the workspace index."""
    evidence_count = (
        select(func.count(evidence.c.id))
        .where(evidence.c.incident_id == incidents.c.id)
        .correlate(incidents)
        .scalar_subquery()
    )
    pending_count = (
        select(func.count(decisions.c.id))
        .where(
            decisions.c.incident_id == incidents.c.id,
            decisions.c.status == "PENDING",
        )
        .correlate(incidents)
        .scalar_subquery()
    )
    rows = db.execute(
        select(
            *incidents.c,
            evidence_count.label("evidence_count"),
            pending_count.label("pending_decision_count"),
        )
        .order_by(incidents.c.updated_at.desc(), incidents.c.id)
        .limit(100)
    ).mappings().all()
    return [dict(row) for row in rows]


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
