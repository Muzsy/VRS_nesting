# SGH-Q25-R6 Strict parity semantic hardening — convex-hull disruption, touching edge-cases, upstream mapping

## Why this task exists

Q25-R5 introduced the strict Sparrow parity profile and fixed the major behavior-level gaps: strict touching policy, upstream-like sample budgets, worker RNG ordering, separator 200/3 loop limits, and upstream-like exploration/disruption structure.

The Q25-R5 audit still had three yellow flags:

1. Large-item disruption still appeared to use `inst.part.width * inst.part.height` as the large-item area key. That is bbox area, not upstream-style convex hull area.
2. Strict touching/boundary tests existed, but they were not strong enough to prove edge/corner/boundary epsilon behavior across the strict CDE path.
3. The audit could not independently verify the upstream `.cache/sparrow` line-by-line mapping from the ZIP. The next implementation run must do this locally against `.cache/sparrow` and document it.

This task is only for those items. It is not another broad porting pass. It is not benchmark tuning.

## Required outcome

After Q25-R6:

```text
Strict Sparrow parity profile remains active.
Large-item disruption uses convex-hull-area-derived keys/cutoffs.
Strict touching/boundary semantics are covered by hard edge-case tests.
Upstream mapping for the strict core functions is documented against .cache/sparrow.
No compression or LV8 quality acceptance is added.
```

## Source of truth

Read before editing:

```text
AGENTS.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
codex/reports/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md
rust/vrs_solver/src/optimizer/sparrow/explore.rs
rust/vrs_solver/src/optimizer/sparrow/tests.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs
.cache/sparrow/src/optimizer/explore.rs
.cache/sparrow/src/optimizer/worker.rs
.cache/sparrow/src/optimizer/separator.rs
.cache/sparrow/src/sample/search.rs
.cache/sparrow/src/optimizer/lbf.rs
.cache/sparrow/src/eval/sep_evaluator.rs
.cache/sparrow/src/eval/lbf_evaluator.rs
```

Record:

```bash
git -C .cache/sparrow rev-parse HEAD
git -C .cache/sparrow status --porcelain=v1
```

If `.cache/sparrow` is unavailable, stop with `BLOCKED_UPSTREAM_MISSING`. Do not infer upstream behavior from memory.

## Scope hygiene gate

At task start run:

```bash
git status --porcelain=v1
git diff --name-only
```

Report:

```text
PRE_TASK_GIT_STATUS
PRE_TASK_DIRTY_FILES
PRE_EXISTING_OUT_OF_SCOPE_DIRTY_FILES
```

Do not revert or edit pre-existing dirty files outside the allowed outputs. If unrelated dirty files exist, list them. Only fail the task if your own changes create new out-of-scope diffs.

## Hard exclusions

Do not:

- add or wire compression;
- make LV8 / first-sheet / full-276 density a success criterion;
- change the fixed multisheet model into strip packing;
- reintroduce `WorkingLayout`, `VrsCollisionTracker`, old VRS solver core, bbox/AABB ranking, overlap proxy ranking, or legacy fallback into `optimizer/sparrow`;
- weaken Q25-R5 strict profile values: separator 50/25/3, LBF 1000/0/3, worker count 3, separator 200/3, no strict downscaling;
- change strict touching into touch-allowed behavior;
- broaden the task into performance tuning or benchmark chasing;
- claim PASS without source-level tests and mapping evidence.

## Required implementation details

### 1. Replace bbox-area disruption key with convex-hull-area key

Current suspicious area from Q25-R5:

```rust
inst.part.width * inst.part.height
```

inside or near `select_large_item_swap_pair` / large-item disruption logic.

Strict mode must use a convex-hull-area-derived key. Prefer an explicit helper name so regressions are easy to catch:

```rust
fn large_item_disruption_area_key(inst: &SPInstance) -> f64
```

The helper should derive the key from the item geometry, using existing local CDE utilities such as:

```rust
prepare_shape_native(...)
convex_hull_area_and_diameter(...)
```

or an equivalent already-existing prepared-shape/surrogate path. The cutoff should be based on cumulative convex hull area and `SPARROW_PARITY_LARGE_ITEM_CH_AREA_CUTOFF_PERCENTILE`, not cumulative bbox area.

Fallback rule:

- If shape preparation fails, a bbox fallback may be used only inside the fallback branch.
- The report must state that this is an exceptional fallback and not the normal strict large-item key.
- The normal strict path must not use bbox area as the item ranking/cutoff truth.

Add/strengthen tests:

- `strict_large_item_disruption_uses_convex_hull_area_not_bbox_area`
- `strict_large_item_cutoff_uses_cumulative_convex_hull_area_percentile`
- `strict_large_item_bbox_fallback_is_only_for_unprepared_shape`

The first test must use at least one irregular/non-rectangular fixture where bbox area and convex hull area can diverge materially. Do not test only rectangles.

### 2. Harden strict touching and boundary edge-case tests

