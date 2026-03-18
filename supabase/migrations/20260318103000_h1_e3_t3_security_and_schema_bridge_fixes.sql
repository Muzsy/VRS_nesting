-- H1-E3-T3 follow-up hardening: grants, auth profile provisioning,
-- SECURITY DEFINER search_path pinning, and public phase4 helpers bridged to app.*.

-- -----------------------------------------------------------------------------
-- 1) app schema privileges (RLS needs base privileges to be effective)
-- -----------------------------------------------------------------------------

grant usage on schema app to authenticated, anon, service_role;

grant select, insert, update, delete on all tables in schema app to authenticated;
grant usage, select on all sequences in schema app to authenticated;
grant execute on all functions in schema app to authenticated;

grant select on all tables in schema app to anon;

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
  grant select on tables to anon;

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

-- -----------------------------------------------------------------------------
-- 7) Explicit bridge for legacy public.* API table names -> app.* source-of-truth
-- -----------------------------------------------------------------------------

-- Ensure app run status can represent legacy API lifecycle labels.
do $$
begin
  if not exists (
    select 1
    from pg_enum e
    join pg_type t on t.oid = e.enumtypid
    join pg_namespace n on n.oid = t.typnamespace
    where n.nspname = 'app'
      and t.typname = 'run_request_status'
      and e.enumlabel = 'running'
  ) then
    alter type app.run_request_status add value 'running';
  end if;

  if not exists (
    select 1
    from pg_enum e
    join pg_type t on t.oid = e.enumtypid
    join pg_namespace n on n.oid = t.typnamespace
    where n.nspname = 'app'
      and t.typname = 'run_request_status'
      and e.enumlabel = 'done'
  ) then
    alter type app.run_request_status add value 'done';
  end if;

  if not exists (
    select 1
    from pg_enum e
    join pg_type t on t.oid = e.enumtypid
    join pg_namespace n on n.oid = t.typnamespace
    where n.nspname = 'app'
      and t.typname = 'run_request_status'
      and e.enumlabel = 'failed'
  ) then
    alter type app.run_request_status add value 'failed';
  end if;
end;
$$;

create table if not exists app.run_configs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references app.projects(id) on delete cascade,
  created_by uuid not null references app.profiles(id) on delete restrict,
  name text,
  schema_version text not null default 'dxf_v1',
  seed integer not null default 0,
  time_limit_s integer not null default 60,
  spacing_mm double precision not null default 2.0,
  margin_mm double precision not null default 5.0,
  stock_file_id uuid not null references app.file_objects(id) on delete restrict,
  parts_config jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  check (schema_version <> ''),
  check (time_limit_s > 0),
  check (spacing_mm >= 0),
  check (margin_mm >= 0)
);

create index if not exists idx_run_configs_project_id
  on app.run_configs(project_id, created_at desc);

alter table app.run_configs enable row level security;

drop policy if exists h1_e3_t3_run_configs_select_owner on app.run_configs;
create policy h1_e3_t3_run_configs_select_owner
on app.run_configs
for select
to authenticated
using (app.is_project_owner(project_id));

drop policy if exists h1_e3_t3_run_configs_insert_owner on app.run_configs;
create policy h1_e3_t3_run_configs_insert_owner
on app.run_configs
for insert
to authenticated
with check (app.is_project_owner(project_id) and created_by = app.current_user_id());

drop policy if exists h1_e3_t3_run_configs_update_owner on app.run_configs;
create policy h1_e3_t3_run_configs_update_owner
on app.run_configs
for update
to authenticated
using (app.is_project_owner(project_id))
with check (app.is_project_owner(project_id));

drop policy if exists h1_e3_t3_run_configs_delete_owner on app.run_configs;
create policy h1_e3_t3_run_configs_delete_owner
on app.run_configs
for delete
to authenticated
using (app.is_project_owner(project_id));

