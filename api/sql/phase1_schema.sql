-- Phase 1 schema bootstrap for VRS web platform (Supabase/PostgreSQL)

create extension if not exists pgcrypto;

create table if not exists users (
  id uuid primary key,
  email text unique not null,
  display_name text,
  tier text not null default 'free',
  quota_runs_per_month integer not null default 50,
  created_at timestamptz not null default now()
);

create table if not exists projects (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references users(id),
  name text not null,
  description text,
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  archived_at timestamptz
);
create index if not exists idx_projects_owner_id on projects(owner_id);
create index if not exists idx_projects_owner_archived on projects(owner_id, archived_at);

create table if not exists project_files (
  id uuid primary key,
  project_id uuid not null references projects(id) on delete cascade,
  uploaded_by uuid not null references users(id),
  file_type text not null,
  original_filename text not null,
  storage_key text not null unique,
  size_bytes bigint,
  content_hash_sha256 text,
  validation_status text not null default 'pending',
  validation_error text,
  uploaded_at timestamptz not null default now()
);
create index if not exists idx_project_files_project_id on project_files(project_id);
create index if not exists idx_project_files_storage_key on project_files(storage_key);

create table if not exists run_configs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  created_by uuid not null references users(id),
  name text,
  schema_version text not null default 'dxf_v1',
  seed integer not null default 0,
  time_limit_s integer not null default 60,
  spacing_mm double precision not null default 2.0,
  margin_mm double precision not null default 5.0,
  stock_file_id uuid references project_files(id),
  parts_config jsonb not null,
  created_at timestamptz not null default now()
);
create index if not exists idx_run_configs_project_id on run_configs(project_id);

create table if not exists runs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  run_config_id uuid references run_configs(id),
  triggered_by uuid not null references users(id),
  status text not null default 'queued',
  run_dir_key text,
  worker_run_id text,
  queued_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz,
  duration_sec double precision,
  placements_count integer,
  unplaced_count integer,
  sheet_count integer,
  solver_exit_code integer,
  error_message text,
  input_snapshot_hash text
);
create index if not exists idx_runs_project_status on runs(project_id, status);
create index if not exists idx_runs_project_queued on runs(project_id, queued_at desc);

create table if not exists run_artifacts (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references runs(id) on delete cascade,
  artifact_type text not null,
  filename text not null,
  storage_key text not null,
  size_bytes bigint,
  sheet_index integer,
  content_hash_sha256 text,
  created_at timestamptz not null default now()
);
create index if not exists idx_run_artifacts_run_id on run_artifacts(run_id);
create index if not exists idx_run_artifacts_run_type on run_artifacts(run_id, artifact_type);

create table if not exists run_queue (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references runs(id) on delete cascade,
  priority integer not null default 0,
  attempts integer not null default 0,
  max_attempts integer not null default 3,
  locked_by text,
  locked_at timestamptz,
  visible_after timestamptz not null default now(),
  created_at timestamptz not null default now()
);
create index if not exists idx_run_queue_visible_after on run_queue(visible_after);
create index if not exists idx_run_queue_locked_by on run_queue(locked_by);
