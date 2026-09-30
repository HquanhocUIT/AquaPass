from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, model_validator

from app.schemas.evidence import EvidenceGraphRecordRequest
from app.schemas.intelligence import EvidenceCandidateRequest, RankEvidenceResponse


RequestPriority = Literal["ROUTINE", "URGENT", "ASAP", "STAT"]
RequestStatus = Literal[
    "DRAFT",
    "REQUESTED",
    "ACCEPTED",
    "COLLECTING",
    "SUBMITTED",
    "VERIFIED",
    "INGESTED",
    "DECISION_UPDATED",
    "REJECTED",
]


class EvidenceRequestCreateRequest(BaseModel):
    incident_id: UUID
    decision_id: UUID
    evidence_gap_id: UUID | None = None
    assigned_actor_id: UUID | None = None
    requested_evidence_code: str = Field(min_length=1, max_length=80)
    purpose: str = Field(min_length=1)
    priority: RequestPriority = "ROUTINE"
    estimated_cost: float | None = Field(default=None, ge=0.0)
    estimated_minutes: int | None = Field(default=None, ge=0)
    requested_by: str = Field(default="system", min_length=1, max_length=120)


class RequestStatusTransitionRequest(BaseModel):
    to_status: RequestStatus
    actor_name: str = Field(min_length=1, max_length=120)
    note: str | None = None


class RequestStatusEventResponse(BaseModel):
    id: UUID
    request_id: UUID
    from_status: str | None
    to_status: str
    actor_name: str
    note: str | None
    occurred_at: datetime


class EvidenceRequestAttachmentResponse(BaseModel):
    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    created_at: datetime


class EvidenceRequestResponse(BaseModel):
    id: UUID
    incident_id: UUID
    decision_id: UUID
    evidence_gap_id: UUID | None
    assigned_actor_id: UUID | None
    result_evidence_id: UUID | None
    requested_evidence_code: str
    purpose: str
    priority: str
    status: str
    estimated_cost: float | None
    estimated_minutes: int | None
    requested_by: str
    created_at: datetime
    updated_at: datetime
    status_events: list[RequestStatusEventResponse] = Field(default_factory=list)
    attachments: list[EvidenceRequestAttachmentResponse] = Field(default_factory=list)


class ActorCapacityRequest(BaseModel):
    actor_id: str = Field(min_length=1)
    actor_name: str = Field(min_length=1)
    actor_type: str = Field(min_length=1)
    capability: str = Field(min_length=1)
    location: str = Field(min_length=1)
    status: Literal["available", "busy", "full"]
    available_from: AwareDatetime
    available_until: AwareDatetime
    max_concurrent_tasks: int = Field(ge=0)
    expected_delay_minutes: int = Field(ge=0)


class ActorAssignmentRequest(BaseModel):
    evidence_id: str = Field(min_length=1)
    required_capability: str = Field(min_length=1)
    required_location: str | None = None
    decision_deadline: AwareDatetime
    actors: list[ActorCapacityRequest] = Field(min_length=1)


class ActorAssignmentResponse(BaseModel):
    evidence_id: str
    actor_id: str | None
    actor_name: str | None
    feasible: bool
    location: str | None
    expected_delay_minutes: int | None
    reasons: list[str]


class DecisionApprovalRequest(BaseModel):
    action: Literal["APPROVE", "REJECT"]
    reviewer_id: str = Field(min_length=1, max_length=120)
    reason: str | None = None

    @model_validator(mode="after")
    def require_rejection_reason(self) -> "DecisionApprovalRequest":
        if self.action == "REJECT" and not self.reason:
            raise ValueError("reason is required when rejecting a decision")
        return self


class DecisionApprovalResponse(BaseModel):
    decision_id: UUID
    version_number: int
    status: Literal["APPROVED", "REJECTED"]
    reviewer_id: str
    reason: str | None


class AuditEventResponse(BaseModel):
    id: UUID
    incident_id: UUID | None
    entity_type: str
    entity_id: UUID
    event_type: str
    actor_name: str
    payload: dict[str, Any]
    created_at: datetime


class ObservationIngestResponse(BaseModel):
    observation_id: str
    evidence_id: UUID
    incident_id: UUID
    request_id: UUID
    decision_id: UUID
    request_status: str
    decision_version: int
    uncertainty_level: str
    value: str
    hypothesis_updates: list[dict[str, Any]] = Field(default_factory=list)


class IntelligenceOverviewRequest(BaseModel):
    records: list[EvidenceGraphRecordRequest] = Field(min_length=1)
    candidates: list[EvidenceCandidateRequest] = Field(min_length=1)


class IntelligenceStateResponse(BaseModel):
    evidence_id: str
    state: str
    reason: str


class IntelligenceOverviewResponse(BaseModel):
    graph: list[dict[str, Any]]
    states: list[IntelligenceStateResponse]
    gaps: list[dict[str, Any]]
    ranking: RankEvidenceResponse
    profiles: list[dict[str, Any]] = Field(default_factory=list)
    hypotheses: list[dict[str, Any]] = Field(default_factory=list)
    actors: list[dict[str, Any]] = Field(default_factory=list)
