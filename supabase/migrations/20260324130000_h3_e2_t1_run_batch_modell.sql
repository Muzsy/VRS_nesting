-- H3-E2-T1: run batch model truth layer
-- Scope: app.run_batches + app.run_batch_items + owner/project scoped RLS.
-- Non-scope: orchestrator, run creation, evaluation, ranking, comparison projection.

-- ============================================================
-- 1. run_batches (project-level grouping truth)
-- ============================================================

create table if not exists app.run_batches (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references app.projects(id) on delete cascade,
  created_by uuid references app.profiles(id) on delete set null,
  batch_kind text not null default 'comparison',
  notes text,
  created_at timestamptz not null default now(),
  check (length(btrim(batch_kind)) > 0)
);

create index if not exists idx_run_batches_project_created_at_desc
  on app.run_batches(project_id, created_at desc, id desc);

create index if not exists idx_run_batches_created_by
  on app.run_batches(created_by);

-- ============================================================
-- 2. run_batch_items (existing run -> batch binding truth)
-- ============================================================

create table if not exists app.run_batch_items (
  batch_id uuid not null references app.run_batches(id) on delete cascade,
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  candidate_label text,
  strategy_profile_version_id uuid references app.run_strategy_profile_versions(id) on delete set null,
  scoring_profile_version_id uuid references app.scoring_profile_versions(id) on delete set null,
  created_at timestamptz not null default now(),
  primary key (batch_id, run_id),
  check (candidate_label is null or length(btrim(candidate_label)) > 0)
);

create index if not exists idx_run_batch_items_run_id
  on app.run_batch_items(run_id);

create index if not exists idx_run_batch_items_strategy_profile_version_id
  on app.run_batch_items(strategy_profile_version_id);

create index if not exists idx_run_batch_items_scoring_profile_version_id
  on app.run_batch_items(scoring_profile_version_id);

-- ============================================================
-- 3. RLS policies
-- ============================================================

alter table app.run_batches enable row level security;
alter table app.run_batch_items enable row level security;

-- run_batches RLS ------------------------------------------------------------

drop policy if exists h3_e2_t1_run_batches_select_owner on app.run_batches;
create policy h3_e2_t1_run_batches_select_owner
on app.run_batches
for select
to authenticated
using (app.is_project_owner(project_id));

drop policy if exists h3_e2_t1_run_batches_insert_owner on app.run_batches;
create policy h3_e2_t1_run_batches_insert_owner
on app.run_batches
for insert
to authenticated
with check (
  app.is_project_owner(project_id)
  and (created_by is null or created_by = app.current_user_id())
);

drop policy if exists h3_e2_t1_run_batches_update_owner on app.run_batches;
create policy h3_e2_t1_run_batches_update_owner
on app.run_batches
for update
to authenticated
using (app.is_project_owner(project_id))
with check (
  app.is_project_owner(project_id)
  and (created_by is null or created_by = app.current_user_id())
);

drop policy if exists h3_e2_t1_run_batches_delete_owner on app.run_batches;
create policy h3_e2_t1_run_batches_delete_owner
on app.run_batches
for delete
to authenticated
using (app.is_project_owner(project_id));

-- run_batch_items RLS --------------------------------------------------------

drop policy if exists h3_e2_t1_run_batch_items_select_owner on app.run_batch_items;
create policy h3_e2_t1_run_batch_items_select_owner
on app.run_batch_items
for select
to authenticated
using (
  exists (
    select 1
    from app.run_batches rb
    where rb.id = run_batch_items.batch_id
      and app.is_project_owner(rb.project_id)
  )
);

drop policy if exists h3_e2_t1_run_batch_items_insert_owner on app.run_batch_items;
create policy h3_e2_t1_run_batch_items_insert_owner
on app.run_batch_items
for insert
to authenticated
with check (
  exists (
    select 1
    from app.run_batches rb
    join app.nesting_runs nr on nr.id = run_batch_items.run_id
    where rb.id = run_batch_items.batch_id
      and nr.project_id = rb.project_id
      and app.is_project_owner(rb.project_id)
  )
  and (
    run_batch_items.strategy_profile_version_id is null
    or exists (
      select 1
      from app.run_strategy_profile_versions rspv
      where rspv.id = run_batch_items.strategy_profile_version_id
        and rspv.owner_user_id = app.current_user_id()
    )
  )
  and (
    run_batch_items.scoring_profile_version_id is null
    or exists (
      select 1
      from app.scoring_profile_versions spv
      where spv.id = run_batch_items.scoring_profile_version_id
        and spv.owner_user_id = app.current_user_id()
    )
  )
);

drop policy if exists h3_e2_t1_run_batch_items_delete_owner on app.run_batch_items;
create policy h3_e2_t1_run_batch_items_delete_owner
on app.run_batch_items
for delete
to authenticated
using (
  exists (
    select 1
    from app.run_batches rb
    where rb.id = run_batch_items.batch_id
      and app.is_project_owner(rb.project_id)
  )
);
