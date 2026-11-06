-- SIN-1381: Prüfergebnisse, Rechte-Bestätigung und Quote je Creator. assets bleibt unveränderlich (SIN-1168),
-- deshalb eigene Tabellen. Composite-FKs über (asset_id, creator_id) nutzen assets_id_creator_key aus SIN-1378.
-- Additiv: nur Objekte in social_media.

-- Ein Ergebnis je Asset und Prüfart; der Worker überschreibt es bei einer neuen Prüfung.
create table social_media.asset_checks (
  asset_id uuid not null,
  creator_id uuid not null,
  kind text not null check (kind in ('validate', 'scan')),
  status text not null check (status in ('pending', 'clean', 'infected', 'error', 'unavailable', 'rejected')),
  detail text check (char_length(detail) <= 500),
  checked_at timestamptz not null default now(),
  primary key (asset_id, kind),
  foreign key (asset_id, creator_id) references social_media.assets (id, creator_id) on delete cascade
);

-- Bestätigt der Nutzer beim Upload; danach fest (kein UPDATE). Ohne Eintrag ist das Asset nicht verwendbar.
create table social_media.asset_rights (
  asset_id uuid primary key,
  creator_id uuid not null,
  source text not null check (source in ('own', 'licensed', 'reference')),
  statement text not null check (char_length(statement) between 1 and 2000),
  confirmed_at timestamptz not null default now(),
  foreign key (asset_id, creator_id) references social_media.assets (id, creator_id) on delete cascade
);

-- Fehlt die Zeile, gelten die Standardwerte. Nur service_role setzt Limits.
create table social_media.creator_limits (
  creator_id uuid primary key references social_media.creators (id) on delete cascade,
  max_storage_bytes bigint not null default 5368709120 check (max_storage_bytes > 0),
  max_assets integer not null default 500 check (max_assets > 0)
);

alter table social_media.asset_checks enable row level security;
alter table social_media.asset_rights enable row level security;
alter table social_media.creator_limits enable row level security;

grant select on social_media.asset_checks, social_media.creator_limits to authenticated;
grant select, insert on social_media.asset_rights to authenticated;
grant all on social_media.asset_checks, social_media.asset_rights, social_media.creator_limits to service_role;

create policy asset_checks_select_own on social_media.asset_checks for select to authenticated
  using (creator_id in (select id from social_media.creators where user_id = (select auth.uid())));
create policy asset_rights_select_own on social_media.asset_rights for select to authenticated
  using (creator_id in (select id from social_media.creators where user_id = (select auth.uid())));
create policy asset_rights_insert_own on social_media.asset_rights for insert to authenticated
  with check (creator_id in (select id from social_media.creators where user_id = (select auth.uid())));
create policy creator_limits_select_own on social_media.creator_limits for select to authenticated
  using (creator_id in (select id from social_media.creators where user_id = (select auth.uid())));

-- Fail-closed: verwendbar nur mit sauberer Validierung, sauberem Virenscan, bestätigten Rechten und ohne Ablehnung.
-- SECURITY INVOKER: unter RLS liefert ein fremdes Asset false.
create function social_media.asset_usable(asset_id uuid) returns boolean
language sql stable set search_path = '' as $$
  select exists (select 1 from social_media.assets a
                 where a.id = asset_usable.asset_id and a.approval_status <> 'abgelehnt')
     and exists (select 1 from social_media.asset_checks c
                 where c.asset_id = asset_usable.asset_id and c.kind = 'validate' and c.status = 'clean')
     and exists (select 1 from social_media.asset_checks c
                 where c.asset_id = asset_usable.asset_id and c.kind = 'scan' and c.status = 'clean')
     and exists (select 1 from social_media.asset_rights r where r.asset_id = asset_usable.asset_id);
$$;
revoke all on function social_media.asset_usable(uuid) from public, anon;
grant execute on function social_media.asset_usable(uuid) to authenticated, service_role;

-- Quote beim Anlegen eines Assets; Fehlercode 53400 (configuration_limit_exceeded).
-- SECURITY DEFINER, weil die Sperre auf creators und das Zählen aller Assets über die Rechte des Nutzers gehen.
create function social_media.assets_quota() returns trigger
language plpgsql security definer set search_path = '' as $$
declare
  lim_bytes bigint := 5368709120;
  lim_assets integer := 500;
  used_bytes bigint;
  used_assets bigint;
begin
  -- Gleichzeitige Uploads desselben Creators nacheinander prüfen, sonst passen zwei knapp über die Grenze.
  perform 1 from social_media.creators where id = new.creator_id for update;
  select l.max_storage_bytes, l.max_assets into lim_bytes, lim_assets
    from social_media.creator_limits l where l.creator_id = new.creator_id;
  if not found then
    lim_bytes := 5368709120;
    lim_assets := 500;
  end if;
  select count(*), coalesce(sum(size_bytes), 0) into used_assets, used_bytes
    from social_media.assets where creator_id = new.creator_id;
  if used_assets + 1 > lim_assets then
    raise exception 'assets: Quote erreicht (höchstens % Dateien)', lim_assets
      using errcode = 'configuration_limit_exceeded';
  end if;
  if used_bytes + new.size_bytes > lim_bytes then
    raise exception 'assets: Quote erreicht (höchstens % Bytes)', lim_bytes
      using errcode = 'configuration_limit_exceeded';
  end if;
  return new;
end $$;
revoke all on function social_media.assets_quota() from public, anon, authenticated;

create trigger assets_quota before insert on social_media.assets
  for each row execute function social_media.assets_quota();
