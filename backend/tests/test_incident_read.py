"""Contract tests without accessing the user's Supabase project."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app


INCIDENT_ID = UUID("8f03fdce-cc4e-4fc1-a90b-15b2122e68b8")
DECISION_ID = UUID("00000000-0000-4000-8000-000000000201")
EVIDENCE_ID = UUID("00000000-0000-4000-8000-000000000102")
NOW = datetime(2026, 9, 19, 4, 0, tzinfo=timezone.utc)


class FakeResult:
    def __init__(self, rows: list[dict]):
        self.rows = rows

    def mappings(self) -> "FakeResult":
        return self

    def first(self) -> dict | None:
        return self.rows[0] if self.rows else None

    def all(self) -> list[dict]:
        return self.rows


class FakeSession:
    def __init__(self, results: list[list[dict]]):
        self.results = iter(results)
        self.query_count = 0

    def execute(self, statement, parameters=None) -> FakeResult:
        assert parameters is None
        self.query_count += 1
        return FakeResult(next(self.results))


def incident_row() -> dict:
    return {
        "id": INCIDENT_ID,
        "title": "Fish mortality at urban freshwater site",
        "description": "SIMULATED DATA: Fish mortality reported.",
        "incident_type": "FISH_MORTALITY",
        "location_name": "Demo Urban Lake - Site A",
        "latitude": 10.7769,
        "longitude": 106.7009,
        "severity": "HIGH",
        "status": "OPEN",
        "occurred_at": NOW,
        "created_at": NOW,
        "updated_at": NOW,
    }


def test_incident_detail_returns_evidence_and_decisions() -> None:
    evidence = {
        "id": EVIDENCE_ID,
        "incident_id": INCIDENT_ID,
        "code": "DISSOLVED_OXYGEN_SENSOR",
        "evidence_type": "SENSOR_READING",
        "state": "LOW_CONFIDENCE",
        "value_numeric": 3.8,
        "value_text": None,
        "unit": "mg/L",
        "source": "Simulated fixed sensor",
        "observed_at": NOW,
        "reliability_score": 0.55,
        "provenance": {"simulated": True},
        "is_simulated": True,
    }
    decision = {
        "id": DECISION_ID,
        "incident_id": INCIDENT_ID,
        "question": "Should the authority escalate the field investigation?",
        "deadline": NOW,
        "status": "PENDING",
        "current_version": 1,
    }
    fake_db = FakeSession([[incident_row()], [evidence], [decision]])
    app.dependency_overrides[get_db] = lambda: fake_db
    try:
        with TestClient(app) as client:
            response = client.get(f"/incidents/{INCIDENT_ID}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(INCIDENT_ID)
    assert body["evidence"][0]["value_numeric"] == 3.8
    assert body["evidence"][0]["is_simulated"] is True
    assert body["decisions"][0]["current_version"] == 1
    assert fake_db.query_count == 3


def test_unknown_incident_returns_404_without_querying_children() -> None:
    fake_db = FakeSession([[]])
    app.dependency_overrides[get_db] = lambda: fake_db
    try:
        with TestClient(app) as client:
            response = client.get(f"/incidents/{INCIDENT_ID}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Incident not found"}
    assert fake_db.query_count == 1


def test_malformed_incident_id_returns_422() -> None:
    with TestClient(app) as client:
        response = client.get("/incidents/not-a-uuid")

    assert response.status_code == 422


def test_openapi_contains_incident_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/incidents/{incident_id}" in response.json()["paths"]
