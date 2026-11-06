-- SIN-1380: privater Bucket `social-media` und Policies auf storage.objects.
-- Die Migration liegt bewusst in supabase/tests/pending_migrations/ (nicht in migrations/), weil sie das fremde Schema `storage`
-- im gemeinsamen Projekt berührt; ob sie dort angewendet wird, entscheidet SIN-1411. Dieser Test lädt sie nur in
-- seiner eigenen Transaktion und belegt, dass bestehende Buckets und Policies unverändert bleiben.
begin;
select plan(25);

insert into auth.users (id, email) values
  ('aaaaaaaa-0000-0000-0000-000000000001', 'a@example.test'),
  ('bbbbbbbb-0000-0000-0000-000000000002', 'b@example.test');
insert into social_media.creators (id, user_id, display_name) values
  ('a1000000-0000-0000-0000-000000000001', 'aaaaaaaa-0000-0000-0000-000000000001', 'A'),
  ('b2000000-0000-0000-0000-000000000002', 'bbbbbbbb-0000-0000-0000-000000000002', 'B');

-- Snapshot vor der Migration: ein fremder Bucket mit Policy, dazu alle bestehenden Policies
insert into storage.buckets (id, name, public) values ('fremd', 'fremd', true);
create policy fremd_lesen on storage.objects for select using (bucket_id = 'fremd');
create temp table vorher as
  select policyname, cmd, roles, qual, with_check from pg_policies where schemaname = 'storage';
create temp table buckets_vorher as select id, name, public, file_size_limit, allowed_mime_types from storage.buckets;

\ir pending_migrations/20261106040000_sin1380_storage_bucket.psql

-- Bucket
select results_eq(
  $$select public, file_size_limit, allowed_mime_types from storage.buckets where id = 'social-media'$$,
  $$values (false, 524288000::bigint, array['video/mp4', 'video/quicktime', 'image/jpeg', 'image/png'])$$,
  'Bucket social-media: privat, 500 MB, nur MP4/MOV/JPEG/PNG');
select is(
  (select count(*) from (select id, name, public, file_size_limit, allowed_mime_types from storage.buckets
                         where id <> 'social-media'
                         except select * from buckets_vorher) d),
  0::bigint, 'bestehende Buckets unverändert');
select is(
  (select count(*) from (select * from vorher
                         except select policyname, cmd, roles, qual, with_check from pg_policies
                                where schemaname = 'storage') d),
  0::bigint, 'bestehende Policies unverändert');
select is(
  (select count(*) from pg_policies where schemaname = 'storage'
     and policyname not in (select policyname from vorher)
     and (qual not like '%''social-media''%' or coalesce(with_check, qual) not like '%''social-media''%')),
  0::bigint, 'jede neue Policy ist auf bucket_id = social-media begrenzt');
select is(
  (select count(*) from pg_policies where schemaname = 'storage' and policyname not in (select policyname from vorher)
     and cmd in ('UPDATE', 'ALL')),
  0::bigint, 'keine UPDATE-Policy: Originale werden nie überschrieben');

-- Nutzer A
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub":"aaaaaaaa-0000-0000-0000-000000000001","role":"authenticated"}', true);
select lives_ok(
  $$insert into storage.objects (bucket_id, name, owner_id)
    values ('social-media', 'originals/a1000000-0000-0000-0000-000000000001/x1/clip.mp4', 'aaaaaaaa-0000-0000-0000-000000000001')$$,
  'A lädt ins eigene originals/ hoch');
select throws_ok(
  $$insert into storage.objects (bucket_id, name, owner_id)
    values ('social-media', 'originals/b2000000-0000-0000-0000-000000000002/x1/clip.mp4', 'aaaaaaaa-0000-0000-0000-000000000001')$$,
  '42501', null, 'A lädt nicht in den Ordner von B');
select throws_ok(
  $$insert into storage.objects (bucket_id, name, owner_id)
    values ('social-media', 'derived/a1000000-0000-0000-0000-000000000001/j1/out.mp4', 'aaaaaaaa-0000-0000-0000-000000000001')$$,
  '42501', null, 'A schreibt nicht in derived/');
select throws_ok(
  $$insert into storage.objects (bucket_id, name, owner_id)
    values ('social-media', 'a1000000-0000-0000-0000-000000000001/clip.mp4', 'aaaaaaaa-0000-0000-0000-000000000001')$$,
  '42501', null, 'A schreibt nur unter originals/<creator>/');
