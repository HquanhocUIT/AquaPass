begin;

-- Core incident record. All evidence and decisions belong to an incident.
create table public.incidents (
    id uuid primary key default gen_random_uuid(),
    title varchar(200) not null,
    description text not null,
    incident_type varchar(80) not null,
    location_name varchar(200) not null,
    latitude double precision,
    longitude double precision,
    severity varchar(20) not null default 'MEDIUM'
        constraint incidents_severity_check
        check (severity in ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    status varchar(20) not null default 'OPEN'
        constraint incidents_status_check
        check (status in ('OPEN', 'MONITORING', 'CLOSED')),
    occurred_at timestamptz not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Evidence may contain either a numeric measurement or a textual report.
create table public.evidence (
    id uuid primary key default gen_random_uuid(),
    incident_id uuid not null references public.incidents(id),
    code varchar(80) not null,
    evidence_type varchar(80) not null,
    state varchar(30) not null default 'KNOWN'
        constraint evidence_state_check
        check (
            state in (
                'KNOWN',
                'MISSING',
                'CONFLICTING',
                'STALE',
                'LOW_CONFIDENCE'
            )
        ),
    value_numeric double precision,
    value_text text,
    unit varchar(40),
    source varchar(200) not null,
    observed_at timestamptz not null,
    reliability_score double precision not null default 0.5
        constraint evidence_reliability_score_check
        check (reliability_score between 0 and 1),
    provenance jsonb not null default '{}'::jsonb,
    is_simulated boolean not null default true,
    created_at timestamptz not null default now(),
    constraint evidence_value_check check (
        state = 'MISSING'
        or value_numeric is not null
        or value_text is not null
    )
);

create index evidence_incident_id_idx
    on public.evidence (incident_id);

-- SQL Editor-created tables need RLS enabled explicitly.
alter table public.incidents enable row level security;
alter table public.evidence enable row level security;

-- The frontend must call FastAPI instead of these tables directly.
revoke all privileges on table public.incidents from anon, authenticated;
revoke all privileges on table public.evidence from anon, authenticated;

-- Preserve optional server-side access through Supabase's service role.
grant select, insert, update, delete on table public.incidents to service_role;
grant select, insert, update, delete on table public.evidence to service_role;

commit;
