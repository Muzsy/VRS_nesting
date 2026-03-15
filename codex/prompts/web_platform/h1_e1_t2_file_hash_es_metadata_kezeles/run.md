# DXF Nesting Platform Codex Task - H1-E1-T2 File hash és metadata kezelés
TASK_SLUG: h1_e1_t2_file_hash_es_metadata_kezeles

Olvasd el:
- AGENTS.md
- canvases/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles.md
- codex/goals/canvases/web_platform/fill_canvas_h1_e1_t2_file_hash_es_metadata_kezeles.yaml
- docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md
- docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md
- docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md
- supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql
- api/routes/files.py
- api/services/dxf_validation.py
- api/supabase_client.py
- api/config.py
- scripts/smoke_h1_e1_t1_upload_endpoint_service_h0_schema_realignment.py

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithatsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez H1 ingest metadata-hardening task, nem geometry pipeline task.
- Ne hozz letre uj domain migraciot, ha a meglévő H0 `app.file_objects` oszlopok elegendoek.
- Ne vezesd vissza a megoldast a legacy `project_files` / `storage_key` / `content_hash_sha256` truth-ra.
- Ne bizz a kliens altal kuldott `storage_bucket`, `byte_size`, `mime_type`, `sha256`, `file_name` mezokben mint vegleges DB-truth-ban.
- Ne nyisd meg idovel elott a H1-E2 geometry workflow-t: `geometry_revisions`, `geometry_validation_reports`,
  `geometry_derivatives` tenyleges bekotese most nem scope.

Modellezesi elvek:
- A source file metadata truth az `app.file_objects` meglévő H0 mezoire ul: `storage_bucket`, `storage_path`,
  `file_name`, `mime_type`, `byte_size`, `sha256`.
- A kanonikus source bucket H0 szerint `source-files` (konfiguralhato default: `settings.storage_bucket`).
- A complete upload ne a kliens metadatajat masolja at, hanem a storage objectbol allitsa elo a vegleges metadata truth-ot.
- A `file_name` a kanonikus `storage_path` basename-je legyen.
- A `sha256` legyen szerveroldali ingest truth, hogy a kesobbi duplicate-detection es audit mar erre epulhessen.
- Sikertelen storage letoltes eseten ne jojjon letre felig ervenyes rekord.

Kulon figyelj:
- a H1-E1-T1-ben mar elert H0 schema realignment ne torjon vissza;
- a bucket override gap zarodjon le;
- a smoke script explicit bizonyitsa, hogy a kliens metadata override nem irja felul a szerver truth-ot;
- a reportban nevezd meg egyertelmuen, hogy mi lett most szerveroldali truth, es mi marad kesobbi duplicate policy / geometry scope-ban.

A reportban kulon nevezd meg:
- a source bucket kanonikus rogzitesenek eredmenyet;
- a file_name/byte_size/mime_type/sha256 szerveroldali eloallitasanak eredmenyet;
- a smoke bizonyitekokat;
- a megmarado advisory/out-of-scope pontokat.

A vegen futtasd a standard gate-et:
- ./scripts/verify.sh --report codex/reports/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles.md

Ez frissitse:
- codex/reports/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles.md
- codex/reports/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles.verify.log

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
