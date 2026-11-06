-- SIN-1381: asset_checks, asset_rights, asset_usable und creator_limits (Quote je Creator).
-- Läuft mit `supabase test db`. Nutzer A und B haben je einen Creator und Assets.
begin;
select plan(41);

insert into auth.users (id, email) values
  ('aaaaaaaa-0000-0000-0000-000000000001', 'a@example.test'),
  ('bbbbbbbb-0000-0000-0000-000000000002', 'b@example.test');
insert into social_media.creators (id, user_id, display_name) values
  ('a1000000-0000-0000-0000-000000000001', 'aaaaaaaa-0000-0000-0000-000000000001', 'A'),
  ('b2000000-0000-0000-0000-000000000002', 'bbbbbbbb-0000-0000-0000-000000000002', 'B');
insert into social_media.assets (id, creator_id, storage_path, original_filename, sha256, mime_type, size_bytes) values
  ('a1a00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001',
   'a/1.mp4', '1.mp4', repeat('1', 64), 'video/mp4', 1000),
  ('a1a00000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000001',
   'a/2.mp4', '2.mp4', repeat('2', 64), 'video/mp4', 1000),
  ('b2b00000-0000-0000-0000-000000000001', 'b2000000-0000-0000-0000-000000000002',
   'b/1.mp4', '1.mp4', repeat('3', 64), 'video/mp4', 1000);
