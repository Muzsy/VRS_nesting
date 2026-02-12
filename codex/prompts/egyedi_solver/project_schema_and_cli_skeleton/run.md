# VRS Nesting Codex Task - Projekt schema + CLI skeleton + run artifact alap
TASK_SLUG: project_schema_and_cli_skeleton

Olvasd el:
- AGENTS.md
- canvases/egyedi_solver/project_schema_and_cli_skeleton.md
- codex/goals/canvases/egyedi_solver/fill_canvas_project_schema_and_cli_skeleton.yaml

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd (ne rogtanozz uj, parhuzamos check parancsokat).

A vegen futtasd a standard gate-et (report+log frissitessel):
- ./scripts/verify.sh --report codex/reports/egyedi_solver/project_schema_and_cli_skeleton.md
  (ez letrehozza/frissiti: codex/reports/egyedi_solver/project_schema_and_cli_skeleton.verify.log, es a report AUTO_VERIFY blokkjat)

Eredmeny:
- Frissitsd a kovetkezoket (ha a YAML outputs-ban szerepelnek):
  - codex/codex_checklist/egyedi_solver/project_schema_and_cli_skeleton.md
  - codex/reports/egyedi_solver/project_schema_and_cli_skeleton.md
  - codex/reports/egyedi_solver/project_schema_and_cli_skeleton.verify.log
- Add meg a vegleges fajltartalmakat.
