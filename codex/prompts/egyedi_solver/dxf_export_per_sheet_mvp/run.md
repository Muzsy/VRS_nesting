# VRS Nesting Codex Task - DXF export sheet-enkent (MVP)
TASK_SLUG: dxf_export_per_sheet_mvp

Olvasd el:
- AGENTS.md
- canvases/egyedi_solver/dxf_export_per_sheet_mvp.md
- codex/goals/canvases/egyedi_solver/fill_canvas_dxf_export_per_sheet_mvp.yaml

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd (ne rogtanozz uj, parhuzamos check parancsokat).

A vegen futtasd a standard gate-et (report+log frissitessel):
- ./scripts/verify.sh --report codex/reports/egyedi_solver/dxf_export_per_sheet_mvp.md
  (ez letrehozza/frissiti: codex/reports/egyedi_solver/dxf_export_per_sheet_mvp.verify.log, es a report AUTO_VERIFY blokkjat)

Eredmeny:
- Frissitsd a kovetkezoket (ha a YAML outputs-ban szerepelnek):
  - codex/codex_checklist/egyedi_solver/dxf_export_per_sheet_mvp.md
  - codex/reports/egyedi_solver/dxf_export_per_sheet_mvp.md
  - codex/reports/egyedi_solver/dxf_export_per_sheet_mvp.verify.log
- Add meg a vegleges fajltartalmakat.
