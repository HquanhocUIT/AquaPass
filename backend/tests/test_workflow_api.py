"""HTTP tests for Quân's closed-loop workflow endpoints."""

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.db.tables import metadata
from app.main import app
from tests.test_incident_create import valid_payload as valid_incident_payload


@pytest.fixture
def client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def attach_public_schema(dbapi_connection, connection_record) -> None:
        dbapi_connection.execute("ATTACH DATABASE ':memory:' AS public")

    metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    def override_get_db() -> Iterator[Session]:
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def _create_demo_decision(client: TestClient) -> tuple[str, str]:
    incident = client.post("/incidents", json=valid_incident_payload())
    assert incident.status_code == 201
    incident_id = incident.json()["id"]

    decision = client.post(
        f"/incidents/{incident_id}/decisions",
        json={
            "question": "Should the authority escalate the field investigation?",
            "deadline": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        },
    )
    assert decision.status_code == 201
    return incident_id, decision.json()["id"]


def _transition(client: TestClient, request_id: str, to_status: str) -> None:
    response = client.post(
        f"/api/requests/{request_id}/transitions",
        json={"to_status": to_status, "actor_name": "demo-user"},
    )
    assert response.status_code == 200, response.text


def test_request_fhir_ingestion_and_human_approval_close_the_loop(client: TestClient) -> None:
    incident_id, decision_id = _create_demo_decision(client)

    request = client.post(
        "/api/requests",
        json={
            "incident_id": incident_id,
            "decision_id": decision_id,
            "requested_evidence_code": "FIELD_DISSOLVED_OXYGEN",
            "purpose": "Verify the low dissolved oxygen hypothesis.",
            "priority": "URGENT",
            "estimated_cost": 1.0,
            "estimated_minutes": 20,
            "requested_by": "human-reviewer",
        },
    )
    assert request.status_code == 201, request.text
    request_id = request.json()["id"]
    assert request.json()["status"] == "DRAFT"
    assert request.json()["status_events"][0]["to_status"] == "DRAFT"

    for state in ("REQUESTED", "ACCEPTED", "COLLECTING", "SUBMITTED"):
        _transition(client, request_id, state)

    fhir = client.get(f"/api/requests/{request_id}/fhir")
    assert fhir.status_code == 200
    assert [entry["resource"]["resourceType"] for entry in fhir.json()["entry"]] == [
        "ServiceRequest",
        "Task",
    ]
    assert fhir.json()["entry"][0]["resource"]["subject"]["reference"] == (
        f"Incident/{incident_id}"
    )

    observation = client.post(
        f"/api/requests/{request_id}/observation",
        json={
            "resourceType": "Observation",
            "id": "OBS-DEMO-001",
            "status": "final",
            "effectiveDateTime": "2026-09-28T10:00:00+07:00",
            "valueQuantity": {"value": 3.4, "unit": "mg/L"},
            "device": {"display": "Simulated field DO meter"},
        },
    )
    assert observation.status_code == 200, observation.text
    assert observation.json()["request_status"] == "DECISION_UPDATED"
    assert observation.json()["decision_version"] == 2
    evidence_id = observation.json()["evidence_id"]

    approval = client.post(
        f"/api/decisions/{decision_id}/approval",
        json={
            "action": "APPROVE",
            "reviewer_id": "authority-user",
            "reason": "The direct measurement supports the escalation review.",
        },
    )
    assert approval.status_code == 200, approval.text
    assert approval.json()["status"] == "APPROVED"

    incident = client.get(f"/incidents/{incident_id}")
    assert incident.status_code == 200
    assert any(item["id"] == evidence_id for item in incident.json()["evidence"])

    audit = client.get(f"/api/incidents/{incident_id}/audit")
    assert audit.status_code == 200
    assert [item["event_type"] for item in audit.json()] == [
        "REQUEST_CREATED",
            "REQUEST_STATUS_CHANGED",
        "REQUEST_STATUS_CHANGED",
        "REQUEST_STATUS_CHANGED",
        "REQUEST_STATUS_CHANGED",
        "REQUEST_STATUS_CHANGED",
        "REQUEST_STATUS_CHANGED",
            "REQUEST_STATUS_CHANGED",
        "EVIDENCE_INGESTED",
        "DECISION_VERSION_CREATED",
        "DECISION_APPROVED",
    ]


def test_invalid_request_transition_is_rejected(client: TestClient) -> None:
    incident_id, decision_id = _create_demo_decision(client)
    request = client.post(
        "/api/requests",
        json={
            "incident_id": incident_id,
            "decision_id": decision_id,
            "requested_evidence_code": "FIELD_DISSOLVED_OXYGEN",
            "purpose": "Verify the low dissolved oxygen hypothesis.",
        },
    )
    request_id = request.json()["id"]

    invalid = client.post(
        f"/api/requests/{request_id}/transitions",
        json={"to_status": "COLLECTING", "actor_name": "demo-user"},
    )
    assert invalid.status_code == 409
    assert "Expected 'requested'" in invalid.json()["detail"]


def test_actor_assignment_and_intelligence_overview(client: TestClient) -> None:
    assigned = client.post(
        "/api/requests/assign",
        json={
            "evidence_id": "EV-005",
            "required_capability": "dissolved_oxygen_measurement",
            "required_location": "Demo Lake",
            "decision_deadline": "2026-09-28T12:00:00+00:00",
            "actors": [
                {
                    "actor_id": "ACT-FIELD-A",
                    "actor_name": "Field Team A",
                    "actor_type": "field_team",
                    "capability": "dissolved_oxygen_measurement",
                    "location": "Demo Lake",
                    "status": "available",
                    "available_from": "2026-09-28T09:00:00+00:00",
                    "available_until": "2026-09-28T17:00:00+00:00",
                    "max_concurrent_tasks": 1,
                    "expected_delay_minutes": 20,
                }
            ],
        },
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["actor_id"] == "ACT-FIELD-A"

    overview = client.post(
        "/api/intelligence/overview",
        json={
            "records": [
                {
                    "graph_id": "G-001",
                    "incident_id": "INC-FISH-001",
                    "decision_id": "DEC-FISH-001",
                    "source_node": "EV-005",
                    "source_type": "evidence",
                    "relationship": "missing_for",
                    "target_node": "HYP-LOW-DO",
                    "target_type": "hypothesis",
                    "confidence": 0.9,
                    "state": "missing",
                    "rationale": "Direct DO measurement is needed.",
                }
            ],
            "candidates": [
                {
                    "evidence_id": "EV-005",
                    "candidate_name": "Field DO measurement",
                    "decision_value": 0.95,
                    "reliability": 0.9,
                    "feasibility": 0.9,
                    "cost": 0.2,
                    "time": 0.2,
                }
            ],
        },
    )
    assert overview.status_code == 200, overview.text
    assert overview.json()["states"][0]["state"] == "missing"
    assert overview.json()["gaps"][0]["evidence_id"] == "EV-005"
    assert overview.json()["ranking"]["results"][0]["rank"] == 1
