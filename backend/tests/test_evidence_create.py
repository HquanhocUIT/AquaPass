"""Evidence write tests run only against a disposable in-memory database."""

from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.db.tables import evidence, metadata
from app.main import app
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


def valid_evidence_payload() -> dict:
    return {
        "code": "FIELD_DISSOLVED_OXYGEN",
        "evidence_type": "FIELD_MEASUREMENT",
        "value_numeric": 3.4,
        "unit": "mg/L",
        "source": "Demo field team",
        "observed_at": "2026-09-19T09:00:00+07:00",
        "provenance": {"method": "portable DO meter", "simulated": False},
    }


def make_incident(client: TestClient) -> str:
    response = client.post("/incidents", json=valid_incident_payload())
    assert response.status_code == 201
    return response.json()["id"]


def test_evidence_is_attached_to_same_incident(
    client: TestClient, test_database: sessionmaker[Session]
) -> None:
    incident_id = make_incident(client)
    response = client.post(
        f"/incidents/{incident_id}/evidence", json=valid_evidence_payload()
    )

    assert response.status_code == 201
    body = response.json()
    assert body["incident_id"] == incident_id
    assert body["value_numeric"] == 3.4
    assert body["state"] == "KNOWN"
    assert body["reliability_score"] == 0.5
    assert body["is_simulated"] is True
    assert body["provenance"]["simulated"] is True

    refreshed = client.get(f"/incidents/{incident_id}")
    assert refreshed.status_code == 200
    assert [item["id"] for item in refreshed.json()["evidence"]] == [body["id"]]

    with test_database() as db:
        attached_id = db.scalar(select(evidence.c.incident_id))
    assert attached_id == UUID(incident_id)


def test_same_code_can_be_measured_twice(
    client: TestClient, test_database: sessionmaker[Session]
) -> None:
    incident_id = make_incident(client)
    first = client.post(f"/incidents/{incident_id}/evidence", json=valid_evidence_payload())
    second_payload = valid_evidence_payload()
    second_payload["value_numeric"] = 3.6
    second_payload["observed_at"] = "2026-09-19T09:30:00+07:00"
    second = client.post(f"/incidents/{incident_id}/evidence", json=second_payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    with test_database() as db:
        assert db.scalar(select(func.count()).select_from(evidence)) == 2


def test_unknown_incident_returns_404_without_insert(
    client: TestClient, test_database: sessionmaker[Session]
) -> None:
    response = client.post(
        "/incidents/00000000-0000-4000-8000-000000000000/evidence",
        json=valid_evidence_payload(),
    )

    assert response.status_code == 404
    with test_database() as db:
        assert db.scalar(select(func.count()).select_from(evidence)) == 0


@pytest.mark.parametrize(
    "change",
    [
        {"value_numeric": None},
        {"value_text": "Dead fish seen"},
        {"unit": None},
        {"observed_at": "2026-09-19T09:00:00"},
        {"source": ""},
        {"incident_id": "00000000-0000-4000-8000-000000000000"},
        {"is_simulated": False},
    ],
)
def test_invalid_evidence_returns_422_without_insert(
    client: TestClient,
    test_database: sessionmaker[Session],
    change: dict,
) -> None:
    incident_id = make_incident(client)
    payload = valid_evidence_payload()
    payload.update(change)
    response = client.post(f"/incidents/{incident_id}/evidence", json=payload)

    assert response.status_code == 422
    with test_database() as db:
        assert db.scalar(select(func.count()).select_from(evidence)) == 0


def test_text_evidence_does_not_need_unit(client: TestClient) -> None:
    incident_id = make_incident(client)
    payload = valid_evidence_payload()
    payload.pop("value_numeric")
    payload.pop("unit")
    payload["value_text"] = "Multiple dead fish observed"
    response = client.post(f"/incidents/{incident_id}/evidence", json=payload)

    assert response.status_code == 201
    assert response.json()["value_text"] == "Multiple dead fish observed"
    assert response.json()["unit"] is None
