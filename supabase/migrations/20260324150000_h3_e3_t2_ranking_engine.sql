-- H3-E3-T2: ranking engine truth layer.
-- Scope: app.run_ranking_results + owner/project scoped RLS.
-- Non-scope: run_evaluations recalculation, comparison projection, selected-run workflows.

create table if not exists app.run_ranking_results (
  id uuid primary key default gen_random_uuid(),
  batch_id uuid not null references app.run_batches(id) on delete cascade,
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  rank_no integer not null check (rank_no > 0),
  ranking_reason_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  constraint uq_run_ranking_results_batch_run unique (batch_id, run_id),
  constraint uq_run_ranking_results_batch_rank unique (batch_id, rank_no),
  constraint fk_run_ranking_results_batch_item
    foreign key (batch_id, run_id)
    references app.run_batch_items(batch_id, run_id)
    on delete cascade
);

create index if not exists idx_run_ranking_results_batch_rank_no
  on app.run_ranking_results(batch_id, rank_no asc);

create index if not exists idx_run_ranking_results_run_id
  on app.run_ranking_results(run_id);

create index if not exists idx_run_ranking_results_created_at_desc
  on app.run_ranking_results(created_at desc, id);

alter table app.run_ranking_results enable row level security;

drop policy if exists h3_e3_t2_run_ranking_results_select_owner on app.run_ranking_results;
create policy h3_e3_t2_run_ranking_results_select_owner
on app.run_ranking_results
for select
to authenticated
using (
  exists (
    select 1
    from app.run_batches rb
    where rb.id = run_ranking_results.batch_id
      and app.is_project_owner(rb.project_id)
  )
);

drop policy if exists h3_e3_t2_run_ranking_results_insert_owner on app.run_ranking_results;
create policy h3_e3_t2_run_ranking_results_insert_owner
on app.run_ranking_results
for insert
to authenticated
with check (
  exists (
    select 1
    from app.run_batches rb
    where rb.id = run_ranking_results.batch_id
      and app.is_project_owner(rb.project_id)
  )
  and exists (
    select 1
    from app.run_batch_items rbi
    where rbi.batch_id = run_ranking_results.batch_id
      and rbi.run_id = run_ranking_results.run_id
  )
);

drop policy if exists h3_e3_t2_run_ranking_results_update_owner on app.run_ranking_results;
create policy h3_e3_t2_run_ranking_results_update_owner
on app.run_ranking_results
for update
to authenticated
using (
  exists (
    select 1
    from app.run_batches rb
    where rb.id = run_ranking_results.batch_id
      and app.is_project_owner(rb.project_id)
  )
)
with check (
  exists (
    select 1
    from app.run_batches rb
    where rb.id = run_ranking_results.batch_id
      and app.is_project_owner(rb.project_id)
  )
  and exists (
    select 1
    from app.run_batch_items rbi
    where rbi.batch_id = run_ranking_results.batch_id
      and rbi.run_id = run_ranking_results.run_id
  )
);

drop policy if exists h3_e3_t2_run_ranking_results_delete_owner on app.run_ranking_results;
create policy h3_e3_t2_run_ranking_results_delete_owner
on app.run_ranking_results
for delete
to authenticated
using (
  exists (
    select 1
    from app.run_batches rb
    where rb.id = run_ranking_results.batch_id
      and app.is_project_owner(rb.project_id)
  )
);
