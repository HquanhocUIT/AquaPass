from __future__ import annotations

from math import isfinite
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.tables import (
    decision_versions,
    decisions,
    evidence,
    evidence_gaps,
    evidence_requests,
    incidents,
    request_status_events,
)
from app.modules.audit.audit_store import append_audit_event, list_audit_events
from app.modules.decision.approval import (
    approve_decision,
    create_approval,
    reject_decision,
)
from app.modules.decision.uncertainty_engine import (
    DecisionEvidence,
    evaluate_uncertainty,
)
from app.modules.fhir.evidence_result_mapping import (
    fhir_observation_to_evidence_result,
)
from app.modules.orchestration.actor_assignment import assign_collection_actor
from app.modules.orchestration.evidence_request import (
    EvidenceRequest,
    EvidenceRequestStatus,
    reject_evidence_request,
    transition_evidence_request,
)
from app.modules.fhir.evidence_mapping import evidence_request_to_fhir_bundle
from app.modules.constraints.constraint_engine import (
    ActorCapacity,
    EvidenceRequirement,
)
from app.schemas.workflow import (
    ActorAssignmentRequest,
    ActorAssignmentResponse,
    AuditEventResponse,
    DecisionApprovalRequest,
    DecisionApprovalResponse,
    EvidenceRequestCreateRequest,
    EvidenceRequestResponse,
    ObservationIngestResponse,
    RequestStatusTransitionRequest,
)


router = APIRouter(tags=["workflow"])


_PRIORITY_TO_DOMAIN = {
    "ROUTINE": "low",
    "URGENT": "medium",
    "ASAP": "high",
    "STAT": "high",
}


def _domain_request(row: dict[str, Any]) -> EvidenceRequest:
    try:
        domain_status = EvidenceRequestStatus(str(row["status"]).lower())
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Unknown request status") from exc

    return EvidenceRequest(
        request_id=str(row["id"]),
        incident_id=str(row["incident_id"]),
        decision_id=str(row["decision_id"]),
        evidence_id=str(row["requested_evidence_code"]),
        evidence_type=str(row["requested_evidence_code"]),
        purpose=str(row["purpose"]),
        priority=_PRIORITY_TO_DOMAIN.get(str(row["priority"]), "low"),
        decision_value=1.0,
        expected_cost=float(row["estimated_cost"] or 0.0),
        expected_time_minutes=int(row["estimated_minutes"] or 0),
        status=domain_status,
        assigned_actor_id=(
            str(row["assigned_actor_id"])
            if row["assigned_actor_id"] is not None
            else None
        ),
        created_at=row["created_at"],
    )


def _status_event_rows(db: Session, request_id: UUID) -> list[dict[str, Any]]:
    rows = db.execute(
        select(request_status_events)
        .where(request_status_events.c.request_id == request_id)
        .order_by(request_status_events.c.occurred_at, request_status_events.c.id)
    ).mappings().all()
    return [dict(row) for row in rows]


def _request_response(db: Session, row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "status_events": _status_event_rows(db, row["id"]),
    }


