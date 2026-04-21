-- DXF Prefilter E3-T1: minimális preflight persistence + artifact storage truth.
-- Scope: app.preflight_runs, app.preflight_diagnostics, app.preflight_artifacts
--        + owner-scoped RLS policies.
-- Non-scope: dxf_rules_profiles/versions domain (rules_profile_snapshot_jsonb is used instead),
--            preflight_review_decisions, artifact list/url route, geometry import gate,
--            upload trigger, frontend UI, worker queue.
--
-- Indok a rules_profile_snapshot_jsonb megoldásra:
--   A rules-profile domain (dxf_rules_profiles / dxf_rules_profile_versions) current-code
--   szinten még nem létezik. Az E3-T1 nem épülhet hard FK-ként nem létező táblákra.
--   A V1 truth JSONB snapshot-ot tárol; a formal FK extension egy later task scope-ja.

-- ---------------------------------------------------------------------------
-- app.preflight_runs
-- ---------------------------------------------------------------------------

create table if not exists app.preflight_runs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references app.projects(id) on delete cascade,
  source_file_object_id uuid not null references app.file_objects(id) on delete restrict,
  run_seq integer not null default 1 check (run_seq > 0),
  run_status text not null default 'preflight_complete'
    check (run_status in (
      'preflight_running',
      'preflight_complete',
      'preflight_failed'
    )),
  acceptance_outcome text
    check (acceptance_outcome in (
      'accepted_for_import',
      'preflight_review_required',
      'preflight_rejected',
      null
    )),
  rules_profile_snapshot_jsonb jsonb not null default '{}'::jsonb,
  summary_jsonb jsonb not null default '{}'::jsonb,
  source_hash_sha256 text,
  normalized_hash_sha256 text,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists idx_preflight_runs_project_id
  on app.preflight_runs(project_id, created_at desc, id desc);

create index if not exists idx_preflight_runs_source_file_object_id
  on app.preflight_runs(source_file_object_id, run_seq desc);

create index if not exists idx_preflight_runs_acceptance_outcome
  on app.preflight_runs(acceptance_outcome) where acceptance_outcome is not null;

alter table app.preflight_runs enable row level security;

drop policy if exists dxf_e3_t1_preflight_runs_select_owner on app.preflight_runs;
create policy dxf_e3_t1_preflight_runs_select_owner
on app.preflight_runs
for select
to authenticated
using (app.is_project_owner(project_id));

drop policy if exists dxf_e3_t1_preflight_runs_insert_owner on app.preflight_runs;
create policy dxf_e3_t1_preflight_runs_insert_owner
on app.preflight_runs
for insert
to authenticated
with check (app.is_project_owner(project_id));

drop policy if exists dxf_e3_t1_preflight_runs_update_owner on app.preflight_runs;
create policy dxf_e3_t1_preflight_runs_update_owner
on app.preflight_runs
for update
to authenticated
using (app.is_project_owner(project_id))
with check (app.is_project_owner(project_id));

-- ---------------------------------------------------------------------------
-- app.preflight_diagnostics
-- ---------------------------------------------------------------------------

create table if not exists app.preflight_diagnostics (
  id uuid primary key default gen_random_uuid(),
  preflight_run_id uuid not null references app.preflight_runs(id) on delete cascade,
  diagnostic_seq integer not null check (diagnostic_seq >= 0),
  severity text not null
    check (severity in ('blocking', 'review_required', 'warning', 'info')),
  code text not null,
  message text not null default '',
  source text not null default '',
  family text not null default '',
  details_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  constraint uq_preflight_diagnostics_run_seq unique (preflight_run_id, diagnostic_seq)
);

create index if not exists idx_preflight_diagnostics_run_id_seq
  on app.preflight_diagnostics(preflight_run_id, diagnostic_seq asc);

create index if not exists idx_preflight_diagnostics_severity
  on app.preflight_diagnostics(preflight_run_id, severity);

alter table app.preflight_diagnostics enable row level security;

drop policy if exists dxf_e3_t1_preflight_diagnostics_select_owner on app.preflight_diagnostics;
create policy dxf_e3_t1_preflight_diagnostics_select_owner
on app.preflight_diagnostics
for select
to authenticated
using (
  exists (
    select 1
    from app.preflight_runs pr
    where pr.id = preflight_diagnostics.preflight_run_id
      and app.is_project_owner(pr.project_id)
  )
);

drop policy if exists dxf_e3_t1_preflight_diagnostics_insert_owner on app.preflight_diagnostics;
create policy dxf_e3_t1_preflight_diagnostics_insert_owner
on app.preflight_diagnostics
for insert
to authenticated
with check (
  exists (
    select 1
    from app.preflight_runs pr
    where pr.id = preflight_diagnostics.preflight_run_id
      and app.is_project_owner(pr.project_id)
  )
);

-- ---------------------------------------------------------------------------
-- app.preflight_artifacts
-- ---------------------------------------------------------------------------

create table if not exists app.preflight_artifacts (
  id uuid primary key default gen_random_uuid(),
  preflight_run_id uuid not null references app.preflight_runs(id) on delete cascade,
  artifact_kind text not null
    check (artifact_kind in (
      'normalized_dxf',
      'source_input',
      'diagnostics_report',
      'other'
    )),
  storage_bucket text not null,
  storage_path text not null,
  artifact_hash_sha256 text not null,
  content_type text not null default 'application/octet-stream',
  size_bytes bigint not null check (size_bytes >= 0),
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  constraint uq_preflight_artifacts_run_kind unique (preflight_run_id, artifact_kind)
);

create index if not exists idx_preflight_artifacts_run_id
  on app.preflight_artifacts(preflight_run_id, artifact_kind);

create index if not exists idx_preflight_artifacts_storage
  on app.preflight_artifacts(storage_bucket, storage_path);

alter table app.preflight_artifacts enable row level security;

drop policy if exists dxf_e3_t1_preflight_artifacts_select_owner on app.preflight_artifacts;
create policy dxf_e3_t1_preflight_artifacts_select_owner
on app.preflight_artifacts
for select
to authenticated
using (
  exists (
    select 1
    from app.preflight_runs pr
    where pr.id = preflight_artifacts.preflight_run_id
      and app.is_project_owner(pr.project_id)
  )
);

drop policy if exists dxf_e3_t1_preflight_artifacts_insert_owner on app.preflight_artifacts;
create policy dxf_e3_t1_preflight_artifacts_insert_owner
on app.preflight_artifacts
for insert
to authenticated
with check (
  exists (
    select 1
    from app.preflight_runs pr
    where pr.id = preflight_artifacts.preflight_run_id
      and app.is_project_owner(pr.project_id)
  )
);
