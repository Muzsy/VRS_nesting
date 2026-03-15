# DXF Nesting Platform Codex Task - H1-E2-T1 DXF parser integráció
TASK_SLUG: h1_e2_t1_dxf_parser_integracio

Olvasd el:
- AGENTS.md
- canvases/web_platform/h1_e2_t1_dxf_parser_integracio.md
- codex/goals/canvases/web_platform/fill_canvas_h1_e2_t1_dxf_parser_integracio.yaml
- docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md
- docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md
- docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md
- docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md
- docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md
- supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql
- supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql
- supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql
- supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql
- api/routes/files.py
- api/services/file_ingest_metadata.py
- api/services/dxf_validation.py
- api/supabase_client.py
- vrs_nesting/dxf/importer.py
- scripts/smoke_h1_e1_t2_file_hash_es_metadata_kezeles.py

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithatsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez H1 parser integration task, nem teljes geometry pipeline leszallitas.
- Ne talalj ki uj, parhuzamos DXF parser logikat: a meglévő `vrs_nesting.dxf.importer.import_part_raw` legyen a kiindulasi pont.
- Ne hozz letre uj domain migraciot, ha a H0 `app.geometry_revisions` schema elegendo.
- Ne nyisd meg idovel elott a H1-E2-T3 validation report es a H1-E2-T4 derivative generator scope-jat.
- Ne keverd ossze a geometry revision truth-ot a `geometry_validation_reports` vagy `geometry_derivatives` vilaggal.
- Ne probalj ebben a taskban sheet-role DXF ingestet megoldani; a minimum H1 target most a part-szeru `source_dxf` import.

Modellezesi elvek:
- A source file truth mar a H1-E1 ingestben letrejott `app.file_objects` rekord es a storage object.
- A parser service a kanonikus source bucket/path alapjan dolgozzon, ne kliens payloadra tamaszkodjon.
- Sikeres parse eseten `app.geometry_revisions` rekord jojjon letre legalabb a kovetkezokkel:
  - `project_id`
  - `source_file_object_id`
  - `geometry_role='part'`
  - `revision_no`
  - `status='parsed'`
  - `canonical_format_version`
  - `canonical_geometry_jsonb`
  - `canonical_hash_sha256`
  - `source_hash_sha256`
  - `bbox_jsonb`
  - `created_by`
- A `canonical_geometry_jsonb` minimum-formátuma determinisztikus legyen, es ugyanabból a blobból ugyanazt a hash-et adja.
- Sikertelen letoltes vagy parse eseten ne jojjon letre hamis `parsed` geometry revision rekord.

Kulon figyelj:
- a H1-E1-ben mar elert server-side metadata truth ne torjon vissza;
- a parser integration explicit lineage-et adjon file_object -> geometry_revision iranyban;
- a smoke script bizonyitsa a sikeres es hibas scenariot is;
- a reportban nevezd meg egyertelmuen, hogy mi lett most megoldva, es mi marad H1-E2-T2/H1-E2-T3/H1-E2-T4 scope-ban.

A reportban kulon nevezd meg:
- a parser bekotesenek eredmenyet;
- a geometry revision payload/status/hash/bbox kitoltes eredmenyet;
- a smoke bizonyitekokat;
- a megmarado advisory/out-of-scope pontokat.

A vegen futtasd a standard gate-et:
- ./scripts/verify.sh --report codex/reports/web_platform/h1_e2_t1_dxf_parser_integracio.md

Ez frissitse:
- codex/reports/web_platform/h1_e2_t1_dxf_parser_integracio.md
- codex/reports/web_platform/h1_e2_t1_dxf_parser_integracio.verify.log

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
