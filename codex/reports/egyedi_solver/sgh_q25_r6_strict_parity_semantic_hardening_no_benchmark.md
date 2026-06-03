# SGH-Q25-R6 Strict parity semantic hardening

SGH-Q25-R6_STATUS: PASS

## Meta

- Task slug: `sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark`
- Canvas: `canvases/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.yaml`
- Run date: `2026-06-03`
- Branch / commit: `main` / `3bd87d7`
- Focus area: `rust/vrs_solver/optimizer/sparrow`

## UPSTREAM_COMMIT

- `.cache/sparrow`: `c95454e390276231b278c879d25b39708398b7d3`
- `.cache/sparrow` status: clean

## PRE_TASK_GIT_STATUS

```text
?? README_SGH_Q25_R6_STRICT_PARITY_SEMANTIC_HARDENING_PACKAGE.md
?? canvases/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md
?? codex/codex_checklist/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.yaml
?? codex/prompts/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark/
?? scripts/smoke_sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.py
```

## PRE_TASK_DIRTY_FILES

```text
README_SGH_Q25_R6_STRICT_PARITY_SEMANTIC_HARDENING_PACKAGE.md
canvases/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md
codex/codex_checklist/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.yaml
codex/prompts/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark/run.md
scripts/smoke_sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.py
```

## PRE_EXISTING_OUT_OF_SCOPE_DIRTY_FILES

```text
README_SGH_Q25_R6_STRICT_PARITY_SEMANTIC_HARDENING_PACKAGE.md
canvases/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.yaml
codex/prompts/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark/run.md
```

These files are package/task scaffolding copied into place before solver implementation started.

## TASK_CHANGED_FILES

