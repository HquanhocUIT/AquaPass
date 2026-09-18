from app.modules.decision.evidence_outcome import (
    evaluate_evidence_outcome,
)
from app.modules.ranking.ranking_engine import (
    EvidenceCandidate,
    rank_evidence,
)


def make_candidate(**overrides):
    data = {
        "evidence_id": "EV-001",
        "candidate_name": "Field dissolved oxygen measurement",
        "decision_value": 0.90,
        "reliability": 0.90,
        "feasibility": 0.90,
        "cost": 0.10,
        "time": 0.10,
    }

    data.update(overrides)

    return EvidenceCandidate(**data)


def rank_candidates(candidates):
    return rank_evidence(candidates)


def test_collect_additional_evidence_when_candidate_is_actionable():
    ranked = rank_candidates(
        [
            make_candidate(
                evidence_id="EV-001",
                decision_value=0.90,
            )
        ]
    )

    outcome = evaluate_evidence_outcome(ranked)

    assert outcome.recommendation == "collect_additional_evidence"
    assert outcome.recommended_evidence_id == "EV-001"
    assert outcome.considered_candidates == 1


def test_no_additional_evidence_when_all_candidates_are_low_value():
    ranked = rank_candidates(
        [
            make_candidate(
                evidence_id="EV-001",
                decision_value=0.10,
                reliability=0.20,
                feasibility=0.20,
                cost=0.80,
                time=0.80,
            ),
            make_candidate(
                evidence_id="EV-002",
                decision_value=0.15,
                reliability=0.20,
                feasibility=0.20,
                cost=0.80,
                time=0.80,
            ),
            make_candidate(
                evidence_id="EV-003",
                decision_value=0.20,
                reliability=0.30,
                feasibility=0.20,
                cost=0.80,
                time=0.80,
            ),
        ]
    )

    outcome = evaluate_evidence_outcome(ranked)

    assert outcome.recommendation == "no_additional_evidence"
    assert outcome.recommended_evidence_id is None
    assert outcome.considered_candidates == 3


def test_candidate_with_high_score_but_low_decision_value_is_rejected():
    ranked = rank_candidates(
        [
            make_candidate(
                evidence_id="EV-001",
                decision_value=0.20,
                reliability=1.00,
                feasibility=1.00,
                cost=0.00,
                time=0.00,
            )
        ]
    )

    outcome = evaluate_evidence_outcome(ranked)

    assert outcome.recommendation == "no_additional_evidence"
    assert outcome.recommended_evidence_id is None


def test_candidate_with_high_decision_value_but_low_score_is_rejected():
    ranked = rank_candidates(
        [
            make_candidate(
                evidence_id="EV-001",
                decision_value=0.90,
                reliability=0.00,
                feasibility=0.00,
                cost=1.00,
                time=1.00,
            )
        ]
    )

    outcome = evaluate_evidence_outcome(ranked)

    assert outcome.recommendation == "no_additional_evidence"
    assert outcome.recommended_evidence_id is None


def test_custom_thresholds_are_explicit():
    ranked = rank_candidates(
        [
            make_candidate(
                evidence_id="EV-001",
                decision_value=0.50,
            )
        ]
    )

    outcome = evaluate_evidence_outcome(
        ranked,
        min_decision_value=0.60,
        min_score=0.30,
    )

    assert outcome.recommendation == "no_additional_evidence"


def test_invalid_decision_value_threshold_is_rejected():
    ranked = rank_candidates([make_candidate()])

    try:
        evaluate_evidence_outcome(
            ranked,
            min_decision_value=1.5,
        )
    except ValueError:
        return

    raise AssertionError("Expected ValueError")


def test_invalid_score_threshold_is_rejected():
    ranked = rank_candidates([make_candidate()])

    try:
        evaluate_evidence_outcome(
            ranked,
            min_score=1.5,
        )
    except ValueError:
        return

    raise AssertionError("Expected ValueError")


def test_empty_candidates_return_no_additional_evidence():
    outcome = evaluate_evidence_outcome([])

    assert outcome.recommendation == "no_additional_evidence"
    assert outcome.recommended_evidence_id is None
    assert outcome.considered_candidates == 0


def test_result_is_deterministic():
    ranked = rank_candidates(
        [
            make_candidate(
                evidence_id="EV-002",
                decision_value=0.50,
            ),
            make_candidate(
                evidence_id="EV-001",
                decision_value=0.50,
            ),
        ]
    )

    first = evaluate_evidence_outcome(ranked)
    second = evaluate_evidence_outcome(ranked)

    assert first == second