-- Prüfergebnisse schreibt der Worker (hier der Aufbau als Superuser).
insert into social_media.asset_checks (asset_id, creator_id, kind, status) values
  ('a1a00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 'validate', 'clean'),
  ('a1a00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 'scan', 'clean'),
  ('a1a00000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000001', 'validate', 'clean'),
  ('a1a00000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000001', 'scan', 'pending'),
  ('b2b00000-0000-0000-0000-000000000001', 'b2000000-0000-0000-0000-000000000002', 'validate', 'clean');

-- Struktur
select has_table('social_media', 'asset_checks', 'Tabelle asset_checks');
select has_table('social_media', 'asset_rights', 'Tabelle asset_rights');
select has_table('social_media', 'creator_limits', 'Tabelle creator_limits');
select has_function('social_media', 'asset_usable', array['uuid'], 'Funktion asset_usable');
select is(
  (select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'social_media' and c.relname in ('asset_checks', 'asset_rights', 'creator_limits')
      and c.relrowsecurity),
  3::bigint, 'RLS auf allen drei Tabellen');
select throws_ok(
  $$insert into social_media.asset_checks (asset_id, creator_id, kind, status)
    values ('a1a00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 'virus', 'clean')$$,
  '23514', null, 'unbekannte Prüfart wird abgelehnt');
select throws_ok(
  $$insert into social_media.asset_checks (asset_id, creator_id, kind, status)
    values ('b2b00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 'scan', 'clean')$$,
  '23503', null, 'Prüfung zu fremdem Asset ist nicht verknüpfbar');

-- Nutzer A
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub":"aaaaaaaa-0000-0000-0000-000000000001","role":"authenticated"}', true);
select is((select count(*) from social_media.asset_checks), 4::bigint, 'A sieht nur eigene Prüfungen');
select throws_ok(
  $$insert into social_media.asset_checks (asset_id, creator_id, kind, status)
    values ('a1a00000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000001', 'scan', 'clean')$$,
  '42501', null, 'Nutzer schreibt keine Prüfergebnisse');
select throws_ok(
  $$update social_media.asset_checks set status = 'clean'$$,
  '42501', null, 'Nutzer ändert keine Prüfergebnisse');
select lives_ok(
  $$insert into social_media.asset_rights (asset_id, creator_id, source, statement)
    values ('a1a00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 'own',
            'Selbst gefilmt, alle Personen haben zugestimmt.')$$,
  'A bestätigt Rechte am eigenen Asset');
select lives_ok(
  $$insert into social_media.asset_rights (asset_id, creator_id, source, statement)
    values ('a1a00000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000001', 'licensed',
            'Lizenz liegt vor.')$$,
  'A bestätigt Rechte am zweiten Asset');
select throws_ok(
  $$insert into social_media.asset_rights (asset_id, creator_id, source, statement)
    values ('b2b00000-0000-0000-0000-000000000001', 'b2000000-0000-0000-0000-000000000002', 'own', 'x')$$,
  '42501', null, 'A bestätigt keine Rechte für B');
select throws_ok(
  $$insert into social_media.asset_rights (asset_id, creator_id, source, statement)
    values ('b2b00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 'own', 'x')$$,
  '23503', null, 'A bestätigt keine Rechte an B-Asset unter eigenem Creator');
select throws_ok(
  $$insert into social_media.asset_rights (asset_id, creator_id, source, statement)
    values ('a1a00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 'gefunden', 'x')$$,
  '23514', null, 'unbekannte Rechte-Quelle wird abgelehnt');
select throws_ok(
  $$insert into social_media.asset_rights (asset_id, creator_id, source, statement)
    values ('a1a00000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000001', 'own', '')$$,
  '23514', null, 'leere Erklärung wird abgelehnt');
select throws_ok(
  $$update social_media.asset_rights set source = 'reference'$$,
  '42501', null, 'Rechte-Bestätigung bleibt fest');
select is(social_media.asset_usable('a1a00000-0000-0000-0000-000000000001'), true,
  'geprüft, sauber, Rechte bestätigt: verwendbar');
select is(social_media.asset_usable('a1a00000-0000-0000-0000-000000000002'), false,
  'Virenscan pending: nicht verwendbar');
select throws_ok(
  $$insert into social_media.creator_limits (creator_id, max_assets) values ('a1000000-0000-0000-0000-000000000001', 9999)$$,
  '42501', null, 'Nutzer legt keine Limits an');
reset role;
insert into social_media.creator_limits (creator_id, max_assets, max_storage_bytes)
  values ('a1000000-0000-0000-0000-000000000001', 3, 10000);
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub":"aaaaaaaa-0000-0000-0000-000000000001","role":"authenticated"}', true);
select throws_ok(
  $$update social_media.creator_limits set max_assets = 9999$$,
  '42501', null, 'Nutzer hebt Limits nicht an');
select is((select max_assets from social_media.creator_limits), 3, 'A liest das eigene Limit');

-- Nutzer B
select set_config('request.jwt.claims',
  '{"sub":"bbbbbbbb-0000-0000-0000-000000000002","role":"authenticated"}', true);
select is((select count(*) from social_media.asset_checks), 1::bigint, 'B sieht nur eigene Prüfungen');
select is((select count(*) from social_media.asset_rights), 0::bigint, 'B sieht keine Rechte von A');
select is((select count(*) from social_media.creator_limits), 0::bigint, 'B sieht das Limit von A nicht');
select is(social_media.asset_usable('a1a00000-0000-0000-0000-000000000001'), false,
  'fremdes Asset ist für B nicht verwendbar');

-- anonym
reset role;
set local role anon;
select throws_ok($$select * from social_media.asset_rights$$, '42501', null, 'anon liest keine Rechte');
select throws_ok($$select social_media.asset_usable('a1a00000-0000-0000-0000-000000000001')$$, '42501', null,
  'anon ruft asset_usable nicht auf');
reset role;

-- asset_usable ist fail-closed (als Superuser, Zustände je Fall umgestellt)
update social_media.asset_checks set status = 'infected'
  where asset_id = 'a1a00000-0000-0000-0000-000000000002' and kind = 'scan';
select is(social_media.asset_usable('a1a00000-0000-0000-0000-000000000002'), false, 'infected: nicht verwendbar');
update social_media.asset_checks set status = 'unavailable'
  where asset_id = 'a1a00000-0000-0000-0000-000000000002' and kind = 'scan';
select is(social_media.asset_usable('a1a00000-0000-0000-0000-000000000002'), false,
  'Scanner nicht verfügbar: nicht verwendbar');
delete from social_media.asset_checks where asset_id = 'a1a00000-0000-0000-0000-000000000002' and kind = 'scan';
select is(social_media.asset_usable('a1a00000-0000-0000-0000-000000000002'), false,
  'Scan fehlt: nicht verwendbar');
insert into social_media.asset_checks (asset_id, creator_id, kind, status)
  values ('a1a00000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000001', 'scan', 'clean');
select is(social_media.asset_usable('a1a00000-0000-0000-0000-000000000002'), true,
  'nach sauberem Scan verwendbar');
delete from social_media.asset_rights where asset_id = 'a1a00000-0000-0000-0000-000000000002';
select is(social_media.asset_usable('a1a00000-0000-0000-0000-000000000002'), false,
  'ohne Rechte-Bestätigung: nicht verwendbar');
update social_media.assets set approval_status = 'abgelehnt' where id = 'a1a00000-0000-0000-0000-000000000001';
select is(social_media.asset_usable('a1a00000-0000-0000-0000-000000000001'), false,
  'abgelehntes Asset: nicht verwendbar');
select is(social_media.asset_usable('00000000-0000-0000-0000-000000000000'), false,
  'unbekanntes Asset: nicht verwendbar');

-- Quote (A: höchstens 3 Assets, 10000 Bytes; vorhanden 2 Assets, 2000 Bytes)
select lives_ok(
  $$insert into social_media.assets (creator_id, storage_path, original_filename, sha256, mime_type, size_bytes)
    values ('a1000000-0000-0000-0000-000000000001', 'a/3.mp4', '3.mp4', repeat('4', 64), 'video/mp4', 1000)$$,
  'drittes Asset passt in die Quote');
select throws_ok(
  $$insert into social_media.assets (creator_id, storage_path, original_filename, sha256, mime_type, size_bytes)
    values ('a1000000-0000-0000-0000-000000000001', 'a/4.mp4', '4.mp4', repeat('5', 64), 'video/mp4', 1)$$,
  '53400', null, 'viertes Asset überschreitet max_assets');
update social_media.creator_limits set max_assets = 10 where creator_id = 'a1000000-0000-0000-0000-000000000001';
select throws_ok(
  $$insert into social_media.assets (creator_id, storage_path, original_filename, sha256, mime_type, size_bytes)
    values ('a1000000-0000-0000-0000-000000000001', 'a/5.mp4', '5.mp4', repeat('6', 64), 'video/mp4', 7001)$$,
  '53400', null, 'Speicher über max_storage_bytes wird abgelehnt');
select lives_ok(
  $$insert into social_media.assets (creator_id, storage_path, original_filename, sha256, mime_type, size_bytes)
    values ('a1000000-0000-0000-0000-000000000001', 'a/6.mp4', '6.mp4', repeat('7', 64), 'video/mp4', 7000)$$,
  'genau bis zur Speichergrenze erlaubt');
select col_default_is('social_media', 'creator_limits', 'max_storage_bytes', '5368709120'::text,
  'Standard: 5 GiB');
select col_default_is('social_media', 'creator_limits', 'max_assets', '500'::text, 'Standard: 500 Assets');

select * from finish();
rollback;
