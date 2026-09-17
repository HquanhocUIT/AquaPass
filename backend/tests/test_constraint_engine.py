from datetime import datetime

import pytest

from app.modules.constraints.constraint_engine import (
    ActorCapacity,
    ConstraintContext,
    evaluate_actor_capacity,
    evaluate_capacity_options,
)


def make_actor(**overrides):
    data = {
        "actor_id": "ACT-001",
        "actor_name": "Field Team A",
        "actor_type": "field_team",
        "capability": "dissolved_oxygen",
        "location": "Site 04",
        "status": "available",
        "available_from": datetime(2026, 9, 18, 9, 0),
        "available_until": datetime(2026, 9, 18, 17, 0),
        "max_concurrent_tasks": 1,
        "expected_delay_minutes": 20,
    }

    data.update(overrides)

    return ActorCapacity(**data)


def make_context(**overrides):
    data = {
        "decision_deadline": datetime(2026, 9, 18, 11, 0),
        "required_capability": "dissolved_oxygen",
        "required_location": "Site 04",
    }

    data.update(overrides)

    return ConstraintContext(**data)


def test_available_actor_is_feasible():
    result = evaluate_actor_capacity(
        make_actor(),
        make_context(),
    )

    assert result.feasible is True
    assert result.penalty == pytest.approx(0.0)
    assert result.actor_id == "ACT-001"


def test_busy_actor_gets_soft_penalty():
    result = evaluate_actor_capacity(
        make_actor(
            status="busy",
            expected_delay_minutes=20,
        ),
        make_context(),
    )

    assert result.feasible is True
    assert result.penalty == pytest.approx(0.20)
    assert any("busy" in reason.lower() for reason in result.reasons)


def test_full_actor_is_infeasible():
    result = evaluate_actor_capacity(
        make_actor(status="full"),
        make_context(),
    )

    assert result.feasible is False
    assert result.penalty == pytest.approx(1.0)
    assert any("full" in reason.lower() for reason in result.reasons)


def test_late_result_is_infeasible():
    result = evaluate_actor_capacity(
        make_actor(expected_delay_minutes=180),
        make_context(),
    )

    assert result.feasible is False
    assert result.penalty == pytest.approx(1.0)
    assert any(
        "deadline" in reason.lower()
        for reason in result.reasons
    )


def test_capability_mismatch_is_infeasible():
    result = evaluate_actor_capacity(
        make_actor(capability="water_chemistry"),
        make_context(required_capability="dissolved_oxygen"),
    )

    assert result.feasible is False
    assert any(
        "capability" in reason.lower()
        for reason in result.reasons
    )


def test_available_actor_is_ranked_before_busy_actor():
    actors = [
        make_actor(
            actor_id="ACT-002",
            status="busy",
        ),
        make_actor(
            actor_id="ACT-001",
            status="available",
        ),
    ]

    results = evaluate_capacity_options(
        actors,
        make_context(),
    )

    assert [result.actor_id for result in results] == [
        "ACT-001",
        "ACT-002",
    ]


def test_infeasible_actor_is_after_feasible_actor():
    actors = [
        make_actor(
            actor_id="ACT-002",
            status="full",
        ),
        make_actor(
            actor_id="ACT-001",
            status="available",
        ),
    ]

    results = evaluate_capacity_options(
        actors,
        make_context(),
    )

    assert results[0].feasible is True
    assert results[1].feasible is False


def test_results_are_deterministic():
    actors = [
        make_actor(
            actor_id="ACT-003",
            status="available",
        ),
        make_actor(
            actor_id="ACT-001",
            status="available",
        ),
        make_actor(
            actor_id="ACT-002",
            status="available",
        ),
    ]

    first = evaluate_capacity_options(
        actors,
        make_context(),
    )

    second = evaluate_capacity_options(
        actors,
        make_context(),
    )

    assert first == second