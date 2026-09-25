from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.modules.constraints.constraint_engine import (
    ActorCapacity,
    EvidenceRequirement,
    evaluate_evidence_requirement,
)


@dataclass(frozen=True)
class ActorAssignment:
    evidence_id: str
    actor_id: str | None
    actor_name: str | None
    feasible: bool
    location: str | None
    expected_delay_minutes: int | None
    reasons: tuple[str, ...]


def assign_collection_actor(
    *,
    requirement: EvidenceRequirement,
    actors: list[ActorCapacity],
    decision_deadline: datetime,
) -> ActorAssignment:
    result = evaluate_evidence_requirement(
        requirement=requirement,
        actors=actors,
        decision_deadline=decision_deadline,
    )

    selected_actor = next(
        (
            actor
            for actor in actors
            if actor.actor_id == result.actor_id
        ),
        None,
    )

    return ActorAssignment(
        evidence_id=requirement.evidence_id,
        actor_id=result.actor_id,
        actor_name=result.actor_name,
        feasible=result.feasible,
        location=(
            selected_actor.location
            if selected_actor is not None
            else requirement.required_location
        ),
        expected_delay_minutes=result.expected_delay_minutes,
        reasons=result.reasons,
    )