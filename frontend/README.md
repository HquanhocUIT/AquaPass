# AquaPass frontend

The decision workspace follows the saved incident from evidence review through
human approval:

`Incident → Evidence state and graph → Candidate ranking → Evidence request → FHIR Observation → Decision version → Human review`

The `/cases` page lists incidents returned by the API. Opening a case leads to
its Decision page; Evidence, Evidence map, Ranking, Workflow and Activity each
have a dedicated route. The case workspace reads
the saved decision, evidence, hypotheses, operational gaps, collection actors,
ranked profiles and audit history from the backend. Request transitions,
Observation ingestion and approval write to the database. API failures are
shown directly; the interface does not replace them with local sample state.

Candidate parameters in `data/demo/candidate_evidence.csv` are prototype
assumptions for the simulated scenario. Scores use the documented deterministic
weights and are not presented as calibrated probabilities or real field data.
An operator records whether a result supports or contradicts a hypothesis and
must give a rationale; the system does not infer causality from the measurement.

See [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) for interface tokens and
[`docs/api/workflow.md`](../docs/api/workflow.md) for the API contract.

## Run locally

Node.js 20.9 or newer is required.

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. Configure `NEXT_PUBLIC_API_URL` if the backend is
not at `http://127.0.0.1:8000`.

## Verify

```powershell
npm run typecheck
npm run build
```
