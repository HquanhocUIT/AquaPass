# AquaPass API contract

The machine-readable contract is [`openapi.json`](openapi.json), exported
from the mounted FastAPI application. Interactive docs are served at `/docs`;
the live JSON is at `/openapi.json`.

| Method | Path | Request | Success | Errors |
| --- | --- | --- | --- | --- |
| GET | `/` | none | 200 service metadata | — |
| GET | `/health` | none | 200 if the service is ready | 503 |
| GET | `/health/readiness` | none | 200 if database is reachable | 503 |
| POST | `/incidents` | [`IncidentCreateRequest`](incident-create.md) | 201 incident | 422 |
| GET | `/incidents/{incident_id}` | UUID path | 200 incident + evidence + decisions | 404, 422 |
| POST | `/incidents/{incident_id}/evidence` | [`EvidenceCreateRequest`](evidence-create.md) | 201 evidence | 404, 422 |
| POST | `/incidents/{incident_id}/decisions` | [`DecisionCreateRequest`](decision-create.md) | 201 decision + version 1 | 404, 422 |
| GET | `/decisions/{decision_id}` | UUID path | 200 decision + ordered versions | 404, 422 |
| POST | `/api/intelligence/overview` | graph records + candidates | 200 graph, states, gaps and ranking | 422 |
| POST | `/api/requests` | incident, decision and evidence request | 201 draft request | 404, 422 |
| GET | `/api/requests/{request_id}` | UUID path | 200 request + lifecycle events | 404, 422 |
| POST | `/api/requests/{request_id}/transitions` | target status + actor | 200 updated request | 404, 409, 422 |
| POST | `/api/requests/assign` | requirement + actor capacities | 200 assignment decision | 422 |
| GET | `/api/requests/{request_id}/fhir` | UUID path | 200 ServiceRequest + Task Bundle | 404, 422 |
| POST | `/api/requests/{request_id}/observation` | FHIR Observation | 200 same-incident evidence + decision version | 404, 409, 422 |
| POST | `/api/decisions/{decision_id}/approval` | approve/reject + reviewer | 200 reviewed version | 404, 409, 422 |
| GET | `/api/incidents/{incident_id}/audit` | UUID path | 200 append-only events | 404, 422 |

All request/response bodies are JSON. Timestamps sent to write endpoints must
include a timezone. A malformed UUID or invalid body returns `422` with
FastAPI validation details. Server-managed IDs, status and approval fields
cannot be set by the client.

The closed-loop workflow contract is documented in
[`workflow.md`](workflow.md). The API requires human approval and clients
must not write directly to Supabase tables.

Regenerate after changing routes or schemas:

```powershell
cd backend
python scripts/export_openapi.py
python -m pytest -q
```
