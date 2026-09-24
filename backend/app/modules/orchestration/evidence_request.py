from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class EvidenceRequestStatus(str, Enum):
    DRAFT = "draft"
    REQUESTED = "requested"
    ACCEPTED = "accepted"
    COLLECTING = "collecting"
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    INGESTED = "ingested"
    DECISION_UPDATED = "decision_updated"


@dataclass(frozen=True)
class EvidenceRequestTransition:
    from_status: EvidenceRequestStatus
    to_status: EvidenceRequestStatus
    transitioned_at: datetime


@dataclass(frozen=True)
class EvidenceRequest:
    request_id: str
    incident_id: str
    decision_id: str
    evidence_id: str
    evidence_type: str
    purpose: str
    priority: str
    decision_value: float
    expected_cost: float
    expected_time_minutes: int
    status: EvidenceRequestStatus = EvidenceRequestStatus.DRAFT
    assigned_actor_id: str | None = None
    created_at: datetime | None = None
    transition_history: tuple[EvidenceRequestTransition, ...] = ()


_ALLOWED_TRANSITIONS: dict[
    EvidenceRequestStatus,
    EvidenceRequestStatus,
] = {
    EvidenceRequestStatus.DRAFT: EvidenceRequestStatus.REQUESTED,
    EvidenceRequestStatus.REQUESTED: EvidenceRequestStatus.ACCEPTED,
    EvidenceRequestStatus.ACCEPTED: EvidenceRequestStatus.COLLECTING,
    EvidenceRequestStatus.COLLECTING: EvidenceRequestStatus.SUBMITTED,
    EvidenceRequestStatus.SUBMITTED: EvidenceRequestStatus.VERIFIED,
    EvidenceRequestStatus.VERIFIED: EvidenceRequestStatus.INGESTED,
    EvidenceRequestStatus.INGESTED: EvidenceRequestStatus.DECISION_UPDATED,
}


def _validate_request(request: EvidenceRequest) -> None:
    if not request.request_id:
        raise ValueError("request_id must not be empty")

    if not request.incident_id:
        raise ValueError("incident_id must not be empty")

    if not request.decision_id:
        raise ValueError("decision_id must not be empty")

    if not request.evidence_id:
        raise ValueError("evidence_id must not be empty")

    if not request.evidence_type:
        raise ValueError("evidence_type must not be empty")

    if not request.purpose:
        raise ValueError("purpose must not be empty")

    if request.priority not in {"high", "medium", "low"}:
        raise ValueError(
            "priority must be one of: high, medium, low"
        )

    if not 0.0 <= request.decision_value <= 1.0:
        raise ValueError(
            "decision_value must be between 0.0 and 1.0"
        )

    if not 0.0 <= request.expected_cost <= 1.0:
        raise ValueError(
            "expected_cost must be between 0.0 and 1.0"
        )

    if request.expected_time_minutes < 0:
        raise ValueError(
            "expected_time_minutes must not be negative"
        )


def create_evidence_request(
    *,
    request_id: str,
    incident_id: str,
    decision_id: str,
    evidence_id: str,
    evidence_type: str,
    purpose: str,
    priority: str,
    decision_value: float,
    expected_cost: float,
    expected_time_minutes: int,
    assigned_actor_id: str | None = None,
    created_at: datetime | None = None,
) -> EvidenceRequest:
    request = EvidenceRequest(
        request_id=request_id,
        incident_id=incident_id,
        decision_id=decision_id,
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        purpose=purpose,
        priority=priority,
        decision_value=decision_value,
        expected_cost=expected_cost,
        expected_time_minutes=expected_time_minutes,
        status=EvidenceRequestStatus.DRAFT,
        assigned_actor_id=assigned_actor_id,
        created_at=created_at,
    )

    _validate_request(request)

    return request


def transition_evidence_request(
    request: EvidenceRequest,
    next_status: EvidenceRequestStatus,
) -> EvidenceRequest:
    _validate_request(request)

    expected_next = _ALLOWED_TRANSITIONS.get(request.status)

    if expected_next is None:
        raise ValueError(
            f"Evidence request is already terminal at status "
            f"'{request.status.value}'."
        )

    if next_status != expected_next:
        raise ValueError(
            f"Invalid evidence request transition: "
            f"'{request.status.value}' -> '{next_status.value}'. "
            f"Expected '{expected_next.value}'."
        )

    transitioned_at = datetime.now()

    transition = EvidenceRequestTransition(
        from_status=request.status,
        to_status=next_status,
        transitioned_at=transitioned_at,
    )

    return EvidenceRequest(
        request_id=request.request_id,
        incident_id=request.incident_id,
        decision_id=request.decision_id,
        evidence_id=request.evidence_id,
        evidence_type=request.evidence_type,
        purpose=request.purpose,
        priority=request.priority,
        decision_value=request.decision_value,
        expected_cost=request.expected_cost,
        expected_time_minutes=request.expected_time_minutes,
        status=next_status,
        assigned_actor_id=request.assigned_actor_id,
        created_at=request.created_at,
        transition_history=(
            *request.transition_history,
            transition,
        ),
    )