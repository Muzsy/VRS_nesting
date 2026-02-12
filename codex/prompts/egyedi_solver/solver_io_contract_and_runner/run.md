# VRS Nesting Codex Task - Solver IO contract + runner integracios reteg
TASK_SLUG: solver_io_contract_and_runner

Olvasd el:
- AGENTS.md
- canvases/egyedi_solver/solver_io_contract_and_runner.md
- codex/goals/canvases/egyedi_solver/fill_canvas_solver_io_contract_and_runner.yaml

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd (ne rogtanozz uj, parhuzamos check parancsokat).

A vegen futtasd a standard gate-et (report+log frissitessel):
- ./scripts/verify.sh --report codex/reports/egyedi_solver/solver_io_contract_and_runner.md
  (ez letrehozza/frissiti: codex/reports/egyedi_solver/solver_io_contract_and_runner.verify.log, es a report AUTO_VERIFY blokkjat)

Eredmeny:
- Frissitsd a kovetkezoket (ha a YAML outputs-ban szerepelnek):
  - codex/codex_checklist/egyedi_solver/solver_io_contract_and_runner.md
  - codex/reports/egyedi_solver/solver_io_contract_and_runner.md
  - codex/reports/egyedi_solver/solver_io_contract_and_runner.verify.log
- Add meg a vegleges fajltartalmakat.
