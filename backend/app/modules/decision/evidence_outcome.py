from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.modules.ranking.ranking_engine import RankedEvidence


DEFAULT_MIN_DECISION_VALUE = 0.30
DEFAULT_MIN_SCORE = 0.30


@dataclass(frozen=True)
class EvidenceOutcome:
    recommendation: str
    recommended_evidence_id: str | None
    reason: str
    considered_candidates: int


def evaluate_evidence_outcome(
    ranked_candidates: Iterable[RankedEvidence],
    *,
    min_decision_value: float = DEFAULT_MIN_DECISION_VALUE,
    min_score: float = DEFAULT_MIN_SCORE,
) -> EvidenceOutcome:
    """
    Determine whether AquaPass should recommend collecting
    additional evidence.

    This is a prototype threshold rule.

    An evidence candidate is considered actionable only when:
        decision_value >= min_decision_value
        AND
        score >= min_score

    If no candidate satisfies both thresholds, AquaPass explicitly
    returns a no-additional-evidence outcome.

    The rule is deterministic and does not make the final decision.
    """

    if not 0.0 <= min_decision_value <= 1.0:
        raise ValueError(
            "min_decision_value must be between 0.0 and 1.0"
        )

    if not -1.0 <= min_score <= 1.0:
        raise ValueError(
            "min_score must be between -1.0 and 1.0"
        )

    candidates = list(ranked_candidates)

    for candidate in candidates:
        if candidate.decision_value >= min_decision_value:
            if candidate.score >= min_score:
                return EvidenceOutcome(
                    recommendation="collect_additional_evidence",
                    recommended_evidence_id=candidate.evidence_id,
                    reason=(
                        "At least one candidate meets the prototype "
                        "decision-value and score thresholds."
                    ),
                    considered_candidates=len(candidates),
                )

    return EvidenceOutcome(
        recommendation="no_additional_evidence",
        recommended_evidence_id=None,
        reason=(
            "No available evidence candidate meets the prototype "
            "thresholds for practical decision value."
        ),
        considered_candidates=len(candidates),
    )