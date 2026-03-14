# DXF Nesting Platform Codex Task - H0-E6-T1 storage bucket strategia es path policy
TASK_SLUG: h0_e6_t1_storage_bucket_strategia_es_path_policy

Olvasd el:
- AGENTS.md
- canvases/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy.md
- codex/goals/canvases/web_platform/fill_canvas_h0_e6_t1_storage_bucket_strategia_es_path_policy.yaml
- docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md
- docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md
- docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md
- docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md
- docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md
- supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql
- supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql
- supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez **docs-only task**.
- Migracio most nem johet letre.
- Storage provisioning script most nem johet letre.
- RLS policy most nem johet letre.
- Upload/export API vagy worker implementacio most nincs scope-ban.
- Ne moditsd a `api/sql/phase1_schema.sql` legacy bootstrap fajlt.

Modellezesi elvek:
- A `file_objects` storage-reference truth.
- A `run_artifacts` file/blob output truth.
- Az `app.geometry_derivatives` tovabbra is DB-ben tarolt derivalt truth,
  nem storage bucket/path alap entitas.
- A H0 kanonikus bucket inventory legalabb:
  - `source-files`
  - `geometry-artifacts`
  - `run-artifacts`
- A `geometry-artifacts` bucket reserved/canonical hely jovobeli file-backed
  geometry/viewer/manufacturing artifactokhoz.
- A bucket-nevek stabilak legyenek es ne feature-onkent novekedjenek kontroll nelkul.
- A project ownership es a bucket/path szerzodes keszitse elo a H0-E6-T2 RLS taskot,
  de magat az enforcementet most ne implementald.

Kulon figyelj:
- ne hozz letre `supabase/migrations/*` fajlt ehhez a taskhoz;
- ne hozz letre storage provisioning, seed vagy CLI scriptet;
- ne keruljon bele RLS policy vagy storage policy implementacio;
- a dedikalt storage source-of-truth dokumentum legyen konkret, ne altalanos;
- legyen benne egyertelmu entitas -> bucket mapping;
- legyen benne bucketenkenti kanonikus path minta;
- legyen benne explicit mondat, hogy a `geometry_derivatives` nem storage-truth;
- a fo architecture es H0 roadmap dokumentum csak annyiban valtozzon, amennyiben a
  T1 storage source-of-truth lezarasahoz szukseges.

A reportban kulon nevezd meg:
- a vegleges bucket inventoryt;
- az entitas -> bucket mappinget;
- a bucketenkenti path mintakat;
- az immutabilitas / overwrite elveket;
- hogy a `geometry_derivatives` miert nem storage-truth;
- hogy mi maradt szandekosan out-of-scope.

A vegen futtasd a standard gate-et:
- ./scripts/verify.sh --report codex/reports/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy.md

Ez frissitse:
- codex/reports/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy.md
- codex/reports/web_platform/h0_e6_t1_storage_bucket_strategia_es_path_policy.verify.log

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
