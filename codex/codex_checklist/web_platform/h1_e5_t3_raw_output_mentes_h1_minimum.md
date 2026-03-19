# Codex checklist - h1_e5_t3_raw_output_mentes_h1_minimum

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Keszult explicit raw artifact helper: `worker/raw_output_artifacts.py`
- [x] A canonical path kepzes H0 policy szerint tortenik (`projects/{project_id}/runs/{run_id}/{artifact_kind}/{content_hash}.{ext}`)
- [x] A raw output mentes default bucketje `run-artifacts` (`RUN_ARTIFACTS_BUCKET`)
- [x] A worker csak projecthez tartozo snapshot `project_id`-val kepzi a canonical prefixet
- [x] A `solver_stdout.log` / `solver_stderr.log` / `solver_output.json` / `runner_meta.json` / `run.log` raw output lista explicit
- [x] Az `app.run_artifacts` regisztracio idempotens (`ON CONFLICT (run_id, storage_path) DO UPDATE`)
- [x] A worker nem megy hamis success-be upload-hiba miatt (a run allapotot tovabbra a process lifecycle vezerli)
- [x] A runner ir `run.log`-ot success/failure/timeout/missing-output agban
- [x] Letrejott task-specifikus smoke script: `scripts/smoke_h1_e5_t3_raw_output_mentes_h1_minimum.py`
- [x] `python3 -m py_compile worker/main.py worker/raw_output_artifacts.py worker/queue_lease.py worker/engine_adapter_input.py vrs_nesting/runner/vrs_solver_runner.py scripts/smoke_h1_e5_t3_raw_output_mentes_h1_minimum.py` PASS
- [x] `python3 scripts/smoke_h1_e5_t3_raw_output_mentes_h1_minimum.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h1_e5_t3_raw_output_mentes_h1_minimum.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
