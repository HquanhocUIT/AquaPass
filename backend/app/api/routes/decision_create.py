"""Create a pending decision and its first immutable evidence snapshot."""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.tables import decision_versions, decisions, evidence, incidents
from app.schemas.decision_create import DecisionCreateRequest, DecisionCreateResponse


router = APIRouter(prefix="/incidents", tags=["decisions"])


@router.post(
    "/{incident_id}/decisions",
    response_model=DecisionCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_decision(
    incident_id: UUID,
    payload: DecisionCreateRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Commit a decision and version 1 together, or save neither one."""
    try:
        exists = db.scalar(select(incidents.c.id).where(incidents.c.id == incident_id))
        if exists is None:
            raise HTTPException(status_code=404, detail="Incident not found")

        evidence_rows = db.execute(
            select(evidence.c.id, evidence.c.code)
            .where(evidence.c.incident_id == incident_id)
            .order_by(evidence.c.observed_at, evidence.c.id)
        ).all()
        snapshot = {
            "evidence_ids": [str(row.id) for row in evidence_rows],
            "evidence_codes": [row.code for row in evidence_rows],
        }

        decision_id = uuid4()
        created_decision = dict(
            db.execute(
                insert(decisions)
                .values(
                    id=decision_id,
                    incident_id=incident_id,
                    question=payload.question,
                    deadline=payload.deadline,
                    status="PENDING",
                    current_version=1,
                )
                .returning(*decisions.c)
            ).mappings().one()
        )
        created_version = dict(
            db.execute(
                insert(decision_versions)
                .values(
                    id=uuid4(),
                    decision_id=decision_id,
                    version_number=1,
                    summary="Awaiting evidence review.",
                    uncertainty_level="HIGH",
                    evidence_snapshot=snapshot,
                    approval_status="PENDING",
                    created_by="system",
                )
                .returning(*decision_versions.c)
            ).mappings().one()
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {**created_decision, "version": created_version}
