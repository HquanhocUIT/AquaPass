from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv

from app.modules.ranking.ranking_engine import (
    EvidenceCandidate,
    rank_evidence,
)


@dataclass(frozen=True)
class RankingEvaluationRow:
    incident_id: str
    decision_id: str
    gold_evidence_id: str
    aquapass_evidence_id: str
    freshness_evidence_id: str
    aquapass_correct: bool
    freshness_correct: bool


@dataclass(frozen=True)
class RankingEvaluationSummary:
    total_scenarios: int
    aquapass_correct: int
    freshness_correct: int
    aquapass_accuracy: float
    freshness_accuracy: float
    rows: tuple[RankingEvaluationRow, ...]


def _load_gold_rows(
    path: Path,
) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        return list(csv.DictReader(file))


def _to_candidate(
    row: dict[str, str],
) -> EvidenceCandidate:
    return EvidenceCandidate(
        evidence_id=row["evidence_id"],
        candidate_name=row["candidate_name"],
        decision_value=float(row["decision_value"]),
        reliability=float(row["reliability"]),
        feasibility=float(row["feasibility"]),
        cost=float(row["cost"]),
        time=float(row["time"]),
    )


def _freshness_baseline(
    rows: list[dict[str, str]],
) -> str:
    """
    Prototype baseline.

    The current gold-set schema does not contain an explicit
    freshness/timestamp field. Therefore this baseline uses
    CSV row order as the available deterministic proxy for
    the currently listed evidence order.

    This is intentionally documented as a limitation.
    """

    if not rows:
        raise ValueError("freshness baseline requires at least one row")

    return rows[0]["evidence_id"]


def evaluate_ranking(
    path: str | Path,
) -> RankingEvaluationSummary:
    """
    Compare AquaPass ranking against a deterministic freshness
    baseline on the supplied gold-set scenarios.
    """

    gold_path = Path(path)

    if not gold_path.exists():
        raise FileNotFoundError(
            f"ranking gold file does not exist: {gold_path}"
        )

    rows = _load_gold_rows(gold_path)

    if not rows:
        return RankingEvaluationSummary(
            total_scenarios=0,
            aquapass_correct=0,
            freshness_correct=0,
            aquapass_accuracy=0.0,
            freshness_accuracy=0.0,
            rows=(),
        )

    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}

    for row in rows:
        key = (
            row["incident_id"],
            row["decision_id"],
        )

        grouped.setdefault(key, []).append(row)

    evaluation_rows: list[RankingEvaluationRow] = []

    for (
        incident_id,
        decision_id,
    ), candidates in sorted(grouped.items()):
        gold_candidates = sorted(
            candidates,
            key=lambda row: int(row["expected_rank"]),
        )

        gold_evidence_id = gold_candidates[0]["evidence_id"]

        evidence_candidates = [
            _to_candidate(row)
            for row in candidates
        ]

        ranked = rank_evidence(evidence_candidates)

        if not ranked:
            raise ValueError(
                f"No rankable evidence for {incident_id}/{decision_id}"
            )

        aquapass_evidence_id = ranked[0].evidence_id

        freshness_evidence_id = _freshness_baseline(
            candidates
        )

        evaluation_rows.append(
            RankingEvaluationRow(
                incident_id=incident_id,
                decision_id=decision_id,
                gold_evidence_id=gold_evidence_id,
                aquapass_evidence_id=aquapass_evidence_id,
                freshness_evidence_id=freshness_evidence_id,
                aquapass_correct=(
                    aquapass_evidence_id == gold_evidence_id
                ),
                freshness_correct=(
                    freshness_evidence_id == gold_evidence_id
                ),
            )
        )

    total = len(evaluation_rows)

    aquapass_correct = sum(
        row.aquapass_correct
        for row in evaluation_rows
    )

    freshness_correct = sum(
        row.freshness_correct
        for row in evaluation_rows
    )

    return RankingEvaluationSummary(
        total_scenarios=total,
        aquapass_correct=aquapass_correct,
        freshness_correct=freshness_correct,
        aquapass_accuracy=(
            aquapass_correct / total
            if total
            else 0.0
        ),
        freshness_accuracy=(
            freshness_correct / total
            if total
            else 0.0
        ),
        rows=tuple(evaluation_rows),
    )