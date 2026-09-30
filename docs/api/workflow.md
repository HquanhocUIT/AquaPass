# Closed-loop workflow API

These endpoints connect the intelligence output to the request and human
approval workflow. They use the tables created by
`supabase/migrations/20260917000300_workflow_foundation.sql` and
`supabase/migrations/20260917000400_request_attachments.sql`.

## Request lifecycle

```text
DRAFT -> REQUESTED -> ACCEPTED -> COLLECTING -> SUBMITTED
      -> VERIFIED -> INGESTED -> DECISION_UPDATED
```

A request can be rejected while it is `DRAFT`, `REQUESTED` or `ACCEPTED`.
Every transition writes a row to `request_status_events` and `audit_events`.

Attachments are stored in `public.evidence_request_attachments` as database
binary data with a filename, media type, byte count and SHA-256 digest. Uploads
accept PNG, JPG, WEBP, PDF, CSV and TXT; each file is limited to 10 MB, with up
to five files and 25 MB total per request. File signatures are checked, and new
attachments are accepted only while the request is a draft. The API returns
attachment metadata with the request; the download route returns the saved
content as an attachment.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/requests` | Create a human-reviewable draft request |
| GET | `/api/requests/{request_id}` | Read the request and its timeline |
| POST | `/api/requests/{request_id}/attachments` | Upload supporting images or files to a draft request |
| GET | `/api/requests/{request_id}/attachments/{attachment_id}` | Download a request attachment |
| POST | `/api/requests/{request_id}/transitions` | Move through the validated lifecycle |
| POST | `/api/requests/assign` | Select a feasible actor from capacity options |
| GET | `/api/requests/{request_id}/fhir` | Return a FHIR `Bundle` containing `ServiceRequest` and `Task` |
| POST | `/api/requests/{request_id}/observation` | Validate an `Observation`, attach it to the same incident, and create the next decision version |
| POST | `/api/decisions/{decision_id}/approval` | Human approval or rejection of the current version |
| GET | `/api/incidents/{incident_id}/audit` | Read the append-only audit trail |

## Intelligence composition

`POST /api/intelligence/overview` combines the existing evidence graph, gap
detection and deterministic ranking contracts into one response for the
lower-level contract. The database-backed workspace uses
`GET /api/intelligence/incidents/{incident_id}/overview`. That route loads the
incident's latest decision, saved evidence, active hypotheses, open gaps and
available actors; it joins them with the matching rows in
`data/demo/candidate_evidence.csv`, classifies evidence, builds graph
relationships, applies capability and deadline feasibility checks, and ranks
feasible candidates. A missing incident returns `404`; an incident without a
decision or configured graph relationships returns `409`.

The ranking formula and weights are deterministic prototype choices:

```text
score = 0.40 × decision_value
      + 0.25 × reliability
      + 0.15 × feasibility
      − 0.10 × cost
      − 0.10 × time
```

All catalog dimensions are normalized from `0` to `1`. Feasibility also applies
a hard gate: candidates with no capable available actor or with an estimated
collection time beyond the decision deadline are excluded from the ranked
results and returned with an explanation. Catalog values are scenario
assumptions, not learned weights or calibrated probabilities.

Observation ingestion requires `resourceType`, `id`, an `effectiveDateTime`
or `issued` timestamp, and either `valueQuantity` or `valueString`. Numeric
quantities preserve the value and unit in the original incident's `evidence`
row. The resulting decision version remains `PENDING` until a human calls the
approval endpoint.
The new version's `evidence_snapshot` includes evidence IDs and codes, the
triggering evidence ID, the prototype uncertainty score, and any recorded
hypothesis updates. `GET /decisions/{decision_id}` returns this complete
version history after ingestion and review.

An Observation may include one AquaPass `hypothesis-impact` extension with
`hypothesisCode`, `direction` (`supports`, `corroborates` or `contradicts`) and
a non-empty human-written `rationale`. AquaPass validates that the hypothesis
is active on the same incident, stores the operator interpretation with the
evidence provenance, adjusts the prototype support score by `+0.10` or
`−0.10` (bounded to `0..1`), and records `HYPOTHESIS_UPDATED` in the audit log.
This field captures a human interpretation; it does not claim statistical or
causal inference. Omitting the extension leaves the hypothesis unchanged.
