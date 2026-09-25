from datetime import datetime

from app.modules.orchestration.evidence_request import (
    EvidenceRequestStatus,
    create_evidence_request,
    transition_evidence_request,
)


def test_evidence_request_full_lifecycle():
    request = create_evidence_request(
        request_id="REQ-FISH-005",
        incident_id="INC-FISH-001",
        decision_id="DEC-FISH-001",
        evidence_id="EV-005",
        evidence_type="dissolved_oxygen",
        purpose="Assess the low-DO hypothesis.",
        priority="high",
        decision_value=0.95,
        expected_cost=0.20,
        expected_time_minutes=30,
        assigned_actor_id="ACTOR-FIELD-001",
        created_at=datetime(2026, 9, 25, 10, 0),
    )

    expected_flow = [
        EvidenceRequestStatus.REQUESTED,
        EvidenceRequestStatus.ACCEPTED,
        EvidenceRequestStatus.COLLECTING,
        EvidenceRequestStatus.SUBMITTED,
        EvidenceRequestStatus.VERIFIED,
        EvidenceRequestStatus.INGESTED,
        EvidenceRequestStatus.DECISION_UPDATED,
    ]

    for expected_status in expected_flow:
        request = transition_evidence_request(
            request,
            expected_status,
        )

        assert request.status == expected_status

    assert len(request.transition_history) == 7