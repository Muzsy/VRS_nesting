# DXF Nesting Platform Codex Task - H1-E2-T2 Geometry normalizer
TASK_SLUG: h1_e2_t2_geometry_normalizer

Olvasd el:
- AGENTS.md
- canvases/web_platform/h1_e2_t2_geometry_normalizer.md
- codex/goals/canvases/web_platform/fill_canvas_h1_e2_t2_geometry_normalizer.yaml
- docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md
- docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md
- docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md
- docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md
- supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql
- supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql
- supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql
- api/services/dxf_geometry_import.py
- api/routes/files.py
- vrs_nesting/dxf/importer.py
- vrs_nesting/geometry/clean.py
- scripts/smoke_h1_e2_t1_dxf_parser_integracio.py

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithatsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez H1 geometry normalizer task, nem teljes validation/derivative leszallitas.
- Ne talalj ki uj, parhuzamos DXF parser logikat: a meglévő `vrs_nesting.dxf.importer.import_part_raw` maradjon a parse forras.
- Ne hozz letre uj domain migraciot, ha a H0 `app.geometry_revisions` schema elegendo.
- Ne nyisd meg idovel elott a H1-E2-T3 validation report es a H1-E2-T4 derivative generator scope-jat.
- Ne keverd ossze a geometry revision canonical truth-ot a `geometry_validation_reports` vagy `geometry_derivatives` vilaggal.
- Ne probalj ebben a taskban part/sheet binding workflow-t vagy uj geometry query API-t epiteni.

Modellezesi elvek:
- A source file truth mar a H1-E1 ingestben letrejott `app.file_objects` rekord es a storage object.
- A parse tovabbra is a meglévő importerre epuljon, a normalizer erre a `PartRaw` eredmenyre uljon.
- A `canonical_geometry_jsonb` minimum H1 normalized truth legyen, nem laza importer dump.
- A normalized payload determinisztikus legyen: ugyanabból a DXF-bol ugyanaz a JSON es ugyanaz a hash keletkezzen.
- A `canonical_format_version` mar a normalized payloadot tukrozze.
- A `bbox_jsonb` a normalized geometryval maradjon konzisztens.
- Sikertelen letoltes vagy parse eseten tovabbra se jojjon letre hamis geometry revision rekord.

Kulon figyelj:
- a H1-E1 server-side metadata truth es a H1-E2-T1 lineage/logika ne torjon vissza;
- a normalizer explicit, tiszta service-hatar legyen;
- a smoke script bizonyitsa a determinisztikussagot is, ne csak a sikeres parse-t;
- a reportban nevezd meg egyertelmuen, hogy mi lett most normalizalt truth, es mi marad H1-E2-T3/H1-E2-T4 scope-ban.

A reportban kulon nevezd meg:
- a normalizer bekotesenek eredmenyet;
- a normalized payload/hash/bbox/format_version kitoltes eredmenyet;
- a smoke bizonyitekokat;
- a megmarado advisory/out-of-scope pontokat.

A vegen futtasd a standard gate-et:
- ./scripts/verify.sh --report codex/reports/web_platform/h1_e2_t2_geometry_normalizer.md

Ez frissitse:
- codex/reports/web_platform/h1_e2_t2_geometry_normalizer.md
- codex/reports/web_platform/h1_e2_t2_geometry_normalizer.verify.log

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
