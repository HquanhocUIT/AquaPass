from __future__ import annotations

from dataclasses import dataclass

from app.evaluation.ranking_evaluation import (
    RankingEvaluationRow,
    _load_gold_rows,
)
from app.modules.ranking.ranking_engine import (
    EvidenceCandidate,
    rank_evidence,
)


@dataclass(frozen=True)
class RankingDisagreement:
    incident_id: str
    decision_id: str
    expected_evidence_id: str
    selected_evidence_id: str
    score_margin: float
    expected_decision_value: float
    selected_decision_value: float
    expected_reliability: float
    selected_reliability: float
    expected_feasibility: float
    selected_feasibility: float
    expected_cost: float
    selected_cost: float
    expected_time: float
    selected_time: float


def analyze_ranking_disagreement(
    gold_path,
    evaluation_row: RankingEvaluationRow,
) -> RankingDisagreement | None:
    """
    Analyze a single AquaPass ranking disagreement.

    Returns None when AquaPass agrees with the expected top candidate.
    """

    if evaluation_row.aquapass_correct:
        return None

    rows = _load_gold_rows(gold_path)

    candidates = [
        row
        for row in rows
        if (
            row["incident_id"]
            == evaluation_row.incident_id
            and row["decision_id"]
            == evaluation_row.decision_id
        )
    ]

    if not candidates:
        raise ValueError(
            "No gold-set candidates found for "
            f"{evaluation_row.incident_id}/"
            f"{evaluation_row.decision_id}"
        )

    ranked = rank_evidence(
        [
            EvidenceCandidate(
                evidence_id=row["evidence_id"],
                candidate_name=row["candidate_name"],
                decision_value=float(row["decision_value"]),
                reliability=float(row["reliability"]),
                feasibility=float(row["feasibility"]),
                cost=float(row["cost"]),
                time=float(row["time"]),
            )
            for row in candidates
        ]
    )

    selected = next(
        item
        for item in ranked
        if item.evidence_id
        == evaluation_row.aquapass_top_evidence_id
    )

    expected = next(
        item
        for item in ranked
        if item.evidence_id
        == evaluation_row.expected_top_evidence_id
    )

    return RankingDisagreement(
        incident_id=evaluation_row.incident_id,
        decision_id=evaluation_row.decision_id,
        expected_evidence_id=expected.evidence_id,
        selected_evidence_id=selected.evidence_id,
        score_margin=selected.score - expected.score,
        expected_decision_value=expected.decision_value,
        selected_decision_value=selected.decision_value,
        expected_reliability=expected.reliability,
        selected_reliability=selected.reliability,
        expected_feasibility=expected.feasibility,
        selected_feasibility=selected.feasibility,
        expected_cost=expected.cost,
        selected_cost=selected.cost,
        expected_time=expected.time,
        selected_time=selected.time,
    )


def analyze_all_disagreements(
    gold_path,
    evaluation_rows: list[RankingEvaluationRow],
) -> list[RankingDisagreement]:
    """
    Analyze all scenarios where AquaPass disagrees
    with the gold-set expected top candidate.
    """

    disagreements: list[RankingDisagreement] = []

    for row in evaluation_rows:
        disagreement = analyze_ranking_disagreement(
            gold_path,
            row,
        )

        if disagreement is not None:
            disagreements.append(disagreement)

    return disagreements