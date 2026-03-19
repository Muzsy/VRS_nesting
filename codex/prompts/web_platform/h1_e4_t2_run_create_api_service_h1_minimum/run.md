# DXF Nesting Platform Codex Task - H1-E4-T2 Run create API/service (H1 minimum)
TASK_SLUG: h1_e4_t2_run_create_api_service_h1_minimum

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql`
- `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql`
- `api/services/run_snapshot_builder.py`
- `api/routes/runs.py`
- `api/sql/phase4_run_quota_atomic.sql`
- `canvases/web_platform/h1_e4_t2_run_create_api_service_h1_minimum.md`
- `codex/goals/canvases/web_platform/fill_canvas_h1_e4_t2_run_create_api_service_h1_minimum.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ne talalj ki nem letezo schema-t vagy API-konvenciot: a H0/H1 docsbol,
  migraciokbol es a meglevo route/service mintakbol indulj ki.
- Ez a task H1 minimum **run create** scope: ne csussz at worker lease,
  solver futtatas, result normalizer, layout/projection vagy artifact scope-ba.
- A canonical run create flow a H1-E4-T1 `build_run_snapshot_payload(...)`
  builderre epuljon.
- A canonical tablavilag: `app.nesting_runs`, `app.nesting_run_snapshots`,
  `app.run_queue`.
- A letezo `api/routes/runs.py` file-ban csak a create agat igazitsd a H1
  minimum truth-hoz; a list/log/artifact reszeket ne terjeszd tul.
- A legacy `api/sql/phase4_run_quota_atomic.sql` helper referencia maradhat,
  de ne az legyen a H0/H1 source-of-truth megoldas.
- Az idempotencia / dedup kezeles legyen explicit: a `snapshot_hash_sha256`
  unique truth miatt a service ne nyers DB hibaval alljon meg.

Implementacios elvarasok:
- Vezess be explicit `api/services/run_creation.py` service-t.
- A service projekt owner guard utan hivja a H1-E4-T1 snapshot buildert.
- Sikeres create eseten jojjon letre:
  - `app.nesting_runs` rekord,
  - `app.nesting_run_snapshots` rekord `status='ready'` allapottal,
  - `app.run_queue` rekord `queue_state='pending'` allapottal.
- A final response queued run legyen.
- A request contract maradjon H1 minimum, project truth alapu; ne huzd vissza a
  taskot a legacy inline `run_config` / `parts_config` vilagba.
- Dokumentald pontosan, hogy a T2 milyen idempotencia / dedup szemantikat
  valosit meg.
- Keszits task-specifikus smoke scriptet a sikeres es hibas agakra.
- Ha kiderul valos schema/runtime fuggoseg vagy kompromisszum, azt a reportban
  expliciten nevezd meg. Ne fedd el.

A reportban kulon nevezd meg:
- hogy a task mit szallit le a H1 minimum run create scope-ban;
- hogy mit NEM szallit le meg (lease, worker, solver, result, artifact);
- hogyan kezeli a snapshot hash unique + idempotencia helyzetet;
- miert nem a legacy quota helper a canonical H1 megoldas.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e4_t2_run_create_api_service_h1_minimum.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
