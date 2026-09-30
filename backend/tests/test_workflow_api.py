"""HTTP tests for Quân's closed-loop workflow endpoints."""

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
import hashlib
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, insert, select, update
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.db.tables import actors, evidence, evidence_gaps, hypotheses, request_attachments
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
            test_client.app.state.test_session_factory = factory
            yield test_client
    finally:
        app.dependency_overrides.clear()
        if hasattr(app.state, "test_session_factory"):
            del app.state.test_session_factory
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
    hypothesis_id = uuid4()
    with client.app.state.test_session_factory() as db:
        db.execute(
            insert(hypotheses).values(
                id=hypothesis_id,
                incident_id=UUID(incident_id),
                code="H1",
                title="Low dissolved oxygen",
                description="Prototype hypothesis for testing.",
                status="ACTIVE",
                support_score=0.60,
            )
        )
        db.commit()

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

    invalid_observation = client.post(
        f"/api/requests/{request_id}/observation",
        json={
            "resourceType": "Observation",
            "id": "OBS-MISSING-RATIONALE",
            "effectiveDateTime": "2026-09-28T10:00:00+07:00",
            "valueQuantity": {"value": 3.4, "unit": "mg/L"},
            "extension": [
                {
                    "url": "https://aquapass.example/fhir/StructureDefinition/hypothesis-impact",
                    "extension": [
                        {"url": "hypothesisCode", "valueCode": "H1"},
                        {"url": "direction", "valueCode": "supports"},
                    ],
                }
            ],
        },
    )
    assert invalid_observation.status_code == 422
    assert "rationale" in invalid_observation.json()["detail"]
    with client.app.state.test_session_factory() as db:
        assert db.scalar(
            select(evidence.c.id).where(evidence.c.incident_id == UUID(incident_id))
        ) is None

    observation = client.post(
        f"/api/requests/{request_id}/observation",
        json={
            "resourceType": "Observation",
            "id": "OBS-DEMO-001",
            "status": "final",
            "effectiveDateTime": "2026-09-28T10:00:00+07:00",
            "valueQuantity": {"value": 3.4, "unit": "mg/L"},
            "device": {"display": "Simulated field DO meter"},
            "performer": [{"display": "field-operator"}],
            "meta": {
                "tag": [
                    {
                        "system": "https://aquapass.example/tags",
                        "code": "simulated",
                    }
                ]
            },
            "extension": [
                {
                    "url": "https://aquapass.example/fhir/StructureDefinition/hypothesis-impact",
                    "extension": [
                        {"url": "hypothesisCode", "valueCode": "H1"},
                        {"url": "direction", "valueCode": "supports"},
                        {
                            "url": "rationale",
                            "valueString": "The recorded field result supports the stated hypothesis.",
                        },
                    ],
                }
            ],
        },
    )
    assert observation.status_code == 200, observation.text
    assert observation.json()["request_status"] == "DECISION_UPDATED"
    assert observation.json()["decision_version"] == 2
    assert observation.json()["hypothesis_updates"][0]["new_status"] == "stronger"
    assert observation.json()["hypothesis_updates"][0]["new_support_score"] == 0.7
    updated_decision = client.get(f"/decisions/{decision_id}")
    assert updated_decision.status_code == 200, updated_decision.text
    assert updated_decision.json()["current_version"] == 2
    snapshot = updated_decision.json()["versions"][-1]["evidence_snapshot"]
    assert snapshot["triggering_evidence_id"] == observation.json()["evidence_id"]
    assert snapshot["evidence_codes"] == ["FIELD_DISSOLVED_OXYGEN"]
    assert snapshot["hypothesis_updates"][0]["hypothesis_code"] == "H1"
    with client.app.state.test_session_factory() as db:
        support_score = db.scalar(
            select(hypotheses.c.support_score).where(hypotheses.c.id == hypothesis_id)
        )
    assert support_score == 0.7
    evidence_id = observation.json()["evidence_id"]
    with client.app.state.test_session_factory() as db:
        persisted_evidence = db.execute(
            select(evidence).where(evidence.c.id == UUID(evidence_id))
        ).mappings().one()
    assert persisted_evidence["is_simulated"] is True

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
        "HYPOTHESIS_UPDATED",
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


