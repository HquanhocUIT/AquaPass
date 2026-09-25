import pytest

from app.modules.decision.decision_store import (
    DecisionStore,
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


def _create_v2():
    return create_decision_version(
        decision_id="DEC-FISH-001",
        version=2,
        incident_id="INC-FISH-001",
        uncertainty=0.45,
        uncertainty_level="medium",
        hypothesis_summary=(
            "Low dissolved oxygen is increasingly supported."
        ),
        triggering_evidence_id="EV-005",
    )


def test_store_returns_latest_version():
    store = DecisionStore(
        [_create_v1(), _create_v2()]
    )

    latest = store.get_latest(
        "DEC-FISH-001"
    )

    assert latest.version == 2
    assert latest.uncertainty == 0.45
    assert latest.triggering_evidence_id == "EV-005"


def test_store_returns_versions_in_order():
    store = DecisionStore(
        [_create_v2(), _create_v1()]
    )

    versions = store.get_versions(
        "DEC-FISH-001"
    )

    assert [item.version for item in versions] == [1, 2]


def test_store_rejects_duplicate_version():
    v1 = _create_v1()

    store = DecisionStore([v1])

    with pytest.raises(
        ValueError,
        match="already exists",
    ):
        store.add(v1)


def test_store_raises_for_unknown_decision():
    store = DecisionStore()

    with pytest.raises(
        KeyError,
        match="Decision not found",
    ):
        store.get_latest("UNKNOWN")


def test_store_raises_for_unknown_versions():
    store = DecisionStore()

    with pytest.raises(
        KeyError,
        match="Decision not found",
    ):
        store.get_versions("UNKNOWN")