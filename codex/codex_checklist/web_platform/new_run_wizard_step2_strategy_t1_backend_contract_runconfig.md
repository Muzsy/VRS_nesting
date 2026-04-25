# Codex checklist - new_run_wizard_step2_strategy_t1_backend_contract_runconfig

- [x] Canvas + goal YAML + run prompt artefaktok veglegesitve
- [x] Uj migration letrejott: `20260425110000_new_run_wizard_step2_strategy_t1_runconfig_contract.sql`
- [x] `app.run_configs` strategia mezoi (strategy version + overrides JSONB) schema es bridge szinten bekotve
- [x] `POST /projects/{project_id}/run-configs` request/response/list contract bovitve
- [x] Strategy version owner + active validacio bekerult
- [x] Solver override whitelist es validacio bekerult (`quality_profile`, `sa_eval_budget_sec`, `nesting_engine_runtime_policy`, `engine_backend_hint`)
- [x] `POST /projects/{project_id}/runs` request modell T1 mezokkel bovitve
- [x] `run_creation` run_config scope validacio + `nesting_runs.run_config_id` persistence megvalositva
- [x] `request_payload_jsonb` audit mezok T1 contract szerint bovitve
- [x] Snapshot builder explicit request override truth tamogatas bekotve
- [x] Strategy selection loader select payload bovitve (`solver_config_jsonb`, `placement_config_jsonb`, `manufacturing_bias_jsonb`)
- [x] Dedikalt smoke kesz: `scripts/smoke_new_run_wizard_step2_strategy_t1_backend_contract_runconfig.py`
- [x] `python3 -m py_compile ...` PASS
- [x] `python3 scripts/smoke_new_run_wizard_step2_strategy_t1_backend_contract_runconfig.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/new_run_wizard_step2_strategy_t1_backend_contract_runconfig.md` PASS
- [x] Report DoD -> Evidence matrix es AUTO_VERIFY blokk kesz
