-- Phase 4 P4.7 cleanup orchestration helpers
-- DEPRECATED LEGACY NOTE:
--   This file is kept for backward compatibility, but it is aligned to app.*
--   tables/functions. Canonical rollout is via Supabase migrations.

create table if not exists app.cleanup_job_locks (
  lock_name text primary key,
  locked_until timestamptz not null default now(),
  owner text not null default 'edge-cleanup',
  updated_at timestamptz not null default now()
);

alter table app.cleanup_job_locks enable row level security;

drop policy if exists phase4_cleanup_job_locks_service_role_all on app.cleanup_job_locks;
create policy phase4_cleanup_job_locks_service_role_all
on app.cleanup_job_locks
for all
to service_role
using (true)
with check (true);

create or replace function public.try_acquire_cleanup_lock(
  p_lock_name text,
  p_owner text default 'edge-cleanup',
  p_ttl_seconds integer default 600
)
returns boolean
language plpgsql
security definer
set search_path = app
as $$
declare
  v_deadline timestamptz := now() + make_interval(secs => greatest(1, p_ttl_seconds));
  v_acquired boolean := false;
begin
  insert into app.cleanup_job_locks (lock_name, locked_until, owner, updated_at)
  values (p_lock_name, v_deadline, coalesce(nullif(p_owner, ''), 'edge-cleanup'), now())
  on conflict (lock_name) do update
    set locked_until = excluded.locked_until,
        owner = excluded.owner,
        updated_at = now()
  where app.cleanup_job_locks.locked_until <= now()
  returning true into v_acquired;

  return coalesce(v_acquired, false);
end;
$$;

create or replace function public.release_cleanup_lock(p_lock_name text)
returns void
language sql
security definer
set search_path = app
as $$
  update app.cleanup_job_locks
     set locked_until = now(),
         updated_at = now()
   where lock_name = p_lock_name;
$$;

create or replace function public.list_cleanup_candidates(p_limit integer default 200)
returns table (
  candidate_type text,
  row_id uuid,
  storage_key text
)
language sql
security definer
set search_path = app
as $$
with failed_or_cancelled as (
  select
    'run_artifact'::text as candidate_type,
    ra.id as row_id,
    ra.storage_path as storage_key,
    ra.created_at as ts
  from app.run_artifacts ra
  join app.nesting_runs r on r.id = ra.run_id
  where r.status::text in ('failed', 'cancelled')
    and ra.created_at <= now() - interval '7 days'
),
archived_project_files as (
  select
    'project_file'::text as candidate_type,
    fo.id as row_id,
    fo.storage_path as storage_key,
    coalesce(p.updated_at, p.created_at, fo.created_at) as ts
  from app.file_objects fo
  join app.projects p on p.id = fo.project_id
  where p.lifecycle = 'archived'
    and coalesce(p.updated_at, p.created_at, fo.created_at) <= now() - interval '30 days'
),
bundle_zip_files as (
  select
    'run_artifact'::text as candidate_type,
    ra.id as row_id,
    ra.storage_path as storage_key,
    ra.created_at as ts
  from app.run_artifacts ra
  where ra.artifact_kind = 'bundle_zip'
    and ra.created_at <= now() - interval '24 hours'
),
unioned as (
  select * from failed_or_cancelled
  union all
  select * from archived_project_files
  union all
  select * from bundle_zip_files
)
select u.candidate_type, u.row_id, u.storage_key
from unioned u
order by u.ts asc
limit greatest(1, p_limit);
$$;

create or replace function public.delete_cleanup_candidate(
  p_candidate_type text,
  p_row_id uuid
)
returns boolean
language plpgsql
security definer
set search_path = app
as $$
declare
  v_deleted integer := 0;
begin
  if p_candidate_type = 'run_artifact' then
    delete from app.run_artifacts where id = p_row_id;
    get diagnostics v_deleted = row_count;
    return v_deleted > 0;
  end if;

  if p_candidate_type = 'project_file' then
    delete from app.file_objects where id = p_row_id;
    get diagnostics v_deleted = row_count;
    return v_deleted > 0;
  end if;

  return false;
end;
$$;

revoke all on function public.try_acquire_cleanup_lock(text, text, integer) from public;
revoke all on function public.release_cleanup_lock(text) from public;
revoke all on function public.list_cleanup_candidates(integer) from public;
revoke all on function public.delete_cleanup_candidate(text, uuid) from public;

grant execute on function public.try_acquire_cleanup_lock(text, text, integer) to service_role;
grant execute on function public.release_cleanup_lock(text) to service_role;
grant execute on function public.list_cleanup_candidates(integer) to service_role;
grant execute on function public.delete_cleanup_candidate(text, uuid) to service_role;
