-- H0-E3-T1 file domain base migration: file_objects table
-- Scope intentionally limited to file metadata + storage-reference ownership.

create table if not exists app.file_objects (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references app.projects(id) on delete cascade,
  storage_bucket text not null,
  storage_path text not null,
  file_name text not null,
  mime_type text,
  file_kind app.file_kind not null,
  byte_size bigint,
  sha256 text,
  uploaded_by uuid references app.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  unique (storage_bucket, storage_path),
  check (length(btrim(storage_bucket)) > 0),
  check (length(btrim(storage_path)) > 0),
  check (length(btrim(file_name)) > 0),
  check (byte_size is null or byte_size >= 0)
);

create index if not exists idx_file_objects_project_id
  on app.file_objects(project_id);

create index if not exists idx_file_objects_uploaded_by
  on app.file_objects(uploaded_by);

-- NOTE:
-- This migration intentionally does not create geometry_revisions,
-- geometry_validation_reports, geometry_review_actions, geometry_derivatives,
-- run, or export domain tables.
-- RLS policies remain intentionally out of scope.
