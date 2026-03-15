-- H0-E6-T2: baseline RLS + storage policy foundations
-- Scope: minimal H0 ownership/project-bound DB-RLS and storage.objects policy.

-- ---------------------------------------------------------------------------
-- Helper functions for readable policies
-- ---------------------------------------------------------------------------

create or replace function app.current_user_id()
returns uuid
language sql
stable
as $$
  select auth.uid();
$$;

create or replace function app.is_project_owner(project_uuid uuid)
returns boolean
language sql
stable
security definer
set search_path = app, public
as $$
  select exists (
    select 1
    from app.projects p
    where p.id = project_uuid
      and p.owner_user_id = auth.uid()
  );
$$;

create or replace function app.owns_part_definition(part_definition_uuid uuid)
returns boolean
language sql
stable
security definer
set search_path = app, public
as $$
  select exists (
    select 1
    from app.part_definitions pd
    where pd.id = part_definition_uuid
      and pd.owner_user_id = auth.uid()
  );
$$;

create or replace function app.owns_sheet_definition(sheet_definition_uuid uuid)
returns boolean
language sql
stable
security definer
set search_path = app, public
as $$
  select exists (
    select 1
    from app.sheet_definitions sd
    where sd.id = sheet_definition_uuid
      and sd.owner_user_id = auth.uid()
  );
$$;

create or replace function app.can_access_geometry_revision(geometry_revision_uuid uuid)
returns boolean
language sql
stable
security definer
set search_path = app, public
as $$
  select exists (
    select 1
    from app.geometry_revisions gr
    join app.projects p on p.id = gr.project_id
    where gr.id = geometry_revision_uuid
      and p.owner_user_id = auth.uid()
  );
$$;

create or replace function app.can_access_run(run_uuid uuid)
returns boolean
language sql
stable
security definer
set search_path = app, public
as $$
  select exists (
    select 1
    from app.nesting_runs r
    join app.projects p on p.id = r.project_id
    where r.id = run_uuid
      and p.owner_user_id = auth.uid()
  );
$$;

create or replace function app.storage_object_project_id(object_name text)
returns uuid
language plpgsql
stable
as $$
declare
  match_groups text[];
begin
  if object_name is null then
    return null;
  end if;

  match_groups := regexp_match(
    object_name,
    '^projects/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12})/'
  );

  if match_groups is null then
    return null;
  end if;

  return match_groups[1]::uuid;
end;
$$;

grant execute on function app.current_user_id() to authenticated;
grant execute on function app.is_project_owner(uuid) to authenticated;
grant execute on function app.owns_part_definition(uuid) to authenticated;
grant execute on function app.owns_sheet_definition(uuid) to authenticated;
grant execute on function app.can_access_geometry_revision(uuid) to authenticated;
grant execute on function app.can_access_run(uuid) to authenticated;
grant execute on function app.storage_object_project_id(text) to authenticated;

-- ---------------------------------------------------------------------------
-- Enable RLS on core H0 app.* tables
-- ---------------------------------------------------------------------------

alter table app.profiles enable row level security;
alter table app.projects enable row level security;
alter table app.project_settings enable row level security;
alter table app.technology_presets enable row level security;
alter table app.project_technology_setups enable row level security;
alter table app.part_definitions enable row level security;
alter table app.part_revisions enable row level security;
alter table app.project_part_requirements enable row level security;
alter table app.sheet_definitions enable row level security;
alter table app.sheet_revisions enable row level security;
alter table app.project_sheet_inputs enable row level security;
alter table app.file_objects enable row level security;
alter table app.geometry_revisions enable row level security;
alter table app.geometry_validation_reports enable row level security;
alter table app.geometry_review_actions enable row level security;
alter table app.geometry_derivatives enable row level security;
alter table app.nesting_runs enable row level security;
alter table app.nesting_run_snapshots enable row level security;
alter table app.run_queue enable row level security;
alter table app.run_logs enable row level security;
alter table app.run_artifacts enable row level security;
alter table app.run_layout_sheets enable row level security;
alter table app.run_layout_placements enable row level security;
alter table app.run_layout_unplaced enable row level security;
alter table app.run_metrics enable row level security;

-- ---------------------------------------------------------------------------
-- app.profiles: self-row
-- ---------------------------------------------------------------------------

