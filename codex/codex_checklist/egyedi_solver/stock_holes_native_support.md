# Codex checklist - stock_holes_native_support

## Kotelezo (felderites)

- [x] Elolvastam: `AGENTS.md`
- [x] Elolvastam: `docs/codex/overview.md`
- [x] Elolvastam: `docs/codex/yaml_schema.md`
- [x] Elolvastam: `docs/codex/report_standard.md`
- [x] Elolvastam: `canvases/egyedi_solver/stock_holes_native_support.md`
- [x] Elolvastam: `codex/goals/canvases/egyedi_solver/fill_canvas_stock_holes_native_support.yaml`

## Kotelezo (implementacio)

- [x] Frissult: `docs/solver_io_contract.md` (outer_points + holes_points)
- [x] Frissult: `rust/vrs_solver/src/main.rs` (shape+holes fit ellenorzes)
- [x] Frissult: `vrs_nesting/nesting/instances.py` (shape+holes validator)
- [x] Frissult: `scripts/validate_nesting_solution.py` (natív shape validacio)
- [x] Frissult: `scripts/check.sh` (shape+holes smoke input)
- [x] Frissult: `.github/workflows/nesttool-smoketest.yml` (shape+holes CI smoke input)

## Minosegkapu

- [x] Lefutott: `./scripts/verify.sh --report codex/reports/egyedi_solver/stock_holes_native_support.md`
- [x] Letrejott/frissult: `codex/reports/egyedi_solver/stock_holes_native_support.verify.log`
- [x] Report AUTO_VERIFY blokk frissult
