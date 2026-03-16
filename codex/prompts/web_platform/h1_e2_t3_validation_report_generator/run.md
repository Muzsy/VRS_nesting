# DXF Nesting Platform Codex Task - H1-E2-T3 Validation report generator
TASK_SLUG: h1_e2_t3_validation_report_generator

Olvasd el:
- AGENTS.md
- canvases/web_platform/h1_e2_t3_validation_report_generator.md
- codex/goals/canvases/web_platform/fill_canvas_h1_e2_t3_validation_report_generator.yaml
- docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md
- docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md
- docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md
- docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md
- supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql
- supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql
- api/services/dxf_geometry_import.py
- api/services/dxf_validation.py
- api/routes/files.py
- scripts/smoke_h1_e2_t2_geometry_normalizer.py

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithatsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez H1 geometry validation report task, nem review workflow es nem derivative generator.
- Ne talalj ki uj, parhuzamos DXF parser logikat es ne vezesd vissza a Phase1-fele `validation_status` / `validation_error` file-szintu modellt.
- Ne hozz letre uj domain migraciot, ha a meglévo H0 `app.geometry_validation_reports` schema elegendo.
- Ne nyisd meg idovel elott a H1-E2-T4 derivative generator, a geometry review actions workflow vagy a part/sheet approval scope-jat.
- Ne hozz letre uj list/query API endpointot csak azert, hogy a reportot szemleltesd; a focus a generator service es a pipeline bekotese.

Modellezesi elvek:
- A validation report a normalizalt `app.geometry_revisions` truth-ra uljon, ne a nyers storage file-ra.
- A report JSON legyen strukturalt es determinisztikus: issue-lista, severity osszesites, validator meta, lineage.
- A `validation_seq` novekedjen korrektul geometry revisionon belul.
- A `geometry_revisions.status` legalabb `validated` / `rejected` iranyba frissuljon, de `approved`-ot ez a task nem adhat.
- A `geometry_validation_reports.status` legyen konzisztens a report verdicttel.
- Parse/import failure eseten tovabbra se jojjon letre hamis parsed geometry revision rekord.

Kulon figyelj:
- a H1-E2-T2 normalized canonical truth ne torjon vissza importer-kimeneti formara;
- a validation report generator ne keverje ossze a file-szintu DXF letoltes/olvasas hibat a geometry truth validacioval;
- ha a meglévo `api/services/dxf_validation.py` mar nem a fo H1 pipeline-resz, ezt a route/service bekotesben egyertelmusitsd;
- a smoke script bizonyitsa a valid es a rejected validation branch-et is;
- a reportban nevezd meg kulon, hogy mi lett most H1-E2-T3 scope-ban leszallitva, es mi marad H1-E2-T4 illetve kesobbi review scope-ban.

A reportban kulon nevezd meg:
- a validation report service bekotesenek eredmenyet;
- a `summary_jsonb` / `report_jsonb` struktura eredmenyet;
- a `validation_seq`, `validator_version` es statuszfrissites eredmenyet;
- a smoke bizonyitekokat;
- a megmarado advisory/out-of-scope pontokat.

A vegen futtasd a standard gate-et:
- ./scripts/verify.sh --report codex/reports/web_platform/h1_e2_t3_validation_report_generator.md

Ez frissitse:
- codex/reports/web_platform/h1_e2_t3_validation_report_generator.md
- codex/reports/web_platform/h1_e2_t3_validation_report_generator.verify.log

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
