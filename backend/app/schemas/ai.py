from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.evidence import DetectEvidenceGapsRequest
from app.schemas.intelligence import RankEvidenceRequest


AiProvider = Literal["gemini", "deterministic_fallback"]


class AiEvidenceGapResponse(BaseModel):
    gap_id: str
    incident_id: str
    decision_id: str
    evidence_id: str
    evidence_type: str
    target_hypothesis: str
    reason: str
    decision_impact: str
    priority: str


class AiEvidenceGapsRequest(DetectEvidenceGapsRequest):
    """Evidence graph input for grounded Gemini gap suggestions."""


class AiEvidenceGapsResponse(BaseModel):
    provider: AiProvider
    model: str | None = None
    fallback_reason: str | None = None
    gaps: list[AiEvidenceGapResponse] = Field(default_factory=list)


class AiRankingExplanationRequest(RankEvidenceRequest):
    """Candidate input for grounded Gemini ranking explanations."""


class AiRankingExplanationItem(BaseModel):
    evidence_id: str
    candidate_name: str
    rank: int
    score: float
    selected: bool
    explanation: str
    strengths: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)


class AiRankingExplanationResponse(BaseModel):
    provider: AiProvider
    model: str | None = None
    fallback_reason: str | None = None
    results: list[AiRankingExplanationItem] = Field(default_factory=list)
