# Codex checklist - h3_quality_t1_engine_observability_and_artifact_truth

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Felderites: worker/viewer/trial tool jelenlegi artifact truth allapota rogzitve a canvasban
- [x] A `worker/main.py`-ban a canonical solver input artifact egyertelmuen regisztralva
- [x] Engine meta (backend, contract_version, profile) explicit artifact/meta-kent rogzitve a run-hoz
- [x] Az `api/routes/runs.py` viewer-data elsokorben a canonical solver_input artifact-bol olvas
- [x] A viewer determinisztikus fallback logikaja biztositva snapshot jellegu input eseten
- [x] A `scripts/trial_run_tool_core.py` summary bovitve: backend, contract_version, artifact jelenlet, completeness
- [x] Task-specifikus smoke: `scripts/smoke_h3_quality_t1_engine_observability_and_artifact_truth.py` letrehozva es zold
- [x] `python3 -m py_compile worker/main.py api/routes/runs.py scripts/trial_run_tool_core.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t1_engine_observability_and_artifact_truth.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
