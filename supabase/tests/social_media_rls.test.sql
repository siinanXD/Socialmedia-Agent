-- SIN-1168: Mandantentrennung, Idempotenz und Unveränderlichkeit im Schema social_media.
-- Läuft mit `supabase test db`. Nutzer A und B haben je einen Creator, Nutzer C hat keinen.
begin;
select plan(39);

-- Aufbau als Superuser (umgeht RLS)
insert into auth.users (id, email) values
  ('aaaaaaaa-0000-0000-0000-000000000001', 'a@example.test'),
  ('bbbbbbbb-0000-0000-0000-000000000002', 'b@example.test'),
  ('cccccccc-0000-0000-0000-000000000003', 'c@example.test');
insert into social_media.creators (id, user_id, display_name) values
  ('a1000000-0000-0000-0000-000000000001', 'aaaaaaaa-0000-0000-0000-000000000001', 'A'),
  ('b2000000-0000-0000-0000-000000000002', 'bbbbbbbb-0000-0000-0000-000000000002', 'B');
insert into social_media.assets (id, creator_id, storage_path, original_filename, sha256, mime_type, size_bytes) values
  ('a1a00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001',
   'a/clip.mp4', 'clip.mp4', repeat('a', 64), 'video/mp4', 1000),
  ('b2b00000-0000-0000-0000-000000000002', 'b2000000-0000-0000-0000-000000000002',
   'b/clip.mp4', 'clip.mp4', repeat('b', 64), 'video/mp4', 2000);
