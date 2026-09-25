from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class DecisionApproval:
    approval_id: str
    decision_id: str
    decision_version: int
    status: ApprovalStatus
    reviewer_id: str | None = None
    reason: str | None = None
    created_at: datetime | None = None
    reviewed_at: datetime | None = None


def create_approval(
    *,
    approval_id: str,
    decision_id: str,
    decision_version: int,
    created_at: datetime | None = None,
) -> DecisionApproval:
    if not approval_id:
        raise ValueError("approval_id must not be empty")

    if not decision_id:
        raise ValueError("decision_id must not be empty")

    if decision_version < 1:
        raise ValueError(
            "decision_version must be at least 1"
        )

    return DecisionApproval(
        approval_id=approval_id,
        decision_id=decision_id,
        decision_version=decision_version,
        status=ApprovalStatus.PENDING,
        created_at=created_at,
    )


def approve_decision(
    approval: DecisionApproval,
    *,
    reviewer_id: str,
    reason: str | None = None,
    reviewed_at: datetime | None = None,
) -> DecisionApproval:
    return _review_decision(
        approval,
        status=ApprovalStatus.APPROVED,
        reviewer_id=reviewer_id,
        reason=reason,
        reviewed_at=reviewed_at,
    )


def reject_decision(
    approval: DecisionApproval,
    *,
    reviewer_id: str,
    reason: str,
    reviewed_at: datetime | None = None,
) -> DecisionApproval:
    if not reason:
        raise ValueError(
            "reason must not be empty when rejecting"
        )

    return _review_decision(
        approval,
        status=ApprovalStatus.REJECTED,
        reviewer_id=reviewer_id,
        reason=reason,
        reviewed_at=reviewed_at,
    )


def _review_decision(
    approval: DecisionApproval,
    *,
    status: ApprovalStatus,
    reviewer_id: str,
    reason: str | None,
    reviewed_at: datetime | None,
) -> DecisionApproval:
    if approval.status != ApprovalStatus.PENDING:
        raise ValueError(
            "Decision approval has already been reviewed."
        )

    if not reviewer_id:
        raise ValueError(
            "reviewer_id must not be empty"
        )

    return DecisionApproval(
        approval_id=approval.approval_id,
        decision_id=approval.decision_id,
        decision_version=approval.decision_version,
        status=status,
        reviewer_id=reviewer_id,
        reason=reason,
        created_at=approval.created_at,
        reviewed_at=reviewed_at,
    )