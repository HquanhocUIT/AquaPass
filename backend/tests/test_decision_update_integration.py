from app.modules.decision.decision_store import (
    DecisionStore,
)
from app.modules.decision.decision_updater import (
    create_updated_decision,
)
from app.modules.decision.decision_version import (
    create_decision_version,
)
from app.modules.decision.decision_comparison import (
    compare_decision_versions,
)


def test_decision_update_is_stored_and_comparable():
    v1 = create_decision_version(
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

    store = DecisionStore([v1])

    v2 = create_updated_decision(
        store.get_latest("DEC-FISH-001"),
        uncertainty=0.45,
        uncertainty_level="medium",
        hypothesis_summary=(
            "Low dissolved oxygen is increasingly supported."
        ),
        triggering_evidence_id="EV-005",
    )

    store.add(v2)

    latest = store.get_latest("DEC-FISH-001")

    assert latest.version == 2
    assert latest.uncertainty == 0.45
    assert latest.triggering_evidence_id == "EV-005"

    versions = store.get_versions("DEC-FISH-001")

    assert [item.version for item in versions] == [1, 2]

    comparison = compare_decision_versions(
        versions[0],
        versions[1],
    )

    assert comparison.from_version == 1
    assert comparison.to_version == 2
    assert comparison.uncertainty_before == 0.70
    assert comparison.uncertainty_after == 0.45
    assert comparison.uncertainty_change == 0.25
    assert comparison.triggering_evidence_id == "EV-005"
    assert comparison.hypothesis_changed is True