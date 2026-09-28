from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.db.tables import audit_events


def append_audit_event(
    db: Session,
    *,
    incident_id: UUID | None,
    entity_type: str,
    entity_id: UUID,
    event_type: str,
    actor_name: str,
    payload: dict,
) -> dict:
    """Append one immutable workflow event to the audit table."""
    created_at = datetime.now(timezone.utc).replace(tzinfo=None)
    previous_created_at = db.execute(
        select(audit_events.c.created_at)
        .where(audit_events.c.incident_id == incident_id)
        .order_by(audit_events.c.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if previous_created_at is not None and created_at <= previous_created_at:
        created_at = previous_created_at + timedelta(microseconds=1)

    row = db.execute(
        insert(audit_events)
        .values(
            id=uuid4(),
            incident_id=incident_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            actor_name=actor_name,
            payload=payload,
            # Use naive UTC here so SQLite and PostgreSQL sort this value in
            # the same format as the migration's timestamptz default.
            created_at=created_at,
        )
        .returning(*audit_events.c)
    ).mappings().one()
    return dict(row)


def list_audit_events(
    db: Session,
    *,
    incident_id: UUID,
) -> list[dict]:
    rows = db.execute(
        select(audit_events)
        .where(audit_events.c.incident_id == incident_id)
        .order_by(audit_events.c.created_at, audit_events.c.id)
    ).mappings().all()
    return [dict(row) for row in rows]
