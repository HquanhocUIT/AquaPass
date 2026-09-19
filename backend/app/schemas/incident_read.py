"""Public response contract for the first read-only incident endpoint."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class EvidenceResponse(BaseModel):
    id: UUID
    incident_id: UUID
    code: str
    evidence_type: str
    state: str
    value_numeric: float | None
    value_text: str | None
    unit: str | None
    source: str
    observed_at: datetime
    reliability_score: float
    provenance: dict
    is_simulated: bool


class DecisionResponse(BaseModel):
    id: UUID
    incident_id: UUID
    question: str
    deadline: datetime
    status: str
    current_version: int


class IncidentResponse(BaseModel):
    id: UUID
    title: str
    description: str
    incident_type: str
    location_name: str
    latitude: float | None
    longitude: float | None
    severity: str
    status: str
    occurred_at: datetime
    created_at: datetime
    updated_at: datetime


class IncidentDetailResponse(IncidentResponse):
    evidence: list[EvidenceResponse]
    decisions: list[DecisionResponse]
