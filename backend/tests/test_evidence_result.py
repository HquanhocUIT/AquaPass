from datetime import datetime

import pytest

from app.modules.orchestration.evidence_result import (
    EvidenceResultStatus,
    create_evidence_result,
)


def _create_result():
    return create_evidence_result(
        result_id="RES-001",
        request_id="REQ-001",
        incident_id="INC-FISH-001",
        decision_id="DEC-FISH-001",
        evidence_id="EV-005",
        evidence_type="water_quality",
        value="dissolved_oxygen=3.1",
        source="Demo Sensor",
        reliability=0.92,
        collected_at=datetime(2026, 9, 18, 10, 0),
    )


def test_create_evidence_result():
    result = _create_result()

    assert result.result_id == "RES-001"
    assert result.request_id == "REQ-001"
    assert result.incident_id == "INC-FISH-001"
    assert result.decision_id == "DEC-FISH-001"
    assert result.status == EvidenceResultStatus.DRAFT


@pytest.mark.parametrize(
    "field",
    [
        "result_id",
        "request_id",
        "incident_id",
        "decision_id",
        "evidence_id",
        "evidence_type",
        "value",
        "source",
    ],
)
def test_required_fields_are_validated(field):
    kwargs = {
        "result_id": "RES-001",
        "request_id": "REQ-001",
        "incident_id": "INC-FISH-001",
        "decision_id": "DEC-FISH-001",
        "evidence_id": "EV-005",
        "evidence_type": "water_quality",
        "value": "dissolved_oxygen=3.1",
        "source": "Demo Sensor",
        "reliability": 0.92,
        "collected_at": datetime(2026, 9, 18, 10, 0),
    }

    kwargs[field] = ""

    with pytest.raises(
        ValueError,
        match=f"{field} must not be empty",
    ):
        create_evidence_result(**kwargs)


@pytest.mark.parametrize(
    "reliability",
    [-0.1, 1.1],
)
def test_reliability_is_validated(reliability):
    with pytest.raises(
        ValueError,
        match="reliability must be between 0.0 and 1.0",
    ):
        create_evidence_result(
            result_id="RES-001",
            request_id="REQ-001",
            incident_id="INC-FISH-001",
            decision_id="DEC-FISH-001",
            evidence_id="EV-005",
            evidence_type="water_quality",
            value="dissolved_oxygen=3.1",
            source="Demo Sensor",
            reliability=reliability,
            collected_at=datetime(2026, 9, 18, 10, 0),
        )