# DXF Nesting Platform Codex Task - H0-E2-T5 sheet definition, revision es project input alapok
TASK_SLUG: h0_e2_t5_sheet_definition_revision_es_project_input_alapok

Olvasd el:
- AGENTS.md
- canvases/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok.md
- codex/goals/canvases/web_platform/fill_canvas_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.yaml
- docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md
- docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md
- docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md
- supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql
- supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql
- supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql
- supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez schema-task, de a scope tovabbra is kontrollalt:
  most csak a sheet-domain bazis tablavilaga johet letre.
- Remnant/inventory/file/geometry/run/export vilag nincs scope-ban.
- Ne moditsd a `api/sql/phase1_schema.sql` legacy bootstrap fajlt.
- A mar meglevo H0-E2-T1/T2/T3/T4 migraciokat ne ird at; uj migracioban folytasd a sort.

Modellezesi elvek:
- `app` schema a canonical celterulet.
- `Sheet Definition` != `Sheet Revision` != `Project Sheet Input`
- A project sheet input projekt-specifikus input/availability vilag, nem a definition resze.
- A project input a `sheet_revisions` vilagra uljon, ne kozvetlenul a definitionre.
- A `sheet_revisions` most meg NEM inventory truth es NEM remnant vilag.
- A `current_revision_id` integritasnal ugyanazt az elvet kovessuk, mint a part-domain taskban:
  ne lehessen mas definitionhoz tartozo revisionra mutatni.
- Ha a file/geometry pipeline tablák meg nincsenek lerakva, ne eroszakolj be hianyzo FK-ket.
- A revision tabla most minimalis, de stabil domain bazis legyen.
- A task egyben docs-tisztitas is: a stale `public.*` sheet-domain peldakat es a
  rossz aggregate-koteseket minimalisan szinkronizald.

Kulon figyelj:
- ne hozz letre remnant, stock inventory unit, geometry_revisions, geometry_derivatives,
  file_objects, run request/snapshot/attempt, export vagy manufacturing package tablat;
- ne keruljon bele RLS policy;
- ne keverd a definition, revision es project input vilagokat;
- a report kulon nevezze meg, hogy a project input a revisionhoz kotott;
- a report kulon nevezze meg, hogy a `current_revision_id` integritas hogyan van vedve.

A reportban kulon nevezd meg:
- a 3 tabla vegleges oszlopait;
- a PK/FK kapcsolatokat;
- az indexeket;
- hogy mi maradt szandekosan out-of-scope.

A vegen futtasd a standard gate-et:
- ./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok.md

Ez frissitse:
- codex/reports/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok.md
- codex/reports/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok.verify.log

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
