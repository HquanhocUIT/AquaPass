from datetime import datetime

import pytest

from app.modules.decision.decision_version import (
    create_decision_version,
    create_next_decision_version,
)


def _create_v1():
    return create_decision_version(
        decision_id="DEC-FISH-001",
        version=1,
        incident_id="INC-FISH-001",
        uncertainty=0.80,
        uncertainty_level="high",
        hypothesis_summary="Low dissolved oxygen may be contributing to fish mortality.",
        created_at=datetime(2026, 9, 18, 10, 0),
    )


def test_create_decision_version():
    decision = _create_v1()

    assert decision.decision_id == "DEC-FISH-001"
    assert decision.version == 1
    assert decision.incident_id == "INC-FISH-001"
    assert decision.uncertainty == 0.80
    assert decision.uncertainty_level == "high"


def test_create_next_decision_version():
    v1 = _create_v1()

    v2 = create_next_decision_version(
        v1,
        uncertainty=0.45,
        uncertainty_level="medium",
        hypothesis_summary="Low dissolved oxygen is increasingly supported.",
        triggering_evidence_id="EV-005",
    )

    assert v2.decision_id == "DEC-FISH-001"
    assert v2.version == 2
    assert v2.incident_id == "INC-FISH-001"
    assert v2.triggering_evidence_id == "EV-005"

    assert v1.version == 1
    assert v1.uncertainty == 0.80

    assert v2.uncertainty == 0.45


def test_version_must_start_at_one():
    with pytest.raises(ValueError, match="version"):
        create_decision_version(
            decision_id="DEC-FISH-001",
            version=0,
            incident_id="INC-FISH-001",
            uncertainty=0.5,
            uncertainty_level="medium",
            hypothesis_summary="Test",
        )


@pytest.mark.parametrize(
    "uncertainty",
    [-0.1, 1.1],
)
def test_uncertainty_is_validated(uncertainty):
    with pytest.raises(
        ValueError,
        match="uncertainty must be between",
    ):
        create_decision_version(
            decision_id="DEC-FISH-001",
            version=1,
            incident_id="INC-FISH-001",
            uncertainty=uncertainty,
            uncertainty_level="medium",
            hypothesis_summary="Test",
        )


def test_uncertainty_level_is_validated():
    with pytest.raises(ValueError, match="uncertainty_level"):
        create_decision_version(
            decision_id="DEC-FISH-001",
            version=1,
            incident_id="INC-FISH-001",
            uncertainty=0.5,
            uncertainty_level="unknown",
            hypothesis_summary="Test",
        )


def test_required_ids_are_validated():
    with pytest.raises(ValueError, match="decision_id"):
        create_decision_version(
            decision_id="",
            version=1,
            incident_id="INC-FISH-001",
            uncertainty=0.5,
            uncertainty_level="medium",
            hypothesis_summary="Test",
        )

    with pytest.raises(ValueError, match="incident_id"):
        create_decision_version(
            decision_id="DEC-FISH-001",
            version=1,
            incident_id="",
            uncertainty=0.5,
            uncertainty_level="medium",
            hypothesis_summary="Test",
        )