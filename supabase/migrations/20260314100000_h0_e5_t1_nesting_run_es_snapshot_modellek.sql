-- H0-E5-T1 run request + snapshot base migration
-- Scope intentionally limited to request/snapshot storage foundations.

create table if not exists app.nesting_runs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references app.projects(id) on delete cascade,
  requested_by uuid references app.profiles(id) on delete set null,
  status app.run_request_status not null default 'draft',
  run_purpose text not null default 'nesting',
  idempotency_key text,
  request_payload_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (length(btrim(run_purpose)) > 0),
  check (idempotency_key is null or length(btrim(idempotency_key)) > 0)
);

create unique index if not exists uq_nesting_runs_project_idempotency_key
  on app.nesting_runs(project_id, idempotency_key)
  where idempotency_key is not null;

create index if not exists idx_nesting_runs_project_id_created_at_desc
  on app.nesting_runs(project_id, created_at desc);

create index if not exists idx_nesting_runs_status
  on app.nesting_runs(status);

drop trigger if exists trg_nesting_runs_set_updated_at on app.nesting_runs;
create trigger trg_nesting_runs_set_updated_at
before update on app.nesting_runs
for each row execute function app.set_updated_at();

create table if not exists app.nesting_run_snapshots (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null unique references app.nesting_runs(id) on delete cascade,
  status app.run_snapshot_status not null default 'building',
  snapshot_version text not null,
  snapshot_hash_sha256 text,
  project_manifest_jsonb jsonb not null default '{}'::jsonb,
  technology_manifest_jsonb jsonb not null default '{}'::jsonb,
  parts_manifest_jsonb jsonb not null default '[]'::jsonb,
  sheets_manifest_jsonb jsonb not null default '[]'::jsonb,
  geometry_manifest_jsonb jsonb not null default '[]'::jsonb,
  solver_config_jsonb jsonb not null default '{}'::jsonb,
  manufacturing_manifest_jsonb jsonb not null default '{}'::jsonb,
  created_by uuid references app.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  check (length(btrim(snapshot_version)) > 0)
);

create unique index if not exists uq_nesting_run_snapshots_snapshot_hash_sha256
  on app.nesting_run_snapshots(snapshot_hash_sha256)
  where snapshot_hash_sha256 is not null;

create index if not exists idx_nesting_run_snapshots_status
  on app.nesting_run_snapshots(status);

-- NOTE:
-- This migration intentionally does not create queue/attempt/log tables,
-- or result/artifact/projection tables.
-- RLS policies remain intentionally out of scope.
