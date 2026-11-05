-- SIN-1382: Creator-Profil (Nische, Plattformen, Tonalität, Zielgruppe, erlaubte Quellen, Budget) und Änderungsprotokoll.
-- Additiv: legt nur Objekte in social_media an. Nischen sind Daten, keine Sonderlogik.
-- Standardwerte sind restriktiv: keine Plattformen, keine Quellen, Budget 0, Veröffentlichen aus.

create table social_media.creator_profiles (
  creator_id uuid primary key references social_media.creators (id) on delete cascade,
  niche text not null default '' check (char_length(niche) <= 100),
  platforms text[] not null default '{}'
    check (platforms <@ array['youtube', 'instagram', 'tiktok'] and array_position(platforms, null) is null),
  tone text not null default '' check (char_length(tone) <= 500),
  target_audience text not null default '' check (char_length(target_audience) <= 500),
  hashtags text[] not null default '{}'
    check (cardinality(hashtags) <= 30 and array_position(hashtags, null) is null
           and char_length(array_to_string(hashtags, ' ')) <= 1500),
  allowed_sources text[] not null default '{}'
    check (allowed_sources <@ array['creator_submitted', 'official_api', 'manual_import']
           and array_position(allowed_sources, null) is null),
  reference_accounts text[] not null default '{}'
    check (cardinality(reference_accounts) <= 20 and array_position(reference_accounts, null) is null
           and char_length(array_to_string(reference_accounts, ' ')) <= 1000),
  default_budget_cap numeric(10, 2) not null default 0 check (default_budget_cap >= 0),
  kpis text[] not null default '{}'
    check (cardinality(kpis) <= 20 and array_position(kpis, null) is null
           and char_length(array_to_string(kpis, ' ')) <= 500),
  publish_enabled boolean not null default false,
  updated_at timestamptz not null default now()
);

-- Nur Anfügen: Zeilen entstehen durch den Trigger unten, nie durch Nutzer oder Worker.
create table social_media.profile_audit (
  id bigint generated always as identity primary key,
  creator_id uuid not null references social_media.creators (id) on delete cascade,
  changed_at timestamptz not null default now(),
  changed_by uuid,
  action text not null check (action in ('insert', 'update')),
  old_values jsonb,
  new_values jsonb
);
create index profile_audit_creator_idx on social_media.profile_audit (creator_id);

create function social_media.creator_profiles_guard() returns trigger
language plpgsql set search_path = '' as $$
begin
  if tg_op = 'UPDATE' and new.creator_id is distinct from old.creator_id then
    raise exception 'creator_profiles: creator_id ist unveraenderlich' using errcode = 'check_violation';
  end if;
  -- Einschalten darf nur der Nutzer des Creators selbst; service_role und Worker haben keine Nutzerkennung.
  if new.publish_enabled and (tg_op = 'INSERT' or not old.publish_enabled)
     and (select auth.uid()) is distinct from (select user_id from social_media.creators where id = new.creator_id) then
    raise exception 'creator_profiles: publish_enabled darf nur der Nutzer selbst einschalten'
      using errcode = 'insufficient_privilege';
  end if;
  new.updated_at := now();
  return new;
end $$;

create trigger creator_profiles_guard before insert or update on social_media.creator_profiles
  for each row execute function social_media.creator_profiles_guard();

-- security definer: der Nutzer hat kein INSERT-Recht auf profile_audit, der Trigger schreibt als Eigentümer.
create function social_media.creator_profiles_audit() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  if tg_op = 'UPDATE' and to_jsonb(new) - 'updated_at' = to_jsonb(old) - 'updated_at' then
    return null;
  end if;
  insert into social_media.profile_audit (creator_id, changed_by, action, old_values, new_values)
  values (new.creator_id, (select auth.uid()), lower(tg_op),
          case when tg_op = 'UPDATE' then to_jsonb(old) end, to_jsonb(new));
  return null;
end $$;

create trigger creator_profiles_audit after insert or update on social_media.creator_profiles
  for each row execute function social_media.creator_profiles_audit();

-- Auch für Superuser und service_role: keine Änderung, kein Löschen, kein Leeren.
-- Löschen ist nur erlaubt, wenn der Creator selbst nicht mehr existiert (Cascade beim Löschen des Creators).
create function social_media.profile_audit_append_only() returns trigger
language plpgsql set search_path = '' as $$
begin
  if tg_op = 'DELETE' then
    if not exists (select 1 from social_media.creators where id = old.creator_id) then
      return old;
    end if;
  end if;
  raise exception 'profile_audit: nur Anfuegen' using errcode = 'check_violation';
end $$;

create trigger profile_audit_append_only before update or delete on social_media.profile_audit
  for each row execute function social_media.profile_audit_append_only();
create trigger profile_audit_no_truncate before truncate on social_media.profile_audit
  for each statement execute function social_media.profile_audit_append_only();

-- Rechte und RLS über creator_id (wie in SIN-1168). anon bekommt nichts.
alter table social_media.creator_profiles enable row level security;
alter table social_media.profile_audit enable row level security;

grant select, insert, delete on social_media.creator_profiles to authenticated;
grant update (niche, platforms, tone, target_audience, hashtags, allowed_sources, reference_accounts,
              default_budget_cap, kpis, publish_enabled) on social_media.creator_profiles to authenticated;
grant select, insert, update, delete on social_media.creator_profiles to service_role;
grant select on social_media.profile_audit to authenticated, service_role;

create policy creator_profiles_select_own on social_media.creator_profiles for select to authenticated
  using (creator_id in (select id from social_media.creators where user_id = (select auth.uid())));
create policy creator_profiles_insert_own on social_media.creator_profiles for insert to authenticated
  with check (creator_id in (select id from social_media.creators where user_id = (select auth.uid())));
create policy creator_profiles_update_own on social_media.creator_profiles for update to authenticated
  using (creator_id in (select id from social_media.creators where user_id = (select auth.uid())))
  with check (creator_id in (select id from social_media.creators where user_id = (select auth.uid())));
create policy creator_profiles_delete_own on social_media.creator_profiles for delete to authenticated
  using (creator_id in (select id from social_media.creators where user_id = (select auth.uid())));

create policy profile_audit_select_own on social_media.profile_audit for select to authenticated
  using (creator_id in (select id from social_media.creators where user_id = (select auth.uid())));
