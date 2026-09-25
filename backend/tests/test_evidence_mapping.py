from datetime import datetime, timezone

from app.modules.fhir.evidence_mapping import (
    evidence_request_to_fhir_bundle,
    evidence_request_to_fhir_service_request,
    evidence_request_to_fhir_task,
)
from app.modules.orchestration.evidence_request import (
    create_evidence_request,
)


def make_request():
    return create_evidence_request(
        request_id="REQ-001",
        incident_id="INC-FISH-001",
        decision_id="DEC-FISH-001",
        evidence_id="EV-005",
        evidence_type="dissolved_oxygen_measurement",
        purpose="Assess the low-DO hypothesis.",
        priority="high",
        decision_value=0.90,
        expected_cost=0.20,
        expected_time_minutes=20,
        assigned_actor_id="ACT-FIELD-A",
        created_at=datetime(
            2026,
            9,
            25,
            8,
            0,
            tzinfo=timezone.utc,
        ),
    )


def test_maps_evidence_request_to_service_request():
    request = make_request()

    resource = evidence_request_to_fhir_service_request(
        request
    )

    assert resource["resourceType"] == "ServiceRequest"
    assert resource["id"] == "REQ-001"
    assert resource["status"] == "draft"
    assert resource["intent"] == "order"
    assert resource["priority"] == "high"
    assert resource["subject"]["reference"] == (
        "Incident/INC-FISH-001"
    )
    assert resource["requester"]["reference"] == (
        "Practitioner/ACT-FIELD-A"
    )


def test_maps_evidence_request_to_task():
    request = make_request()

    resource = evidence_request_to_fhir_task(request)

    assert resource["resourceType"] == "Task"
    assert resource["id"] == "TASK-REQ-001"
    assert resource["status"] == "requested"
    assert resource["focus"]["reference"] == (
        "ServiceRequest/REQ-001"
    )
    assert resource["owner"]["reference"] == (
        "Practitioner/ACT-FIELD-A"
    )


def test_maps_evidence_request_to_bundle():
    request = make_request()

    bundle = evidence_request_to_fhir_bundle(request)

    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"
    assert len(bundle["entry"]) == 2
    assert (
        bundle["entry"][0]["resource"]["resourceType"]
        == "ServiceRequest"
    )
    assert (
        bundle["entry"][1]["resource"]["resourceType"]
        == "Task"
    )