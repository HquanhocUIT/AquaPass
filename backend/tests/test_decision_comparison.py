from app.modules.decision.decision_comparison import (
    compare_decision_versions,
)
from app.modules.decision.decision_version import (
    create_decision_version,
    create_next_decision_version,
)


def test_decision_comparison_shows_before_and_after():
    v1 = create_decision_version(
        decision_id="DEC-FISH-001",
        version=1,
        incident_id="INC-FISH-001",
        uncertainty=0.80,
        uncertainty_level="high",
        hypothesis_summary="Low DO may contribute.",
    )

    v2 = create_next_decision_version(
        v1,
        uncertainty=0.45,
        uncertainty_level="medium",
        hypothesis_summary="Low DO is increasingly supported.",
        triggering_evidence_id="EV-005",
    )

    comparison = compare_decision_versions(v1, v2)

    assert comparison.decision_id == "DEC-FISH-001"
    assert comparison.from_version == 1
    assert comparison.to_version == 2
    assert comparison.triggering_evidence_id == "EV-005"

    assert comparison.uncertainty_before == 0.80
    assert comparison.uncertainty_after == 0.45
    assert comparison.uncertainty_change == 0.35

    assert comparison.hypothesis_changed is True