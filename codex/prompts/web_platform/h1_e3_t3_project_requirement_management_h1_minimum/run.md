# DXF Nesting Platform Codex Task - H1-E3-T3 Project requirement management (H1 minimum)
TASK_SLUG: h1_e3_t3_project_requirement_management_h1_minimum

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql`
- `supabase/migrations/20260314113000_h0_e6_t2_rls_policy_alapok.sql`
- `api/services/part_creation.py`
- `api/routes/parts.py`
- `canvases/web_platform/h1_e3_t3_project_requirement_management_h1_minimum.md`
- `codex/goals/canvases/web_platform/fill_canvas_h1_e3_t3_project_requirement_management_h1_minimum.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ne talalj ki nem letezo schema-t vagy API-konvenciot: a H0/H1 docsbol,
  migraciokbol es a meglevo route/service mintakbol indulj ki.
- Ez a task H1 minimum project requirement scope: ne csussz at run snapshot,
  solver-input aggregation, sheet input, inventory/remnant vagy manufacturing
  scope-ba.
- A workflow kizarolag a meglevo `app.projects`, `app.part_definitions`,
  `app.part_revisions` es `app.project_part_requirements` truth-ra epuljon.
- A service validalja, hogy a projekt a jelenlegi user tulajdona, es a
  `part_revision_id` a jelenlegi owner altal birtokolt `part_definition`-hoz
  tartozik.
- A service kezelje az uj es meglevo `(project_id, part_revision_id)` agakat,
  ne termeljen duplikalt requirement rekordot.
- A `placement_policy` inputot a valos enum truth-hoz igazitsd; ne vezess be
  kitalalt policy ertekeket.

Implementacios elvarasok:
- Vezess be explicit `api/services/project_part_requirements.py` service-t.
- Keszits minimalis `api/routes/project_part_requirements.py` endpointot, es kotd
  be az `api/main.py`-ba.
- A smoke script bizonyitsa a sikeres uj-record, meglevo-record, idegen projekt,
  idegen part revision, ervenytelen `required_qty`, `placement_priority` es
  `placement_policy` agak funkcionalitasat.
- Ha runtime-fuggoseg vagy plusz migracio derul ki, azt a reportban expliciten
  nevezd meg. Ne rejts el valos runtime-fuggoseget.

A reportban kulon nevezd meg:
- hogy a task mit szallit le a H1 minimum requirement flowhoz;
- hogy mit NEM szallit le meg (kulonosen run snapshot, solver-input aggregation,
  sheet input, inventory/remnant es manufacturing iranyokban);
- ha van kulso runtime-fuggoseg vagy plusz migracio, azt explicit dokumentald.

A vegén futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e3_t3_project_requirement_management_h1_minimum.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
