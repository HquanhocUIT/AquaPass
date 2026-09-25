from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REQUIRED_COLUMNS = {
    "incident_id",
    "decision_id",
    "request_id",
    "evidence_id",
    "collection_strategy",
    "requested_at",
    "useful_at",
    "latency_hours",
    "cost_units",
    "resource_units",
    "decision_changed",
    "useful_evidence",
    "unnecessary_request",
}


@dataclass(frozen=True)
class WorkflowMetric:
    collection_strategy: str
    request_count: int
    useful_evidence_count: int
    unnecessary_request_count: int
    useful_evidence_rate: float
    unnecessary_request_rate: float
    average_latency_hours: float
    total_cost_units: float
    total_resource_units: float


def load_request_metrics(
    path: str | Path,
) -> list[dict[str, str]]:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"request metrics file not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError(
                "request metrics CSV must contain a header"
            )

        missing_columns = (
            REQUIRED_COLUMNS
            - set(reader.fieldnames)
        )

        if missing_columns:
            missing = ", ".join(
                sorted(missing_columns)
            )

            raise ValueError(
                f"request metrics CSV is missing columns: {missing}"
            )

        return list(reader)


def _parse_bool(
    value: str,
    field_name: str,
) -> bool:
    normalized = value.strip().lower()

    if normalized == "true":
        return True

    if normalized == "false":
        return False

    raise ValueError(
        f"{field_name} must be true or false"
    )


def _parse_non_negative_float(
    value: str,
    field_name: str,
) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError(
            f"{field_name} must be numeric"
        ) from exc

    if number < 0.0:
        raise ValueError(
            f"{field_name} must be non-negative"
        )

    return number


def evaluate_workflow_metrics(
    rows: Iterable[dict[str, str]],
) -> list[WorkflowMetric]:
    rows = list(rows)

    grouped: dict[str, list[dict[str, str]]] = {}

    for row in rows:
        strategy = row["collection_strategy"].strip()

        if not strategy:
            raise ValueError(
                "collection_strategy must not be empty"
            )

        _parse_non_negative_float(
            row["latency_hours"],
            "latency_hours",
        )

        _parse_non_negative_float(
            row["cost_units"],
            "cost_units",
        )

        _parse_non_negative_float(
            row["resource_units"],
            "resource_units",
        )

        _parse_bool(
            row["decision_changed"],
            "decision_changed",
        )

        _parse_bool(
            row["useful_evidence"],
            "useful_evidence",
        )

        _parse_bool(
            row["unnecessary_request"],
            "unnecessary_request",
        )

        grouped.setdefault(
            strategy,
            [],
        ).append(row)

    results: list[WorkflowMetric] = []

    for strategy in sorted(grouped):
        strategy_rows = grouped[strategy]

        request_count = len(strategy_rows)

        useful_evidence_count = sum(
            _parse_bool(
                row["useful_evidence"],
                "useful_evidence",
            )
            for row in strategy_rows
        )

        unnecessary_request_count = sum(
            _parse_bool(
                row["unnecessary_request"],
                "unnecessary_request",
            )
            for row in strategy_rows
        )

        total_latency = sum(
            _parse_non_negative_float(
                row["latency_hours"],
                "latency_hours",
            )
            for row in strategy_rows
        )

        total_cost = sum(
            _parse_non_negative_float(
                row["cost_units"],
                "cost_units",
            )
            for row in strategy_rows
        )

        total_resources = sum(
            _parse_non_negative_float(
                row["resource_units"],
                "resource_units",
            )
            for row in strategy_rows
        )

        useful_rate = (
            useful_evidence_count / request_count
            if request_count
            else 0.0
        )

        unnecessary_rate = (
            unnecessary_request_count / request_count
            if request_count
            else 0.0
        )

        average_latency = (
            total_latency / request_count
            if request_count
            else 0.0
        )

        results.append(
            WorkflowMetric(
                collection_strategy=strategy,
                request_count=request_count,
                useful_evidence_count=useful_evidence_count,
                unnecessary_request_count=(
                    unnecessary_request_count
                ),
                useful_evidence_rate=useful_rate,
                unnecessary_request_rate=(
                    unnecessary_rate
                ),
                average_latency_hours=average_latency,
                total_cost_units=total_cost,
                total_resource_units=total_resources,
            )
        )

    return results

def write_workflow_summary(
    metrics: Iterable[WorkflowMetric],
    output_path: str | Path,
) -> None:
    output_path = Path(output_path)

    metrics = list(metrics)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.writer(file)

        writer.writerow(
            [
                "metric",
                "decision_aware",
                "freshness_only",
            ]
        )

        by_strategy = {
            item.collection_strategy: item
            for item in metrics
        }

        decision_aware = by_strategy.get(
            "decision_aware"
        )

        freshness_only = by_strategy.get(
            "freshness_only"
        )

        if decision_aware is None:
            raise ValueError(
                "decision_aware strategy is required"
            )

        if freshness_only is None:
            raise ValueError(
                "freshness_only strategy is required"
            )

        writer.writerow(
            [
                "request_count",
                decision_aware.request_count,
                freshness_only.request_count,
            ]
        )

        writer.writerow(
            [
                "useful_evidence_count",
                decision_aware.useful_evidence_count,
                freshness_only.useful_evidence_count,
            ]
        )

        writer.writerow(
            [
                "useful_evidence_rate",
                f"{decision_aware.useful_evidence_rate:.3f}",
                f"{freshness_only.useful_evidence_rate:.3f}",
            ]
        )

        writer.writerow(
            [
                "unnecessary_request_count",
                decision_aware.unnecessary_request_count,
                freshness_only.unnecessary_request_count,
            ]
        )

        writer.writerow(
            [
                "unnecessary_request_rate",
                f"{decision_aware.unnecessary_request_rate:.3f}",
                f"{freshness_only.unnecessary_request_rate:.3f}",
            ]
        )

        writer.writerow(
            [
                "average_latency_hours",
                f"{decision_aware.average_latency_hours:.3f}",
                f"{freshness_only.average_latency_hours:.3f}",
            ]
        )

        writer.writerow(
            [
                "total_cost_units",
                f"{decision_aware.total_cost_units:.3f}",
                f"{freshness_only.total_cost_units:.3f}",
            ]
        )

        writer.writerow(
            [
                "total_resource_units",
                f"{decision_aware.total_resource_units:.3f}",
                f"{freshness_only.total_resource_units:.3f}",
            ]
        )