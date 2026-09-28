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

This repository contains a backend contract and local verification. A public
production deployment still needs a hosting provider, secret configuration,
authentication and a frontend deployment; those are intentionally not
invented by the MVP backend.
