-- H1-E3-T3 follow-up hardening: grants, auth profile provisioning,
-- SECURITY DEFINER search_path pinning, and public phase4 helpers bridged to app.*.

-- -----------------------------------------------------------------------------
-- 1) app schema privileges (RLS needs base privileges to be effective)
-- -----------------------------------------------------------------------------

grant usage on schema app to authenticated, service_role;

grant select, insert, update, delete on all tables in schema app to authenticated;
grant usage, select on all sequences in schema app to authenticated;
grant execute on all functions in schema app to authenticated;

grant all privileges on all tables in schema app to service_role;
grant all privileges on all sequences in schema app to service_role;
grant execute on all functions in schema app to service_role;

alter default privileges in schema app
  grant select, insert, update, delete on tables to authenticated;
alter default privileges in schema app
  grant usage, select on sequences to authenticated;
alter default privileges in schema app
  grant execute on functions to authenticated;

alter default privileges in schema app
  grant all privileges on tables to service_role;
alter default privileges in schema app
  grant all privileges on sequences to service_role;
alter default privileges in schema app
  grant execute on functions to service_role;

-- -----------------------------------------------------------------------------
-- 2) auth.users -> app.profiles auto-provisioning
-- -----------------------------------------------------------------------------

alter table app.profiles
  add column if not exists tier text not null default 'free';

alter table app.profiles
  add column if not exists quota_runs_per_month integer not null default 50;

alter table app.profiles
  drop constraint if exists ck_profiles_quota_runs_per_month_nonnegative;

alter table app.profiles
  add constraint ck_profiles_quota_runs_per_month_nonnegative
  check (quota_runs_per_month >= 0);

create or replace function app.handle_auth_user_profile_sync()
returns trigger
language plpgsql
security definer
set search_path = app
as $$
begin
  if tg_op = 'INSERT' or tg_op = 'UPDATE' then
    insert into app.profiles (id, display_name)
    values (
      new.id,
      coalesce(new.raw_user_meta_data->>'display_name', new.raw_user_meta_data->>'full_name')
    )
    on conflict (id) do update
      set display_name = coalesce(excluded.display_name, app.profiles.display_name),
          updated_at = now();
    return new;
  end if;

  if tg_op = 'DELETE' then
    delete from app.profiles where id = old.id;
    return old;
  end if;

  return null;
end;
$$;

revoke all on function app.handle_auth_user_profile_sync() from public;

drop trigger if exists on_auth_user_profile_sync_app on auth.users;
create trigger on_auth_user_profile_sync_app
  after insert or update or delete on auth.users
  for each row
  execute function app.handle_auth_user_profile_sync();

-- -----------------------------------------------------------------------------
-- 3) search_path hardening for helper functions
-- -----------------------------------------------------------------------------

create or replace function app.current_user_id()
returns uuid
language sql
stable
set search_path = app
as $$
  select auth.uid();
$$;

create or replace function app.is_project_owner(project_uuid uuid)
returns boolean
language sql
stable
security definer
set search_path = app
as $$
  select exists (
    select 1
    from app.projects p
    where p.id = project_uuid
      and p.owner_user_id = auth.uid()
  );
$$;

create or replace function app.owns_part_definition(part_definition_uuid uuid)
returns boolean
language sql
stable
security definer
set search_path = app
as $$
  select exists (
    select 1
    from app.part_definitions pd
    where pd.id = part_definition_uuid
      and pd.owner_user_id = auth.uid()
  );
$$;

create or replace function app.owns_sheet_definition(sheet_definition_uuid uuid)
returns boolean
language sql
stable
security definer
set search_path = app
as $$
  select exists (
    select 1
    from app.sheet_definitions sd
    where sd.id = sheet_definition_uuid
      and sd.owner_user_id = auth.uid()
  );
$$;

create or replace function app.can_access_geometry_revision(geometry_revision_uuid uuid)
returns boolean
language sql
stable
security definer
set search_path = app
as $$
  select exists (
    select 1
    from app.geometry_revisions gr
    join app.projects p on p.id = gr.project_id
    where gr.id = geometry_revision_uuid
      and p.owner_user_id = auth.uid()
  );
$$;

create or replace function app.can_access_run(run_uuid uuid)
returns boolean
language sql
stable
security definer
set search_path = app
as $$
  select exists (
    select 1
    from app.nesting_runs r
    join app.projects p on p.id = r.project_id
    where r.id = run_uuid
      and p.owner_user_id = auth.uid()
  );
$$;

create or replace function app.storage_object_project_id(object_name text)
returns uuid
language plpgsql
stable
set search_path = app
as $$
declare
  match_groups text[];
begin
  if object_name is null then
    return null;
  end if;

  match_groups := regexp_match(
    object_name,
    '^projects/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12})/'
  );

  if match_groups is null then
    return null;
  end if;

  return match_groups[1]::uuid;