create or replace function app.legacy_artifact_type_to_kind(legacy_artifact_type text)
returns app.artifact_kind
language sql
immutable
set search_path = app
as $$
  select case coalesce(legacy_artifact_type, '')
    when 'sheet_dxf' then 'sheet_dxf'::app.artifact_kind
    when 'sheet_svg' then 'sheet_svg'::app.artifact_kind
    when 'bundle_zip' then 'bundle_zip'::app.artifact_kind
    when 'machine_program' then 'machine_program'::app.artifact_kind
    when 'report_json' then 'report_json'::app.artifact_kind
    when 'run_log' then 'log'::app.artifact_kind
    when 'solver_output' then 'solver_output'::app.artifact_kind
    when 'solver_input' then 'solver_output'::app.artifact_kind
    else 'log'::app.artifact_kind
  end;
$$;

create or replace function app.artifact_kind_to_legacy_type(
  kind app.artifact_kind,
  metadata jsonb default '{}'::jsonb
)
returns text
language sql
stable
set search_path = app
as $$
  select coalesce(
    metadata->>'legacy_artifact_type',
    case kind
      when 'log' then 'run_log'
      else kind::text
    end
  );
$$;

-- Create compatibility views only when legacy public table does not already exist.
do $$
begin
  if to_regclass('public.projects') is null then
    execute $ddl$
      create view public.projects as
      select
        p.id,
        p.owner_user_id as owner_id,
        p.name,
        p.description,
        p.created_at,
        p.updated_at,
        null::timestamptz as archived_at
      from app.projects p
    $ddl$;
  elsif exists (
    select 1
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = 'projects' and c.relkind = 'v'
  ) then
    execute $ddl$
      create or replace view public.projects as
      select
        p.id,
        p.owner_user_id as owner_id,
        p.name,
        p.description,
        p.created_at,
        p.updated_at,
        null::timestamptz as archived_at
      from app.projects p
    $ddl$;
  end if;
end;
$$;

do $$
begin
  if to_regclass('public.project_files') is null then
    execute $ddl$
      create view public.project_files as
      select
        fo.id,
        fo.project_id,
        fo.uploaded_by,
        fo.file_kind::text as file_type,
        fo.file_name as original_filename,
        fo.storage_path as storage_key,
        fo.byte_size as size_bytes,
        fo.sha256 as content_hash_sha256,
        null::text as validation_status,
        null::text as validation_error,
        fo.created_at as uploaded_at
      from app.file_objects fo
    $ddl$;
  elsif exists (
    select 1
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = 'project_files' and c.relkind = 'v'
  ) then
    execute $ddl$
      create or replace view public.project_files as
      select
        fo.id,
        fo.project_id,
        fo.uploaded_by,
        fo.file_kind::text as file_type,
        fo.file_name as original_filename,
        fo.storage_path as storage_key,
        fo.byte_size as size_bytes,
        fo.sha256 as content_hash_sha256,
        null::text as validation_status,
        null::text as validation_error,
        fo.created_at as uploaded_at
      from app.file_objects fo
    $ddl$;
  end if;
end;
$$;

do $$
begin
  if to_regclass('public.run_configs') is null then
    execute $ddl$
      create view public.run_configs as
      select
        rc.id,
        rc.project_id,
        rc.created_by,
        rc.name,
        rc.schema_version,
        rc.seed,
        rc.time_limit_s,
        rc.spacing_mm,
        rc.margin_mm,
        rc.stock_file_id,
        rc.parts_config,
        rc.created_at
      from app.run_configs rc
    $ddl$;
  elsif exists (
    select 1
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = 'run_configs' and c.relkind = 'v'
  ) then
    execute $ddl$
      create or replace view public.run_configs as
      select
        rc.id,
        rc.project_id,
        rc.created_by,
        rc.name,
        rc.schema_version,
        rc.seed,
        rc.time_limit_s,
        rc.spacing_mm,
        rc.margin_mm,
        rc.stock_file_id,
        rc.parts_config,
        rc.created_at
      from app.run_configs rc
    $ddl$;
  end if;
end;
$$;

do $$
begin
  if to_regclass('public.runs') is null then
    execute $ddl$
      create view public.runs as
      select
        r.id,
        r.project_id,
        r.run_config_id,
        r.requested_by as triggered_by,
        r.status::text as status,
        r.queued_at,
        r.started_at,
        r.finished_at,
        r.duration_sec,
        r.solver_exit_code,
        r.error_message,
        r.placements_count,
        r.unplaced_count,
        r.sheet_count
      from app.nesting_runs r
    $ddl$;
  elsif exists (
    select 1
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = 'runs' and c.relkind = 'v'
  ) then
    execute $ddl$
      create or replace view public.runs as
      select
        r.id,
        r.project_id,
        r.run_config_id,
        r.requested_by as triggered_by,
        r.status::text as status,
        r.queued_at,
        r.started_at,
        r.finished_at,
        r.duration_sec,
        r.solver_exit_code,
        r.error_message,
        r.placements_count,
        r.unplaced_count,
        r.sheet_count
      from app.nesting_runs r
    $ddl$;
  end if;
