# Codex checklist - h3_quality_t6_local_tool_backend_selector_and_ab_compare

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] A `TrialRunConfig` explicit `engine_backend` mezot kapott (`auto | sparrow_v1 | nesting_engine_v2`)
- [x] A CLI `--engine-backend` argumentummal vezerlheto a kert backend
- [x] A GUI backend selector combobox default `auto`-val mukodik
- [x] A platform start/restart subprocess `WORKER_ENGINE_BACKEND` env override-ot kap konkret backend eseten
- [x] A `quality_summary.json` tartalmazza: `requested_engine_backend`, `effective_engine_backend`, `engine_backend_match`
- [x] A `summary.md` tartalmazza a `requested_engine_backend` erteket
- [x] A benchmark runner `--engine-backend` (repeatable) es `--compare-backends` argumentumokat kapott
- [x] A benchmark runner `--plan-only --compare-backends` modban determinisztikus case x backend matrixot ir
- [x] A benchmark output `compare_results` delta blokkot ad azonos case ket backendes futasahoz
- [x] A compare delta blokk evidence-first, hibaturo (incomplete_reason ha valamelyik oldal hianyzik)
- [x] Keszult task-specifikus smoke script: `scripts/smoke_h3_quality_t6_local_tool_backend_selector_and_ab_compare.py`
- [x] `python3 -m py_compile scripts/trial_run_tool_core.py scripts/run_trial_run_tool.py scripts/trial_run_tool_gui.py scripts/run_h3_quality_benchmark.py scripts/smoke_h3_quality_t6_local_tool_backend_selector_and_ab_compare.py` PASS
- [x] `python3 scripts/smoke_h3_quality_t6_local_tool_backend_selector_and_ab_compare.py` PASS
- [x] Meglevo regresszio smoke-ok: `smoke_trial_run_tool_cli_core.py`, `smoke_h3_quality_t2_benchmark_pack_and_quality_summary_harness.py`, `smoke_trial_run_tool_tkinter_gui.py` PASS
- [x] Report DoD -> Evidence matrix kitoltve
