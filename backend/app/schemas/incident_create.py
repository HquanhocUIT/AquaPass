"""Fields a human may provide when opening a new incident."""

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class IncidentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=3)
    incident_type: str = Field(min_length=2, max_length=80)
    location_name: str = Field(min_length=2, max_length=200)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    occurred_at: AwareDatetime
