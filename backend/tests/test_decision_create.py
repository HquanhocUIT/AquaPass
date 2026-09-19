"""Decision writes are exercised only against a disposable SQLite database."""

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.db.tables import decision_versions, decisions, metadata
from app.main import app
from tests.test_evidence_create import valid_evidence_payload
from tests.test_incident_create import valid_payload as valid_incident_payload


@pytest.fixture
def test_database() -> Iterator[sessionmaker[Session]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def attach_public_schema(dbapi_connection, connection_record) -> None:
        dbapi_connection.execute("ATTACH DATABASE ':memory:' AS public")

    metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    yield session_factory
    engine.dispose()


@pytest.fixture
def client(test_database: sessionmaker[Session]) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        with test_database() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def valid_decision_payload() -> dict:
    return {
        "question": "Should the authority escalate the field investigation?",
        "deadline": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    }


def make_incident(client: TestClient) -> str:
    response = client.post("/incidents", json=valid_incident_payload())
    assert response.status_code == 201
    return response.json()["id"]


def test_create_decision_with_first_version_and_evidence_snapshot(
    client: TestClient, test_database: sessionmaker[Session]
) -> None:
    incident_id = make_incident(client)
    evidence_response = client.post(
        f"/incidents/{incident_id}/evidence", json=valid_evidence_payload()
    )
    assert evidence_response.status_code == 201

    response = client.post(
        f"/incidents/{incident_id}/decisions", json=valid_decision_payload()
    )

    assert response.status_code == 201
    body = response.json()
    assert body["incident_id"] == incident_id
    assert body["status"] == "PENDING"
    assert body["current_version"] == 1
    assert body["version"]["decision_id"] == body["id"]
    assert body["version"]["version_number"] == 1
    assert body["version"]["uncertainty_level"] == "HIGH"
    assert body["version"]["approval_status"] == "PENDING"
    assert body["version"]["created_by"] == "system"
    assert body["version"]["evidence_snapshot"] == {
        "evidence_ids": [evidence_response.json()["id"]],
        "evidence_codes": [evidence_response.json()["code"]],
    }

    refreshed = client.get(f"/incidents/{incident_id}")
    assert refreshed.status_code == 200
    assert [item["id"] for item in refreshed.json()["decisions"]] == [body["id"]]
    with test_database() as db:
        assert db.scalar(select(func.count()).select_from(decisions)) == 1
        assert db.scalar(select(func.count()).select_from(decision_versions)) == 1


def test_empty_evidence_snapshot(client: TestClient) -> None:
    incident_id = make_incident(client)
    response = client.post(
        f"/incidents/{incident_id}/decisions", json=valid_decision_payload()
    )

    assert response.status_code == 201
    assert response.json()["version"]["evidence_snapshot"] == {
        "evidence_ids": [],
        "evidence_codes": [],
    }


def test_unknown_incident_returns_404_without_inserts(
    client: TestClient, test_database: sessionmaker[Session]
) -> None:
    response = client.post(
        "/incidents/00000000-0000-4000-8000-000000000000/decisions",
        json=valid_decision_payload(),
    )

    assert response.status_code == 404
    with test_database() as db:
        assert db.scalar(select(func.count()).select_from(decisions)) == 0
        assert db.scalar(select(func.count()).select_from(decision_versions)) == 0


@pytest.mark.parametrize(
    "change",
    [
        {"question": "  "},
        {"deadline": "2026-09-19T10:00:00"},
        {"deadline": "2020-01-01T00:00:00+00:00"},
        {"status": "APPROVED"},
    ],
)
def test_invalid_payload_returns_422_without_inserts(
    client: TestClient, test_database: sessionmaker[Session], change: dict
) -> None:
    incident_id = make_incident(client)
    payload = valid_decision_payload()
    payload.update(change)
    response = client.post(f"/incidents/{incident_id}/decisions", json=payload)

    assert response.status_code == 422
    with test_database() as db:
        assert db.scalar(select(func.count()).select_from(decisions)) == 0
        assert db.scalar(select(func.count()).select_from(decision_versions)) == 0


def test_version_insert_failure_rolls_back_decision(
    client: TestClient, test_database: sessionmaker[Session]
) -> None:
    incident_id = make_incident(client)
    engine = test_database.kw["bind"]

    def reject_version_insert(conn, cursor, statement, parameters, context, executemany):
        if "INSERT INTO public.decision_versions" in statement:
            raise RuntimeError("simulated version insert failure")

    event.listen(engine, "before_cursor_execute", reject_version_insert)
    try:
        with TestClient(app, raise_server_exceptions=False) as error_client:
            response = error_client.post(
                f"/incidents/{incident_id}/decisions", json=valid_decision_payload()
            )
    finally:
        event.remove(engine, "before_cursor_execute", reject_version_insert)

    assert response.status_code == 500
    with test_database() as db:
        assert db.scalar(select(func.count()).select_from(decisions)) == 0
        assert db.scalar(select(func.count()).select_from(decision_versions)) == 0
