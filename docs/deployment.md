# Deployment and technical handoff

## Required configuration

Copy `.env.example` to `.env` and set `DATABASE_URL` to the Supabase session
pooler URI in SQLAlchemy format:

```text
postgresql+psycopg://USER:PASSWORD@HOST:5432/postgres?sslmode=require
```

Keep `.env` local. Never place the password, Supabase secret key or service
role key in the repository or in `.env.example`.

## Supabase setup

Run the files in `supabase/migrations/` in filename order, then run
`supabase/seed.sql`. The seed is additive and provides the fish-mortality demo,
its hypotheses, one field actor and the initial evidence gap. Verify the
installation with:

```powershell
cd backend
python scripts/check_demo.py
```

The check is read-only. It does not create tables or reset data.

## Local demo without Supabase

The repository can run the same API contract against an isolated SQLite
database for review. From `backend/`, run:

```powershell
python scripts/bootstrap_local_demo.py
python -m app
```

The bootstrap creates only local SQLite files, inserts a simulated incident
with a 48-hour review window, and leaves existing request and decision history
intact on later runs. It refreshes the untouched initial decision's deadline if
you rerun it before creating a request. The database URL must remain SQLite for
this script; it refuses to seed a hosted database. Run the frontend in a second
terminal with `npm run dev` from `frontend/`.

## Run and verify the API

```powershell
cd backend
python -m pip install -r requirements.txt
python -m app
```

Open `http://127.0.0.1:8000/docs`. The repeatable backend verification is:

```powershell
python -m pytest -q
python scripts/export_openapi.py
```

The demo flow is: create/read incident → create decision → create request →
move request through its lifecycle → inspect FHIR `ServiceRequest`/`Task` →
submit FHIR `Observation` → receive evidence on the same incident → create a
new pending decision version → human approval → inspect audit history.

## Hosted deployment target

The repository includes a Render Blueprint at `render.yaml` and a backend
Dockerfile at `backend/Dockerfile`. The intended hosted arrangement is:

- Supabase for PostgreSQL;
- Render for the FastAPI backend;
- Vercel for the Next.js frontend.

### Deploy the backend to Render

1. Push the repository to GitHub, then create a new Render Blueprint from the
   repository root. Render reads `render.yaml` and builds `backend/Dockerfile`.
2. Set `DATABASE_URL` to the Supabase session-pooler URL using the
   `postgresql+psycopg://` SQLAlchemy format from the Supabase setup above.
3. Set `CORS_ORIGINS` to the final Vercel URL. Keep `LLM_ENABLED=false` unless
   Gemini is intentionally configured for the hosted demo.
4. Apply the Supabase migrations and seed before opening the frontend.
5. Verify `https://<render-service>.onrender.com/health` and
   `/health/readiness`.

### Deploy the frontend to Vercel

1. Import the same repository into Vercel.
2. Set the project root directory to `frontend`; Vercel detects Next.js and
   uses `npm run build`.
3. Set `NEXT_PUBLIC_API_URL` to the Render service URL, then redeploy.
4. Copy the final Vercel URL back into Render's `CORS_ORIGINS` and redeploy
   the backend.

The write API still needs authentication/authorization before this becomes a
public production service. Until that protection is added, use the hosted
deployment only as a restricted review environment and do not expose it as a
trusted public system.
