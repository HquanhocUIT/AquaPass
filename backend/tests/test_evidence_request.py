from datetime import datetime, timezone

import pytest

from app.modules.orchestration.evidence_request import (
    EvidenceRequestStatus,
    create_evidence_request,
    transition_evidence_request,
)


def _create_request():
    return create_evidence_request(
        request_id="REQ-001",
        incident_id="INC-FISH-001",
        decision_id="DEC-FISH-001",
        evidence_id="EV-005",
        evidence_type="dissolved_oxygen",
        purpose="Determine whether low dissolved oxygen is contributing to fish mortality.",
        priority="high",
        decision_value=0.95,
        expected_cost=0.20,
        expected_time_minutes=30,
        assigned_actor_id="ACTOR-FIELD-001",
        created_at=datetime(
            2026,
            9,
            17,
            12,
            0,
            tzinfo=timezone.utc,
        ),
    )


def test_create_evidence_request_starts_as_draft():
    request = _create_request()

    assert request.status == EvidenceRequestStatus.DRAFT
    assert request.incident_id == "INC-FISH-001"
    assert request.decision_id == "DEC-FISH-001"
    assert request.evidence_id == "EV-005"


def test_full_evidence_request_lifecycle():
    request = _create_request()

    request = transition_evidence_request(
        request,
        EvidenceRequestStatus.REQUESTED,
    )
    assert request.status == EvidenceRequestStatus.REQUESTED

    request = transition_evidence_request(
        request,
        EvidenceRequestStatus.ACCEPTED,
    )
    assert request.status == EvidenceRequestStatus.ACCEPTED

    request = transition_evidence_request(
        request,
        EvidenceRequestStatus.COLLECTING,
    )
    assert request.status == EvidenceRequestStatus.COLLECTING

    request = transition_evidence_request(
        request,
        EvidenceRequestStatus.SUBMITTED,
    )
    assert request.status == EvidenceRequestStatus.SUBMITTED

    request = transition_evidence_request(
        request,
        EvidenceRequestStatus.VERIFIED,
    )
    assert request.status == EvidenceRequestStatus.VERIFIED

    request = transition_evidence_request(
        request,
        EvidenceRequestStatus.INGESTED,
    )
    assert request.status == EvidenceRequestStatus.INGESTED


def test_invalid_transition_is_rejected():
    request = _create_request()

    with pytest.raises(ValueError, match="Invalid evidence request transition"):
        transition_evidence_request(
            request,
            EvidenceRequestStatus.ACCEPTED,
        )


def test_terminal_request_cannot_transition_again():
    request = _create_request()

    for next_status in (
        EvidenceRequestStatus.REQUESTED,
        EvidenceRequestStatus.ACCEPTED,
        EvidenceRequestStatus.COLLECTING,
        EvidenceRequestStatus.SUBMITTED,
        EvidenceRequestStatus.VERIFIED,
        EvidenceRequestStatus.INGESTED,
        EvidenceRequestStatus.DECISION_UPDATED,
    ):
        request = transition_evidence_request(
            request,
            next_status,
        )

    with pytest.raises(
        ValueError,
        match="already terminal",
    ):
        transition_evidence_request(
            request,
            EvidenceRequestStatus.DECISION_UPDATED,
        )


def test_request_preserves_same_incident_and_decision():
    request = _create_request()

    request = transition_evidence_request(
        request,
        EvidenceRequestStatus.REQUESTED,
    )

    request = transition_evidence_request(
        request,
        EvidenceRequestStatus.ACCEPTED,
    )

    assert request.incident_id == "INC-FISH-001"
    assert request.decision_id == "DEC-FISH-001"
    assert request.evidence_id == "EV-005"


@pytest.mark.parametrize(
    "field, value",
    [
        ("request_id", ""),
        ("incident_id", ""),
        ("decision_id", ""),
        ("evidence_id", ""),
        ("evidence_type", ""),
        ("purpose", ""),
    ],
)
def test_required_fields_are_validated(field, value):
    values = {
        "request_id": "REQ-001",
        "incident_id": "INC-FISH-001",
        "decision_id": "DEC-FISH-001",
        "evidence_id": "EV-005",
        "evidence_type": "dissolved_oxygen",
        "purpose": "Determine whether low dissolved oxygen is contributing to fish mortality.",
        "priority": "high",
        "decision_value": 0.95,
        "expected_cost": 0.20,
        "expected_time_minutes": 30,
    }

    values[field] = value

    with pytest.raises(ValueError):
        create_evidence_request(**values)


