"""POST tests use a disposable SQLite database, never Supabase."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.db.tables import incidents, metadata
from app.main import app


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


def valid_payload() -> dict:
    return {
        "title": "Fish mortality at Site B",
        "description": "SIMULATED DATA: Fish mortality reported.",
        "incident_type": "FISH_MORTALITY",
        "location_name": "Demo Urban Lake - Site B",
        "latitude": 10.77,
        "longitude": 106.70,
        "severity": "HIGH",
        "occurred_at": "2026-09-19T08:00:00+07:00",
    }


def test_create_incident_returns_201_and_persists_row(
    client: TestClient, test_database: sessionmaker[Session]
) -> None:
    response = client.post("/incidents", json=valid_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Fish mortality at Site B"
    assert body["status"] == "OPEN"
    assert body["severity"] == "HIGH"
    assert body["id"]
    assert body["created_at"]
    assert body["updated_at"]

    with test_database() as db:
        assert db.scalar(select(func.count()).select_from(incidents)) == 1


@pytest.mark.parametrize(
    "change",
    [
        {"title": None},
        {"severity": "URGENT"},
        {"occurred_at": "2026-09-19T08:00:00"},
        {"id": "00000000-0000-4000-8000-000000000000"},
    ],
)
def test_invalid_incident_returns_422_without_inserting(
    client: TestClient,
    test_database: sessionmaker[Session],
    change: dict,
) -> None:
    payload = valid_payload()
    payload.update(change)
    response = client.post("/incidents", json=payload)

    assert response.status_code == 422
    with test_database() as db:
        assert db.scalar(select(func.count()).select_from(incidents)) == 0


def test_openapi_describes_create_incident(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert "post" in schema["paths"]["/incidents"]
