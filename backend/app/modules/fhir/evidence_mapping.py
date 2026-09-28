from __future__ import annotations

from datetime import datetime, timezone

from app.modules.orchestration.evidence_request import EvidenceRequest


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.isoformat()


def _service_request_status(request: EvidenceRequest) -> str:
    return {
        "draft": "draft",
        "requested": "active",
        "accepted": "active",
        "collecting": "active",
        "submitted": "active",
        "verified": "active",
        "ingested": "completed",
        "decision_updated": "completed",
        "rejected": "revoked",
    }.get(request.status.value, "unknown")


def _task_status(request: EvidenceRequest) -> str:
    return {
        "draft": "requested",
        "requested": "requested",
        "accepted": "accepted",
        "collecting": "in-progress",
        "submitted": "in-progress",
        "verified": "in-progress",
        "ingested": "completed",
        "decision_updated": "completed",
        "rejected": "cancelled",
    }.get(request.status.value, "unknown")


def evidence_request_to_fhir_service_request(
    request: EvidenceRequest,
) -> dict:
    """
    Map an AquaPass EvidenceRequest to a FHIR ServiceRequest.

    This is a lightweight interoperability representation for the demo.
    It does not claim full clinical workflow conformance.
    """

    return {
        "resourceType": "ServiceRequest",
        "id": request.request_id,
        "status": _service_request_status(request),
        "intent": "order",
        "priority": request.priority,
        "code": {
            "text": request.evidence_type,
        },
        "subject": {
            "reference": f"Incident/{request.incident_id}",
        },
        "reasonCode": [
            {
                "text": request.purpose,
            }
        ],
        "authoredOn": _isoformat(request.created_at),
        "requester": (
            {
                "reference": (
                    f"Practitioner/{request.assigned_actor_id}"
                ),
            }
            if request.assigned_actor_id
            else None
        ),
        "note": [
            {
                "text": (
                    f"Decision-aware evidence request for "
                    f"decision {request.decision_id}. "
                    f"Expected collection time: "
                    f"{request.expected_time_minutes} minutes."
                )
            }
        ],
    }


def evidence_request_to_fhir_task(
    request: EvidenceRequest,
) -> dict:
    """
    Map an AquaPass EvidenceRequest to a FHIR Task.

    The Task represents the operational collection workflow.
    """

    task: dict = {
        "resourceType": "Task",
        "id": f"TASK-{request.request_id}",
        "status": _task_status(request),
        "intent": "order",
        "priority": request.priority,
        "focus": {
            "reference": (
                f"ServiceRequest/{request.request_id}"
            ),
        },
        "for": {
            "reference": f"Incident/{request.incident_id}",
        },
        "description": request.purpose,
        "authoredOn": _isoformat(request.created_at),
    }

    if request.assigned_actor_id:
        task["owner"] = {
            "reference": (
                f"Practitioner/{request.assigned_actor_id}"
            )
        }

    return task


def evidence_request_to_fhir_bundle(
    request: EvidenceRequest,
) -> dict:
    """
    Return ServiceRequest + Task as one FHIR Bundle.
    """

    service_request = evidence_request_to_fhir_service_request(
        request
    )

    task = evidence_request_to_fhir_task(request)

    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": service_request,
            },
            {
                "resource": task,
            },
        ],
    }
