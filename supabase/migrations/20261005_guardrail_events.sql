-- Backend service-role access only. Clients must use the admin-gated API.
create table if not exists public.guardrail_events (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null,
    user_name text not null,
    user_email text,
    user_access integer not null check (user_access in (1, 2, 3)),
    conversation_id uuid not null,
    source text not null,
    rule text not null,
    action text not null check (action in ('flagged', 'blocked')),
    reason text not null,
    created_at timestamptz not null default now()
);
create index if not exists guardrail_events_created_idx on public.guardrail_events (created_at desc, id desc);
alter table public.guardrail_events enable row level security;
revoke all on public.guardrail_events from anon, authenticated;
grant select, insert on public.guardrail_events to service_role;
