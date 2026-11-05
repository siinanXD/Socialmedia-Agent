-- SIN-1382: creator_profiles und profile_audit (Mandantentrennung, Allowlists, Veröffentlichen-Schalter, Audit).
-- Läuft mit `supabase test db`. Nutzer A und B haben je einen Creator, Nutzer C hat keinen.
begin;
select plan(49);

-- Aufbau als Superuser (umgeht RLS). B bekommt ein Profil.
insert into auth.users (id, email) values
  ('aaaaaaaa-0000-0000-0000-000000000001', 'a@example.test'),
  ('bbbbbbbb-0000-0000-0000-000000000002', 'b@example.test'),
  ('cccccccc-0000-0000-0000-000000000003', 'c@example.test');
insert into social_media.creators (id, user_id, display_name) values
  ('a1000000-0000-0000-0000-000000000001', 'aaaaaaaa-0000-0000-0000-000000000001', 'A'),
  ('b2000000-0000-0000-0000-000000000002', 'bbbbbbbb-0000-0000-0000-000000000002', 'B');
insert into social_media.creator_profiles (creator_id, niche)
  values ('b2000000-0000-0000-0000-000000000002', 'Kochen');

-- Struktur
select has_table('social_media', 'creator_profiles', 'Tabelle creator_profiles existiert');
select has_table('social_media', 'profile_audit', 'Tabelle profile_audit existiert');
select is(
  (select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'social_media' and c.relname in ('creator_profiles', 'profile_audit') and c.relrowsecurity),
  2::bigint, 'RLS ist auf beiden Tabellen aktiv');
select is(
  (select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname in ('creator_profiles', 'profile_audit')),
  0::bigint, 'nichts davon liegt in public');

-- Nutzer A
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub":"aaaaaaaa-0000-0000-0000-000000000001","role":"authenticated"}', true);

select lives_ok(
  $$insert into social_media.creator_profiles (creator_id) values ('a1000000-0000-0000-0000-000000000001')$$,
  'A legt ein Profil nur mit creator_id an');
select is((select publish_enabled from social_media.creator_profiles
  where creator_id = 'a1000000-0000-0000-0000-000000000001'), false, 'Standard: Veröffentlichen ist aus');
select is((select default_budget_cap from social_media.creator_profiles
  where creator_id = 'a1000000-0000-0000-0000-000000000001'), 0::numeric, 'Standard: Budget 0');
select is((select platforms = '{}' and allowed_sources = '{}' and hashtags = '{}' from social_media.creator_profiles
  where creator_id = 'a1000000-0000-0000-0000-000000000001'), true, 'Standard: keine Plattformen, Quellen, Hashtags');

-- Mandantentrennung
select is((select count(*) from social_media.creator_profiles), 1::bigint, 'A sieht nur das eigene Profil');
select throws_ok(
  $$insert into social_media.creator_profiles (creator_id) values ('b2000000-0000-0000-0000-000000000002')$$,
  '42501', null, 'A kann kein Profil für Creator B anlegen');
select is_empty(
  $$update social_media.creator_profiles set niche = 'x'
    where creator_id = 'b2000000-0000-0000-0000-000000000002' returning 1$$,
  'A ändert das Profil von B nicht');
select is_empty(
  $$delete from social_media.creator_profiles where creator_id = 'b2000000-0000-0000-0000-000000000002' returning 1$$,
  'A löscht das Profil von B nicht');
select throws_ok(
  $$update social_media.creator_profiles set creator_id = 'b2000000-0000-0000-0000-000000000002'$$,
  '42501', null, 'A kann das Profil nicht auf Creator B umhängen (kein Spaltenrecht)');

-- Allowlists und Längen (CHECK)
select throws_ok(
  $$update social_media.creator_profiles set platforms = '{youtube,myspace}'$$,
  '23514', null, 'ungültige Plattform wird abgelehnt');
select throws_ok(
  $$update social_media.creator_profiles set platforms = '{youtube,null}'$$,
  '23514', null, 'NULL-Eintrag in platforms wird abgelehnt');
select throws_ok(
  $$update social_media.creator_profiles set allowed_sources = '{scraping}'$$,
  '23514', null, 'ungültige Quelle wird abgelehnt');
select throws_ok(
  $$update social_media.creator_profiles set hashtags = (select array_agg('tag' || i) from generate_series(1, 31) i)$$,
  '23514', null, 'mehr als 30 Hashtags werden abgelehnt');
select throws_ok(
  $$update social_media.creator_profiles set default_budget_cap = -1$$,
  '23514', null, 'negatives Budget wird abgelehnt');
select throws_ok(
  $$update social_media.creator_profiles set niche = repeat('n', 101)$$,
  '23514', null, 'zu lange Nische wird abgelehnt');
select throws_ok(
  $$update social_media.creator_profiles set tone = repeat('t', 501)$$,
  '23514', null, 'zu lange Tonalität wird abgelehnt');
select lives_ok(
  $$update social_media.creator_profiles
    set platforms = '{youtube,instagram,tiktok}', allowed_sources = '{creator_submitted,official_api,manual_import}',
        hashtags = (select array_agg('tag' || i) from generate_series(1, 30) i),
        reference_accounts = '{@vorbild}', kpis = '{views}', tone = 'locker',
        target_audience = 'Einsteiger', default_budget_cap = 5, niche = 'Gaming'$$,
  'A speichert ein vollständiges gültiges Profil (30 Hashtags sind erlaubt)');

