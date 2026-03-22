-- H2-E4-T2: manufacturing plan builder — persisted plan truth tables.
-- Scope: run_manufacturing_plans + run_manufacturing_contours.
-- Audit FK chain: manufacturing_profile_version_id, cut_rule_set_id,
--   geometry_derivative_id, contour_class_id, matched_rule_id.
-- Does NOT introduce preview/export/postprocessor tables.
-- Does NOT modify earlier truth tables.

-- 1) run_manufacturing_plans ------------------------------------------------

create table if not exists app.run_manufacturing_plans (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  sheet_id uuid not null references app.run_layout_sheets(id) on delete cascade,
  manufacturing_profile_version_id uuid
    references app.manufacturing_profile_versions(id) on delete set null,
  cut_rule_set_id uuid
    references app.cut_rule_sets(id) on delete set null,
  status text not null default 'generated',
  summary_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (run_id, sheet_id)
);

create index if not exists idx_run_manufacturing_plans_run
  on app.run_manufacturing_plans(run_id);

create index if not exists idx_run_manufacturing_plans_sheet
  on app.run_manufacturing_plans(sheet_id);

-- 2) run_manufacturing_contours ---------------------------------------------

create table if not exists app.run_manufacturing_contours (
  id uuid primary key default gen_random_uuid(),
  manufacturing_plan_id uuid not null
    references app.run_manufacturing_plans(id) on delete cascade,
  placement_id uuid
    references app.run_layout_placements(id) on delete cascade,
  geometry_derivative_id uuid
    references app.geometry_derivatives(id) on delete set null,
  contour_class_id uuid
    references app.geometry_contour_classes(id) on delete set null,
  matched_rule_id uuid
    references app.cut_contour_rules(id) on delete set null,
  contour_index integer not null,
  contour_kind text not null,
  feature_class text not null default 'default',
  entry_point_jsonb jsonb,
  lead_in_jsonb jsonb,
  lead_out_jsonb jsonb,
  cut_order_index integer,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_run_manufacturing_contours_plan
  on app.run_manufacturing_contours(manufacturing_plan_id);

create index if not exists idx_run_manufacturing_contours_placement
  on app.run_manufacturing_contours(placement_id);

-- 3) RLS: owner-scoped via nesting_runs.owner_user_id ----------------------

alter table app.run_manufacturing_plans enable row level security;

drop policy if exists h2_e4_t2_run_manufacturing_plans_select_owner
  on app.run_manufacturing_plans;
create policy h2_e4_t2_run_manufacturing_plans_select_owner
on app.run_manufacturing_plans
for select to authenticated
using (
  exists (
    select 1 from app.nesting_runs nr
    where nr.id = run_manufacturing_plans.run_id
      and nr.owner_user_id = app.current_user_id()
  )
);

drop policy if exists h2_e4_t2_run_manufacturing_plans_insert_owner
  on app.run_manufacturing_plans;
create policy h2_e4_t2_run_manufacturing_plans_insert_owner
on app.run_manufacturing_plans
for insert to authenticated
with check (
  exists (
    select 1 from app.nesting_runs nr
    where nr.id = run_manufacturing_plans.run_id
      and nr.owner_user_id = app.current_user_id()
  )
);

drop policy if exists h2_e4_t2_run_manufacturing_plans_delete_owner
  on app.run_manufacturing_plans;
create policy h2_e4_t2_run_manufacturing_plans_delete_owner
on app.run_manufacturing_plans
for delete to authenticated
using (
  exists (
    select 1 from app.nesting_runs nr
    where nr.id = run_manufacturing_plans.run_id
      and nr.owner_user_id = app.current_user_id()
  )
);

alter table app.run_manufacturing_contours enable row level security;

drop policy if exists h2_e4_t2_run_manufacturing_contours_select_owner
  on app.run_manufacturing_contours;
create policy h2_e4_t2_run_manufacturing_contours_select_owner
on app.run_manufacturing_contours
for select to authenticated
using (
  exists (
    select 1 from app.run_manufacturing_plans rmp
      join app.nesting_runs nr on nr.id = rmp.run_id
    where rmp.id = run_manufacturing_contours.manufacturing_plan_id
      and nr.owner_user_id = app.current_user_id()
  )
);

drop policy if exists h2_e4_t2_run_manufacturing_contours_insert_owner
  on app.run_manufacturing_contours;
create policy h2_e4_t2_run_manufacturing_contours_insert_owner
on app.run_manufacturing_contours
for insert to authenticated
with check (
  exists (
    select 1 from app.run_manufacturing_plans rmp
      join app.nesting_runs nr on nr.id = rmp.run_id
    where rmp.id = run_manufacturing_contours.manufacturing_plan_id
      and nr.owner_user_id = app.current_user_id()
  )
);

drop policy if exists h2_e4_t2_run_manufacturing_contours_delete_owner
  on app.run_manufacturing_contours;
create policy h2_e4_t2_run_manufacturing_contours_delete_owner
on app.run_manufacturing_contours
for delete to authenticated
using (
  exists (
    select 1 from app.run_manufacturing_plans rmp
      join app.nesting_runs nr on nr.id = rmp.run_id
    where rmp.id = run_manufacturing_contours.manufacturing_plan_id
      and nr.owner_user_id = app.current_user_id()
  )
);
