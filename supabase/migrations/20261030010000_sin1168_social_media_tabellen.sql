-- SIN-1168: Schema social_media, Teil 1 von 2 (Tabellen und Zustandsregeln).
-- Additiv: legt nur Objekte in social_media an. Einzige Verbindung nach außen ist der Fremdschlüssel
-- auf auth.users(id) (nur referenziert). Keine bestehende Tabelle wird angefasst.
-- RLS, Rechte und Policies folgen in der nächsten Migration.
create schema if not exists social_media;

-- Ein Creator je Login; creators.id ist der creator_id-Schlüssel aller anderen Tabellen.
create table social_media.creators (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references auth.users (id) on delete cascade,
  display_name text not null default '' check (char_length(display_name) <= 100),
  created_at timestamptz not null default now()
);

-- Unveränderliche Originale. Der Inhalt liegt im privaten Storage, hier nur Pfad und Metadaten.
create table social_media.assets (
  id uuid primary key default gen_random_uuid(),
  creator_id uuid not null references social_media.creators (id) on delete cascade,
  storage_path text not null check (char_length(storage_path) between 1 and 500),
  original_filename text not null check (char_length(original_filename) between 1 and 255),
  sha256 text not null check (sha256 ~ '^[0-9a-f]{64}$'),
  mime_type text not null check (mime_type ~ '^(video|image)/[a-z0-9.+-]+$'),
  size_bytes bigint not null check (size_bytes > 0),
  approval_status text not null default 'wartet_auf_freigabe'
    check (approval_status in ('wartet_auf_freigabe', 'freigegeben', 'abgelehnt')),
  created_at timestamptz not null default now(),
  -- Deduplizierung: dieselbe Datei kommt je Creator nur einmal vor.
  unique (creator_id, sha256),
  unique (creator_id, storage_path)
);

create function social_media.assets_immutable() returns trigger
language plpgsql set search_path = '' as $$
begin
  -- Nur approval_status darf sich ändern; das Original selbst nie, auch nicht für service_role.
  if (new.id, new.creator_id, new.storage_path, new.original_filename, new.sha256,
      new.mime_type, new.size_bytes, new.created_at)
     is distinct from
     (old.id, old.creator_id, old.storage_path, old.original_filename, old.sha256,
      old.mime_type, old.size_bytes, old.created_at) then
    raise exception 'assets: Originale sind unveraenderlich' using errcode = 'check_violation';
  end if;
  return new;
end $$;

create trigger assets_immutable before update on social_media.assets
  for each row execute function social_media.assets_immutable();

-- Jobs: queued -> running -> succeeded | failed | cancelled (auch queued -> cancelled).
-- idempotency_key ist je Creator eindeutig: ein Wiederholungsversuch legt keinen zweiten Job an.
-- budget_cap 0 heißt: kein bezahlter Schritt erlaubt.
create table social_media.jobs (
  id uuid primary key default gen_random_uuid(),
  creator_id uuid not null references social_media.creators (id) on delete cascade,
  idempotency_key text not null check (char_length(idempotency_key) between 1 and 200),
  status text not null default 'queued'
    check (status in ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
  params jsonb not null default '{}'::jsonb,
  budget_cap numeric(10, 2) not null default 0 check (budget_cap >= 0),
  progress smallint not null default 0 check (progress between 0 and 100),
  error text check (char_length(error) <= 2000),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz,
  unique (creator_id, idempotency_key)
);

create function social_media.jobs_guard() returns trigger
language plpgsql set search_path = '' as $$
begin
  if old.status in ('succeeded', 'failed', 'cancelled') then
    raise exception 'jobs: % ist ein Endzustand', old.status using errcode = 'check_violation';
  end if;
  if (new.id, new.creator_id, new.idempotency_key, new.params, new.budget_cap, new.created_at)
     is distinct from
     (old.id, old.creator_id, old.idempotency_key, old.params, old.budget_cap, old.created_at) then
    raise exception 'jobs: Eingabefelder sind unveraenderlich' using errcode = 'check_violation';
  end if;
  if new.status <> old.status
     and not ((old.status = 'queued' and new.status in ('running', 'cancelled'))
              or (old.status = 'running' and new.status in ('succeeded', 'failed', 'cancelled'))) then
    raise exception 'jobs: Uebergang % -> % nicht erlaubt', old.status, new.status
      using errcode = 'check_violation';
  end if;
  new.updated_at := now();
  if new.status = 'running' and old.status = 'queued' then
    new.started_at := now();
  elsif new.status in ('succeeded', 'failed', 'cancelled') then
    new.finished_at := now();
  end if;
  return new;
end $$;

create trigger jobs_guard before update on social_media.jobs
  for each row execute function social_media.jobs_guard();
