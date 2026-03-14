# DXF Nesting Platform Codex Task - H0-E5-T2 queue es log modellek
TASK_SLUG: h0_e5_t2_queue_es_log_modellek

Olvasd el:
- AGENTS.md
- canvases/web_platform/h0_e5_t2_queue_es_log_modellek.md
- codex/goals/canvases/web_platform/fill_canvas_h0_e5_t2_queue_es_log_modellek.yaml
- docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md
- docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md
- docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md
- supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql
- supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez schema-task, de a scope kontrollalt:
  most csak az `app.run_queue` es `app.run_logs` tablavilag johet letre.
- Kulon `run_attempts` tabla most nem johet letre.
- Result / artifact / projection es RLS vilag nincs scope-ban.
- Ne moditsd a `api/sql/phase1_schema.sql` legacy bootstrap fajlt.
- A mar meglevo migraciokat ne ird at; uj migracioban folytasd a sort.

Modellezesi elvek:
- `app` schema a canonical celterulet.
- A `nesting_runs` marad a Run Request aggregate fizikai taroloja.
- A `nesting_run_snapshots` marad a Run Snapshot immutable truth fizikai taroloja.
- A H0-E5-T2 fizikai outputja a backlog szerint `run_queue` es `run_logs`.
- A fogalmi attempt/lease vilag ebben a taskban a `run_queue` rekordban jelenjen meg,
  ne kulon tablaban.
- A `attempt_status` az `app.run_attempt_status` enumot hasznalja.
- A queue-level allapot explicit legyen (pl. `pending`, `leased`, `done`, `error`,
  `cancel_requested`, `cancelled`).
- A `run_logs` append-only audit/log reteg.
- A result / artifact / projection vilag kulon H0-E5-T3 task marad.

Kulon figyelj:
- ne hozz letre `run_attempts`, `run_results`, `run_artifacts`, `run_layout_sheets`,
  `run_layout_placements`, `run_layout_unplaced`, `run_metrics` tablat;
- ne keruljon bele RLS policy;
- a queue kapcsolodjon a T1-ben letett run + snapshot vilaghoz;
- a docsban egyertelmu legyen, hogy a fogalmi attempt T2-ben a queue sorban el,
  es nem kulon tablaban;
- ahol a kozeli run-vilag blokkokban meg stale `public.nesting_runs` vagy
  `public.nesting_run_snapshots` schema-prefix maradt, azt csak akkor es annyiban
  igazitsd, amennyiben ez nem noveli meg a blast radiusat es segiti a T2 source-of-truth
  tisztasagat.

A reportban kulon nevezd meg:
- az `app.run_queue` vegleges oszlopait;
- az `app.run_logs` vegleges oszlopait;
- a PK/FK kapcsolatokat;
- a `queue_state` es `attempt_status` szerepkoret;
- a lease/heartbeat/retry mezoket;
- hogy a `run_logs` append-only;
- hogy mi maradt szandekosan out-of-scope.

A vegen futtasd a standard gate-et:
- ./scripts/verify.sh --report codex/reports/web_platform/h0_e5_t2_queue_es_log_modellek.md

Ez frissitse:
- codex/reports/web_platform/h0_e5_t2_queue_es_log_modellek.md
- codex/reports/web_platform/h0_e5_t2_queue_es_log_modellek.verify.log

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
