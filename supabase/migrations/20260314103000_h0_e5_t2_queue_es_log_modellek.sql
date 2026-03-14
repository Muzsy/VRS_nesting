-- H0-E5-T2 queue + log base migration
-- Scope intentionally limited to queue-state and append-only log foundations.

alter table app.nesting_run_snapshots
  drop constraint if exists uq_nesting_run_snapshots_run_id_id;

alter table app.nesting_run_snapshots
  add constraint uq_nesting_run_snapshots_run_id_id
  unique (run_id, id);

create table if not exists app.run_queue (
  run_id uuid primary key references app.nesting_runs(id) on delete cascade,
  snapshot_id uuid not null unique,
  queue_state text not null default 'pending',
  attempt_no integer not null default 0,
  attempt_status app.run_attempt_status,
  priority integer not null default 100,
  available_at timestamptz not null default now(),
  leased_by text,
  lease_token uuid,
  leased_at timestamptz,
  lease_expires_at timestamptz,
  heartbeat_at timestamptz,
  started_at timestamptz,
  finished_at timestamptz,
  last_error_code text,
  last_error_message text,
  retry_count integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (queue_state in ('pending', 'leased', 'done', 'error', 'cancel_requested', 'cancelled')),
  check (attempt_no >= 0),
  check (retry_count >= 0),
  check (leased_by is null or length(btrim(leased_by)) > 0),
  check (
    queue_state <> 'leased'
    or (lease_token is not null and lease_expires_at is not null)
  )
);

alter table app.run_queue
  drop constraint if exists fk_run_queue_snapshot_same_run;

alter table app.run_queue
  add constraint fk_run_queue_snapshot_same_run
  foreign key (run_id, snapshot_id)
  references app.nesting_run_snapshots(run_id, id)
  on delete cascade;

create index if not exists idx_run_queue_state_available_at
  on app.run_queue(queue_state, available_at);

create index if not exists idx_run_queue_lease_expires_at
  on app.run_queue(lease_expires_at);

drop trigger if exists trg_run_queue_set_updated_at on app.run_queue;
create trigger trg_run_queue_set_updated_at
before update on app.run_queue
for each row execute function app.set_updated_at();

create table if not exists app.run_logs (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  snapshot_id uuid references app.nesting_run_snapshots(id) on delete set null,
  attempt_no integer not null default 0,
  log_level text not null,
  log_kind text not null,
  message text not null,
  payload_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (attempt_no >= 0),
  check (length(btrim(log_level)) > 0),
  check (length(btrim(log_kind)) > 0),
  check (length(btrim(message)) > 0)
);

create index if not exists idx_run_logs_run_id_created_at
  on app.run_logs(run_id, created_at);

create index if not exists idx_run_logs_snapshot_id_created_at
  on app.run_logs(snapshot_id, created_at);

-- NOTE:
-- This migration intentionally does not create a dedicated run_attempts table.
-- This migration intentionally does not create result/artifact/projection tables.
-- RLS policies remain intentionally out of scope.
