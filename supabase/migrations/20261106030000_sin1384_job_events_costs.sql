-- SIN-1384: Ereignisverlauf (Audit) und Kosten je Job mit Budget-Grenze. Beides nur Anfügen; schreiben darf nur
-- service_role (Worker), Nutzer lesen eigene Zeilen. Additiv: nur Objekte in social_media.

create table social_media.job_events (
  id bigint generated always as identity primary key,
  job_id uuid not null,
  creator_id uuid not null,
  at timestamptz not null default now(),
  level text not null check (level in ('info', 'warn', 'error')),
  code text not null check (char_length(code) between 1 and 100),
  message text not null check (char_length(message) <= 500),
  data jsonb not null default '{}'::jsonb,
  foreign key (job_id, creator_id) references social_media.jobs (id, creator_id) on delete cascade
);
create index job_events_job_idx on social_media.job_events (job_id, at);
comment on column social_media.job_events.message is
  'Für Menschen lesbar; keine personenbezogenen Daten, keine Secrets, keine Dateinamen.';
comment on column social_media.job_events.data is
  'Technische Details; keine personenbezogenen Daten, keine Secrets, keine Dateinamen.';

create table social_media.cost_entries (
  id bigint generated always as identity primary key,
  job_id uuid not null,
  creator_id uuid not null,
  provider text not null check (char_length(provider) between 1 and 100),
  item text not null check (char_length(item) between 1 and 200),
  amount_eur numeric(10, 4) not null check (amount_eur >= 0),
  at timestamptz not null default now(),
  foreign key (job_id, creator_id) references social_media.jobs (id, creator_id) on delete cascade
);
create index cost_entries_job_idx on social_media.cost_entries (job_id);

-- Auch für Superuser keine Änderung und kein Löschen; erlaubt ist nur das Cascade-Löschen mit dem Job.
create function social_media.job_rows_append_only() returns trigger
language plpgsql set search_path = '' as $$
begin
  if tg_op = 'DELETE' and not exists (select 1 from social_media.jobs where id = old.job_id) then
    return old;
  end if;
  raise exception '%: nur Anfuegen', tg_table_name using errcode = 'check_violation';
end $$;
create trigger job_events_append_only before update or delete on social_media.job_events
  for each row execute function social_media.job_rows_append_only();
create trigger cost_entries_append_only before update or delete on social_media.cost_entries
  for each row execute function social_media.job_rows_append_only();

-- Budget-Grenze: Summe der Posten darf jobs.budget_cap nicht übersteigen (Standard 0 = nur 0-€-Posten).
-- Fehlercode 53400; die Sperre auf dem Job verhindert, dass zwei gleichzeitige Posten gemeinsam darüber kommen.
create function social_media.cost_entries_budget() returns trigger
language plpgsql set search_path = '' as $$
declare
  cap numeric;
  spent numeric;
begin
  select budget_cap into cap from social_media.jobs where id = new.job_id for update;
  select coalesce(sum(amount_eur), 0) into spent from social_media.cost_entries where job_id = new.job_id;
  if spent + new.amount_eur > cap then
    raise exception 'cost_entries: Budget des Jobs ueberschritten (% von % EUR)', spent + new.amount_eur, cap
      using errcode = 'configuration_limit_exceeded';
  end if;
  return new;
end $$;
create trigger cost_entries_budget before insert on social_media.cost_entries
  for each row execute function social_media.cost_entries_budget();

create view social_media.job_cost_summary with (security_invoker = true) as
  select j.id as job_id, coalesce(sum(c.amount_eur), 0)::numeric(10, 4) as total_eur, j.budget_cap
  from social_media.jobs j left join social_media.cost_entries c on c.job_id = j.id
  group by j.id, j.budget_cap;

alter table social_media.job_events enable row level security;
alter table social_media.cost_entries enable row level security;

grant select on social_media.job_events, social_media.cost_entries, social_media.job_cost_summary
  to authenticated, service_role;
grant insert on social_media.job_events, social_media.cost_entries to service_role;

create policy job_events_select_own on social_media.job_events for select to authenticated
  using (creator_id in (select id from social_media.creators where user_id = (select auth.uid())));
create policy cost_entries_select_own on social_media.cost_entries for select to authenticated
  using (creator_id in (select id from social_media.creators where user_id = (select auth.uid())));
