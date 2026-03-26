-- H3-E3-T1: run evaluation engine truth layer.
-- Scope: app.run_evaluations + owner-scoped RLS.
-- Non-scope: run_ranking_results, batch comparison, decision/review workflow.

create table if not exists app.run_evaluations (
  run_id uuid primary key references app.nesting_runs(id) on delete cascade,
  scoring_profile_version_id uuid references app.scoring_profile_versions(id) on delete set null,
  total_score numeric(18,6),
  evaluation_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (total_score is null or (total_score >= -1 and total_score <= 1))
);

create index if not exists idx_run_evaluations_scoring_profile_version_id
  on app.run_evaluations(scoring_profile_version_id);

create index if not exists idx_run_evaluations_created_at_desc
  on app.run_evaluations(created_at desc, run_id);

alter table app.run_evaluations enable row level security;

drop policy if exists h3_e3_t1_run_evaluations_select_owner on app.run_evaluations;
create policy h3_e3_t1_run_evaluations_select_owner
on app.run_evaluations
for select to authenticated
using (
  exists (
    select 1
    from app.nesting_runs nr
    where nr.id = run_evaluations.run_id
      and nr.owner_user_id = app.current_user_id()
  )
);

drop policy if exists h3_e3_t1_run_evaluations_insert_owner on app.run_evaluations;
create policy h3_e3_t1_run_evaluations_insert_owner
on app.run_evaluations
for insert to authenticated
with check (
  exists (
    select 1
    from app.nesting_runs nr
    where nr.id = run_evaluations.run_id
      and nr.owner_user_id = app.current_user_id()
  )
  and (
    run_evaluations.scoring_profile_version_id is null
    or exists (
      select 1
      from app.scoring_profile_versions spv
      where spv.id = run_evaluations.scoring_profile_version_id
        and spv.owner_user_id = app.current_user_id()
    )
  )
);

drop policy if exists h3_e3_t1_run_evaluations_update_owner on app.run_evaluations;
create policy h3_e3_t1_run_evaluations_update_owner
on app.run_evaluations
for update to authenticated
using (
  exists (
    select 1
    from app.nesting_runs nr
    where nr.id = run_evaluations.run_id
      and nr.owner_user_id = app.current_user_id()
  )
)
with check (
  exists (
    select 1
    from app.nesting_runs nr
    where nr.id = run_evaluations.run_id
      and nr.owner_user_id = app.current_user_id()
  )
  and (
    run_evaluations.scoring_profile_version_id is null
    or exists (
      select 1
      from app.scoring_profile_versions spv
      where spv.id = run_evaluations.scoring_profile_version_id
        and spv.owner_user_id = app.current_user_id()
    )
  )
);

drop policy if exists h3_e3_t1_run_evaluations_delete_owner on app.run_evaluations;
create policy h3_e3_t1_run_evaluations_delete_owner
on app.run_evaluations
for delete to authenticated
using (
  exists (
    select 1
    from app.nesting_runs nr
    where nr.id = run_evaluations.run_id
      and nr.owner_user_id = app.current_user_id()
  )
);
