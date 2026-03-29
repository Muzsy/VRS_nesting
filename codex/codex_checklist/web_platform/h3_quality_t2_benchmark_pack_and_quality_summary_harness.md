# Codex checklist - h3_quality_t2_benchmark_pack_and_quality_summary_harness

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Keszult determinisztikus benchmark fixture generator (`scripts/gen_h3_quality_benchmark_fixtures.py`)
- [x] Keszult repo-local benchmark manifest legalabb 3 case-szel (`samples/trial_run_quality/benchmark_manifest_v1.json`)
- [x] Keszult benchmark lane dokumentacio (`docs/nesting_quality/h3_quality_benchmark_harness.md`)
- [x] A `scripts/trial_run_tool_core.py` futas vegere ir `quality_summary.json`-t
- [x] A quality summary tartalmazza a minimum KPI + artifact + signals mezoket
- [x] Keszult benchmark runner (`scripts/run_h3_quality_benchmark.py`)
- [x] A benchmark runner `--plan-only` modban live platform nelkul is fut
- [x] Keszult task-specifikus smoke script: `scripts/smoke_h3_quality_t2_benchmark_pack_and_quality_summary_harness.py`
- [x] `python3 -m py_compile scripts/trial_run_tool_core.py scripts/gen_h3_quality_benchmark_fixtures.py scripts/run_h3_quality_benchmark.py scripts/smoke_h3_quality_t2_benchmark_pack_and_quality_summary_harness.py` PASS
- [x] `python3 scripts/smoke_h3_quality_t2_benchmark_pack_and_quality_summary_harness.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t2_benchmark_pack_and_quality_summary_harness.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
