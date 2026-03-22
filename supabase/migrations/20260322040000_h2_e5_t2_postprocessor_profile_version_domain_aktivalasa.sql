-- H2-E5-T2: postprocessor profile/version domain aktivalasa
-- Scope: owner-scoped postprocessor_profiles + postprocessor_profile_versions
--        truth-reteg, manufacturing_profile_versions nullable
--        active_postprocessor_profile_version_id mezo, owner-konzisztencia.
-- Nem-scope: catalog FK, export/adapter, project-level postprocess selection tabla.

-- ============================================================
-- 1. postprocessor_profiles (owner-scoped profile csoport)
-- ============================================================

create table if not exists app.postprocessor_profiles (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references app.profiles(id) on delete restrict,
  profile_code text not null,
  display_name text not null,
  adapter_key text not null default 'generic',
  is_active boolean not null default true,
  notes text,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (length(btrim(profile_code)) > 0),
  check (length(btrim(display_name)) > 0),
  check (length(btrim(adapter_key)) > 0),
  unique (owner_user_id, profile_code)
);

create index if not exists idx_postprocessor_profiles_owner_user_id
  on app.postprocessor_profiles(owner_user_id);

create unique index if not exists uq_postprocessor_profiles_owner_profile_code
  on app.postprocessor_profiles(owner_user_id, profile_code);

create unique index if not exists uq_postprocessor_profiles_id_owner
  on app.postprocessor_profiles(id, owner_user_id);

-- ============================================================
-- 2. postprocessor_profile_versions (owner-scoped version truth)
-- ============================================================

create table if not exists app.postprocessor_profile_versions (
  id uuid primary key default gen_random_uuid(),
  postprocessor_profile_id uuid not null references app.postprocessor_profiles(id) on delete cascade,
  owner_user_id uuid not null references app.profiles(id) on delete restrict,
  version_no integer not null,
  lifecycle app.revision_lifecycle not null default 'draft',
  is_active boolean not null default true,
  adapter_key text not null default 'generic',
  output_format text not null default 'json',
  schema_version text not null default 'v1',
  config_jsonb jsonb not null default '{}'::jsonb,
  notes text,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (version_no > 0),
  check (length(btrim(adapter_key)) > 0),
  check (length(btrim(output_format)) > 0),
  check (length(btrim(schema_version)) > 0),
  unique (postprocessor_profile_id, version_no)
);

-- owner-konzisztencia: version owner meg kell egyezzen a profile ownerevel
do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'fk_postprocessor_profile_versions_profile_owner'
      and conrelid = 'app.postprocessor_profile_versions'::regclass
  ) then
    alter table app.postprocessor_profile_versions
      add constraint fk_postprocessor_profile_versions_profile_owner
      foreign key (postprocessor_profile_id, owner_user_id)
      references app.postprocessor_profiles(id, owner_user_id)
      on delete cascade;
  end if;
end
$$;

create index if not exists idx_postprocessor_profile_versions_owner_user_id
  on app.postprocessor_profile_versions(owner_user_id);

create index if not exists idx_postprocessor_profile_versions_profile_id
  on app.postprocessor_profile_versions(postprocessor_profile_id);

create unique index if not exists uq_postprocessor_profile_versions_profile_version_no
  on app.postprocessor_profile_versions(postprocessor_profile_id, version_no);

-- ============================================================
-- 3. manufacturing_profile_versions bovites: active_postprocessor_profile_version_id
-- ============================================================

alter table app.manufacturing_profile_versions
  add column if not exists active_postprocessor_profile_version_id uuid
    references app.postprocessor_profile_versions(id) on delete set null;

create index if not exists idx_manufacturing_profile_versions_active_postprocessor
  on app.manufacturing_profile_versions(active_postprocessor_profile_version_id);

-- ============================================================
-- 4. RLS policyk
-- ============================================================

alter table app.postprocessor_profiles enable row level security;
alter table app.postprocessor_profile_versions enable row level security;

-- postprocessor_profiles RLS
drop policy if exists h2_e5_t2_postprocessor_profiles_select_owner on app.postprocessor_profiles;
create policy h2_e5_t2_postprocessor_profiles_select_owner
on app.postprocessor_profiles
for select
to authenticated
using (owner_user_id = app.current_user_id());

drop policy if exists h2_e5_t2_postprocessor_profiles_insert_owner on app.postprocessor_profiles;
create policy h2_e5_t2_postprocessor_profiles_insert_owner
on app.postprocessor_profiles
for insert
to authenticated
with check (owner_user_id = app.current_user_id());

drop policy if exists h2_e5_t2_postprocessor_profiles_update_owner on app.postprocessor_profiles;
create policy h2_e5_t2_postprocessor_profiles_update_owner
on app.postprocessor_profiles
for update
to authenticated
using (owner_user_id = app.current_user_id())
with check (owner_user_id = app.current_user_id());

drop policy if exists h2_e5_t2_postprocessor_profiles_delete_owner on app.postprocessor_profiles;
create policy h2_e5_t2_postprocessor_profiles_delete_owner
on app.postprocessor_profiles
for delete
to authenticated
using (owner_user_id = app.current_user_id());

-- postprocessor_profile_versions RLS
drop policy if exists h2_e5_t2_postprocessor_profile_versions_select_owner on app.postprocessor_profile_versions;
create policy h2_e5_t2_postprocessor_profile_versions_select_owner
on app.postprocessor_profile_versions
for select
to authenticated
using (owner_user_id = app.current_user_id());

drop policy if exists h2_e5_t2_postprocessor_profile_versions_insert_owner on app.postprocessor_profile_versions;
create policy h2_e5_t2_postprocessor_profile_versions_insert_owner
on app.postprocessor_profile_versions
for insert
to authenticated
with check (owner_user_id = app.current_user_id());

drop policy if exists h2_e5_t2_postprocessor_profile_versions_update_owner on app.postprocessor_profile_versions;
create policy h2_e5_t2_postprocessor_profile_versions_update_owner
on app.postprocessor_profile_versions
for update
to authenticated
using (owner_user_id = app.current_user_id())
with check (owner_user_id = app.current_user_id());

drop policy if exists h2_e5_t2_postprocessor_profile_versions_delete_owner on app.postprocessor_profile_versions;
create policy h2_e5_t2_postprocessor_profile_versions_delete_owner
on app.postprocessor_profile_versions
for delete
to authenticated
using (owner_user_id = app.current_user_id());

-- ============================================================
-- 5. updated_at triggerek
-- ============================================================

drop trigger if exists trg_postprocessor_profiles_set_updated_at on app.postprocessor_profiles;
create trigger trg_postprocessor_profiles_set_updated_at
before update on app.postprocessor_profiles
for each row execute function app.set_updated_at();

drop trigger if exists trg_postprocessor_profile_versions_set_updated_at on app.postprocessor_profile_versions;
create trigger trg_postprocessor_profile_versions_set_updated_at
before update on app.postprocessor_profile_versions
for each row execute function app.set_updated_at();
