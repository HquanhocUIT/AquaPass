# Evidence submission API — Phase 1

## `POST /incidents/{incident_id}/evidence`

This endpoint attaches one prototype evidence item to an **existing** incident. The UUID in the URL is the only incident identifier accepted; a client-supplied `incident_id` in the JSON body is rejected.

Example request for a simulated field measurement:

```json
{
  "code": "FIELD_DISSOLVED_OXYGEN",
  "evidence_type": "FIELD_MEASUREMENT",
  "value_numeric": 3.4,
  "unit": "mg/L",
  "source": "Demo field team",
  "observed_at": "2026-09-19T09:00:00+07:00",
  "provenance": {"method": "portable DO meter"}
}
```

For a textual report, send `value_text` instead of `value_numeric` and omit `unit`. Exactly one value field is required. A numeric value requires a unit. `source` and a timezone-aware `observed_at` are required. The same `code` may be used for later measurements; each observation receives a distinct UUID.

Success: HTTP `201 Created` with the new evidence row, including `id`, the URL's `incident_id`, `state: "KNOWN"`, `reliability_score: 0.5`, `is_simulated: true`, and `provenance.simulated: true`. These are provisional MVP defaults, not a validated scientific confidence rating. Clients cannot override these server-managed fields.

An unknown incident UUID returns HTTP `404` with `{"detail":"Incident not found"}`. Invalid data or a malformed UUID returns HTTP `422` without inserting a row.

The existing Supabase schema is defined by `supabase/migrations/20260917000100_foundation.sql`. Automated write tests use a disposable in-memory SQLite database; do not use Swagger's Execute button for this POST against the shared Supabase project merely to test it. Authentication and audit logging must be added before public deployment.
