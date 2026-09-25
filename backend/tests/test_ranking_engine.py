import pytest

from app.modules.ranking.ranking_engine import (
    DEFAULT_WEIGHTS,
    EvidenceCandidate,
    RankingWeights,
    calculate_score,
    rank_evidence,
)


def make_candidate(**overrides):
    data = {
        "evidence_id": "EV-005",
        "candidate_name": "Independent field dissolved oxygen measurement",
        "decision_value": 0.95,
        "reliability": 0.90,
        "feasibility": 0.90,
        "cost": 0.20,
        "time": 0.15,
    }

    data.update(overrides)

    return EvidenceCandidate(**data)


def test_calculate_score():
    candidate = make_candidate()

    score = calculate_score(candidate)

    assert score == pytest.approx(0.705)


def test_gold_set_order():
    candidates = [
        make_candidate(
            evidence_id="EV-005",
            candidate_name="Independent field dissolved oxygen measurement",
            decision_value=0.95,
            reliability=0.90,
            feasibility=0.90,
            cost=0.20,
            time=0.15,
        ),
        make_candidate(
            evidence_id="EV-006",
            candidate_name="Laboratory water chemistry testing",
            decision_value=0.85,
            reliability=0.95,
            feasibility=0.55,
            cost=0.65,
            time=0.70,
        ),
        make_candidate(
            evidence_id="EV-007",
            candidate_name="Additional citizen verification",
            decision_value=0.45,
            reliability=0.60,
            feasibility=0.85,
            cost=0.10,
            time=0.10,
        ),
    ]

    ranked = rank_evidence(candidates)

    assert [item.evidence_id for item in ranked] == [
        "EV-005",
        "EV-006",
        "EV-007",
    ]

    assert [item.rank for item in ranked] == [1, 2, 3]


def test_highest_rank_is_selected():
    ranked = rank_evidence(
        [
            make_candidate(evidence_id="EV-001"),
            make_candidate(
                evidence_id="EV-002",
                decision_value=0.50,
                reliability=0.50,
                feasibility=0.50,
                cost=0.20,
                time=0.20,
            ),
        ]
    )

    assert ranked[0].selected is True
    assert ranked[1].selected is False


def test_cost_and_time_reduce_score():
    cheap_fast = make_candidate(
        evidence_id="EV-001",
        cost=0.10,
        time=0.10,
    )

    expensive_slow = make_candidate(
        evidence_id="EV-002",
        cost=0.90,
        time=0.90,
    )

    assert calculate_score(cheap_fast) > calculate_score(expensive_slow)


def test_invalid_dimension_is_rejected():
    candidate = make_candidate(decision_value=1.5)

    with pytest.raises(ValueError):
        calculate_score(candidate)


def test_empty_evidence_id_is_rejected():
    candidate = make_candidate(evidence_id="")

    with pytest.raises(ValueError):
        calculate_score(candidate)


def test_custom_weights_are_explicit():
    weights = RankingWeights(
        decision_value=1.0,
        reliability=0.0,
        feasibility=0.0,
        cost_penalty=0.0,
        time_penalty=0.0,
    )

    candidate = make_candidate(decision_value=0.80)

    assert calculate_score(
        candidate,
        weights=weights,
    ) == pytest.approx(0.80)


def test_infeasible_candidate_is_excluded():
    feasible = make_candidate(
        evidence_id="EV-001",
        decision_value=0.60,
    )

    infeasible = make_candidate(
        evidence_id="EV-002",
        decision_value=0.99,
        is_feasible=False,
        infeasibility_reason="No field team is available.",
    )

    ranked = rank_evidence([infeasible, feasible])

    assert [item.evidence_id for item in ranked] == ["EV-001"]


def test_results_are_deterministic():
    candidates = [
        make_candidate(
            evidence_id="EV-003",
            decision_value=0.50,
        ),
        make_candidate(
            evidence_id="EV-001",
            decision_value=0.50,
        ),
        make_candidate(
            evidence_id="EV-002",
            decision_value=0.50,
        ),
    ]

    first = rank_evidence(candidates)
    second = rank_evidence(candidates)

    assert first == second
    assert [item.evidence_id for item in first] == [
        "EV-001",
        "EV-002",
        "EV-003",
    ]


def test_explanation_contains_score_dimensions():
    ranked = rank_evidence([make_candidate()])

    explanation = ranked[0].explanation

    assert "decision value" in explanation
    assert "reliability" in explanation
    assert "feasibility" in explanation
    assert "cost" in explanation
    assert "time" in explanation
    assert "Prototype score" in explanation


def test_explanation_identifies_strengths_and_tradeoffs():
    ranked = rank_evidence(
        [
            make_candidate(
                decision_value=0.95,
                reliability=0.90,
                feasibility=0.90,
                cost=0.20,
                time=0.15,
            ),
        ]
    )

    result = ranked[0]

    assert "very high decision value" in result.strengths
    assert "very high reliability" in result.strengths
    assert "high feasibility" in result.strengths
    assert "low acquisition burden" in result.strengths
    assert "fast turnaround" in result.strengths


def test_explanation_identifies_expensive_slow_tradeoffs():
    ranked = rank_evidence(
        [
            make_candidate(
                evidence_id="EV-006",
                decision_value=0.85,
                reliability=0.95,
                feasibility=0.55,
                cost=0.65,
                time=0.70,
            ),
        ]
    )

    result = ranked[0]

    assert "high acquisition burden" in result.tradeoffs
    assert "slow turnaround" in result.tradeoffs


def test_explanation_is_deterministic():
    candidate = make_candidate()

    first = rank_evidence([candidate])
    second = rank_evidence([candidate])

    assert first[0].explanation == second[0].explanation
    assert first[0].strengths == second[0].strengths
    assert first[0].tradeoffs == second[0].tradeoffs