end;
$$;

do $$
begin
  if to_regclass('public.run_queue') is null then
    execute $ddl$
      create view public.run_queue as
      select
        rq.run_id,
        rq.priority,
        rq.attempt_no as attempts,
        3::integer as max_attempts,
        rq.leased_by as locked_by,
        rq.leased_at as locked_at,
        rq.available_at as visible_after,
        rq.created_at
      from app.run_queue rq
    $ddl$;
  elsif exists (
    select 1
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = 'run_queue' and c.relkind = 'v'
  ) then
    execute $ddl$
      create or replace view public.run_queue as
      select
        rq.run_id,
        rq.priority,
        rq.attempt_no as attempts,
        3::integer as max_attempts,
        rq.leased_by as locked_by,
        rq.leased_at as locked_at,
        rq.available_at as visible_after,
        rq.created_at
      from app.run_queue rq
    $ddl$;
  end if;
end;
$$;

do $$
begin
  if to_regclass('public.run_artifacts') is null then
    execute $ddl$
      create view public.run_artifacts as
      select
        ra.id,
        ra.run_id,
        app.artifact_kind_to_legacy_type(ra.artifact_kind, ra.metadata_jsonb) as artifact_type,
        coalesce(ra.metadata_jsonb->>'filename', regexp_replace(ra.storage_path, '^.*/', '')) as filename,
        ra.storage_path as storage_key,
        nullif(ra.metadata_jsonb->>'size_bytes', '')::bigint as size_bytes,
        nullif(ra.metadata_jsonb->>'sheet_index', '')::integer as sheet_index,
        ra.created_at
      from app.run_artifacts ra
    $ddl$;
  elsif exists (
    select 1
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = 'run_artifacts' and c.relkind = 'v'
  ) then
    execute $ddl$
      create or replace view public.run_artifacts as
      select
        ra.id,
        ra.run_id,
        app.artifact_kind_to_legacy_type(ra.artifact_kind, ra.metadata_jsonb) as artifact_type,
        coalesce(ra.metadata_jsonb->>'filename', regexp_replace(ra.storage_path, '^.*/', '')) as filename,
        ra.storage_path as storage_key,
        nullif(ra.metadata_jsonb->>'size_bytes', '')::bigint as size_bytes,
        nullif(ra.metadata_jsonb->>'sheet_index', '')::integer as sheet_index,
        ra.created_at
      from app.run_artifacts ra
    $ddl$;
  end if;
end;
$$;

create or replace function public.run_configs_view_iud()
returns trigger
language plpgsql
security definer
set search_path = app
as $$
declare
  v_row app.run_configs%rowtype;
begin
  if tg_op = 'INSERT' then
    if not app.is_project_owner(new.project_id) then
      raise exception 'project_forbidden' using errcode = '42501';
    end if;

    insert into app.run_configs (
      project_id,
      created_by,
      name,
      schema_version,
      seed,
      time_limit_s,
      spacing_mm,
      margin_mm,
      stock_file_id,
      parts_config
    ) values (
      new.project_id,
      coalesce(new.created_by, app.current_user_id()),
      new.name,
      coalesce(new.schema_version, 'dxf_v1'),
      coalesce(new.seed, 0),
      coalesce(new.time_limit_s, 60),
      coalesce(new.spacing_mm, 2.0),
      coalesce(new.margin_mm, 5.0),
      new.stock_file_id,
      coalesce(new.parts_config, '[]'::jsonb)
    ) returning * into v_row;

    new.id := v_row.id;
    new.created_by := v_row.created_by;
    new.created_at := v_row.created_at;
    return new;
  end if;

  if tg_op = 'UPDATE' then
    update app.run_configs
       set name = new.name,
           schema_version = coalesce(new.schema_version, app.run_configs.schema_version),
           seed = coalesce(new.seed, app.run_configs.seed),
           time_limit_s = coalesce(new.time_limit_s, app.run_configs.time_limit_s),
           spacing_mm = coalesce(new.spacing_mm, app.run_configs.spacing_mm),
           margin_mm = coalesce(new.margin_mm, app.run_configs.margin_mm),
           stock_file_id = coalesce(new.stock_file_id, app.run_configs.stock_file_id),
           parts_config = coalesce(new.parts_config, app.run_configs.parts_config)
     where id = old.id
     returning * into v_row;

    if v_row.id is null then
      raise exception 'run_config_not_found' using errcode = 'P0001';
    end if;

    new.id := v_row.id;
    new.project_id := v_row.project_id;
    new.created_by := v_row.created_by;
    new.created_at := v_row.created_at;
    return new;
  end if;

  if tg_op = 'DELETE' then
    delete from app.run_configs where id = old.id;
    return old;
  end if;

  return null;
