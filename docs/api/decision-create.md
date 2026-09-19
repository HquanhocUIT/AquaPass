# Decision creation API — Phase 1

## `POST /incidents/{incident_id}/decisions`

Creates a pending decision and its first version for an existing incident. The incident ID comes only from the URL.

```json
{
  "question": "Should the authority escalate the field investigation?",
  "deadline": "2026-09-20T10:00:00+07:00"
}
```

The question must not be blank. The deadline must include a timezone and be in the future. Server-managed fields such as status, version, approval, and evidence snapshot cannot be provided by the client.

On success, HTTP `201 Created` returns the decision (`status: "PENDING"`, `current_version: 1`) and a nested `version` (`version_number: 1`, `approval_status: "PENDING"`, `uncertainty_level: "HIGH"`, `created_by: "system"`). The version's `evidence_snapshot` contains `evidence_ids` and `evidence_codes` from the incident's evidence at creation time; both are empty arrays if there is no evidence. `HIGH` and the summary are provisional MVP defaults, not an automated scientific judgment or human approval.

Both rows are committed in one database transaction. If creating version 1 fails, the decision is rolled back too. An unknown incident returns HTTP `404`; an invalid body or malformed incident UUID returns HTTP `422`.

Automated tests write only to an in-memory SQLite database. Do not run this POST through Swagger against the shared Supabase project just for a test. This endpoint has no authentication or audit trail yet; keep the API local until those protections are added.
