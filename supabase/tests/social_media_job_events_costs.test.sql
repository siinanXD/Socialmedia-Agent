-- SIN-1384: job_events (Audit, nur Anfügen), cost_entries mit Budget-Grenze, View job_cost_summary.
-- Läuft mit `supabase test db`. Nutzer A und B haben je einen Creator und Jobs.
begin;
select plan(32);

insert into auth.users (id, email) values
  ('aaaaaaaa-0000-0000-0000-000000000001', 'a@example.test'),
  ('bbbbbbbb-0000-0000-0000-000000000002', 'b@example.test');
insert into social_media.creators (id, user_id, display_name) values
  ('a1000000-0000-0000-0000-000000000001', 'aaaaaaaa-0000-0000-0000-000000000001', 'A'),
  ('b2000000-0000-0000-0000-000000000002', 'bbbbbbbb-0000-0000-0000-000000000002', 'B');
-- ja: Budget 0 (Standard), jb: Budget 1,00 €, jB: Job von B
insert into social_media.jobs (id, creator_id, idempotency_key, budget_cap) values
  ('a1c00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 'ja', 0),
  ('a1c00000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000001', 'jb', 1),
  ('b2c00000-0000-0000-0000-000000000001', 'b2000000-0000-0000-0000-000000000002', 'jB', 0);

-- Struktur
select has_table('social_media', 'job_events', 'Tabelle job_events');
select has_table('social_media', 'cost_entries', 'Tabelle cost_entries');
select has_view('social_media', 'job_cost_summary', 'View job_cost_summary');
select is(
  (select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'social_media' and c.relname in ('job_events', 'cost_entries') and c.relrowsecurity),
  2::bigint, 'RLS auf job_events und cost_entries');

-- Worker (service_role) schreibt Ereignisse und Kosten
set local role service_role;
select lives_ok(
  $$insert into social_media.job_events (job_id, creator_id, level, code, message)
    values ('a1c00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 'info', 'claimed', 'Job übernommen')$$,
  'Worker schreibt ein Ereignis');
select lives_ok(
  $$insert into social_media.job_events (job_id, creator_id, level, code, message, data)
    values ('a1c00000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000001', 'error', 'render_failed',
            'Render abgebrochen', '{"versuch": 1}')$$,
  'Worker schreibt ein Fehlerereignis mit Daten');
select throws_ok(
  $$insert into social_media.job_events (job_id, creator_id, level, code, message)
    values ('a1c00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 'debug', 'x', 'x')$$,
  '23514', null, 'unbekannte Stufe wird abgelehnt');
select throws_ok(
  $$insert into social_media.job_events (job_id, creator_id, level, code, message)
    values ('a1c00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 'info', 'x', repeat('m', 501))$$,
  '23514', null, 'Meldung über 500 Zeichen wird abgelehnt');
select throws_ok(
  $$insert into social_media.job_events (job_id, creator_id, level, code, message)
    values ('b2c00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 'info', 'x', 'x')$$,
  '23503', null, 'Ereignis zu fremdem Job ist nicht verknüpfbar');
select lives_ok(
  $$insert into social_media.cost_entries (job_id, creator_id, provider, item, amount_eur)
    values ('a1c00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 'ffmpeg', 'render', 0)$$,
  '0-€-Posten bei Budget 0 erlaubt');
select throws_ok(
  $$insert into social_media.cost_entries (job_id, creator_id, provider, item, amount_eur)
    values ('a1c00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 'llm', 'caption', 0.0001)$$,
  '53400', null, 'bezahlter Posten bei Budget 0 wird abgelehnt');
select lives_ok(
  $$insert into social_media.cost_entries (job_id, creator_id, provider, item, amount_eur)
    values ('a1c00000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000001', 'llm', 'caption', 0.6)$$,
  'Posten im Budget');
select lives_ok(
  $$insert into social_media.cost_entries (job_id, creator_id, provider, item, amount_eur)
    values ('a1c00000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000001', 'llm', 'hooks', 0.4)$$,
  'Posten genau bis zum Budget');
select throws_ok(
  $$insert into social_media.cost_entries (job_id, creator_id, provider, item, amount_eur)
    values ('a1c00000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000001', 'llm', 'hooks', 0.0001)$$,
  '53400', null, 'Posten über dem Budget wird abgelehnt');
select throws_ok(
  $$insert into social_media.cost_entries (job_id, creator_id, provider, item, amount_eur)
    values ('a1c00000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000001', 'llm', 'x', -1)$$,
  '23514', null, 'negativer Betrag wird abgelehnt');
select throws_ok($$update social_media.job_events set message = 'x'$$, '42501', null,
  'auch der Worker ändert keine Ereignisse');
select throws_ok($$delete from social_media.cost_entries$$, '42501', null, 'auch der Worker löscht keine Kosten');
reset role;
select throws_ok($$update social_media.job_events set message = 'x'$$, '23514', null,
  'Ereignisse bleiben auch für den Superuser fest');
select throws_ok($$delete from social_media.cost_entries$$, '23514', null,
  'Kosten bleiben auch für den Superuser fest');

-- Nutzer A
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub":"aaaaaaaa-0000-0000-0000-000000000001","role":"authenticated"}', true);
select is((select count(*) from social_media.job_events), 2::bigint, 'A sieht die eigenen Ereignisse');
select results_eq(
  $$select total_eur, budget_cap from social_media.job_cost_summary
    where job_id = 'a1c00000-0000-0000-0000-000000000002'$$,
  $$values (1.0000::numeric, 1.00::numeric)$$, 'Kostenübersicht: 1,00 € von 1,00 €');
select results_eq(
  $$select total_eur from social_media.job_cost_summary where job_id = 'a1c00000-0000-0000-0000-000000000001'$$,
  $$values (0.0000::numeric)$$, 'Kostenübersicht: 0,00 € bei 0-€-Posten');
select throws_ok(
  $$insert into social_media.job_events (job_id, creator_id, level, code, message)
    values ('a1c00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 'info', 'x', 'x')$$,
  '42501', null, 'Nutzer schreibt keine Ereignisse');
select throws_ok(
  $$insert into social_media.cost_entries (job_id, creator_id, provider, item, amount_eur)
    values ('a1c00000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 'x', 'x', 0)$$,
  '42501', null, 'Nutzer schreibt keine Kosten');

-- Nutzer B
select set_config('request.jwt.claims',
  '{"sub":"bbbbbbbb-0000-0000-0000-000000000002","role":"authenticated"}', true);
select is((select count(*) from social_media.job_events), 0::bigint, 'B sieht keine Ereignisse von A');
select is((select count(*) from social_media.cost_entries), 0::bigint, 'B sieht keine Kosten von A');
select results_eq($$select job_id, total_eur from social_media.job_cost_summary$$,
  $$values ('b2c00000-0000-0000-0000-000000000001'::uuid, 0.0000::numeric)$$,
  'B sieht in der Übersicht nur den eigenen Job');

-- anonym
reset role;
set local role anon;
select throws_ok($$select * from social_media.job_events$$, '42501', null, 'anon liest keine Ereignisse');
select throws_ok($$select * from social_media.job_cost_summary$$, '42501', null, 'anon liest keine Kosten');
reset role;

-- Löschen des Jobs nimmt Ereignisse und Kosten mit (Cascade), sonst bleibt beides fest
select lives_ok($$delete from social_media.jobs where id = 'a1c00000-0000-0000-0000-000000000002'$$,
  'Job mit Ereignissen und Kosten lässt sich löschen');
select is((select count(*) from social_media.job_events where job_id = 'a1c00000-0000-0000-0000-000000000002'),
  0::bigint, 'Ereignisse des gelöschten Jobs sind weg');
select is((select count(*) from social_media.cost_entries where job_id = 'a1c00000-0000-0000-0000-000000000002'),
  0::bigint, 'Kosten des gelöschten Jobs sind weg');

select * from finish();
rollback;
