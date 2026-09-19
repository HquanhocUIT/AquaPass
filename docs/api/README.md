# AquaPass API contract

The machine-readable contract is [`openapi.json`](openapi.json), exported from the mounted FastAPI application. Interactive docs are served at `/docs`; the live JSON is at `/openapi.json`.

Implemented Phase 1 endpoints:

| Method | Path | Request | Success | Errors |
| --- | --- | --- | --- | --- |
| GET | `/` | none | 200 service metadata | — |
| GET | `/health` | none | 200 if database reachable | 503 |
| POST | `/incidents` | [`IncidentCreateRequest`](incident-create.md) | 201 incident | 422 |
| GET | `/incidents/{incident_id}` | UUID path | 200 incident + evidence + decisions | 404, 422 |
| POST | `/incidents/{incident_id}/evidence` | [`EvidenceCreateRequest`](evidence-create.md) | 201 evidence | 404, 422 |
| POST | `/incidents/{incident_id}/decisions` | [`DecisionCreateRequest`](decision-create.md) | 201 decision + version 1 | 404, 422 |
| GET | `/decisions/{decision_id}` | UUID path | 200 decision + ordered versions | 404, 422 |

All request/response bodies are JSON. Timestamps sent to write endpoints must include a timezone. A malformed UUID or invalid body returns `422` with FastAPI validation details. Server-managed IDs, status and approval fields cannot be set by the client.

The request lifecycle, ranking and FHIR endpoints described in the root README are **planned**, not included in this OpenAPI file. Do not build the frontend as if those paths already exist. Quân, Sang and Phú should agree on any new shared request/response schema before implementation.

Regenerate after changing routes or schemas:

```powershell
cd backend
python scripts/export_openapi.py
python -m pytest -q
```
