# Codex checklist - p1_python_dependency_management_reproducible_install

## Kotelezo (felderites)

- [x] Elolvastam: `AGENTS.md`
- [x] Elolvastam: `canvases/egyedi_solver/p1_python_dependency_management_reproducible_install.md`
- [x] Elolvastam: `codex/goals/canvases/egyedi_solver/fill_canvas_p1_python_dependency_management_reproducible_install.yaml`
- [x] Felmerve: Python deps install pontok (`scripts/check.sh`, `scripts/run_sparrow_smoketest.sh`, workflow-k)

## Kotelezo (implementacio)

- [x] Letrejott: `requirements.in`
- [x] Letrejott: `requirements-dev.in`
- [x] Letrejott: `requirements.txt`
- [x] Letrejott: `requirements-dev.txt`
- [x] Frissult: `scripts/check.sh`
- [x] Frissult: `scripts/run_sparrow_smoketest.sh`
- [x] Frissult: `.github/workflows/repo-gate.yml`
- [x] Frissult: `.github/workflows/sparrow-smoketest.yml`
- [x] Frissult: `.github/workflows/nesttool-smoketest.yml`
- [x] Frissult: `docs/qa/testing_guidelines.md`
- [x] Frissult: `docs/qa/dry_run_checklist.md`
- [x] Frissult: `docs/codex/overview.md`
- [x] Frissult: `AGENTS.md`

## DoD (canvas alapjan)

- [x] Reprodukálható requirements `.in` + pinelt `.txt` fájlok létrejöttek
- [x] Script tippek `requirements-dev.txt` telepítésre mutatnak
- [x] CI workflow-k Python deps telepítése konzisztensen a pinelt requirements-ből történik
- [x] Dokumentáció rögzíti az install/update szabályt (`.in` + `piptools compile`)
- [x] Verify PASS: `./scripts/verify.sh --report codex/reports/egyedi_solver/p1_python_dependency_management_reproducible_install.md`

## Minosegkapu

- [x] Lefutott: `./scripts/verify.sh --report codex/reports/egyedi_solver/p1_python_dependency_management_reproducible_install.md`
- [x] Letrejott/frissult: `codex/reports/egyedi_solver/p1_python_dependency_management_reproducible_install.verify.log`
- [x] Lefutott: `./scripts/check.sh`
