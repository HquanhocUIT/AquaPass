from pathlib import Path

import pytest

from app.evaluation.ranking_error_analysis import (
    analyze_all_disagreements,
    analyze_ranking_disagreement,
)
from app.evaluation.ranking_evaluation import (
    evaluate_ranking,
)


GOLD_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "evaluation"
    / "ranking_gold.csv"
)


def test_correct_scenario_has_no_disagreement():
    results, _ = evaluate_ranking(GOLD_PATH)

    fish = next(
        row
        for row in results
        if row.incident_id == "INC-FISH-001"
    )

    disagreement = analyze_ranking_disagreement(
        GOLD_PATH,
        fish,
    )

    assert disagreement is None


def test_water_scenario_is_detected_as_disagreement():
    results, _ = evaluate_ranking(GOLD_PATH)

    water = next(
        row
        for row in results
        if row.incident_id == "INC-WATER-001"
    )

    disagreement = analyze_ranking_disagreement(
        GOLD_PATH,
        water,
    )

    assert disagreement is not None
    assert disagreement.expected_evidence_id == "EV-014"
    assert disagreement.selected_evidence_id == "EV-015"


def test_water_score_margin_is_correct():
    results, _ = evaluate_ranking(GOLD_PATH)

    water = next(
        row
        for row in results
        if row.incident_id == "INC-WATER-001"
    )

    disagreement = analyze_ranking_disagreement(
        GOLD_PATH,
        water,
    )

    assert disagreement is not None

    assert disagreement.score_margin == pytest.approx(
        0.0215
    )


def test_water_expected_candidate_has_higher_decision_value():
    results, _ = evaluate_ranking(GOLD_PATH)

    water = next(
        row
        for row in results
        if row.incident_id == "INC-WATER-001"
    )

    disagreement = analyze_ranking_disagreement(
        GOLD_PATH,
        water,
    )

    assert disagreement is not None

    assert (
        disagreement.expected_decision_value
        > disagreement.selected_decision_value
    )


def test_water_expected_candidate_has_higher_reliability():
    results, _ = evaluate_ranking(GOLD_PATH)

    water = next(
        row
        for row in results
        if row.incident_id == "INC-WATER-001"
    )

    disagreement = analyze_ranking_disagreement(
        GOLD_PATH,
        water,
    )

    assert disagreement is not None

    assert (
        disagreement.expected_reliability
        > disagreement.selected_reliability
    )


def test_water_selected_candidate_has_lower_cost():
    results, _ = evaluate_ranking(GOLD_PATH)

    water = next(
        row
        for row in results
        if row.incident_id == "INC-WATER-001"
    )

    disagreement = analyze_ranking_disagreement(
        GOLD_PATH,
        water,
    )

    assert disagreement is not None

    assert (
        disagreement.selected_cost
        < disagreement.expected_cost
    )


def test_water_selected_candidate_is_faster():
    results, _ = evaluate_ranking(GOLD_PATH)

    water = next(
        row
        for row in results
        if row.incident_id == "INC-WATER-001"
    )

    disagreement = analyze_ranking_disagreement(
        GOLD_PATH,
        water,
    )

    assert disagreement is not None

    assert (
        disagreement.selected_time
        < disagreement.expected_time
    )


def test_all_disagreements_are_deterministic():
    results, _ = evaluate_ranking(GOLD_PATH)

    first = analyze_all_disagreements(
        GOLD_PATH,
        results,
    )

    second = analyze_all_disagreements(
        GOLD_PATH,
        results,
    )

    assert first == second


def test_only_water_scenario_currently_disagrees():
    results, _ = evaluate_ranking(GOLD_PATH)

    disagreements = analyze_all_disagreements(
        GOLD_PATH,
        results,
    )

    assert len(disagreements) == 1
    assert disagreements[0].incident_id == "INC-WATER-001"