# Codex checklist - cavity_t0_artifact_recovery_and_baseline_replay

- [x] AGENTS.md + Codex szabalyok + T0 canvas/YAML/prompt atnezve
- [x] `api/routes/runs.py` artifact URL recovery logika bucket fallbackgel bovitve
- [x] Uj unit teszt keszult: `tests/test_run_artifact_url_recovery.py`
- [x] Uj smoke keszult: `scripts/smoke_cavity_t0_artifact_recovery_and_baseline_replay.py`
- [x] `python3 -m pytest -q tests/test_run_artifact_url_recovery.py` PASS
- [x] `python3 scripts/smoke_cavity_t0_artifact_recovery_and_baseline_replay.py` PASS
- [x] `python3 -m py_compile api/routes/runs.py tests/test_run_artifact_url_recovery.py scripts/smoke_cavity_t0_artifact_recovery_and_baseline_replay.py` PASS
- [x] Baseline legacy hiba bizonyitek (`fallback to blf`, `TIME_LIMIT_EXCEEDED`) dokumentalva lokalis repro artifactokkal
- [ ] Production run artifact URL javitas eloben, valos API ellen ujrafuttatassal bizonyitva (kulso hozzaferesi blokk)
- [ ] Production run 1:1 replay uj letoltott `solver_input` + `engine_meta` alapjan (kulso hozzaferesi blokk)
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t0_artifact_recovery_and_baseline_replay.md` PASS
