-- SIN-1378: jobs als Queue (Typ, Versuche, Lease, Abbruch) und Verknüpfung job_assets.
-- Läuft mit `supabase test db`. Nutzer A und B haben je einen Creator, Assets und Jobs.
begin;
select plan(58);

-- Aufbau als Superuser (umgeht RLS)
insert into auth.users (id, email) values
  ('aaaaaaaa-0000-0000-0000-000000000001', 'a@example.test'),
  ('bbbbbbbb-0000-0000-0000-000000000002', 'b@example.test');
insert into social_media.creators (id, user_id, display_name) values
  ('a1000000-0000-0000-0000-000000000001', 'aaaaaaaa-0000-0000-0000-000000000001', 'A'),
  ('b2000000-0000-0000-0000-000000000002', 'bbbbbbbb-0000-0000-0000-000000000002', 'B');
insert into social_media.assets (id, creator_id, storage_path, original_filename, sha256, mime_type, size_bytes) values
  ('a1a00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001',
   'a/clip.mp4', 'clip.mp4', repeat('a', 64), 'video/mp4', 1000),
  ('b2b00000-0000-0000-0000-000000000002', 'b2000000-0000-0000-0000-000000000002',
   'b/clip.mp4', 'clip.mp4', repeat('b', 64), 'video/mp4', 2000);