- `rust/vrs_solver/src/optimizer/sparrow/explore.rs`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs`
- `scripts/smoke_sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.py`
- `codex/codex_checklist/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md`
- `codex/reports/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md`

## OUT_OF_SCOPE_NEW_CHANGES

OUT_OF_SCOPE_NEW_CHANGES: NONE

## CONVEX_HULL_DISRUPTION_AUDIT

CONVEX_HULL_AREA_KEY: USED_FOR_STRICT_LARGE_ITEM_DISRUPTION
BBOX_WIDTH_HEIGHT_PRODUCT: NOT_USED_FOR_STRICT_LARGE_ITEM_CUTOFF

- `select_large_item_swap_pair` now computes both total area and sorted item keys through `large_item_disruption_area_key`, so the 0.75 cutoff is cumulative convex-hull area based.
- `large_item_disruption_area_key` prepares the native CDE shape and reads `convex_hull_area_and_diameter`; bbox area appears only in the explicit shape-preparation failure fallback branch.
- Evidence: `rust/vrs_solver/src/optimizer/sparrow/explore.rs:197`, `rust/vrs_solver/src/optimizer/sparrow/explore.rs:208`, `rust/vrs_solver/src/optimizer/sparrow/explore.rs:249`.

## STRICT_TOUCHING_EDGE_CASE_AUDIT

STRICT_TOUCHING_TESTS: EDGE_CORNER_BOUNDARY_EPSILON_COVERED

- Strict pair edge touching and corner touching are asserted through `SparrowCollisionTracker`, which uses the strict CDE path.
- Explicit `VrsTouchAllowed` remains clear for edge and corner touching through `CdeAdapter::with_vrs_touch_allowed`.
- Strict exact boundary fit, epsilon-inside, and epsilon-outside behavior are covered through tracker feasibility/boundary violation checks.
- Evidence: `rust/vrs_solver/src/optimizer/sparrow/tests.rs:720`, `rust/vrs_solver/src/optimizer/sparrow/tests.rs:741`, `rust/vrs_solver/src/optimizer/sparrow/tests.rs:774`, `rust/vrs_solver/src/optimizer/sparrow/tests.rs:810`, `rust/vrs_solver/src/optimizer/sparrow/tests.rs:831`, `rust/vrs_solver/src/optimizer/sparrow/tests.rs:853`.

## UPSTREAM_LINE_MAPPING_AUDIT

UPSTREAM_MAPPING: LINE_BY_LINE_RECHECKED

| Upstream source | Local source | Status | Notes |
| --- | --- | --- | --- |
| `.cache/sparrow/src/optimizer/explore.rs:21` `exploration_phase` | `rust/vrs_solver/src/optimizer/sparrow/explore.rs:14` `exploration_phase` | ADAPTED_FIXED_SHEET | Fixed sheets do not shrink strip width; local loop repeats separation, stores infeasible pool, restores biased pool entry, then disrupts. |
| `.cache/sparrow/src/optimizer/explore.rs:65` pool selection equivalent | `rust/vrs_solver/src/optimizer/sparrow/explore.rs:49`, `rust/vrs_solver/src/optimizer/sparrow/explore.rs:175` | PORTED | Normal-absolute biased pool index with `0.25` stddev maps better infeasible states to lower indices. |
| `.cache/sparrow/src/optimizer/explore.rs:89` disrupt / large item swap | `rust/vrs_solver/src/optimizer/sparrow/explore.rs:59`, `rust/vrs_solver/src/optimizer/sparrow/explore.rs:187`, `rust/vrs_solver/src/optimizer/sparrow/explore.rs:249` | PORTED | Large-item pool now uses convex hull area cutoff and random pair selection; fixed-sheet relocation keeps in-bounds placement. |
| `.cache/sparrow/src/optimizer/worker.rs:35` `move_items` | `rust/vrs_solver/src/optimizer/sparrow/worker.rs:27` `run_worker_pass` | PORTED | Colliding items are RNG-shuffled in strict profile, searched, moved, and accepted only on non-increasing weighted loss. |
| `.cache/sparrow/src/optimizer/separator.rs:72` `separate` | `rust/vrs_solver/src/optimizer/sparrow/separator.rs:84` `separate` | PORTED | Strict loop uses raw loss, 200 no-improve limit, 3 strike limit, GLS updates, and best snapshot rollback. |
| `.cache/sparrow/src/optimizer/separator.rs:146` `move_items_multi` | `rust/vrs_solver/src/optimizer/sparrow/separator.rs:5` `move_items_multi` | PORTED | Local worker competition is sequential/deterministic but preserves multi-worker candidate generation and best weighted-loss load-back. |
| `.cache/sparrow/src/sample/search.rs:20` `search_placement` | `rust/vrs_solver/src/optimizer/sparrow/sample/search.rs:51` `search_placement` | PORTED | Focused sampling, container sampling, retained best samples, and two-stage coordinate descent are preserved. |
| `.cache/sparrow/src/sample/search.rs:20` search path | `rust/vrs_solver/src/optimizer/sparrow/sample/search.rs:188` `native_search_placement` | ADAPTED_FIXED_SHEET | Wrapper searches current fixed sheet first, then eligible alternate sheets; strip growth is not introduced. |
| `.cache/sparrow/src/optimizer/lbf.rs:15` `LBFBuilder` | `rust/vrs_solver/src/optimizer/sparrow/lbf.rs:16` `LBFBuilder` | ADAPTED_FIXED_SHEET | Upstream clear-only construction and convex-hull-area-diameter order are kept; failed placement becomes unresolved because fixed sheets cannot widen. |
| `.cache/sparrow/src/eval/sep_evaluator.rs:11` `SeparationEvaluator` | `rust/vrs_solver/src/optimizer/sparrow/eval/sep_evaluator.rs:3` `SeparationEvaluator` | PORTED | CDE-backed hazard collection, upper-bound early termination, and tracker-weighted loss scoring are preserved. |
| `.cache/sparrow/src/eval/lbf_evaluator.rs:15` `LBFEvaluator` | `rust/vrs_solver/src/optimizer/sparrow/eval/lbf_evaluator.rs:3` `LBFEvaluator` | PORTED | LBF accepts only clear candidates and uses left-bottom positional score for clear placements. |
| `.cache/sparrow/src/consts.rs:51` `LBF_SAMPLE_CONFIG` | `rust/vrs_solver/src/optimizer/sparrow/lbf.rs:166`, `rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs:77` | PORTED | Strict LBF samples are `1000/0/3`. |
| `.cache/sparrow/src/config.rs:55` `DEFAULT_SPARROW_CONFIG` | `rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs:74` | PORTED | Strict separator samples are `50/25/3`, loop is `200/3`, workers are `3`, pool stddev is `0.25`, large-item cutoff is `0.75`. |
| `.cache/sparrow/src/config.rs:75` compression config | N/A | DEFERRED_COMPRESSION | Compression remains intentionally out of scope for Q25-R6 and is not wired locally. |

## Q25_R5_INVARIANT_REGRESSION_AUDIT

Q25_R5_STRICT_PROFILE_INVARIANTS: PRESERVED

- `SparrowProfile::SparrowStrictParity` remains default in `SparrowConfig::from_solver_input`.
- Strict LBF remains `1000/0/3`; strict separator remains `50/25/3`; strict separator loop remains `200/3`; strict worker count remains `3`.
- Strict instance-count downscaling remains disabled in `scaled_for_instance_count`.
- Strict worker ordering remains RNG shuffle only.
- Evidence: `rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs:74`, `rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs:86`, `rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs:120`, `rust/vrs_solver/src/optimizer/sparrow/worker.rs:100`.

## LEGACY_CORE_REGRESSION_GATE

COMPRESSION_STATUS: DEFERRED_ONLY
LV8_BENCHMARK_STATUS: NOT_USED_AS_ACCEPTANCE

- No compression hook was added to `optimizer/sparrow`.
- No LV8 benchmark acceptance gate was added.
- No `WorkingLayout` or `VrsCollisionTracker` was introduced into `optimizer/sparrow`.
- No bbox/AABB/proxy ranking was added to LBF or separation.

## TESTS_ADDED_OR_UPDATED

- `strict_large_item_disruption_uses_convex_hull_area_not_bbox_area`
- `strict_large_item_cutoff_uses_cumulative_convex_hull_area_percentile`
- `strict_large_item_bbox_fallback_is_only_for_unprepared_shape`
- `strict_pair_edge_touching_is_collision`
- `strict_pair_corner_touching_is_collision`
- `vrs_touch_allowed_pair_edge_and_corner_touching_are_clear`
- `strict_boundary_exact_fit_is_not_feasible`
- `strict_boundary_epsilon_inside_is_feasible`
- `strict_boundary_epsilon_outside_is_collision`

## BUILD_TEST_RESULTS

- `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release` -> PASS (`Finished release profile`; existing warnings only).
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` -> PASS (`454 passed; 0 failed`; finished in 172.74s).
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib strict_large_item -- --nocapture` -> PASS (`3 passed; 0 failed`).
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib strict_ -- --nocapture` -> PASS (`14 passed; 0 failed`).
- `python3 scripts/smoke_sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.py` -> PASS (`69 PASS; 0 WARN; 0 FAIL`).
- `./scripts/check.sh` -> PASS (`[DONE] smoketest OK`).
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md` -> PASS (`eredmény: PASS`; AUTO_VERIFY block below).

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-03T21:22:29+02:00 → 2026-06-03T21:25:29+02:00 (180s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.verify.log`
- git: `main@3bd87d7`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 rust/vrs_solver/src/optimizer/sparrow/explore.rs |  19 +-
 rust/vrs_solver/src/optimizer/sparrow/tests.rs   | 327 +++++++++++++++++++++++
 2 files changed, 344 insertions(+), 2 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/optimizer/sparrow/explore.rs
 M rust/vrs_solver/src/optimizer/sparrow/tests.rs
?? README_SGH_Q25_R6_STRICT_PARITY_SEMANTIC_HARDENING_PACKAGE.md
?? canvases/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md
?? codex/codex_checklist/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.yaml
?? codex/prompts/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark/
?? codex/reports/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md
?? codex/reports/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.verify.log
?? scripts/smoke_sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.py
```

<!-- AUTO_VERIFY_END -->