select throws_ok(
  $$insert into storage.objects (bucket_id, name, owner_id)
    values ('social-media', 'originals/a1000000-0000-0000-0000-000000000001/x1/clip.mp4', 'aaaaaaaa-0000-0000-0000-000000000001')$$,
  '23505', null, 'gleicher Pfad noch einmal: kein Überschreiben');
-- DML in pgTAP-Ausdrücken geht nicht; deshalb ausführen und den Zustand danach als Superuser prüfen.
select lives_ok($$update storage.objects set name = name || '.neu'$$, 'UPDATE läuft ohne Fehler, aber …');
select lives_ok($$update storage.objects set metadata = '{"x":1}'$$, 'Metadaten-UPDATE läuft ohne Fehler, aber …');
reset role;
select results_eq(
  $$select name, metadata from storage.objects where bucket_id = 'social-media'$$,
  $$values ('originals/a1000000-0000-0000-0000-000000000001/x1/clip.mp4'::text, null::jsonb)$$,
  '… A hat weder Namen noch Metadaten des Originals geändert');

-- Worker (service_role) legt abgeleitete Medien an; B hat ein eigenes Original
insert into storage.objects (bucket_id, name) values
  ('social-media', 'derived/a1000000-0000-0000-0000-000000000001/j1/variante-1.mp4'),
  ('social-media', 'originals/b2000000-0000-0000-0000-000000000002/x2/clip.mp4'),
  ('fremd', 'originals/a1000000-0000-0000-0000-000000000001/x1/clip.mp4');

set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub":"aaaaaaaa-0000-0000-0000-000000000001","role":"authenticated"}', true);
select is(
  (select count(*) from storage.objects where bucket_id = 'social-media'),
  2::bigint, 'A liest eigenes Original und eigene abgeleitete Datei, nicht die von B');
select set_config('storage.allow_delete_query', 'true', true);
select lives_ok($$delete from storage.objects where bucket_id = 'social-media' and name like 'derived/%'$$,
  'Löschversuch derived/');
select lives_ok($$delete from storage.objects where bucket_id = 'social-media' and name like 'originals/b2%'$$,
  'Löschversuch bei B');
select lives_ok($$delete from storage.objects where bucket_id = 'social-media' and name like 'originals/a1%'$$,
  'Löschen des eigenen Originals');
reset role;
select results_eq(
  $$select name from storage.objects where bucket_id = 'social-media' order by name$$,
  $$values ('derived/a1000000-0000-0000-0000-000000000001/j1/variante-1.mp4'::text),
           ('originals/b2000000-0000-0000-0000-000000000002/x2/clip.mp4'::text)$$,
  'A hat nur das eigene Original gelöscht; derived/ und B bleiben');
set local role authenticated;

-- Nutzer B
select set_config('request.jwt.claims',
  '{"sub":"bbbbbbbb-0000-0000-0000-000000000002","role":"authenticated"}', true);
select is(
  (select count(*) from storage.objects where bucket_id = 'social-media'),
  1::bigint, 'B sieht nur das eigene Original');
select is(
  (select count(*) from storage.objects where name like '%a1000000-0000-0000-0000-000000000001%'
     and bucket_id = 'social-media'),
  0::bigint, 'B sieht nichts von A');
reset role;

-- anonym
set local role anon;
select is((select count(*) from storage.objects where bucket_id = 'social-media'), 0::bigint,
  'anon sieht nichts im Bucket');
select throws_ok(
  $$insert into storage.objects (bucket_id, name)
    values ('social-media', 'originals/a1000000-0000-0000-0000-000000000001/x9/clip.mp4')$$,
  '42501', null, 'anon lädt nichts hoch');
reset role;

-- Nutzer ohne Creator
insert into auth.users (id, email) values ('cccccccc-0000-0000-0000-000000000003', 'c@example.test');
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub":"cccccccc-0000-0000-0000-000000000003","role":"authenticated"}', true);
select throws_ok(
  $$insert into storage.objects (bucket_id, name, owner_id)
    values ('social-media', 'originals/a1000000-0000-0000-0000-000000000001/x3/clip.mp4', 'cccccccc-0000-0000-0000-000000000003')$$,
  '42501', null, 'Nutzer ohne Creator lädt nichts hoch');
select is((select count(*) from storage.objects where bucket_id = 'social-media'), 0::bigint,
  'Nutzer ohne Creator sieht nichts');
reset role;

-- Bestehender fremder Bucket bleibt für sich (Policy fremd_lesen unverändert wirksam)
set local role anon;
select is((select count(*) from storage.objects where bucket_id = 'fremd'), 1::bigint,
  'fremde Bucket-Policy wirkt weiter wie vorher');
reset role;

select * from finish();
rollback;
