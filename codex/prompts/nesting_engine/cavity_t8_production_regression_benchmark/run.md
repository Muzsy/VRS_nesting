# DXF Nesting Platform Codex Task - Cavity T8 production regression benchmark
TASK_SLUG: cavity_t8_production_regression_benchmark

## Szerep
Senior performance/regression agent vagy. Evidence-first benchmark es rollout
dontesi taskot vegzel.

## Cel
Hasonlitsd ossze a legacy es `quality_cavity_prepack` futast ugyanazon
production/trial snapshoton, ha az T0 utan elerheto. Keszits rollout decision
doksit, de ne allitsd at a `quality_default` profilt.

## Olvasd el eloszor
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `codex/reports/nesting_engine/cavity_t0_artifact_recovery_and_baseline_replay.md`
- `codex/reports/nesting_engine/cavity_t2_runtime_profile_prepack_mode.md`
- `codex/reports/nesting_engine/cavity_t3_worker_cavity_prepack_v1.md`
- `codex/reports/nesting_engine/cavity_t4_worker_integration_and_artifacts.md`
- `codex/reports/nesting_engine/cavity_t5_result_normalizer_expansion.md`
- `scripts/run_h3_quality_benchmark.py`
- `rust/nesting_engine/src/main.rs`
- `rust/nesting_engine/src/search/sa.rs`
- `rust/nesting_engine/src/multi_bin/greedy.rs`
- `canvases/nesting_engine/cavity_t8_production_regression_benchmark.md`
- `codex/goals/canvases/nesting_engine/fill_canvas_cavity_t8_production_regression_benchmark.yaml`

## Engedelyezett modositas
Csak a YAML `outputs` listaja. Core logic fix tilos ebben a taskban; ha hibat
talalsz, dokumentald es nyiss visszacsatolast a megfelelo korabbi taskhoz.

## Szigoru tiltasok
- Ne noveld csak timeoutot/work_budgetet.
- Ne nyomd el a fallback warningot.
- Ne allitsd at a `quality_default` profilt.
- Ne bizonyits part_code csoportot, ha a snapshot nem tartalmazza.

## Elvart parancsok
- `python3 scripts/smoke_cavity_t8_production_regression_benchmark.py`
- Ha relevans: `python3 scripts/run_h3_quality_benchmark.py --plan-only ...`
- Legacy es prepack replay parancsok `NESTING_ENGINE_EMIT_NFP_STATS=1` mellett,
  ha input elerheto.
- `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t8_production_regression_benchmark.md`

## Stop conditions
Allj meg PASS_WITH_NOTES vagy FAIL reporttal, ha production snapshot nem
elerheto. Ne helyettesitsd talalgatott production adattal; synthetic fallback
csak kulon jelolve hasznalhato.

## Report nyelve es formatuma
A report magyarul keszuljon. Legyen legacy vs prepack tablazat:
effective placer, fallback warning, placed/unplaced, elapsed, NFP stats, BLF
profile, SA profile, es rollout dontes.
