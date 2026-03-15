# DXF Nesting Platform Codex Task - H0-E7-T1 H0 end-to-end struktura audit
TASK_SLUG: h0_e7_t1_h0_end_to_end_struktura_audit

Olvasd el:
- AGENTS.md
- canvases/web_platform/h0_e7_t1_h0_end_to_end_struktura_audit.md
- codex/goals/canvases/web_platform/fill_canvas_h0_e7_t1_h0_end_to_end_struktura_audit.yaml
- docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md
- docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md
- docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md
- docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md
- docs/web_platform/architecture/h0_security_rls_alapok.md
- docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md
- docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md
- docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md
- supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql
- supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql
- supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql
- supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql
- supabase/migrations/20260310240000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql
- supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql
- supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql
- supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql
- supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql
- supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql
- supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql
- supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql
- supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez audit/closure task, nem feature-task.
- Uj domain tabla vagy uj feature most nem johet letre.
- Uj migracio csak akkor johetne letre, ha kritikus, kozvetlen H0-zaro inkonzisztencia miatt elkerulhetetlen lenne,
  de alapertelmezetten ne hozz letre uj migraciot.
- Ne moditsd a `api/sql/phase1_schema.sql` legacy bootstrap fajlt.

Modellezesi elvek:
- A cel a H0 lezarhatóságának bizonyítása vagy őszinte cáfolata.
- A H0 gate verdict csak evidence alapon mondhato ki.
- A kisebb, nem blokkoló eltérések advisory kategóriában maradhatnak.
- A H1 csak akkor indulhat tisztán, ha a verdict `PASS` vagy `PASS WITH ADVISORIES`.
- A task tree, a source-of-truth docs és a tényleges migrációk egymással konzisztens képet kell adjanak.

Kulon figyelj:
- keszits completion matrixot a teljes H0-ra;
- kulon valaszd szet a blokkolo es advisory eltéréseket;
- ahol a docsban maradt kisebb stale naming vagy allapotmaradvany, azt minimalisan tisztitsd ki;
- ne csuszd at altalanos docs-refaktorba;
- ne szepitsd PASS-ra, ha valami valojaban meg blokkolna a H1-et.

A reportban kulon nevezd meg:
- a H0 completion matrix roviditett eredmenyet;
- a blokkolo vs advisory eltéréseket;
- a H1 entry gate vegso iteletet;
- a javitott docs-konzisztencia pontokat;
- hogy mi maradt szandekosan out-of-scope.

A vegen futtasd a standard gate-et:
- ./scripts/verify.sh --report codex/reports/web_platform/h0_e7_t1_h0_end_to_end_struktura_audit.md

Ez frissitse:
- codex/reports/web_platform/h0_e7_t1_h0_end_to_end_struktura_audit.md
- codex/reports/web_platform/h0_e7_t1_h0_end_to_end_struktura_audit.verify.log

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
