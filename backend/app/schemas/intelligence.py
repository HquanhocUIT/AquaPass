from __future__ import annotations

from pydantic import BaseModel, Field


class EvidenceCandidateRequest(BaseModel):
    evidence_id: str = Field(min_length=1)
    candidate_name: str = Field(min_length=1)
    decision_value: float = Field(ge=0.0, le=1.0)
    reliability: float = Field(ge=0.0, le=1.0)
    feasibility: float = Field(ge=0.0, le=1.0)
    cost: float = Field(ge=0.0, le=1.0)
    time: float = Field(ge=0.0, le=1.0)
    is_feasible: bool = True
    infeasibility_reason: str | None = None


class RankEvidenceRequest(BaseModel):
    candidates: list[EvidenceCandidateRequest] = Field(min_length=1)


class RankedEvidenceResponse(BaseModel):
    evidence_id: str
    candidate_name: str
    score: float
    rank: int
    decision_value: float
    reliability: float
    feasibility: float
    cost: float
    time: float
    explanation: str
    strengths: list[str]
    tradeoffs: list[str]
    selected: bool


class RankEvidenceResponse(BaseModel):
    results: list[RankedEvidenceResponse]