def test_priority_is_validated():
    with pytest.raises(ValueError, match="priority"):
        create_evidence_request(
            request_id="REQ-001",
            incident_id="INC-FISH-001",
            decision_id="DEC-FISH-001",
            evidence_id="EV-005",
            evidence_type="dissolved_oxygen",
            purpose="Test",
            priority="critical",
            decision_value=0.95,
            expected_cost=0.20,
            expected_time_minutes=30,
        )


def test_decision_value_is_validated():
    with pytest.raises(ValueError, match="decision_value"):
        create_evidence_request(
            request_id="REQ-001",
            incident_id="INC-FISH-001",
            decision_id="DEC-FISH-001",
            evidence_id="EV-005",
            evidence_type="dissolved_oxygen",
            purpose="Test",
            priority="high",
            decision_value=1.5,
            expected_cost=0.20,
            expected_time_minutes=30,
        )


def test_cost_and_time_are_validated():
    with pytest.raises(ValueError, match="expected_cost"):
        create_evidence_request(
            request_id="REQ-001",
            incident_id="INC-FISH-001",
            decision_id="DEC-FISH-001",
            evidence_id="EV-005",
            evidence_type="dissolved_oxygen",
            purpose="Test",
            priority="high",
            decision_value=0.95,
            expected_cost=-0.1,
            expected_time_minutes=30,
        )

    with pytest.raises(ValueError, match="expected_time_minutes"):
        create_evidence_request(
            request_id="REQ-001",
            incident_id="INC-FISH-001",
            decision_id="DEC-FISH-001",
            evidence_id="EV-005",
            evidence_type="dissolved_oxygen",
            purpose="Test",
            priority="high",
            decision_value=0.95,
            expected_cost=0.20,
            expected_time_minutes=-1,
        )


def test_transition_history_records_every_transition():
    request = _create_request()

    request = transition_evidence_request(
        request,
        EvidenceRequestStatus.REQUESTED,
    )

    request = transition_evidence_request(
        request,
        EvidenceRequestStatus.ACCEPTED,
    )

    assert len(request.transition_history) == 2

    first = request.transition_history[0]
    second = request.transition_history[1]

    assert first.from_status == EvidenceRequestStatus.DRAFT
    assert first.to_status == EvidenceRequestStatus.REQUESTED
    assert first.transitioned_at is not None

    assert second.from_status == EvidenceRequestStatus.REQUESTED
    assert second.to_status == EvidenceRequestStatus.ACCEPTED
    assert second.transitioned_at is not None


def test_transition_history_is_preserved_through_full_lifecycle():
    request = _create_request()

    for next_status in (
        EvidenceRequestStatus.REQUESTED,
        EvidenceRequestStatus.ACCEPTED,
        EvidenceRequestStatus.COLLECTING,
        EvidenceRequestStatus.SUBMITTED,
        EvidenceRequestStatus.VERIFIED,
        EvidenceRequestStatus.INGESTED,
        EvidenceRequestStatus.DECISION_UPDATED,
    ):
        request = transition_evidence_request(
            request,
            next_status,
        )

    assert request.status == EvidenceRequestStatus.DECISION_UPDATED
    assert len(request.transition_history) == 7


def test_decision_updated_is_terminal():
    request = _create_request()

    for next_status in (
        EvidenceRequestStatus.REQUESTED,
        EvidenceRequestStatus.ACCEPTED,
        EvidenceRequestStatus.COLLECTING,
        EvidenceRequestStatus.SUBMITTED,
        EvidenceRequestStatus.VERIFIED,
        EvidenceRequestStatus.INGESTED,
        EvidenceRequestStatus.DECISION_UPDATED,
    ):
        request = transition_evidence_request(
            request,
            next_status,
        )

    with pytest.raises(ValueError, match="already terminal"):
        transition_evidence_request(
            request,
            EvidenceRequestStatus.REQUESTED,
        )