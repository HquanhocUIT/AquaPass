"""Validate the documented examples against HL7's published FHIR R4 JSON Schema."""

import argparse
import hashlib
import io
import json
import urllib.request
import zipfile
from pathlib import Path

from jsonschema import Draft6Validator


SCHEMA_URL = "https://www.hl7.org/fhir/R4/fhir.schema.json.zip"
SCHEMA_SHA256 = "75e5560da3cf503895a44c8ca7af17a83b4cca6c2cb5ba1883d2aec0d1cb5ac6"
EXAMPLES = Path(__file__).resolve().parents[2] / "docs" / "fhir" / "examples"


def load_schema(schema_zip: Path | None = None) -> dict:
    if schema_zip is None:
        with urllib.request.urlopen(SCHEMA_URL, timeout=30) as response:
            content = response.read()
    else:
        content = schema_zip.read_bytes()

    actual_hash = hashlib.sha256(content).hexdigest()
    if actual_hash != SCHEMA_SHA256:
        raise ValueError(f"Unexpected FHIR R4 schema SHA-256: {actual_hash}")

    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        return json.loads(archive.read("fhir.schema.json"))


def validate_examples(schema: dict) -> list[str]:
    Draft6Validator.check_schema(schema)
    validator = Draft6Validator(schema)
    failures: list[str] = []
    resources: dict[str, dict] = {}

    for path in sorted(EXAMPLES.glob("*.json")):
        resource = json.loads(path.read_text(encoding="utf-8"))
        resources[f"{resource['resourceType']}/{resource['id']}"] = resource
        for error in validator.iter_errors(resource):
            failures.append(f"{path.name}: {error.message}")

    request = resources["ServiceRequest/demo-field-do-request"]
    task = resources["Task/demo-field-do-task"]
    observation = resources["Observation/demo-do-observation"]
    references = [
        request["subject"]["reference"],
        task["focus"]["reference"],
        task["for"]["reference"],
        task["owner"]["reference"],
        task["output"][0]["valueReference"]["reference"],
        observation["basedOn"][0]["reference"],
        observation["subject"]["reference"],
    ]
    failures.extend(f"Unresolved example reference: {ref}" for ref in references if ref not in resources)
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--schema-zip",
        type=Path,
        help="Previously downloaded official R4 schema zip; omit to download from HL7",
    )
    args = parser.parse_args()
    failures = validate_examples(load_schema(args.schema_zip))
    if failures:
        raise SystemExit("\n".join(failures))
    print("Five linked examples pass HL7 FHIR R4 JSON Schema structure validation.")


if __name__ == "__main__":
    main()
