from pathlib import Path

import pytest

from app.evaluation.ranking_evaluation import (
    evaluate_ranking,
)


GOLD_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "evaluation"
    / "ranking_gold.csv"
)


def test_ranking_evaluation_loads_gold_set():
    results, summary = evaluate_ranking(GOLD_PATH)

    assert summary.scenarios == 1
    assert len(results) == 1


def test_aquapass_matches_expected_top1():
    results, _ = evaluate_ranking(GOLD_PATH)

    assert results[0].expected_top_evidence_id == "EV-005"
    assert results[0].aquapass_top_evidence_id == "EV-005"
    assert results[0].aquapass_correct is True


def test_baseline_is_evaluated_separately():
    results, summary = evaluate_ranking(GOLD_PATH)

    assert results[0].baseline_top_evidence_id == "EV-007"
    assert summary.baseline_top1_accuracy == pytest.approx(0.0)


def test_aquapass_accuracy_is_reported():
    _, summary = evaluate_ranking(GOLD_PATH)

    assert summary.aquapass_top1_accuracy == pytest.approx(1.0)


def test_evaluation_is_deterministic():
    first_results, first_summary = evaluate_ranking(
        GOLD_PATH
    )

    second_results, second_summary = evaluate_ranking(
        GOLD_PATH
    )

    assert first_results == second_results
    assert first_summary == second_summary