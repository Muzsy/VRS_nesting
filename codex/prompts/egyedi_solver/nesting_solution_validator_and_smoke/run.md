# VRS Nesting Codex Task - Tablas validacio + smoke gate
TASK_SLUG: nesting_solution_validator_and_smoke

Olvasd el:
- AGENTS.md
- canvases/egyedi_solver/nesting_solution_validator_and_smoke.md
- codex/goals/canvases/egyedi_solver/fill_canvas_nesting_solution_validator_and_smoke.yaml

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd (ne rogtanozz uj, parhuzamos check parancsokat).

A vegen futtasd a standard gate-et (report+log frissitessel):
- ./scripts/verify.sh --report codex/reports/egyedi_solver/nesting_solution_validator_and_smoke.md
  (ez letrehozza/frissiti: codex/reports/egyedi_solver/nesting_solution_validator_and_smoke.verify.log, es a report AUTO_VERIFY blokkjat)

Eredmeny:
- Frissitsd a kovetkezoket (ha a YAML outputs-ban szerepelnek):
  - codex/codex_checklist/egyedi_solver/nesting_solution_validator_and_smoke.md
  - codex/reports/egyedi_solver/nesting_solution_validator_and_smoke.md
  - codex/reports/egyedi_solver/nesting_solution_validator_and_smoke.verify.log
- Add meg a vegleges fajltartalmakat.
