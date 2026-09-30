from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.evidence import detect_gaps
from app.api.routes.ranking import rank_evidence_candidates
from app.core.config import PROJECT_ROOT
from app.db.session import get_db
from app.db.tables import actors, decisions, evidence, evidence_gaps, hypotheses, incidents
from app.modules.evidence.evidence_state import (
    EvidenceClassification,
    EvidenceRecord,
    EvidenceState,
    classify_evidence,
)
from app.schemas.evidence import DetectEvidenceGapsRequest, EvidenceGraphRecordRequest
from app.schemas.intelligence import RankEvidenceRequest
from app.schemas.intelligence import EvidenceCandidateRequest
from app.schemas.workflow import (
    IntelligenceOverviewRequest,
    IntelligenceOverviewResponse,
    IntelligenceStateResponse,
)


router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])


@router.post("/overview", response_model=IntelligenceOverviewResponse)
def intelligence_overview(payload: IntelligenceOverviewRequest) -> IntelligenceOverviewResponse:
    """Return graph, state, gap and ranking data in one frontend call.

    Sang's deterministic graph and ranking modules remain the source of truth;
    this route only composes their existing contracts for the decision workspace.
    """
    gap_response = detect_gaps(
        DetectEvidenceGapsRequest(records=payload.records)
    )
    ranking_response = rank_evidence_candidates(
        RankEvidenceRequest(candidates=payload.candidates)
    )

    states_by_id: dict[str, IntelligenceStateResponse] = {}
    for record in payload.records:
        states_by_id[record.source_node] = IntelligenceStateResponse(
            evidence_id=record.source_node,
            state=record.state,
            reason=record.rationale,
        )

    return IntelligenceOverviewResponse(
        graph=[record.model_dump() for record in payload.records],
        states=list(states_by_id.values()),
        gaps=[gap.model_dump() for gap in gap_response.gaps],
        ranking=ranking_response.model_dump(),
    )


def _candidate_profiles(incident_type: str) -> list[dict[str, Any]]:
    catalog_path = PROJECT_ROOT / "data" / "demo" / "candidate_evidence.csv"
    with catalog_path.open(encoding="utf-8", newline="") as catalog_file:
        rows = list(csv.DictReader(catalog_file))

    exact = [row for row in rows if row["incident_type"] == incident_type]
    selected = exact or [row for row in rows if row["incident_type"] == "*"]
    return [
        {
            "incident_type": row["incident_type"],
            "evidence_id": row["evidence_id"],
            "evidence_code": row["evidence_code"],
            "candidate_name": row["candidate_name"],
            "target_hypotheses": [value for value in row["target_hypotheses"].split(";") if value],
            "related_evidence_codes": [value for value in row["related_evidence_codes"].split(";") if value],
            "relationship": row["relationship"],
            "confidence": float(row["confidence"]),
            "decision_value": float(row["decision_value"]),
            "reliability": float(row["reliability"]),
            "feasibility": float(row["feasibility"]),
            "cost": float(row["cost"]),
            "time": float(row["time"]),
            "estimated_cost": float(row["estimated_cost"]),
            "estimated_minutes": int(row["estimated_minutes"]),
            "priority": row["priority"],
            "required_capability": row["required_capability"],
            "purpose": row["purpose"],
        }
        for row in selected
    ]


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _classify_database_evidence(row: dict[str, Any]) -> EvidenceClassification:
    stored_state = str(row["state"]).upper()
    provenance = row.get("provenance") or {}
    classification = classify_evidence(
        EvidenceRecord(
            evidence_id=str(row["id"]),
            summary=str(row["value_text"] or row["code"]),
            observed_at=row["observed_at"],
            is_available=stored_state != "MISSING",
            reliability=float(row["reliability_score"]),
            verification_status=(
                "invalid" if stored_state in {"LOW_CONFIDENCE", "UNRELIABLE"}
                else str(provenance.get("verification_status", "valid"))
            ),
            has_conflict=stored_state == "CONFLICTING",
        )
    )
    if stored_state == "STALE":
        return EvidenceClassification(
            evidence_id=str(row["id"]),
            state=EvidenceState.STALE,
            reason="Evidence is marked stale in the incident record.",
        )
    if stored_state == "UNRELIABLE":
        return EvidenceClassification(
            evidence_id=str(row["id"]),
            state=EvidenceState.UNRELIABLE,
            reason="Evidence is marked unreliable in the incident record.",
        )
    return classification


