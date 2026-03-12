# DXF Nesting Platform Codex Task - H0-E3-T1 file object modell
TASK_SLUG: h0_e3_t1_file_object_modell

Olvasd el:
- AGENTS.md
- canvases/web_platform/h0_e3_t1_file_object_modell.md
- codex/goals/canvases/web_platform/fill_canvas_h0_e3_t1_file_object_modell.yaml
- docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md
- docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md
- docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md
- supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql
- supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql
- supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql
- supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql
- supabase/migrations/20260310240000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez schema-task, de a scope kontrollalt:
  most csak az `app.file_objects` tabla johet letre.
- Geometry revision, validation, review, derivative, run, export es storage policy vilag nincs scope-ban.
- Ne moditsd a `api/sql/phase1_schema.sql` legacy bootstrap fajlt.
- A mar meglevo migraciokat ne ird at; uj migracioban folytasd a sort.

Modellezesi elvek:
- `app` schema a canonical celterulet.
- A `file_objects` nyers storage-referencia + metaadat truth.
