# Codex checklist - h1_e5_t2_solver_process_futtatas_h1_minimum

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] A worker canonical solver futtatasi utja snapshot-input alapu
- [x] A legacy `python -m vrs_nesting.cli dxf-run ...` kikerult a canonical worker process utbol
- [x] Keszult explicit solver runner bridge (`SolverRunnerInvocation` + `_build_solver_runner_invocation`)
- [x] A worker tovabbra is tartja a lease/heartbeat/cancel/timeout vedelmeket
- [x] Runner/invalid output hiba eseten nincs hamis success
- [x] A task nem nyit raw output storage / result normalizer / artifact redesign scope-ot
- [x] Keszult task-specifikus smoke: `scripts/smoke_h1_e5_t2_solver_process_futtatas_h1_minimum.py`
- [x] `python3 -m py_compile worker/main.py worker/engine_adapter_input.py worker/queue_lease.py vrs_nesting/runner/vrs_solver_runner.py scripts/smoke_h1_e5_t2_solver_process_futtatas_h1_minimum.py` PASS
- [x] `python3 scripts/smoke_h1_e5_t2_solver_process_futtatas_h1_minimum.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h1_e5_t2_solver_process_futtatas_h1_minimum.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
