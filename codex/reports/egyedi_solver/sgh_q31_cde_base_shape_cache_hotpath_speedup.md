# SGH-Q31 CDE Base-Shape Cache Hot-Path Speedup — Codex Report

## Status

**Q31_STATUS: PASS**

## Task

Eliminate `prepare_base_shape_native` from the search/LBF/tracker hot paths by
building a per-part `CdeBaseShape` cache once in `SparrowProblem::from_solver_input`.

Q30-R1 profiling established that `prepare_base_shape_native` accounted for 78.9%
of `search_total_ms` on dense191 (~21,433ms of ~27,200ms). Each `native_search_placement`
call rebuilt the POI+surrogate CDE shape from scratch for the same part type, repeatedly.

## Implementation

- `optimizer/cde_adapter.rs` — Made `CdeBaseShape` fields `pub(crate)`, added manual
  `Debug` impl (required because `SPInstance: Debug`)
- `optimizer/sparrow/model.rs` — Added `base_shape: Rc<CdeBaseShape>` to `SPInstance`;
  `SparrowProblem::from_solver_input` builds a `HashMap<String, Rc<CdeBaseShape>>` keyed
  by `part.id`: one `prepare_base_shape_native` call per unique part type, then all instances
  of that type share the `Rc`; cache stats (`unique_parts`, `hits`, `misses`, `build_ms`)
  stored in `SparrowProblem` and transferred to `SearchProfiler` in `solve()`
- `optimizer/sparrow/sample/search.rs` — Replaced `prepare_base_shape_native(&inst.part)`
  with `inst.base_shape.clone()` (O(1) Rc clone); added early-exit guard via
  `transform_base_to_candidate(&base, cur.x, cur.y, cur.rotation_deg).is_none()` for
  degenerate shape detection
- `optimizer/sparrow/lbf.rs` — Replaced both hot-path calls in `find_clear_placement` and
  `lbf_order_key`: `prepare_base_shape_native` / `prepare_shape_native` → `inst.base_shape.clone()`
  + `transform_base_to_candidate`
- `optimizer/sparrow/quantify/tracker.rs` — `prepare_item`: `prepare_shape_native(&inst.part, ...)`
  → `transform_base_to_candidate(&inst.base_shape, ...)`
- `optimizer/sparrow/profile.rs` — Added 10 Q31 fields: `base_shape_cache_{build_ms,hits,misses,
  unique_parts,reused_instances}`, `prepare_base_shape_native_hotpath_{calls,ms}`,
  `tracker_transform_from_base_ms`, `{lbf,search}_base_shape_cache_hits`
- `optimizer/sparrow/optimizer.rs` — Transfers cache stats from problem to profiler at start of `solve()`
- `io.rs` — 10 new `sparrow_q31_*` `Option` fields
- `adapter.rs` — Mapped Q31 fields in `native_sparrow_diag_to_output`
- `optimizer/sparrow/tests.rs` — Fixed 2 `SPInstance` struct literals to include `base_shape`

## Dense191 Results

| Metric | Value | Gate |
|---|---|---|
| status | partial | ✓ partial/ok |
| placed_count | 191 | ✓ == 191 |
| final_pairs | 5 | ✓ ≤ 88 |
| hotpath_calls | 0 | ✓ == 0 |
| hotpath_ms | 0.000 ms | ✓ ≤ 2143.31 ms |
| cache_unique_parts | 12 | ✓ > 0 |
| cache_misses | 12 | ✓ ≤ 14 (unique+2) |
| cache_hits | 179 | ✓ ≥ 179 (191-12) |
| cache_build_ms | ~2–4 ms | informational |
| prepare_base_reduction_pct | 100.0% | informational |

### Q30-R1 baseline vs Q31

| Phase | Q30-R1 | Q31 |
|---|---|---|
| prepare_base_shape_native hot-path | ~21,433 ms | 0 ms |
| hot-path calls | ~N×search_calls | 0 |
| cache build | N/A | ~2–4 ms (once) |

## Non-Goals Preserved

