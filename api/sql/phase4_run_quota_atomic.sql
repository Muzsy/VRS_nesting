-- Phase 4 P4.2: atomic monthly run quota + queue insert

create table if not exists public.user_run_quota_monthly_usage (
  user_id uuid not null references public.users(id) on delete cascade,
  period_start date not null,
  used_runs integer not null default 0 check (used_runs >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (user_id, period_start)
);
create index if not exists idx_user_run_quota_monthly_usage_period
  on public.user_run_quota_monthly_usage(period_start);

alter table public.user_run_quota_monthly_usage enable row level security;

drop policy if exists user_run_quota_usage_self_select on public.user_run_quota_monthly_usage;
create policy user_run_quota_usage_self_select on public.user_run_quota_monthly_usage
  for select
  using (user_id = auth.uid());

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
set search_path = public
as $$
declare
  v_owner_id uuid;
  v_quota integer;
  v_used integer;
  v_period_start date;
  v_run public.runs%rowtype;
begin
  v_period_start := date_trunc('month', timezone('utc', now()))::date;

  select owner_id
    into v_owner_id
    from public.projects
   where projects.id = p_project_id
   for update;
  if v_owner_id is null then
    raise exception 'project_not_found' using errcode = 'P0001';
  end if;
  if v_owner_id <> p_triggered_by then
    raise exception 'project_forbidden' using errcode = '42501';
  end if;

  select quota_runs_per_month
    into v_quota
    from public.users
   where users.id = p_triggered_by
   for update;
  if v_quota is null then
    raise exception 'user_profile_not_found' using errcode = 'P0001';
  end if;

  insert into public.user_run_quota_monthly_usage (user_id, period_start, used_runs)
  values (p_triggered_by, v_period_start, 0)
  on conflict (user_id, period_start) do nothing;

  select used_runs
    into v_used
    from public.user_run_quota_monthly_usage
   where user_id = p_triggered_by
     and period_start = v_period_start
   for update;

  if v_used >= v_quota then
    raise exception 'quota_exceeded' using errcode = 'P0001';
  end if;

  update public.user_run_quota_monthly_usage
     set used_runs = used_runs + 1,
         updated_at = now()
   where user_id = p_triggered_by
     and period_start = v_period_start;

  insert into public.runs (project_id, run_config_id, triggered_by, status, queued_at)
  values (p_project_id, p_run_config_id, p_triggered_by, 'queued', now())
  returning * into v_run;

  insert into public.run_queue (run_id, priority, attempts, max_attempts)
  values (v_run.id, 0, 0, 3);

  return query
    select
      v_run.id,
      v_run.project_id,
      v_run.run_config_id,
      v_run.triggered_by,
      v_run.status,
      v_run.queued_at,
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
