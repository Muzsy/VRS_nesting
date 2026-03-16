# DXF Nesting Platform Codex Task - H1-E2-T4 Geometry derivative generator (H1 minimum)
TASK_SLUG: h1_e2_t4_geometry_derivative_generator_h1_minimum

Olvasd el:
- AGENTS.md
- canvases/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum.md
- codex/goals/canvases/web_platform/fill_canvas_h1_e2_t4_geometry_derivative_generator_h1_minimum.yaml
- docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md
- docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md
- docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md
- docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md
- supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql
- supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql
- supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql
- api/services/dxf_geometry_import.py
- api/services/geometry_validation_report.py
- scripts/smoke_h1_e2_t3_validation_report_generator.py

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithatsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez H1 minimum geometry derivative task, nem manufacturing pipeline, nem part/sheet binding es nem run snapshot epites.
- Ne talalj ki uj, parhuzamos geometry truth-ot: a source tovabbra is a H1-E2-T2/H1-E2-T3 altal letrehozott `app.geometry_revisions` rekord.
- Ne hozz letre uj domain migraciot, ha a meglevő H0 `app.geometry_derivatives` schema elegendo.
- Ne nyisd meg idovel elott a H1-E3 part creation, a manufacturing_canonical vagy a run snapshot/scheduler scope-jat.
- Ne keverd ossze a geometry revision canonical truth-ot a derivative reteggel; a derivative ujraeloallithato, cel-specifikus reteg maradjon.
- Ne hozz letre uj list/query API endpointot csak azert, hogy a derivative-eket szemleltesd.

Modellezesi elvek:
- A derivative generator csak validalt geometry truth-ra uljon; `rejected` geometrybol nem keletkezhet H1 minimum derivative.
- Legalabb ket kulon derivative keszuljon: `nesting_canonical` es `viewer_outline`.
- A ket payload szerepe legyen elvalasztva; ne ugyanaz a JSON legyen ket kulonbozo kinddel.
- A `producer_version`, `format_version`, `derivative_hash_sha256` es `source_geometry_hash_sha256` determinisztikusan toltodjon.
- Ujrageneralas / retry eseten a `(geometry_revision_id, derivative_kind)` uniqueness ne torjon el; legyen kontrollalt update vagy ezzel egyenerteku viselkedes.
- Parse/import failure eseten tovabbra se jojjon letre hamis geometry revision vagy derivative rekord.

Kulon figyelj:
- a H1-E2-T2 normalized canonical truth es a H1-E2-T3 validation verdict ne torjon vissza;
- a derivative generator csak a validation utan futhat a pipeline-ban;
- a smoke script bizonyitsa a determinisztikus payloadot/hash-t es az ujrageneralasi agat is, ne csak a happy pathot;
- a reportban nevezd meg kulon, hogy mi lett most H1 minimum derivative scope-ban leszallitva, es mi marad H1-E3, H1-E4 illetve H2 manufacturing scope-ban.

A reportban kulon nevezd meg:
- a derivative generator service bekotesenek eredmenyet;
- a `nesting_canonical` es `viewer_outline` payload szerepet es formatumot;
- a hash / version / source lineage eredmenyet;
- az ujrageneralasi/uniqueness viselkedest;
- a smoke bizonyitekokat;
- a megmarado advisory/out-of-scope pontokat.

A vegen futtasd a standard gate-et:
- ./scripts/verify.sh --report codex/reports/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum.md

Ez frissitse:
- codex/reports/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum.md
- codex/reports/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum.verify.log

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
