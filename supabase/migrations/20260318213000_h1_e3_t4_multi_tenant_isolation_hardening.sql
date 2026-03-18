-- H1-E3-T4: multi-tenant isolation hardening follow-up
-- Scope:
--  - remove anon access on app schema/tables
--  - add missing authenticated write RLS policies
--  - enforce source-files bucket ownership policies on storage.objects

-- -----------------------------------------------------------------------------
-- 1) Revoke anon exposure on app schema/tables (defense-in-depth)
-- -----------------------------------------------------------------------------

revoke usage on schema app from anon;
revoke select on all tables in schema app from anon;

alter default privileges in schema app
  revoke select on tables from anon;

-- -----------------------------------------------------------------------------
-- 2) Missing write policies for geometry validation/derivatives
-- -----------------------------------------------------------------------------

drop policy if exists h1_e3_t4_geometry_validation_reports_insert_owner on app.geometry_validation_reports;
create policy h1_e3_t4_geometry_validation_reports_insert_owner
on app.geometry_validation_reports
for insert
to authenticated
with check (app.can_access_geometry_revision(geometry_revision_id));

drop policy if exists h1_e3_t4_geometry_validation_reports_update_owner on app.geometry_validation_reports;
create policy h1_e3_t4_geometry_validation_reports_update_owner
on app.geometry_validation_reports
for update
to authenticated
using (app.can_access_geometry_revision(geometry_revision_id))
with check (app.can_access_geometry_revision(geometry_revision_id));

drop policy if exists h1_e3_t4_geometry_derivatives_insert_owner on app.geometry_derivatives;
create policy h1_e3_t4_geometry_derivatives_insert_owner
on app.geometry_derivatives
for insert
to authenticated
with check (app.can_access_geometry_revision(geometry_revision_id));

drop policy if exists h1_e3_t4_geometry_derivatives_update_owner on app.geometry_derivatives;
create policy h1_e3_t4_geometry_derivatives_update_owner
on app.geometry_derivatives
for update
to authenticated
using (app.can_access_geometry_revision(geometry_revision_id))
with check (app.can_access_geometry_revision(geometry_revision_id));

-- -----------------------------------------------------------------------------
-- 3) Missing write policies for run_queue / run_artifacts (app.* direct API)
-- -----------------------------------------------------------------------------

drop policy if exists h1_e3_t4_run_queue_delete_owner on app.run_queue;
create policy h1_e3_t4_run_queue_delete_owner
on app.run_queue
for delete
to authenticated
using (app.can_access_run(run_id));

drop policy if exists h1_e3_t4_run_artifacts_insert_owner on app.run_artifacts;
create policy h1_e3_t4_run_artifacts_insert_owner
on app.run_artifacts
for insert
to authenticated
with check (app.can_access_run(run_id));

drop policy if exists h1_e3_t4_run_artifacts_update_owner on app.run_artifacts;
create policy h1_e3_t4_run_artifacts_update_owner
on app.run_artifacts
for update
to authenticated
using (app.can_access_run(run_id))
with check (app.can_access_run(run_id));

drop policy if exists h1_e3_t4_run_artifacts_delete_owner on app.run_artifacts;
create policy h1_e3_t4_run_artifacts_delete_owner
on app.run_artifacts
for delete
to authenticated
using (app.can_access_run(run_id));

-- -----------------------------------------------------------------------------
-- 4) source-files storage.objects project-owner policies
-- -----------------------------------------------------------------------------
do $$
begin
  begin
    execute 'alter table storage.objects enable row level security';

    execute 'drop policy if exists h1_e3_t4_source_files_owner_select on storage.objects';
    execute $ddl$
      create policy h1_e3_t4_source_files_owner_select on storage.objects
      for select
      to authenticated
      using (
        bucket_id = 'source-files'
        and app.is_project_owner(app.storage_object_project_id(name))
      )
    $ddl$;

    execute 'drop policy if exists h1_e3_t4_source_files_owner_insert on storage.objects';
    execute $ddl$
      create policy h1_e3_t4_source_files_owner_insert on storage.objects
      for insert
      to authenticated
      with check (
        bucket_id = 'source-files'
        and app.is_project_owner(app.storage_object_project_id(name))
      )
    $ddl$;

    execute 'drop policy if exists h1_e3_t4_source_files_owner_update on storage.objects';
    execute $ddl$
      create policy h1_e3_t4_source_files_owner_update on storage.objects
      for update
      to authenticated
      using (
        bucket_id = 'source-files'
        and app.is_project_owner(app.storage_object_project_id(name))
      )
      with check (
        bucket_id = 'source-files'
        and app.is_project_owner(app.storage_object_project_id(name))
      )
    $ddl$;

    execute 'drop policy if exists h1_e3_t4_source_files_owner_delete on storage.objects';
    execute $ddl$
      create policy h1_e3_t4_source_files_owner_delete on storage.objects
      for delete
      to authenticated
      using (
        bucket_id = 'source-files'
        and app.is_project_owner(app.storage_object_project_id(name))
      )
    $ddl$;
  exception
    when insufficient_privilege then
      raise notice
        'h1_e3_t4 storage.objects policy rollout skipped (insufficient_privilege): %',
        sqlerrm;
  end;
end;
$$;
