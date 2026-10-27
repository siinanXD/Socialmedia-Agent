begin;
select plan(2);
select has_table('probe', 'notes', 'table exists');
select is((select relrowsecurity from pg_class where oid = 'probe.notes'::regclass), true, 'rls on');
select * from finish();
rollback;
