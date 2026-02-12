# VRS Nesting Codex Task - DXF import konvenciok + clean pipeline
TASK_SLUG: dxf_import_convention_layers

Olvasd el:
- AGENTS.md
- canvases/egyedi_solver/dxf_import_convention_layers.md
- codex/goals/canvases/egyedi_solver/fill_canvas_dxf_import_convention_layers.yaml

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd (ne rogtanozz uj, parhuzamos check parancsokat).
- P0 regresszio guard: a `scripts/check.sh` gate ne romoljon; a P0 verify logok ne seruljenek.

A vegen futtasd a standard gate-et (report+log frissitessel):
- ./scripts/verify.sh --report codex/reports/egyedi_solver/dxf_import_convention_layers.md
  (ez letrehozza/frissiti: codex/reports/egyedi_solver/dxf_import_convention_layers.verify.log, es a report AUTO_VERIFY blokkjat)

Eredmeny:
- Frissitsd a kovetkezoket (ha a YAML outputs-ban szerepelnek):
  - codex/codex_checklist/egyedi_solver/dxf_import_convention_layers.md
  - codex/reports/egyedi_solver/dxf_import_convention_layers.md
  - codex/reports/egyedi_solver/dxf_import_convention_layers.verify.log
- Add meg a vegleges fajltartalmakat.