insert into social_media.jobs (id, creator_id, idempotency_key) values
  ('a1c00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 'key-a'),
  ('b2c00000-0000-0000-0000-000000000002', 'b2000000-0000-0000-0000-000000000002', 'key-b'),
  ('a1c00000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000001', 'key-a-run');
update social_media.jobs set status = 'running' where id = 'a1c00000-0000-0000-0000-000000000002';

-- Struktur: alles in social_media, RLS überall an
select has_schema('social_media');
select has_table('social_media', 'creators', 'Tabelle creators existiert');
select has_table('social_media', 'assets', 'Tabelle assets existiert');
select has_table('social_media', 'jobs', 'Tabelle jobs existiert');
select is(
  (select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'social_media' and c.relkind = 'r' and c.relrowsecurity),
  3::bigint, 'RLS ist auf allen drei Tabellen aktiv');
select is(
  (select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname in ('creators', 'assets', 'jobs')),
  0::bigint, 'nichts davon liegt in public');

-- Nutzer A
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub":"aaaaaaaa-0000-0000-0000-000000000001","role":"authenticated"}', true);

select is((select count(*) from social_media.creators), 1::bigint, 'A sieht nur den eigenen Creator');
select is((select count(*) from social_media.assets), 1::bigint, 'A sieht nur eigene Assets');
select is((select count(*) from social_media.jobs), 2::bigint, 'A sieht nur eigene Jobs');

select throws_ok(
  $$insert into social_media.assets (creator_id, storage_path, original_filename, sha256, mime_type, size_bytes)
    values ('b2000000-0000-0000-0000-000000000002', 'x/f.mp4', 'f.mp4', repeat('c', 64), 'video/mp4', 1)$$,
  '42501', null, 'A kann kein Asset für Creator B anlegen');
select throws_ok(
  $$insert into social_media.jobs (creator_id, idempotency_key)
    values ('b2000000-0000-0000-0000-000000000002', 'fremd')$$,
  '42501', null, 'A kann keinen Job für Creator B anlegen');
select throws_ok(
  $$insert into social_media.creators (user_id) values ('bbbbbbbb-0000-0000-0000-000000000002')$$,
  '42501', null, 'A kann keinen Creator für Nutzer B anlegen');

select is_empty(
  $$update social_media.creators set display_name = 'x'
    where id = 'b2000000-0000-0000-0000-000000000002' returning 1$$,
  'A ändert den Creator von B nicht');
select is_empty(
  $$update social_media.jobs set status = 'cancelled'
    where id = 'b2c00000-0000-0000-0000-000000000002' returning 1$$,
  'A bricht den Job von B nicht ab');
select is_empty(
  $$delete from social_media.assets where id = 'b2b00000-0000-0000-0000-000000000002' returning 1$$,
  'A löscht das Asset von B nicht');
select is_empty(
  $$delete from social_media.jobs where id = 'b2c00000-0000-0000-0000-000000000002' returning 1$$,
  'A löscht den Job von B nicht');

select isnt_empty(
  $$update social_media.creators set display_name = 'Anna'
    where id = 'a1000000-0000-0000-0000-000000000001' returning 1$$,
  'A ändert den eigenen Anzeigenamen');
select throws_ok(
  $$update social_media.creators set user_id = 'bbbbbbbb-0000-0000-0000-000000000002'$$,
  '42501', null, 'A kann user_id nicht umhängen (kein Spaltenrecht)');

-- Originale sind nicht überschreibbar
select throws_ok(
  $$update social_media.assets set sha256 = repeat('d', 64) where id = 'a1a00000-0000-0000-0000-000000000001'$$,
  '42501', null, 'A hat kein UPDATE-Recht auf Assets');
select throws_ok(
  $$insert into social_media.assets (creator_id, storage_path, original_filename, sha256, mime_type, size_bytes)
    values ('a1000000-0000-0000-0000-000000000001', 'a/zwei.mp4', 'zwei.mp4', repeat('a', 64), 'video/mp4', 1)$$,
  '23505', null, 'dieselbe Datei (SHA-256) wird je Creator nur einmal gespeichert');
select throws_ok(
  $$insert into social_media.assets (creator_id, storage_path, original_filename, sha256, mime_type, size_bytes)
    values ('a1000000-0000-0000-0000-000000000001', 'a/neu.exe', 'neu.exe', repeat('e', 64), 'application/x-msdownload', 1)$$,
  '23514', null, 'MIME-Typ außerhalb video/* und image/* wird abgelehnt');
select throws_ok(
  $$insert into social_media.assets (creator_id, storage_path, original_filename, sha256, mime_type, size_bytes, approval_status)
    values ('a1000000-0000-0000-0000-000000000001', 'a/frei.mp4', 'frei.mp4', repeat('f', 64), 'video/mp4', 1, 'freigegeben')$$,
  '42501', null, 'A kann ein Asset nicht selbst freigeben');

-- Idempotenz
select lives_ok(
  $$insert into social_media.jobs (creator_id, idempotency_key, budget_cap)
    values ('a1000000-0000-0000-0000-000000000001', 'neu-1', 5)$$,
  'A legt einen Job an');
select throws_ok(
  $$insert into social_media.jobs (creator_id, idempotency_key)
    values ('a1000000-0000-0000-0000-000000000001', 'neu-1')$$,
  '23505', null, 'derselbe idempotency_key erzeugt keinen zweiten Job');
select is_empty(
  $$insert into social_media.jobs (creator_id, idempotency_key)
    values ('a1000000-0000-0000-0000-000000000001', 'neu-1') on conflict do nothing returning 1$$,
  'on conflict do nothing legt ebenfalls nichts an');
select is(
  (select count(*) from social_media.jobs where idempotency_key = 'neu-1'),
  1::bigint, 'es gibt genau einen Job mit diesem Schlüssel');

-- Zustandsmaschine aus Nutzersicht
select throws_ok(
  $$insert into social_media.jobs (creator_id, idempotency_key, status)
    values ('a1000000-0000-0000-0000-000000000001', 'schon-fertig', 'succeeded')$$,
  '42501', null, 'A kann keinen Job direkt als succeeded anlegen');
select throws_ok(
  $$update social_media.jobs set status = 'succeeded' where id = 'a1c00000-0000-0000-0000-000000000001'$$,
  '23514', null, 'A kann einen wartenden Job nicht auf succeeded setzen (Trigger)');
select throws_ok(
  $$update social_media.jobs set status = 'succeeded' where id = 'a1c00000-0000-0000-0000-000000000002'$$,
  '42501', null, 'A kann einen laufenden Job nicht auf succeeded setzen (RLS)');
select isnt_empty(
  $$update social_media.jobs set status = 'cancelled' where id = 'a1c00000-0000-0000-0000-000000000001' returning 1$$,
  'A bricht den eigenen Job ab');

-- Anonym
reset role;
set local role anon;
select throws_ok($$select count(*) from social_media.assets$$, '42501', null, 'anon liest keine Assets');
select throws_ok(
  $$insert into social_media.jobs (creator_id, idempotency_key)
    values ('a1000000-0000-0000-0000-000000000001', 'anon')$$,
  '42501', null, 'anon legt keinen Job an');

-- Nutzer C ohne Creator
reset role;
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub":"cccccccc-0000-0000-0000-000000000003","role":"authenticated"}', true);
select is((select count(*) from social_media.jobs), 0::bigint, 'C ohne Creator sieht keine Jobs');
select throws_ok(
  $$insert into social_media.creators (user_id) values ('aaaaaaaa-0000-0000-0000-000000000001')$$,
  '42501', null, 'C kann keinen Creator für Nutzer A anlegen');

-- Zustandsregeln der Trigger, als Superuser (gelten auch für service_role)
reset role;
select throws_ok(
  $$update social_media.assets set sha256 = repeat('d', 64) where id = 'a1a00000-0000-0000-0000-000000000001'$$,
  '23514', null, 'auch ein Superuser überschreibt kein Original');
select lives_ok(
  $$update social_media.assets set approval_status = 'freigegeben' where id = 'a1a00000-0000-0000-0000-000000000001'$$,
  'der Freigabe-Status darf sich ändern');
select throws_ok(
  $$update social_media.jobs set status = 'succeeded' where id = 'b2c00000-0000-0000-0000-000000000002'$$,
  '23514', null, 'queued -> succeeded ist verboten');
select lives_ok(
  $$update social_media.jobs set status = 'running' where id = 'b2c00000-0000-0000-0000-000000000002'$$,
  'queued -> running ist erlaubt');
select throws_ok(
  $$update social_media.jobs set status = 'queued' where id = 'a1c00000-0000-0000-0000-000000000001'$$,
  '23514', null, 'ein abgebrochener Job bleibt abgebrochen');

select * from finish();
rollback;
