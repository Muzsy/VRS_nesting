-- H0-E3-T4 geometry derivatives base migration
-- Scope intentionally limited to source geometry bound derivative storage.

create table if not exists app.geometry_derivatives (
  id uuid primary key default gen_random_uuid(),
  geometry_revision_id uuid not null references app.geometry_revisions(id) on delete cascade,
  derivative_kind app.geometry_derivative_kind not null,
  producer_version text not null,
  format_version text not null,
  derivative_jsonb jsonb not null,
  derivative_hash_sha256 text,
  source_geometry_hash_sha256 text,
  created_at timestamptz not null default now(),
  unique (geometry_revision_id, derivative_kind),
  check (length(btrim(producer_version)) > 0),
  check (length(btrim(format_version)) > 0)
);

create index if not exists idx_geometry_derivatives_geometry_revision_id
  on app.geometry_derivatives(geometry_revision_id);

create index if not exists idx_geometry_derivatives_kind
  on app.geometry_derivatives(derivative_kind);

-- NOTE:
-- This migration intentionally does not create part/sheet binding,
-- run, or export domain tables.
-- RLS policies remain intentionally out of scope.
