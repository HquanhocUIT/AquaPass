# Backend

Backend dùng kiến trúc modular monolith.

- Quân phụ trách database, API, FHIR, vòng đời yêu cầu và lưu lịch sử.
- Sang phụ trách evidence graph, AI, ranking, constraints và đánh giá.

Mỗi module chỉ nên làm một việc rõ ràng. Không tách microservice trong thời gian hackathon.

## First read-only API

`GET /incidents/{incident_id}` reads the Supabase PostgreSQL tables. The response contract is in `docs/api/incident-read.md`; FastAPI exposes OpenAPI at `/openapi.json`.

Create a local `.env` in the repository root with `DATABASE_URL` copied from Supabase **Connect → Session pooler** (or Direct connection if your network supports IPv6). Use a SQLAlchemy URL beginning with `postgresql+psycopg://` and append `?sslmode=require`. Never commit this URL or the database password. The `backend/.venv` directory and `.env` are ignored by Git.

From `backend/`, run `python -m pip install -r requirements.txt` and `python -m app`. The server does not create tables or run the seed on startup. Tables are managed by SQL migrations in `supabase/migrations/`; demo rows are managed by `supabase/seed.sql`.

For an isolated local demonstration without Supabase credentials, run
`python scripts/bootstrap_local_demo.py` from `backend/` before `python -m app`.
It creates an SQLite database plus an attached `public` schema file and inserts
the simulated fish-mortality scenario with a 48-hour review window. The script
refuses non-SQLite database URLs and is idempotent: it inserts missing seed IDs
without resetting workflow data. It refreshes only the initial pending decision's
demo deadline when no request has been started. Both SQLite files are ignored
by Git.

The incident, evidence, decision, intelligence, request lifecycle, FHIR ingestion, approval and audit routes are mounted in `app.main`. The database-backed intelligence workspace reads saved evidence, hypotheses, gaps and actors, then composes the deterministic graph and ranking modules with the candidate catalog in `data/demo/candidate_evidence.csv`.

`POST /incidents` is now implemented; see `docs/api/incident-create.md`. It is not authenticated yet, so keep the server local and do not run the POST example against the shared Supabase project just to test it. Run `python -m pytest -q` from `backend/` instead; those write tests use a disposable SQLite database.

`POST /incidents/{incident_id}/evidence` is implemented with the same safety boundary; see `docs/api/evidence-create.md`. It attaches a new simulated record to the incident ID in the URL, returning `201`, `404`, or `422` as documented.

`POST /incidents/{incident_id}/decisions` creates a pending decision and version 1 in one transaction; see `docs/api/decision-create.md`. The first version snapshots the incident's existing evidence. Its uncertainty and summary are provisional defaults, not human approval. Test writes against disposable SQLite only.

`GET /decisions/{decision_id}` reads a decision with all saved versions in order; see `docs/api/decision-read.md`. It does not modify Supabase data.

## Reproducible Phase 1 setup

1. Copy `.env.example` to `.env`, then set `DATABASE_URL` to the Supabase Postgres **session pooler** URI with `postgresql+psycopg://` and `?sslmode=require`. Keep `.env` local. If the password has URI special characters, percent-encode them.
2. On a new project, run every SQL file in `supabase/migrations/` in filename order in Supabase SQL Editor, then run `supabase/seed.sql`. On an existing database, apply every migration that has not been run yet; the request workflow and its attachment table are added by `20260917000300_workflow_foundation.sql` and `20260917000400_request_attachments.sql`. **Do not** run `backend/schema.sql` or the old `app/db/bootstrap.py` against Supabase.
3. From `backend/`, run `python -m pip install -r requirements.txt`, then `python scripts/check_demo.py` to verify the tables and seed without changing them.
4. Run `python -m app`; visit `http://127.0.0.1:8000/health` for liveness, `http://127.0.0.1:8000/health/readiness` for database reachability and `http://127.0.0.1:8000/docs` for the API. The server does not execute migrations or seed automatically.

The seed is additive and deliberately does **not** reset a demo after users create more data or decision versions. Use a disposable Supabase project when a clean demo is required. API examples currently have no authentication; bind locally and never expose the write endpoints publicly.

The versioned API contract is `docs/api/openapi.json`. Regenerate it with `python scripts/export_openapi.py` after route/schema changes. The mounted workflow endpoints are documented in `docs/api/workflow.md`; they persist request events, FHIR ingestion, human hypothesis interpretations, decision versions, approvals and audit history through the workflow migration.
