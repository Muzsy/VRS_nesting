-- H3-E1-T1: run strategy profile/version domain bevezetese
-- Scope: owner-scoped run_strategy_profiles + run_strategy_profile_versions
--        truth-reteg a futtatasi strategiak kulon domainjehez.
-- Nem-scope: scoring profile, project_run_strategy_selection,
--            batch/ranking, snapshot-builder/run-creation integracio,
--            machine_catalog/material_catalog FK vilag.

-- ============================================================
-- 1. run_strategy_profiles (owner-scoped profile csoport)
-- ============================================================

create table if not exists app.run_strategy_profiles (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references app.profiles(id) on delete restrict,
  strategy_code text not null,
  display_name text not null,
  description text,
  lifecycle app.revision_lifecycle not null default 'draft',
  is_active boolean not null default true,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (length(btrim(strategy_code)) > 0),
  check (length(btrim(display_name)) > 0),
  unique (owner_user_id, strategy_code)
);

create index if not exists idx_run_strategy_profiles_owner_user_id
  on app.run_strategy_profiles(owner_user_id);

create unique index if not exists uq_run_strategy_profiles_owner_strategy_code
  on app.run_strategy_profiles(owner_user_id, strategy_code);

create unique index if not exists uq_run_strategy_profiles_id_owner
  on app.run_strategy_profiles(id, owner_user_id);

-- ============================================================
-- 2. run_strategy_profile_versions (owner-scoped version truth)
-- ============================================================

create table if not exists app.run_strategy_profile_versions (
  id uuid primary key default gen_random_uuid(),
  run_strategy_profile_id uuid not null references app.run_strategy_profiles(id) on delete cascade,
  owner_user_id uuid not null references app.profiles(id) on delete restrict,
  version_no integer not null,
  lifecycle app.revision_lifecycle not null default 'draft',
  is_active boolean not null default true,
  solver_config_jsonb jsonb not null default '{}'::jsonb,
  placement_config_jsonb jsonb not null default '{}'::jsonb,
  manufacturing_bias_jsonb jsonb not null default '{}'::jsonb,
  notes text,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (version_no > 0),
  unique (run_strategy_profile_id, version_no)
);

-- owner-konzisztencia: version owner meg kell egyezzen a profile ownerevel
do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'fk_run_strategy_profile_versions_profile_owner'
      and conrelid = 'app.run_strategy_profile_versions'::regclass
  ) then
    alter table app.run_strategy_profile_versions
      add constraint fk_run_strategy_profile_versions_profile_owner
      foreign key (run_strategy_profile_id, owner_user_id)
      references app.run_strategy_profiles(id, owner_user_id)
      on delete cascade;
  end if;
end
$$;

create index if not exists idx_run_strategy_profile_versions_owner_user_id
  on app.run_strategy_profile_versions(owner_user_id);

create index if not exists idx_run_strategy_profile_versions_profile_id
  on app.run_strategy_profile_versions(run_strategy_profile_id);

create unique index if not exists uq_run_strategy_profile_versions_profile_version_no
  on app.run_strategy_profile_versions(run_strategy_profile_id, version_no);

-- ============================================================
-- 3. RLS policyk
-- ============================================================

alter table app.run_strategy_profiles enable row level security;
alter table app.run_strategy_profile_versions enable row level security;

-- run_strategy_profiles RLS
drop policy if exists h3_e1_t1_run_strategy_profiles_select_owner on app.run_strategy_profiles;
create policy h3_e1_t1_run_strategy_profiles_select_owner
on app.run_strategy_profiles
for select
to authenticated
using (owner_user_id = app.current_user_id());

drop policy if exists h3_e1_t1_run_strategy_profiles_insert_owner on app.run_strategy_profiles;
create policy h3_e1_t1_run_strategy_profiles_insert_owner
on app.run_strategy_profiles
for insert
to authenticated
with check (owner_user_id = app.current_user_id());

drop policy if exists h3_e1_t1_run_strategy_profiles_update_owner on app.run_strategy_profiles;
create policy h3_e1_t1_run_strategy_profiles_update_owner
on app.run_strategy_profiles
for update
to authenticated
using (owner_user_id = app.current_user_id())
with check (owner_user_id = app.current_user_id());

drop policy if exists h3_e1_t1_run_strategy_profiles_delete_owner on app.run_strategy_profiles;
create policy h3_e1_t1_run_strategy_profiles_delete_owner
on app.run_strategy_profiles
for delete
to authenticated
using (owner_user_id = app.current_user_id());

-- run_strategy_profile_versions RLS
drop policy if exists h3_e1_t1_run_strategy_profile_versions_select_owner on app.run_strategy_profile_versions;
create policy h3_e1_t1_run_strategy_profile_versions_select_owner
on app.run_strategy_profile_versions
for select
to authenticated
using (owner_user_id = app.current_user_id());

drop policy if exists h3_e1_t1_run_strategy_profile_versions_insert_owner on app.run_strategy_profile_versions;
create policy h3_e1_t1_run_strategy_profile_versions_insert_owner
on app.run_strategy_profile_versions
for insert
to authenticated
with check (owner_user_id = app.current_user_id());

drop policy if exists h3_e1_t1_run_strategy_profile_versions_update_owner on app.run_strategy_profile_versions;
create policy h3_e1_t1_run_strategy_profile_versions_update_owner
on app.run_strategy_profile_versions
for update
to authenticated
using (owner_user_id = app.current_user_id())
with check (owner_user_id = app.current_user_id());

drop policy if exists h3_e1_t1_run_strategy_profile_versions_delete_owner on app.run_strategy_profile_versions;
create policy h3_e1_t1_run_strategy_profile_versions_delete_owner
on app.run_strategy_profile_versions
for delete
to authenticated
using (owner_user_id = app.current_user_id());

-- ============================================================
-- 4. updated_at triggerek
-- ============================================================

drop trigger if exists trg_run_strategy_profiles_set_updated_at on app.run_strategy_profiles;
create trigger trg_run_strategy_profiles_set_updated_at
before update on app.run_strategy_profiles
for each row execute function app.set_updated_at();

drop trigger if exists trg_run_strategy_profile_versions_set_updated_at on app.run_strategy_profile_versions;
create trigger trg_run_strategy_profile_versions_set_updated_at
before update on app.run_strategy_profile_versions
for each row execute function app.set_updated_at();
