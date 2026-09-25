import pytest

from app.modules.decision.decision_updater import (
    create_updated_decision,
)
from app.modules.decision.decision_version import (
    create_decision_version,
)


def _create_v1():
    return create_decision_version(
        decision_id="DEC-FISH-001",
        version=1,
        incident_id="INC-FISH-001",
        uncertainty=0.70,
        uncertainty_level="high",
        hypothesis_summary=(
            "Low dissolved oxygen may be contributing "
            "to fish mortality."
        ),
    )


def test_create_updated_decision_creates_next_version():
    previous = _create_v1()

    updated = create_updated_decision(
        previous,
        uncertainty=0.45,
        uncertainty_level="medium",
        hypothesis_summary=(
            "Low dissolved oxygen is increasingly supported."
        ),
        triggering_evidence_id="EV-005",
    )

    assert updated.decision_id == "DEC-FISH-001"
    assert updated.version == 2
    assert updated.incident_id == "INC-FISH-001"
    assert updated.uncertainty == 0.45
    assert updated.uncertainty_level == "medium"
    assert updated.triggering_evidence_id == "EV-005"


def test_create_updated_decision_does_not_mutate_previous():
    previous = _create_v1()

    updated = create_updated_decision(
        previous,
        uncertainty=0.45,
        uncertainty_level="medium",
        hypothesis_summary=(
            "Low dissolved oxygen is increasingly supported."
        ),
        triggering_evidence_id="EV-005",
    )

    assert previous.version == 1
    assert previous.uncertainty == 0.70
    assert previous.triggering_evidence_id is None

    assert updated.version == 2


def test_create_updated_decision_requires_triggering_evidence():
    previous = _create_v1()

    with pytest.raises(
        ValueError,
        match="triggering_evidence_id must not be empty",
    ):
        create_updated_decision(
            previous,
            uncertainty=0.45,
            uncertainty_level="medium",
            hypothesis_summary=(
                "Low dissolved oxygen is increasingly supported."
            ),
            triggering_evidence_id="",
        )