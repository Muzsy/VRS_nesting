# SGH-Q31 CDE Base-Shape Cache Hot-Path Speedup — Report

## Summary

**Status:** `PASS`

## Problem Context

SGH-Q30-R1 profiling revealed that `prepare_base_shape_native` (POI+surrogate
computation per search call) accounted for 78.9% of `search_total_ms` on dense191
(baseline: 21433.1ms). Q31 builds a per-part `HashMap<String,
Rc<CdeBaseShape>>` cache in `from_solver_input` so each unique part's base shape
is built exactly once. All instances share the `Rc`, and hot paths in search.rs,
lbf.rs, and tracker.rs now use `transform_base_to_candidate` instead.

## Dense191 Results

| Metric | Value | Gate |
|---|---|---|
| status | partial | partial/ok |
| placed_count | 191 | == 191 |
| final_pairs | 5 | <= 88 |
| hotpath_calls | 0 | == 0 |
| hotpath_ms | 0.000 | <= 2143.31 |
| cache_unique_parts | 12 | > 0 |
| cache_misses | 12 | <= unique+2 |
| cache_hits | 179 | >= instances-unique |
| cache_build_ms | 1337.006 | informational |
| prepare_base_reduction_pct | 100.0% | informational |
| search_total_ms | 101119.4 | informational |

## Case Results

### Case: dense191

| Field | Value |
|---|---|
| status | partial |
| placed_count | 191 |
| final_pairs | 5 |
| hotpath_calls | 0 |
| hotpath_ms | 0.0 |
| cache_unique_parts | 12 |
| cache_misses | 12 |
| cache_hits | 179 |
| cache_build_ms | 1337.006 |
| search_total_ms | 101119.422 |

### Case: lv8_subset

| Field | Value |
|---|---|
| status | ok |
| placed_count | 67 |
| final_pairs | 0 |
| hotpath_calls | 0 |
| hotpath_ms | 0.0 |
| cache_unique_parts | 3 |
| cache_misses | 3 |
| cache_hits | 64 |
| cache_build_ms | 37.033 |
| search_total_ms | 0.0 |

## Implementation

- `SparrowProblem::from_solver_input`: builds `HashMap<String, Rc<CdeBaseShape>>`
- `SPInstance`: stores `pub base_shape: Rc<CdeBaseShape>`
- `sample/search.rs`: uses `inst.base_shape.clone()` (O(1) Rc clone)
- `lbf.rs` `find_clear_placement` + `lbf_order_key`: same pattern
- `quantify/tracker.rs` `prepare_item`: `transform_base_to_candidate(&inst.base_shape, ...)`

---

Q31_STATUS: PASS
DENSE191_BASE_SHAPE_HOTPATH_CALLS: 0
DENSE191_BASE_SHAPE_HOTPATH_MS: 0.000
DENSE191_BASE_SHAPE_CACHE_MISSES: 12
DENSE191_BASE_SHAPE_CACHE_HITS: 179
DENSE191_PREPARE_BASE_REDUCTION_PCT: 100.0%
DENSE191_FINAL_PAIRS: 5
NEXT_HOTSPOT: eval/sep_evaluator.rs::SeparationEvaluator::evaluate_sample
