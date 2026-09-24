def test_full_aquapass_closed_loop():

    # 1. Existing incident
    incident_id = "INC-FISH-001"

    # 2. Pending decision
    decision_id = "DEC-FISH-001"

    # 3. Detect gap
    gaps = detect_evidence_gaps(...)

    assert gaps

    # 4. Rank evidence
    ranked = rank_evidence(...)

    assert ranked[0].selected

    # 5. Create request
    request = create_evidence_request(...)

    assert request.status == DRAFT

    # 6. Request lifecycle
    request = transition(...)

    # requested
    # accepted
    # collecting
    # submitted
    # verified
    # ingested
    # decision_updated

    # 7. Actor constraint
    constraint = evaluate_evidence_requirement(...)

    assert constraint.feasible

    # 8. Submit result
    result = create_evidence_result(...)

    # 9. Update decision
    decision_v2 = update_decision(...)

    assert decision_v2.version == 2

    # 10. Uncertainty decreases
    assert ...

    # 11. Human approval
    approval = approve_decision(...)

    assert approval.status == APPROVED