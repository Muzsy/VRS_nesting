-- H3-E1-T3: project-level strategy es scoring selection truth
-- Scope: project_run_strategy_selection + project_scoring_selection tablak.
-- Nem-scope: strategy/scoring profile CRUD, run_batches, run_evaluations,
--            ranking, snapshot builder/run create integracio.

-- ============================================================
-- 1. project_run_strategy_selection (projekt-szintu strategy binding)
-- ============================================================

create table if not exists app.project_run_strategy_selection (
  project_id uuid primary key references app.projects(id) on delete cascade,
  active_run_strategy_profile_version_id uuid not null references app.run_strategy_profile_versions(id) on delete restrict,
  selected_at timestamptz not null default now(),
  selected_by uuid not null references app.profiles(id) on delete restrict
);

create index if not exists idx_project_run_strategy_selection_active_version
  on app.project_run_strategy_selection(active_run_strategy_profile_version_id);

-- ============================================================
-- 2. project_scoring_selection (projekt-szintu scoring binding)
-- ============================================================

create table if not exists app.project_scoring_selection (
  project_id uuid primary key references app.projects(id) on delete cascade,
  active_scoring_profile_version_id uuid not null references app.scoring_profile_versions(id) on delete restrict,
  selected_at timestamptz not null default now(),
  selected_by uuid not null references app.profiles(id) on delete restrict
);

create index if not exists idx_project_scoring_selection_active_version
  on app.project_scoring_selection(active_scoring_profile_version_id);

-- ============================================================
-- 3. RLS policyk
-- ============================================================

alter table app.project_run_strategy_selection enable row level security;
alter table app.project_scoring_selection enable row level security;

-- project_run_strategy_selection RLS

drop policy if exists h3_e1_t3_project_run_strategy_selection_select_owner on app.project_run_strategy_selection;
create policy h3_e1_t3_project_run_strategy_selection_select_owner
on app.project_run_strategy_selection
for select
to authenticated
using (app.is_project_owner(project_id));

drop policy if exists h3_e1_t3_project_run_strategy_selection_insert_owner on app.project_run_strategy_selection;
create policy h3_e1_t3_project_run_strategy_selection_insert_owner
on app.project_run_strategy_selection
for insert
to authenticated
with check (
  app.is_project_owner(project_id)
  and selected_by = app.current_user_id()
);

drop policy if exists h3_e1_t3_project_run_strategy_selection_update_owner on app.project_run_strategy_selection;
create policy h3_e1_t3_project_run_strategy_selection_update_owner
on app.project_run_strategy_selection
for update
to authenticated
using (app.is_project_owner(project_id))
with check (
  app.is_project_owner(project_id)
  and selected_by = app.current_user_id()
);

drop policy if exists h3_e1_t3_project_run_strategy_selection_delete_owner on app.project_run_strategy_selection;
create policy h3_e1_t3_project_run_strategy_selection_delete_owner
on app.project_run_strategy_selection
for delete
to authenticated
using (app.is_project_owner(project_id));

-- project_scoring_selection RLS

drop policy if exists h3_e1_t3_project_scoring_selection_select_owner on app.project_scoring_selection;
create policy h3_e1_t3_project_scoring_selection_select_owner
on app.project_scoring_selection
for select
to authenticated
using (app.is_project_owner(project_id));

drop policy if exists h3_e1_t3_project_scoring_selection_insert_owner on app.project_scoring_selection;
create policy h3_e1_t3_project_scoring_selection_insert_owner
on app.project_scoring_selection
for insert
to authenticated
with check (
  app.is_project_owner(project_id)
  and selected_by = app.current_user_id()
);

drop policy if exists h3_e1_t3_project_scoring_selection_update_owner on app.project_scoring_selection;
create policy h3_e1_t3_project_scoring_selection_update_owner
on app.project_scoring_selection
for update
to authenticated
using (app.is_project_owner(project_id))
with check (
  app.is_project_owner(project_id)
  and selected_by = app.current_user_id()
);

drop policy if exists h3_e1_t3_project_scoring_selection_delete_owner on app.project_scoring_selection;
create policy h3_e1_t3_project_scoring_selection_delete_owner
on app.project_scoring_selection
for delete
to authenticated
using (app.is_project_owner(project_id));
