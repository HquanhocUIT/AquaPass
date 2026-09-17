import pytest

from app.modules.decision.hypothesis_engine import (
    EvidenceImpact,
    Hypothesis,
    update_hypotheses,
)


def make_hypothesis(**overrides):
    data = {
        "hypothesis_id": "H1",
        "name": "Rainfall-related oxygen depletion",
        "status": "unchanged",
    }

    data.update(overrides)

    return Hypothesis(**data)


def make_impact(**overrides):
    data = {
        "evidence_id": "EV-NEW-001",
        "hypothesis_id": "H1",
        "direction": "supports",
        "rationale": "New field evidence is consistent with the hypothesis.",
    }

    data.update(overrides)

    return EvidenceImpact(**data)


def test_supporting_evidence_strengthens_hypothesis():
    results = update_hypotheses(
        [make_hypothesis()],
        [make_impact()],
    )

    assert results[0].previous_status == "unchanged"
    assert results[0].new_status == "stronger"


def test_contradicting_evidence_weakens_hypothesis():
    results = update_hypotheses(
        [make_hypothesis(status="stronger")],
        [
            make_impact(
                direction="contradicts",
                rationale="New evidence conflicts with this hypothesis.",
            )
        ],
    )

    assert results[0].previous_status == "stronger"
    assert results[0].new_status == "weaker"


def test_corroborating_evidence_strengthens_hypothesis():
    results = update_hypotheses(
        [make_hypothesis()],
        [
            make_impact(
                direction="corroborates",
                rationale="Independent evidence corroborates the hypothesis.",
            )
        ],
    )

    assert results[0].new_status == "stronger"


def test_unrelated_hypothesis_remains_unchanged():
    hypotheses = [
        make_hypothesis(
            hypothesis_id="H1",
            name="Rainfall-related oxygen depletion",
        ),
        make_hypothesis(
            hypothesis_id="H2",
            name="Pollution-related stress",
            status="stronger",
        ),
    ]

    impacts = [
        make_impact(
            hypothesis_id="H1",
        )
    ]

    results = update_hypotheses(
        hypotheses,
        impacts,
    )

    h1 = next(
        item for item in results
        if item.hypothesis_id == "H1"
    )

    h2 = next(
        item for item in results
        if item.hypothesis_id == "H2"
    )

    assert h1.new_status == "stronger"
    assert h2.new_status == "stronger"


def test_triggering_evidence_is_preserved():
    results = update_hypotheses(
        [make_hypothesis()],
        [
            make_impact(
                evidence_id="EV-NEW-007",
            )
        ],
    )

    assert results[0].triggering_evidence_id == "EV-NEW-007"


def test_rationale_is_preserved():
    rationale = (
        "Low dissolved oxygen observed after heavy rainfall "
        "supports the rainfall-related hypothesis."
    )

    results = update_hypotheses(
        [make_hypothesis()],
        [
            make_impact(
                rationale=rationale,
            )
        ],
    )

    assert results[0].rationale == rationale


def test_empty_evidence_id_is_rejected():
    with pytest.raises(ValueError):
        update_hypotheses(
            [make_hypothesis()],
            [
                make_impact(
                    evidence_id="",
                )
            ],
        )


def test_empty_hypothesis_id_is_rejected():
    with pytest.raises(ValueError):
        update_hypotheses(
            [
                make_hypothesis(
                    hypothesis_id="",
                )
            ],
            [],
        )


def test_invalid_direction_is_rejected():
    with pytest.raises(ValueError):
        update_hypotheses(
            [make_hypothesis()],
            [
                make_impact(
                    direction="random",
                )
            ],
        )


def test_unknown_hypothesis_reference_is_rejected():
    with pytest.raises(ValueError):
        update_hypotheses(
            [make_hypothesis(hypothesis_id="H1")],
            [
                make_impact(
                    hypothesis_id="H999",
                )
            ],
        )


def test_results_are_deterministic():
    hypotheses = [
        make_hypothesis(
            hypothesis_id="H2",
            name="Pollution-related stress",
        ),
        make_hypothesis(
            hypothesis_id="H1",
            name="Rainfall-related oxygen depletion",
        ),
    ]

    impacts = [
        make_impact(
            evidence_id="EV-002",
            hypothesis_id="H2",
            direction="contradicts",
            rationale="Evidence contradicts H2.",
        ),
        make_impact(
            evidence_id="EV-001",
            hypothesis_id="H1",
            direction="supports",
            rationale="Evidence supports H1.",
        ),
    ]

    first = update_hypotheses(
        hypotheses,
        impacts,
    )

    second = update_hypotheses(
        hypotheses,
        impacts,
    )

    assert first == second
    assert [item.hypothesis_id for item in first] == [
        "H1",
        "H2",
    ]


def test_supporting_and_contradicting_evidence_are_traceable():
    hypotheses = [
        make_hypothesis(
            hypothesis_id="H1",
            name="Rainfall-related oxygen depletion",
        ),
        make_hypothesis(
            hypothesis_id="H2",
            name="Pollution-related stress",
            status="stronger",
        ),
    ]

    impacts = [
        make_impact(
            evidence_id="EV-NEW-001",
            hypothesis_id="H1",
            direction="supports",
            rationale="Low dissolved oxygen supports H1.",
        ),
        make_impact(
            evidence_id="EV-NEW-001",
            hypothesis_id="H2",
            direction="contradicts",
            rationale="The same evidence weakens H2.",
        ),
    ]

    results = update_hypotheses(
        hypotheses,
        impacts,
    )

    h1 = next(
        item for item in results
        if item.hypothesis_id == "H1"
    )

    h2 = next(
        item for item in results
        if item.hypothesis_id == "H2"
    )

    assert h1.new_status == "stronger"
    assert h2.new_status == "weaker"

    assert h1.triggering_evidence_id == "EV-NEW-001"
    assert h2.triggering_evidence_id == "EV-NEW-001"