# Incident creation API — Phase 1

## `POST /incidents`

This endpoint opens a new incident. Unlike `GET`, it **writes to the database**. Do not use it to test against the shared Supabase project until the team agrees on the test data. For now, automated tests use a disposable in-memory SQLite database.

Request body:

```json
{
  "title": "Fish mortality at Site B",
  "description": "SIMULATED DATA: Fish mortality reported.",
  "incident_type": "FISH_MORTALITY",
  "location_name": "Demo Urban Lake - Site B",
  "latitude": 10.77,
  "longitude": 106.70,
  "severity": "HIGH",
  "occurred_at": "2026-09-19T08:00:00+07:00"
}
```

Required: `title`, `description`, `incident_type`, `location_name`, and `occurred_at`. Coordinates are optional. `severity` defaults to `MEDIUM` and must be `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`. `occurred_at` must include a timezone offset.

Success: HTTP `201 Created`. The response contains the new `id`, all incident fields, `status: "OPEN"`, and server-generated `created_at`/`updated_at` timestamps. The client cannot supply `id`, `status`, `created_at`, or `updated_at`; extra fields and invalid values return HTTP `422`.

The database table is defined by `supabase/migrations/20260917000100_foundation.sql`. The Python mapping in `backend/app/db/tables.py` only builds queries; it does not create or alter Supabase tables.

Security note: authentication/authorization is not implemented yet. The development server defaults to `127.0.0.1`; do not expose this write endpoint publicly until access control and audit logging are added. FastAPI provides the machine-readable contract at `/openapi.json` and the interactive UI at `/docs`.
