"""Attach newly submitted prototype evidence to an existing incident."""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.tables import evidence, incidents
from app.schemas.evidence_create import EvidenceCreateRequest
from app.schemas.incident_read import EvidenceResponse


router = APIRouter(prefix="/incidents", tags=["evidence"])


@router.post(
    "/{incident_id}/evidence",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_evidence(
    incident_id: UUID,
    payload: EvidenceCreateRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Store one simulated observation under the incident ID from the URL."""
    exists = db.scalar(select(incidents.c.id).where(incidents.c.id == incident_id))
    if exists is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    statement = (
        insert(evidence)
        .values(
            id=uuid4(),
            incident_id=incident_id,
            **payload.model_dump(exclude={"provenance"}),
            state="KNOWN",
            reliability_score=0.5,
            provenance={**payload.provenance, "simulated": True},
            is_simulated=True,
        )
        .returning(*evidence.c)
    )
    created = dict(db.execute(statement).mappings().one())
    db.commit()
    return created
