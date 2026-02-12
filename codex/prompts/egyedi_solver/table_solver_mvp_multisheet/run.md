# VRS Nesting Codex Task - Tablas MVP solver + multi-sheet ciklus
TASK_SLUG: table_solver_mvp_multisheet

Olvasd el:
- AGENTS.md
- canvases/egyedi_solver/table_solver_mvp_multisheet.md
- codex/goals/canvases/egyedi_solver/fill_canvas_table_solver_mvp_multisheet.yaml

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd (ne rogtanozz uj, parhuzamos check parancsokat).

A vegen futtasd a standard gate-et (report+log frissitessel):
- ./scripts/verify.sh --report codex/reports/egyedi_solver/table_solver_mvp_multisheet.md
  (ez letrehozza/frissiti: codex/reports/egyedi_solver/table_solver_mvp_multisheet.verify.log, es a report AUTO_VERIFY blokkjat)

Eredmeny:
- Frissitsd a kovetkezoket (ha a YAML outputs-ban szerepelnek):
  - codex/codex_checklist/egyedi_solver/table_solver_mvp_multisheet.md
  - codex/reports/egyedi_solver/table_solver_mvp_multisheet.md
  - codex/reports/egyedi_solver/table_solver_mvp_multisheet.verify.log
- Add meg a vegleges fajltartalmakat.
