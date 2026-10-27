create schema probe;
create table probe.notes (id uuid primary key default gen_random_uuid(), owner uuid not null default auth.uid() references auth.users(id), body text);
alter table probe.notes enable row level security;
create policy own on probe.notes for all to authenticated using (owner = (select auth.uid()));
