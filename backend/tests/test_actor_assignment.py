from datetime import datetime, timedelta

from app.modules.constraints.constraint_engine import (
    ActorCapacity,
    EvidenceRequirement,
)
from app.modules.orchestration.actor_assignment import (
    assign_collection_actor,
)


def test_assigns_available_field_team():
    now = datetime.now()

    actors = [
        ActorCapacity(
            actor_id="ACT-FIELD-A",
            actor_name="Field Team A",
            actor_type="field_team",
            capability="dissolved_oxygen_measurement",
            location="Demo Lake",
            status="available",
            available_from=now,
            available_until=now + timedelta(hours=2),
            max_concurrent_tasks=2,
            expected_delay_minutes=20,
        )
    ]

    requirement = EvidenceRequirement(
        evidence_id="EV-005",
        required_capability="dissolved_oxygen_measurement",
        required_location="Demo Lake",
    )

    assignment = assign_collection_actor(
        requirement=requirement,
        actors=actors,
        decision_deadline=now + timedelta(hours=1),
    )

    assert assignment.feasible is True
    assert assignment.actor_id == "ACT-FIELD-A"
    assert assignment.actor_name == "Field Team A"
    assert assignment.location == "Demo Lake"
    assert assignment.expected_delay_minutes == 20