insert into social_media.jobs (id, creator_id, idempotency_key) values
  ('a1c00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 'queued-a'),
  ('a1c00000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000001', 'running-a'),
  ('a1c00000-0000-0000-0000-000000000003', 'a1000000-0000-0000-0000-000000000001', 'cancel-a'),
  ('a1c00000-0000-0000-0000-000000000004', 'a1000000-0000-0000-0000-000000000001', 'done-a'),
  ('b2c00000-0000-0000-0000-000000000002', 'b2000000-0000-0000-0000-000000000002', 'queued-b');
-- Verknüpfungen für laufenden und abgeschlossenen Job legt der Aufbau an (Nutzer dürfen das nur bei queued)
insert into social_media.job_assets (job_id, asset_id, creator_id) values
  ('a1c00000-0000-0000-0000-000000000002', 'a1a00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001'),
  ('a1c00000-0000-0000-0000-000000000004', 'a1a00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001');
update social_media.jobs set status = 'running' where id in
  ('a1c00000-0000-0000-0000-000000000002', 'a1c00000-0000-0000-0000-000000000004');
update social_media.jobs set status = 'succeeded' where id = 'a1c00000-0000-0000-0000-000000000004';

-- Struktur
select has_column('social_media', 'jobs', 'kind', 'jobs.kind');
select has_column('social_media', 'jobs', 'attempts', 'jobs.attempts');
select has_column('social_media', 'jobs', 'max_attempts', 'jobs.max_attempts');
select has_column('social_media', 'jobs', 'run_after', 'jobs.run_after');
select has_column('social_media', 'jobs', 'locked_by', 'jobs.locked_by');
select has_column('social_media', 'jobs', 'locked_until', 'jobs.locked_until');
select has_column('social_media', 'jobs', 'cancel_requested', 'jobs.cancel_requested');
select has_table('social_media', 'job_assets', 'Tabelle job_assets existiert');
select is(
  (select relrowsecurity from pg_class where oid = 'social_media.job_assets'::regclass),
  true, 'RLS ist auf job_assets aktiv');
select is(
  (select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
    where n.nspname <> 'social_media' and c.relname = 'job_assets'),
  0::bigint, 'job_assets liegt nur in social_media');
select results_eq(
  $$select kind, attempts, max_attempts, cancel_requested from social_media.jobs
    where id = 'a1c00000-0000-0000-0000-000000000001'$$,
  $$values ('analyze'::text, 0, 3, false)$$,
  'Standard: analyze, 0 Versuche, höchstens 3, kein Abbruch');
select throws_ok(
  $$insert into social_media.jobs (creator_id, idempotency_key, kind)
    values ('a1000000-0000-0000-0000-000000000001', 'k', 'publish')$$,
  '23514', null, 'unbekannter Typ wird abgelehnt');

-- Verknüpfung: Composite-FK auf creator_id (als Superuser, RLS greift dort nicht)
select lives_ok(
  $$insert into social_media.job_assets (job_id, asset_id, creator_id) values
    ('a1c00000-0000-0000-0000-000000000003', 'a1a00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001')$$,
  'eigenes Asset am eigenen Job');
select throws_ok(
  $$insert into social_media.job_assets (job_id, asset_id, creator_id) values
    ('a1c00000-0000-0000-0000-000000000001', 'b2b00000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000001')$$,
  '23503', null, 'fremdes Asset in job_assets (creator_id des Jobs) -> Fehler');
select throws_ok(
  $$insert into social_media.job_assets (job_id, asset_id, creator_id) values
    ('a1c00000-0000-0000-0000-000000000001', 'b2b00000-0000-0000-0000-000000000002', 'b2000000-0000-0000-0000-000000000002')$$,
  '23503', null, 'fremdes Asset in job_assets (creator_id des Assets) -> Fehler');

-- Nutzer A
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub":"aaaaaaaa-0000-0000-0000-000000000001","role":"authenticated"}', true);

select is((select count(*) from social_media.job_assets where job_id = 'a1c00000-0000-0000-0000-000000000003'),
  1::bigint, 'A sieht die eigene Verknüpfung');
select lives_ok(
  $$insert into social_media.job_assets (job_id, asset_id, creator_id) values
    ('a1c00000-0000-0000-0000-000000000001', 'a1a00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001')$$,
  'A verknüpft eigenes Asset mit wartendem Job');
select throws_ok(
  $$insert into social_media.job_assets (job_id, asset_id, creator_id) values
    ('a1c00000-0000-0000-0000-000000000001', 'b2b00000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000001')$$,
  '23503', null, 'A kann kein fremdes Asset verknüpfen');
select throws_ok(
  $$insert into social_media.job_assets (job_id, asset_id, creator_id) values
    ('b2c00000-0000-0000-0000-000000000002', 'b2b00000-0000-0000-0000-000000000002', 'b2000000-0000-0000-0000-000000000002')$$,
  '42501', null, 'A kann nichts für Creator B verknüpfen');
select throws_ok(
  $$insert into social_media.job_assets (job_id, asset_id, creator_id) values
    ('b2c00000-0000-0000-0000-000000000002', 'a1a00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001')$$,
  '42501', null, 'A kann das eigene Asset nicht an den Job von B hängen');
select throws_ok(
  $$insert into social_media.job_assets (job_id, asset_id, creator_id) values
    ('a1c00000-0000-0000-0000-000000000002', 'a1a00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001')$$,
  '42501', null, 'A ändert die Eingabe eines laufenden Jobs nicht');
select is_empty(
  $$delete from social_media.job_assets where job_id = 'a1c00000-0000-0000-0000-000000000002' returning 1$$,
  'A löscht keine Verknüpfung eines laufenden Jobs');
select is_empty(
  $$delete from social_media.job_assets where job_id = 'a1c00000-0000-0000-0000-000000000004' returning 1$$,
  'A löscht keine Verknüpfung eines abgeschlossenen Jobs');
select isnt_empty(
  $$delete from social_media.job_assets where job_id = 'a1c00000-0000-0000-0000-000000000001' returning 1$$,
  'A löscht die Verknüpfung eines wartenden Jobs');

-- Worker-Felder gehören dem Worker
select throws_ok(
  $$insert into social_media.jobs (creator_id, idempotency_key, attempts)
    values ('a1000000-0000-0000-0000-000000000001', 'x1', 2)$$,
  '42501', null, 'A legt keinen Job mit attempts an');
select throws_ok(
  $$insert into social_media.jobs (creator_id, idempotency_key, locked_by)
    values ('a1000000-0000-0000-0000-000000000001', 'x2', 'ich')$$,
  '42501', null, 'A legt keinen Job mit locked_by an');
select throws_ok(
  $$insert into social_media.jobs (creator_id, idempotency_key, max_attempts)
    values ('a1000000-0000-0000-0000-000000000001', 'x3', 99)$$,
  '42501', null, 'A legt keinen Job mit eigenem max_attempts an');
select lives_ok(
  $$insert into social_media.jobs (creator_id, idempotency_key, kind)
    values ('a1000000-0000-0000-0000-000000000001', 'x4', 'render')$$,
  'A wählt den Typ beim Anlegen');
select throws_ok(
  $$update social_media.jobs set attempts = 0 where id = 'a1c00000-0000-0000-0000-000000000002'$$,
  '42501', null, 'A setzt attempts nicht');
select throws_ok(
  $$update social_media.jobs set locked_by = 'ich' where id = 'a1c00000-0000-0000-0000-000000000002'$$,
  '42501', null, 'A setzt locked_by nicht');
select throws_ok(
  $$update social_media.jobs set locked_until = now() where id = 'a1c00000-0000-0000-0000-000000000002'$$,
  '42501', null, 'A setzt locked_until nicht');
select throws_ok(
  $$update social_media.jobs set max_attempts = 99 where id = 'a1c00000-0000-0000-0000-000000000001'$$,
  '42501', null, 'A setzt max_attempts nicht');
select throws_ok(
  $$update social_media.jobs set run_after = now() where id = 'a1c00000-0000-0000-0000-000000000001'$$,
  '42501', null, 'A setzt run_after nicht');
select throws_ok(
  $$update social_media.jobs set kind = 'delete' where id = 'a1c00000-0000-0000-0000-000000000001'$$,
  '42501', null, 'A ändert den Typ nachträglich nicht');

-- Abbruch aus Nutzersicht
select lives_ok(
  $$update social_media.jobs set cancel_requested = true where id = 'a1c00000-0000-0000-0000-000000000002'$$,
  'A fordert den Abbruch eines laufenden Jobs an');
select is(
  (select status from social_media.jobs where id = 'a1c00000-0000-0000-0000-000000000002'),
  'running', 'der laufende Job bleibt running, bis der Worker ihn beendet');
select throws_ok(
  $$update social_media.jobs set cancel_requested = false where id = 'a1c00000-0000-0000-0000-000000000002'$$,
  '23514', null, 'A nimmt die Abbruchanforderung nicht zurück');
select throws_ok(
  $$update social_media.jobs set status = 'cancelled' where id = 'a1c00000-0000-0000-0000-000000000002'$$,
  '23514', null, 'A setzt einen laufenden Job nicht selbst auf cancelled');
select isnt_empty(
  $$update social_media.jobs set status = 'cancelled' where id = 'a1c00000-0000-0000-0000-000000000001' returning 1$$,
  'A bricht einen wartenden Job ab (queued -> cancelled)');
select is_empty(
  $$update social_media.jobs set cancel_requested = true where id = 'b2c00000-0000-0000-0000-000000000002' returning 1$$,
  'A fordert keinen Abbruch für den Job von B an');

-- Nutzer B sieht nichts von A
reset role;
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub":"bbbbbbbb-0000-0000-0000-000000000002","role":"authenticated"}', true);
select is((select count(*) from social_media.job_assets), 0::bigint, 'B sieht keine Verknüpfungen von A');
select is_empty(
  $$delete from social_media.job_assets returning 1$$, 'B löscht keine Verknüpfungen von A');

-- anon
reset role;
set local role anon;
select throws_ok($$select count(*) from social_media.job_assets$$, '42501', null, 'anon liest job_assets nicht');

-- Worker-Sicht (Superuser; die Trigger gelten auch für service_role)
reset role;
-- Retry: Versuche zählt der Trigger beim Start, nicht der Aufrufer
select lives_ok(
  $$update social_media.jobs set status = 'running', locked_by = 'w1', locked_until = now() + interval '1 minute'
    where id = 'b2c00000-0000-0000-0000-000000000002'$$,
  'Worker startet den Job (queued -> running mit Lease)');
select results_eq(
  $$select attempts from social_media.jobs where id = 'b2c00000-0000-0000-0000-000000000002'$$,
  $$values (1)$$, 'der Start zählt einen Versuch');
select lives_ok(
  $$update social_media.jobs set attempts = 0 where id = 'b2c00000-0000-0000-0000-000000000002'$$,
  'ein Zurücksetzen von attempts ...');
select results_eq(
  $$select attempts from social_media.jobs where id = 'b2c00000-0000-0000-0000-000000000002'$$,
  $$values (1)$$, '... bleibt wirkungslos');
select lives_ok(
  $$update social_media.jobs set status = 'queued' where id = 'b2c00000-0000-0000-0000-000000000002'$$,
  'running -> queued ist erlaubt, solange attempts < max_attempts');
select results_eq(
  $$select locked_by, locked_until from social_media.jobs where id = 'b2c00000-0000-0000-0000-000000000002'$$,
  $$values (null::text, null::timestamptz)$$, 'beim Zurückstellen endet die Lease');
select throws_ok(
  $$update social_media.jobs set locked_by = 'w2' where id = 'b2c00000-0000-0000-0000-000000000002'$$,
  '23514', null, 'ein wartender Job kann keine Lease halten');
select lives_ok(
  $$update social_media.jobs set status = 'running', locked_by = 'w2' where id = 'b2c00000-0000-0000-0000-000000000002'$$,
  'zweiter Versuch');
select lives_ok(
  $$update social_media.jobs set status = 'queued' where id = 'b2c00000-0000-0000-0000-000000000002'$$,
  'zweiter Versuch wird zurückgestellt');
select lives_ok(
  $$update social_media.jobs set status = 'running', locked_by = 'w3' where id = 'b2c00000-0000-0000-0000-000000000002'$$,
  'dritter Versuch');
select throws_ok(
  $$update social_media.jobs set status = 'queued' where id = 'b2c00000-0000-0000-0000-000000000002'$$,
  '23514', null, 'Retry über max_attempts hinaus -> Fehler');
select lives_ok(
  $$update social_media.jobs set status = 'failed', error = 'aus' where id = 'b2c00000-0000-0000-0000-000000000002'$$,
  'nach dem letzten Versuch bleibt nur failed');
select throws_ok(
  $$update social_media.jobs set status = 'queued' where id = 'b2c00000-0000-0000-0000-000000000002'$$,
  '23514', null, 'der Endzustand bleibt fest');
select throws_ok(
  $$update social_media.jobs set max_attempts = 0 where id = 'a1c00000-0000-0000-0000-000000000002'$$,
  '23514', null, 'max_attempts unter attempts ist ungültig');
select lives_ok(
  $$update social_media.jobs set status = 'cancelled' where id = 'a1c00000-0000-0000-0000-000000000002'$$,
  'der Worker beendet einen Job mit Abbruchanforderung als cancelled');

select * from finish();
rollback;
