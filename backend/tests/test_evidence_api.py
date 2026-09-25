from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_detect_evidence_gaps_api():
    response = client.post(
        "/api/evidence/gaps",
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
                    "confidence": 0.90,
                    "state": "missing",
                    "rationale": (
                        "Direct DO measurement is needed "
                        "to assess the low-DO hypothesis."
                    ),
                }
            ]
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert "gaps" in body
    assert len(body["gaps"]) == 1

    gap = body["gaps"][0]

    assert gap["incident_id"] == "INC-FISH-001"
    assert gap["decision_id"] == "DEC-FISH-001"
    assert gap["evidence_id"] == "EV-005"
    assert gap["priority"] == "high"