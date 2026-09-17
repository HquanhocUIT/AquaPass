from app.modules.evidence.gap_detector import (
    EvidenceGraphRecord,
    GapPriority,
    detect_evidence_gaps,
)


def make_record(**overrides):
    data = {
        "graph_id": "G-009",
        "incident_id": "INC-FISH-001",
        "decision_id": "DEC-FISH-001",
        "source_node": "EV-005",
        "source_type": "evidence",
        "relationship": "missing_for",
        "target_node": "HYP-001",
        "target_type": "hypothesis",
        "confidence": 0.90,
        "state": "missing",
        "rationale": (
            "Independent field dissolved oxygen measurement is needed "
            "to verify the low dissolved oxygen hypothesis."
        ),
    }

    data.update(overrides)

    return EvidenceGraphRecord(**data)


def test_detects_missing_evidence_gap():
    gaps = detect_evidence_gaps([make_record()])

    assert len(gaps) == 1

    gap = gaps[0]

    assert gap.gap_id == "GAP-G-009"
    assert gap.decision_id == "DEC-FISH-001"
    assert gap.evidence_id == "EV-005"
    assert gap.evidence_type == "evidence"
    assert gap.target_hypothesis == "HYP-001"
    assert gap.priority == GapPriority.HIGH


def test_preserves_graph_rationale():
    gaps = detect_evidence_gaps([make_record()])

    assert gaps[0].why_missing == (
        "Independent field dissolved oxygen measurement is needed "
        "to verify the low dissolved oxygen hypothesis."
    )


def test_ignores_non_missing_for_relationships():
    record = make_record(relationship="supports")

    assert detect_evidence_gaps([record]) == []


def test_ignores_non_missing_state():
    record = make_record(state="known")

    assert detect_evidence_gaps([record]) == []


def test_ignores_non_evidence_source():
    record = make_record(source_type="hypothesis")

    assert detect_evidence_gaps([record]) == []


def test_ignores_unrelated_target_type():
    record = make_record(target_type="incident")

    assert detect_evidence_gaps([record]) == []


def test_medium_priority():
    record = make_record(confidence=0.60)

    gaps = detect_evidence_gaps([record])

    assert gaps[0].priority == GapPriority.MEDIUM


def test_low_priority():
    record = make_record(confidence=0.30)

    gaps = detect_evidence_gaps([record])

    assert gaps[0].priority == GapPriority.LOW


def test_decision_level_gap():
    record = make_record(
        graph_id="G-012",
        target_node="DEC-FISH-001",
        target_type="decision",
        rationale="Additional evidence is required for the pending decision.",
    )

    gaps = detect_evidence_gaps([record])

    assert len(gaps) == 1
    assert gaps[0].target_hypothesis == (
        "decision-level evidence requirement"
    )
    assert gaps[0].decision_id == "DEC-FISH-001"


def test_results_are_deterministic():
    records = [
        make_record(
            graph_id="G-011",
            confidence=0.30,
        ),
        make_record(
            graph_id="G-009",
            confidence=0.90,
        ),
        make_record(
            graph_id="G-010",
            confidence=0.85,
        ),
    ]

    first = detect_evidence_gaps(records)
    second = detect_evidence_gaps(records)

    assert first == second

    assert [gap.gap_id for gap in first] == [
        "GAP-G-009",
        "GAP-G-010",
        "GAP-G-011",
    ]


def test_invalid_confidence_is_rejected():
    record = make_record(confidence=1.5)

    try:
        detect_evidence_gaps([record])
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_missing_required_graph_id_is_rejected():
    record = make_record(graph_id="")

    try:
        detect_evidence_gaps([record])
        assert False, "Expected ValueError"
    except ValueError:
        pass