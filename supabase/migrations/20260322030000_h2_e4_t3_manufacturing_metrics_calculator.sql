-- H2-E4-T3: manufacturing metrics calculator — persisted metrics truth table.
-- Scope: run_manufacturing_metrics as a separate truth layer from H1 run_metrics.
-- Source: persisted manufacturing plan truth (run_manufacturing_contours +
--   geometry_contour_classes + cut_contour_rules).
-- Does NOT modify earlier truth tables.
-- Does NOT introduce preview/export/postprocessor tables.

-- 1) run_manufacturing_metrics ------------------------------------------------

create table if not exists app.run_manufacturing_metrics (
  run_id uuid primary key references app.nesting_runs(id) on delete cascade,
  pierce_count integer not null default 0,
  outer_contour_count integer not null default 0,
  inner_contour_count integer not null default 0,
  estimated_cut_length_mm numeric(18,4) not null default 0,
  estimated_rapid_length_mm numeric(18,4) not null default 0,
  estimated_process_time_s numeric(18,4) not null default 0,
  metrics_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (pierce_count >= 0),
  check (outer_contour_count >= 0),
  check (inner_contour_count >= 0),
  check (estimated_cut_length_mm >= 0),
  check (estimated_rapid_length_mm >= 0),
  check (estimated_process_time_s >= 0)
);

-- 2) RLS: owner-scoped via nesting_runs.owner_user_id ----------------------

alter table app.run_manufacturing_metrics enable row level security;

drop policy if exists h2_e4_t3_run_manufacturing_metrics_select_owner
  on app.run_manufacturing_metrics;
create policy h2_e4_t3_run_manufacturing_metrics_select_owner
on app.run_manufacturing_metrics
for select to authenticated
using (
  exists (
    select 1 from app.nesting_runs nr
    where nr.id = run_manufacturing_metrics.run_id
      and nr.owner_user_id = app.current_user_id()
  )
);

drop policy if exists h2_e4_t3_run_manufacturing_metrics_insert_owner
  on app.run_manufacturing_metrics;
create policy h2_e4_t3_run_manufacturing_metrics_insert_owner
on app.run_manufacturing_metrics
for insert to authenticated
with check (
  exists (
    select 1 from app.nesting_runs nr
    where nr.id = run_manufacturing_metrics.run_id
      and nr.owner_user_id = app.current_user_id()
  )
);

drop policy if exists h2_e4_t3_run_manufacturing_metrics_delete_owner
  on app.run_manufacturing_metrics;
create policy h2_e4_t3_run_manufacturing_metrics_delete_owner
on app.run_manufacturing_metrics
for delete to authenticated
using (
  exists (
    select 1 from app.nesting_runs nr
    where nr.id = run_manufacturing_metrics.run_id
      and nr.owner_user_id = app.current_user_id()
  )
);

-- NOTE:
-- This migration intentionally keeps run_manufacturing_metrics separate
-- from the H1 app.run_metrics table.
-- No preview/export/postprocessor tables are introduced.
-- No earlier truth tables are modified.
