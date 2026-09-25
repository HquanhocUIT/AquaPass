from datetime import datetime

import pytest

from app.modules.decision.approval import (
    ApprovalStatus,
    approve_decision,
    create_approval,
    reject_decision,
)


def _create_approval():
    return create_approval(
        approval_id="APR-001",
        decision_id="DEC-FISH-001",
        decision_version=2,
        created_at=datetime(2026, 9, 18, 11, 0),
    )


def test_create_approval_starts_pending():
    approval = _create_approval()

    assert approval.status == ApprovalStatus.PENDING
    assert approval.decision_id == "DEC-FISH-001"
    assert approval.decision_version == 2


def test_human_can_approve_decision():
    approval = _create_approval()

    approved = approve_decision(
        approval,
        reviewer_id="USER-001",
        reason="Evidence supports the proposed update.",
    )

    assert approved.status == ApprovalStatus.APPROVED
    assert approved.reviewer_id == "USER-001"
    assert approved.reason == (
        "Evidence supports the proposed update."
    )


def test_human_can_reject_decision():
    approval = _create_approval()

    rejected = reject_decision(
        approval,
        reviewer_id="USER-001",
        reason="Evidence is insufficient.",
    )

    assert rejected.status == ApprovalStatus.REJECTED
    assert rejected.reviewer_id == "USER-001"


def test_rejection_requires_reason():
    approval = _create_approval()

    with pytest.raises(ValueError, match="reason"):
        reject_decision(
            approval,
            reviewer_id="USER-001",
            reason="",
        )


def test_reviewer_is_required():
    approval = _create_approval()

    with pytest.raises(ValueError, match="reviewer_id"):
        approve_decision(
            approval,
            reviewer_id="",
        )


def test_reviewed_approval_cannot_be_reviewed_again():
    approval = _create_approval()

    approval = approve_decision(
        approval,
        reviewer_id="USER-001",
    )

    with pytest.raises(
        ValueError,
        match="already been reviewed",
    ):
        approve_decision(
            approval,
            reviewer_id="USER-002",
        )


def test_required_fields_are_validated():
    with pytest.raises(ValueError, match="approval_id"):
        create_approval(
            approval_id="",
            decision_id="DEC-FISH-001",
            decision_version=1,
        )

    with pytest.raises(ValueError, match="decision_id"):
        create_approval(
            approval_id="APR-001",
            decision_id="",
            decision_version=1,
        )

    with pytest.raises(ValueError, match="decision_version"):
        create_approval(
            approval_id="APR-001",
            decision_id="DEC-FISH-001",
            decision_version=0,
        )