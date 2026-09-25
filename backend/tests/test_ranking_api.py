from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "aquapass-api",
        "database": "reachable",
    }


def test_ranking_endpoint():
    payload = {
        "candidates": [
            {
                "evidence_id": "EV-005",
                "candidate_name": "Field dissolved oxygen measurement",
                "decision_value": 0.95,
                "reliability": 0.90,
                "feasibility": 0.90,
                "cost": 0.20,
                "time": 0.20,
                "is_feasible": True,
            },
            {
                "evidence_id": "EV-006",
                "candidate_name": "Laboratory water analysis",
                "decision_value": 0.85,
                "reliability": 0.95,
                "feasibility": 0.70,
                "cost": 0.80,
                "time": 0.80,
                "is_feasible": True,
            },
        ]
    }

    response = client.post(
        "/api/ranking/evidence",
        json=payload,
    )

    assert response.status_code == 200

    body = response.json()

    assert len(body["results"]) == 2
    assert body["results"][0]["rank"] == 1
    assert body["results"][0]["selected"] is True
    assert body["results"][0]["evidence_id"] == "EV-005"


def test_ranking_endpoint_rejects_invalid_dimension():
    payload = {
        "candidates": [
            {
                "evidence_id": "EV-BAD",
                "candidate_name": "Invalid evidence",
                "decision_value": 1.5,
                "reliability": 0.90,
                "feasibility": 0.90,
                "cost": 0.20,
                "time": 0.20,
            }
        ]
    }

    response = client.post(
        "/api/ranking/evidence",
        json=payload,
    )

    assert response.status_code == 422