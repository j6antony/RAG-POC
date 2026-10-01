-- Run once in the Supabase SQL editor before uploading PDFs with images.
create table if not exists public.knowledge_images (
    id uuid primary key,
    document_id uuid not null references public.knowledge_documents(id) on delete cascade,
    page_number integer not null check (page_number > 0),
    image_path text not null unique,
    created_at timestamptz not null default now()
);
create index if not exists knowledge_images_document_id_idx on public.knowledge_images(document_id);
alter table public.knowledge_images enable row level security;
-- Access goes through the backend, which checks the parent document's level.
insert into storage.buckets (id, name, public)
values ('knowledge-images', 'knowledge-images', false)
on conflict (id) do update set public = false;
