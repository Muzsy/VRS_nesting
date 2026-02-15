# Codex checklist - p1_3_sparrow_dependency_risk_reduction_vendor_fallback

## Kotelezo (felderites)

- [x] Elolvastam: `AGENTS.md`
- [x] Elolvastam: `canvases/egyedi_solver/p1_3_sparrow_dependency_risk_reduction_vendor_fallback.md`
- [x] Elolvastam: `codex/goals/canvases/egyedi_solver/fill_canvas_p1_3_sparrow_dependency_risk_reduction_vendor_fallback.yaml`
- [x] Feltarva: Sparrow clone/pin/build belépési pontok (`scripts/check.sh`, `.github/workflows/sparrow-smoketest.yml`)

## Kotelezo (implementacio)

- [x] Letrejott: `scripts/ensure_sparrow.sh`
- [x] Frissult: `scripts/check.sh` (Sparrow resolver centralizalas)
- [x] Frissult: `.github/workflows/sparrow-smoketest.yml`
- [x] Frissult: `.github/workflows/repo-gate.yml`
- [x] Frissult: `docs/qa/testing_guidelines.md`
- [x] Frissult: `AGENTS.md`
- [x] Letrejott: `vendor/README.md`
- [x] Frissult: `codex/codex_checklist/egyedi_solver/p1_3_sparrow_dependency_risk_reduction_vendor_fallback.md`
- [x] Frissult: `codex/reports/egyedi_solver/p1_3_sparrow_dependency_risk_reduction_vendor_fallback.md`

## DoD (canvas alapjan)

- [x] Letrejott `scripts/ensure_sparrow.sh` prioritasi szabalyokkal, stdout csak bin path
- [x] `scripts/check.sh` `ensure_sparrow.sh`-t hasznal explicit `SPARROW_BIN` mellett is kompatibilisen
- [x] `sparrow-smoketest.yml` `ensure_sparrow.sh`-t hasznal es `submodules: recursive` beallitva
- [x] `repo-gate.yml` checkout `submodules: recursive`
- [x] `docs/qa/testing_guidelines.md` es `AGENTS.md` Sparrow dependency logikara frissitve
- [x] Verify PASS: `./scripts/verify.sh --report codex/reports/egyedi_solver/p1_3_sparrow_dependency_risk_reduction_vendor_fallback.md`

## Minosegkapu

- [x] Lefutott: `./scripts/verify.sh --report codex/reports/egyedi_solver/p1_3_sparrow_dependency_risk_reduction_vendor_fallback.md`
- [x] Letrejott/frissult: `codex/reports/egyedi_solver/p1_3_sparrow_dependency_risk_reduction_vendor_fallback.verify.log`
- [x] Lefutott: `./scripts/check.sh`
