create table if not exists conversations (
    id uuid primary key,
    user_id uuid not null,
    name text not null,
    created_at timestamptz not null default now()
);

create index if not exists conversations_user_idx
    on conversations (user_id, created_at desc);

create table if not exists agent_tasks (
    id uuid primary key default gen_random_uuid(),
    source_conversation_id uuid not null references conversations(id) on delete cascade,
    target_conversation_id uuid not null references conversations(id) on delete cascade,
    user_id uuid not null,
    task text not null,
    context text,
    status text not null default 'pending'
        check (status in ('pending', 'running', 'completed', 'failed')),
    result text,
    created_at timestamptz not null default now(),
    completed_at timestamptz
);

create index if not exists agent_tasks_target_status_idx
    on agent_tasks (target_conversation_id, status, created_at);
