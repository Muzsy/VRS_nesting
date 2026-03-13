# DXF Nesting Platform Codex Task - H0-E3-T3 validation es review tablak
TASK_SLUG: h0_e3_t3_validation_es_review_tablak

Olvasd el:
- AGENTS.md
- canvases/web_platform/h0_e3_t3_validation_es_review_tablak.md
- codex/goals/canvases/web_platform/fill_canvas_h0_e3_t3_validation_es_review_tablak.yaml
- docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md
- docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md
- docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md
- supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql
- supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez schema-task, de a scope kontrollalt:
  most csak az `app.geometry_validation_reports` es az `app.geometry_review_actions`
  tablavilag johet letre.
- Derivative, binding, run, export es RLS vilag nincs scope-ban.
- Ne moditsd a `api/sql/phase1_schema.sql` legacy bootstrap fajlt.
- A mar meglevo migraciokat ne ird at; uj migracioban folytasd a sort.

Modellezesi elvek:
- `app` schema a canonical celterulet.
- A `geometry_revisions` marad a canonical geometry truth helye.
- A `geometry_validation_reports` audit/report reteg.
- A `geometry_review_actions` emberi review / dontesi reteg.
- Ezeket nem szabad egy tablaba osszemosni.
- A review action validation report-hivatkozasanal ugyanazt az integritasi fegyelmet
  tartsd, mint a korabbi composite-FK javitasoknal:
  csak ugyanahhoz a geometry revisionhoz tartozo report legyen hivatkozhato.
- Ha review action tipus vedelmehez uj enum kell, azt ebben a migracioban hozd letre,
  ne a H0-E2-T1 enum migracio visszairasaval.

Kulon figyelj:
- ne hozz letre `geometry_derivatives`, part/sheet binding, `nesting_runs`,
  `run_artifacts` vagy mas hasonlo tablat;
- ne keruljon bele RLS policy;
- ha a fo architecture/H0 docs meg `public.*` validation/review peldat vagy
  pontatlan ownership leirast tartalmaznak, azt minimalisan szinkronizald;
- a report kulon nevezze meg a same-geometry report-hivatkozas vedelmet.

A reportban kulon nevezd meg:
- a ket tabla vegleges oszlopait;
- a PK/FK kapcsolatokat;
- az indexeket;
- az audit-integritast;
- hogy mi maradt szandekosan out-of-scope.

A vegen futtasd a standard gate-et:
- ./scripts/verify.sh --report codex/reports/web_platform/h0_e3_t3_validation_es_review_tablak.md

Ez frissitse:
- codex/reports/web_platform/h0_e3_t3_validation_es_review_tablak.md
- codex/reports/web_platform/h0_e3_t3_validation_es_review_tablak.verify.log

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
