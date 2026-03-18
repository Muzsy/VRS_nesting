-- Phase 4 P4.2: atomic monthly run quota + queue insert
-- DEPRECATED LEGACY NOTE:
--   This file is kept for backward compatibility, but it is aligned to app.*
--   tables/functions. Canonical rollout is via Supabase migrations.

alter table app.profiles
  add column if not exists quota_runs_per_month integer not null default 50;

alter table app.profiles
  drop constraint if exists ck_profiles_quota_runs_per_month_nonnegative;

alter table app.profiles
  add constraint ck_profiles_quota_runs_per_month_nonnegative
  check (quota_runs_per_month >= 0);

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

drop policy if exists phase4_user_run_quota_usage_self_select on app.user_run_quota_monthly_usage;
create policy phase4_user_run_quota_usage_self_select on app.user_run_quota_monthly_usage
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