- No sample budget / worker ordering / GLS / acceptance logic changes
- No upstream Sparrow A/B changes
- No geometry simplification
- No compression changes
- `explore.rs` disruption paths (`prepare_shape_native`) unchanged (not in hot path)

## Artifacts

- `artifacts/benchmarks/sgh_q31/base_shape_cache_summary.json`
- `artifacts/benchmarks/sgh_q31/base_shape_cache_report.md`
- `artifacts/benchmarks/sgh_q31/inputs/dense191.json`
- `artifacts/benchmarks/sgh_q31/inputs/lv8_subset.json`

---

Q31_STATUS: PASS
DENSE191_BASE_SHAPE_HOTPATH_CALLS: 0
DENSE191_BASE_SHAPE_HOTPATH_MS: 0.000
DENSE191_BASE_SHAPE_CACHE_MISSES: 12
DENSE191_BASE_SHAPE_CACHE_HITS: 179
DENSE191_PREPARE_BASE_REDUCTION_PCT: 100.0%
DENSE191_FINAL_PAIRS: 5
NEXT_HOTSPOT: eval/sep_evaluator.rs::SeparationEvaluator::evaluate_sample

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-07T20:44:58+02:00 → 2026-06-07T20:48:14+02:00 (196s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q31_cde_base_shape_cache_hotpath_speedup.verify.log`
- git: `main@04b7f1d`
- módosított fájlok (git status): 20

**git diff --stat**

```text
 .codegraphcontext/db/falkordb.settings             |  2 +-
 rust/vrs_solver/src/adapter.rs                     | 20 +++++++
 rust/vrs_solver/src/io.rs                          | 21 +++++++
 rust/vrs_solver/src/optimizer/cde_adapter.rs       | 12 +++-
 rust/vrs_solver/src/optimizer/sparrow/lbf.rs       | 20 +++----
 rust/vrs_solver/src/optimizer/sparrow/model.rs     | 69 ++++++++++++++++++++++
 rust/vrs_solver/src/optimizer/sparrow/optimizer.rs |  8 +++
 rust/vrs_solver/src/optimizer/sparrow/profile.rs   | 18 ++++++
 .../src/optimizer/sparrow/quantify/tracker.rs      |  5 +-
 .../src/optimizer/sparrow/sample/search.rs         | 16 +++--
 rust/vrs_solver/src/optimizer/sparrow/tests.rs     | 11 ++++
 11 files changed, 180 insertions(+), 22 deletions(-)
```

**git status --porcelain (preview)**

```text
 M .codegraphcontext/db/falkordb.settings
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/cde_adapter.rs
 M rust/vrs_solver/src/optimizer/sparrow/lbf.rs
 M rust/vrs_solver/src/optimizer/sparrow/model.rs
 M rust/vrs_solver/src/optimizer/sparrow/optimizer.rs
 M rust/vrs_solver/src/optimizer/sparrow/profile.rs
 M rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs
 M rust/vrs_solver/src/optimizer/sparrow/sample/search.rs
 M rust/vrs_solver/src/optimizer/sparrow/tests.rs
?? artifacts/benchmarks/sgh_q31/
?? canvases/egyedi_solver/sgh_q31_cde_base_shape_cache_hotpath_speedup.md
?? codex/codex_checklist/egyedi_solver/sgh_q31_cde_base_shape_cache_hotpath_speedup.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q31_cde_base_shape_cache_hotpath_speedup.yaml
?? codex/prompts/egyedi_solver/sgh_q31_cde_base_shape_cache_hotpath_speedup/
?? codex/reports/egyedi_solver/sgh_q31_cde_base_shape_cache_hotpath_speedup.md
?? codex/reports/egyedi_solver/sgh_q31_cde_base_shape_cache_hotpath_speedup.verify.log
?? scripts/profile_sgh_q31_base_shape_cache_speedup.py
?? scripts/smoke_sgh_q31_cde_base_shape_cache_hotpath_speedup.py
```

<!-- AUTO_VERIFY_END -->
