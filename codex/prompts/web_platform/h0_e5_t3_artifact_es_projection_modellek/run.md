# DXF Nesting Platform Codex Task - H0-E5-T3 artifact es projection modellek
TASK_SLUG: h0_e5_t3_artifact_es_projection_modellek

Olvasd el:
- AGENTS.md
- canvases/web_platform/h0_e5_t3_artifact_es_projection_modellek.md
- codex/goals/canvases/web_platform/fill_canvas_h0_e5_t3_artifact_es_projection_modellek.yaml
- docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md
- docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md
- docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md
- supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql
- supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql
- supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez schema-task, de a scope kontrollalt:
  most csak az `app.run_artifacts`, `app.run_layout_sheets`,
  `app.run_layout_placements`, `app.run_layout_unplaced`, `app.run_metrics`
  tablavilag johet letre.
- Kulon `app.run_results` tabla most nem johet letre.
- Storage policy / RLS / worker implementacio nincs scope-ban.
- Ne moditsd a `api/sql/phase1_schema.sql` legacy bootstrap fajlt.
- A mar meglevo migraciokat ne ird at; uj migracioban folytasd a sort.

Modellezesi elvek:
- `app` schema a canonical celterulet.
- Az `app.run_artifacts` file/blob jellegu output reteg.
- Az `app.run_layout_*` query-zheto projection reteg.
- Az `app.run_metrics` a run-level osszegzett eredmeny reteg.
- H0-E5-T3-ban nincs kulon `app.run_results` tabla.
- A projection es az artifact ne mosodjon ossze egy tablaba.
- Az artifact tabla az `app.artifact_kind` enumot hasznalja.
- A projection tablavilag runhoz kotott marad.
- A storage bucket strategy kulon H0-E6-T1 task marad.
- Az RLS kulon H0-E6-T2 task marad.

Kulon figyelj:
- ne hozz letre `run_results`, `run_attempts`, `run_queue`, `run_logs` vagy egyeb uj,
  T3-on tuli tablakat;
- ne keruljon bele storage bucket policy vagy RLS policy;
- a docsban egyertelmu legyen, hogy a T3 fizikai outputja
  `run_artifacts` + `run_layout_*` + `run_metrics`;
- ahol a T3-kozelben meg stale `public.run_layout_*` vagy `public.run_metrics`
  schema-prefix maradt, azt minimalisan igazitsd az `app.*` iranyhoz;
- a stale `run_results` emlitest a T3 canonical modellhez igazitsd;
- a report kulon nevezze meg, hogy a fogalmi eredmeny H0-ban miert nem kulon
  `run_results` tablaban jelenik meg.

A reportban kulon nevezd meg:
- az `app.run_artifacts` vegleges oszlopait;
- az `app.run_layout_sheets` vegleges oszlopait;
- az `app.run_layout_placements` vegleges oszlopait;
- az `app.run_layout_unplaced` vegleges oszlopait;
- az `app.run_metrics` vegleges oszlopait;
- az `app.artifact_kind` enum hasznalatot;
- hogy az artifact es projection reteg fizikailag kulon marad;
- hogy mi maradt szandekosan out-of-scope.

A vegen futtasd a standard gate-et:
- ./scripts/verify.sh --report codex/reports/web_platform/h0_e5_t3_artifact_es_projection_modellek.md

Ez frissitse:
- codex/reports/web_platform/h0_e5_t3_artifact_es_projection_modellek.md
- codex/reports/web_platform/h0_e5_t3_artifact_es_projection_modellek.verify.log

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