Existing Q25-R5 tests are not enough. Add explicit tests covering:

- pair edge touching is collision in `SparrowStrict`;
- pair corner touching is collision in `SparrowStrict`;
- the same pair edge/corner touching remains allowed only in explicit `VrsTouchAllowed` non-parity policy;
- exact boundary fit / exact boundary touching is not feasible in strict mode;
- epsilon-inside placement is feasible in strict mode;
- epsilon-outside placement is collision/infeasible in strict mode.

Required test names:

```text
strict_pair_edge_touching_is_collision
strict_pair_corner_touching_is_collision
vrs_touch_allowed_pair_edge_and_corner_touching_are_clear
strict_boundary_exact_fit_is_not_feasible
strict_boundary_epsilon_inside_is_feasible
strict_boundary_epsilon_outside_is_collision
```

These tests must exercise the real CDE adapter/session/tracker/evaluator path used by the strict Sparrow profile. Avoid fake pure-rectangle helper assertions that bypass the production path.

### 3. Upstream mapping report against `.cache/sparrow`

Create a source-level mapping audit in the Q25-R6 report. This is a report requirement, not optional commentary.

For each row, include:

```text
upstream file:function or upstream line range
local file:function or local line range
status: PORTED | ADAPTED_FIXED_SHEET | DEFERRED_COMPRESSION | NOT_RELEVANT_FIXED_SHEET | GAP
why the adaptation is acceptable, if not exact
```

Required rows:

```text
.cache/sparrow/src/optimizer/explore.rs::exploration_phase
.cache/sparrow/src/optimizer/explore.rs::restore_from_pool / pool selection equivalent
.cache/sparrow/src/optimizer/explore.rs::disrupt / large item swap
.cache/sparrow/src/optimizer/worker.rs::move_items
.cache/sparrow/src/optimizer/separator.rs::separation_phase
.cache/sparrow/src/sample/search.rs::search_position / search_placement path
.cache/sparrow/src/optimizer/lbf.rs::LBFBuilder path
.cache/sparrow/src/eval/sep_evaluator.rs::SeparationEvaluator
.cache/sparrow/src/eval/lbf_evaluator.rs::LBFEvaluator
.cache/sparrow/src/consts.rs::LBF_SAMPLE_CONFIG
.cache/sparrow/src/config.rs::DEFAULT_SPARROW_CONFIG
```

The mapping must explicitly mark compression as deferred and out-of-scope. Do not hide a core GAP under `ADAPTED_FIXED_SHEET` unless the difference is truly caused by fixed multisheet.

### 4. Preserve Q25-R5 strict profile invariants

Q25-R6 must not regress Q25-R5. Keep these invariants:

```text
SparrowStrictParity exists and is the default parity profile.
CdeTouchingPolicy::{SparrowStrict,VrsTouchAllowed} exists.
Strict LBF = 1000/0/3.
Strict separator = 50/25/3.
Strict separator loop = 200/3.
Strict worker count = 3.
Strict instance-count downscaling disabled.
Strict worker ordering = RNG shuffle only.
No compression.
No LV8 benchmark gate.
```

## Required report sections

The Q25-R6 report must contain these exact section headers/tokens:

```text
SGH-Q25-R6_STATUS
UPSTREAM_COMMIT
PRE_TASK_GIT_STATUS
PRE_TASK_DIRTY_FILES
PRE_EXISTING_OUT_OF_SCOPE_DIRTY_FILES
TASK_CHANGED_FILES
OUT_OF_SCOPE_NEW_CHANGES
CONVEX_HULL_DISRUPTION_AUDIT
STRICT_TOUCHING_EDGE_CASE_AUDIT
UPSTREAM_LINE_MAPPING_AUDIT
Q25_R5_INVARIANT_REGRESSION_AUDIT
LEGACY_CORE_REGRESSION_GATE
TESTS_ADDED_OR_UPDATED
BUILD_TEST_RESULTS
```

If PASS, the report must include these exact tokens:

```text
CONVEX_HULL_AREA_KEY: USED_FOR_STRICT_LARGE_ITEM_DISRUPTION
BBOX_WIDTH_HEIGHT_PRODUCT: NOT_USED_FOR_STRICT_LARGE_ITEM_CUTOFF
STRICT_TOUCHING_TESTS: EDGE_CORNER_BOUNDARY_EPSILON_COVERED
UPSTREAM_MAPPING: LINE_BY_LINE_RECHECKED
Q25_R5_STRICT_PROFILE_INVARIANTS: PRESERVED
COMPRESSION_STATUS: DEFERRED_ONLY
LV8_BENCHMARK_STATUS: NOT_USED_AS_ACCEPTANCE
OUT_OF_SCOPE_NEW_CHANGES: NONE
```

## Acceptance gates

Mandatory commands:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.py
./scripts/check.sh
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md
```

If any mandatory gate cannot run, do not claim full PASS. Use FAIL or PASS_WITH_NOTES according to `docs/codex/report_standard.md`.
