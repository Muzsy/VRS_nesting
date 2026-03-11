-- H0-E2-T2 core migration: profiles + projects + project_settings
-- Scope intentionally limited to identity/project core tables.

create table if not exists app.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (display_name is null or length(btrim(display_name)) > 0)
);

create table if not exists app.projects (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references app.profiles(id) on delete restrict,
  name text not null,
  description text,
  lifecycle app.project_lifecycle not null default 'draft',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (length(btrim(name)) > 0)
);

create table if not exists app.project_settings (
  project_id uuid primary key references app.projects(id) on delete cascade,
  default_units text not null default 'mm',
  default_rotation_step_deg integer not null default 90,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (default_units in ('mm', 'cm', 'm', 'in')),
  check (default_rotation_step_deg > 0 and default_rotation_step_deg <= 360)
);

create index if not exists idx_projects_owner_user_id
  on app.projects(owner_user_id);

create index if not exists idx_projects_lifecycle
  on app.projects(lifecycle);

create or replace function app.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_profiles_set_updated_at on app.profiles;
create trigger trg_profiles_set_updated_at
before update on app.profiles
for each row execute function app.set_updated_at();

drop trigger if exists trg_projects_set_updated_at on app.projects;
create trigger trg_projects_set_updated_at
before update on app.projects
for each row execute function app.set_updated_at();

drop trigger if exists trg_project_settings_set_updated_at on app.project_settings;
create trigger trg_project_settings_set_updated_at
before update on app.project_settings
for each row execute function app.set_updated_at();

-- NOTE:
-- This migration intentionally does not create technology/file/revision/run domain tables.
-- RLS and auth auto-provisioning are intentionally out of scope.
