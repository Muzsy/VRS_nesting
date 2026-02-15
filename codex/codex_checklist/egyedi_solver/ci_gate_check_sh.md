# Codex checklist - ci_gate_check_sh

## Kotelezo (felderites)

- [x] Elolvastam: `AGENTS.md`
- [x] Elolvastam: `canvases/egyedi_solver/ci_gate_check_sh.md`
- [x] Elolvastam: `codex/goals/canvases/egyedi_solver/fill_canvas_ci_gate_check_sh.yaml`
- [x] Felmerve a gate valos allapota: `scripts/check.sh`, `scripts/verify.sh`, `.github/workflows/*`

## Kotelezo (implementacio)

- [x] Frissult: `canvases/egyedi_solver/ci_gate_check_sh.md`
- [x] Frissult: `docs/qa/testing_guidelines.md`
- [x] Frissult: `docs/codex/overview.md`
- [x] Uj: `.github/workflows/repo-gate.yml`
- [x] Letrejott/frissult: `codex/codex_checklist/egyedi_solver/ci_gate_check_sh.md`
- [x] Letrejott/frissult: `codex/reports/egyedi_solver/ci_gate_check_sh.md`

## DoD (canvas alapjan)

- [x] `docs/qa/testing_guidelines.md` tartalmazza a szokasos vegfuttatast (`./scripts/check.sh`) es a fo gate lepeseket
- [x] `testing_guidelines` explicit jelzi az `ezdxf` fuggoseget a valos DXF smoke-okhoz
- [x] `docs/codex/overview.md` gate leirasa osszhangban van a `scripts/check.sh` valos lepeseivel
- [x] Uj workflow letrejott: `.github/workflows/repo-gate.yml`
- [x] Workflow trigger: `push`, `pull_request`, `workflow_dispatch`
- [x] Workflow futtatja: `./scripts/check.sh`
- [x] Workflow telepit: `python3`, `python3-pytest`, `python3-pip`, `python3-shapely`, `git`, es `pip install ezdxf`
- [x] Workflow failure eseten artifact upload van (`runs/**`, `.cache/sparrow/**`)
- [x] Verify PASS es report evidence kitoltve

## Minosegkapu

- [x] Lefutott: `./scripts/verify.sh --report codex/reports/egyedi_solver/ci_gate_check_sh.md`
- [x] Letrejott/frissult: `codex/reports/egyedi_solver/ci_gate_check_sh.verify.log`
- [x] Lefutott: `./scripts/check.sh`
