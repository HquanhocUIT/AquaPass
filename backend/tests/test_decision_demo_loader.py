from app.modules.decision.decision_store import DecisionStore
from app.modules.decision.demo_loader import load_demo_decision


def test_load_demo_decision():
    store = DecisionStore()

    load_demo_decision(store)

    decision = store.get_latest(
        "DEC-FISH-001"
    )

    assert decision.decision_id == "DEC-FISH-001"
    assert decision.version == 1
    assert decision.incident_id == "INC-FISH-001"
    assert decision.uncertainty == 0.70
    assert decision.uncertainty_level == "high"
    assert (
        decision.triggering_evidence_id
        is None
    )