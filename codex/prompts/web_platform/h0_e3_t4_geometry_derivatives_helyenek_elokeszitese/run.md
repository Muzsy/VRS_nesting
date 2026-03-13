# DXF Nesting Platform Codex Task - H0-E3-T4 geometry derivatives helyenek elokeszitese
TASK_SLUG: h0_e3_t4_geometry_derivatives_helyenek_elokeszitese

Olvasd el:
- AGENTS.md
- canvases/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.md
- codex/goals/canvases/web_platform/fill_canvas_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.yaml
- docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md
- docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md
- docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md
- supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql
- supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql
- supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez schema-task, de a scope kontrollalt:
  most csak az `app.geometry_derivatives` tabla johet letre.
- Binding, run, export es RLS vilag nincs scope-ban.
- Ne moditsd a `api/sql/phase1_schema.sql` legacy bootstrap fajlt.
- A mar meglevo migraciokat ne ird at; uj migracioban folytasd a sort.

Modellezesi elvek:
- `app` schema a canonical celterulet.
- A `geometry_revisions` marad a canonical geometry truth helye.
- A `geometry_derivatives` a cel-specifikus, ujraeloallithato derivalt reteg.
- Ez nem binding tabla.
- Ez nem run snapshot tabla.
- Ez nem export artifact tabla.
- A derivative kind legalabb a H0 docsben nevesitett vilagokat fedje:
  `nesting_canonical`, `manufacturing_canonical`, `viewer_outline`.
- A tabla maradjon minimalis, de tenylegesen hasznalhato H0 bazis.

Kulon figyelj:
- ne hozz letre part/sheet binding, `nesting_runs`, `nesting_run_snapshots`,
  `run_artifacts` vagy mas export jellegu tablat;
- ne keruljon bele RLS policy;
- ha a fo architecture/H0 docs meg `public.*` derivative peldat vagy pontatlan
  ownership leirast tartalmaznak, azt minimalisan szinkronizald;
- a report kulon nevezze meg a uniqueness vedelmet es a payload/version/hash mezoket.

A reportban kulon nevezd meg:
- a `geometry_derivatives` vegleges oszlopait;
- a PK/FK kapcsolatokat;
- az indexeket;
- az egyedi `(geometry_revision_id, derivative_kind)` vedelmet;
- hogy mi maradt szandekosan out-of-scope.

A vegen futtasd a standard gate-et:
- ./scripts/verify.sh --report codex/reports/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.md

Ez frissitse:
- codex/reports/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.md
- codex/reports/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.verify.log

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
