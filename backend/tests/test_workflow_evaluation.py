from pathlib import Path

import pytest

from app.evaluation.workflow_evaluation import (
    evaluate_workflow_metrics,
    load_request_metrics,
)

from app.evaluation.workflow_evaluation import (
    evaluate_workflow_metrics,
    load_request_metrics,
    write_workflow_summary,
)


DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "evaluation"
    / "request_metrics.csv"
)


def test_request_metrics_loads():
    rows = load_request_metrics(DATA_PATH)

    assert len(rows) == 6


def test_workflow_metrics_are_grouped_by_strategy():
    rows = load_request_metrics(DATA_PATH)

    metrics = evaluate_workflow_metrics(rows)

    assert [
        item.collection_strategy
        for item in metrics
    ] == [
        "decision_aware",
        "freshness_only",
    ]


def test_decision_aware_useful_evidence_rate():
    rows = load_request_metrics(DATA_PATH)

    metrics = evaluate_workflow_metrics(rows)

    decision_aware = next(
        item
        for item in metrics
        if item.collection_strategy == "decision_aware"
    )

    assert decision_aware.useful_evidence_rate == pytest.approx(
        2 / 3
    )


def test_decision_aware_unnecessary_request_rate():
    rows = load_request_metrics(DATA_PATH)

    metrics = evaluate_workflow_metrics(rows)

    decision_aware = next(
        item
        for item in metrics
        if item.collection_strategy == "decision_aware"
    )

    assert decision_aware.unnecessary_request_rate == pytest.approx(
        1 / 3
    )


def test_decision_aware_average_latency():
    rows = load_request_metrics(DATA_PATH)

    metrics = evaluate_workflow_metrics(rows)

    decision_aware = next(
        item
        for item in metrics
        if item.collection_strategy == "decision_aware"
    )

    assert decision_aware.average_latency_hours == pytest.approx(
        3.1666666667
    )


def test_invalid_boolean_is_rejected():
    rows = [
        {
            "incident_id": "INC-001",
            "decision_id": "DEC-001",
            "request_id": "REQ-001",
            "evidence_id": "EV-001",
            "collection_strategy": "decision_aware",
            "requested_at": "2026-09-18T08:00:00",
            "useful_at": "2026-09-18T10:00:00",
            "latency_hours": "2.0",
            "cost_units": "1.0",
            "resource_units": "1.0",
            "decision_changed": "maybe",
            "useful_evidence": "true",
            "unnecessary_request": "false",
        }
    ]

    with pytest.raises(ValueError):
        evaluate_workflow_metrics(rows)


def test_invalid_negative_latency_is_rejected():
    rows = [
        {
            "incident_id": "INC-001",
            "decision_id": "DEC-001",
            "request_id": "REQ-001",
            "evidence_id": "EV-001",
            "collection_strategy": "decision_aware",
            "requested_at": "2026-09-18T08:00:00",
            "useful_at": "2026-09-18T10:00:00",
            "latency_hours": "-1.0",
            "cost_units": "1.0",
            "resource_units": "1.0",
            "decision_changed": "true",
            "useful_evidence": "true",
            "unnecessary_request": "false",
        }
    ]

    with pytest.raises(ValueError):
        evaluate_workflow_metrics(rows)


def test_results_are_deterministic():
    rows = load_request_metrics(DATA_PATH)

    first = evaluate_workflow_metrics(rows)
    second = evaluate_workflow_metrics(rows)

    assert first == second

def test_workflow_summary_is_written(tmp_path):
    rows = load_request_metrics(DATA_PATH)

    metrics = evaluate_workflow_metrics(rows)

    output_path = (
        tmp_path
        / "workflow_metrics_summary.csv"
    )

    write_workflow_summary(
        metrics,
        output_path,
    )

    content = output_path.read_text(
        encoding="utf-8"
    )

    assert "metric,decision_aware,freshness_only" in content
    assert "useful_evidence_rate,0.667,0.333" in content
    assert "unnecessary_request_rate,0.333,0.667" in content
    assert "average_latency_hours,3.167,4.500" in content