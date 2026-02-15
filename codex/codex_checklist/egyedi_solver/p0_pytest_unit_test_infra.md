# Codex checklist - p0_pytest_unit_test_infra

## Kotelezo (felderites)

- [x] Elolvastam: `AGENTS.md`
- [x] Elolvastam: `canvases/egyedi_solver/p0_pytest_unit_test_infra.md`
- [x] Elolvastam: `codex/goals/canvases/egyedi_solver/fill_canvas_p0_pytest_unit_test_infra.yaml`
- [x] Igazolva: pytest infrastruktura kezdetben hianyzott (`tests/`, `pytest.ini`, `test_*.py`)

## Kotelezo (implementacio)

- [x] Letrejott: `pytest.ini` (`testpaths = tests`)
- [x] Letrejott: `tests/test_dxf_importer_json_fixture.py`
- [x] Letrejott: `tests/test_project_model_validation.py`
- [x] Letrejott: `tests/test_run_dir.py`
- [x] Frissult: `scripts/check.sh` (pytest fail-fast gate elejen)
- [x] Frissult: `.github/workflows/nesttool-smoketest.yml` (pytest install + run)
- [x] Frissult: `.github/workflows/sparrow-smoketest.yml` (pytest install + run)
- [x] Frissult: `docs/qa/testing_guidelines.md`
- [x] Frissult: `docs/qa/dry_run_checklist.md`
- [x] Frissult: `docs/codex/overview.md`
- [x] Frissult: `AGENTS.md`

## DoD (canvas alapjan)

- [x] `python3 -m pytest -q` PASS lokalisan
- [x] `scripts/check.sh` elejen pytest fail-fast fut
- [x] CI-ben mindket workflow futtat pytest-et
- [x] Docs frissitve: `docs/qa/testing_guidelines.md`, `docs/codex/overview.md`
- [x] Docs szabaly rogzitve: uj teszt tipus -> gate + docs egyutt frissitendo
- [x] `AGENTS.md` tooling elvaras kozt pytest szerepel
- [x] Repo gate PASS: `./scripts/verify.sh --report codex/reports/egyedi_solver/p0_pytest_unit_test_infra.md`

## Minosegkapu

- [x] Lefutott: `./scripts/verify.sh --report codex/reports/egyedi_solver/p0_pytest_unit_test_infra.md`
- [x] Letrejott/frissult: `codex/reports/egyedi_solver/p0_pytest_unit_test_infra.verify.log`
- [x] Lefutott: `./scripts/check.sh`