end;
$$;

create or replace function app.set_updated_at()
returns trigger
language plpgsql
set search_path = app
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- -----------------------------------------------------------------------------
-- 4) SECURITY DEFINER hardening for part revision atomic helper
-- -----------------------------------------------------------------------------

create or replace function app.create_part_revision_atomic(
  p_part_definition_id             uuid,
  p_source_geometry_revision_id    uuid,
  p_selected_nesting_derivative_id uuid,
  p_source_label                   text default null,
  p_source_checksum_sha256         text default null,
  p_notes                          text default null
)
returns jsonb
language plpgsql
security definer
set search_path = app
as $$
declare
  v_definition  app.part_definitions%rowtype;
  v_next_rev_no integer;
  v_revision    app.part_revisions%rowtype;
begin
  select *
    into v_definition
    from app.part_definitions
   where id = p_part_definition_id
   for update;

  if v_definition.id is null then
    raise exception 'part_definition_not_found' using errcode = 'P0001';
  end if;

  if v_definition.owner_user_id <> app.current_user_id() then
    raise exception 'part_definition_forbidden' using errcode = '42501';
  end if;

  select coalesce(max(pr.revision_no), 0) + 1
    into v_next_rev_no
    from app.part_revisions pr
   where pr.part_definition_id = p_part_definition_id;

  insert into app.part_revisions (
    part_definition_id,
    revision_no,
    lifecycle,
    source_geometry_revision_id,
    selected_nesting_derivative_id,
    source_label,
    source_checksum_sha256,
    notes
  ) values (
    p_part_definition_id,
    v_next_rev_no,
    'draft',
    p_source_geometry_revision_id,
    p_selected_nesting_derivative_id,
    p_source_label,
    p_source_checksum_sha256,
    p_notes
  )
  returning * into v_revision;

  update app.part_definitions
     set current_revision_id = v_revision.id,
         updated_at          = now()
   where id = p_part_definition_id
  returning * into v_definition;

  return jsonb_build_object(
    'part_definition', to_jsonb(v_definition),
    'part_revision',   to_jsonb(v_revision)
  );
end;
$$;

revoke all on function app.create_part_revision_atomic(uuid, uuid, uuid, text, text, text) from public;
grant execute on function app.create_part_revision_atomic(uuid, uuid, uuid, text, text, text) to authenticated;
grant execute on function app.create_part_revision_atomic(uuid, uuid, uuid, text, text, text) to service_role;

-- -----------------------------------------------------------------------------
-- 5) Public phase4 SQL helpers bridged to app.* model
-- -----------------------------------------------------------------------------

create table if not exists app.cleanup_job_locks (
  lock_name text primary key,
  locked_until timestamptz not null default now(),
  owner text not null default 'edge-cleanup',
  updated_at timestamptz not null default now()
);

alter table app.cleanup_job_locks enable row level security;

drop policy if exists h1_e3_t3_cleanup_job_locks_service_role_all on app.cleanup_job_locks;
create policy h1_e3_t3_cleanup_job_locks_service_role_all
on app.cleanup_job_locks
for all
to service_role
using (true)
with check (true);

-- Harden legacy public.cleanup_job_locks as well when present.
do $$
begin
  if exists (
    select 1
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public'
      and c.relname = 'cleanup_job_locks'
      and c.relkind = 'r'
  ) then
    execute 'alter table public.cleanup_job_locks enable row level security';
    execute 'drop policy if exists h1_e3_t3_cleanup_job_locks_service_role_all on public.cleanup_job_locks';
    execute 'create policy h1_e3_t3_cleanup_job_locks_service_role_all on public.cleanup_job_locks for all to service_role using (true) with check (true)';
  end if;
end;
$$;

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

-- -----------------------------------------------------------------------------
-- 6) Quota RPC bridged from legacy public RPC to app.* model
-- -----------------------------------------------------------------------------

alter table app.nesting_runs
  add column if not exists run_config_id uuid;

alter table app.nesting_runs
  add column if not exists queued_at timestamptz;

alter table app.nesting_runs
  add column if not exists started_at timestamptz;

alter table app.nesting_runs
  add column if not exists finished_at timestamptz;

alter table app.nesting_runs
  add column if not exists duration_sec double precision;

alter table app.nesting_runs
  add column if not exists solver_exit_code integer;

alter table app.nesting_runs
  add column if not exists error_message text;

alter table app.nesting_runs
  add column if not exists placements_count integer;

alter table app.nesting_runs
  add column if not exists unplaced_count integer;

alter table app.nesting_runs
  add column if not exists sheet_count integer;

