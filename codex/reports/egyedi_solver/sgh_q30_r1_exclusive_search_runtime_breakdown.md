# SGH-Q30-R1 Exclusive Search Runtime Breakdown — Codex Report

## Status

**Q30_R1_STATUS: PASS**

## Task

Bring dense191 `search_unaccounted_ratio_pct` from 79.4% (Q30 baseline) to ≤ 15% using
exclusive timing instrumentation. Measurement-only task: no solver semantics changed.

## Implementation

Added exclusive `ProfileTimer` instrumentation to:

- `optimizer/sparrow/profile.rs` — R1 exclusive fields, `finalize()` on solve path,
  `r1_active()` helper, `new_from_env()` for `SGH_Q30_R1_EXCLUSIVE_PROFILE=1`
- `optimizer/sparrow/sample/search.rs` — `prepare_base_shape_native_ms`,
  `fixed_shapes_clone_ms`, `sheet_order_build_ms`, `best_samples_clone_ms`,
  `best_samples_best_ms`, context-specific eval counters
- `optimizer/sparrow/sample/coord_descent.rs` — `coord_descent_ask_ms`,
  `coord_descent_tell_ms`, `evaluate_sample_calls_from_coord_descent`
- `optimizer/sparrow/optimizer.rs` — full runtime tree: `seed_lbf_total_ms`,
  `tracker_initial_build_ms`, `exploration_total_ms`, `tracker_final_validation_ms`,
  `output_mapping_ms`; `finalize()` called before returning `SparrowSolveResult`
- `optimizer/sparrow/separator.rs` — `separator_total_ms`,
  `separator_iteration_total_ms`, `worker_competition_total_ms`, `worker_pass_total_ms`
- `adapter.rs` — `adapter_solve_total_ms`, all `sparrow_q30r1_*` output fields
- `io.rs` — 36 new `sparrow_q30r1_*` struct fields

## Dense191 Results

| Metric | Value |
|---|---|
| search_total_ms | ~27,210 ms |
| search_accounted_ms | ~27,073 ms |
| search_unaccounted_ms | ~137 ms |
| **search_unaccounted_ratio_pct** | **0.5%** |
| total_solver_runtime_ms | ~201,000 ms |
| runtime_accounted_ratio_pct | ~100% |

### Top exclusive search buckets

| Bucket | ms | % of search |
|---|---|---|
| prepare_base_shape_native_ms | ~21,300 | ~78% |
| evaluate_sample_total_ms | ~5,500 | ~20% |
| coord_descent_ask_ms | ~25 | 0.1% |
| coord_descent_tell_ms | ~23 | 0.1% |
| best_samples_insert_dedup_ms | ~6 | 0.02% |

## Non-Goals Preserved

- No solver search/acceptance logic changes
- No sample budget changes
- No upstream Sparrow A/B
- No compression changes
- No dense191 acceptance expectation changes

## Artifacts

- `artifacts/benchmarks/sgh_q30_r1/local_exclusive_profile_summary.json`
- `artifacts/benchmarks/sgh_q30_r1/local_exclusive_profile_report.md`

---

Q30_R1_STATUS: PASS
DENSE191_SEARCH_UNACCOUNTED_RATIO: 0.5%
DENSE191_RUNTIME_UNACCOUNTED_RATIO: 0.0%
NEXT_HOTSPOT: cde_adapter.rs::prepare_base_shape_native

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-07T11:16:59+02:00 → 2026-06-07T11:19:53+02:00 (174s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q30_r1_exclusive_search_runtime_breakdown.verify.log`
- git: `main@34fb6d5`
- módosított fájlok (git status): 16

**git diff --stat**

```text
 rust/vrs_solver/src/adapter.rs                     |  79 ++++++++-
 rust/vrs_solver/src/io.rs                          |  73 ++++++++
 rust/vrs_solver/src/optimizer/sparrow/optimizer.rs |  17 ++
 rust/vrs_solver/src/optimizer/sparrow/profile.rs   | 190 +++++++++++++++------
 .../src/optimizer/sparrow/sample/coord_descent.rs  |  15 +-
 .../src/optimizer/sparrow/sample/search.rs         |  26 ++-
 rust/vrs_solver/src/optimizer/sparrow/separator.rs |  15 ++
 7 files changed, 358 insertions(+), 57 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/sparrow/optimizer.rs
 M rust/vrs_solver/src/optimizer/sparrow/profile.rs
 M rust/vrs_solver/src/optimizer/sparrow/sample/coord_descent.rs
 M rust/vrs_solver/src/optimizer/sparrow/sample/search.rs
 M rust/vrs_solver/src/optimizer/sparrow/separator.rs
?? artifacts/benchmarks/sgh_q30_r1/
?? canvases/egyedi_solver/sgh_q30_r1_exclusive_search_runtime_breakdown.md
?? codex/codex_checklist/egyedi_solver/sgh_q30_r1_exclusive_search_runtime_breakdown.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q30_r1_exclusive_search_runtime_breakdown.yaml
?? codex/prompts/egyedi_solver/sgh_q30_r1_exclusive_search_runtime_breakdown/
?? codex/reports/egyedi_solver/sgh_q30_r1_exclusive_search_runtime_breakdown.md
?? codex/reports/egyedi_solver/sgh_q30_r1_exclusive_search_runtime_breakdown.verify.log
?? scripts/profile_sgh_q30_r1_exclusive_search_runtime_breakdown.py
?? scripts/smoke_sgh_q30_r1_exclusive_search_runtime_breakdown.py
```

<!-- AUTO_VERIFY_END -->
