-- H2-E1-T2: project manufacturing selection minimum truth
-- Scope: project-level manufacturing profile version selection only.

create table if not exists app.manufacturing_profiles (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references app.profiles(id) on delete restrict,
  profile_code text not null,
  profile_name text not null,
  lifecycle app.revision_lifecycle not null default 'draft',
  is_active boolean not null default true,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (length(btrim(profile_code)) > 0),
  check (length(btrim(profile_name)) > 0),
  unique (owner_user_id, profile_code)
);

alter table app.manufacturing_profiles
  add column if not exists owner_user_id uuid references app.profiles(id) on delete restrict,
  add column if not exists profile_code text,
  add column if not exists profile_name text,
  add column if not exists lifecycle app.revision_lifecycle not null default 'draft',
  add column if not exists is_active boolean not null default true,
  add column if not exists notes text,
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists updated_at timestamptz not null default now();

create index if not exists idx_manufacturing_profiles_owner_user_id
  on app.manufacturing_profiles(owner_user_id);

create unique index if not exists uq_manufacturing_profiles_owner_profile_code
  on app.manufacturing_profiles(owner_user_id, profile_code);

create unique index if not exists uq_manufacturing_profiles_id_owner
  on app.manufacturing_profiles(id, owner_user_id);

create table if not exists app.manufacturing_profile_versions (
  id uuid primary key default gen_random_uuid(),
  manufacturing_profile_id uuid not null references app.manufacturing_profiles(id) on delete cascade,
  owner_user_id uuid not null references app.profiles(id) on delete restrict,
  version_no integer not null,
  lifecycle app.revision_lifecycle not null default 'draft',
  is_active boolean not null default true,
  machine_code text,
  material_code text,
  thickness_mm numeric(10,3) not null,
  kerf_mm numeric(10,3) not null default 0,
  config_jsonb jsonb not null default '{}'::jsonb,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (version_no > 0),
  check (thickness_mm > 0),
  check (kerf_mm >= 0),
  check (machine_code is null or length(btrim(machine_code)) > 0),
  check (material_code is null or length(btrim(material_code)) > 0),
  unique (manufacturing_profile_id, version_no)
);

alter table app.manufacturing_profile_versions
  add column if not exists manufacturing_profile_id uuid references app.manufacturing_profiles(id) on delete cascade,
  add column if not exists owner_user_id uuid references app.profiles(id) on delete restrict,
  add column if not exists version_no integer,
  add column if not exists lifecycle app.revision_lifecycle not null default 'draft',
  add column if not exists is_active boolean not null default true,
  add column if not exists machine_code text,
  add column if not exists material_code text,
  add column if not exists thickness_mm numeric(10,3),
  add column if not exists kerf_mm numeric(10,3) not null default 0,
  add column if not exists config_jsonb jsonb not null default '{}'::jsonb,
  add column if not exists notes text,
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists updated_at timestamptz not null default now();

update app.manufacturing_profile_versions mpv
set owner_user_id = mp.owner_user_id
from app.manufacturing_profiles mp
where mpv.manufacturing_profile_id = mp.id
  and mpv.owner_user_id is null;

update app.manufacturing_profile_versions
set version_no = 1
where version_no is null;

update app.manufacturing_profile_versions
set thickness_mm = 1.000
where thickness_mm is null;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'fk_manufacturing_profile_versions_profile_owner'
      and conrelid = 'app.manufacturing_profile_versions'::regclass
  ) then
    alter table app.manufacturing_profile_versions
      add constraint fk_manufacturing_profile_versions_profile_owner
      foreign key (manufacturing_profile_id, owner_user_id)
      references app.manufacturing_profiles(id, owner_user_id)
      on delete cascade;
  end if;
end
$$;

create index if not exists idx_manufacturing_profile_versions_owner_user_id
  on app.manufacturing_profile_versions(owner_user_id);

create index if not exists idx_manufacturing_profile_versions_profile_id
  on app.manufacturing_profile_versions(manufacturing_profile_id);

create unique index if not exists uq_manufacturing_profile_versions_profile_version_no
  on app.manufacturing_profile_versions(manufacturing_profile_id, version_no);

create table if not exists app.project_manufacturing_selection (
  project_id uuid primary key references app.projects(id) on delete cascade,
  active_manufacturing_profile_version_id uuid not null references app.manufacturing_profile_versions(id) on delete restrict,
  selected_at timestamptz not null default now(),
  selected_by uuid not null references app.profiles(id) on delete restrict
);

alter table app.project_manufacturing_selection
  add column if not exists project_id uuid references app.projects(id) on delete cascade,
  add column if not exists active_manufacturing_profile_version_id uuid references app.manufacturing_profile_versions(id) on delete restrict,
  add column if not exists selected_at timestamptz not null default now(),
  add column if not exists selected_by uuid references app.profiles(id) on delete restrict;

update app.project_manufacturing_selection pms
set selected_by = p.owner_user_id
from app.projects p
where pms.project_id = p.id
  and pms.selected_by is null;

alter table app.project_manufacturing_selection
  alter column selected_by set default app.current_user_id();

