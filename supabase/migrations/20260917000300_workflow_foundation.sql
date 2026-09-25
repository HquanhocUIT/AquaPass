begin;

-- A decision belongs to the same incident as every gap/request referring to it.
alter table public.decisions
    add constraint decisions_id_incident_unique unique (id, incident_id);
alter table public.evidence
    add constraint evidence_id_incident_unique unique (id, incident_id);

create table public.hypotheses (
    id uuid primary key default gen_random_uuid(),
    incident_id uuid not null references public.incidents(id),
    code varchar(40) not null,
    title varchar(200) not null,
    description text not null,
    status varchar(30) not null default 'ACTIVE'
        constraint hypotheses_status_check check (status in ('ACTIVE', 'REJECTED', 'RESOLVED')),
    support_score double precision not null default 0
        constraint hypotheses_score_check check (support_score between 0 and 1),
    created_at timestamptz not null default now(),
    constraint hypotheses_incident_code_unique unique (incident_id, code)
);

create table public.evidence_gaps (
    id uuid primary key default gen_random_uuid(),
    incident_id uuid not null references public.incidents(id),
    decision_id uuid not null,
    code varchar(80) not null,
    description text not null,
    criticality varchar(20) not null default 'MEDIUM'
        constraint evidence_gaps_criticality_check check (criticality in ('LOW', 'MEDIUM', 'HIGH')),
    status varchar(30) not null default 'OPEN'
        constraint evidence_gaps_status_check check (status in ('OPEN', 'RESOLVED', 'DISMISSED')),
    rationale text,
    created_at timestamptz not null default now(),
    constraint evidence_gaps_decision_incident_fk
        foreign key (decision_id, incident_id) references public.decisions(id, incident_id),
    constraint evidence_gaps_id_decision_incident_unique unique (id, decision_id, incident_id)
);

create table public.actors (
    id uuid primary key default gen_random_uuid(),
    code varchar(80) not null unique,
    name varchar(160) not null,
    actor_type varchar(60) not null,
    capabilities jsonb not null default '[]'::jsonb
        constraint actors_capabilities_array_check check (jsonb_typeof(capabilities) = 'array'),
    location_name varchar(200),
    available boolean not null default true,
    capacity integer not null default 1
        constraint actors_capacity_check check (capacity >= 0),
    turnaround_minutes integer
        constraint actors_turnaround_check check (turnaround_minutes >= 0),
    created_at timestamptz not null default now()
);

create table public.evidence_requests (
    id uuid primary key default gen_random_uuid(),
    incident_id uuid not null references public.incidents(id),
    decision_id uuid not null,
    evidence_gap_id uuid,
    assigned_actor_id uuid references public.actors(id),
    result_evidence_id uuid,
    requested_evidence_code varchar(80) not null,
    purpose text not null,
    priority varchar(20) not null default 'ROUTINE'
        constraint evidence_requests_priority_check
        check (priority in ('ROUTINE', 'URGENT', 'ASAP', 'STAT')),
    status varchar(30) not null default 'DRAFT'
        constraint evidence_requests_status_check
        check (status in (
            'DRAFT', 'REQUESTED', 'ACCEPTED', 'COLLECTING', 'SUBMITTED',
            'VERIFIED', 'INGESTED', 'DECISION_UPDATED', 'REJECTED'
        )),
    estimated_cost double precision
        constraint evidence_requests_cost_check check (estimated_cost >= 0),
    estimated_minutes integer
        constraint evidence_requests_minutes_check check (estimated_minutes >= 0),
    requested_by varchar(120) not null default 'system',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint evidence_requests_decision_incident_fk
        foreign key (decision_id, incident_id) references public.decisions(id, incident_id),
    constraint evidence_requests_gap_fk
        foreign key (evidence_gap_id, decision_id, incident_id)
        references public.evidence_gaps(id, decision_id, incident_id),
    constraint evidence_requests_result_incident_fk
        foreign key (result_evidence_id, incident_id)
        references public.evidence(id, incident_id)
);

create table public.request_status_events (
    id uuid primary key default gen_random_uuid(),
    request_id uuid not null references public.evidence_requests(id),
    from_status varchar(30),
    to_status varchar(30) not null,
    actor_name varchar(120) not null,
    note text,
    occurred_at timestamptz not null default now()
);

create table public.audit_events (
    id uuid primary key default gen_random_uuid(),
    incident_id uuid references public.incidents(id),
    entity_type varchar(60) not null,
    entity_id uuid not null,
    event_type varchar(80) not null,
    actor_name varchar(120) not null,
    payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index hypotheses_incident_id_idx on public.hypotheses (incident_id);
create index evidence_gaps_decision_id_idx on public.evidence_gaps (decision_id);
create index evidence_requests_incident_id_idx on public.evidence_requests (incident_id);
create index evidence_requests_decision_id_idx on public.evidence_requests (decision_id);
create index request_status_events_request_id_idx on public.request_status_events (request_id);
create index audit_events_incident_created_idx on public.audit_events (incident_id, created_at);

alter table public.hypotheses enable row level security;
alter table public.evidence_gaps enable row level security;
alter table public.actors enable row level security;
alter table public.evidence_requests enable row level security;
alter table public.request_status_events enable row level security;
alter table public.audit_events enable row level security;

revoke all privileges on table public.hypotheses, public.evidence_gaps,
    public.actors, public.evidence_requests, public.request_status_events,
    public.audit_events from anon, authenticated;
grant select, insert, update, delete on table public.hypotheses, public.evidence_gaps,
    public.actors, public.evidence_requests, public.request_status_events,
    public.audit_events to service_role;

commit;
