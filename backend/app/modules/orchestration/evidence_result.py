from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class EvidenceResultStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    INGESTED = "ingested"


@dataclass(frozen=True)
class EvidenceResult:
    result_id: str
    request_id: str
    incident_id: str
    decision_id: str
    evidence_id: str
    evidence_type: str
    value: str
    source: str
    reliability: float
    collected_at: datetime
    status: EvidenceResultStatus = EvidenceResultStatus.DRAFT


def _validate_result(result: EvidenceResult) -> None:
    required_fields = {
        "result_id": result.result_id,
        "request_id": result.request_id,
        "incident_id": result.incident_id,
        "decision_id": result.decision_id,
        "evidence_id": result.evidence_id,
        "evidence_type": result.evidence_type,
        "value": result.value,
        "source": result.source,
    }

    for name, value in required_fields.items():
        if not value:
            raise ValueError(
                f"{name} must not be empty"
            )

    if not 0.0 <= result.reliability <= 1.0:
        raise ValueError(
            "reliability must be between 0.0 and 1.0"
        )


def create_evidence_result(
    *,
    result_id: str,
    request_id: str,
    incident_id: str,
    decision_id: str,
    evidence_id: str,
    evidence_type: str,
    value: str,
    source: str,
    reliability: float,
    collected_at: datetime,
) -> EvidenceResult:

    result = EvidenceResult(
        result_id=result_id,
        request_id=request_id,
        incident_id=incident_id,
        decision_id=decision_id,
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        value=value,
        source=source,
        reliability=reliability,
        collected_at=collected_at,
    )

    _validate_result(result)

    return result