create index if not exists idx_project_manufacturing_selection_active_version
  on app.project_manufacturing_selection(active_manufacturing_profile_version_id);

alter table app.manufacturing_profiles enable row level security;
alter table app.manufacturing_profile_versions enable row level security;
alter table app.project_manufacturing_selection enable row level security;

create or replace function app.owns_manufacturing_profile_version(version_uuid uuid)
returns boolean
language sql
stable
security definer
set search_path = app
as $$
  select exists (
    select 1
    from app.manufacturing_profile_versions mpv
    where mpv.id = version_uuid
      and mpv.owner_user_id = auth.uid()
  );
$$;

grant execute on function app.owns_manufacturing_profile_version(uuid) to authenticated;
grant execute on function app.owns_manufacturing_profile_version(uuid) to service_role;

drop policy if exists h2_e1_t2_manufacturing_profiles_select_owner on app.manufacturing_profiles;
create policy h2_e1_t2_manufacturing_profiles_select_owner
on app.manufacturing_profiles
for select
to authenticated
using (owner_user_id = app.current_user_id());

drop policy if exists h2_e1_t2_manufacturing_profiles_insert_owner on app.manufacturing_profiles;
create policy h2_e1_t2_manufacturing_profiles_insert_owner
on app.manufacturing_profiles
for insert
to authenticated
with check (owner_user_id = app.current_user_id());

drop policy if exists h2_e1_t2_manufacturing_profiles_update_owner on app.manufacturing_profiles;
create policy h2_e1_t2_manufacturing_profiles_update_owner
on app.manufacturing_profiles
for update
to authenticated
using (owner_user_id = app.current_user_id())
with check (owner_user_id = app.current_user_id());

drop policy if exists h2_e1_t2_manufacturing_profiles_delete_owner on app.manufacturing_profiles;
create policy h2_e1_t2_manufacturing_profiles_delete_owner
on app.manufacturing_profiles
for delete
to authenticated
using (owner_user_id = app.current_user_id());

drop policy if exists h2_e1_t2_manufacturing_profile_versions_select_owner on app.manufacturing_profile_versions;
create policy h2_e1_t2_manufacturing_profile_versions_select_owner
on app.manufacturing_profile_versions
for select
to authenticated
using (owner_user_id = app.current_user_id());

drop policy if exists h2_e1_t2_manufacturing_profile_versions_insert_owner on app.manufacturing_profile_versions;
create policy h2_e1_t2_manufacturing_profile_versions_insert_owner
on app.manufacturing_profile_versions
for insert
to authenticated
with check (owner_user_id = app.current_user_id());

drop policy if exists h2_e1_t2_manufacturing_profile_versions_update_owner on app.manufacturing_profile_versions;
create policy h2_e1_t2_manufacturing_profile_versions_update_owner
on app.manufacturing_profile_versions
for update
to authenticated
using (owner_user_id = app.current_user_id())
with check (owner_user_id = app.current_user_id());

drop policy if exists h2_e1_t2_manufacturing_profile_versions_delete_owner on app.manufacturing_profile_versions;
create policy h2_e1_t2_manufacturing_profile_versions_delete_owner
on app.manufacturing_profile_versions
for delete
to authenticated
using (owner_user_id = app.current_user_id());

drop policy if exists h2_e1_t2_project_manufacturing_selection_select_owner on app.project_manufacturing_selection;
create policy h2_e1_t2_project_manufacturing_selection_select_owner
on app.project_manufacturing_selection
for select
to authenticated
using (app.is_project_owner(project_id));

drop policy if exists h2_e1_t2_project_manufacturing_selection_insert_owner on app.project_manufacturing_selection;
create policy h2_e1_t2_project_manufacturing_selection_insert_owner
on app.project_manufacturing_selection
for insert
to authenticated
with check (
  app.is_project_owner(project_id)
  and app.owns_manufacturing_profile_version(active_manufacturing_profile_version_id)
  and selected_by = app.current_user_id()
);

drop policy if exists h2_e1_t2_project_manufacturing_selection_update_owner on app.project_manufacturing_selection;
create policy h2_e1_t2_project_manufacturing_selection_update_owner
on app.project_manufacturing_selection
for update
to authenticated
using (app.is_project_owner(project_id))
with check (
  app.is_project_owner(project_id)
  and app.owns_manufacturing_profile_version(active_manufacturing_profile_version_id)
  and selected_by = app.current_user_id()
);

drop policy if exists h2_e1_t2_project_manufacturing_selection_delete_owner on app.project_manufacturing_selection;
create policy h2_e1_t2_project_manufacturing_selection_delete_owner
on app.project_manufacturing_selection
for delete
to authenticated
using (app.is_project_owner(project_id));

drop trigger if exists trg_manufacturing_profiles_set_updated_at on app.manufacturing_profiles;
create trigger trg_manufacturing_profiles_set_updated_at
before update on app.manufacturing_profiles
for each row execute function app.set_updated_at();

drop trigger if exists trg_manufacturing_profile_versions_set_updated_at on app.manufacturing_profile_versions;
create trigger trg_manufacturing_profile_versions_set_updated_at
before update on app.manufacturing_profile_versions
for each row execute function app.set_updated_at();
