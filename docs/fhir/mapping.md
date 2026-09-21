# AquaPass → FHIR R4 mapping (Phase 1 design)

These **simulated examples** illustrate an exchange boundary, not a live FHIR endpoint or a certified OneAquaHealth profile. The base specification used here is FHIR R4 (4.0.1): [ServiceRequest](https://hl7.org/fhir/R4/servicerequest.html), [Task](https://hl7.org/fhir/R4/task.html), [Observation](https://hl7.org/fhir/R4/observation.html). The [OneAquaHealth implementation guide](https://build.fhir.org/ig/hl7-eu/oah/) is a draft; profile alignment must be reviewed separately before claiming conformance.

| AquaPass field/state | FHIR R4 element | Rule in this prototype |
| --- | --- | --- |
| `evidence_requests.id` | `ServiceRequest.identifier` | Stable business identifier; the FHIR `id` is an exchange-layer ID. |
| `evidence_requests.requested_evidence_code` | `ServiceRequest.code.coding` | Local AquaPass code until an agreed environmental terminology is selected. |
| `evidence_requests.purpose` | `ServiceRequest.reasonCode.text` | Human-readable reason tied to the pending decision. |
| `evidence_requests.priority` | `ServiceRequest.priority` | Lower-case FHIR code: routine, urgent, asap or stat. |
| `evidence_requests.status` | `ServiceRequest.status` and `Task.status` | Request authorization and execution are different state machines; do not copy one code into both. |
| `evidence_requests.assigned_actor_id` | `Task.owner` | Resolve actor to an Organization/Device reference; demo uses Organization. |
| `evidence_requests.incident_id` + `decision_id` | local correlation via `ServiceRequest.identifier` lookup | FHIR has no native AquaPass Incident/Decision resource. The adapter resolves the request identifier to the original database row; IDs are also shown in the demo note only. Do not misuse Patient or clinical diagnosis fields. |
| `evidence_requests.result_evidence_id` | `Task.output.valueReference` and `Observation.basedOn` | Link the returned Observation to its Task and ServiceRequest. The adapter then writes evidence to the original incident. |
| `evidence.code` | `Observation.code` | Same local code as the requested evidence; map to standard terminology when validated. |
| `evidence.value_numeric` + `unit` | `Observation.valueQuantity` | Unit uses UCUM `mg/L` in this demo. Text evidence would use `valueString` instead. |
| `evidence.observed_at` | `Observation.effectiveDateTime` | Timestamp with timezone. |
| `evidence.source` + `provenance` | `Observation.method`, `performer`, `Provenance` (future) | Preserve source/method in AquaPass even if only a subset crosses this sample boundary. |
| Monitoring site | `Location` referenced by `ServiceRequest.subject`, `Task.for`, `Observation.subject` | R4 permits Location as the subject of these environmental observations; no fictitious Patient is created. |

The files in [`examples/`](examples/) are a linked snapshot of **one hypothetical request**, not rows already inserted by `seed.sql`. The seed intentionally stops before request creation so the demo can show a human confirmation. Example references resolve within this folder: ServiceRequest → Location; Task → ServiceRequest, Location, Organization, Observation; Observation → ServiceRequest, Location. FHIR `Observation.status = final` means the *measurement result* is final, not that AquaPass's decision is approved.

`https://aquapass.example.org/...` is a documentation-only namespace and not a published terminology server. This sample does not assert conformance to a custom OAH profile or real-world ecological validity. Human review, permissions, standard terminology and full profile validation remain separate integration work.

To repeat the base R4 structural validation, install `backend/requirements.txt`, then run `python scripts/validate_fhir_examples.py` from `backend/`. The script downloads HL7's [FHIR R4 JSON Schema](https://www.hl7.org/fhir/R4/downloads.html), verifies its SHA-256 and checks every example plus local references. Use `--schema-zip PATH` to validate offline with a copy of the official archive. JSON Schema alone does not verify terminology bindings, external references, profile rules or OAH-IG conformance.
