"""Read decision history from a disposable in-memory database."""

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import insert, update
from sqlalchemy.orm import Session, sessionmaker

from app.db.tables import decision_versions, decisions
from tests.test_decision_create import (
    client,
    make_incident,
    test_database,
    valid_decision_payload,
)
from tests.test_evidence_create import valid_evidence_payload


def test_get_decision_preserves_first_snapshot_after_new_evidence(
    client: TestClient,
) -> None:
    incident_id = make_incident(client)
    first_evidence = client.post(
        f"/incidents/{incident_id}/evidence", json=valid_evidence_payload()
    )
    assert first_evidence.status_code == 201
    created = client.post(
        f"/incidents/{incident_id}/decisions", json=valid_decision_payload()
    )
    assert created.status_code == 201

    later_payload = valid_evidence_payload()
    later_payload["code"] = "FOLLOW_UP_MEASUREMENT"
    later_evidence = client.post(
        f"/incidents/{incident_id}/evidence", json=later_payload
    )
    assert later_evidence.status_code == 201

    response = client.get(f"/decisions/{created.json()['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created.json()["id"]
    assert body["incident_id"] == incident_id
    assert body["current_version"] == 1
    assert body["versions"] == [created.json()["version"]]
    assert body["versions"][0]["evidence_snapshot"]["evidence_ids"] == [
        first_evidence.json()["id"]
    ]


def test_versions_are_returned_in_version_number_order(
    client: TestClient, test_database: sessionmaker[Session]
) -> None:
    incident_id = make_incident(client)
    created = client.post(
        f"/incidents/{incident_id}/decisions", json=valid_decision_payload()
    )
    assert created.status_code == 201
    decision_id = UUID(created.json()["id"])
    with test_database.begin() as db:
        db.execute(
            insert(decision_versions).values(
                id=uuid4(),
                decision_id=decision_id,
                version_number=2,
                summary="Later review.",
                uncertainty_level="MEDIUM",
                evidence_snapshot={"evidence_ids": [], "evidence_codes": []},
                approval_status="PENDING",
                created_by="system",
            )
        )
        db.execute(
            update(decisions)
            .where(decisions.c.id == decision_id)
            .values(current_version=2)
        )

    response = client.get(f"/decisions/{decision_id}")

    assert response.status_code == 200
    assert response.json()["current_version"] == 2
    assert [version["version_number"] for version in response.json()["versions"]] == [1, 2]


def test_unknown_decision_returns_404(client: TestClient) -> None:
    response = client.get("/decisions/00000000-0000-4000-8000-000000000000")

    assert response.status_code == 404
    assert response.json() == {"detail": "Decision not found"}


def test_invalid_decision_id_returns_422(client: TestClient) -> None:
    response = client.get("/decisions/not-a-uuid")

    assert response.status_code == 422
