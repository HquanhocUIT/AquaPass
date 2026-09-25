from app.modules.decision.hypothesis_engine import (
    EvidenceImpact,
    Hypothesis,
    update_hypotheses,
)
from app.modules.decision.uncertainty_engine import (
    DecisionEvidence,
    evaluate_uncertainty,
)


def test_new_evidence_updates_hypothesis_and_uncertainty():
    hypotheses = [
        Hypothesis(
            hypothesis_id="HYP-LOW-DO",
            name="Low DO contributes to fish mortality",
            status="unchanged",
        )
    ]

    impacts = [
        EvidenceImpact(
            evidence_id="EV-005",
            hypothesis_id="HYP-LOW-DO",
            direction="supports",
            rationale=(
                "Direct dissolved oxygen measurement supports "
                "the low-DO hypothesis."
            ),
        )
    ]

    updated = update_hypotheses(
        hypotheses,
        impacts,
    )

    assert len(updated) == 1

    hypothesis = updated[0]

    assert hypothesis.hypothesis_id == "HYP-LOW-DO"
    assert hypothesis.previous_status == "unchanged"
    assert hypothesis.new_status == "stronger"
    assert hypothesis.triggering_evidence_id == "EV-005"


    evidence = [
        DecisionEvidence(
            evidence_id="EV-001",
            state="available",
            reliability=0.80,
        ),
        DecisionEvidence(
            evidence_id="EV-005",
            state="available",
            reliability=0.92,
        ),
    ]

    uncertainty = evaluate_uncertainty(
        evidence,
        previous_score=0.60,
        previous_level="MEDIUM",
    )

    assert uncertainty.score < 0.60
    assert uncertainty.previous_score == 0.60
    assert uncertainty.previous_level == "MEDIUM"
    assert uncertainty.level in {"LOW", "MEDIUM"}