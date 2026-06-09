# SGH-Q32 Finite-Stock Sparrow Multisheet Manager — LV8 Benchmark Report

## Summary

**Status:** `PASS`

| Case | Status | Placed | Used Sheets | Final Pairs | Gate |
|---|---|---|---|---|---|
| Case 01 (2×1500×3000) | ok | 276 | 2 | 0 | PASS |
| Case 02 (3×1500×3000) | ok | 276 | 2 | 0 | PASS |
| Case 03 (1×1500×3000+2×1000×2000) | partial | 271 | 3 | 0 | PASS |

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
| sparrow_ms_runtime_ms | 663890.65197 |
| sparrow_q31_cache_build_ms | 1334.202204 |
| sparrow_q31_hotpath_calls | 0 |
| wall_s | 689.68 |

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
| sparrow_ms_runtime_ms | 651511.879767 |
| sparrow_q31_cache_build_ms | 1369.842959 |
| sparrow_q31_hotpath_calls | 0 |
| wall_s | 676.56 |

## case_03 — PASS

| Metric | Value |
|---|---|
| status | partial |
| placed_count | 271 |
| unplaced_count | 5 |
| sparrow_ms_active | True |
| sparrow_ms_status | partial |
| sparrow_ms_available_sheet_count | 3 |
| sparrow_ms_used_sheet_count | 3 |
| sparrow_ms_used_sheet_indices | [0, 1, 2] |
| sparrow_ms_used_sheet_area | 8500000.0 |
| sparrow_ms_utilization_pct | 50.08670866466097 |
| sparrow_ms_total_instances | 276 |
| sparrow_ms_placed_instances | 271 |
| sparrow_ms_unplaced_instances | 5 |
| sparrow_ms_attempts | 5 |
| sparrow_ms_candidate_subsets | 5 |
| sparrow_ms_best_full_solution_found | False |
| sparrow_ms_stock_exhausted | True |
| sparrow_ms_final_pairs | 0 |
| sparrow_ms_boundary_violations | 0 |
| sparrow_ms_runtime_ms | 1193910.730652 |
| sparrow_q31_cache_build_ms | 1341.1800030000002 |
| sparrow_q31_hotpath_calls | 0 |
| wall_s | 1214.19 |

---

Q32_STATUS: PASS
Q32_CASE01_STATUS: PASS
Q32_CASE02_STATUS: PASS
Q32_CASE03_STATUS: PASS
Q32_CASE01_PLACED: 276
Q32_CASE02_PLACED: 276
Q32_CASE03_PLACED: 271
Q32_CASE01_USED_SHEETS: 2
Q32_CASE02_USED_SHEETS: 2
Q32_CASE03_USED_SHEETS: 3
Q32_CASE01_FINAL_PAIRS: 0
Q32_CASE02_FINAL_PAIRS: 0
Q32_CASE03_FINAL_PAIRS: 0
Q32_CASE03_UNPLACED: 5
Q32_FINAL_VERDICT: All gates passed
