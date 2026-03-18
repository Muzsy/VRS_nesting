-- Worker lifecycle hardening: artifact idempotency guard.
-- Keep one row per (run_id, storage_path), then enforce uniqueness.

with ranked as (
  select
    id,
    row_number() over (
      partition by run_id, storage_path
      order by created_at desc, id desc
    ) as rn
  from app.run_artifacts
)
delete from app.run_artifacts ra
using ranked r
where ra.id = r.id
  and r.rn > 1;

create unique index if not exists uq_run_artifacts_run_id_storage_path
  on app.run_artifacts(run_id, storage_path);