drop policy if exists h0_e6_t2_profiles_select_self on app.profiles;
create policy h0_e6_t2_profiles_select_self
on app.profiles
for select
to authenticated
using (id = app.current_user_id());

drop policy if exists h0_e6_t2_profiles_insert_self on app.profiles;
create policy h0_e6_t2_profiles_insert_self
on app.profiles
for insert
to authenticated
with check (id = app.current_user_id());

drop policy if exists h0_e6_t2_profiles_update_self on app.profiles;
create policy h0_e6_t2_profiles_update_self
on app.profiles
for update
to authenticated
using (id = app.current_user_id())
with check (id = app.current_user_id());

drop policy if exists h0_e6_t2_profiles_delete_self on app.profiles;
create policy h0_e6_t2_profiles_delete_self
on app.profiles
for delete
to authenticated
using (id = app.current_user_id());

-- ---------------------------------------------------------------------------
-- app.projects and direct project child tables
-- ---------------------------------------------------------------------------

drop policy if exists h0_e6_t2_projects_select_owner on app.projects;
create policy h0_e6_t2_projects_select_owner
on app.projects
for select
to authenticated
using (owner_user_id = app.current_user_id());

drop policy if exists h0_e6_t2_projects_insert_owner on app.projects;
create policy h0_e6_t2_projects_insert_owner
on app.projects
for insert
to authenticated
with check (owner_user_id = app.current_user_id());

drop policy if exists h0_e6_t2_projects_update_owner on app.projects;
create policy h0_e6_t2_projects_update_owner
on app.projects
for update
to authenticated
using (owner_user_id = app.current_user_id())
with check (owner_user_id = app.current_user_id());

drop policy if exists h0_e6_t2_projects_delete_owner on app.projects;
create policy h0_e6_t2_projects_delete_owner
on app.projects
for delete
to authenticated
using (owner_user_id = app.current_user_id());

