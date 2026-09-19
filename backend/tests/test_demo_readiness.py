"""The demo preflight is read-only and checks the entire Phase 1 seed shape."""

from datetime import datetime, timezone
from uuid import UUID

import pytest
from sqlalchemy import insert
from sqlalchemy.orm import Session, sessionmaker

from app.db.tables import (
    actors, decision_versions, decisions, evidence, evidence_gaps,
    hypotheses, incidents,
)
from scripts.check_demo import check_connection
from tests.test_decision_create import test_database


INCIDENT_ID = UUID("8f03fdce-cc4e-4fc1-a90b-15b2122e68b8")
DECISION_ID = UUID("00000000-0000-4000-8000-000000000201")


def test_demo_preflight_detects_missing_seed(test_database: sessionmaker[Session]) -> None:
    with test_database.kw["bind"].connect() as connection:
        with pytest.raises(RuntimeError, match="Demo seed incomplete"):
            check_connection(connection)


def test_demo_preflight_accepts_seed_shape(test_database: sessionmaker[Session]) -> None:
    when = datetime(2026, 9, 19, tzinfo=timezone.utc)
    with test_database.begin() as db:
        db.execute(insert(incidents).values(
            id=INCIDENT_ID, title="Simulated incident", description="Simulated",
            incident_type="FISH_MORTALITY", location_name="Demo lake",
            severity="HIGH", status="OPEN", occurred_at=when,
        ))
        for number in (101, 102, 103):
            db.execute(insert(evidence).values(
                id=UUID(f"00000000-0000-4000-8000-{number:012d}"),
                incident_id=INCIDENT_ID, code=f"EVIDENCE_{number}",
                evidence_type="FIELD_REPORT", state="KNOWN", value_text="Simulated",
                source="Demo", observed_at=when, reliability_score=0.5,
                provenance={"simulated": True}, is_simulated=True,
            ))
        db.execute(insert(decisions).values(
            id=DECISION_ID, incident_id=INCIDENT_ID, question="Investigate?",
            deadline=when, status="PENDING", current_version=1,
        ))
        db.execute(insert(decision_versions).values(
            id=UUID("00000000-0000-4000-8000-000000000301"),
            decision_id=DECISION_ID, version_number=1, summary="Pending",
            uncertainty_level="HIGH", evidence_snapshot={"evidence_ids": []},
            approval_status="PENDING", created_by="demo-seed",
        ))
        for number in (601, 602):
            db.execute(insert(hypotheses).values(
                id=UUID(f"00000000-0000-4000-8000-{number:012d}"),
                incident_id=INCIDENT_ID, code=f"H{number}", title="Hypothesis",
                description="Simulated",
            ))
        db.execute(insert(actors).values(
            id=UUID("00000000-0000-4000-8000-000000000401"),
            code="DEMO_FIELD_TEAM", name="Demo team", actor_type="FIELD_TEAM",
            capabilities=["FIELD_DISSOLVED_OXYGEN"],
        ))
        db.execute(insert(evidence_gaps).values(
            id=UUID("00000000-0000-4000-8000-000000000501"),
            incident_id=INCIDENT_ID, decision_id=DECISION_ID,
            code="FIELD_DISSOLVED_OXYGEN", description="Missing field reading",
        ))

    with test_database.kw["bind"].connect() as connection:
        assert check_connection(connection) == {
            "incident": 1, "evidence": 3, "decision": 1,
            "version": 1, "hypothesis": 2, "gap": 1, "actor": 1,
        }
