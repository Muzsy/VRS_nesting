# Codex checklist - p0_mypy_type_check_infra

## Kotelezo (felderites)

- [x] Elolvastam: `AGENTS.md`
- [x] Elolvastam: `canvases/egyedi_solver/p0_mypy_type_check_infra.md`
- [x] Elolvastam: `codex/goals/canvases/egyedi_solver/fill_canvas_p0_mypy_type_check_infra.yaml`
- [x] Igazolva: mypy konfiguracio hianyzott (`mypy.ini` nem letezett)
- [x] Igazolva: standard gate a `scripts/check.sh`, wrapper a `scripts/verify.sh`, CI gate a `.github/workflows/repo-gate.yml`

## Kotelezo (implementacio)

- [x] Letrejott: `mypy.ini`
- [x] Frissult: `vrs_nesting/nesting/instances.py`
- [x] Frissult: `vrs_nesting/geometry/polygonize.py`
- [x] Frissult: `vrs_nesting/dxf/importer.py`
- [x] Frissult: `vrs_nesting/dxf/exporter.py`
- [x] Frissult: `vrs_nesting/runner/sparrow_runner.py`
- [x] Frissult: `scripts/check.sh` (mypy fail-fast bekotve)
- [x] Frissult: `.github/workflows/repo-gate.yml` (mypy install)
- [x] Frissult: `docs/qa/testing_guidelines.md`
- [x] Frissult: `docs/qa/dry_run_checklist.md`
- [x] Frissult: `docs/codex/overview.md`
- [x] Frissult: `AGENTS.md`

## DoD (canvas alapjan)

- [x] `python3 -m mypy --config-file mypy.ini vrs_nesting` PASS
- [x] `scripts/check.sh` futtatja a mypy-t fail-fast modon, install tippel
- [x] `repo-gate` workflow telepiti a mypy-t es a gate futtatasa kompatibilis
- [x] Doksikban a mypy a standard futtatas resze
- [x] Verify PASS: `./scripts/verify.sh --report codex/reports/egyedi_solver/p0_mypy_type_check_infra.md`

## Minosegkapu

- [x] Lefutott: `./scripts/verify.sh --report codex/reports/egyedi_solver/p0_mypy_type_check_infra.md`
- [x] Letrejott/frissult: `codex/reports/egyedi_solver/p0_mypy_type_check_infra.verify.log`
- [x] Lefutott: `./scripts/check.sh`
