-- H0-E3-T2 geometry domain base migration: geometry_revisions table
-- Scope intentionally limited to canonical geometry revision metadata + source lineage.

create table if not exists app.geometry_revisions (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references app.projects(id) on delete cascade,
  source_file_object_id uuid not null references app.file_objects(id) on delete restrict,
  geometry_role app.geometry_role not null,
  revision_no integer not null,
  status app.geometry_validation_status not null default 'uploaded',
  canonical_format_version text not null,
  canonical_geometry_jsonb jsonb,
  canonical_hash_sha256 text,
  source_hash_sha256 text,
  bbox_jsonb jsonb,
  created_by uuid references app.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (source_file_object_id, revision_no),
  check (revision_no > 0),
  check (length(btrim(canonical_format_version)) > 0)
);

create index if not exists idx_geometry_revisions_project_id
  on app.geometry_revisions(project_id);

create index if not exists idx_geometry_revisions_source_file_object_id
  on app.geometry_revisions(source_file_object_id);

create index if not exists idx_geometry_revisions_status
  on app.geometry_revisions(status);

drop trigger if exists trg_geometry_revisions_set_updated_at on app.geometry_revisions;
create trigger trg_geometry_revisions_set_updated_at
before update on app.geometry_revisions
for each row execute function app.set_updated_at();

-- NOTE:
-- This migration intentionally does not create geometry_validation_reports,
-- geometry_review_actions, geometry_derivatives, run, or export domain tables.
-- RLS policies remain intentionally out of scope.
