# DXF Nesting Platform Codex Task - H2-E3-T1 cut rule set model
TASK_SLUG: h2_e3_t1_cut_rule_set_model

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql`
- `api/routes/project_manufacturing_selection.py`
- `api/services/project_manufacturing_selection.py`
- `canvases/web_platform/h2_e3_t1_cut_rule_set_model.md`
- `codex/goals/canvases/web_platform/fill_canvas_h2_e3_t1_cut_rule_set_model.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- A jelenlegi repoban a H2 docs altal emlitett `machine_catalog` es
  `material_catalog` tablakat nem latod a tenyleges migraciokban. Emiatt a
  cut rule set domainnek a jelenlegi repo truth-hoz kell igazodnia:
  `machine_code`, `material_code`, `thickness_mm` mezokkel dolgozz.
- A task H2-E3-T1, nem H2-E3-T2/H2-E3-T3. Ezert ne hozz letre
  `cut_contour_rules` tablakat, ne implementalj lead-in/out sorokat, es ne irj
  contour class -> rule matching logikat.
- A task ne nyisson manufacturing profile version FK-bovitest sem; a rule set
  domain most kulon truth marad.
- A CRUD owner-scoped legyen, es mintakovesse a meglevo H2-E1-T2 project
  manufacturing selection service validacios stilusat.
- A verziozhatosag tenyleges kovetelmeny: ugyanazon owner + name alatt uj verzio
  letrehozhato legyen determinisztikus `version_no` emelessel.
- A `name`, `machine_code`, `material_code` mezok ne legyenek ures stringek;
  a `thickness_mm`, ha jelen van, pozitiv legyen.

Implementacios fokusz:
- Vezess be minimalis `app.cut_rule_sets` truth-ot.
- Keszits explicit `api/services/cut_rule_sets.py` service-t.
- Keszits minimalis `api/routes/cut_rule_sets.py` route-okat, es kotd be az
  `api/main.py`-ba.
- A smoke script bizonyitsa a fo sikeres es hibas agakat.
- A report kulon nevezze meg, hogy a task mit NEM szallit le meg:
  - contour rules,
  - rule matching,
  - manufacturing profile rule set binding,
  - snapshot / plan / preview / export.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h2_e3_t1_cut_rule_set_model.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
