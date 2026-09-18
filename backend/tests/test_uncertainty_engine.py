import pytest

from app.modules.decision.uncertainty_engine import (
    DecisionEvidence,
    calculate_uncertainty,
    classify_uncertainty,
    evaluate_uncertainty,
)


def make_evidence(**overrides):
    data = {
        "evidence_id": "EV-001",
        "state": "available",
        "reliability": 0.90,
        "supports_decision": True,
    }

    data.update(overrides)

    return DecisionEvidence(**data)


def test_available_evidence_reduces_uncertainty():
    score = calculate_uncertainty(
        [
            make_evidence(
                reliability=0.90,
            )
        ]
    )

    assert score == pytest.approx(0.10)


def test_missing_evidence_creates_high_uncertainty():
    score = calculate_uncertainty(
        [
            make_evidence(
                state="missing",
                reliability=0.90,
            )
        ]
    )

    assert score == pytest.approx(1.0)
    assert classify_uncertainty(score) == "HIGH"


def test_conflicting_evidence_has_partial_contribution():
    score = calculate_uncertainty(
        [
            make_evidence(
                state="conflicting",
                reliability=0.80,
            )
        ]
    )

    assert score == pytest.approx(0.80)


def test_stale_evidence_has_limited_contribution():
    score = calculate_uncertainty(
        [
            make_evidence(
                state="stale",
                reliability=0.80,
            )
        ]
    )

    assert score == pytest.approx(0.80)


def test_unreliable_evidence_has_very_low_contribution():
    score = calculate_uncertainty(
        [
            make_evidence(
                state="unreliable",
                reliability=0.80,
            )
        ]
    )

    assert score == pytest.approx(0.92)


def test_non_supporting_evidence_does_not_reduce_uncertainty():
    score = calculate_uncertainty(
        [
            make_evidence(
                reliability=0.95,
                supports_decision=False,
            )
        ]
    )

    assert score == pytest.approx(1.0)


def test_uncertainty_levels():
    assert classify_uncertainty(0.80) == "HIGH"
    assert classify_uncertainty(0.55) == "MEDIUM"
    assert classify_uncertainty(0.20) == "LOW"


def test_empty_evidence_means_high_uncertainty():
    score = calculate_uncertainty([])

    assert score == 1.0
    assert classify_uncertainty(score) == "HIGH"


def test_invalid_reliability_is_rejected():
    with pytest.raises(ValueError):
        calculate_uncertainty(
            [
                make_evidence(
                    reliability=1.5,
                )
            ]
        )


def test_invalid_state_is_rejected():
    with pytest.raises(ValueError):
        calculate_uncertainty(
            [
                make_evidence(
                    state="unknown-state",
                )
            ]
        )


def test_empty_evidence_id_is_rejected():
    with pytest.raises(ValueError):
        calculate_uncertainty(
            [
                make_evidence(
                    evidence_id="",
                )
            ]
        )


def test_new_evidence_reduces_uncertainty():
    before = evaluate_uncertainty(
        [
            make_evidence(
                evidence_id="EV-001",
                state="available",
                reliability=0.90,
            ),
            make_evidence(
                evidence_id="EV-002",
                state="missing",
                reliability=0.90,
            ),
        ]
    )

    after = evaluate_uncertainty(
        [
            make_evidence(
                evidence_id="EV-001",
                state="available",
                reliability=0.90,
            ),
            make_evidence(
                evidence_id="EV-002",
                state="available",
                reliability=0.95,
            ),
        ],
        previous_score=before.score,
        previous_level=before.level,
    )

    assert after.score < before.score
    assert after.previous_score == before.score
    assert after.previous_level == before.level
    assert "decreased" in after.explanation


def test_results_are_deterministic():
    evidence = [
        make_evidence(
            evidence_id="EV-002",
            reliability=0.80,
        ),
        make_evidence(
            evidence_id="EV-001",
            reliability=0.90,
        ),
    ]

    first = evaluate_uncertainty(evidence)
    second = evaluate_uncertainty(evidence)

    assert first == second