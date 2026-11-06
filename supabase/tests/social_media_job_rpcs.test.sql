-- SIN-1379: Queue-RPCs claim_next_job, heartbeat_job, complete_job, fail_job (nur service_role).
-- Läuft mit `supabase test db`. now() ist in der Transaktion fest, Zeiten stehen deshalb relativ dazu.
begin;
select plan(47);

insert into auth.users (id, email) values ('aaaaaaaa-0000-0000-0000-000000000001', 'a@example.test');
insert into social_media.creators (id, user_id, display_name) values
  ('a1000000-0000-0000-0000-000000000001', 'aaaaaaaa-0000-0000-0000-000000000001', 'A');
-- Reihenfolge nach run_after: j4 (Abbruch gewünscht), j1, j2 (render), j7, j3 und j8 liegen in der Zukunft.
insert into social_media.jobs (id, creator_id, idempotency_key, kind, run_after, max_attempts, cancel_requested) values
  ('c0000000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 'j1', 'analyze', now() - interval '2 min', 3, false),
  ('c0000000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000001', 'j2', 'render', now() - interval '1 min', 3, false),
  ('c0000000-0000-0000-0000-000000000003', 'a1000000-0000-0000-0000-000000000001', 'j3', 'analyze', now() + interval '1 hour', 3, false),
  ('c0000000-0000-0000-0000-000000000004', 'a1000000-0000-0000-0000-000000000001', 'j4', 'analyze', now() - interval '3 min', 3, true),
  ('c0000000-0000-0000-0000-000000000005', 'a1000000-0000-0000-0000-000000000001', 'j5', 'analyze', now() - interval '9 min', 3, false),
  ('c0000000-0000-0000-0000-000000000006', 'a1000000-0000-0000-0000-000000000001', 'j6', 'analyze', now() - interval '9 min', 1, false),
  ('c0000000-0000-0000-0000-000000000007', 'a1000000-0000-0000-0000-000000000001', 'j7', 'analyze', now() - interval '30 sec', 3, false),
  ('c0000000-0000-0000-0000-000000000008', 'a1000000-0000-0000-0000-000000000001', 'j8', 'analyze', now() + interval '2 hours', 1, false);
-- j5 und j6 laufen bei einem verschwundenen Worker, ihre Lease ist abgelaufen; j8 läuft bei w1.
update social_media.jobs set status = 'running', locked_by = 'w-alt', locked_until = now() - interval '1 min'
  where id in ('c0000000-0000-0000-0000-000000000005', 'c0000000-0000-0000-0000-000000000006');
update social_media.jobs set status = 'running', locked_by = 'w1', locked_until = now() + interval '1 min'
  where id = 'c0000000-0000-0000-0000-000000000008';

-- Struktur
select has_function('social_media', 'claim_next_job', array['text', 'integer', 'text[]'], 'claim_next_job existiert');
select has_function('social_media', 'heartbeat_job', array['uuid', 'text', 'integer', 'integer'], 'heartbeat_job existiert');
select has_function('social_media', 'complete_job', array['uuid', 'text', 'jsonb'], 'complete_job existiert');
select has_function('social_media', 'fail_job', array['uuid', 'text', 'text', 'boolean'], 'fail_job existiert');
select has_column('social_media', 'jobs', 'result', 'jobs.result');
select is(
  (select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'social_media' and p.proname in ('claim_next_job', 'heartbeat_job', 'complete_job', 'fail_job')
      and p.prosecdef and p.proconfig @> array['search_path=""']),
  4::bigint, 'alle vier sind SECURITY DEFINER mit leerem search_path');

-- Rechte: nur service_role
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub":"aaaaaaaa-0000-0000-0000-000000000001","role":"authenticated"}', true);
select throws_ok($$select * from social_media.claim_next_job('w', 60, null)$$, '42501', null,
  'authenticated darf claim_next_job nicht ausführen');
select throws_ok($$select social_media.heartbeat_job('c0000000-0000-0000-0000-000000000008', 'w1', 10, 60)$$,
  '42501', null, 'authenticated darf heartbeat_job nicht ausführen');
select throws_ok($$select social_media.complete_job('c0000000-0000-0000-0000-000000000008', 'w1', '{}')$$,
  '42501', null, 'authenticated darf complete_job nicht ausführen');
select throws_ok($$select social_media.fail_job('c0000000-0000-0000-0000-000000000008', 'w1', 'x', false)$$,
  '42501', null, 'authenticated darf fail_job nicht ausführen');
select throws_ok(
  $$insert into social_media.jobs (creator_id, idempotency_key, result)
    values ('a1000000-0000-0000-0000-000000000001', 'k', '{}')$$,
  '42501', null, 'authenticated setzt kein result');
reset role;
set local role anon;
select throws_ok($$select * from social_media.claim_next_job('w', 60, null)$$, '42501', null,
  'anon darf claim_next_job nicht ausführen');
reset role;

-- Claim
set local role service_role;
select throws_ok($$select * from social_media.claim_next_job('w1', 0, null)$$, '22023', null,
  'Lease von 0 Sekunden wird abgelehnt');
select throws_ok($$select * from social_media.claim_next_job('', 60, null)$$, '22023', null,
  'leere worker_id wird abgelehnt');
select is((select id from social_media.claim_next_job('w1', 60, array['analyze', 'render'])),
  'c0000000-0000-0000-0000-000000000001'::uuid, '1. Claim: ältester wartender Job ohne Abbruchwunsch');
select results_eq(
  $$select status, locked_by, attempts, locked_until = now() + interval '60 seconds' from social_media.jobs
    where id = 'c0000000-0000-0000-0000-000000000001'$$,
  $$values ('running'::text, 'w1'::text, 1, true)$$,
  'geclaimter Job läuft bei w1, Versuch 1, Lease 60 s');
select is((select status from social_media.jobs where id = 'c0000000-0000-0000-0000-000000000004'),
  'cancelled', 'wartender Job mit Abbruchwunsch wird beim Claim abgebrochen');
select results_eq(
  $$select status, attempts, locked_by, run_after = now() from social_media.jobs
    where id = 'c0000000-0000-0000-0000-000000000005'$$,
  $$values ('queued'::text, 1, null::text, true)$$,
  'abgelaufene Lease mit Versuchen übrig: Job wartet wieder, ohne Lease');
select results_eq(
  $$select status, error from social_media.jobs where id = 'c0000000-0000-0000-0000-000000000006'$$,
  $$values ('failed'::text, 'Lease abgelaufen nach 1 von 1 Versuchen'::text)$$,
  'abgelaufene Lease nach max_attempts: failed mit Grund');
select is((select id from social_media.claim_next_job('w1', 60, null)),
  'c0000000-0000-0000-0000-000000000002'::uuid, '2. Claim liefert einen anderen Job');
select is((select count(*) from social_media.claim_next_job('w2', 60, array['export'])), 0::bigint,
  'kein wartender Job dieser Art: leeres Ergebnis');
select is((select id from social_media.claim_next_job('w1', 60, array['analyze'])),
  'c0000000-0000-0000-0000-000000000007'::uuid, '3. Claim nur analyze');
select is((select id from social_media.claim_next_job('w2', 60, array['analyze'])),
  'c0000000-0000-0000-0000-000000000005'::uuid, 'zurückgeholter Job wird neu vergeben');
select is((select attempts from social_media.jobs where id = 'c0000000-0000-0000-0000-000000000005'),
  2, 'neu vergeben zählt als 2. Versuch');
select is((select count(*) from social_media.claim_next_job('w1', 60, null)), 0::bigint,
  'nur noch Jobs in der Zukunft: leeres Ergebnis');

-- Heartbeat
select throws_ok($$select social_media.heartbeat_job('c0000000-0000-0000-0000-000000000001', 'w-falsch', 10, 60)$$,
  '55P03', null, 'falscher Worker: kein Heartbeat');
select throws_ok($$select social_media.heartbeat_job('c0000000-0000-0000-0000-000000000003', 'w1', 10, 60)$$,
  '55P03', null, 'wartender Job: kein Heartbeat');
select is(social_media.heartbeat_job('c0000000-0000-0000-0000-000000000001', 'w1', 40, 120), false,
  'Heartbeat ohne Abbruchwunsch liefert false');
select results_eq(
  $$select progress::int, locked_until = now() + interval '120 seconds' from social_media.jobs
    where id = 'c0000000-0000-0000-0000-000000000001'$$,
  $$values (40, true)$$, 'Heartbeat setzt Fortschritt und verlängert die Lease');
reset role;
update social_media.jobs set cancel_requested = true where id = 'c0000000-0000-0000-0000-000000000002';
set local role service_role;
select is(social_media.heartbeat_job('c0000000-0000-0000-0000-000000000002', 'w1', 50, 60), true,
  'Heartbeat mit Abbruchwunsch liefert true');
select results_eq(
  $$select status, locked_by from social_media.jobs where id = 'c0000000-0000-0000-0000-000000000002'$$,
  $$values ('cancelled'::text, null::text)$$, 'und bricht den Job kontrolliert ab');

-- Complete
select throws_ok($$select social_media.complete_job('c0000000-0000-0000-0000-000000000001', 'w-falsch', '{}')$$,
  '55P03', null, 'falscher Worker: kein complete');
select is((social_media.complete_job('c0000000-0000-0000-0000-000000000001', 'w1', '{"clips":1}')).status,
  'succeeded', 'complete beendet den Job');
select results_eq(
  $$select progress::int, result, locked_by from social_media.jobs where id = 'c0000000-0000-0000-0000-000000000001'$$,
  $$values (100, '{"clips":1}'::jsonb, null::text)$$, 'Ergebnis gespeichert, Fortschritt 100, Lease frei');
select lives_ok($$select social_media.complete_job('c0000000-0000-0000-0000-000000000001', 'w1', '{"clips":2}')$$,
  'zweites complete läuft ohne Fehler');
select is((select result from social_media.jobs where id = 'c0000000-0000-0000-0000-000000000001'),
  '{"clips":1}'::jsonb, 'zweites complete ändert nichts');
select throws_ok($$select social_media.complete_job('c0000000-0000-0000-0000-000000000003', 'w1', '{}')$$,
  '55P03', null, 'wartender Job lässt sich nicht abschließen');

-- Fail
select throws_ok($$select social_media.fail_job('c0000000-0000-0000-0000-000000000005', 'w1', 'x', true)$$,
  '55P03', null, 'falscher Worker: kein fail');
select is((social_media.fail_job('c0000000-0000-0000-0000-000000000005', 'w2', 'Netz weg', true)).status,
  'queued', 'fail mit retry und Versuchen übrig: wartet wieder');
select results_eq(
  $$select error, locked_by, run_after = now() + interval '60 seconds' from social_media.jobs
    where id = 'c0000000-0000-0000-0000-000000000005'$$,
  $$values ('Netz weg'::text, null::text, true)$$, 'Fehler gespeichert, Backoff 60 s nach Versuch 2');
select is((select count(*) from social_media.claim_next_job('w1', 60, null)), 0::bigint,
  'Job im Backoff wird nicht sofort wieder vergeben');
select is((social_media.fail_job('c0000000-0000-0000-0000-000000000007', 'w1', 'kaputt', false)).status,
  'failed', 'fail ohne retry: failed');
select is((social_media.fail_job('c0000000-0000-0000-0000-000000000007', 'w1', 'nochmal', false)).error,
  'kaputt', 'zweites fail ändert nichts');
select is((social_media.fail_job('c0000000-0000-0000-0000-000000000008', 'w1', 'x', true)).status,
  'failed', 'fail mit retry bei ausgeschöpften Versuchen: failed');
select is(char_length((select error from social_media.jobs where id = 'c0000000-0000-0000-0000-000000000008')),
  1, 'Fehlertext gespeichert');
reset role;
insert into social_media.jobs (id, creator_id, idempotency_key, run_after) values
  ('c0000000-0000-0000-0000-000000000009', 'a1000000-0000-0000-0000-000000000001', 'j9', now() - interval '1 hour');
set local role service_role;
select is((select id from social_media.claim_next_job('w1', 60, null)),
  'c0000000-0000-0000-0000-000000000009'::uuid, 'j9 geclaimt');
select is(char_length((social_media.fail_job('c0000000-0000-0000-0000-000000000009', 'w1', repeat('x', 5000), false)).error),
  2000, 'langer Fehlertext wird auf 2000 Zeichen gekürzt');
reset role;

select * from finish();
rollback;
