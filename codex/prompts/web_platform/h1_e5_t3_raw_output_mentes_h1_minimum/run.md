# DXF Nesting Platform Codex Task - H1-E5-T3 Raw output mentes (H1 minimum)
TASK_SLUG: h1_e5_t3_raw_output_mentes_h1_minimum

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md`
- `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
- `supabase/migrations/20260318233000_worker_lifecycle_artifact_idempotency_guard.sql`
- `worker/main.py`
- `worker/queue_lease.py`
- `worker/engine_adapter_input.py`
- `vrs_nesting/runner/vrs_solver_runner.py`
- `canvases/web_platform/h1_e5_t3_raw_output_mentes_h1_minimum.md`
- `codex/goals/canvases/web_platform/fill_canvas_h1_e5_t3_raw_output_mentes_h1_minimum.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ne talalj ki nem letezo schema-t, enumot vagy artifact kindot: a H0
  migraciokbol es a web_platform source-of-truth doksikbol indulj ki.
- Ez a task H1 minimum **raw output mentes** scope: ne csussz at result
  normalizer, projection, viewer SVG/DXF vagy export pipeline iranyba.
- A canonical storage bucket/path a H0 policy legyen:
  `run-artifacts` + `projects/{project_id}/runs/{run_id}/{artifact_kind}/{content_hash}.{ext}`.
- Az artifact regisztracio legyen idempotens es retry-biztos.
- A helper boundary legyen explicit es tesztelheto; ne maradjon minden inline a
  workerben.

Implementacios elvarasok:
- Legyen explicit worker-oldali raw artifact persistence helper.
- A solver stdout/stderr/raw result/run-log/runner-meta tarolasa a canonical
  run-artifact vilagra alljon at.
- A task pontosan nevezze meg, mely raw artifactok garantaltak success/failure/
  timeout/cancel esetben.
- A worker ne menjen hamis success-be csak azert, mert raw artifact upload tortent
  vagy nem tortent meg.
- A task-specifikus smoke fake upload/client boundaryval bizonyitsa a canonical
  pathot, az artifact tipus mappinget es az idempotens hash/path kepzest.

A reportban kulon nevezd meg:
- hogyan keletkezik a canonical raw artifact storage path;
- mely fajlok minosulnek H1 minimum raw output evidence-nek;
- hogyan maradnak visszakereshetok a hibak es eredmenyek;
- mit NEM vallal meg a task (result normalizer, projection, viewer/export).

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e5_t3_raw_output_mentes_h1_minimum.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
