from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable


@dataclass(frozen=True)
class ActorCapacity:
    actor_id: str
    actor_name: str
    actor_type: str
    capability: str
    location: str
    status: str
    available_from: datetime
    available_until: datetime
    max_concurrent_tasks: int
    expected_delay_minutes: int


@dataclass(frozen=True)
class ConstraintContext:
    decision_deadline: datetime
    required_capability: str
    required_location: str | None = None


@dataclass(frozen=True)
class ConstraintResult:
    feasible: bool
    penalty: float
    reasons: tuple[str, ...]
    actor_id: str | None = None
    actor_name: str | None = None
    expected_delay_minutes: int | None = None


def _validate_capacity(actor: ActorCapacity) -> None:
    if not actor.actor_id:
        raise ValueError("actor_id must not be empty")

    if not actor.actor_name:
        raise ValueError("actor_name must not be empty")

    if not actor.capability:
        raise ValueError("capability must not be empty")

    if actor.status not in {
        "available",
        "busy",
        "full",
    }:
        raise ValueError(
            "status must be one of: available, busy, full"
        )

    if actor.max_concurrent_tasks < 0:
        raise ValueError(
            "max_concurrent_tasks must not be negative"
        )

    if actor.expected_delay_minutes < 0:
        raise ValueError(
            "expected_delay_minutes must not be negative"
        )


def _validate_context(context: ConstraintContext) -> None:
    if not context.required_capability:
        raise ValueError(
            "required_capability must not be empty"
        )


def evaluate_actor_capacity(
    actor: ActorCapacity,
    context: ConstraintContext,
) -> ConstraintResult:
    """
    Evaluate whether one actor can satisfy the evidence request.

    Hard constraints:
    - capability mismatch
    - actor explicitly full
    - actor availability starts after the decision deadline
    - expected result arrives after the decision deadline

    Soft constraint:
    - busy actors receive a penalty when they remain operationally usable
    """

    _validate_capacity(actor)
    _validate_context(context)

    reasons: list[str] = []

    if actor.capability != context.required_capability:
        reasons.append(
            "Actor capability does not match the required evidence."
        )

        return ConstraintResult(
            feasible=False,
            penalty=1.0,
            reasons=tuple(reasons),
            actor_id=actor.actor_id,
            actor_name=actor.actor_name,
            expected_delay_minutes=actor.expected_delay_minutes,
        )

    if actor.status == "full":
        reasons.append(
            "Actor capacity is full."
        )

        return ConstraintResult(
            feasible=False,
            penalty=1.0,
            reasons=tuple(reasons),
            actor_id=actor.actor_id,
            actor_name=actor.actor_name,
            expected_delay_minutes=actor.expected_delay_minutes,
        )

    if actor.available_from > context.decision_deadline:
        reasons.append(
            "Actor becomes available after the decision deadline."
        )

        return ConstraintResult(
            feasible=False,
            penalty=1.0,
            reasons=tuple(reasons),
            actor_id=actor.actor_id,
            actor_name=actor.actor_name,
            expected_delay_minutes=actor.expected_delay_minutes,
        )

    arrival_time = (
        actor.available_from
        + timedelta(minutes=actor.expected_delay_minutes)
    )

    if arrival_time > context.decision_deadline:
        reasons.append(
            "Expected result arrives after the decision deadline."
        )

        return ConstraintResult(
            feasible=False,
            penalty=1.0,
            reasons=tuple(reasons),
            actor_id=actor.actor_id,
            actor_name=actor.actor_name,
            expected_delay_minutes=actor.expected_delay_minutes,
        )

    penalty = 0.0

    if actor.status == "busy":
        penalty = 0.20
        reasons.append(
            "Actor is currently busy, so collection receives a soft penalty."
        )
    else:
        reasons.append(
            "Actor is available within the decision window."
        )

    return ConstraintResult(
        feasible=True,
        penalty=penalty,
        reasons=tuple(reasons),
        actor_id=actor.actor_id,
        actor_name=actor.actor_name,
        expected_delay_minutes=actor.expected_delay_minutes,
    )


def evaluate_capacity_options(
    actors: Iterable[ActorCapacity],
    context: ConstraintContext,
) -> list[ConstraintResult]:
    """
    Evaluate all actors deterministically.

    Results are ordered by:
    1. feasible before infeasible
    2. lower penalty
    3. lower expected delay
    4. actor_id
    """

    evaluated = [
        evaluate_actor_capacity(actor, context)
        for actor in actors
    ]

    return sorted(
        evaluated,
        key=lambda result: (
            not result.feasible,
            result.penalty,
            result.expected_delay_minutes
            if result.expected_delay_minutes is not None
            else float("inf"),
            result.actor_id or "",
        ),
    )