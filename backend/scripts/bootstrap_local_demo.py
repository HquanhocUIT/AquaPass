"""Create an isolated local SQLite schema and the simulated AquaPass demo rows."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import insert, select, update

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.db.session import SessionLocal, engine
from app.db.tables import (
    actors,
    decision_versions,
    decisions,
    evidence,
    evidence_gaps,
    evidence_requests,
    hypotheses,
    incidents,
    metadata,
)


INCIDENT_ID = UUID("8f03fdce-cc4e-4fc1-a90b-15b2122e68b8")
DECISION_ID = UUID("00000000-0000-4000-8000-000000000201")
EVIDENCE_IDS = {
    "FISH_MORTALITY_REPORT": UUID("00000000-0000-4000-8000-000000000101"),
    "DISSOLVED_OXYGEN_SENSOR": UUID("00000000-0000-4000-8000-000000000102"),
    "HEAVY_RAINFALL": UUID("00000000-0000-4000-8000-000000000103"),
}
VERSION_ID = UUID("00000000-0000-4000-8000-000000000301")
ACTOR_ID = UUID("00000000-0000-4000-8000-000000000401")
GAP_ID = UUID("00000000-0000-4000-8000-000000000501")
HYPOTHESIS_IDS = {
    "H1": UUID("00000000-0000-4000-8000-000000000601"),
    "H2": UUID("00000000-0000-4000-8000-000000000602"),
}


def insert_if_missing(db, table, row: dict) -> None:
    if db.scalar(select(table.c.id).where(table.c.id == row["id"])) is None:
        db.execute(insert(table).values(**row))


def main() -> None:
    if not settings.database_url.startswith("sqlite"):
        raise SystemExit(
            "Local bootstrap only supports SQLite. It will not write to Supabase."
        )

    metadata.create_all(engine)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    evidence_rows = [
        {
            "id": EVIDENCE_IDS["FISH_MORTALITY_REPORT"],
            "incident_id": INCIDENT_ID,
            "code": "FISH_MORTALITY_REPORT",
            "evidence_type": "FIELD_REPORT",
            "state": "KNOWN",
            "value_text": "Multiple dead fish observed near the shoreline",
            "source": "Simulated citizen report",
            "observed_at": now - timedelta(minutes=55),
            "reliability_score": 0.65,
            "provenance": {"simulated": True, "reporter_type": "citizen"},
            "is_simulated": True,
        },
        {
            "id": EVIDENCE_IDS["DISSOLVED_OXYGEN_SENSOR"],
            "incident_id": INCIDENT_ID,
            "code": "DISSOLVED_OXYGEN_SENSOR",
            "evidence_type": "SENSOR_READING",
            "state": "LOW_CONFIDENCE",
            "value_numeric": 3.8,
            "unit": "mg/L",
            "source": "Simulated fixed sensor",
            "observed_at": now - timedelta(hours=3),
            "reliability_score": 0.55,
            "provenance": {"simulated": True, "quality_note": "requires field verification"},
            "is_simulated": True,
        },
        {
            "id": EVIDENCE_IDS["HEAVY_RAINFALL"],
            "incident_id": INCIDENT_ID,
            "code": "HEAVY_RAINFALL",
            "evidence_type": "WEATHER_OBSERVATION",
            "state": "KNOWN",
            "value_numeric": 42.0,
            "unit": "mm/24h",
            "source": "Simulated weather service",
            "observed_at": now - timedelta(hours=6),
            "reliability_score": 0.90,
            "provenance": {"simulated": True},
            "is_simulated": True,
        },
    ]

    with SessionLocal() as db:
        insert_if_missing(
            db,
            incidents,
            {
                "id": INCIDENT_ID,
                "title": "Fish mortality at urban freshwater site",
                "description": "SIMULATED DATA: Multiple dead fish were reported after heavy rainfall.",
                "incident_type": "FISH_MORTALITY",
                "location_name": "Demo Urban Lake - Site A",
                "latitude": 10.7769,
                "longitude": 106.7009,
                "severity": "HIGH",
                "status": "OPEN",
                "occurred_at": now - timedelta(hours=1),
            },
        )
        for row in evidence_rows:
            insert_if_missing(db, evidence, row)

        insert_if_missing(
            db,
            decisions,
            {
                "id": DECISION_ID,
                "incident_id": INCIDENT_ID,
                "question": "Should the authority escalate the field investigation?",
                "deadline": now + timedelta(hours=48),
                "status": "PENDING",
                "current_version": 1,
            },
        )
        existing_decision = db.execute(
            select(decisions).where(decisions.c.id == DECISION_ID)
        ).mappings().one()
        has_request = db.scalar(
            select(evidence_requests.c.id)
            .where(evidence_requests.c.decision_id == DECISION_ID)
            .limit(1)
        )
        if (
            existing_decision["status"] == "PENDING"
            and int(existing_decision["current_version"]) == 1
            and has_request is None
        ):
            db.execute(
                update(decisions)
                .where(decisions.c.id == DECISION_ID)
                .values(deadline=now + timedelta(hours=48))
            )
        insert_if_missing(
            db,
            decision_versions,
            {
                "id": VERSION_ID,
                "decision_id": DECISION_ID,
                "version_number": 1,
                "summary": "Current evidence is insufficient; field verification is pending.",
                "uncertainty_level": "HIGH",
                "evidence_snapshot": {
                    "evidence_ids": [str(row["id"]) for row in evidence_rows],
                    "evidence_codes": [str(row["code"]) for row in evidence_rows],
                },
                "approval_status": "PENDING",
                "created_by": "local-demo-seed",
            },
        )
        for code, title, description, score in (
            (
                "H1",
                "Low dissolved oxygen",
                "SIMULATED: runoff may have contributed to oxygen depletion.",
                0.6,
            ),
            (
                "H2",
                "Toxic discharge",
                "SIMULATED: an unverified discharge is another possible explanation.",
                0.4,
            ),
        ):
            insert_if_missing(
                db,
                hypotheses,
                {
                    "id": HYPOTHESIS_IDS[code],
                    "incident_id": INCIDENT_ID,
                    "code": code,
                    "title": title,
                    "description": description,
                    "status": "ACTIVE",
                    "support_score": score,
                },
            )
        insert_if_missing(
            db,
            actors,
            {
                "id": ACTOR_ID,
                "code": "DEMO_FIELD_TEAM",
                "name": "Simulated field team",
                "actor_type": "FIELD_TEAM",
                "capabilities": ["FIELD_DISSOLVED_OXYGEN"],
                "location_name": "Demo Urban Lake - Site A",
                "available": True,
                "capacity": 1,
                "turnaround_minutes": 20,
            },
        )
        insert_if_missing(
            db,
            evidence_gaps,
            {
                "id": GAP_ID,
                "incident_id": INCIDENT_ID,
                "decision_id": DECISION_ID,
                "code": "FIELD_DISSOLVED_OXYGEN",
                "description": "A recent field dissolved-oxygen measurement is missing.",
                "criticality": "HIGH",
                "status": "OPEN",
                "rationale": "The earlier sensor reading has low confidence and requires verification.",
            },
        )
        db.commit()

    print("Local AquaPass demo database is ready.")
    print(f"Incident: {INCIDENT_ID}")
    print("All seeded observations and catalog values are simulated.")


if __name__ == "__main__":
    main()