end;
$$;

create or replace function public.runs_view_iud()
returns trigger
language plpgsql
security definer
set search_path = app
as $$
declare
  v_row app.nesting_runs%rowtype;
begin
  if tg_op = 'INSERT' then
    if not app.is_project_owner(new.project_id) then
      raise exception 'project_forbidden' using errcode = '42501';
    end if;

    insert into app.nesting_runs (
      project_id,
      requested_by,
      status,
      run_purpose,
      request_payload_jsonb,
      run_config_id,
      queued_at,
      started_at,
      finished_at,
      duration_sec,
      solver_exit_code,
      error_message,
      placements_count,
      unplaced_count,
      sheet_count
    ) values (
      new.project_id,
      coalesce(new.triggered_by, app.current_user_id()),
      coalesce(new.status, 'queued')::app.run_request_status,
      'nesting',
      '{}'::jsonb,
      new.run_config_id,
      coalesce(new.queued_at, now()),
      new.started_at,
      new.finished_at,
      new.duration_sec,
      new.solver_exit_code,
      new.error_message,
      new.placements_count,
      new.unplaced_count,
      new.sheet_count
    ) returning * into v_row;

    new.id := v_row.id;
    new.triggered_by := v_row.requested_by;
    new.status := v_row.status::text;
    new.queued_at := v_row.queued_at;
    new.started_at := v_row.started_at;
    new.finished_at := v_row.finished_at;
    new.duration_sec := v_row.duration_sec;
    new.solver_exit_code := v_row.solver_exit_code;
    new.error_message := v_row.error_message;
    new.placements_count := v_row.placements_count;
    new.unplaced_count := v_row.unplaced_count;
    new.sheet_count := v_row.sheet_count;
    return new;
  end if;

  if tg_op = 'UPDATE' then
    update app.nesting_runs
       set run_config_id = coalesce(new.run_config_id, app.nesting_runs.run_config_id),
           status = coalesce(new.status, app.nesting_runs.status::text)::app.run_request_status,
           queued_at = coalesce(new.queued_at, app.nesting_runs.queued_at),
           started_at = coalesce(new.started_at, app.nesting_runs.started_at),
           finished_at = coalesce(new.finished_at, app.nesting_runs.finished_at),
           duration_sec = coalesce(new.duration_sec, app.nesting_runs.duration_sec),
           solver_exit_code = coalesce(new.solver_exit_code, app.nesting_runs.solver_exit_code),
           error_message = coalesce(new.error_message, app.nesting_runs.error_message),
           placements_count = coalesce(new.placements_count, app.nesting_runs.placements_count),
           unplaced_count = coalesce(new.unplaced_count, app.nesting_runs.unplaced_count),
           sheet_count = coalesce(new.sheet_count, app.nesting_runs.sheet_count),
           updated_at = now()
     where id = old.id
     returning * into v_row;

    if v_row.id is null then
      raise exception 'run_not_found' using errcode = 'P0001';
    end if;

    new.id := v_row.id;
    new.project_id := v_row.project_id;
    new.triggered_by := v_row.requested_by;
    new.status := v_row.status::text;
    new.queued_at := v_row.queued_at;
    new.started_at := v_row.started_at;
    new.finished_at := v_row.finished_at;
    new.duration_sec := v_row.duration_sec;
    new.solver_exit_code := v_row.solver_exit_code;
    new.error_message := v_row.error_message;
    new.placements_count := v_row.placements_count;
    new.unplaced_count := v_row.unplaced_count;
    new.sheet_count := v_row.sheet_count;
    return new;
  end if;

  if tg_op = 'DELETE' then
    delete from app.nesting_runs where id = old.id;
    return old;
  end if;

  return null;
