from __future__ import annotations

from pydantic import BaseModel, Field


class EvidenceGraphRecordRequest(BaseModel):
    graph_id: str = Field(min_length=1)
    incident_id: str = Field(min_length=1)
    decision_id: str = Field(min_length=1)

    source_node: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    relationship: str = Field(min_length=1)

    target_node: str = Field(min_length=1)
    target_type: str = Field(min_length=1)

    confidence: float = Field(ge=0.0, le=1.0)

    state: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class DetectEvidenceGapsRequest(BaseModel):
    records: list[EvidenceGraphRecordRequest] = Field(
        min_length=1
    )


class EvidenceGapResponse(BaseModel):
    incident_id: str
    decision_id: str
    evidence_id: str
    priority: str
    reason: str


class DetectEvidenceGapsResponse(BaseModel):
    gaps: list[EvidenceGapResponse]