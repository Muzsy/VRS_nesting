-- Phase 1 RLS policy bootstrap (owner-scoped MVP)

alter table users enable row level security;
alter table projects enable row level security;
alter table project_files enable row level security;
alter table run_configs enable row level security;
alter table runs enable row level security;
alter table run_artifacts enable row level security;
alter table run_queue enable row level security;

-- users: each user can see/update own profile row
drop policy if exists users_self_select on users;
create policy users_self_select on users
  for select using (id = auth.uid());
drop policy if exists users_self_update on users;
create policy users_self_update on users
  for update using (id = auth.uid()) with check (id = auth.uid());

-- projects: owner scoped
drop policy if exists projects_owner_all on projects;
create policy projects_owner_all on projects
  for all using (owner_id = auth.uid()) with check (owner_id = auth.uid());

-- project_files: accessible through owned project
drop policy if exists project_files_owner_all on project_files;
create policy project_files_owner_all on project_files
  for all using (
    project_id in (select p.id from projects p where p.owner_id = auth.uid())
  )
  with check (
    project_id in (select p.id from projects p where p.owner_id = auth.uid())
  );

-- run_configs: accessible through owned project
drop policy if exists run_configs_owner_all on run_configs;
create policy run_configs_owner_all on run_configs
  for all using (
    project_id in (select p.id from projects p where p.owner_id = auth.uid())
  )
  with check (
    project_id in (select p.id from projects p where p.owner_id = auth.uid())
  );

-- runs: accessible through owned project
drop policy if exists runs_owner_all on runs;
create policy runs_owner_all on runs
  for all using (
    project_id in (select p.id from projects p where p.owner_id = auth.uid())
  )
  with check (
    project_id in (select p.id from projects p where p.owner_id = auth.uid())
  );

-- run_artifacts: accessible through runs -> projects owner
drop policy if exists run_artifacts_owner_all on run_artifacts;
create policy run_artifacts_owner_all on run_artifacts
  for all using (
    run_id in (
      select r.id
      from runs r
      join projects p on p.id = r.project_id
      where p.owner_id = auth.uid()
    )
  )
  with check (
    run_id in (
      select r.id
      from runs r
      join projects p on p.id = r.project_id
      where p.owner_id = auth.uid()
    )
  );

-- run_queue: worker queue rows tied to owned runs
drop policy if exists run_queue_owner_all on run_queue;
create policy run_queue_owner_all on run_queue
  for all using (
    run_id in (
      select r.id
      from runs r
      join projects p on p.id = r.project_id
      where p.owner_id = auth.uid()
    )
  )
  with check (
    run_id in (
      select r.id
      from runs r
      join projects p on p.id = r.project_id
      where p.owner_id = auth.uid()
    )
  );