end;
$$;

create or replace function public.run_queue_view_iud()
returns trigger
language plpgsql
security definer
set search_path = app
as $$
declare
  v_snapshot_id uuid;
  v_created_by uuid;
begin
  if tg_op = 'INSERT' then
    if not app.can_access_run(new.run_id) then
      raise exception 'run_forbidden' using errcode = '42501';
    end if;

    select id
      into v_snapshot_id
      from app.nesting_run_snapshots
     where run_id = new.run_id
     order by created_at desc
     limit 1;

    if v_snapshot_id is null then
      select requested_by
        into v_created_by
        from app.nesting_runs
       where id = new.run_id;

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
      ) values (
        new.run_id,
        'building',
        'bridge_stub_v1',
        '{}'::jsonb,
        '{}'::jsonb,
        '[]'::jsonb,
        '[]'::jsonb,
        '[]'::jsonb,
        '{}'::jsonb,
        '{}'::jsonb,
        v_created_by
      )
      returning id into v_snapshot_id;
    end if;

    insert into app.run_queue (
      run_id,
      snapshot_id,
      queue_state,
      attempt_no,
      priority,
      available_at,
      retry_count
    ) values (
      new.run_id,
      v_snapshot_id,
      'pending',
      coalesce(new.attempts, 0),
      coalesce(new.priority, 100),
      coalesce(new.visible_after, now()),
      0
    )
    on conflict (run_id) do update
      set snapshot_id = excluded.snapshot_id,
          queue_state = 'pending',
          attempt_no = excluded.attempt_no,
          priority = excluded.priority,
          available_at = excluded.available_at,
          updated_at = now();

    return new;
  end if;

  if tg_op = 'DELETE' then
    if not app.can_access_run(old.run_id) then
      raise exception 'run_forbidden' using errcode = '42501';
    end if;
    delete from app.run_queue where run_id = old.run_id;
    return old;
  end if;

  if tg_op = 'UPDATE' then
    update app.run_queue
       set attempt_no = coalesce(new.attempts, app.run_queue.attempt_no),
           priority = coalesce(new.priority, app.run_queue.priority),
           available_at = coalesce(new.visible_after, app.run_queue.available_at),
           leased_by = new.locked_by,
           leased_at = new.locked_at,
           updated_at = now()
     where run_id = old.run_id;
    return new;
  end if;

  return null;
end;
$$;

create or replace function public.run_artifacts_view_iud()
returns trigger
language plpgsql
security definer
set search_path = app
as $$
declare
  v_row app.run_artifacts%rowtype;
  v_metadata jsonb;
begin
  if tg_op = 'INSERT' then
    if not app.can_access_run(new.run_id) then
      raise exception 'run_forbidden' using errcode = '42501';
    end if;

    v_metadata := jsonb_strip_nulls(
      jsonb_build_object(
        'legacy_artifact_type', new.artifact_type,
        'filename', new.filename,
        'size_bytes', new.size_bytes,
        'sheet_index', new.sheet_index
      )
    );

    insert into app.run_artifacts (
      run_id,
      artifact_kind,
      storage_bucket,
      storage_path,
      metadata_jsonb
    ) values (
      new.run_id,
      app.legacy_artifact_type_to_kind(new.artifact_type),
      'run-artifacts',
      new.storage_key,
      coalesce(v_metadata, '{}'::jsonb)
    )
    returning * into v_row;

    new.id := v_row.id;
    new.created_at := v_row.created_at;
    return new;
  end if;

  if tg_op = 'DELETE' then
    delete from app.run_artifacts where id = old.id;
    return old;
  end if;

  if tg_op = 'UPDATE' then
    update app.run_artifacts
       set artifact_kind = app.legacy_artifact_type_to_kind(coalesce(new.artifact_type, app.artifact_kind_to_legacy_type(app.run_artifacts.artifact_kind, app.run_artifacts.metadata_jsonb))),
           storage_path = coalesce(new.storage_key, app.run_artifacts.storage_path),
           metadata_jsonb = jsonb_strip_nulls(
             coalesce(app.run_artifacts.metadata_jsonb, '{}'::jsonb)
             || jsonb_build_object(
               'legacy_artifact_type', coalesce(new.artifact_type, app.run_artifacts.metadata_jsonb->>'legacy_artifact_type'),
               'filename', coalesce(new.filename, app.run_artifacts.metadata_jsonb->>'filename'),
               'size_bytes', coalesce(new.size_bytes, nullif(app.run_artifacts.metadata_jsonb->>'size_bytes', '')::bigint),
               'sheet_index', coalesce(new.sheet_index, nullif(app.run_artifacts.metadata_jsonb->>'sheet_index', '')::integer)
             )
           )
     where id = old.id
     returning * into v_row;

    if v_row.id is null then
      raise exception 'run_artifact_not_found' using errcode = 'P0001';
    end if;

    new.id := v_row.id;
    new.run_id := v_row.run_id;
    new.created_at := v_row.created_at;
    return new;
  end if;

  return null;
