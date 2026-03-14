-- H0-E5-T3 artifact + projection base migration
-- Scope intentionally limited to artifact storage pointers, layout projection, and run-level metrics.

create table if not exists app.run_artifacts (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  snapshot_id uuid references app.nesting_run_snapshots(id) on delete set null,
  artifact_kind app.artifact_kind not null,
  storage_bucket text not null,
  storage_path text not null,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (length(btrim(storage_bucket)) > 0),
  check (length(btrim(storage_path)) > 0)
);

create index if not exists idx_run_artifacts_run
  on app.run_artifacts(run_id);

create table if not exists app.run_layout_sheets (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  sheet_index integer not null,
  sheet_revision_id uuid references app.sheet_revisions(id) on delete set null,
  width_mm numeric(12,3),
  height_mm numeric(12,3),
  utilization_ratio numeric(8,5),
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (sheet_index >= 0),
  unique (run_id, sheet_index)
);

create index if not exists idx_run_layout_sheets_run
  on app.run_layout_sheets(run_id);

create table if not exists app.run_layout_placements (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  sheet_id uuid not null references app.run_layout_sheets(id) on delete cascade,
  placement_index integer not null,
  part_revision_id uuid references app.part_revisions(id) on delete set null,
  quantity integer not null default 1,
  transform_jsonb jsonb not null,
  bbox_jsonb jsonb not null default '{}'::jsonb,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (placement_index >= 0),
  check (quantity > 0),
  unique (sheet_id, placement_index)
);

create index if not exists idx_run_layout_placements_sheet_id_placement_index
  on app.run_layout_placements(sheet_id, placement_index);

create index if not exists idx_run_layout_placements_run
  on app.run_layout_placements(run_id);

create table if not exists app.run_layout_unplaced (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  part_revision_id uuid references app.part_revisions(id) on delete set null,
  remaining_qty integer not null,
  reason text,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (remaining_qty > 0)
);

create index if not exists idx_run_layout_unplaced_run
  on app.run_layout_unplaced(run_id);

create table if not exists app.run_metrics (
  run_id uuid primary key references app.nesting_runs(id) on delete cascade,
  placed_count integer not null default 0,
  unplaced_count integer not null default 0,
  used_sheet_count integer not null default 0,
  utilization_ratio numeric(8,5),
  remnant_value numeric(14,2),
  metrics_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (placed_count >= 0),
  check (unplaced_count >= 0),
  check (used_sheet_count >= 0)
);

-- NOTE:
-- This migration intentionally does not create a dedicated app.run_results table.
-- Storage bucket policy and RLS policies remain intentionally out of scope.