create table if not exists app.user_run_quota_monthly_usage (
  user_id uuid not null references app.profiles(id) on delete cascade,
  period_start date not null,
  used_runs integer not null default 0 check (used_runs >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (user_id, period_start)
);

create index if not exists idx_user_run_quota_monthly_usage_period
  on app.user_run_quota_monthly_usage(period_start);

alter table app.user_run_quota_monthly_usage enable row level security;

drop policy if exists h1_e3_t3_user_run_quota_usage_self_select on app.user_run_quota_monthly_usage;
create policy h1_e3_t3_user_run_quota_usage_self_select
on app.user_run_quota_monthly_usage
for select
to authenticated
using (user_id = app.current_user_id());

create or replace function public.enqueue_run_with_quota(
  p_project_id uuid,
  p_triggered_by uuid,
  p_run_config_id uuid default null
)
returns table (
  id uuid,
  project_id uuid,
  run_config_id uuid,
  triggered_by uuid,
  status text,
  queued_at timestamptz,
  started_at timestamptz,
  finished_at timestamptz,
  duration_sec double precision,
  solver_exit_code integer,
  error_message text,
  placements_count integer,
  unplaced_count integer,
  sheet_count integer
)
language plpgsql
security definer
set search_path = app
as $$
declare
  v_owner_id uuid;
  v_quota integer;
  v_used integer;
  v_period_start date;
  v_run app.nesting_runs%rowtype;
  v_snapshot app.nesting_run_snapshots%rowtype;
begin
  v_period_start := date_trunc('month', timezone('utc', now()))::date;

  select owner_user_id
    into v_owner_id
    from app.projects
   where id = p_project_id
   for update;
  if v_owner_id is null then
    raise exception 'project_not_found' using errcode = 'P0001';
  end if;
  if v_owner_id <> p_triggered_by then
    raise exception 'project_forbidden' using errcode = '42501';
  end if;

  select quota_runs_per_month
    into v_quota
    from app.profiles
   where id = p_triggered_by
   for update;
  if v_quota is null then
    raise exception 'user_profile_not_found' using errcode = 'P0001';
  end if;

  insert into app.user_run_quota_monthly_usage (user_id, period_start, used_runs)
  values (p_triggered_by, v_period_start, 0)
  on conflict (user_id, period_start) do nothing;

  select used_runs
    into v_used
    from app.user_run_quota_monthly_usage
   where user_id = p_triggered_by
     and period_start = v_period_start
   for update;

  if coalesce(v_used, 0) >= v_quota then
    raise exception 'quota_exceeded' using errcode = 'P0001';
  end if;

  update app.user_run_quota_monthly_usage
     set used_runs = used_runs + 1,
         updated_at = now()
   where user_id = p_triggered_by
     and period_start = v_period_start;

  insert into app.nesting_runs (
    project_id,
    requested_by,
    status,
    run_purpose,
    request_payload_jsonb,
    run_config_id,
    queued_at
  )
  values (
    p_project_id,
    p_triggered_by,
    'queued',
    'nesting',
    jsonb_build_object('source', 'enqueue_run_with_quota'),
    p_run_config_id,
    now()
  )
  returning * into v_run;

  insert into app.nesting_run_snapshots (
    run_id,
    status,
    snapshot_version,
    project_manifest_jsonb,
    technology_manifest_jsonb,
    parts_manifest_jsonb,
    sheets_manifest_jsonb,
    geometry_manifest_jsonb,
    solver_config_jsonb,
    manufacturing_manifest_jsonb,
    created_by
  )
  values (
    v_run.id,
    'building',
    'h0_queue_stub_v1',
    '{}'::jsonb,
    '{}'::jsonb,
    '[]'::jsonb,
    '[]'::jsonb,
    '[]'::jsonb,
    '{}'::jsonb,
    '{}'::jsonb,
    p_triggered_by
  )
  returning * into v_snapshot;

  insert into app.run_queue (
    run_id,
    snapshot_id,
    queue_state,
    attempt_no,
    priority,
    retry_count
  )
  values (
    v_run.id,
    v_snapshot.id,
    'pending',
    0,
    100,
    0
  );

  return query
    select
      v_run.id,
      v_run.project_id,
      v_run.run_config_id,
      v_run.requested_by as triggered_by,
      v_run.status::text,
      coalesce(v_run.queued_at, v_run.created_at),
      v_run.started_at,
      v_run.finished_at,
      v_run.duration_sec,
      v_run.solver_exit_code,
      v_run.error_message,
      v_run.placements_count,
      v_run.unplaced_count,
      v_run.sheet_count;
end;
$$;

revoke all on function public.enqueue_run_with_quota(uuid, uuid, uuid) from public;
grant execute on function public.enqueue_run_with_quota(uuid, uuid, uuid) to authenticated;
grant execute on function public.enqueue_run_with_quota(uuid, uuid, uuid) to service_role;
