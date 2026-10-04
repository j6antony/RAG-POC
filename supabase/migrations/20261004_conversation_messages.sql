create table if not exists conversation_messages (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references conversations(id) on delete cascade,
    user_id uuid not null,
    role text not null check (role in ('user', 'assistant')),
    text text not null,
    created_at timestamptz not null default now()
);

create index if not exists conversation_messages_conversation_created_idx
    on conversation_messages (conversation_id, created_at);

create index if not exists conversation_messages_user_idx
    on conversation_messages (user_id);
