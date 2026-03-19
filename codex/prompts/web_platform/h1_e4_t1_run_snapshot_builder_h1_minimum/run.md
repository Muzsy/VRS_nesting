# DXF Nesting Platform Codex Task - H1-E4-T1 Run snapshot builder (H1 minimum)
TASK_SLUG: h1_e4_t1_run_snapshot_builder_h1_minimum

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql`
- `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql`
- `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql`
- `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql`
- `supabase/migrations/20260311000000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql`
- `api/services/part_creation.py`
- `api/services/project_part_requirements.py`
- `api/services/sheet_creation.py`
- `api/services/project_sheet_inputs.py`
- `api/routes/runs.py`
- `api/sql/phase4_run_quota_atomic.sql`
- `canvases/web_platform/h1_e4_t1_run_snapshot_builder_h1_minimum.md`
- `codex/goals/canvases/web_platform/fill_canvas_h1_e4_t1_run_snapshot_builder_h1_minimum.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ne talalj ki nem letezo schema-t vagy API-konvenciot: a H0/H1 docsbol,
  migraciokbol es a meglevo route/service mintakbol indulj ki.
- Ez a task H1 minimum **snapshot builder** scope: ne csussz at run create API,
  queue insert, worker lease, solver futtatas, result normalizer vagy artifact
  scope-ba.
- A service a meglevo canonical tablavilagbol dolgozzon: `app.projects`,
  `app.project_settings`, `app.project_technology_setups`,
  `app.project_part_requirements`, `app.part_definitions`,
  `app.part_revisions`, `app.project_sheet_inputs`, `app.sheet_definitions`,
  `app.sheet_revisions`, es ahol kell `app.geometry_derivatives`.
- A builder csak solverre alkalmas inputot engedjen tovabb: H1 minimum szinten
  a part revision legyen `approved`, es legyen explicit
  `selected_nesting_derivative_id` referencia.
- A technology selection legyen egyertelmu; ha nincs valaszthato setup, a
  service adjon korrekt hibajat.
- A snapshot hash kepzes legyen determinisztikus.

Implementacios elvarasok:
- Vezess be explicit `api/services/run_snapshot_builder.py` service-t.
- A service H0 snapshot-structure kompatibilis payloadot adjon vissza:
  `snapshot_version`, `project_manifest_jsonb`, `technology_manifest_jsonb`,
  `parts_manifest_jsonb`, `sheets_manifest_jsonb`, `geometry_manifest_jsonb`,
  `solver_config_jsonb`, `manufacturing_manifest_jsonb`, `snapshot_hash_sha256`.
- Ne modositd a `api/routes/runs.py` legacy route-ot ebben a taskban.
- Ne vezesd vissza a taskot a `phase4_run_quota_atomic.sql` helperre; az csak
  referencia, nem source-of-truth.
- Keszits task-specifikus smoke scriptet a sikeres es hibas agakra.
- Ha kiderul valos runtime-fuggoseg vagy schema-hiany, azt a reportban
  expliciten nevezd meg. Ne rejts el valos fuggoseget.

A reportban kulon nevezd meg:
- hogy a task mit szallit le a H1 minimum snapshot builder scope-ban;
- hogy mit NEM szallit le meg (kulonosen run create, queue, worker, solver,
  result normalizer es artifact iranyokban);
- ha van legacy/korabbi run route vagy helper, mondd ki, hogy miert nem az a
  canonical H0/H1 truth.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e4_t1_run_snapshot_builder_h1_minimum.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
