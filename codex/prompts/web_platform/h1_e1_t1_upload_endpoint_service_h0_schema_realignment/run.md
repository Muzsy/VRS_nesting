# DXF Nesting Platform Codex Task - H1-E1-T1 Upload endpoint/service H0 schema realignment
TASK_SLUG: h1_e1_t1_upload_endpoint_service_h0_schema_realignment

Olvasd el:
- AGENTS.md
- canvases/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.md
- codex/goals/canvases/web_platform/fill_canvas_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.yaml
- docs/web_platform/roadmap/h0_lezarasi_kriteriumok_es_h1_entry_gate.md
- docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md
- docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md
- docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md
- docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md
- docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md
- supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql
- supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql
- supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql
- api/routes/projects.py
- api/routes/files.py
- api/services/dxf_validation.py
- api/config.py
- scripts/smoke_phase1_api_auth_projects_files_validation.py

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithatsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez H1 nyito realignment task, nem teljes feature-epites.
- Ne hozz letre uj domain migraciot, ha a H0 schema elegendo a route-ok helyes bekotesere.
- Ne vezesd vissza a megoldast a legacy `project_files` / `owner_id` / `archived_at` modellre.
- Ne nyisd meg idovel elott a H1-E2 geometry pipeline-t: `geometry_revisions`, `geometry_validation_reports`,
  `geometry_derivatives` tenyleges workflow-bekotese most nem scope.
- Ne moditsd a legacy `api/sql/phase1_schema.sql` bootstrap fajlt; ez a task a mostani H0 source-of-truth-hoz igazitasrol szol.

Modellezesi elvek:
- A H0 lezarasi gate utan a file ingest a `app.projects` + `app.file_objects` truth-ra kell hogy uljon.
- A canonical source upload path: `projects/{project_id}/files/{file_object_id}/{sanitized_original_name}`.
- A source file metadata truth az `app.file_objects`; ne talalj ki legacy kompatibilitas kedveert uj, nem letezo oszlopokat.
- A projects route archiválási logikaja a H0 `lifecycle` mezore epuljon.
- A validacios helper ne irjon nem letezo `validation_status`/`validation_error` mezokbe a `file_objects` tablan.
- Ha bucket defaultot kell korrigalni, a H0-kanonikus `source-files` legyen az irany, de teljes multi-bucket config refaktor nem kell ebben a taskban.

Kulon figyelj:
- a projects CRUD es a files upload flow egyszerre legyen H0-kompatibilis;
- a smoke script ne a legacy phase1 tablakra, hanem az uj H0 truth-ra ellenorizzen;
- ne hagyj bent felerdekes mezoneveket (`owner_id`, `archived_at`, `project_files`) a route logicaban vagy response modellekben;
- a reportban nevezd meg egyertelmuen, hogy mi kerult most helyre, es mi marad H1-E1-T2 / H1-E2 tovabbi scope-ban.

A reportban kulon nevezd meg:
- a projects route H0 realignment eredmenyet;
- a files route + storage path policy realignment eredmenyet;
- a DXF validation helper minimalis H1-E1-kompatibilis allapotat;
- a smoke bizonyitekokat;
- a megmarado advisory/out-of-scope pontokat.

A vegen futtasd a standard gate-et:
- ./scripts/verify.sh --report codex/reports/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.md

Ez frissitse:
- codex/reports/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.md
- codex/reports/web_platform/h1_e1_t1_upload_endpoint_service_h0_schema_realignment.verify.log

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
