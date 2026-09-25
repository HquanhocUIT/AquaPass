"""Read-only readiness check for the existing Supabase demo tables and rows."""

import sys
from pathlib import Path
from uuid import UUID

from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.exc import SQLAlchemyError


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.db.tables import (  # noqa: E402
    actors,
    audit_events,
    decision_versions,
    decisions,
    evidence,
    evidence_gaps,
    evidence_requests,
    hypotheses,
    incidents,
    request_status_events,
)


DEMO_INCIDENT_ID = "8f03fdce-cc4e-4fc1-a90b-15b2122e68b8"
DEMO_DECISION_ID = "00000000-0000-4000-8000-000000000201"
DEMO_ACTOR_ID = "00000000-0000-4000-8000-000000000401"
REQUIRED_TABLES = (
    incidents,
    evidence,
    decisions,
    decision_versions,
    hypotheses,
    evidence_gaps,
    actors,
    evidence_requests,
    request_status_events,
    audit_events,
)


def check_connection(connection) -> dict[str, int]:
    """Inspect schema and count only demo rows; never create or modify data."""
    inspector = inspect(connection)
    missing = [
        table.name
        for table in REQUIRED_TABLES
        if not inspector.has_table(table.name, schema="public")
    ]
    if missing:
        raise RuntimeError(f"Missing public tables: {', '.join(missing)}")

    incident_id = UUID(DEMO_INCIDENT_ID)
    decision_id = UUID(DEMO_DECISION_ID)
    counts = {
        "incident": connection.scalar(
            select(func.count()).select_from(incidents).where(incidents.c.id == incident_id)
        ),
        "evidence": connection.scalar(
            select(func.count()).select_from(evidence).where(evidence.c.incident_id == incident_id)
        ),
        "decision": connection.scalar(
            select(func.count()).select_from(decisions).where(decisions.c.incident_id == incident_id)
        ),
        "version": connection.scalar(
            select(func.count()).select_from(decision_versions)
            .where(decision_versions.c.decision_id == decision_id)
        ),
        "hypothesis": connection.scalar(
            select(func.count()).select_from(hypotheses)
            .where(hypotheses.c.incident_id == incident_id)
        ),
        "gap": connection.scalar(
            select(func.count()).select_from(evidence_gaps)
            .where(evidence_gaps.c.decision_id == decision_id)
        ),
        "actor": connection.scalar(
            select(func.count()).select_from(actors)
            .where(actors.c.id == UUID(DEMO_ACTOR_ID))
        ),
    }
    if (
        counts["incident"] != 1
        or counts["evidence"] < 3
        or counts["decision"] < 1
        or counts["version"] < 1
        or counts["hypothesis"] < 2
        or counts["gap"] < 1
        or counts["actor"] != 1
    ):
        raise RuntimeError(f"Demo seed incomplete: {counts}")
    return counts


def main() -> None:
    db_engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        with db_engine.connect() as connection:
            counts = check_connection(connection)
    except (SQLAlchemyError, RuntimeError) as exc:
        raise SystemExit(f"Demo readiness failed: {exc}") from exc
    finally:
        db_engine.dispose()
    print(f"Demo ready (read-only check): {counts}")


if __name__ == "__main__":
    main()
