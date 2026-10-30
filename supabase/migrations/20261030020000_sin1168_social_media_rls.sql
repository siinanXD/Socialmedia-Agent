-- SIN-1168: Schema social_media, Teil 2 von 2 (Rechte und RLS über creator_id).
-- anon bekommt nichts. authenticated sieht und ändert nur Zeilen des eigenen Creators.
-- Worker und serverseitiger Code laufen als service_role (umgeht RLS) und brauchen nur Tabellenrechte.
alter table social_media.creators enable row level security;
alter table social_media.assets enable row level security;
alter table social_media.jobs enable row level security;

grant usage on schema social_media to authenticated, service_role;
grant all on all tables in schema social_media to service_role;

-- Creator: eigene Zeile anlegen, Anzeigename ändern, löschen (entfernt alle Daten per Cascade).
grant select, insert, delete on social_media.creators to authenticated;
grant update (display_name) on social_media.creators to authenticated;
-- Originale: lesen, anlegen, löschen (Löschung ist Pflicht), aber kein UPDATE-Recht.
grant select, insert, delete on social_media.assets to authenticated;
-- Jobs: anlegen und abbrechen. Alle anderen Zustandswechsel macht der Worker.
grant select, insert, delete on social_media.jobs to authenticated;
grant update (status) on social_media.jobs to authenticated;

create policy creators_select_own on social_media.creators for select to authenticated
  using (user_id = (select auth.uid()));
create policy creators_insert_own on social_media.creators for insert to authenticated
  with check (user_id = (select auth.uid()));
create policy creators_update_own on social_media.creators for update to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy creators_delete_own on social_media.creators for delete to authenticated
  using (user_id = (select auth.uid()));

create policy assets_select_own on social_media.assets for select to authenticated
  using (creator_id in (select id from social_media.creators where user_id = (select auth.uid())));
create policy assets_insert_own on social_media.assets for insert to authenticated
  with check (approval_status = 'wartet_auf_freigabe'
    and creator_id in (select id from social_media.creators where user_id = (select auth.uid())));
create policy assets_delete_own on social_media.assets for delete to authenticated
  using (creator_id in (select id from social_media.creators where user_id = (select auth.uid())));

create policy jobs_select_own on social_media.jobs for select to authenticated
  using (creator_id in (select id from social_media.creators where user_id = (select auth.uid())));
create policy jobs_insert_own on social_media.jobs for insert to authenticated
  with check (status = 'queued' and progress = 0 and error is null
    and creator_id in (select id from social_media.creators where user_id = (select auth.uid())));
create policy jobs_cancel_own on social_media.jobs for update to authenticated
  using (creator_id in (select id from social_media.creators where user_id = (select auth.uid())))
  with check (status = 'cancelled');
create policy jobs_delete_own on social_media.jobs for delete to authenticated
  using (creator_id in (select id from social_media.creators where user_id = (select auth.uid())));
