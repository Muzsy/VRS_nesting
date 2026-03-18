-- H0-E2-T5 sheet domain base migration: definitions + revisions + project sheet inputs
-- Scope intentionally limited to definition/revision/project-input split.

create table if not exists app.sheet_definitions (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references app.profiles(id) on delete restrict,
  code text not null,
  name text not null,
  description text,
  current_revision_id uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (owner_user_id, code),
  check (length(btrim(code)) > 0),
  check (length(btrim(name)) > 0)
);

create table if not exists app.sheet_revisions (
  id uuid primary key default gen_random_uuid(),
  sheet_definition_id uuid not null references app.sheet_definitions(id) on delete cascade,
  revision_no integer not null,
  lifecycle app.revision_lifecycle not null default 'draft',
  width_mm numeric(12,3) not null,
  height_mm numeric(12,3) not null,
  grain_direction text,
  source_label text,
  source_checksum_sha256 text,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (sheet_definition_id, revision_no),
  check (revision_no > 0),
  check (width_mm > 0),
  check (height_mm > 0)
);

alter table app.sheet_revisions
  drop constraint if exists uq_sheet_revisions_id_definition;

alter table app.sheet_revisions
  add constraint uq_sheet_revisions_id_definition
  unique (id, sheet_definition_id);

alter table app.sheet_definitions
  drop constraint if exists fk_sheet_definitions_current_revision;

alter table app.sheet_definitions
  add constraint fk_sheet_definitions_current_revision
  foreign key (current_revision_id, id)
  references app.sheet_revisions(id, sheet_definition_id)
  on delete set null (current_revision_id)
  deferrable initially deferred;

create table if not exists app.project_sheet_inputs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references app.projects(id) on delete cascade,
  sheet_revision_id uuid not null references app.sheet_revisions(id) on delete restrict,
  required_qty integer not null,
  is_active boolean not null default true,
  is_default boolean not null default false,
  placement_priority smallint not null default 50,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (project_id, sheet_revision_id),
  check (required_qty > 0),
  check (placement_priority between 0 and 100)
);

create index if not exists idx_sheet_revisions_sheet_definition_id
  on app.sheet_revisions(sheet_definition_id);

create index if not exists idx_sheet_revisions_lifecycle
  on app.sheet_revisions(lifecycle);

create index if not exists idx_project_sheet_inputs_project
  on app.project_sheet_inputs(project_id);

create index if not exists idx_project_sheet_inputs_priority
  on app.project_sheet_inputs(project_id, placement_priority, is_active);

create index if not exists idx_project_sheet_inputs_sheet_revision
  on app.project_sheet_inputs(sheet_revision_id);

drop trigger if exists trg_sheet_definitions_set_updated_at on app.sheet_definitions;
create trigger trg_sheet_definitions_set_updated_at
before update on app.sheet_definitions
for each row execute function app.set_updated_at();

drop trigger if exists trg_sheet_revisions_set_updated_at on app.sheet_revisions;
create trigger trg_sheet_revisions_set_updated_at
before update on app.sheet_revisions
for each row execute function app.set_updated_at();

drop trigger if exists trg_project_sheet_inputs_set_updated_at on app.project_sheet_inputs;
create trigger trg_project_sheet_inputs_set_updated_at
before update on app.project_sheet_inputs
for each row execute function app.set_updated_at();

-- NOTE:
-- This migration intentionally does not create remnant/inventory/file/geometry/run/export tables.
-- RLS policies remain intentionally out of scope.
