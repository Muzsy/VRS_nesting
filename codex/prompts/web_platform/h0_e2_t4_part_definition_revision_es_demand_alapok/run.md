# DXF Nesting Platform Codex Task - H0-E2-T4 part definition, revision es demand alapok
TASK_SLUG: h0_e2_t4_part_definition_revision_es_demand_alapok

Olvasd el:
- AGENTS.md
- canvases/web_platform/h0_e2_t4_part_definition_revision_es_demand_alapok.md
- codex/goals/canvases/web_platform/fill_canvas_h0_e2_t4_part_definition_revision_es_demand_alapok.yaml
- docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md
- docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md
- docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md
- supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql
- supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql
- supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez schema-task, de a scope tovabbra is kontrollalt:
  most csak a part-domain bazis tablavilaga johet letre.
- Geometry/file/sheet/run/remnant/export vilag nincs scope-ban.
- Ne moditsd a `api/sql/phase1_schema.sql` legacy bootstrap fajlt.
- A mar meglevo H0-E2-T1/T2/T3 migraciokat ne ird at; uj migracioban folytasd a sort.

Modellezesi elvek:
- `app` schema a canonical celterulet.
- `Part Definition` != `Part Revision` != `Part Demand`
- A demand projekt-specifikus usage/input vilag, nem a definition resze.
- A demand a `part_revisions` vilagra uljon, ne kozvetlenul a definitionre.
- Ha a geometry pipeline tablák meg nincsenek lerakva, ne eroszakolj be hianyzo FK-ket.
- A revision tabla most minimalis, de stabil domain bazis legyen.
- A task egyben docs-tisztitas is: a stale `public.*` part-domain peldakat es a
  rossz aggregate-koteseket minimalisan szinkronizald.

Kulon figyelj:
- ne hozz letre geometry_revisions, geometry_derivatives, file_objects,
  sheet_definitions, sheet_revisions, project_sheet_inputs, run request/snapshot/attempt,
  remnant, export vagy manufacturing package tablat;
- ne keruljon bele RLS policy;
- ne keverd a definition, revision es demand vilagokat;
- a report kulon nevezze meg, hogy a demand a revisionhoz kotott.

A reportban kulon nevezd meg:
- a 3 tabla vegleges oszlopait;
- a PK/FK kapcsolatokat;
- az indexeket;
- hogy mi maradt szandekosan out-of-scope.

A vegen futtasd a standard gate-et:
- ./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t4_part_definition_revision_es_demand_alapok.md

Ez frissitse:
- codex/reports/web_platform/h0_e2_t4_part_definition_revision_es_demand_alapok.md
- codex/reports/web_platform/h0_e2_t4_part_definition_revision_es_demand_alapok.verify.log

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
