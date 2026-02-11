Olvasd el:
- AGENTS.md
- canvases/[<AREA>/]<TASK_SLUG>.md
- codex/goals/canvases/[<AREA>/]fill_canvas_<TASK_SLUG>.yaml

Majd hajtsd végre a YAML `steps` lépéseit sorrendben.

Szabályok:
- Csak olyan fájlt hozhatsz létre / módosíthatsz, ami szerepel valamely step `outputs` listájában.
- A minőségkaput kizárólag wrapperrel futtasd (ne rögtönözz új, párhuzamos check parancsokat).

A végén futtasd a standard gate-et (report+log frissítéssel):
- ./scripts/verify.sh --report codex/reports/[<AREA>/]<TASK_SLUG>.md
  (ez létrehozza/frissíti: codex/reports/[<AREA>/]<TASK_SLUG>.verify.log, és a report AUTO_VERIFY blokkját)

Eredmény:
- Frissítsd a következőket (ha a YAML outputs-ban szerepelnek):
  - codex/codex_checklist/[<AREA>/]<TASK_SLUG>.md
  - codex/reports/[<AREA>/]<TASK_SLUG>.md
  - codex/reports/[<AREA>/]<TASK_SLUG>.verify.log
- Add meg a végleges fájltartalmakat.
