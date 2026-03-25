-- H3-E1-T2: scoring profile/version domain bevezetese
-- Scope: owner-scoped scoring_profiles + scoring_profile_versions
--        truth-reteg a scoring preferencia kulon domainjehez.
-- Nem-scope: project_scoring_selection, run_evaluations,
--            ranking engine, batch orchestration, comparison projection,
--            H2 manufacturing truth tabla modositas.

-- ============================================================
-- 1. scoring_profiles (owner-scoped profile csoport)
-- ============================================================

create table if not exists app.scoring_profiles (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references app.profiles(id) on delete restrict,
  name text not null,
  description text,
  lifecycle app.revision_lifecycle not null default 'draft',
  is_active boolean not null default true,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (length(btrim(name)) > 0),
  unique (owner_user_id, name)
);

create index if not exists idx_scoring_profiles_owner_user_id
  on app.scoring_profiles(owner_user_id);

create unique index if not exists uq_scoring_profiles_owner_name
  on app.scoring_profiles(owner_user_id, name);

create unique index if not exists uq_scoring_profiles_id_owner
  on app.scoring_profiles(id, owner_user_id);

-- ============================================================
-- 2. scoring_profile_versions (owner-scoped version truth)
-- ============================================================

create table if not exists app.scoring_profile_versions (
  id uuid primary key default gen_random_uuid(),
  scoring_profile_id uuid not null references app.scoring_profiles(id) on delete cascade,
  owner_user_id uuid not null references app.profiles(id) on delete restrict,
  version_no integer not null,
  lifecycle app.revision_lifecycle not null default 'draft',
  is_active boolean not null default true,
  weights_jsonb jsonb not null default '{}'::jsonb,
  tie_breaker_jsonb jsonb not null default '{}'::jsonb,
  threshold_jsonb jsonb not null default '{}'::jsonb,
  notes text,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (version_no > 0),
  unique (scoring_profile_id, version_no)
);

-- owner-konzisztencia: version owner meg kell egyezzen a profile ownerevel
do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'fk_scoring_profile_versions_profile_owner'
      and conrelid = 'app.scoring_profile_versions'::regclass
  ) then
    alter table app.scoring_profile_versions
      add constraint fk_scoring_profile_versions_profile_owner
      foreign key (scoring_profile_id, owner_user_id)
      references app.scoring_profiles(id, owner_user_id)
      on delete cascade;
  end if;
end
$$;

create index if not exists idx_scoring_profile_versions_owner_user_id
  on app.scoring_profile_versions(owner_user_id);

create index if not exists idx_scoring_profile_versions_profile_id
  on app.scoring_profile_versions(scoring_profile_id);

create unique index if not exists uq_scoring_profile_versions_profile_version_no
  on app.scoring_profile_versions(scoring_profile_id, version_no);

-- ============================================================
-- 3. RLS policyk
-- ============================================================

alter table app.scoring_profiles enable row level security;
alter table app.scoring_profile_versions enable row level security;

-- scoring_profiles RLS
drop policy if exists h3_e1_t2_scoring_profiles_select_owner on app.scoring_profiles;
create policy h3_e1_t2_scoring_profiles_select_owner
on app.scoring_profiles
for select
to authenticated
using (owner_user_id = app.current_user_id());

drop policy if exists h3_e1_t2_scoring_profiles_insert_owner on app.scoring_profiles;
create policy h3_e1_t2_scoring_profiles_insert_owner
on app.scoring_profiles
for insert
to authenticated
with check (owner_user_id = app.current_user_id());

drop policy if exists h3_e1_t2_scoring_profiles_update_owner on app.scoring_profiles;
create policy h3_e1_t2_scoring_profiles_update_owner
on app.scoring_profiles
for update
to authenticated
using (owner_user_id = app.current_user_id())
with check (owner_user_id = app.current_user_id());

drop policy if exists h3_e1_t2_scoring_profiles_delete_owner on app.scoring_profiles;
create policy h3_e1_t2_scoring_profiles_delete_owner
on app.scoring_profiles
for delete
to authenticated
using (owner_user_id = app.current_user_id());

-- scoring_profile_versions RLS
drop policy if exists h3_e1_t2_scoring_profile_versions_select_owner on app.scoring_profile_versions;
create policy h3_e1_t2_scoring_profile_versions_select_owner
on app.scoring_profile_versions
for select
to authenticated
using (owner_user_id = app.current_user_id());

drop policy if exists h3_e1_t2_scoring_profile_versions_insert_owner on app.scoring_profile_versions;
create policy h3_e1_t2_scoring_profile_versions_insert_owner
on app.scoring_profile_versions
for insert
to authenticated
with check (owner_user_id = app.current_user_id());

drop policy if exists h3_e1_t2_scoring_profile_versions_update_owner on app.scoring_profile_versions;
create policy h3_e1_t2_scoring_profile_versions_update_owner
on app.scoring_profile_versions
for update
to authenticated
using (owner_user_id = app.current_user_id())
with check (owner_user_id = app.current_user_id());

drop policy if exists h3_e1_t2_scoring_profile_versions_delete_owner on app.scoring_profile_versions;
create policy h3_e1_t2_scoring_profile_versions_delete_owner
on app.scoring_profile_versions
for delete
to authenticated
using (owner_user_id = app.current_user_id());

-- ============================================================
-- 4. updated_at triggerek
-- ============================================================

drop trigger if exists trg_scoring_profiles_set_updated_at on app.scoring_profiles;
create trigger trg_scoring_profiles_set_updated_at
before update on app.scoring_profiles
for each row execute function app.set_updated_at();

drop trigger if exists trg_scoring_profile_versions_set_updated_at on app.scoring_profile_versions;
create trigger trg_scoring_profile_versions_set_updated_at
before update on app.scoring_profile_versions
for each row execute function app.set_updated_at();
