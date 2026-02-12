# Codex checklist - determinism_hash_stability_smoke

## Kotelezo (felderites)

- [x] Elolvastam: `AGENTS.md`
- [x] Elolvastam: `docs/codex/overview.md`
- [x] Elolvastam: `docs/codex/yaml_schema.md`
- [x] Elolvastam: `docs/codex/report_standard.md`
- [x] Elolvastam: `canvases/egyedi_solver/determinism_hash_stability_smoke.md`
- [x] Elolvastam: `codex/goals/canvases/egyedi_solver/fill_canvas_determinism_hash_stability_smoke.yaml`

## Kotelezo (implementacio)

- [x] Frissult: `scripts/check.sh` (kettos run hash stability check)
- [x] Frissult: `.github/workflows/nesttool-smoketest.yml` (CI determinism hash check)
- [x] `output_sha256` alapu osszehasonlitas mismatch eseten FAIL

## Minosegkapu

- [x] Lefutott: `./scripts/verify.sh --report codex/reports/egyedi_solver/determinism_hash_stability_smoke.md`
- [x] Letrejott/frissult: `codex/reports/egyedi_solver/determinism_hash_stability_smoke.verify.log`
- [x] Report AUTO_VERIFY blokk frissult
