from datetime import datetime

import pytest

from app.modules.constraints.constraint_engine import (
    EvidenceRequirement,
    ActorCapacity,
    ConstraintContext,
    evaluate_actor_capacity,
    evaluate_capacity_options,
    evaluate_evidence_requirement,
)


DEADLINE = datetime(2026, 9, 18, 17, 0)


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
        "expected_delay_minutes": 0,
    }

    data.update(overrides)

    return ActorCapacity(**data)


def make_context(**overrides):
    data = {
        "decision_deadline": DEADLINE,
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
    assert result.expected_delay_minutes == 0


def test_busy_actor_is_feasible_but_penalized():
    result = evaluate_actor_capacity(
        make_actor(
            actor_id="ACT-002",
            actor_name="Field Team B",
            status="busy",
            expected_delay_minutes=180,
        ),
        make_context(),
    )

    assert result.feasible is True
    assert result.penalty == pytest.approx(0.20)
    assert result.actor_id == "ACT-002"
    assert result.expected_delay_minutes == 180
    assert "busy" in result.reasons[0].lower()


def test_full_actor_is_infeasible():
    result = evaluate_actor_capacity(
        make_actor(
            actor_id="ACT-004",
            actor_name="Water Laboratory B",
            actor_type="laboratory",
            capability="water_chemistry",
            location="Central Lab",
            status="full",
            max_concurrent_tasks=0,
            expected_delay_minutes=4320,
        ),
        make_context(
            required_capability="water_chemistry",
            required_location="Central Lab",
        ),
    )

    assert result.feasible is False
    assert result.penalty == pytest.approx(1.0)
    assert "full" in result.reasons[0].lower()


def test_capability_mismatch_is_infeasible():
    result = evaluate_actor_capacity(
        make_actor(
            capability="satellite_analysis",
        ),
        make_context(
            required_capability="dissolved_oxygen",
        ),
    )

    assert result.feasible is False
    assert result.penalty == pytest.approx(1.0)
    assert "capability" in result.reasons[0].lower()


def test_late_result_is_infeasible():
    result = evaluate_actor_capacity(
        make_actor(
            actor_id="ACT-003",
            actor_name="Water Laboratory A",
            actor_type="laboratory",
            capability="water_chemistry",
            location="Central Lab",
            expected_delay_minutes=4320,
        ),
        make_context(
            required_capability="water_chemistry",
            required_location="Central Lab",
            decision_deadline=datetime(2026, 9, 18, 17, 0),
        ),
    )

    assert result.feasible is False
    assert result.penalty == pytest.approx(1.0)
    assert "deadline" in result.reasons[0].lower()


def test_actor_available_after_deadline_is_infeasible():
    result = evaluate_actor_capacity(
        make_actor(
            available_from=datetime(2026, 9, 19, 9, 0),
        ),
        make_context(),
    )

    assert result.feasible is False
    assert "available after" in result.reasons[0].lower()


def test_capacity_options_are_deterministic():
    actors = [
        make_actor(
            actor_id="ACT-003",
            actor_name="Busy Team",
            status="busy",
            expected_delay_minutes=180,
        ),
        make_actor(
            actor_id="ACT-001",
            actor_name="Available Team",
            status="available",
            expected_delay_minutes=0,
        ),
        make_actor(
            actor_id="ACT-004",
            actor_name="Full Team",
            status="full",
            expected_delay_minutes=0,
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
    assert [result.actor_id for result in first] == [
        "ACT-001",
        "ACT-003",
        "ACT-004",
    ]


def test_invalid_status_is_rejected():
    actor = make_actor(status="offline")

    with pytest.raises(ValueError):
        evaluate_actor_capacity(
            actor,
            make_context(),
        )


def test_negative_delay_is_rejected():
    actor = make_actor(
        expected_delay_minutes=-1,
    )

    with pytest.raises(ValueError):
        evaluate_actor_capacity(
            actor,
            make_context(),
        )

def test_wrong_location_is_infeasible():
    result = evaluate_actor_capacity(
        make_actor(
            location="Site 99",
        ),
        make_context(
            required_location="Site 04",
        ),
    )

    assert result.feasible is False
    assert result.penalty == pytest.approx(1.0)
    assert "location" in result.reasons[0].lower()

def test_evidence_requirement_selects_best_available_actor():
    requirement = EvidenceRequirement(
        evidence_id="EV-005",
        required_capability="dissolved_oxygen",
        required_location="Site 04",
    )

    actors = [
        make_actor(
            actor_id="ACT-002",
            actor_name="Field Team B",
            status="busy",
            expected_delay_minutes=180,
        ),
        make_actor(
            actor_id="ACT-001",
            actor_name="Field Team A",
            status="available",
            expected_delay_minutes=0,
        ),
    ]

    result = evaluate_evidence_requirement(
        requirement,
        actors,
        decision_deadline=DEADLINE,
    )

    assert result.feasible is True
    assert result.actor_id == "ACT-001"
    assert result.expected_delay_minutes == 0

def test_evidence_requirement_rejects_late_laboratory():
    requirement = EvidenceRequirement(
        evidence_id="EV-006",
        required_capability="water_chemistry",
        required_location="Central Lab",
    )

    actors = [
        make_actor(
            actor_id="ACT-003",
            actor_name="Water Laboratory A",
            actor_type="laboratory",
            capability="water_chemistry",
            location="Central Lab",
            status="available",
            expected_delay_minutes=4320,
        ),
    ]

    result = evaluate_evidence_requirement(
        requirement,
        actors,
        decision_deadline=DEADLINE,
    )

    assert result.feasible is False
    assert result.actor_id == "ACT-003"
    assert result.expected_delay_minutes == 4320