def _get_request(db: Session, request_id: UUID) -> dict[str, Any]:
    row = db.execute(
        select(evidence_requests).where(evidence_requests.c.id == request_id)
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Evidence request not found")
    return dict(row)


def _record_status_event(
    db: Session,
    *,
    request_id: UUID,
    from_status: str | None,
    to_status: str,
    actor_name: str,
    note: str | None,
) -> None:
    db.execute(
        insert(request_status_events).values(
            id=uuid4(),
            request_id=request_id,
            from_status=from_status,
            to_status=to_status,
            actor_name=actor_name,
            note=note,
        )
    )


def _apply_domain_transition(
    db: Session,
    *,
    row: dict[str, Any],
    target_status: str,
    actor_name: str,
    note: str | None,
) -> dict[str, Any]:
    request = _domain_request(row)
    previous_status = request.status.value.upper()

    if target_status == "REJECTED":
        updated = reject_evidence_request(request)
    else:
        updated = transition_evidence_request(
            request,
            EvidenceRequestStatus(target_status.lower()),
        )

    db.execute(
        update(evidence_requests)
        .where(evidence_requests.c.id == UUID(str(row["id"])))
        .values(status=target_status, updated_at=func.now())
    )
    _record_status_event(
        db,
        request_id=UUID(str(row["id"])),
        from_status=previous_status,
        to_status=target_status,
        actor_name=actor_name,
        note=note,
    )
    append_audit_event(
        db,
        incident_id=row["incident_id"],
        entity_type="evidence_request",
        entity_id=UUID(str(row["id"])),
        event_type="REQUEST_STATUS_CHANGED",
        actor_name=actor_name,
        payload={"from": previous_status, "to": target_status, "note": note},
    )
    return {
        **row,
        "status": target_status,
    }


@router.post(
    "/api/requests",
    response_model=EvidenceRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_request(
    payload: EvidenceRequestCreateRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Create a draft request linked to one incident and decision."""
    incident_exists = db.scalar(
        select(incidents.c.id).where(incidents.c.id == payload.incident_id)
    )
    if incident_exists is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    decision_exists = db.execute(
        select(decisions.c.id)
        .where(
            decisions.c.id == payload.decision_id,
            decisions.c.incident_id == payload.incident_id,
        )
    ).scalar_one_or_none()
    if decision_exists is None:
        raise HTTPException(status_code=404, detail="Decision not found for incident")

    if payload.evidence_gap_id is not None:
        gap_exists = db.execute(
            select(evidence_gaps.c.id)
            .where(
                evidence_gaps.c.id == payload.evidence_gap_id,
                evidence_gaps.c.decision_id == payload.decision_id,
                evidence_gaps.c.incident_id == payload.incident_id,
            )
        ).scalar_one_or_none()
        if gap_exists is None:
            raise HTTPException(status_code=404, detail="Evidence gap not found for decision")

    if payload.assigned_actor_id is not None:
        from app.db.tables import actors

        actor_exists = db.scalar(
            select(actors.c.id).where(actors.c.id == payload.assigned_actor_id)
        )
        if actor_exists is None:
            raise HTTPException(status_code=404, detail="Assigned actor not found")

    request_id = uuid4()
    try:
        row = dict(
            db.execute(
                insert(evidence_requests)
                .values(
                    id=request_id,
                    incident_id=payload.incident_id,
                    decision_id=payload.decision_id,
                    evidence_gap_id=payload.evidence_gap_id,
                    assigned_actor_id=payload.assigned_actor_id,
                    requested_evidence_code=payload.requested_evidence_code,
                    purpose=payload.purpose,
                    priority=payload.priority,
                    status="DRAFT",
                    estimated_cost=payload.estimated_cost,
                    estimated_minutes=payload.estimated_minutes,
                    requested_by=payload.requested_by,
                )
                .returning(*evidence_requests.c)
            ).mappings().one()
        )
        _record_status_event(
            db,
            request_id=request_id,
            from_status=None,
            to_status="DRAFT",
            actor_name=payload.requested_by,
            note="Request created and awaiting human confirmation.",
        )
        append_audit_event(
            db,
            incident_id=payload.incident_id,
            entity_type="evidence_request",
            entity_id=request_id,
            event_type="REQUEST_CREATED",
            actor_name=payload.requested_by,
            payload={"status": "DRAFT", "evidence_code": payload.requested_evidence_code},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return _request_response(db, row)


@router.post("/api/requests/assign", response_model=ActorAssignmentResponse)
def assign_actor(payload: ActorAssignmentRequest) -> ActorAssignmentResponse:
    requirement = EvidenceRequirement(
        evidence_id=payload.evidence_id,
        required_capability=payload.required_capability,
        required_location=payload.required_location,
    )
    actors = [
        ActorCapacity(**actor.model_dump())
        for actor in payload.actors
    ]
    assignment = assign_collection_actor(
        requirement=requirement,
        actors=actors,
        decision_deadline=payload.decision_deadline,
    )
    return ActorAssignmentResponse(
        evidence_id=assignment.evidence_id,
        actor_id=assignment.actor_id,
        actor_name=assignment.actor_name,
        feasible=assignment.feasible,
        location=assignment.location,
        expected_delay_minutes=assignment.expected_delay_minutes,
        reasons=list(assignment.reasons),
    )


@router.get("/api/requests/{request_id}", response_model=EvidenceRequestResponse)
def get_request(request_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    return _request_response(db, _get_request(db, request_id))


@router.post("/api/requests/{request_id}/transitions", response_model=EvidenceRequestResponse)
def transition_request(
    request_id: UUID,
    payload: RequestStatusTransitionRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    row = _get_request(db, request_id)
    try:
        updated = _apply_domain_transition(
            db,
            row=row,
            target_status=payload.to_status,
            actor_name=payload.actor_name,
            note=payload.note,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise

    return _request_response(db, updated)


@router.get("/api/requests/{request_id}/fhir")
def get_fhir_request(request_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = _get_request(db, request_id)
    request = _domain_request(row)
    return evidence_request_to_fhir_bundle(request)


def _observation_value(observation: dict[str, Any]) -> tuple[float | None, str | None, str | None]:
    quantity = observation.get("valueQuantity")
    if quantity is not None:
        value = quantity.get("value")
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(float(value)):
            raise ValueError("Observation valueQuantity.value must be a finite number")
        return float(value), None, quantity.get("unit")

    text_value = observation.get("valueString")
    if text_value is None or not str(text_value).strip():
        raise ValueError("Observation must contain valueQuantity or valueString")
    return None, str(text_value), None


@router.post(
    "/api/requests/{request_id}/observation",
    response_model=ObservationIngestResponse,
)
def ingest_observation(
    request_id: UUID,
    observation: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Attach a validated FHIR Observation to the request's original incident."""
    row = _get_request(db, request_id)
    current_status = str(row["status"])
    if current_status not in {"SUBMITTED", "VERIFIED"}:
        raise HTTPException(
            status_code=409,
            detail="Observation can only be ingested after submission or verification",
        )

    evidence_id = uuid4()
    try:
        value_numeric, value_text, unit = _observation_value(observation)
        result = fhir_observation_to_evidence_result(
            observation,
            request_id=str(request_id),
            incident_id=str(row["incident_id"]),
            decision_id=str(row["decision_id"]),
            evidence_id=str(evidence_id),
            evidence_type=str(row["requested_evidence_code"]),
        )

        db.execute(
            insert(evidence).values(
                id=evidence_id,
                incident_id=row["incident_id"],
                code=row["requested_evidence_code"],
                evidence_type=row["requested_evidence_code"],
                state="KNOWN",
                value_numeric=value_numeric,
                value_text=value_text,
                unit=unit,
                source=result.source,
                observed_at=result.collected_at,
                reliability_score=result.reliability,
                provenance={
                    "fhir_observation_id": observation.get("id"),
                    "request_id": str(request_id),
                    "simulated": bool(observation.get("meta", {}).get("tag")),
                },
                is_simulated=bool(observation.get("meta", {}).get("tag")),
            )
        )

        domain_request = _domain_request(row)
        if domain_request.status == EvidenceRequestStatus.SUBMITTED:
            row = _apply_domain_transition(
                db,
                row=row,
                target_status="VERIFIED",
                actor_name="observation-ingestion",
                note="FHIR Observation passed structural validation.",
            )
            domain_request = _domain_request(row)
        row = _apply_domain_transition(
            db,
            row=row,
            target_status="INGESTED",
            actor_name="observation-ingestion",
            note="Observation attached to the original incident.",
        )

        version = db.execute(
            select(decision_versions)
            .where(decision_versions.c.decision_id == row["decision_id"])
            .order_by(decision_versions.c.version_number.desc())
        ).mappings().first()
        if version is None:
            raise HTTPException(status_code=409, detail="Decision has no version to update")

        evidence_rows = db.execute(
            select(evidence.c.id, evidence.c.state, evidence.c.reliability_score)
            .where(evidence.c.incident_id == row["incident_id"])
            .order_by(evidence.c.observed_at, evidence.c.id)
        ).mappings().all()
        uncertainty = evaluate_uncertainty(
            [
                DecisionEvidence(
                    evidence_id=str(item["id"]),
                    state={
                        "KNOWN": "available",
                        "MISSING": "missing",
                        "CONFLICTING": "conflicting",
                        "STALE": "stale",
                        "LOW_CONFIDENCE": "unreliable",
                    }.get(str(item["state"]), "unreliable"),
                    reliability=float(item["reliability_score"]),
                )
                for item in evidence_rows
            ],
        )
        evidence_snapshot = {
            "evidence_ids": [str(item["id"]) for item in evidence_rows],
            "triggering_evidence_id": str(evidence_id),
            "uncertainty_score": uncertainty.score,
        }
        next_version = int(version["version_number"]) + 1
        db.execute(
            insert(decision_versions).values(
                id=uuid4(),
                decision_id=row["decision_id"],
                version_number=next_version,
                summary=(
                    f"New evidence {row['requested_evidence_code']} received from "
                    f"{result.source}; human approval is required."
                ),
                uncertainty_level=uncertainty.level,
                evidence_snapshot=evidence_snapshot,
                approval_status="PENDING",
                created_by="observation-ingestion",
            )
        )
        db.execute(
            update(decisions)
            .where(decisions.c.id == row["decision_id"])
            .values(current_version=next_version, updated_at=func.now())
        )
        row = _apply_domain_transition(
            db,
            row=row,
            target_status="DECISION_UPDATED",
            actor_name="observation-ingestion",
            note=f"Decision version {next_version} created for human approval.",
        )
        db.execute(
            update(evidence_requests)
            .where(evidence_requests.c.id == request_id)
            .values(result_evidence_id=evidence_id, updated_at=func.now())
        )
        append_audit_event(
            db,
            incident_id=row["incident_id"],
            entity_type="evidence",
            entity_id=evidence_id,
            event_type="EVIDENCE_INGESTED",
            actor_name="observation-ingestion",
            payload={"request_id": str(request_id), "observation_id": observation.get("id")},
        )
        append_audit_event(
            db,
            incident_id=row["incident_id"],
            entity_type="decision",
            entity_id=row["decision_id"],
            event_type="DECISION_VERSION_CREATED",
            actor_name="observation-ingestion",
            payload={"version": next_version, "uncertainty_level": uncertainty.level},
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return {
        "observation_id": str(observation.get("id")),
        "evidence_id": evidence_id,
        "incident_id": row["incident_id"],
        "request_id": request_id,
        "decision_id": row["decision_id"],
        "request_status": "DECISION_UPDATED",
        "decision_version": next_version,
        "uncertainty_level": uncertainty.level,
        "value": result.value,
    }


@router.post(
    "/api/decisions/{decision_id}/approval",
    response_model=DecisionApprovalResponse,
)
def approve_decision_version(
    decision_id: UUID,
    payload: DecisionApprovalRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    decision = db.execute(
        select(decisions).where(decisions.c.id == decision_id)
    ).mappings().first()
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")

    version = db.execute(
        select(decision_versions)
        .where(
            decision_versions.c.decision_id == decision_id,
            decision_versions.c.version_number == decision["current_version"],
        )
    ).mappings().first()
    if version is None:
        raise HTTPException(status_code=404, detail="Current decision version not found")
    if version["approval_status"] != "PENDING":
        raise HTTPException(status_code=409, detail="Current decision version has already been reviewed")

    approval = create_approval(
        approval_id=str(uuid4()),
        decision_id=str(decision_id),
        decision_version=int(version["version_number"]),
    )
    try:
        if payload.action == "APPROVE":
            reviewed = approve_decision(
                approval,
                reviewer_id=payload.reviewer_id,
                reason=payload.reason,
            )
        else:
            reviewed = reject_decision(
                approval,
                reviewer_id=payload.reviewer_id,
                reason=payload.reason or "Decision rejected.",
            )
        final_status = reviewed.status.value.upper()
        db.execute(
            update(decision_versions)
            .where(decision_versions.c.id == version["id"])
            .values(approval_status=final_status, approved_by=payload.reviewer_id)
        )
        db.execute(
            update(decisions)
            .where(decisions.c.id == decision_id)
            .values(status=final_status, updated_at=func.now())
        )
        append_audit_event(
            db,
            incident_id=decision["incident_id"],
            entity_type="decision",
            entity_id=decision_id,
            event_type=f"DECISION_{final_status}",
            actor_name=payload.reviewer_id,
            payload={"version": version["version_number"], "reason": payload.reason},
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise

    return {
        "decision_id": decision_id,
        "version_number": version["version_number"],
        "status": final_status,
        "reviewer_id": payload.reviewer_id,
        "reason": payload.reason,
    }


@router.get("/api/incidents/{incident_id}/audit", response_model=list[AuditEventResponse])
def get_incident_audit(incident_id: UUID, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    exists = db.scalar(select(incidents.c.id).where(incidents.c.id == incident_id))
    if exists is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return list_audit_events(db, incident_id=incident_id)
