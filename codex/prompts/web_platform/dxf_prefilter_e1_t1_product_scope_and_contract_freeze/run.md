# DXF Prefilter E1-T1 Product scope and contract freeze
TASK_SLUG: dxf_prefilter_e1_t1_product_scope_and_contract_freeze

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `vrs_nesting/dxf/importer.py`
- `api/services/dxf_geometry_import.py`
- `api/services/geometry_validation_report.py`
- `api/services/dxf_validation.py`
- `api/routes/files.py`
- `frontend/src/pages/ProjectDetailPage.tsx`
- `frontend/src/pages/NewRunPage.tsx`
- `canvases/web_platform/dxf_prefilter_e1_t1_product_scope_and_contract_freeze.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e1_t1_product_scope_and_contract_freeze.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez **docs-only contract freeze** task. Ne vezess be Python, TypeScript,
  SQL, migration vagy API implementacios valtoztatast.
- Ne hozz letre uj DXF parser vagy uj acceptance gate kodot ebben a taskban.
- Ne talalj ki repoban nem letezo route-ot, service-t, state-et vagy fajlt csak
  azert, hogy a scope “szebb” legyen.
- A dokumentumnak a jelenlegi kodra kell epulnie: importer, geometry import,
  validation, file upload es frontend entrypointok konkret figyelembevetelével.

A dokumentacios elvarasok:
- Rogzitsd, hogy a belso truth layer-alapu marad (`CUT_OUTER`, `CUT_INNER`,
  `MARKING`), a szin pedig input-hint.
- Rogzitsd, hogy a V1 fail-fast es csak egyertelmu javitasokat vegez.
- Rogzitsd, hogy a modul a file upload utan, de a geometry import elott kell,
  hogy belepjen.
- Rogzitsd, hogy a helyes UI irany kulon `DXF Intake / Project Preparation`
  oldal, nem a legacy `NewRunPage.tsx` tovabbi foltozasa.
- Rogzitsd kulon, mi **nincs** benne a V1-ben.

A reportban nevezd meg kulon:
- melyik meglevo fajlokra epul a scope freeze;
- miert nem uj parhuzamos DXF motort tervez a task;
- hol lesz a jovobeli backend bekotesi pont;
- miert kell az uj intake oldal kulon a jelenlegi UI mellett.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e1_t1_product_scope_and_contract_freeze.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
