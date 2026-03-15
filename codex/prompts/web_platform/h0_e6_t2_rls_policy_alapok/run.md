# DXF Nesting Platform Codex Task - H0-E6-T2 RLS policy alapok
TASK_SLUG: h0_e6_t2_rls_policy_alapok

Olvasd el:
- AGENTS.md
- canvases/web_platform/h0_e6_t2_rls_policy_alapok.md
- codex/goals/canvases/web_platform/fill_canvas_h0_e6_t2_rls_policy_alapok.yaml
- docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md
- docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md
- docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md
- docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md
- docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md
- docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md
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

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez security/schema task: most jon letre az alap RLS migracio.
- Ne moditsd a mar meglevo korabbi migraciokat; uj migracioban folytasd a sort.
- Ne moditsd a `api/sql/phase1_schema.sql` legacy bootstrap fajlt.
- Auth auto-provisioning trigger most nem johet letre.
- Worker vagy API implementacio most nem johet letre.
- Bucket provisioning script most nem johet letre.

Modellezesi elvek:
- `anon` uzleti tablakat ne lathasson.
- `authenticated` user csak sajat project- es owner-bound adatot lathasson.
- `technology_presets` H0-ban authenticated read-only.
- `nesting_runs` user-oldalon owner-controlled lehet.
- `nesting_run_snapshots` es az output tablavilag (`run_queue`, `run_logs`,
  `run_artifacts`, `run_layout_*`, `run_metrics`) user-oldalon read-only maradjon.
- A worker/output irasi oldal service-role boundary maradjon.
- A storage policy a H0-E6-T1 bucket/path szerzodesre epuljon:
  `source-files`, `geometry-artifacts`, `run-artifacts`.
- A `geometry_derivatives` vedelme DB-RLS alapu; ne probald storage path policyval
  helyettesiteni.

Kulon figyelj:
- a policyk ne legyenek tul szelesek;
- a policyk ne torjek el a normal owner-flowt;
- ha helper fuggvenyeket hozol letre, legyenek kicsik es attekinthetoek;
- `storage.objects` policy a `projects/{project_id}/...` prefix logikara epuljon;
- `source-files` esetben H0-ban megengedheto a sajat projekt-pathra iras;
- `geometry-artifacts` es `run-artifacts` user-oldalon legalabb read-only maradjon;
- a docsban legyen egyertelmu tablankenti access matrix es service-role boundary.

A reportban kulon nevezd meg:
- a vegleges helper fuggvenyeket (ha lettek);
- a tablankenti access matrixot;
- mely tablakat irhat a user es melyek read-only-k user oldalon;
- a `technology_presets` read-only szabalyat;
- a `storage.objects` policy fo szabalyat;
- a service-role boundaryt;
- hogy mi maradt szandekosan out-of-scope.

A vegen futtasd a standard gate-et:
- ./scripts/verify.sh --report codex/reports/web_platform/h0_e6_t2_rls_policy_alapok.md

Ez frissitse:
- codex/reports/web_platform/h0_e6_t2_rls_policy_alapok.md
- codex/reports/web_platform/h0_e6_t2_rls_policy_alapok.verify.log

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
