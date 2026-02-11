# Task runner prompt (VRS Nesting)

Használat:

1) Nyisd meg a feladathoz tartozó fájlokat:
   - `AGENTS.md`
   - `canvases/[<AREA>/]<TASK_SLUG>.md`
   - `codex/goals/canvases/[<AREA>/]fill_canvas_<TASK_SLUG>.yaml`

2) Hajtsd végre a YAML `steps` lépéseit sorrendben.

Szabályok:

- Csak olyan fájlt hozhatsz létre / módosíthatsz, ami szerepel valamely step `outputs` listájában.
- A minőségkaput kizárólag wrapperrel futtasd.

A végén futtasd a standard gate-et (report+log frissítéssel):

- `./scripts/verify.sh --report codex/reports/[<AREA>/]<TASK_SLUG>.md`

Eredmény:

- Frissítsd (ha a YAML outputs-ban szerepelnek):
  - `codex/codex_checklist/[<AREA>/]<TASK_SLUG>.md`
  - `codex/reports/[<AREA>/]<TASK_SLUG>.md`
  - `codex/reports/[<AREA>/]<TASK_SLUG>.verify.log`
