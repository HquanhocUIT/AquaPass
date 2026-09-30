from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from math import isfinite
from typing import Any
from urllib.parse import quote
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.tables import (
    decision_versions,
    decisions,
    evidence,
    evidence_gaps,
    evidence_requests,
    hypotheses,
    incidents,
    request_status_events,
    request_attachments,
)
from app.modules.audit.audit_store import append_audit_event, list_audit_events
from app.modules.decision.approval import (
    approve_decision,
    create_approval,
    reject_decision,
)
from app.modules.decision.hypothesis_engine import (
    EvidenceImpact,
    Hypothesis,
    update_hypotheses,
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
    EvidenceRequestAttachmentResponse,
    EvidenceRequestCreateRequest,
    EvidenceRequestResponse,
    ObservationIngestResponse,
    RequestStatusTransitionRequest,
)


router = APIRouter(tags=["workflow"])

_HYPOTHESIS_IMPACT_URL = (
    "https://aquapass.example/fhir/StructureDefinition/hypothesis-impact"
)

MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024
MAX_ATTACHMENT_COUNT = 5
MAX_ATTACHMENT_TOTAL_SIZE = 25 * 1024 * 1024
_ATTACHMENT_TYPES = {
    ".png": ("image/png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
    ".jpg": ("image/jpeg", lambda data: data.startswith(b"\xff\xd8\xff")),
    ".jpeg": ("image/jpeg", lambda data: data.startswith(b"\xff\xd8\xff")),
    ".webp": ("image/webp", lambda data: len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"),
    ".pdf": ("application/pdf", lambda data: data.startswith(b"%PDF-")),
    ".csv": ("text/csv", lambda data: _is_utf8_text(data)),
    ".txt": ("text/plain", lambda data: _is_utf8_text(data)),
}


def _is_utf8_text(data: bytes) -> bool:
    try:
        return b"\x00" not in data and bool(data.decode("utf-8-sig").strip())
    except UnicodeDecodeError:
        return False


def _attachment_metadata_rows(db: Session, request_id: UUID) -> list[dict[str, Any]]:
    rows = db.execute(
        select(
            request_attachments.c.id,
            request_attachments.c.filename,
            request_attachments.c.content_type,
            request_attachments.c.size_bytes,
            request_attachments.c.sha256,
            request_attachments.c.created_at,
        )
        .where(request_attachments.c.request_id == request_id)
        .order_by(request_attachments.c.created_at, request_attachments.c.id)
    ).mappings().all()
    return [dict(row) for row in rows]


def _validate_attachment(upload: UploadFile, data: bytes) -> tuple[str, str]:
    filename = (upload.filename or "").replace("\\", "/").split("/")[-1].strip()
    if not filename or len(filename) > 255 or any(ord(char) < 32 for char in filename):
        raise HTTPException(status_code=422, detail="Attachment filename is invalid")
    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    spec = _ATTACHMENT_TYPES.get(extension)
    if spec is None:
        raise HTTPException(
            status_code=415,
            detail="Use PNG, JPG, WEBP, PDF, CSV or TXT files",
        )
    expected_type, signature_check = spec
    provided_type = (upload.content_type or "application/octet-stream").lower()
    accepted_declared_types = {
        expected_type,
        "application/octet-stream",
        "application/x-pdf" if expected_type == "application/pdf" else expected_type,
        "application/vnd.ms-excel" if expected_type == "text/csv" else expected_type,
        "text/plain" if expected_type == "text/csv" else expected_type,
    }
    if provided_type not in accepted_declared_types or not signature_check(data):
        raise HTTPException(status_code=415, detail="File contents do not match the selected file type")
    return filename, expected_type


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
        "attachments": _attachment_metadata_rows(db, row["id"]),
    }


def _get_request(db: Session, request_id: UUID) -> dict[str, Any]:
    row = db.execute(
        select(evidence_requests).where(evidence_requests.c.id == request_id)
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Evidence request not found")
    return dict(row)


def _parse_hypothesis_impact(observation: dict[str, Any]) -> dict[str, str] | None:
    extensions = observation.get("extension") or []
    if not isinstance(extensions, list):
        raise ValueError("Observation.extension must be an array")
    matches = [
        item for item in extensions
        if isinstance(item, dict) and item.get("url") == _HYPOTHESIS_IMPACT_URL
    ]
    if not matches:
        return None
    if len(matches) != 1:
        raise ValueError("Observation must contain at most one hypothesis-impact extension")

    nested = matches[0].get("extension")
    if not isinstance(nested, list):
        raise ValueError("Hypothesis-impact extension must contain child extensions")
    values: dict[str, str] = {}
    value_fields = {
        "hypothesisCode": "valueCode",
        "direction": "valueCode",
        "rationale": "valueString",
    }
    for item in nested:
        if not isinstance(item, dict) or item.get("url") not in value_fields:
            raise ValueError("Hypothesis impact contains an invalid child extension")
        key = item["url"]
        if key in values:
            raise ValueError(f"Hypothesis impact contains duplicate {key}")
        value = item.get(value_fields[key])
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Hypothesis impact {key} must contain a non-empty string")
        values[key] = value.strip()

    hypothesis_code = values.get("hypothesisCode", "")
    direction = values.get("direction", "").lower()
    rationale = values.get("rationale", "")
    if not hypothesis_code or not rationale:
        raise ValueError(
            "Hypothesis impact requires hypothesisCode, direction and rationale"
        )
    if direction not in {"supports", "corroborates", "contradicts"}:
        raise ValueError("Hypothesis impact direction must be supports, corroborates or contradicts")
    if len(rationale) > 1000:
        raise ValueError("Hypothesis impact rationale must be 1000 characters or fewer")
    return {
        "hypothesis_code": hypothesis_code,
        "direction": direction,
        "rationale": rationale,
    }


def _support_state(score: float) -> str:
    if score >= 0.66:
        return "stronger"
    if score <= 0.34:
        return "weaker"
    return "unchanged"


def _record_status_event(
    db: Session,
    *,
    request_id: UUID,
    from_status: str | None,
    to_status: str,
    actor_name: str,
    note: str | None,
) -> None:
    occurred_at = datetime.now(timezone.utc)
    previous_occurred_at = db.execute(
        select(request_status_events.c.occurred_at)
        .where(request_status_events.c.request_id == request_id)
        .order_by(request_status_events.c.occurred_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if previous_occurred_at is not None:
        if previous_occurred_at.tzinfo is None:
            previous_occurred_at = previous_occurred_at.replace(tzinfo=timezone.utc)
        if occurred_at <= previous_occurred_at:
            occurred_at = previous_occurred_at + timedelta(microseconds=1)

    db.execute(
        insert(request_status_events).values(
            id=uuid4(),
            request_id=request_id,
            from_status=from_status,
            to_status=to_status,
            actor_name=actor_name,
            note=note,
            occurred_at=occurred_at,
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


@router.post(
    "/api/requests/{request_id}/attachments",
    response_model=list[EvidenceRequestAttachmentResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_request_attachments(
    request_id: UUID,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    request = _get_request(db, request_id)
    if request["status"] != "DRAFT":
        raise HTTPException(status_code=409, detail="Attachments can only be added to a draft request")
    existing_count = int(
        db.scalar(
            select(func.count()).select_from(request_attachments).where(
                request_attachments.c.request_id == request_id
            )
        )
        or 0
    )
    existing_size = int(
        db.scalar(
            select(func.coalesce(func.sum(request_attachments.c.size_bytes), 0)).where(
                request_attachments.c.request_id == request_id
            )
        )
        or 0
    )
    if not files or existing_count + len(files) > MAX_ATTACHMENT_COUNT:
        raise HTTPException(
            status_code=422,
            detail=f"A request can include between 1 and {MAX_ATTACHMENT_COUNT} files in total",
        )

    prepared: list[dict[str, Any]] = []
    total_size = existing_size
    previous_created_at = db.scalar(
        select(func.max(request_attachments.c.created_at)).where(
            request_attachments.c.request_id == request_id
        )
    )
    created_at = datetime.now(timezone.utc)
    if previous_created_at is not None:
        if previous_created_at.tzinfo is None:
            previous_created_at = previous_created_at.replace(tzinfo=timezone.utc)
        if created_at <= previous_created_at:
            created_at = previous_created_at + timedelta(microseconds=1)
    for upload in files:
        data = await upload.read(MAX_ATTACHMENT_SIZE + 1)
        if not data:
            raise HTTPException(status_code=422, detail="Empty files cannot be attached")
        if len(data) > MAX_ATTACHMENT_SIZE:
            raise HTTPException(status_code=413, detail="Each attachment must be 10 MB or smaller")
        total_size += len(data)
        if total_size > MAX_ATTACHMENT_TOTAL_SIZE:
            raise HTTPException(status_code=413, detail="Attachments must total 25 MB or less")
        filename, content_type = _validate_attachment(upload, data)
        prepared.append(
            {
                "id": uuid4(),
                "request_id": request_id,
                "filename": filename,
                "content_type": content_type,
                "size_bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "data": data,
                "created_at": created_at + timedelta(microseconds=len(prepared)),
            }
        )

    try:
        db.execute(insert(request_attachments), prepared)
        append_audit_event(
            db,
            incident_id=request["incident_id"],
            entity_type="evidence_request",
            entity_id=request_id,
            event_type="REQUEST_ATTACHMENT_ADDED",
            actor_name=request["requested_by"],
            payload={
                "attachment_count": len(prepared),
                "attachment_ids": [str(item["id"]) for item in prepared],
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    saved_rows = db.execute(
        select(
            request_attachments.c.id,
            request_attachments.c.filename,
            request_attachments.c.content_type,
            request_attachments.c.size_bytes,
            request_attachments.c.sha256,
            request_attachments.c.created_at,
        ).where(request_attachments.c.id.in_([item["id"] for item in prepared]))
    ).mappings().all()
    saved_by_id = {row["id"]: dict(row) for row in saved_rows}
    return [saved_by_id[item["id"]] for item in prepared]


@router.get("/api/requests/{request_id}/attachments/{attachment_id}")
def download_request_attachment(
    request_id: UUID,
    attachment_id: UUID,
    db: Session = Depends(get_db),
) -> Response:
    row = db.execute(
        select(request_attachments).where(
            request_attachments.c.id == attachment_id,
            request_attachments.c.request_id == request_id,
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return Response(
        content=row["data"],
        media_type=row["content_type"],
        headers={
            "Content-Disposition": "attachment; filename*=UTF-8''" + quote(row["filename"], safe=""),
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


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
        hypothesis_impact = _parse_hypothesis_impact(observation)
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
                    "hypothesis_impact": hypothesis_impact,
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
            select(evidence.c.id, evidence.c.code, evidence.c.state, evidence.c.reliability_score)
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
        hypothesis_updates: list[dict[str, Any]] = []
        if hypothesis_impact is not None:
            hypothesis_row = db.execute(
                select(hypotheses).where(
                    hypotheses.c.incident_id == row["incident_id"],
                    hypotheses.c.code == hypothesis_impact["hypothesis_code"],
                    hypotheses.c.status == "ACTIVE",
                )
            ).mappings().first()
            if hypothesis_row is None:
                raise HTTPException(
                    status_code=422,
                    detail="Hypothesis impact references no active hypothesis on this incident",
                )

            previous_score = float(hypothesis_row["support_score"])
            updated_hypothesis = update_hypotheses(
                [
                    Hypothesis(
                        hypothesis_id=str(hypothesis_row["id"]),
                        name=str(hypothesis_row["title"]),
                        status=_support_state(previous_score),
                    )
                ],
                [
                    EvidenceImpact(
                        evidence_id=str(evidence_id),
                        hypothesis_id=str(hypothesis_row["id"]),
                        direction=hypothesis_impact["direction"],
                        rationale=hypothesis_impact["rationale"],
                    )
                ],
            )[0]
            score_delta = (
                0.10
                if hypothesis_impact["direction"] in {"supports", "corroborates"}
                else -0.10
            )
            next_score = round(max(0.0, min(1.0, previous_score + score_delta)), 4)
            db.execute(
                update(hypotheses)
                .where(hypotheses.c.id == hypothesis_row["id"])
                .values(support_score=next_score)
            )
            hypothesis_updates.append(
                {
                    "hypothesis_id": str(hypothesis_row["id"]),
                    "hypothesis_code": str(hypothesis_row["code"]),
                    "title": str(hypothesis_row["title"]),
                    "previous_status": updated_hypothesis.previous_status,
                    "new_status": updated_hypothesis.new_status,
                    "previous_support_score": previous_score,
                    "new_support_score": next_score,
                    "direction": hypothesis_impact["direction"],
                    "triggering_evidence_id": str(evidence_id),
                    "rationale": hypothesis_impact["rationale"],
                }
            )
            performers = observation.get("performer") or []
            impact_actor = (
                performers[0].get("display")
                if performers and isinstance(performers[0], dict)
                else None
            ) or "observation-ingestion"
            append_audit_event(
                db,
                incident_id=row["incident_id"],
                entity_type="hypothesis",
                entity_id=UUID(str(hypothesis_row["id"])),
                event_type="HYPOTHESIS_UPDATED",
                actor_name=str(impact_actor),
                payload=hypothesis_updates[-1],
            )
        evidence_snapshot = {
            "evidence_ids": [str(item["id"]) for item in evidence_rows],
            "evidence_codes": [str(item["code"]) for item in evidence_rows],
            "triggering_evidence_id": str(evidence_id),
            "uncertainty_score": uncertainty.score,
            "hypothesis_updates": hypothesis_updates,
        }
        next_version = int(version["version_number"]) + 1
        impact_summary = ""
        if hypothesis_updates:
            impact_summary = (
                " Human interpretation: "
                + hypothesis_updates[0]["hypothesis_code"]
                + " "
                + hypothesis_updates[0]["new_status"]
                + " — "
                + hypothesis_updates[0]["rationale"].rstrip(". ")
                + "."
            )
        db.execute(
            insert(decision_versions).values(
                id=uuid4(),
                decision_id=row["decision_id"],
                version_number=next_version,
                summary=(
                    f"New evidence {row['requested_evidence_code']} received from "
                    f"{result.source}.{impact_summary} Human approval is required."
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
        "hypothesis_updates": hypothesis_updates,
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
