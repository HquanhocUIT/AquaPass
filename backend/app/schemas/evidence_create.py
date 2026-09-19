"""Fields accepted when a human submits prototype evidence."""

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class EvidenceCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    code: str = Field(min_length=2, max_length=80)
    evidence_type: str = Field(min_length=2, max_length=80)
    value_numeric: float | None = Field(default=None, allow_inf_nan=False)
    value_text: str | None = Field(default=None, min_length=1)
    unit: str | None = Field(default=None, min_length=1, max_length=40)
    source: str = Field(min_length=2, max_length=200)
    observed_at: AwareDatetime
    provenance: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_one_value_and_numeric_unit(self) -> "EvidenceCreateRequest":
        if (self.value_numeric is None) == (self.value_text is None):
            raise ValueError("Provide exactly one of value_numeric or value_text")
        if self.value_numeric is not None and self.unit is None:
            raise ValueError("unit is required for value_numeric")
        if self.value_text is not None and self.unit is not None:
            raise ValueError("unit is only valid for value_numeric")
        return self
