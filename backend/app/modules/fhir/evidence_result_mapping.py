from __future__ import annotations

from datetime import datetime
from math import isfinite

from app.modules.orchestration.evidence_result import (
    EvidenceResult,
)


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def fhir_observation_to_evidence_result(
    observation: dict,
    *,
    request_id: str,
    incident_id: str,
    decision_id: str,
    evidence_id: str,
    evidence_type: str,
) -> EvidenceResult:
    """
    Convert a FHIR Observation into an AquaPass EvidenceResult.

    This adapter intentionally performs only structural mapping.
    It does not interpret the clinical/environmental meaning of
    the observation.
    """

    if observation.get("resourceType") != "Observation":
        raise ValueError(
            "observation must have resourceType='Observation'"
        )

    observation_id = observation.get("id")

    if not observation_id:
        raise ValueError(
            "FHIR Observation must contain an id"
        )

    value_quantity = observation.get("valueQuantity")

    if value_quantity is not None:
        raw_value = value_quantity.get("value")
        if (
            not isinstance(raw_value, (int, float))
            or isinstance(raw_value, bool)
            or not isfinite(float(raw_value))
        ):
            raise ValueError(
                "FHIR Observation valueQuantity.value must be a finite number"
            )

        value = str(raw_value)

        unit = value_quantity.get("unit")

        if unit:
            value = f"{value} {unit}"
    else:
        value_string = observation.get("valueString")

        if value_string is None:
            raise ValueError(
                "FHIR Observation must contain valueQuantity "
                "or valueString"
            )

        value = str(value_string)

    source = observation.get(
        "device",
        {},
    ).get(
        "display",
        "FHIR Observation",
    )

    effective_at = (
        observation.get("effectiveDateTime")
        or observation.get("issued")
    )

    if not isinstance(effective_at, str) or not effective_at:
        raise ValueError(
            "FHIR Observation must contain "
            "effectiveDateTime or issued"
        )

    reliability = 1.0
    for extension in observation.get("extension") or []:
        if isinstance(extension, dict) and "valueDecimal" in extension:
            reliability = extension["valueDecimal"]
            break

    if (
        not isinstance(reliability, (int, float))
        or isinstance(reliability, bool)
        or not isfinite(float(reliability))
        or not 0.0 <= float(reliability) <= 1.0
    ):
        raise ValueError(
            "FHIR Observation reliability must be between 0.0 and 1.0"
        )

    return EvidenceResult(
        result_id=f"RESULT-{observation_id}",
        request_id=request_id,
        incident_id=incident_id,
        decision_id=decision_id,
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        value=value,
        source=source,
        reliability=float(reliability),
        collected_at=_parse_datetime(effective_at),
    )
