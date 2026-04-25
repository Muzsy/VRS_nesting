-- DXF Prefilter E6-T1: app.file_objects soft archive / active-list hiding.
-- Scope: deleted_at metadata + active-list partial index.
-- Non-scope: lineage hard delete (preflight/geometry/run FK-k miatt tilos ebben a taskban).

alter table app.file_objects
  add column if not exists deleted_at timestamptz null;

comment on column app.file_objects.deleted_at is
  'Soft archive timestamp for hide/archive flows. Lineage records stay intact; this is not hard delete.';

create index if not exists idx_file_objects_project_active_created_at
  on app.file_objects(project_id, created_at desc)
  where deleted_at is null;
