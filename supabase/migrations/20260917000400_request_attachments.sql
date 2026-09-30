begin;

create table public.evidence_request_attachments (
    id uuid primary key default gen_random_uuid(),
    request_id uuid not null references public.evidence_requests(id) on delete cascade,
    filename varchar(255) not null,
    content_type varchar(120) not null,
    size_bytes integer not null check (size_bytes between 1 and 10485760),
    sha256 char(64) not null,
    data bytea not null,
    created_at timestamptz not null default now()
);

create index evidence_request_attachments_request_created_idx
    on public.evidence_request_attachments (request_id, created_at, id);

alter table public.evidence_request_attachments enable row level security;
revoke all privileges on table public.evidence_request_attachments from anon, authenticated;
grant select, insert, update, delete on table public.evidence_request_attachments to service_role;

commit;