-- Audit: Änderungen werden festgehalten, Nichtänderungen nicht
select is((select count(*) from social_media.profile_audit), 2::bigint, 'A sieht zwei Audit-Zeilen (anlegen, ändern)');
select lives_ok($$update social_media.creator_profiles set niche = niche$$, 'A speichert ohne Änderung');
select is((select count(*) from social_media.profile_audit), 2::bigint, 'eine Änderung ohne Wertänderung erzeugt keine Audit-Zeile');
select is(
  (select new_values ->> 'niche' from social_media.profile_audit where action = 'update'),
  'Gaming', 'Audit hält die neuen Werte fest');
select is(
  (select old_values ->> 'niche' from social_media.profile_audit where action = 'update'),
  '', 'Audit hält die alten Werte fest');
select is(
  (select changed_by from social_media.profile_audit where action = 'update'),
  'aaaaaaaa-0000-0000-0000-000000000001'::uuid, 'Audit nennt den ändernden Nutzer');

-- Veröffentlichen-Schalter: der Nutzer selbst darf
select lives_ok(
  $$update social_media.creator_profiles set publish_enabled = true$$,
  'A schaltet Veröffentlichen für das eigene Profil ein');
select is(
  (select new_values ->> 'publish_enabled' from social_media.profile_audit
    where action = 'update' order by id desc limit 1),
  'true', 'Audit hält das Einschalten fest');

-- Audit ist für Nutzer nur lesbar
select throws_ok(
  $$insert into social_media.profile_audit (creator_id, action) values ('a1000000-0000-0000-0000-000000000001', 'update')$$,
  '42501', null, 'A kann keine Audit-Zeile anlegen');
select throws_ok($$update social_media.profile_audit set action = 'insert'$$,
  '42501', null, 'A kann keine Audit-Zeile ändern');
select throws_ok($$delete from social_media.profile_audit$$,
  '42501', null, 'A kann keine Audit-Zeile löschen');

-- Anonym
reset role;
set local role anon;
select throws_ok($$select count(*) from social_media.creator_profiles$$, '42501', null, 'anon liest keine Profile');
select throws_ok($$select count(*) from social_media.profile_audit$$, '42501', null, 'anon liest kein Audit');
select throws_ok(
  $$insert into social_media.creator_profiles (creator_id) values ('a1000000-0000-0000-0000-000000000001')$$,
  '42501', null, 'anon legt kein Profil an');

-- Nutzer C ohne Creator
reset role;
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub":"cccccccc-0000-0000-0000-000000000003","role":"authenticated"}', true);
select is((select count(*) from social_media.creator_profiles), 0::bigint, 'C ohne Creator sieht keine Profile');
select is((select count(*) from social_media.profile_audit), 0::bigint, 'C ohne Creator sieht kein Audit');

-- Dienstrolle (Worker): darf Veröffentlichen nie einschalten, nur ausschalten
reset role;
set local role service_role;
select set_config('request.jwt.claims', '{"role":"service_role"}', true);
select throws_ok(
  $$update social_media.creator_profiles set publish_enabled = true
    where creator_id = 'b2000000-0000-0000-0000-000000000002'$$,
  '42501', null, 'service_role kann Veröffentlichen nicht einschalten');
select throws_ok(
  $$insert into social_media.creator_profiles (creator_id, publish_enabled)
    select id, true from social_media.creators where id = 'a1000000-0000-0000-0000-000000000001'
    on conflict (creator_id) do update set publish_enabled = true$$,
  '42501', null, 'service_role kann es auch nicht per Upsert einschalten');
select lives_ok(
  $$update social_media.creator_profiles set publish_enabled = false
    where creator_id = 'a1000000-0000-0000-0000-000000000001'$$,
  'service_role kann Veröffentlichen ausschalten (Notbremse)');
select is((select publish_enabled from social_media.creator_profiles
  where creator_id = 'b2000000-0000-0000-0000-000000000002'), false, 'B bleibt auf Veröffentlichen aus');

-- Zustandsregeln der Trigger, als Superuser (ohne Nutzerkennung)
reset role;
select set_config('request.jwt.claims', '', true);
select throws_ok(
  $$update social_media.creator_profiles set publish_enabled = true
    where creator_id = 'b2000000-0000-0000-0000-000000000002'$$,
  '42501', null, 'auch ohne Nutzerkennung lässt sich Veröffentlichen nicht einschalten');
select throws_ok($$update social_media.profile_audit set action = 'insert'$$,
  '23514', null, 'auch ein Superuser ändert keine Audit-Zeile');
select throws_ok($$delete from social_media.profile_audit where creator_id = 'b2000000-0000-0000-0000-000000000002'$$,
  '23514', null, 'auch ein Superuser löscht keine Audit-Zeile einzeln');
select throws_ok($$truncate social_media.profile_audit$$,
  '23514', null, 'auch ein Superuser leert das Audit nicht');
update social_media.creator_profiles set updated_at = '2020-01-01'
  where creator_id = 'b2000000-0000-0000-0000-000000000002';
select is((select updated_at > '2020-01-01' from social_media.creator_profiles
  where creator_id = 'b2000000-0000-0000-0000-000000000002'), true, 'updated_at setzt der Trigger, nicht der Aufrufer');
select is((select count(*) from social_media.profile_audit
  where creator_id = 'a1000000-0000-0000-0000-000000000001'), 4::bigint, 'Audit von A hat vier Zeilen (anlegen, ändern, ein, aus)');

-- Löschung: Creator löschen entfernt Profil und Audit per Cascade
select lives_ok($$delete from social_media.creators where id = 'a1000000-0000-0000-0000-000000000001'$$,
  'Creator A lässt sich löschen');
select is(
  (select count(*) from social_media.creator_profiles where creator_id = 'a1000000-0000-0000-0000-000000000001')
  + (select count(*) from social_media.profile_audit where creator_id = 'a1000000-0000-0000-0000-000000000001'),
  0::bigint, 'Profil und Audit von A sind mit gelöscht');

select * from finish();
rollback;
