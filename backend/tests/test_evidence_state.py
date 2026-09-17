from datetime import datetime, timezone

import pytest

from app.modules.evidence.evidence_state import (
    EvidenceRecord,
    EvidenceState,
    classify_evidence,
)


NOW = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)


def make_evidence(**overrides):
    data = {
        "evidence_id": "EV-TEST",
        "summary": "Test evidence",
        "observed_at": datetime(2026, 9, 17, 10, 0, tzinfo=timezone.utc),
        "is_available": True,
        "reliability": 0.90,
        "verification_status": "verified",
        "has_conflict": False,
    }

    data.update(overrides)

    return EvidenceRecord(**data)


def test_available_evidence():
    result = classify_evidence(
        make_evidence(),
        now=NOW,
    )

    assert result.state == EvidenceState.AVAILABLE
    assert result.evidence_id == "EV-TEST"
    assert "available" in result.reason.lower()


def test_missing_evidence():
    result = classify_evidence(
        make_evidence(is_available=False),
        now=NOW,
    )

    assert result.state == EvidenceState.MISSING
    assert "not currently available" in result.reason


def test_conflicting_evidence():
    result = classify_evidence(
        make_evidence(has_conflict=True),
        now=NOW,
    )

    assert result.state == EvidenceState.CONFLICTING
    assert "conflicts" in result.reason


def test_stale_evidence():
    result = classify_evidence(
        make_evidence(
            observed_at=datetime(
                2026,
                9,
                15,
                10,
                0,
                tzinfo=timezone.utc,
            )
        ),
        now=NOW,
        stale_after_hours=24,
    )

    assert result.state == EvidenceState.STALE
    assert "freshness window" in result.reason


def test_unreliable_evidence():
    result = classify_evidence(
        make_evidence(reliability=0.30),
        now=NOW,
        unreliable_threshold=0.40,
    )

    assert result.state == EvidenceState.UNRELIABLE
    assert "reliability" in result.reason


def test_missing_has_precedence_over_low_reliability():
    result = classify_evidence(
        make_evidence(
            is_available=False,
            reliability=0.10,
        ),
        now=NOW,
    )

    assert result.state == EvidenceState.MISSING


def test_conflicting_has_precedence_over_stale():
    result = classify_evidence(
        make_evidence(
            has_conflict=True,
            observed_at=datetime(
                2026,
                9,
                10,
                10,
                0,
                tzinfo=timezone.utc,
            ),
        ),
        now=NOW,
        stale_after_hours=24,
    )

    assert result.state == EvidenceState.CONFLICTING


def test_reliability_range_is_validated():
    with pytest.raises(ValueError):
        classify_evidence(
            make_evidence(reliability=1.2),
            now=NOW,
        )


def test_deterministic_classification():
    evidence = make_evidence()

    first = classify_evidence(
        evidence,
        now=NOW,
    )

    second = classify_evidence(
        evidence,
        now=NOW,
    )

    assert first == second

def test_invalid_verification_marks_evidence_unreliable():
    result = classify_evidence(
        make_evidence(verification_status="invalid"),
        now=NOW,
    )

    assert result.state == EvidenceState.UNRELIABLE
    assert "verification status" in result.reason