# SGH-Q32 Finite-Stock Sparrow Multisheet Manager — LV8 Benchmark Report

## Summary

**Status:** `PASS`

| Case | Status | Placed | Used Sheets | Final Pairs | Gate |
|---|---|---|---|---|---|
| Case 01 (2×1500×3000) | ok | 276 | 2 | 0 | PASS |
| Case 02 (3×1500×3000) | ok | 276 | 2 | 0 | PASS |
| Case 03 (1×1500×3000+2×1000×2000) | partial | 272 | 3 | 0 | PASS |

## case_01 — PASS

| Metric | Value |
|---|---|
| status | ok |
| placed_count | 276 |
| unplaced_count | 0 |
| sparrow_ms_active | True |
| sparrow_ms_status | ok |
| sparrow_ms_available_sheet_count | 2 |
| sparrow_ms_used_sheet_count | 2 |
| sparrow_ms_used_sheet_indices | [0, 1] |
| sparrow_ms_used_sheet_area | 9000000.0 |
| sparrow_ms_utilization_pct | 74.1055296042998 |
| sparrow_ms_total_instances | 276 |
| sparrow_ms_placed_instances | 276 |
| sparrow_ms_unplaced_instances | 0 |
| sparrow_ms_attempts | 2 |
| sparrow_ms_candidate_subsets | 2 |
| sparrow_ms_best_full_solution_found | True |
| sparrow_ms_stock_exhausted | False |
| sparrow_ms_final_pairs | 0 |
| sparrow_ms_boundary_violations | 0 |
| sparrow_ms_runtime_ms | 661496.9253850001 |
| sparrow_q31_cache_build_ms | 1403.309127 |
| sparrow_q31_hotpath_calls | 0 |
| wall_s | 687.27 |

## case_02 — PASS

| Metric | Value |
|---|---|
| status | ok |
| placed_count | 276 |
| unplaced_count | 0 |
| sparrow_ms_active | True |
| sparrow_ms_status | ok |
| sparrow_ms_available_sheet_count | 3 |
| sparrow_ms_used_sheet_count | 2 |
| sparrow_ms_used_sheet_indices | [0, 1] |
| sparrow_ms_used_sheet_area | 9000000.0 |
| sparrow_ms_utilization_pct | 74.1055296042998 |
| sparrow_ms_total_instances | 276 |
| sparrow_ms_placed_instances | 276 |
| sparrow_ms_unplaced_instances | 0 |
| sparrow_ms_attempts | 2 |
| sparrow_ms_candidate_subsets | 3 |
| sparrow_ms_best_full_solution_found | True |
| sparrow_ms_stock_exhausted | False |
| sparrow_ms_final_pairs | 0 |
| sparrow_ms_boundary_violations | 0 |
| sparrow_ms_runtime_ms | 675206.6505110001 |
| sparrow_q31_cache_build_ms | 1437.470335 |
| sparrow_q31_hotpath_calls | 0 |
| wall_s | 701.42 |

## case_03 — PASS

| Metric | Value |
|---|---|
| status | partial |
| placed_count | 272 |
| unplaced_count | 4 |
| sparrow_ms_active | True |
| sparrow_ms_status | partial |
| sparrow_ms_available_sheet_count | 3 |
| sparrow_ms_used_sheet_count | 3 |
| sparrow_ms_used_sheet_indices | [0, 1, 2] |
| sparrow_ms_used_sheet_area | 8500000.0 |
| sparrow_ms_utilization_pct | 50.348539628108846 |
| sparrow_ms_total_instances | 276 |
| sparrow_ms_placed_instances | 272 |
| sparrow_ms_unplaced_instances | 4 |
| sparrow_ms_attempts | 5 |
| sparrow_ms_candidate_subsets | 5 |
| sparrow_ms_best_full_solution_found | False |
| sparrow_ms_stock_exhausted | True |
| sparrow_ms_final_pairs | 0 |
| sparrow_ms_boundary_violations | 0 |
| sparrow_ms_runtime_ms | 1176057.826667 |
| sparrow_q31_cache_build_ms | 1431.166153 |
| sparrow_q31_hotpath_calls | 0 |
| wall_s | 1198.2 |

---

Q32_STATUS: PASS
Q32_CASE01_STATUS: PASS
Q32_CASE02_STATUS: PASS
Q32_CASE03_STATUS: PASS
Q32_CASE01_PLACED: 276
Q32_CASE02_PLACED: 276
Q32_CASE03_PLACED: 272
Q32_CASE01_USED_SHEETS: 2
Q32_CASE02_USED_SHEETS: 2
Q32_CASE03_USED_SHEETS: 3
Q32_CASE01_FINAL_PAIRS: 0
Q32_CASE02_FINAL_PAIRS: 0
Q32_CASE03_FINAL_PAIRS: 0
Q32_CASE03_UNPLACED: 4
Q32_FINAL_VERDICT: All gates passed
