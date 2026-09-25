from __future__ import annotations

from pydantic import BaseModel


class DecisionVersionResponse(BaseModel):
    decision_id: str
    version: int
    incident_id: str
    uncertainty: float
    uncertainty_level: str
    hypothesis_summary: str
    triggering_evidence_id: str | None


class DecisionComparisonResponse(BaseModel):
    decision_id: str
    from_version: int
    to_version: int
    triggering_evidence_id: str | None
    uncertainty_before: float
    uncertainty_after: float
    uncertainty_change: float
    hypothesis_changed: bool