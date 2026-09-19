# AquaPass core database

This is the Phase 1 relational contract owned by Quân. It supports the complete closed loop while allowing Sang's intelligence modules to attach evidence states, gaps and scores later.

```mermaid
erDiagram
    INCIDENT ||--o{ EVIDENCE : contains
    INCIDENT ||--o{ HYPOTHESIS : evaluates
    INCIDENT ||--o{ DECISION : frames
    DECISION ||--|{ DECISION_VERSION : versions
    INCIDENT ||--o{ EVIDENCE_GAP : has
    DECISION ||--o{ EVIDENCE_GAP : targets
    INCIDENT ||--o{ EVIDENCE_REQUEST : owns
    DECISION ||--o{ EVIDENCE_REQUEST : motivates
    EVIDENCE_GAP ||--o{ EVIDENCE_REQUEST : resolves
    ACTOR ||--o{ EVIDENCE_REQUEST : receives
    EVIDENCE_REQUEST ||--o{ REQUEST_STATUS_EVENT : records
    INCIDENT ||--o{ AUDIT_EVENT : traces

    INCIDENT {
        uuid id PK
        string title
        string incident_type
        string location_name
        string severity
        string status
        datetime occurred_at
    }
    EVIDENCE {
        uuid id PK
        uuid incident_id FK
        string code
        string evidence_type
        string state
        float value_numeric
        string value_text
        string unit
        string source
        float reliability_score
    }
    HYPOTHESIS {
        uuid id PK
        uuid incident_id FK
        string code
        string title
        float support_score
    }
    DECISION {
        uuid id PK
        uuid incident_id FK
        string question
        datetime deadline
        string status
        int current_version
    }
    DECISION_VERSION {
        uuid id PK
        uuid decision_id FK
        int version_number
        string uncertainty_level
        json evidence_snapshot
        string approval_status
    }
    EVIDENCE_GAP {
        uuid id PK
        uuid incident_id FK
        uuid decision_id FK
        string code
        string criticality
        string status
    }
    EVIDENCE_REQUEST {
        uuid id PK
        uuid incident_id FK
        uuid decision_id FK
        uuid evidence_gap_id FK
        uuid assigned_actor_id FK
        uuid result_evidence_id FK
        string requested_evidence_code
        string status
    }
    ACTOR {
        uuid id PK
        string code
        json capabilities
        bool available
        int capacity
    }
    REQUEST_STATUS_EVENT {
        uuid id PK
        uuid request_id FK
        string from_status
        string to_status
        datetime occurred_at
    }
    AUDIT_EVENT {
        uuid id PK
        uuid incident_id FK
        string entity_type
        string entity_id
        string event_type
        json payload
    }
```

## Design rules

- Returned evidence always carries `incident_id`; it updates the same incident instead of creating a second one.
- Decisions are never overwritten. `decisions.current_version` points to append-only `decision_versions`.
- Request transitions are recorded in `request_status_events`.
- AI suggestions, ranking configurations and human actions are recorded as append-only `audit_events`.
- `Evidence.provenance` and `DecisionVersion.evidence_snapshot` preserve the source IDs used for an explanation.
- The active Supabase schema uses UUIDs for every ID; the seed uses stable UUIDs for reproducible references.

## Active schema and ownership

The authoritative PostgreSQL DDL is in `supabase/migrations/` and must be applied in filename order. The application query mappings are in `backend/app/db/tables.py`; they refer to tables in the `public` schema and do not create production tables. `supabase/seed.sql` is additive demo data and may be rerun without resetting an existing decision version.

`backend/schema.sql`, `backend/app/models/domain.py` and `backend/app/db/bootstrap.py` are older, unmounted drafts with string IDs. Do **not** run or import them for the Supabase UUID deployment; reconcile or retire them in a separate reviewed change.

Migration `20260917000300_workflow_foundation.sql` adds hypotheses, evidence gaps, actors, evidence requests, request-status events and audit events. Composite foreign keys enforce that a gap/request points to a decision from the same incident. `result_evidence_id` links a completed request to the returned evidence. Database status checks constrain valid values; application services still need to enforce transition order, permissions and human confirmation before those write APIs are exposed.
