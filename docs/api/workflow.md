# Closed-loop workflow API

These endpoints connect the intelligence output to the request and human
approval workflow. They use the tables created by
`supabase/migrations/20260917000300_workflow_foundation.sql`.

## Request lifecycle

```text
DRAFT -> REQUESTED -> ACCEPTED -> COLLECTING -> SUBMITTED
      -> VERIFIED -> INGESTED -> DECISION_UPDATED
```

A request can be rejected while it is `DRAFT`, `REQUESTED` or `ACCEPTED`.
Every transition writes a row to `request_status_events` and `audit_events`.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/requests` | Create a human-reviewable draft request |
| GET | `/api/requests/{request_id}` | Read the request and its timeline |
| POST | `/api/requests/{request_id}/transitions` | Move through the validated lifecycle |
| POST | `/api/requests/assign` | Select a feasible actor from capacity options |
| GET | `/api/requests/{request_id}/fhir` | Return a FHIR `Bundle` containing `ServiceRequest` and `Task` |
| POST | `/api/requests/{request_id}/observation` | Validate an `Observation`, attach it to the same incident, and create the next decision version |
| POST | `/api/decisions/{decision_id}/approval` | Human approval or rejection of the current version |
| GET | `/api/incidents/{incident_id}/audit` | Read the append-only audit trail |

## Intelligence composition

`POST /api/intelligence/overview` combines the existing evidence graph, gap
detection and deterministic ranking contracts into one response for the
frontend decision workspace. It does not make an autonomous decision.

Observation ingestion requires `resourceType`, `id`, an `effectiveDateTime`
or `issued` timestamp, and either `valueQuantity` or `valueString`. Numeric
quantities preserve the value and unit in the original incident's `evidence`
row. The resulting decision version remains `PENDING` until a human calls the
approval endpoint.
