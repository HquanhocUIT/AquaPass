from datetime import datetime

from app.modules.evidence.gap_detector import (
    EvidenceGraphRecord,
    GapPriority,
    detect_evidence_gaps,
)
from app.modules.orchestration.evidence_request import (
    EvidenceRequestStatus,
    create_evidence_request,
    transition_evidence_request,
)
from app.modules.orchestration.evidence_result import (
    create_evidence_result,
)
from app.modules.decision.decision_version import (
    create_decision_version,
    create_next_decision_version,
)
from app.modules.decision.decision_comparison import (
    compare_decision_versions,
)
from app.modules.decision.approval import (
    ApprovalStatus,
    approve_decision,
    create_approval,
)


def test_full_aquapass_closed_loop():
    incident_id = "INC-FISH-001"
    decision_id = "DEC-FISH-001"

    # ---------------------------------------------------------
    # 1. Evidence Graph -> Evidence Gap
    # ---------------------------------------------------------

    graph_records = [
        EvidenceGraphRecord(
            graph_id="G-001",
            incident_id=incident_id,
            decision_id=decision_id,
            source_node="EV-005",
            source_type="evidence",
            relationship="missing_for",
            target_node="HYP-LOW-DO",
            target_type="hypothesis",
            confidence=0.90,
            state="missing",
            rationale="Direct DO measurement is needed to assess the low-DO hypothesis.",
        )
    ]

    gaps = detect_evidence_gaps(graph_records)

    assert len(gaps) == 1

    gap = gaps[0]

    assert gap.decision_id == decision_id
    assert gap.evidence_id == "EV-005"
    assert gap.priority == GapPriority.HIGH

    # ---------------------------------------------------------
    # 2. Evidence Gap -> Evidence Request
    # ---------------------------------------------------------

    request = create_evidence_request(
        request_id="REQ-005",
        incident_id=incident_id,
        decision_id=decision_id,
        evidence_id=gap.evidence_id,
        evidence_type="water_quality",
        purpose=(
            "Collect direct dissolved oxygen evidence "
            "to evaluate the low-DO hypothesis."
        ),
        priority=gap.priority.value,
        decision_value=0.95,
        expected_cost=0.20,
        expected_time_minutes=30,
        assigned_actor_id="ACTOR-FIELD-001",
    )

    assert request.status == EvidenceRequestStatus.DRAFT
    assert request.assigned_actor_id == "ACTOR-FIELD-001"

    # ---------------------------------------------------------
    # 3. Request lifecycle
    # ---------------------------------------------------------

    request = transition_evidence_request(
        request,
        EvidenceRequestStatus.REQUESTED,
    )

    request = transition_evidence_request(
        request,
        EvidenceRequestStatus.ACCEPTED,
    )

    request = transition_evidence_request(
        request,
        EvidenceRequestStatus.COLLECTING,
    )

    assert request.status == EvidenceRequestStatus.COLLECTING

    # ---------------------------------------------------------
    # 4. Evidence Collection -> Result
    # ---------------------------------------------------------

    result = create_evidence_result(
        result_id="RES-005",
        request_id=request.request_id,
        incident_id=incident_id,
        decision_id=decision_id,
        evidence_id="EV-005",
        evidence_type="water_quality",
        value="Dissolved oxygen measured at 2.1 mg/L",
        source="field_sensor",
        reliability=0.92,
        collected_at=datetime.now(),
    )

    assert result.request_id == request.request_id
    assert result.evidence_id == "EV-005"
    assert result.reliability == 0.92

    # ---------------------------------------------------------
    # 5. Existing Decision Version
    # ---------------------------------------------------------

    decision_v1 = create_decision_version(
        decision_id=decision_id,
        version=1,
        incident_id=incident_id,
        uncertainty=0.80,
        uncertainty_level="high",
        hypothesis_summary="Low DO may contribute to fish mortality.",
    )

    # ---------------------------------------------------------
    # 6. Evidence updates Decision Version
    # ---------------------------------------------------------

    decision_v2 = create_next_decision_version(
        decision_v1,
        uncertainty=0.45,
        uncertainty_level="medium",
        hypothesis_summary=(
            "Low DO is increasingly supported by direct measurement."
        ),
        triggering_evidence_id=result.evidence_id,
    )

    assert decision_v2.version == 2
    assert decision_v2.triggering_evidence_id == "EV-005"

    # ---------------------------------------------------------
    # 7. Compare Decision Versions
    # ---------------------------------------------------------

    comparison = compare_decision_versions(
        decision_v1,
        decision_v2,
    )

    assert comparison.decision_id == decision_id
    assert comparison.from_version == 1
    assert comparison.to_version == 2
    assert comparison.triggering_evidence_id == "EV-005"
    assert comparison.uncertainty_before == 0.80
    assert comparison.uncertainty_after == 0.45
    assert comparison.uncertainty_change == 0.35
    assert comparison.hypothesis_changed is True

    # ---------------------------------------------------------
    # 8. Human Approval
    # ---------------------------------------------------------

    approval = create_approval(
        approval_id="APR-002",
        decision_id=decision_id,
        decision_version=decision_v2.version,
    )

    assert approval.status == ApprovalStatus.PENDING

    approval = approve_decision(
        approval,
        reviewer_id="USER-HUMAN-001",
        reason="Evidence supports the updated decision state.",
    )

    assert approval.status == ApprovalStatus.APPROVED
    assert approval.reviewer_id == "USER-HUMAN-001"