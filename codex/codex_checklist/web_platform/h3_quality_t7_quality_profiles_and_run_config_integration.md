# Codex checklist - h3_quality_t7_quality_profiles_and_run_config_integration

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Letrejott a kanonikus quality-profile registry (`fast_preview`, `quality_default`, `quality_aggressive`)
- [x] A quality-profile mapping egyetlen source of truth modulban van (`vrs_nesting/config/nesting_quality_profiles.py`)
- [x] A `nesting_engine_runner.py` opcionis quality CLI flag-eket fogad es tovabbit
- [x] A runner metadata visszaadja a tenylegesen hasznalt `nesting_engine_cli_args` listat
- [x] A snapshot `solver_config_jsonb` explicit `quality_profile` truthot es `nesting_engine_runtime_policy` blokkot ir
- [x] A worker runtime override (`WORKER_QUALITY_PROFILE`) es snapshot truth alapjan resolved profile-t hasznal
- [x] A worker `engine_meta.json` requested vs effective profile mezoket es `nesting_engine_cli_args` evidence-t ir
- [x] A `sparrow_v1` + explicit profile kombinacio egyertelmu noop-kent van kezelve (`effective_engine_profile=sparrow_v1_noop`)
- [x] A local tool core/CLI/GUI explicit `quality_profile` valasztast kapott
- [x] A benchmark runner `--quality-profile` (repeatable) matrixot tamogat, es profile-szintu compare csoportositast ad
- [x] Frissult a benchmark harness dokumentacio profile matrix peldakkal es profile-szintu compare mezokkel
- [x] Keszult dedikalt smoke: `scripts/smoke_h3_quality_t7_quality_profiles_and_run_config_integration.py`
- [x] `python3 -m py_compile ...` (T7 output fajlokra) PASS
- [x] `python3 scripts/smoke_h3_quality_t7_quality_profiles_and_run_config_integration.py` PASS
- [x] Regresszio smoke-ok: `smoke_h3_quality_t6_local_tool_backend_selector_and_ab_compare.py`, `smoke_trial_run_tool_tkinter_gui.py` PASS
- [x] Report DoD -> Evidence matrix kitoltve
