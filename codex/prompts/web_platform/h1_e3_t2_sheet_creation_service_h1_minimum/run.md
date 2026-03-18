# DXF Nesting Platform Codex Task - H1-E3-T2 Sheet creation service (H1 minimum)
TASK_SLUG: h1_e3_t2_sheet_creation_service_h1_minimum

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `supabase/migrations/20260311000000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql`
- `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql`
- `api/services/part_creation.py`
- `api/routes/parts.py`
- `canvases/web_platform/h1_e3_t2_sheet_creation_service_h1_minimum.md`
- `codex/goals/canvases/web_platform/fill_canvas_h1_e3_t2_sheet_creation_service_h1_minimum.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ne talalj ki nem letezo schema-t vagy API-konvenciot: a H0/H1 docsbol,
  migraciokbol es a meglevo route/service mintakbol indulj ki.
- Ez a task H1 minimum sheet creation scope: ne csussz at `project_sheet_inputs`,
  inventory/remnant, run snapshot vagy manufacturing scope-ba.
- H1-ben most csak teglalap alapu sheet revision kell (`width_mm`, `height_mm`,
  opcionális `grain_direction`); ne vezess be idovel elott geometry/DXF alapú
  sheet pipeline-t.
- A `sheet_definition` owner-szintu aggregate maradjon; a route ne kerjen
  `project_id`-t, es ne hozzon letre automatikusan `project_sheet_inputs` rekordot.
- A service kezelje az uj es meglevo `sheet_definition` agakat, valamint a
  `current_revision_id` frissitest.

Implementacios elvarasok:
- Vezess be explicit `api/services/sheet_creation.py` service-t.
- Keszits minimalis `api/routes/sheets.py` endpointot, es kotd be az `api/main.py`-ba.
- Ha a revision-szam vagy current pointer biztonsagos kezelesere DB oldali segedfuggveny
  szukseges, azt csak kulon, explicit task-output migracioban vezesd be, es nevezd meg
  tisztan a reportban. Ne rejts el tenyleges runtime-fuggoseget.
- A smoke script bizonyitsa a sikeres uj-definition, meglevo-definition,
  ervenytelen meret es hianyos request agakat.

A reportban kulon nevezd meg:
- hogy a task mit szallit le a H1 minimum sheet workflowhoz;
- hogy mit NEM szallit le meg (kulonosen `project_sheet_inputs`, remnant/inventory,
  run snapshot es manufacturing iranyokban);
- ha van kulso runtime-fuggoseg vagy plusz migracio, azt explicit dokumentald.

A vegén futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e3_t2_sheet_creation_service_h1_minimum.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
