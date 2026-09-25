import pytest

from app.evaluation.ranking_evaluation import evaluate_ranking


from pathlib import Path

GOLD_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "evaluation"
    / "ranking_gold.csv"
)


def get_result(results, incident_id):
    matches = [
        result
        for result in results
        if result.incident_id == incident_id
    ]

    assert len(matches) == 1

    return matches[0]


def test_ranking_evaluation_loads_gold_set():
    results, summary = evaluate_ranking(GOLD_PATH)

    assert summary.scenarios == 10
    assert len(results) == 10


def test_aquapass_matches_expected_top1_for_fish_scenario():
    results, _ = evaluate_ranking(GOLD_PATH)

    result = get_result(
        results,
        "INC-FISH-001",
    )

    assert result.expected_top_evidence_id == "EV-005"
    assert result.aquapass_top_evidence_id == "EV-005"
    assert result.aquapass_correct is True


def test_baseline_is_evaluated_separately_for_fish_scenario():
    results, _ = evaluate_ranking(GOLD_PATH)

    result = get_result(
        results,
        "INC-FISH-001",
    )

    assert result.baseline_top_evidence_id == "EV-007"
    assert result.baseline_correct is False


def test_aquapass_accuracy_is_reported():
    _, summary = evaluate_ranking(GOLD_PATH)

    assert summary.aquapass_top1_accuracy == pytest.approx(0.90)


def test_evaluation_is_deterministic():
    first_results, first_summary = evaluate_ranking(GOLD_PATH)
    second_results, second_summary = evaluate_ranking(GOLD_PATH)

    assert first_results == second_results
    assert first_summary == second_summary