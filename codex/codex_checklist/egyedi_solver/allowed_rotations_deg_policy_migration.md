# Codex checklist - allowed_rotations_deg_policy_migration

## Kotelezo (felderites)

- [x] Elolvastam: `AGENTS.md`
- [x] Elolvastam: `docs/codex/overview.md`
- [x] Elolvastam: `docs/codex/yaml_schema.md`
- [x] Elolvastam: `docs/codex/report_standard.md`
- [x] Elolvastam: `canvases/egyedi_solver/allowed_rotations_deg_policy_migration.md`
- [x] Elolvastam: `codex/goals/canvases/egyedi_solver/fill_canvas_allowed_rotations_deg_policy_migration.yaml`

## Kotelezo (implementacio)

- [x] Frissult: `docs/mvp_project_schema.md` (`allowed_rotations_deg` policy)
- [x] Frissult: `docs/solver_io_contract.md` (`allowed_rotations_deg` policy)
- [x] Frissult: `vrs_nesting/project/model.py` (listaalapu rotacio parse/validacio)
- [x] Frissult: `rust/vrs_solver/src/main.rs` (listaalapu rotacios placement + fit-check)
- [x] Frissult: `vrs_nesting/nesting/instances.py` (validator listaalapu rotacios check)
- [x] Frissult: `vrs_nesting/dxf/exporter.py` (export listaalapu rotacios check)
- [x] Frissult: `scripts/check.sh` (smoke input `allowed_rotations_deg`)
- [x] Frissult: `.github/workflows/nesttool-smoketest.yml` (CI smoke input `allowed_rotations_deg`)
- [x] Frissult: `samples/project_rect_1000x2000.json`

## Minosegkapu

- [x] Lefutott: `./scripts/verify.sh --report codex/reports/egyedi_solver/allowed_rotations_deg_policy_migration.md`
- [x] Letrejott/frissult: `codex/reports/egyedi_solver/allowed_rotations_deg_policy_migration.verify.log`
- [x] Report AUTO_VERIFY blokk frissult
