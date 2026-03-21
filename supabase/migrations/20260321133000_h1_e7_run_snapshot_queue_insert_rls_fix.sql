-- H1-E7 closure hardening: allow authenticated project owners to create
-- snapshot-first run rows (snapshot + queue) via API.

alter table app.nesting_run_snapshots enable row level security;
alter table app.run_queue enable row level security;

drop policy if exists h1_e7_nesting_run_snapshots_insert_owner on app.nesting_run_snapshots;
create policy h1_e7_nesting_run_snapshots_insert_owner
on app.nesting_run_snapshots
for insert
to authenticated
with check (
  app.can_access_run(run_id)
  and (created_by is null or created_by = app.current_user_id())
);

drop policy if exists h1_e7_run_queue_insert_owner on app.run_queue;
create policy h1_e7_run_queue_insert_owner
on app.run_queue
for insert
to authenticated
with check (app.can_access_run(run_id));
