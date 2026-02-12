# Codex checklist — egyedi_solver_backlog

## Kötelező (felderítés)

- [x] Elolvastam: `AGENTS.md`
- [x] Elolvastam: `docs/codex/overview.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`, `docs/codex/prompt_template.md`
- [x] Elolvastam: `codex/prompts/task_runner_prompt_template.md`
- [x] Megnéztem legalább 2 canvas mintát: `canvases/codex_bootstrap.md`, `canvases/sparrow_runner_module.md`
- [x] Megnéztem legalább 2 goal YAML mintát: `codex/goals/canvases/fill_canvas_codex_bootstrap.yaml`, `codex/goals/canvases/fill_canvas_sparrow_runner_module.yaml`

## Kötelező (doksi/kód evidence)

- [x] A 4 megadott `tmp/egyedi_solver/*` dokumentum felderítve és feldolgozva
- [x] Releváns kód belépési pontok listázva path + rövid szerepleírással
- [x] Hiányzó modulok explicit `NINCS: <path>` formában rögzítve

## Kötelező (backlog)

- [x] Elkészült a P0-P3 backlog prioritással
- [x] Minden backlog task egyedi, ASCII snake_case `TASK_SLUG`-ot kapott
- [x] Minden backlog task tartalmaz DoD + kockázat/mitigáció mezőt

## Kötelező artefaktok ebben a runban

- [x] `canvases/egyedi_solver_backlog.md`
- [x] `codex/reports/egyedi_solver_backlog.md`
- [x] `codex/codex_checklist/egyedi_solver_backlog.md`

## Minőségkapu

- [x] Lefutott: `./scripts/verify.sh --report codex/reports/egyedi_solver_backlog.md`
- [x] Létrejött/frissült: `codex/reports/egyedi_solver_backlog.verify.log`
- [x] Report AUTO_VERIFY blokk frissült
