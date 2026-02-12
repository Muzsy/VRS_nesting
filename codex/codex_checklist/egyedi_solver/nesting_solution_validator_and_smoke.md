# Codex checklist - nesting_solution_validator_and_smoke

## Kotelezo (felderites)

- [x] Elolvastam: `AGENTS.md`
- [x] Elolvastam: `canvases/egyedi_solver/nesting_solution_validator_and_smoke.md`
- [x] Elolvastam: `codex/goals/canvases/egyedi_solver/fill_canvas_nesting_solution_validator_and_smoke.yaml`
- [x] Atneztem: `scripts/check.sh` es `.github/workflows/sparrow-smoketest.yml`

## Kotelezo (implementacio)

- [x] Letrejott: `scripts/validate_nesting_solution.py`
- [x] Letrejott: `.github/workflows/nesttool-smoketest.yml`
- [x] Frissult: `scripts/check.sh` (uj nesting smoke + validator gate)
- [x] Validator ellenorzi: in-bounds, no-overlap, rotation policy, coverage
- [x] Validator hole policy szabaly implementalva (MVP-ben holes tiltva)
- [x] Failure artifact mentes workflowban beallitva

## Minosegkapu

- [x] Lefutott: `./scripts/verify.sh --report codex/reports/egyedi_solver/nesting_solution_validator_and_smoke.md`
- [x] Letrejott/frissult: `codex/reports/egyedi_solver/nesting_solution_validator_and_smoke.verify.log`
- [x] Report AUTO_VERIFY blokk frissult
