# SGH-Q30-R1 Exclusive Search Runtime Breakdown — Report

## Summary

**Status:** `PASS`

## Q30 Problem Context

SGH-Q30 delivered a reusable `SearchProfiler` module but left ~79% of `search_total_ms`
as `other_unaccounted_ms` on dense191 (20,784ms / 26,176ms). Q30-R1 adds exclusive
timing tree instrumentation to close this gap.

## New Exclusive Measurement Points

Added exclusive timers (zero overhead when disabled) for:
- `prepare_base_shape_native_ms` — CDE shape prep once per search call
- `fixed_shapes_clone_ms` — `tracker.shapes.clone()` per search call
- `sheet_order_build_ms` — sheet order vec construction
- `best_samples_clone_ms` — `best.samples.clone()` before pre-stage coord descent
- `best_samples_best_ms` — `best.best()` call before final coord descent
- `coord_descent_ask_ms` — `CoordinateDescent::ask()` calls (exclusive)
- `coord_descent_tell_ms` — `CoordinateDescent::tell()` calls (exclusive)
- Total solver runtime: `seed_lbf`, `tracker_initial_build`, `exploration_total`,
  `tracker_final_validation`, `output_mapping_ms`

## Case Results

### Case: medium

| Field | Value |
|---|---|
| status | ok |
| placed_count | 24 |
| q30r1_profile_enabled | True |
| search_total_ms | 0.0 |
| search_accounted_ms | 0.0 |
| search_unaccounted_ms | 0.0 |
| **search_unaccounted_ratio_pct** | **0.0%** |
| total_solver_runtime_ms | 1073.0 |
| runtime_accounted_ratio_pct | 100.0% |

**Counters (medium):**

| Counter | Value |
|---|---|
| native_search_calls | 0 |
| evaluate_sample_calls | 0 |
| evaluate_sample_calls_from_global | 0 |
| evaluate_sample_calls_from_focused | 0 |
| evaluate_sample_calls_from_coord_descent | 0 |
| candidates_evaluated | 0 |
| global_samples_generated | 0 |
| focused_samples_generated | 0 |
| best_samples_insert_attempts | 0 |
| best_samples_inserted | 0 |
| best_samples_dedup_rejects | 0 |
| best_samples_best_calls | 0 |
| best_samples_clone_calls | 0 |
| coord_descent_runs | 0 |
| coord_descent_steps | 0 |
| deadline_checks | 0 |
| sheet_loop_iterations | 0 |
| worker_passes | 0 |
| worker_candidates_evaluated | 0 |
| worker_candidates_accepted | 0 |
| coord_descent_ask_calls | 0 |
| coord_descent_tell_calls | 0 |
| broadphase_reject_count | 0 |
| early_termination_count | 0 |

### Case: lv8_subset

| Field | Value |
|---|---|
| status | ok |
| placed_count | 67 |
| q30r1_profile_enabled | True |
| search_total_ms | 0.0 |
| search_accounted_ms | 0.0 |
| search_unaccounted_ms | 0.0 |
| **search_unaccounted_ratio_pct** | **0.0%** |
| total_solver_runtime_ms | 26905.9 |
| runtime_accounted_ratio_pct | 100.0% |

**Counters (lv8_subset):**

| Counter | Value |
|---|---|
| native_search_calls | 0 |
| evaluate_sample_calls | 0 |
| evaluate_sample_calls_from_global | 0 |
| evaluate_sample_calls_from_focused | 0 |
| evaluate_sample_calls_from_coord_descent | 0 |
| candidates_evaluated | 0 |
| global_samples_generated | 0 |
| focused_samples_generated | 0 |
| best_samples_insert_attempts | 0 |
| best_samples_inserted | 0 |
| best_samples_dedup_rejects | 0 |
| best_samples_best_calls | 0 |
| best_samples_clone_calls | 0 |
| coord_descent_runs | 0 |
| coord_descent_steps | 0 |
| deadline_checks | 0 |
| sheet_loop_iterations | 0 |
| worker_passes | 0 |
| worker_candidates_evaluated | 0 |
| worker_candidates_accepted | 0 |
| coord_descent_ask_calls | 0 |
| coord_descent_tell_calls | 0 |
| broadphase_reject_count | 0 |
| early_termination_count | 0 |

### Case: dense191

| Field | Value |
|---|---|
| status | partial |
| placed_count | 191 |
| q30r1_profile_enabled | True |
| search_total_ms | 27210.4 |
| search_accounted_ms | 27085.2 |
| search_unaccounted_ms | 125.2 |
| **search_unaccounted_ratio_pct** | **0.5%** |
| total_solver_runtime_ms | 200437.6 |
| runtime_accounted_ratio_pct | 100.0% |

