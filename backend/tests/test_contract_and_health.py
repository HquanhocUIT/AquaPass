"""Published OpenAPI and read-only readiness stay aligned with the app."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from tests.test_decision_create import client, test_database


def test_health_checks_database(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "aquapass-api",
        "database": "reachable",
    }


def test_exported_openapi_matches_runtime() -> None:
    path = Path(__file__).resolve().parents[2] / "docs" / "api" / "openapi.json"
    assert json.loads(path.read_text(encoding="utf-8")) == app.openapi()


def test_phase_one_paths_are_published() -> None:
    paths = app.openapi()["paths"]
    assert "post" in paths["/incidents"]
    assert "get" in paths["/incidents/{incident_id}"]
    assert "post" in paths["/incidents/{incident_id}/evidence"]
    assert "post" in paths["/incidents/{incident_id}/decisions"]
    assert "get" in paths["/decisions/{decision_id}"]
    assert "get" in paths["/health"]
