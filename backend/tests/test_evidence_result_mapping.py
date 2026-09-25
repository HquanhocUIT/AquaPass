from app.modules.fhir.evidence_result_mapping import (
    fhir_observation_to_evidence_result,
)


def test_maps_quantity_observation():
    observation = {
        "resourceType": "Observation",
        "id": "OBS-001",
        "status": "final",
        "effectiveDateTime": "2026-09-25T08:30:00+00:00",
        "valueQuantity": {
            "value": 4.2,
            "unit": "mg/L",
        },
        "device": {
            "display": "DO Sensor A",
        },
    }

    result = fhir_observation_to_evidence_result(
        observation,
        request_id="REQ-001",
        incident_id="INC-FISH-001",
        decision_id="DEC-FISH-001",
        evidence_id="EV-005",
        evidence_type="dissolved_oxygen_measurement",
    )

    assert result.result_id == "RESULT-OBS-001"
    assert result.request_id == "REQ-001"
    assert result.incident_id == "INC-FISH-001"
    assert result.decision_id == "DEC-FISH-001"
    assert result.evidence_id == "EV-005"
    assert result.value == "4.2 mg/L"
    assert result.source == "DO Sensor A"
    assert result.reliability == 1.0


def test_maps_string_observation():
    observation = {
        "resourceType": "Observation",
        "id": "OBS-002",
        "status": "final",
        "issued": "2026-09-25T09:00:00Z",
        "valueString": "heavy rainfall detected",
    }

    result = fhir_observation_to_evidence_result(
        observation,
        request_id="REQ-002",
        incident_id="INC-FISH-001",
        decision_id="DEC-FISH-001",
        evidence_id="EV-006",
        evidence_type="rainfall_observation",
    )

    assert result.value == "heavy rainfall detected"
    assert result.source == "FHIR Observation"
    assert result.collected_at.year == 2026


def test_rejects_non_observation():
    observation = {
        "resourceType": "Patient",
        "id": "P-001",
    }

    try:
        fhir_observation_to_evidence_result(
            observation,
            request_id="REQ-001",
            incident_id="INC-FISH-001",
            decision_id="DEC-FISH-001",
            evidence_id="EV-005",
            evidence_type="dissolved_oxygen_measurement",
        )
    except ValueError as exc:
        assert "Observation" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError"
        )