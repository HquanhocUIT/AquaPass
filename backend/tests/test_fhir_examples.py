"""The sample FHIR exchange is linked and clearly simulated."""

import json
from pathlib import Path


EXAMPLES = Path(__file__).resolve().parents[2] / "docs" / "fhir" / "examples"


def test_examples_have_expected_resource_types_and_links() -> None:
    resources = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in EXAMPLES.glob("*.json")
    }
    assert {resource["resourceType"] for resource in resources.values()} == {
        "Location", "Organization", "ServiceRequest", "Task", "Observation"
    }
    assert resources["task"]["focus"]["reference"] == "ServiceRequest/demo-field-do-request"
    assert resources["observation"]["basedOn"][0]["reference"] == (
        "ServiceRequest/demo-field-do-request"
    )
    assert resources["observation"]["subject"]["reference"] == "Location/demo-site-a"
    assert resources["observation"]["valueQuantity"]["value"] == 3.4
    assert "SIMULATED" in resources["observation"]["note"][0]["text"]
