# DXF Nesting Platform Codex Task - H0-E5-T1 nesting run es snapshot modellek
TASK_SLUG: h0_e5_t1_nesting_run_es_snapshot_modellek

Olvasd el:
- AGENTS.md
- canvases/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek.md
- codex/goals/canvases/web_platform/fill_canvas_h0_e5_t1_nesting_run_es_snapshot_modellek.yaml
- docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md
- docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md
- docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md
- supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql
- supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql
- supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql
- supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql
- supabase/migrations/20260310240000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql
- supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql
- supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql
- supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql
- supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez schema-task, de a scope kontrollalt:
  most csak az `app.nesting_runs` es `app.nesting_run_snapshots` tablavilag johet letre.
- Queue / attempt / log / result / artifact / projection tablakat most nem szabad letrehozni.
- Ne moditsd a `api/sql/phase1_schema.sql` legacy bootstrap fajlt.
- A mar meglevo migraciokat ne ird at; uj migracioban folytasd a sort.

Modellezesi elvek:
- `app` schema a canonical celterulet.
- A `nesting_runs` H0-ban a fogalmi Run Request aggregate fizikai taroloja.
- A `nesting_run_snapshots` H0-ban a fogalmi Run Snapshot immutable truth fizikai taroloja.
- A run es a snapshot ne olvadjon ossze egyetlen tablava.
- A run tabla az `app.run_request_status` enumot hasznalja.
- A snapshot tabla az `app.run_snapshot_status` enumot hasznalja.
- A snapshot append-only szemantikaju legyen; emiatt ne kapjon `updated_at` mezot.
- A queue / attempt / result / artifact / projection vilag kulon H0-E5-T2/T3 task marad.

Kulon figyelj:
- ne hozz letre `run_queue`, `run_logs`, `run_results`, `run_artifacts`,
  `run_layout_sheets`, `run_layout_placements`, `run_layout_unplaced`, `run_metrics` tablat;
- ne keruljon bele RLS policy;
- a docsban a fogalmi Run Request / Run Snapshot es a fizikai
  `app.nesting_runs` / `app.nesting_run_snapshots` viszony legyen egyertelmu;
- a stale `public.*` / `run_status` jellegu run-szakaszokat minimalisan szinkronizald
  az `app.*` + `app.run_request_status` / `app.run_snapshot_status` iranyhoz;
- a report kulon nevezze meg a request-oldali metadata mezoket, a snapshot hash-et
  es a strukturalt manifest blokkokat.

A reportban kulon nevezd meg:
- az `app.nesting_runs` vegleges oszlopait;
- az `app.nesting_run_snapshots` vegleges oszlopait;
- a PK/FK kapcsolatokat;
- az enum hasznalatot;
- a snapshot hash es payload/manifest mezoket;
- hogy a snapshot append-only szemantikaju;
- hogy mi maradt szandekosan out-of-scope.

A vegen futtasd a standard gate-et:
- ./scripts/verify.sh --report codex/reports/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek.md

Ez frissitse:
- codex/reports/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek.md
- codex/reports/web_platform/h0_e5_t1_nesting_run_es_snapshot_modellek.verify.log

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
