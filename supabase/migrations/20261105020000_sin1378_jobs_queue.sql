-- SIN-1378: social_media.jobs wird zur Queue (Typ, Versuche, Lease, Abbruch) und bekommt job_assets.
-- Die Tabelle selbst ist die Queue (Claim per FOR UPDATE SKIP LOCKED in SIN-1379), nicht pgmq: pgmq legt ein eigenes
-- Schema an, das Gate erlaubt nur social_media. Additiv: nur Objekte in social_media.

alter table social_media.jobs
  add column kind text not null default 'analyze'
    check (kind in ('analyze', 'render', 'delete', 'export', 'reference')),
  add column attempts integer not null default 0 check (attempts >= 0),
  add column max_attempts integer not null default 3 check (max_attempts between 1 and 10),
  add column run_after timestamptz not null default now(),
  add column locked_by text check (char_length(locked_by) between 1 and 200),
  add column locked_until timestamptz,
  add column cancel_requested boolean not null default false,
  add constraint jobs_attempts_within_max check (attempts <= max_attempts),
  -- Eine Lease gibt es nur, solange der Job läuft; beim Verlassen von running leert sie der Trigger.
  add constraint jobs_lease_only_running check (status = 'running' or (locked_by is null and locked_until is null));

create index jobs_claim_idx on social_media.jobs (run_after) where status = 'queued';

-- Ziel der Composite-FKs von job_assets: ein Job oder Asset ist nur zusammen mit seinem creator_id referenzierbar.
alter table social_media.jobs add constraint jobs_id_creator_key unique (id, creator_id);
alter table social_media.assets add constraint assets_id_creator_key unique (id, creator_id);

-- Eingabe-Assets eines Jobs. creator_id steckt in beiden Fremdschlüsseln, ein fremdes Asset ist daher nicht verknüpfbar.
create table social_media.job_assets (
  job_id uuid not null,
  asset_id uuid not null,
  creator_id uuid not null,
  primary key (job_id, asset_id),
  foreign key (job_id, creator_id) references social_media.jobs (id, creator_id) on delete cascade,
  foreign key (asset_id, creator_id) references social_media.assets (id, creator_id) on delete cascade
);
create index job_assets_asset_idx on social_media.job_assets (asset_id, creator_id);

-- Zustandsregeln. Nutzer (Rolle authenticated) dürfen nur queued -> cancelled und cancel_requested auf true setzen;
-- alles Weitere macht der Worker (service_role). attempts zählt allein dieser Trigger beim Start (queued -> running),
-- damit kein Aufrufer die Zählung vergessen oder zurücksetzen kann.
create or replace function social_media.jobs_guard() returns trigger
language plpgsql set search_path = '' as $$
begin
  if old.status in ('succeeded', 'failed', 'cancelled') then
    raise exception 'jobs: % ist ein Endzustand', old.status using errcode = 'check_violation';
  end if;
  if (new.id, new.creator_id, new.idempotency_key, new.params, new.budget_cap, new.kind, new.created_at)
     is distinct from
     (old.id, old.creator_id, old.idempotency_key, old.params, old.budget_cap, old.kind, old.created_at) then
    raise exception 'jobs: Eingabefelder sind unveraenderlich' using errcode = 'check_violation';
  end if;
  if old.cancel_requested and not new.cancel_requested then
    raise exception 'jobs: cancel_requested wird nicht zurueckgenommen' using errcode = 'check_violation';
  end if;
  if current_user in ('authenticated', 'anon')
     and new.status <> old.status and not (old.status = 'queued' and new.status = 'cancelled') then
    raise exception 'jobs: Nutzer duerfen nur queued -> cancelled; sonst cancel_requested setzen'
      using errcode = 'check_violation';
  end if;
  if new.status <> old.status
     and not ((old.status = 'queued' and new.status in ('running', 'cancelled'))
              or (old.status = 'running' and new.status in ('succeeded', 'failed', 'cancelled'))
              or (old.status = 'running' and new.status = 'queued' and old.attempts < old.max_attempts)) then
    raise exception 'jobs: Uebergang % -> % nicht erlaubt', old.status, new.status
      using errcode = 'check_violation';
  end if;
  new.attempts := old.attempts + case when old.status = 'queued' and new.status = 'running' then 1 else 0 end;
  if old.status = 'running' and new.status <> 'running' then
    new.locked_by := null;
    new.locked_until := null;
  end if;
  new.updated_at := now();
  if new.status = 'running' and old.status = 'queued' then
    new.started_at := now();
  elsif new.status in ('succeeded', 'failed', 'cancelled') then
    new.finished_at := now();
  end if;
  return new;
end $$;

-- Rechte: Nutzer legen Jobs nur mit Eingabefeldern an (Queue-Felder behalten ihre Standardwerte) und
-- ändern nur status (Abbruch) und cancel_requested. Alles andere hat nur service_role.
revoke insert on social_media.jobs from authenticated;
grant insert (creator_id, idempotency_key, status, params, budget_cap, progress, error, kind)
  on social_media.jobs to authenticated;
grant update (cancel_requested) on social_media.jobs to authenticated;

drop policy jobs_cancel_own on social_media.jobs;
create policy jobs_cancel_own on social_media.jobs for update to authenticated
  using (status in ('queued', 'running')
    and creator_id in (select id from social_media.creators where user_id = (select auth.uid())))
  with check (status = 'cancelled' or (status in ('queued', 'running') and cancel_requested));

-- job_assets: RLS wie jobs; die Eingabe eines Jobs ändert sich nur, solange er wartet.
alter table social_media.job_assets enable row level security;
grant select, insert, delete on social_media.job_assets to authenticated, service_role;

create policy job_assets_select_own on social_media.job_assets for select to authenticated
  using (creator_id in (select id from social_media.creators where user_id = (select auth.uid())));
create policy job_assets_insert_own on social_media.job_assets for insert to authenticated
  with check (creator_id in (select id from social_media.creators where user_id = (select auth.uid()))
    and exists (select 1 from social_media.jobs j where j.id = job_id and j.status = 'queued'));
create policy job_assets_delete_own on social_media.job_assets for delete to authenticated
  using (creator_id in (select id from social_media.creators where user_id = (select auth.uid())));