@router.get(
    "/incidents/{incident_id}/overview",
    response_model=IntelligenceOverviewResponse,
)
def get_incident_intelligence_overview(
    incident_id: UUID,
    db: Session = Depends(get_db),
) -> IntelligenceOverviewResponse:
    """Compose current database evidence with the deterministic intelligence modules."""
    incident = db.execute(
        select(incidents).where(incidents.c.id == incident_id)
    ).mappings().first()
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    decision = db.execute(
        select(decisions)
        .where(decisions.c.incident_id == incident_id)
        .order_by(decisions.c.created_at.desc(), decisions.c.id)
    ).mappings().first()
    if decision is None:
        raise HTTPException(status_code=409, detail="Incident has no decision")

    evidence_rows = db.execute(
        select(evidence)
        .where(evidence.c.incident_id == incident_id)
        .order_by(evidence.c.observed_at, evidence.c.id)
    ).mappings().all()
    hypothesis_rows = db.execute(
        select(hypotheses)
        .where(hypotheses.c.incident_id == incident_id)
        .order_by(hypotheses.c.code, hypotheses.c.id)
    ).mappings().all()
    gap_rows = db.execute(
        select(evidence_gaps)
        .where(
            evidence_gaps.c.incident_id == incident_id,
            evidence_gaps.c.decision_id == decision["id"],
            evidence_gaps.c.status == "OPEN",
        )
    ).mappings().all()
    actor_rows = db.execute(
        select(actors).order_by(actors.c.name, actors.c.id)
    ).mappings().all()

    profiles = _candidate_profiles(str(incident["incident_type"]))
    evidence_by_code: dict[str, list[dict[str, Any]]] = {}
    for row in evidence_rows:
        evidence_by_code.setdefault(str(row["code"]), []).append(dict(row))
    classifications_by_id = {
        str(row["id"]): _classify_database_evidence(dict(row))
        for row in evidence_rows
    }

    active_hypothesis_codes = {
        str(row["code"])
        for row in hypothesis_rows
        if str(row["status"]) == "ACTIVE"
    }
    graph_records: list[EvidenceGraphRecordRequest] = []
    states_by_id: dict[str, IntelligenceStateResponse] = {}

    for profile in profiles:
        for code in profile["related_evidence_codes"]:
            for row in evidence_by_code.get(code, []):
                classification = classifications_by_id[str(row["id"])]
                states_by_id[str(row["id"])] = IntelligenceStateResponse(
                    evidence_id=str(row["id"]),
                    state=classification.state.value,
                    reason=classification.reason,
                )
                for hypothesis_code in profile["target_hypotheses"]:
                    if hypothesis_code not in active_hypothesis_codes:
                        continue
                    graph_records.append(
                        EvidenceGraphRecordRequest(
                            graph_id="observed-" + str(row["id"]) + "-" + hypothesis_code,
                            incident_id=str(incident_id),
                            decision_id=str(decision["id"]),
                            source_node=str(row["id"]),
                            source_type="evidence",
                            relationship=profile["relationship"],
                            target_node=hypothesis_code,
                            target_type="hypothesis",
                            confidence=float(row["reliability_score"]),
                            state=classification.state.value,
                            rationale=(
                                str(row["value_text"] or row["value_numeric"] or row["code"])
                                + " from "
                                + str(row["source"])
                            ),
                        )
                    )

    gap_ids_by_code = {str(row["code"]): str(row["id"]) for row in gap_rows}
    candidate_requests: list[EvidenceCandidateRequest] = []
    actor_payloads = [dict(row) for row in actor_rows]
    now = datetime.now(timezone.utc)
    minutes_remaining = max(
        0,
        int((_as_utc(decision["deadline"]) - now).total_seconds() / 60),
    )
    response_profiles: list[dict[str, Any]] = []

    for profile in profiles:
        capability = str(profile["required_capability"])
        capability_actors = [
            row for row in actor_payloads
            if bool(row["available"])
            and int(row["capacity"]) > 0
            and (not capability or capability in (row["capabilities"] or []))
        ]
        location_actors = [
            row for row in capability_actors
            if row["location_name"] == incident["location_name"]
        ]
        turnaround_actors = [
            row for row in location_actors
            if row["turnaround_minutes"] is None
            or int(row["turnaround_minutes"]) <= minutes_remaining
        ]
        exceeds_window = int(profile["estimated_minutes"]) > minutes_remaining
        actor_exceeds_window = bool(location_actors) and not turnaround_actors
        too_late = exceeds_window or actor_exceeds_window
        feasible = bool(turnaround_actors) and not too_late if capability else not too_late
        infeasibility_reason = None
        if exceeds_window:
            infeasibility_reason = "The estimated collection time exceeds the decision window."
        elif capability and not capability_actors:
            infeasibility_reason = "No available actor has the required collection capability."
        elif capability and not location_actors:
            infeasibility_reason = "No available actor matches the incident location."
        elif capability and actor_exceeds_window:
            infeasibility_reason = "The available actor's turnaround exceeds the decision window."

        candidate_requests.append(
            EvidenceCandidateRequest(
                evidence_id=str(profile["evidence_id"]),
                candidate_name=str(profile["candidate_name"]),
                decision_value=float(profile["decision_value"]),
                reliability=float(profile["reliability"]),
                feasibility=float(profile["feasibility"]),
                cost=float(profile["cost"]),
                time=float(profile["time"]),
                is_feasible=feasible,
                infeasibility_reason=infeasibility_reason,
            )
        )

        evidence_code = str(profile["evidence_code"])
        current_rows = evidence_by_code.get(evidence_code, [])
        current_is_usable = any(
            classifications_by_id[str(row["id"])].state == EvidenceState.AVAILABLE
            for row in current_rows
        )
        if not current_is_usable:
            for hypothesis_code in profile["target_hypotheses"]:
                target_type = "hypothesis" if hypothesis_code in active_hypothesis_codes else "decision"
                target_node = hypothesis_code if target_type == "hypothesis" else str(decision["id"])
                graph_id = "missing-" + evidence_code + "-" + target_node
                graph_records.append(
                    EvidenceGraphRecordRequest(
                        graph_id=graph_id,
                        incident_id=str(incident_id),
                        decision_id=str(decision["id"]),
                        source_node=str(profile["evidence_id"]),
                        source_type="evidence",
                        relationship="missing_for",
                        target_node=target_node,
                        target_type=target_type,
                        confidence=float(profile["confidence"]),
                        state="missing",
                        rationale=str(profile["purpose"]),
                    )
                )
                states_by_id[str(profile["evidence_id"])] = IntelligenceStateResponse(
                    evidence_id=str(profile["evidence_id"]),
                    state="missing",
                    reason=str(profile["purpose"]),
                )

        response_profiles.append(
            {
                **profile,
                "database_gap_id": gap_ids_by_code.get(evidence_code),
                "feasible": feasible,
                "infeasibility_reason": infeasibility_reason,
            }
        )

    if not graph_records:
        raise HTTPException(status_code=409, detail="No graph relationships are configured for this incident")

    gap_response = detect_gaps(DetectEvidenceGapsRequest(records=graph_records))
    ranking_response = rank_evidence_candidates(
        RankEvidenceRequest(candidates=candidate_requests)
    )

    return IntelligenceOverviewResponse(
        graph=[record.model_dump() for record in graph_records],
        states=list(states_by_id.values()),
        gaps=[
            {
                **gap.model_dump(),
                "database_gap_id": gap_ids_by_code.get(gap.evidence_id),
            }
            for gap in gap_response.gaps
        ],
        ranking=ranking_response.model_dump(),
        profiles=response_profiles,
        hypotheses=[
            {
                "id": str(row["id"]),
                "code": str(row["code"]),
                "title": str(row["title"]),
                "description": str(row["description"]),
                "status": str(row["status"]),
                "support_score": float(row["support_score"]),
            }
            for row in hypothesis_rows
        ],
        actors=[
            {
                "id": str(row["id"]),
                "code": str(row["code"]),
                "name": str(row["name"]),
                "actor_type": str(row["actor_type"]),
                "capabilities": list(row["capabilities"] or []),
                "location_name": row["location_name"],
                "available": bool(row["available"]),
                "capacity": int(row["capacity"]),
                "turnaround_minutes": row["turnaround_minutes"],
            }
            for row in actor_payloads
        ],
    )
