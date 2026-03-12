-- H0-E2-T4 part domain base migration: definitions + revisions + project demands
-- Scope intentionally limited to definition/revision/demand split.

create table if not exists app.part_definitions (
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

create table if not exists app.part_revisions (
  id uuid primary key default gen_random_uuid(),
  part_definition_id uuid not null references app.part_definitions(id) on delete cascade,
  revision_no integer not null,
  lifecycle app.revision_lifecycle not null default 'draft',
  source_label text,
  source_checksum_sha256 text,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (part_definition_id, revision_no),
  check (revision_no > 0)
);

alter table app.part_definitions
  drop constraint if exists fk_part_definitions_current_revision;

alter table app.part_definitions
  add constraint fk_part_definitions_current_revision
  foreign key (current_revision_id) references app.part_revisions(id)
  on delete set null
  deferrable initially deferred;

create table if not exists app.project_part_requirements (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references app.projects(id) on delete cascade,
  part_revision_id uuid not null references app.part_revisions(id) on delete restrict,
  required_qty integer not null,
  placement_priority smallint not null default 50,
  placement_policy app.placement_policy not null default 'normal',
  is_active boolean not null default true,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (project_id, part_revision_id),
  check (required_qty > 0),
  check (placement_priority between 0 and 100)
);

create index if not exists idx_part_revisions_part_definition_id
  on app.part_revisions(part_definition_id);

create index if not exists idx_part_revisions_lifecycle
  on app.part_revisions(lifecycle);

create index if not exists idx_project_part_requirements_project
  on app.project_part_requirements(project_id);

create index if not exists idx_project_part_requirements_priority
  on app.project_part_requirements(project_id, placement_priority, placement_policy);

create index if not exists idx_project_part_requirements_part_revision
  on app.project_part_requirements(part_revision_id);

drop trigger if exists trg_part_definitions_set_updated_at on app.part_definitions;
create trigger trg_part_definitions_set_updated_at
before update on app.part_definitions
for each row execute function app.set_updated_at();

drop trigger if exists trg_part_revisions_set_updated_at on app.part_revisions;
create trigger trg_part_revisions_set_updated_at
before update on app.part_revisions
for each row execute function app.set_updated_at();

drop trigger if exists trg_project_part_requirements_set_updated_at on app.project_part_requirements;
create trigger trg_project_part_requirements_set_updated_at
before update on app.project_part_requirements
for each row execute function app.set_updated_at();

-- NOTE:
-- This migration intentionally does not create geometry/file/sheet/run/remnant/export tables.
-- RLS policies remain intentionally out of scope.