drop policy if exists h0_e6_t2_project_settings_select_owner on app.project_settings;
create policy h0_e6_t2_project_settings_select_owner
on app.project_settings
for select
to authenticated
using (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_project_settings_insert_owner on app.project_settings;
create policy h0_e6_t2_project_settings_insert_owner
on app.project_settings
for insert
to authenticated
with check (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_project_settings_update_owner on app.project_settings;
create policy h0_e6_t2_project_settings_update_owner
on app.project_settings
for update
to authenticated
using (app.is_project_owner(project_id))
with check (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_project_settings_delete_owner on app.project_settings;
create policy h0_e6_t2_project_settings_delete_owner
on app.project_settings
for delete
to authenticated
using (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_project_technology_setups_select_owner on app.project_technology_setups;
create policy h0_e6_t2_project_technology_setups_select_owner
on app.project_technology_setups
for select
to authenticated
using (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_project_technology_setups_insert_owner on app.project_technology_setups;
create policy h0_e6_t2_project_technology_setups_insert_owner
on app.project_technology_setups
for insert
to authenticated
with check (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_project_technology_setups_update_owner on app.project_technology_setups;
create policy h0_e6_t2_project_technology_setups_update_owner
on app.project_technology_setups
for update
to authenticated
using (app.is_project_owner(project_id))
with check (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_project_technology_setups_delete_owner on app.project_technology_setups;
create policy h0_e6_t2_project_technology_setups_delete_owner
on app.project_technology_setups
for delete
to authenticated
using (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_project_part_requirements_select_owner on app.project_part_requirements;
create policy h0_e6_t2_project_part_requirements_select_owner
on app.project_part_requirements
for select
to authenticated
using (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_project_part_requirements_insert_owner on app.project_part_requirements;
create policy h0_e6_t2_project_part_requirements_insert_owner
on app.project_part_requirements
for insert
to authenticated
with check (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_project_part_requirements_update_owner on app.project_part_requirements;
create policy h0_e6_t2_project_part_requirements_update_owner
on app.project_part_requirements
for update
to authenticated
using (app.is_project_owner(project_id))
with check (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_project_part_requirements_delete_owner on app.project_part_requirements;
create policy h0_e6_t2_project_part_requirements_delete_owner
on app.project_part_requirements
for delete
to authenticated
using (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_project_sheet_inputs_select_owner on app.project_sheet_inputs;
create policy h0_e6_t2_project_sheet_inputs_select_owner
on app.project_sheet_inputs
for select
to authenticated
using (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_project_sheet_inputs_insert_owner on app.project_sheet_inputs;
create policy h0_e6_t2_project_sheet_inputs_insert_owner
on app.project_sheet_inputs
for insert
to authenticated
with check (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_project_sheet_inputs_update_owner on app.project_sheet_inputs;
create policy h0_e6_t2_project_sheet_inputs_update_owner
on app.project_sheet_inputs
for update
to authenticated
using (app.is_project_owner(project_id))
with check (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_project_sheet_inputs_delete_owner on app.project_sheet_inputs;
create policy h0_e6_t2_project_sheet_inputs_delete_owner
on app.project_sheet_inputs
for delete
to authenticated
using (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_file_objects_select_owner on app.file_objects;
create policy h0_e6_t2_file_objects_select_owner
on app.file_objects
for select
to authenticated
using (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_file_objects_insert_owner on app.file_objects;
create policy h0_e6_t2_file_objects_insert_owner
on app.file_objects
for insert
to authenticated
with check (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_file_objects_update_owner on app.file_objects;
create policy h0_e6_t2_file_objects_update_owner
on app.file_objects
for update
to authenticated
using (app.is_project_owner(project_id))
with check (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_file_objects_delete_owner on app.file_objects;
create policy h0_e6_t2_file_objects_delete_owner
on app.file_objects
for delete
to authenticated
using (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_geometry_revisions_select_owner on app.geometry_revisions;
create policy h0_e6_t2_geometry_revisions_select_owner
on app.geometry_revisions
for select
to authenticated
using (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_geometry_revisions_insert_owner on app.geometry_revisions;
create policy h0_e6_t2_geometry_revisions_insert_owner
on app.geometry_revisions
for insert
to authenticated
with check (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_geometry_revisions_update_owner on app.geometry_revisions;
create policy h0_e6_t2_geometry_revisions_update_owner
on app.geometry_revisions
for update
to authenticated
using (app.is_project_owner(project_id))
with check (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_geometry_revisions_delete_owner on app.geometry_revisions;
create policy h0_e6_t2_geometry_revisions_delete_owner
on app.geometry_revisions
for delete
to authenticated
using (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_nesting_runs_select_owner on app.nesting_runs;
create policy h0_e6_t2_nesting_runs_select_owner
on app.nesting_runs
for select
to authenticated
using (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_nesting_runs_insert_owner on app.nesting_runs;
create policy h0_e6_t2_nesting_runs_insert_owner
on app.nesting_runs
for insert
to authenticated
with check (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_nesting_runs_update_owner on app.nesting_runs;
create policy h0_e6_t2_nesting_runs_update_owner
on app.nesting_runs
for update
to authenticated
using (app.is_project_owner(project_id))
with check (app.is_project_owner(project_id));

drop policy if exists h0_e6_t2_nesting_runs_delete_owner on app.nesting_runs;
create policy h0_e6_t2_nesting_runs_delete_owner
on app.nesting_runs
for delete
to authenticated
using (app.is_project_owner(project_id));

-- ---------------------------------------------------------------------------
-- Owner-bound definition/revision world
-- ---------------------------------------------------------------------------

drop policy if exists h0_e6_t2_part_definitions_select_owner on app.part_definitions;
create policy h0_e6_t2_part_definitions_select_owner
on app.part_definitions
for select
to authenticated
using (owner_user_id = app.current_user_id());

drop policy if exists h0_e6_t2_part_definitions_insert_owner on app.part_definitions;
create policy h0_e6_t2_part_definitions_insert_owner
on app.part_definitions
for insert
to authenticated
with check (owner_user_id = app.current_user_id());

drop policy if exists h0_e6_t2_part_definitions_update_owner on app.part_definitions;
create policy h0_e6_t2_part_definitions_update_owner
on app.part_definitions
for update
to authenticated
using (owner_user_id = app.current_user_id())
with check (owner_user_id = app.current_user_id());

drop policy if exists h0_e6_t2_part_definitions_delete_owner on app.part_definitions;
create policy h0_e6_t2_part_definitions_delete_owner
on app.part_definitions
for delete
to authenticated
using (owner_user_id = app.current_user_id());

drop policy if exists h0_e6_t2_part_revisions_select_owner on app.part_revisions;
create policy h0_e6_t2_part_revisions_select_owner
on app.part_revisions
for select
to authenticated
using (app.owns_part_definition(part_definition_id));

drop policy if exists h0_e6_t2_part_revisions_insert_owner on app.part_revisions;
create policy h0_e6_t2_part_revisions_insert_owner
on app.part_revisions
for insert
to authenticated
with check (app.owns_part_definition(part_definition_id));

drop policy if exists h0_e6_t2_part_revisions_update_owner on app.part_revisions;
create policy h0_e6_t2_part_revisions_update_owner
on app.part_revisions
for update
to authenticated
using (app.owns_part_definition(part_definition_id))
with check (app.owns_part_definition(part_definition_id));

drop policy if exists h0_e6_t2_part_revisions_delete_owner on app.part_revisions;
create policy h0_e6_t2_part_revisions_delete_owner
on app.part_revisions
for delete
to authenticated
using (app.owns_part_definition(part_definition_id));

drop policy if exists h0_e6_t2_sheet_definitions_select_owner on app.sheet_definitions;
create policy h0_e6_t2_sheet_definitions_select_owner
on app.sheet_definitions
for select
to authenticated
using (owner_user_id = app.current_user_id());

drop policy if exists h0_e6_t2_sheet_definitions_insert_owner on app.sheet_definitions;
create policy h0_e6_t2_sheet_definitions_insert_owner
on app.sheet_definitions
for insert
to authenticated
with check (owner_user_id = app.current_user_id());

drop policy if exists h0_e6_t2_sheet_definitions_update_owner on app.sheet_definitions;
create policy h0_e6_t2_sheet_definitions_update_owner
on app.sheet_definitions
for update
to authenticated
using (owner_user_id = app.current_user_id())
with check (owner_user_id = app.current_user_id());

drop policy if exists h0_e6_t2_sheet_definitions_delete_owner on app.sheet_definitions;
create policy h0_e6_t2_sheet_definitions_delete_owner
on app.sheet_definitions
for delete
to authenticated
using (owner_user_id = app.current_user_id());

drop policy if exists h0_e6_t2_sheet_revisions_select_owner on app.sheet_revisions;
create policy h0_e6_t2_sheet_revisions_select_owner
on app.sheet_revisions
for select
to authenticated
using (app.owns_sheet_definition(sheet_definition_id));

drop policy if exists h0_e6_t2_sheet_revisions_insert_owner on app.sheet_revisions;
create policy h0_e6_t2_sheet_revisions_insert_owner
on app.sheet_revisions
for insert
to authenticated
with check (app.owns_sheet_definition(sheet_definition_id));

drop policy if exists h0_e6_t2_sheet_revisions_update_owner on app.sheet_revisions;
create policy h0_e6_t2_sheet_revisions_update_owner
on app.sheet_revisions
for update
to authenticated
using (app.owns_sheet_definition(sheet_definition_id))
with check (app.owns_sheet_definition(sheet_definition_id));

drop policy if exists h0_e6_t2_sheet_revisions_delete_owner on app.sheet_revisions;
create policy h0_e6_t2_sheet_revisions_delete_owner
on app.sheet_revisions
for delete
to authenticated
using (app.owns_sheet_definition(sheet_definition_id));

-- ---------------------------------------------------------------------------
-- Geometry audit/review/derivative world
-- ---------------------------------------------------------------------------

drop policy if exists h0_e6_t2_geometry_validation_reports_select_owner on app.geometry_validation_reports;
create policy h0_e6_t2_geometry_validation_reports_select_owner
on app.geometry_validation_reports
for select
to authenticated
using (app.can_access_geometry_revision(geometry_revision_id));

drop policy if exists h0_e6_t2_geometry_review_actions_select_owner on app.geometry_review_actions;
create policy h0_e6_t2_geometry_review_actions_select_owner
on app.geometry_review_actions
for select
to authenticated
using (app.can_access_geometry_revision(geometry_revision_id));

drop policy if exists h0_e6_t2_geometry_review_actions_insert_owner on app.geometry_review_actions;
create policy h0_e6_t2_geometry_review_actions_insert_owner
on app.geometry_review_actions
for insert
to authenticated
with check (
  app.can_access_geometry_revision(geometry_revision_id)
  and (actor_user_id is null or actor_user_id = app.current_user_id())
);

drop policy if exists h0_e6_t2_geometry_derivatives_select_owner on app.geometry_derivatives;
create policy h0_e6_t2_geometry_derivatives_select_owner
on app.geometry_derivatives
for select
to authenticated
using (app.can_access_geometry_revision(geometry_revision_id));

-- ---------------------------------------------------------------------------
-- Run snapshot/output world: user-side read only
-- ---------------------------------------------------------------------------

drop policy if exists h0_e6_t2_nesting_run_snapshots_select_owner on app.nesting_run_snapshots;
create policy h0_e6_t2_nesting_run_snapshots_select_owner
on app.nesting_run_snapshots
for select
to authenticated
using (app.can_access_run(run_id));

drop policy if exists h0_e6_t2_run_queue_select_owner on app.run_queue;
create policy h0_e6_t2_run_queue_select_owner
on app.run_queue
for select
to authenticated
using (app.can_access_run(run_id));

drop policy if exists h0_e6_t2_run_logs_select_owner on app.run_logs;
create policy h0_e6_t2_run_logs_select_owner
on app.run_logs
for select
to authenticated
using (app.can_access_run(run_id));

drop policy if exists h0_e6_t2_run_artifacts_select_owner on app.run_artifacts;
create policy h0_e6_t2_run_artifacts_select_owner
on app.run_artifacts
for select
to authenticated
using (app.can_access_run(run_id));

drop policy if exists h0_e6_t2_run_layout_sheets_select_owner on app.run_layout_sheets;
create policy h0_e6_t2_run_layout_sheets_select_owner
on app.run_layout_sheets
for select
to authenticated
using (app.can_access_run(run_id));

drop policy if exists h0_e6_t2_run_layout_placements_select_owner on app.run_layout_placements;
create policy h0_e6_t2_run_layout_placements_select_owner
on app.run_layout_placements
for select
to authenticated
using (app.can_access_run(run_id));

drop policy if exists h0_e6_t2_run_layout_unplaced_select_owner on app.run_layout_unplaced;
create policy h0_e6_t2_run_layout_unplaced_select_owner
on app.run_layout_unplaced
for select
to authenticated
using (app.can_access_run(run_id));

drop policy if exists h0_e6_t2_run_metrics_select_owner on app.run_metrics;
create policy h0_e6_t2_run_metrics_select_owner
on app.run_metrics
for select
to authenticated
using (app.can_access_run(run_id));

-- ---------------------------------------------------------------------------
-- technology_presets: authenticated read only
-- ---------------------------------------------------------------------------

drop policy if exists h0_e6_t2_technology_presets_select_authenticated on app.technology_presets;
create policy h0_e6_t2_technology_presets_select_authenticated
on app.technology_presets
for select
to authenticated
using (true);

-- ---------------------------------------------------------------------------
-- storage.objects minimal policy for canonical H0 buckets
-- ---------------------------------------------------------------------------

alter table storage.objects enable row level security;

drop policy if exists h0_e6_t2_storage_source_files_select_owner on storage.objects;
create policy h0_e6_t2_storage_source_files_select_owner
on storage.objects
for select
to authenticated
using (
  bucket_id = 'source-files'
  and app.storage_object_project_id(name) is not null
  and app.is_project_owner(app.storage_object_project_id(name))
);

drop policy if exists h0_e6_t2_storage_source_files_insert_owner on storage.objects;
create policy h0_e6_t2_storage_source_files_insert_owner
on storage.objects
for insert
to authenticated
with check (
  bucket_id = 'source-files'
  and app.storage_object_project_id(name) is not null
  and app.is_project_owner(app.storage_object_project_id(name))
);

drop policy if exists h0_e6_t2_storage_geometry_artifacts_select_owner on storage.objects;
create policy h0_e6_t2_storage_geometry_artifacts_select_owner
on storage.objects
for select
to authenticated
using (
  bucket_id = 'geometry-artifacts'
  and app.storage_object_project_id(name) is not null
  and app.is_project_owner(app.storage_object_project_id(name))
);

drop policy if exists h0_e6_t2_storage_run_artifacts_select_owner on storage.objects;
create policy h0_e6_t2_storage_run_artifacts_select_owner
on storage.objects
for select
to authenticated
using (
  bucket_id = 'run-artifacts'
  and app.storage_object_project_id(name) is not null
  and app.is_project_owner(app.storage_object_project_id(name))
);

-- NOTE:
-- - anon role has no explicit policy on app.* or storage.objects in this migration.
-- - service-role boundary remains the write path for worker/output worlds.
-- - auth auto-provisioning trigger and worker/API implementation stay out of scope.
