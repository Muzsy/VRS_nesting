-- H0-E3-T3 geometry audit/review base migration: validation reports + review actions
-- Scope intentionally limited to audit/report and human review layers.

create table if not exists app.geometry_validation_reports (
  id uuid primary key default gen_random_uuid(),
  geometry_revision_id uuid not null references app.geometry_revisions(id) on delete cascade,
  validation_seq integer not null,
  status app.geometry_validation_status not null,
  validator_version text not null,
  summary_jsonb jsonb,
  report_jsonb jsonb not null,
  source_hash_sha256 text,
  created_at timestamptz not null default now(),
  unique (geometry_revision_id, validation_seq),
  check (validation_seq > 0),
  check (length(btrim(validator_version)) > 0)
);

alter table app.geometry_validation_reports
  drop constraint if exists uq_geometry_validation_reports_geometry_revision_id_id;

alter table app.geometry_validation_reports
  add constraint uq_geometry_validation_reports_geometry_revision_id_id
  unique (geometry_revision_id, id);

create index if not exists idx_geometry_validation_reports_geometry_revision_id
  on app.geometry_validation_reports(geometry_revision_id);

create index if not exists idx_geometry_validation_reports_status
  on app.geometry_validation_reports(status);

create table if not exists app.geometry_review_actions (
  id uuid primary key default gen_random_uuid(),
  geometry_revision_id uuid not null references app.geometry_revisions(id) on delete cascade,
  validation_report_id uuid,
  action_kind text not null,
  actor_user_id uuid references app.profiles(id) on delete set null,
  note text,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (action_kind in ('approve', 'reject', 'request_changes', 'comment'))
);

alter table app.geometry_review_actions
  drop constraint if exists fk_geometry_review_actions_validation_report_same_geometry;

alter table app.geometry_review_actions
  add constraint fk_geometry_review_actions_validation_report_same_geometry
  foreign key (geometry_revision_id, validation_report_id)
  references app.geometry_validation_reports(geometry_revision_id, id)
  on delete restrict;

create index if not exists idx_geometry_review_actions_geometry_revision_id
  on app.geometry_review_actions(geometry_revision_id);

create index if not exists idx_geometry_review_actions_actor_user_id
  on app.geometry_review_actions(actor_user_id);

create index if not exists idx_geometry_review_actions_validation_report_id
  on app.geometry_review_actions(validation_report_id);

-- NOTE:
-- This migration intentionally does not create geometry_derivatives,
-- part/sheet binding, run, or export domain tables.
-- RLS policies remain intentionally out of scope.
