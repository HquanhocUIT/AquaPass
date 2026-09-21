"""Create one incident using the existing Supabase schema."""

from uuid import uuid4

from fastapi import APIRouter, Depends, status
from sqlalchemy import insert
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.tables import incidents
from app.schemas.incident_create import IncidentCreateRequest
from app.schemas.incident_read import IncidentResponse


router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
def create_incident(payload: IncidentCreateRequest, db: Session = Depends(get_db)) -> dict:
    """Store a new incident; server-managed fields are not accepted from clients."""
    statement = (
        insert(incidents)
        .values(
            id=uuid4(),
            **payload.model_dump(),
            status="OPEN",
        )
        .returning(*incidents.c)
    )
    created = dict(db.execute(statement).mappings().one())
    db.commit()
    return created
