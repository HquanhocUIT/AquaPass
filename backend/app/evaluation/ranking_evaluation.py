from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from app.modules.ranking.ranking_engine import (
    EvidenceCandidate,
    rank_evidence,
)


@dataclass(frozen=True)
class RankingEvaluationRow:
    incident_id: str
    decision_id: str
    expected_top_evidence_id: str
    baseline_top_evidence_id: str
    aquapass_top_evidence_id: str
    baseline_correct: bool
    aquapass_correct: bool


@dataclass(frozen=True)
class RankingEvaluationSummary:
    scenarios: int
    baseline_top1_accuracy: float
    aquapass_top1_accuracy: float


def _load_gold_rows(
    path: Path,
) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
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


def _freshness_score(
    row: dict[str, str],
) -> float:
    """
    Prototype freshness-only baseline.

    The current ranking gold-set schema does not yet contain
    an explicit freshness field.

    Therefore, acquisition time is temporarily used as a
    freshness proxy:

        lower acquisition time
        -> higher freshness score
    """

    return 1.0 - float(row["time"])


def evaluate_ranking(
    gold_path: Path,
) -> tuple[
    list[RankingEvaluationRow],
    RankingEvaluationSummary,
]:
    rows = _load_gold_rows(gold_path)

    grouped: dict[
        tuple[str, str],
        list[dict[str, str]],
    ] = {}

    for row in rows:
        key = (
            row["incident_id"],
            row["decision_id"],
        )

        grouped.setdefault(
            key,
            [],
        ).append(row)

    results: list[RankingEvaluationRow] = []

    for (
        incident_id,
        decision_id,
    ), candidates in sorted(grouped.items()):

        expected = sorted(
            candidates,
            key=lambda row: (
                int(row["expected_rank"]),
                row["evidence_id"],
            ),
        )[0]

        baseline_top = sorted(
            candidates,
            key=lambda row: (
                -_freshness_score(row),
                row["evidence_id"],
            ),
        )[0]

        ranked = rank_evidence(
            [
                _to_candidate(row)
                for row in candidates
            ]
        )

        if not ranked:
            raise ValueError(
                "No feasible evidence candidates available "
                f"for {incident_id}/{decision_id}"
            )

        aquapass_top = ranked[0]

        results.append(
            RankingEvaluationRow(
                incident_id=incident_id,
                decision_id=decision_id,
                expected_top_evidence_id=(
                    expected["evidence_id"]
                ),
                baseline_top_evidence_id=(
                    baseline_top["evidence_id"]
                ),
                aquapass_top_evidence_id=(
                    aquapass_top.evidence_id
                ),
                baseline_correct=(
                    baseline_top["evidence_id"]
                    == expected["evidence_id"]
                ),
                aquapass_correct=(
                    aquapass_top.evidence_id
                    == expected["evidence_id"]
                ),
            )
        )

    scenarios = len(results)

    if scenarios == 0:
        summary = RankingEvaluationSummary(
            scenarios=0,
            baseline_top1_accuracy=0.0,
            aquapass_top1_accuracy=0.0,
        )

        return [], summary

    baseline_correct = sum(
        row.baseline_correct
        for row in results
    )

    aquapass_correct = sum(
        row.aquapass_correct
        for row in results
    )

    summary = RankingEvaluationSummary(
        scenarios=scenarios,
        baseline_top1_accuracy=(
            baseline_correct / scenarios
        ),
        aquapass_top1_accuracy=(
            aquapass_correct / scenarios
        ),
    )

    return results, summary