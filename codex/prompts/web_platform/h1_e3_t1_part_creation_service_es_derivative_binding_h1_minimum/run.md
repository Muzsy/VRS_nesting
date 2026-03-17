Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql`
- `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql`
- `api/services/dxf_geometry_import.py`
- `api/routes/files.py`
- `canvases/web_platform/h1_e3_t1_part_creation_service_es_derivative_binding_h1_minimum.md`
- `codex/goals/canvases/web_platform/fill_canvas_h1_e3_t1_part_creation_service_es_derivative_binding_h1_minimum.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosit hatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ne talalj ki nem letezo schema-t vagy API-konvenciot: a H0/H1 docsbol,
  migraciokbol es a meglévo route/service mintakbol indulj ki.
- A task H1 minimum: ne csussz at project requirement, sheet workflow,
  run snapshot vagy manufacturing scope-ba.
- A meglévo `part_revisions.lifecycle` approval-jelentest hasznald; ne vezess be
  vele uzletileg redundans uj approval oszlopot csak szokasbol.
- A geometry/derivative binding legyen explicit es auditálhato a `part_revision`
  szintjen.
- A service csak projektbe tartozo, `validated` geometry revisiont fogadhat el,
  es kotelezoen a hozza tartozo `nesting_canonical` derivative-re kell epulnie.

Implementacios elvarasok:
- Keszits kulon migraciot a `part_revisions` H1-minimum binding bovitesere.
- Vezess be explicit `api/services/part_creation.py` service-t.
- Keszits minimalis `api/routes/parts.py` endpointot, es kotd be az `api/main.py`-ba.
- A service kezelje az uj es meglevo `part_definition` agakat, valamint a
  `current_revision_id` frissitest.
- A smoke script bizonyitsa a sikeres, meglevo-definition, hianyzo-derivative,
  nem-validalt geometry es idegen-projekt agakat.

A vegén futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e3_t1_part_creation_service_es_derivative_binding_h1_minimum.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
