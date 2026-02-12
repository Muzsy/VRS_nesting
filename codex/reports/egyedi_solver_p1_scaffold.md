PASS_WITH_NOTES

## 1) Meta

- Task slug: `egyedi_solver_p1_scaffold`
- Kapcsolodo canvas: `NINCS: canvases/egyedi_solver_p1_scaffold.md`
- Kapcsolodo goal YAML: `NINCS: codex/goals/canvases/fill_canvas_egyedi_solver_p1_scaffold.yaml`
- Futas datuma: `2026-02-12`
- Fokusz terulet: `Docs | Planning`

## 2) Scope

### 2.1 Cel
- A backlog P1 feladatokhoz scaffold artefaktok generalasa.
- Area-struktura konzisztens hasznalata (`egyedi_solver`).
- Canvas + goal YAML + runner prompt + checklist/report vaz keszitese taskonkent.

### 2.2 Nem-cel
- Funkcionalis implementacio.
- P0 artefaktok modositasa/atnevezese.

## 3) P1 taskok (title + slug)

- DXF import konvenciok + clean pipeline - `dxf_import_convention_layers`
- Polygonize + offset robusztussag - `geometry_offset_robustness`
- Rotacios policy + instance regresszio - `rotation_policy_and_instance_regression`
- Determinizmus + idokeret enforcement - `determinism_and_time_budget`

## 4) Letrehozott fajlok

- `canvases/egyedi_solver/dxf_import_convention_layers.md`
- `canvases/egyedi_solver/geometry_offset_robustness.md`
- `canvases/egyedi_solver/rotation_policy_and_instance_regression.md`
- `canvases/egyedi_solver/determinism_and_time_budget.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_dxf_import_convention_layers.yaml`
- `codex/goals/canvases/egyedi_solver/fill_canvas_geometry_offset_robustness.yaml`
- `codex/goals/canvases/egyedi_solver/fill_canvas_rotation_policy_and_instance_regression.yaml`
- `codex/goals/canvases/egyedi_solver/fill_canvas_determinism_and_time_budget.yaml`
- `codex/codex_checklist/egyedi_solver/dxf_import_convention_layers.md`
- `codex/codex_checklist/egyedi_solver/geometry_offset_robustness.md`
- `codex/codex_checklist/egyedi_solver/rotation_policy_and_instance_regression.md`
- `codex/codex_checklist/egyedi_solver/determinism_and_time_budget.md`
- `codex/reports/egyedi_solver/dxf_import_convention_layers.md`
- `codex/reports/egyedi_solver/geometry_offset_robustness.md`
- `codex/reports/egyedi_solver/rotation_policy_and_instance_regression.md`
- `codex/reports/egyedi_solver/determinism_and_time_budget.md`
- `codex/prompts/egyedi_solver/dxf_import_convention_layers/run.md`
- `codex/prompts/egyedi_solver/geometry_offset_robustness/run.md`
- `codex/prompts/egyedi_solver/rotation_policy_and_instance_regression/run.md`
- `codex/prompts/egyedi_solver/determinism_and_time_budget/run.md`

## 5) Kovi szabalyok

- Area struktura: meglvo `egyedi_solver` mappak hasznalata, strukturatores nelkul.
- Slug konvencio: ASCII snake_case, P0 slugokkal nem utkozik.
- Template hasznalat: runner promptok a `codex/prompts/task_runner_prompt_template.md` mintajat kovetik.
- Scaffold-only run: implementacios diff nem tortent.

## 6) Verify

- Kotelezo gate: `./scripts/verify.sh --report codex/reports/egyedi_solver_p1_scaffold.md`

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-12T21:32:27+01:00 → 2026-02-12T21:33:33+01:00 (66s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver_p1_scaffold.verify.log`
- git: `main@6c6de98`
- módosított fájlok (git status): 23

**git status --porcelain (preview)**

```text
?? canvases/egyedi_solver/determinism_and_time_budget.md
?? canvases/egyedi_solver/dxf_import_convention_layers.md
?? canvases/egyedi_solver/geometry_offset_robustness.md
?? canvases/egyedi_solver/rotation_policy_and_instance_regression.md
?? codex/codex_checklist/egyedi_solver/determinism_and_time_budget.md
?? codex/codex_checklist/egyedi_solver/dxf_import_convention_layers.md
?? codex/codex_checklist/egyedi_solver/geometry_offset_robustness.md
?? codex/codex_checklist/egyedi_solver/rotation_policy_and_instance_regression.md
?? codex/codex_checklist/egyedi_solver_p1_scaffold.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_determinism_and_time_budget.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_dxf_import_convention_layers.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_geometry_offset_robustness.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_rotation_policy_and_instance_regression.yaml
?? codex/prompts/egyedi_solver/determinism_and_time_budget/
?? codex/prompts/egyedi_solver/dxf_import_convention_layers/
?? codex/prompts/egyedi_solver/geometry_offset_robustness/
?? codex/prompts/egyedi_solver/rotation_policy_and_instance_regression/
?? codex/reports/egyedi_solver/determinism_and_time_budget.md
?? codex/reports/egyedi_solver/dxf_import_convention_layers.md
?? codex/reports/egyedi_solver/geometry_offset_robustness.md
?? codex/reports/egyedi_solver/rotation_policy_and_instance_regression.md
?? codex/reports/egyedi_solver_p1_scaffold.md
?? codex/reports/egyedi_solver_p1_scaffold.verify.log
```

<!-- AUTO_VERIFY_END -->
