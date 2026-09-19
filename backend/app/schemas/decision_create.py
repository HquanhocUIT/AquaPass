"""Decision request and response contracts."""

from datetime import datetime, timezone
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


class DecisionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(min_length=1)
    deadline: AwareDatetime

    @field_validator("deadline")
    @classmethod
    def deadline_must_be_future(cls, value: datetime) -> datetime:
        if value <= datetime.now(timezone.utc):
            raise ValueError("deadline must be in the future")
        return value


class DecisionVersionResponse(BaseModel):
    id: UUID
    decision_id: UUID
    version_number: int
    summary: str
    uncertainty_level: str
    evidence_snapshot: dict[str, list[str]]
    approval_status: str
    created_by: str
    approved_by: str | None
    created_at: datetime


class DecisionCreateResponse(BaseModel):
    id: UUID
    incident_id: UUID
    question: str
    deadline: datetime
    status: str
    current_version: int
    created_at: datetime
    updated_at: datetime
    version: DecisionVersionResponse


class DecisionDetailResponse(BaseModel):
    id: UUID
    incident_id: UUID
    question: str
    deadline: datetime
    status: str
    current_version: int
    created_at: datetime
    updated_at: datetime
    versions: list[DecisionVersionResponse]