end;
$$;

-- Attach triggers only when the bridge object is a view (not an existing legacy table).
do $$
begin
  if exists (
    select 1
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = 'run_configs' and c.relkind = 'v'
  ) then
    execute 'drop trigger if exists trg_run_configs_view_iud on public.run_configs';
    execute 'create trigger trg_run_configs_view_iud instead of insert or update or delete on public.run_configs for each row execute function public.run_configs_view_iud()';
  end if;

  if exists (
    select 1
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = 'runs' and c.relkind = 'v'
  ) then
    execute 'drop trigger if exists trg_runs_view_iud on public.runs';
    execute 'create trigger trg_runs_view_iud instead of insert or update or delete on public.runs for each row execute function public.runs_view_iud()';
  end if;

  if exists (
    select 1
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = 'run_queue' and c.relkind = 'v'
  ) then
    execute 'drop trigger if exists trg_run_queue_view_iud on public.run_queue';
    execute 'create trigger trg_run_queue_view_iud instead of insert or update or delete on public.run_queue for each row execute function public.run_queue_view_iud()';
  end if;

  if exists (
    select 1
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = 'run_artifacts' and c.relkind = 'v'
  ) then
    execute 'drop trigger if exists trg_run_artifacts_view_iud on public.run_artifacts';
    execute 'create trigger trg_run_artifacts_view_iud instead of insert or update or delete on public.run_artifacts for each row execute function public.run_artifacts_view_iud()';
  end if;
end;
$$;

do $$
begin
  if exists (
    select 1
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = 'projects' and c.relkind = 'v'
  ) then
    execute 'grant select on public.projects to authenticated, service_role';
  end if;

  if exists (
    select 1
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = 'project_files' and c.relkind = 'v'
  ) then
    execute 'grant select on public.project_files to authenticated, service_role';
  end if;

  if exists (
    select 1
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = 'run_configs' and c.relkind = 'v'
  ) then
    execute 'grant select, insert, update, delete on public.run_configs to authenticated, service_role';
  end if;

  if exists (
    select 1
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = 'runs' and c.relkind = 'v'
  ) then
    execute 'grant select, insert, update, delete on public.runs to authenticated, service_role';
  end if;

  if exists (
    select 1
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = 'run_queue' and c.relkind = 'v'
  ) then
    execute 'grant select, insert, update, delete on public.run_queue to authenticated, service_role';
  end if;

  if exists (
    select 1
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = 'run_artifacts' and c.relkind = 'v'
  ) then
    execute 'grant select, insert, update, delete on public.run_artifacts to authenticated, service_role';
  end if;
end;
$$;

grant execute on function public.run_configs_view_iud() to authenticated, service_role;
grant execute on function public.runs_view_iud() to authenticated, service_role;
grant execute on function public.run_queue_view_iud() to authenticated, service_role;
grant execute on function public.run_artifacts_view_iud() to authenticated, service_role;
grant execute on function app.legacy_artifact_type_to_kind(text) to authenticated, service_role;
grant execute on function app.artifact_kind_to_legacy_type(app.artifact_kind, jsonb) to authenticated, service_role;
