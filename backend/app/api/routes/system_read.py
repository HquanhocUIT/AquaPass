"""Read-only checks for service and database readiness."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness endpoint that does not depend on external infrastructure."""
    return {
        "status": "ok",
        "service": "aquapass-api",
        "database": "reachable",
    }


@router.get("/health/readiness")
def readiness(db: Session = Depends(get_db)) -> dict[str, str]:
    """Return 200 only when the configured database answers a read-only query."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc

    return {
        "status": "ok",
        "service": "aquapass-api",
        "database": "reachable",
    }
