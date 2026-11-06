-- SIN-1379: Queue-RPCs für den Worker. Nur service_role darf sie ausführen; SECURITY DEFINER mit leerem search_path,
-- damit die Zustandsregeln aus jobs_guard (SIN-1378) unverändert greifen. Additiv: nur Objekte in social_media.

alter table social_media.jobs add column result jsonb;

-- Holt den ältesten fälligen Job (FOR UPDATE SKIP LOCKED, mehrere Worker blockieren sich nicht).
-- Vorher: abgelaufene Leases zurückholen (Retry bis max_attempts, sonst failed) und Abbruchwünsche wartender Jobs erfüllen.
create function social_media.claim_next_job(worker_id text, lease_seconds integer, kinds text[] default null)
returns setof social_media.jobs
language plpgsql security definer set search_path = '' as $$
begin
  if worker_id is null or char_length(worker_id) not between 1 and 200 then
    raise exception 'claim_next_job: worker_id muss 1 bis 200 Zeichen haben' using errcode = 'invalid_parameter_value';
  end if;
  if lease_seconds is null or lease_seconds not between 1 and 3600 then
    raise exception 'claim_next_job: lease_seconds muss zwischen 1 und 3600 liegen' using errcode = 'invalid_parameter_value';
  end if;

  update social_media.jobs j set
    status = case when j.cancel_requested then 'cancelled'
                  when j.attempts < j.max_attempts then 'queued'
                  else 'failed' end,
    run_after = case when not j.cancel_requested and j.attempts < j.max_attempts then now() else j.run_after end,
    error = case when not j.cancel_requested and j.attempts >= j.max_attempts
                 then format('Lease abgelaufen nach %s von %s Versuchen', j.attempts, j.max_attempts)
                 else j.error end
  where j.id in (select e.id from social_media.jobs e
                 where e.status = 'running' and e.locked_until < now() for update skip locked);

  update social_media.jobs j set status = 'cancelled'
  where j.id in (select c.id from social_media.jobs c
                 where c.status = 'queued' and c.cancel_requested for update skip locked);

  return query
  update social_media.jobs j set
    status = 'running',
    locked_by = claim_next_job.worker_id,
    locked_until = now() + make_interval(secs => claim_next_job.lease_seconds)
  where j.id = (select q.id from social_media.jobs q
                where q.status = 'queued' and not q.cancel_requested and q.run_after <= now()
                  and (claim_next_job.kinds is null or q.kind = any (claim_next_job.kinds))
                order by q.run_after, q.created_at, q.id
                limit 1 for update skip locked)
  returning j.*;
end $$;

-- Sperrt den Job für den Aufrufer; nur der Lease-Inhaber eines laufenden Jobs kommt durch (sonst 55P03).
create function social_media.lease_holder(job_id uuid, worker_id text, fn text)
returns social_media.jobs
language plpgsql security definer set search_path = '' as $$
declare
  j social_media.jobs;
begin
  select * into j from social_media.jobs where id = lease_holder.job_id for update;
  if not found or j.status <> 'running' or j.locked_by is distinct from lease_holder.worker_id then
    raise exception '%: Job % läuft nicht bei Worker %', fn, lease_holder.job_id, lease_holder.worker_id
      using errcode = 'lock_not_available';
  end if;
  return j;
end $$;

-- Verlängert die Lease und meldet Fortschritt. Liefert true, wenn der Nutzer abbrechen will; der Job ist dann cancelled.
create function social_media.heartbeat_job(job_id uuid, worker_id text, progress integer, lease_seconds integer default 300)
returns boolean
language plpgsql security definer set search_path = '' as $$
declare
  j social_media.jobs := social_media.lease_holder(heartbeat_job.job_id, heartbeat_job.worker_id, 'heartbeat_job');
begin
  if j.cancel_requested then
    update social_media.jobs set status = 'cancelled' where id = j.id;
    return true;
  end if;
  if heartbeat_job.lease_seconds is null or heartbeat_job.lease_seconds not between 1 and 3600 then
    raise exception 'heartbeat_job: lease_seconds muss zwischen 1 und 3600 liegen' using errcode = 'invalid_parameter_value';
  end if;
  update social_media.jobs set
    progress = heartbeat_job.progress,
    locked_until = now() + make_interval(secs => heartbeat_job.lease_seconds)
  where id = j.id;
  return false;
end $$;

-- Idempotent: ein schon erfolgreicher Job bleibt, wie er ist (kein zweites Ergebnis).
create function social_media.complete_job(job_id uuid, worker_id text, result jsonb)
returns social_media.jobs
language plpgsql security definer set search_path = '' as $$
declare
  j social_media.jobs;
begin
  select * into j from social_media.jobs where id = complete_job.job_id;
  if found and j.status = 'succeeded' then
    return j;
  end if;
  j := social_media.lease_holder(complete_job.job_id, complete_job.worker_id, 'complete_job');
  update social_media.jobs set status = 'succeeded', progress = 100, result = complete_job.result
  where id = j.id returning * into j;
  return j;
end $$;

-- Mit retry und freien Versuchen wartet der Job wieder (Backoff 30 s, 60 s, 120 s … höchstens 1 h), sonst failed.
-- Ein Abbruchwunsch gewinnt. Idempotent: ein schon fehlgeschlagener Job bleibt, wie er ist.
create function social_media.fail_job(job_id uuid, worker_id text, error text, retry boolean default true)
returns social_media.jobs
language plpgsql security definer set search_path = '' as $$
declare
  j social_media.jobs;
begin
  select * into j from social_media.jobs where id = fail_job.job_id;
  if found and j.status = 'failed' then
    return j;
  end if;
  j := social_media.lease_holder(fail_job.job_id, fail_job.worker_id, 'fail_job');
  update social_media.jobs set
    status = case when j.cancel_requested then 'cancelled'
                  when fail_job.retry and j.attempts < j.max_attempts then 'queued'
                  else 'failed' end,
    error = left(fail_job.error, 2000),
    run_after = case when not j.cancel_requested and fail_job.retry and j.attempts < j.max_attempts
                     then now() + least(interval '1 hour', interval '30 seconds' * power(2, j.attempts - 1))
                     else j.run_after end
  where id = j.id returning * into j;
  return j;
end $$;

-- Funktionen sind standardmäßig für PUBLIC ausführbar; hier nur für den Worker (service_role).
revoke all on function social_media.claim_next_job(text, integer, text[]) from public, anon, authenticated;
revoke all on function social_media.lease_holder(uuid, text, text) from public, anon, authenticated;
revoke all on function social_media.heartbeat_job(uuid, text, integer, integer) from public, anon, authenticated;
revoke all on function social_media.complete_job(uuid, text, jsonb) from public, anon, authenticated;
revoke all on function social_media.fail_job(uuid, text, text, boolean) from public, anon, authenticated;
grant execute on function social_media.claim_next_job(text, integer, text[]) to service_role;
grant execute on function social_media.heartbeat_job(uuid, text, integer, integer) to service_role;
grant execute on function social_media.complete_job(uuid, text, jsonb) to service_role;
grant execute on function social_media.fail_job(uuid, text, text, boolean) to service_role;
