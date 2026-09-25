from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class EvidenceState(str, Enum):
    AVAILABLE = "available"
    MISSING = "missing"
    CONFLICTING = "conflicting"
    STALE = "stale"
    UNRELIABLE = "unreliable"


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    summary: str
    observed_at: Optional[datetime]
    is_available: bool
    reliability: float
    verification_status: str
    has_conflict: bool = False


@dataclass(frozen=True)
class EvidenceClassification:
    evidence_id: str
    state: EvidenceState
    reason: str


def _validate_reliability(value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError("reliability must be between 0.0 and 1.0")


def _is_stale(
    observed_at: Optional[datetime],
    now: datetime,
    stale_after_hours: float,
) -> bool:
    if observed_at is None:
        return False

    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)

    age_hours = (now - observed_at).total_seconds() / 3600

    return age_hours > stale_after_hours


def classify_evidence(
    evidence: EvidenceRecord,
    *,
    now: Optional[datetime] = None,
    stale_after_hours: float = 24.0,
    unreliable_threshold: float = 0.40,
) -> EvidenceClassification:
    """
    Deterministically classify one evidence record.

    Precedence:
    1. missing
    2. invalid verification
    3. conflicting
    4. stale
    5. unreliable
    6. available
    """

    _validate_reliability(evidence.reliability)

    if stale_after_hours <= 0:
        raise ValueError("stale_after_hours must be greater than 0")

    if not 0.0 <= unreliable_threshold <= 1.0:
        raise ValueError("unreliable_threshold must be between 0.0 and 1.0")

    if now is None:
        now = datetime.now(timezone.utc)

    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if not evidence.is_available:
        return EvidenceClassification(
            evidence_id=evidence.evidence_id,
            state=EvidenceState.MISSING,
            reason="Evidence is required but is not currently available.",
        )

    if evidence.verification_status == "invalid":
        return EvidenceClassification(
            evidence_id=evidence.evidence_id,
            state=EvidenceState.UNRELIABLE,
            reason=(
                "Evidence is available, but its verification status is "
                "marked as invalid."
            ),
        )

    if evidence.has_conflict:
        return EvidenceClassification(
            evidence_id=evidence.evidence_id,
            state=EvidenceState.CONFLICTING,
            reason=(
                "Available evidence conflicts with another relevant observation."
            ),
        )

    if _is_stale(
        evidence.observed_at,
        now,
        stale_after_hours,
    ):
        return EvidenceClassification(
            evidence_id=evidence.evidence_id,
            state=EvidenceState.STALE,
            reason=(
                "Evidence is available, but its observation timestamp is "
                "outside the configured freshness window."
            ),
        )

    if evidence.reliability < unreliable_threshold:
        return EvidenceClassification(
            evidence_id=evidence.evidence_id,
            state=EvidenceState.UNRELIABLE,
            reason=(
                "Evidence is available, but its reliability is below "
                f"the configured threshold of {unreliable_threshold:.2f}."
            ),
        )

    return EvidenceClassification(
        evidence_id=evidence.evidence_id,
        state=EvidenceState.AVAILABLE,
        reason=(
            "Evidence is available, sufficiently recent, not marked as "
            "conflicting, and meets the configured reliability threshold."
        ),
    )