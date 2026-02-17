# Codex checklist - p2_run_dir_dedupe_solver_adapter_nightly_perf_baseline

## Kotelezo (felderites)

- [x] Elolvastam: `AGENTS.md`
- [x] Elolvastam: `canvases/egyedi_solver/p2_run_dir_dedupe_solver_adapter_nightly_perf_baseline.md`
- [x] Elolvastam: `codex/goals/canvases/egyedi_solver/fill_canvas_p2_run_dir_dedupe_solver_adapter_nightly_perf_baseline.yaml`
- [x] Feltarva: P2-1/P2-2/P2-3 jelenlegi implementációs pontok

## Kotelezo (implementacio)

- [x] Frissult: `vrs_nesting/runner/sparrow_runner.py` (run_dir deduplikáció)
- [x] Letrejott: `vrs_nesting/runner/solver_adapter.py`
- [x] Frissult: `vrs_nesting/runner/__init__.py`
- [x] Frissult: `vrs_nesting/pipeline/run_pipeline.py`
- [x] Frissult: `vrs_nesting/sparrow/multi_sheet_wrapper.py`
- [x] Letrejott: `tests/test_solver_adapter_contract.py`
- [x] Letrejott: `tests/test_sparrow_runner_run_dir_dedupe.py`
- [x] Frissult: `scripts/smoke_time_budget_guard.py`
- [x] Letrejott: `.github/workflows/nightly-perf-baseline.yml`
- [x] Frissult: `docs/qa/testing_guidelines.md`
- [x] Frissult: `codex/reports/egyedi_solver/p2_run_dir_dedupe_solver_adapter_nightly_perf_baseline.md`

## DoD (canvas alapjan)

- [x] Sparrow runner `create_run_dir`-t hasznal deduplikalt allokációval
- [x] Közös solver adapter boundary készen van és használt a call site-okban
- [x] Adapter contract tesztek + deduplikáció regressziós teszt elérhető
- [x] Nightly perf baseline workflow artifact + threshold summary megvan
- [x] Perf guard baseline JSON és threshold paraméter támogatott
- [x] Verify PASS: `./scripts/verify.sh --report codex/reports/egyedi_solver/p2_run_dir_dedupe_solver_adapter_nightly_perf_baseline.md`

## Minosegkapu

- [x] Lefutott: `./scripts/verify.sh --report codex/reports/egyedi_solver/p2_run_dir_dedupe_solver_adapter_nightly_perf_baseline.md`
- [x] Letrejott/frissult: `codex/reports/egyedi_solver/p2_run_dir_dedupe_solver_adapter_nightly_perf_baseline.verify.log`
