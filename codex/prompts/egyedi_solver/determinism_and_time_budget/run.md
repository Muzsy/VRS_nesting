# VRS Nesting Codex Task - Determinizmus + idokeret enforcement
TASK_SLUG: determinism_and_time_budget

Olvasd el:
- AGENTS.md
- canvases/egyedi_solver/determinism_and_time_budget.md
- codex/goals/canvases/egyedi_solver/fill_canvas_determinism_and_time_budget.yaml

Majd hajtsd vegre a YAML `steps` lepeseit sorrendben.

Szabalyok:
- Csak olyan fajlt hozhatsz letre / modosithetsz, ami szerepel valamely step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd (ne rogtanozz uj, parhuzamos check parancsokat).
- P0 regresszio guard: a `scripts/check.sh` gate ne romoljon; a P0 verify logok ne seruljenek.

A vegen futtasd a standard gate-et (report+log frissitessel):
- ./scripts/verify.sh --report codex/reports/egyedi_solver/determinism_and_time_budget.md
  (ez letrehozza/frissiti: codex/reports/egyedi_solver/determinism_and_time_budget.verify.log, es a report AUTO_VERIFY blokkjat)

Eredmeny:
- Frissitsd a kovetkezoket (ha a YAML outputs-ban szerepelnek):
  - codex/codex_checklist/egyedi_solver/determinism_and_time_budget.md
  - codex/reports/egyedi_solver/determinism_and_time_budget.md
  - codex/reports/egyedi_solver/determinism_and_time_budget.verify.log
- Add meg a vegleges fajltartalmakat.