def test_request_can_be_rejected_before_collection(client: TestClient) -> None:
    incident_id, decision_id = _create_demo_decision(client)
    created = client.post(
        "/api/requests",
        json={
            "incident_id": incident_id,
            "decision_id": decision_id,
            "requested_evidence_code": "FIELD_DISSOLVED_OXYGEN",
            "purpose": "Verify the low dissolved oxygen hypothesis.",
        },
    )
    assert created.status_code == 201, created.text

    rejected = client.post(
        f"/api/requests/{created.json()['id']}/transitions",
        json={"to_status": "REJECTED", "actor_name": "reviewer", "note": "Not needed."},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "REJECTED"
    assert [event["to_status"] for event in rejected.json()["status_events"]] == [
        "DRAFT",
        "REJECTED",
    ]


def test_actor_assignment_and_intelligence_overview(client: TestClient) -> None:
    naive_assignment = client.post(
        "/api/requests/assign",
        json={
            "evidence_id": "EV-005",
            "required_capability": "dissolved_oxygen_measurement",
            "required_location": "Demo Lake",
            "decision_deadline": "2026-09-28T12:00:00",
            "actors": [
                {
                    "actor_id": "ACT-FIELD-A",
                    "actor_name": "Field Team A",
                    "actor_type": "field_team",
                    "capability": "dissolved_oxygen_measurement",
                    "location": "Demo Lake",
                    "status": "available",
                    "available_from": "2026-09-28T09:00:00",
                    "available_until": "2026-09-28T17:00:00",
                    "max_concurrent_tasks": 1,
                    "expected_delay_minutes": 20,
                }
            ],
        },
    )
    assert naive_assignment.status_code == 422

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


def test_database_intelligence_overview_uses_incident_and_candidate_catalog(
    client: TestClient,
) -> None:
    payload = valid_incident_payload()
    payload["incident_type"] = "FISH_MORTALITY"
    incident_response = client.post("/incidents", json=payload)
    assert incident_response.status_code == 201, incident_response.text
    incident_id = incident_response.json()["id"]

    decision_response = client.post(
        f"/incidents/{incident_id}/decisions",
        json={
            "question": "Should the field investigation be escalated?",
            "deadline": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        },
    )
    assert decision_response.status_code == 201, decision_response.text
    decision_id = decision_response.json()["id"]

    hypothesis_id = uuid4()
    field_reading_id = uuid4()
    stale_weather_id = uuid4()
    gap_id = uuid4()
    actor_id = uuid4()
    with client.app.state.test_session_factory() as db:
        db.execute(
            insert(hypotheses).values(
                id=hypothesis_id,
                incident_id=UUID(incident_id),
                code="H1",
                title="Low dissolved oxygen",
                description="Test whether low oxygen contributed to the incident.",
                status="ACTIVE",
                support_score=0.6,
            )
        )
        db.execute(
            insert(evidence).values(
                id=field_reading_id,
                incident_id=UUID(incident_id),
                code="DISSOLVED_OXYGEN_SENSOR",
                evidence_type="SENSOR_READING",
                state="LOW_CONFIDENCE",
                value_numeric=3.8,
                unit="mg/L",
                source="Simulated fixed sensor",
                observed_at=datetime.now(timezone.utc) - timedelta(minutes=30),
                reliability_score=0.55,
                provenance={"simulated": True},
                is_simulated=True,
            )
        )
        db.execute(
            insert(evidence).values(
                id=stale_weather_id,
                incident_id=UUID(incident_id),
                code="HEAVY_RAINFALL",
                evidence_type="WEATHER_OBSERVATION",
                state="STALE",
                value_numeric=42.0,
                unit="mm/24h",
                source="Test weather feed",
                observed_at=datetime.now(timezone.utc) - timedelta(minutes=30),
                reliability_score=0.95,
                provenance={"simulated": True},
                is_simulated=True,
            )
        )
        db.execute(
            insert(evidence_gaps).values(
                id=gap_id,
                incident_id=UUID(incident_id),
                decision_id=UUID(decision_id),
                code="FIELD_DISSOLVED_OXYGEN",
                description="The low-confidence sensor reading needs field verification.",
                criticality="HIGH",
                status="OPEN",
                rationale="Direct field measurement is needed before escalation.",
            )
        )
        db.execute(
            insert(actors).values(
                id=actor_id,
                code="TEST_FIELD_TEAM",
                name="Test field team",
                actor_type="FIELD_TEAM",
                capabilities=["FIELD_DISSOLVED_OXYGEN"],
                location_name=incident_response.json()["location_name"],
                available=True,
                capacity=1,
                turnaround_minutes=20,
            )
        )
        db.commit()

    incident_index = client.get("/incidents")
    assert incident_index.status_code == 200, incident_index.text
    indexed = next(
        item for item in incident_index.json()
        if item["id"] == incident_id
    )
    assert indexed["pending_decision_count"] == 1

    overview = client.get(
        f"/api/intelligence/incidents/{incident_id}/overview"
    )
    assert overview.status_code == 200, overview.text

    result = overview.json()
    assert len(result["profiles"]) == 3
    assert result["ranking"]["results"]
    assert all(
        item["evidence_id"] in {"EV-005", "EV-006", "EV-007"}
        for item in result["ranking"]["results"]
    )
    assert any(
        gap["evidence_id"] == "EV-005"
        for gap in result["gaps"]
    )
    assert any(
        state["evidence_id"] == "EV-005" and state["state"] == "missing"
        for state in result["states"]
    )
    assert any(
        state["evidence_id"] == str(field_reading_id)
        and state["state"] == "unreliable"
        for state in result["states"]
    )
    assert any(
        state["evidence_id"] == str(stale_weather_id)
        and state["state"] == "stale"
        for state in result["states"]
    )
    assert any(
        relation["source_node"] == str(field_reading_id)
        and relation["target_node"] == "H1"
        and relation["state"] == "unreliable"
        for relation in result["graph"]
    )
    field_profile = next(
        profile for profile in result["profiles"]
        if profile["evidence_id"] == "EV-005"
    )
    assert field_profile["database_gap_id"] == str(gap_id)
    assert field_profile["feasible"] is True
    assert any(item["evidence_id"] == "EV-005" for item in result["ranking"]["results"])

    with client.app.state.test_session_factory() as db:
        db.execute(
            update(actors)
            .where(actors.c.id == actor_id)
            .values(location_name="Different test site")
        )
        db.commit()
    moved_actor_overview = client.get(
        f"/api/intelligence/incidents/{incident_id}/overview"
    )
    assert moved_actor_overview.status_code == 200, moved_actor_overview.text
    moved_field_profile = next(
        profile for profile in moved_actor_overview.json()["profiles"]
        if profile["evidence_id"] == "EV-005"
    )
    assert moved_field_profile["feasible"] is False
    assert "location" in moved_field_profile["infeasibility_reason"].lower()
    assert not any(
        item["evidence_id"] == "EV-005"
        for item in moved_actor_overview.json()["ranking"]["results"]
    )


def test_decision_rejection_requires_reason_and_persists_review(client: TestClient) -> None:
    incident_id, decision_id = _create_demo_decision(client)
    rejected_without_reason = client.post(
        f"/api/decisions/{decision_id}/approval",
        json={"action": "REJECT", "reviewer_id": "authority-user"},
    )
    assert rejected_without_reason.status_code == 422

    rejection = client.post(
        f"/api/decisions/{decision_id}/approval",
        json={
            "action": "REJECT",
            "reviewer_id": "authority-user",
            "reason": "The submitted evidence does not justify escalation.",
        },
    )
    assert rejection.status_code == 200, rejection.text
    assert rejection.json()["status"] == "REJECTED"

    detail = client.get(f"/decisions/{decision_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "REJECTED"
    assert detail.json()["versions"][0]["approval_status"] == "REJECTED"
    assert detail.json()["versions"][0]["approved_by"] == "authority-user"

    duplicate = client.post(
        f"/api/decisions/{decision_id}/approval",
        json={
            "action": "APPROVE",
            "reviewer_id": "second-reviewer",
            "reason": "A reviewed version cannot be changed.",
        },
    )
    assert duplicate.status_code == 409
    audit = client.get(f"/api/incidents/{incident_id}/audit")
    assert audit.status_code == 200
    assert audit.json()[-1]["event_type"] == "DECISION_REJECTED"


def test_request_attachments_are_validated_stored_downloadable_and_locked_after_send(
    client: TestClient,
) -> None:
    incident_id, decision_id = _create_demo_decision(client)
    request = client.post(
        "/api/requests",
        json={
            "incident_id": incident_id,
            "decision_id": decision_id,
            "requested_evidence_code": "FIELD_DISSOLVED_OXYGEN",
            "purpose": "Verify a field measurement.",
        },
    )
    assert request.status_code == 201, request.text
    request_id = request.json()["id"]
    assert request.json()["attachments"] == []

    photo = b"\x89PNG\r\n\x1a\n" + b"sample-image-content"
    report = b"%PDF-1.4\nSample field report\n"
    uploaded = client.post(
        f"/api/requests/{request_id}/attachments",
        files=[
            ("files", ("water-sample.png", photo, "image/png")),
            ("files", ("field report.pdf", report, "application/pdf")),
        ],
    )
    assert uploaded.status_code == 201, uploaded.text
    attachments = uploaded.json()
    assert [item["filename"] for item in attachments] == ["water-sample.png", "field report.pdf"]
    assert attachments[0]["sha256"] == hashlib.sha256(photo).hexdigest()
    assert attachments[1]["content_type"] == "application/pdf"

    loaded_request = client.get(f"/api/requests/{request_id}")
    assert loaded_request.status_code == 200
    assert [item["id"] for item in loaded_request.json()["attachments"]] == [
        item["id"] for item in attachments
    ]
    audit = client.get(f"/api/incidents/{incident_id}/audit")
    assert audit.status_code == 200
    assert audit.json()[-1]["event_type"] == "REQUEST_ATTACHMENT_ADDED"
    assert audit.json()[-1]["payload"]["attachment_count"] == 2
    downloaded = client.get(
        f"/api/requests/{request_id}/attachments/{attachments[0]['id']}"
    )
    assert downloaded.status_code == 200
    assert downloaded.content == photo
    assert "attachment; filename*=UTF-8''water-sample.png" in downloaded.headers["content-disposition"]
    assert downloaded.headers["x-content-type-options"] == "nosniff"
    with client.app.state.test_session_factory() as db:
        stored_bytes = db.scalar(
            select(request_attachments.c.data).where(
                request_attachments.c.id == UUID(attachments[0]["id"])
            )
        )
    assert stored_bytes == photo

    wrong_signature = client.post(
        f"/api/requests/{request_id}/attachments",
        files=[("files", ("not-a-photo.png", b"plain text", "image/png"))],
    )
    assert wrong_signature.status_code == 415
    too_large = client.post(
        f"/api/requests/{request_id}/attachments",
        files=[
            (
                "files",
                ("large.pdf", b"%PDF-" + b"x" * (10 * 1024 * 1024), "application/pdf"),
            )
        ],
    )
    assert too_large.status_code == 413
    over_count = client.post(
        f"/api/requests/{request_id}/attachments",
        files=[
            ("files", (f"extra-{index}.txt", b"extra", "text/plain"))
            for index in range(4)
        ],
    )
    assert over_count.status_code == 422

    _transition(client, request_id, "REQUESTED")
    locked = client.post(
        f"/api/requests/{request_id}/attachments",
        files=[("files", ("later.txt", b"supplement", "text/plain"))],
    )
    assert locked.status_code == 409
