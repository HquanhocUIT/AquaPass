from pathlib import Path

import pytest

from app.modules.evaluation.ranking_evaluation import (
    evaluate_ranking,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

GOLD_PATH = (
    PROJECT_ROOT
    / "data"
    / "evaluation"
    / "ranking_gold.csv"
)


def test_ranking_evaluation_uses_gold_order():
    summary = evaluate_ranking(GOLD_PATH)

    assert summary.total_scenarios == 1

    assert summary.aquapass_correct == 1

    assert summary.aquapass_accuracy == pytest.approx(1.0)


def test_ranking_evaluation_identifies_aquapass_choice():
    summary = evaluate_ranking(GOLD_PATH)

    row = summary.rows[0]

    assert row.gold_evidence_id == "EV-005"

    assert row.aquapass_evidence_id == "EV-005"

    assert row.aquapass_correct is True


def test_ranking_evaluation_is_deterministic():
    first = evaluate_ranking(GOLD_PATH)
    second = evaluate_ranking(GOLD_PATH)

    assert first == second


def test_missing_gold_file_is_rejected():
    missing_path = (
        PROJECT_ROOT
        / "data"
        / "evaluation"
        / "does_not_exist.csv"
    )

    with pytest.raises(FileNotFoundError):
        evaluate_ranking(missing_path)