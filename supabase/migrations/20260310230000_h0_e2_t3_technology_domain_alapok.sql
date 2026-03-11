-- H0-E2-T3 technology domain base migration: presets + project setups
-- Scope intentionally limited to technology catalog and project-bound technology setup.

create table if not exists app.technology_presets (
  id uuid primary key default gen_random_uuid(),
  preset_code text not null unique,
  display_name text not null,
  machine_code text not null,
  material_code text not null,
  thickness_mm numeric(10,3) not null,
  kerf_mm numeric(10,3) not null,
  spacing_mm numeric(10,3) not null default 0,
  margin_mm numeric(10,3) not null default 0,
  rotation_step_deg integer not null default 90,
  allow_free_rotation boolean not null default false,
  lifecycle app.revision_lifecycle not null default 'approved',
  is_active boolean not null default true,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (length(btrim(preset_code)) > 0),
  check (length(btrim(display_name)) > 0),
  check (length(btrim(machine_code)) > 0),
  check (length(btrim(material_code)) > 0),
  check (thickness_mm > 0),
  check (kerf_mm >= 0),
  check (spacing_mm >= 0),
  check (margin_mm >= 0),
  check (rotation_step_deg > 0 and rotation_step_deg <= 360)
);

create table if not exists app.project_technology_setups (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references app.projects(id) on delete cascade,
  preset_id uuid references app.technology_presets(id) on delete set null,
  display_name text not null,
  lifecycle app.revision_lifecycle not null default 'draft',
  is_default boolean not null default false,
  machine_code text not null,
  material_code text not null,
  thickness_mm numeric(10,3) not null,
  kerf_mm numeric(10,3) not null,
  spacing_mm numeric(10,3) not null default 0,
  margin_mm numeric(10,3) not null default 0,
  rotation_step_deg integer not null default 90,
  allow_free_rotation boolean not null default false,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (length(btrim(display_name)) > 0),
  check (length(btrim(machine_code)) > 0),
  check (length(btrim(material_code)) > 0),
  check (thickness_mm > 0),
  check (kerf_mm >= 0),
  check (spacing_mm >= 0),
  check (margin_mm >= 0),
  check (rotation_step_deg > 0 and rotation_step_deg <= 360),
  unique (project_id, display_name)
);

create index if not exists idx_technology_presets_is_active
  on app.technology_presets(is_active);

create index if not exists idx_technology_presets_material_machine_thickness
  on app.technology_presets(material_code, machine_code, thickness_mm);

create index if not exists idx_project_technology_setups_project_id
  on app.project_technology_setups(project_id);

create index if not exists idx_project_technology_setups_preset_id
  on app.project_technology_setups(preset_id);

create index if not exists idx_project_technology_setups_project_lifecycle
  on app.project_technology_setups(project_id, lifecycle);

create unique index if not exists uq_project_technology_setups_default_per_project
  on app.project_technology_setups(project_id)
  where is_default;

drop trigger if exists trg_technology_presets_set_updated_at on app.technology_presets;
create trigger trg_technology_presets_set_updated_at
before update on app.technology_presets
for each row execute function app.set_updated_at();

drop trigger if exists trg_project_technology_setups_set_updated_at on app.project_technology_setups;
create trigger trg_project_technology_setups_set_updated_at
before update on app.project_technology_setups
for each row execute function app.set_updated_at();

-- NOTE:
-- This migration intentionally does not create part/file/revision/run/remnant/export tables.
-- RLS policies remain intentionally out of scope.
