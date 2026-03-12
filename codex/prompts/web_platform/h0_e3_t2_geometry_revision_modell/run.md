# DXF Nesting Platform Codex Task - H0-E3-T2 geometry revision modell
TASK_SLUG: h0_e3_t2_geometry_revision_modell

Olvasd el:
- AGENTS.md
- canvases/web_platform/h0_e3_t2_geometry_revision_modell.md
- codex/goals/canvases/web_platform/fill_canvas_h0_e3_t2_geometry_revision_modell.yaml
- docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md
- docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md
- docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md
- supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez schema-task, de a scope kontrollalt:
  most csak az `app.geometry_revisions` tabla johet letre.
- Validation, review, derivative, run, export es RLS vilag nincs scope-ban.
- Ne moditsd a `api/sql/phase1_schema.sql` legacy bootstrap fajlt.
- A mar meglevo migraciokat ne ird at; uj migracioban folytasd a sort.

Modellezesi elvek:
- `app` schema a canonical celterulet.
- A geometry revision a canonical geometry truth helye.
- Ez nem validation report tabla.
- Ez nem review action tabla.
- Ez nem derivative tabla.
- A canonical geometry H0-elv szerint JSON-alapu es verziozott.
- A source file -> geometry revision lineage kotelezoen latszodjon.
- A `canonical_format_version` tarolasa kotelezo.
- A tabla maradjon minimalis, de tenylegesen hasznalhato H0 bazis.

Kulon figyelj:
- ne hozz letre `geometry_validation_reports`, `geometry_review_actions`,
  `geometry_derivatives`, `nesting_runs`, `run_artifacts` vagy mas hasonlo tablat;
- ne keruljon bele RLS policy;
- ha a fo architecture/H0 docs meg `public.*` geometry/file lineage peldat vagy
  pontatlan ownership leirast tartalmaznak, azt minimalisan szinkronizald;
- a report kulon nevezze meg a source lineage-et, a canonical format versiont,
  es a JSON-alapu canonical geometry helyet.

A reportban kulon nevezd meg:
- a `geometry_revisions` vegleges oszlopait;
- a PK/FK kapcsolatokat;
- az indexeket;
- a revision-integritast;
- a source-file lineage-et;
- hogy mi maradt szandekosan out-of-scope.

A vegen futtasd a standard gate-et:
- ./scripts/verify.sh --report codex/reports/web_platform/h0_e3_t2_geometry_revision_modell.md

Ez frissitse:
- codex/reports/web_platform/h0_e3_t2_geometry_revision_modell.md
- codex/reports/web_platform/h0_e3_t2_geometry_revision_modell.verify.log

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
