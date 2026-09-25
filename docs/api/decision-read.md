# Decision history API

## `GET /decisions/{decision_id}`

Read one decision and every saved version. Use the decision `id` returned by `POST /incidents/{incident_id}/decisions` or by `GET /incidents/{incident_id}`.

The response contains the decision's `id`, `incident_id`, `question`, `deadline`, `status`, `current_version`, timestamps, and a `versions` array sorted by `version_number`. Each version includes its summary, uncertainty level, approval status, creator, and `evidence_snapshot` (`evidence_ids` and `evidence_codes`). Evidence added after a version is created does not change that saved snapshot. If no versions exist, the array is empty.

An unknown decision UUID returns HTTP `404` with `{"detail":"Decision not found"}`. A malformed UUID returns HTTP `422`. This endpoint is read-only; it does not create or update versions.
