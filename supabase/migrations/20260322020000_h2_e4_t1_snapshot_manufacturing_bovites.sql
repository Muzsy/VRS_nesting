-- H2-E4-T1: snapshot manufacturing bovites
-- Scope: add includes_manufacturing and includes_postprocess meta columns
-- to app.nesting_run_snapshots. Does NOT introduce manufacturing plan,
-- postprocessor domain, or resolver tables.

alter table app.nesting_run_snapshots
  add column if not exists includes_manufacturing boolean not null default false,
  add column if not exists includes_postprocess boolean not null default false;
