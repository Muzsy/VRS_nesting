# VRS Nesting Codex Task - Polygonize + offset robusztussag
TASK_SLUG: geometry_offset_robustness

Olvasd el:
- AGENTS.md
- canvases/egyedi_solver/geometry_offset_robustness.md
- codex/goals/canvases/egyedi_solver/fill_canvas_geometry_offset_robustness.yaml

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd (ne rogtanozz uj, parhuzamos check parancsokat).
- P0 regresszio guard: a `scripts/check.sh` gate ne romoljon; a P0 verify logok ne seruljenek.

A vegen futtasd a standard gate-et (report+log frissitessel):
- ./scripts/verify.sh --report codex/reports/egyedi_solver/geometry_offset_robustness.md
  (ez letrehozza/frissiti: codex/reports/egyedi_solver/geometry_offset_robustness.verify.log, es a report AUTO_VERIFY blokkjat)

Eredmeny:
- Frissitsd a kovetkezoket (ha a YAML outputs-ban szerepelnek):
  - codex/codex_checklist/egyedi_solver/geometry_offset_robustness.md
  - codex/reports/egyedi_solver/geometry_offset_robustness.md
  - codex/reports/egyedi_solver/geometry_offset_robustness.verify.log
- Add meg a vegleges fajltartalmakat.