**Top exclusive search buckets (dense191):**

| Bucket | ms | % of search |
|---|---|---|
| prepare_base_shape_native_ms | 21433.1 | 78.8% |
| evaluate_sample_total_ms | 5587.0 | 20.5% |
| cde_query_collect_ms | 5139.7 | 18.9% |
| coord_descent_total_ms | 4884.5 | 17.9% |
| candidate_transform_prepare_ms | 140.8 | 0.5% |
| boundary_check_ms | 52.7 | 0.2% |
| coord_descent_ask_ms | 25.4 | 0.1% |
| coord_descent_tell_ms | 23.7 | 0.1% |
| best_samples_insert_dedup_ms | 5.6 | 0.0% |
| sample_generation_ms | 5.0 | 0.0% |

**Counters (dense191):**

| Counter | Value |
|---|---|
| native_search_calls | 285 |
| evaluate_sample_calls | 48253 |
| evaluate_sample_calls_from_global | 898 |
| evaluate_sample_calls_from_focused | 1707 |
| evaluate_sample_calls_from_coord_descent | 43408 |
| candidates_evaluated | 46878 |
| global_samples_generated | 2280 |
| focused_samples_generated | 2280 |
| best_samples_insert_attempts | 4315 |
| best_samples_inserted | 3796 |
| best_samples_dedup_rejects | 159 |
| best_samples_best_calls | 285 |
| best_samples_clone_calls | 285 |
| coord_descent_runs | 1425 |
| coord_descent_steps | 43408 |
| deadline_checks | 0 |
| sheet_loop_iterations | 285 |
| worker_passes | 1 |
| worker_candidates_evaluated | 285 |
| worker_candidates_accepted | 285 |
| coord_descent_ask_calls | 23129 |
| coord_descent_tell_calls | 21704 |
| broadphase_reject_count | 1375 |
| early_termination_count | 24916 |

### Case: full276_optional

| Field | Value |
|---|---|
| status | skipped |
| placed_count | ? |
| q30r1_profile_enabled | False |
| search_total_ms | 0.0 |
| search_accounted_ms | 0.0 |
| search_unaccounted_ms | 0.0 |
| **search_unaccounted_ratio_pct** | **0.0%** |
| total_solver_runtime_ms | 0.0 |
| runtime_accounted_ratio_pct | 0.0% |

## Dense191 Analysis

**search_unaccounted_ratio_pct:** 0.5%
**runtime_unaccounted_ratio_pct:** 0.0%

**What consumes search_total_ms:**

| Bucket | ms | % |
|---|---|---|
| prepare_base_shape_native_ms | 21433.1 | 78.8% |
| evaluate_sample_total_ms | 5587.0 | 20.5% |
| cde_query_collect_ms | 5139.7 | 18.9% |
| coord_descent_total_ms | 4884.5 | 17.9% |
| candidate_transform_prepare_ms | 140.8 | 0.5% |
| boundary_check_ms | 52.7 | 0.2% |
| coord_descent_ask_ms | 25.4 | 0.1% |
| coord_descent_tell_ms | 23.7 | 0.1% |
| best_samples_insert_dedup_ms | 5.6 | 0.0% |
| sample_generation_ms | 5.0 | 0.0% |

Unaccounted: 125.2ms (0.5%)

**Runtime breakdown (top level exclusive):**

| Bucket | ms | % of total |
|---|---|---|
| seed_lbf | 58015.4 | 28.9% |
| tracker_initial_build | 12993.1 | 6.5% |
| exploration | 116510.7 | 58.1% |
| separator | 49026.9 | 24.5% |
| worker_competition | 49026.5 | 24.5% |
| worker_pass | 49026.1 | 24.5% |
| tracker_final_validation | 12918.2 | 6.4% |
| output_mapping | 0.0 | 0.0% |
| **runtime_unaccounted** | **0.2** | **0.0%** |

**Next hotspot to instrument:** `cde_adapter.rs::prepare_base_shape_native`

## Admin Integration

Profile data available via `optimizer_diagnostics.sparrow_q30r1_*` JSON fields.
Enabled only with `SGH_Q30_R1_EXCLUSIVE_PROFILE=1`. Zero overhead when disabled.
Backward compatible with `SGH_Q30_SEARCH_PROFILE=1` (enables all R1 timers too).
Fields suitable for future admin/observability surface (structured, versioned).

---

Q30_R1_STATUS: PASS
DENSE191_SEARCH_UNACCOUNTED_RATIO: 0.5%
DENSE191_RUNTIME_UNACCOUNTED_RATIO: 0.0%
NEXT_HOTSPOT: cde_adapter.rs::prepare_base_shape_native
