begin;

create table public.decisions (
    id uuid primary key default gen_random_uuid(),
    incident_id uuid not null references public.incidents(id),
    question text not null,
    deadline timestamptz not null,
    status varchar(30) not null default 'PENDING'
        constraint decisions_status_check
        check (status in ('PENDING', 'APPROVED', 'REJECTED')),
    current_version integer not null default 1
        constraint decisions_current_version_check
        check (current_version >= 1),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table public.decision_versions (
    id uuid primary key default gen_random_uuid(),
    decision_id uuid not null references public.decisions(id),
    version_number integer not null
        constraint decision_versions_number_check
        check (version_number >= 1),
    summary text not null,
    uncertainty_level varchar(20) not null default 'HIGH'
        constraint decision_versions_uncertainty_check
        check (uncertainty_level in ('LOW', 'MEDIUM', 'HIGH')),
    evidence_snapshot jsonb not null default '{}'::jsonb,
    approval_status varchar(30) not null default 'PENDING'
        constraint decision_versions_approval_check
        check (approval_status in ('PENDING', 'APPROVED', 'EDITED', 'REJECTED')),
    created_by varchar(120) not null default 'system',
    approved_by varchar(120),
    created_at timestamptz not null default now(),
    constraint decision_versions_unique_version
        unique (decision_id, version_number)
);

create index decisions_incident_id_idx
    on public.decisions (incident_id);

create index decision_versions_decision_id_idx
    on public.decision_versions (decision_id);

alter table public.decisions enable row level security;
alter table public.decision_versions enable row level security;

revoke all privileges on table public.decisions from anon, authenticated;
revoke all privileges on table public.decision_versions from anon, authenticated;

grant select, insert, update, delete on table public.decisions to service_role;
grant select, insert, update, delete on table public.decision_versions to service_role;

commit;
