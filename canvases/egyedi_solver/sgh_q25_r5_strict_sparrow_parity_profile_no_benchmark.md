# SGH-Q25-R5 Strict Sparrow parity profile — touching policy, upstream budgets, worker/search/explore semantics

## Why this task exists

Q25-R4 fixed two concrete semantic bugs: anchor-vs-rect-min leakage and LBF collision rejection. A remaining audit still found behavior-level gaps between the local fixed-multisheet Sparrow port and upstream jagua_rs/Sparrow core behavior.

Compression remains intentionally deferred and is not part of this task. Fixed multisheet behavior is the required local production target and is not a defect. This task fixes the remaining core-semantics/config/search deltas that are not justified by fixed multisheet.

The goal is not to improve an LV8 benchmark. The goal is to introduce and enforce a **strict Sparrow parity profile** that behaves like upstream Sparrow core, with only documented fixed-sheet adaptations.

## Required outcome

Introduce an explicit profile/policy split:

```text
SparrowStrictParity
  - collision/touching semantics follow upstream CDE strict behavior
  - upstream-like LBF and separator sample budgets
  - upstream-like worker random ordering
  - upstream-like separator loop limits
  - upstream-like exploration biased restore and large-item disruption
  - no instance-count based automatic sample shrinkage

VrsFast / VrsTouchAllowed, if kept
  - may remain as an explicit non-parity performance/manufacturing mode
  - must not be used to claim Sparrow parity
```

`SparrowStrictParity` must be the mode used by the `sparrow_cde` parity path unless the caller explicitly chooses another profile. Do not silently use fast/touch-allowed behavior under a Sparrow-parity name.

## Source of truth

Read before editing:

```text
AGENTS.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
codex/reports/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md
.cache/sparrow/src/config.rs
.cache/sparrow/src/consts.rs
.cache/sparrow/src/optimizer/worker.rs
.cache/sparrow/src/optimizer/explore.rs
.cache/sparrow/src/optimizer/separator.rs
.cache/sparrow/src/sample/search.rs
.cache/sparrow/src/optimizer/lbf.rs
.cache/sparrow/src/eval/sep_evaluator.rs
.cache/sparrow/src/eval/lbf_evaluator.rs
```

Record:

```bash
git -C .cache/sparrow rev-parse HEAD
```

If `.cache/sparrow` is unavailable, stop with `BLOCKED_UPSTREAM_MISSING`. Do not guess upstream behavior from memory.

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
- make LV8 / 191-first-sheet / full-276 density a success criterion;
- reintroduce `WorkingLayout`, `VrsCollisionTracker`, old VRS solver core, bbox/AABB ranking, overlap proxy ranking, or legacy fallback into `optimizer/sparrow`;
- use instance-count based budget downscaling in strict parity mode;
- keep touching-as-no-collision behavior inside strict Sparrow parity;
- keep worker-index ordering strategies (`worst-first`, `reverse`, `least-loss-first`) in strict parity;
- hide changes behind report wording without source-level tests.

## Required implementation details

### 1. Explicit strict-vs-VRS touching policy

Current `cde_adapter.rs` applies a VRS-side post-policy that treats edge/corner/sheet-boundary touching as `NoCollision`. That must no longer be implicit.

Implement an explicit policy, with names close to:

```rust
pub enum CdeTouchingPolicy {
    SparrowStrict,
    VrsTouchAllowed,
}
```

Then wire it through the CDE adapter/session and the native Sparrow tracker/evaluator path.

Strict behavior:

```text
SparrowStrict:
  - raw CDE touching collision remains Collision
  - pair edge/corner touching is not silently downgraded to NoCollision
  - boundary touching/exact fit is not silently accepted as fully feasible
```

VRS behavior, if retained:

```text
VrsTouchAllowed:
  - positive-area overlap remains Collision
  - pure touching may be allowed
  - must be explicitly named and not used for Sparrow parity claims
```

Add tests:

- `cde_sparrow_strict_reports_touching_rectangles_as_collision`
- `cde_vrs_touch_allowed_reports_touching_rectangles_as_no_collision`
- `sparrow_strict_boundary_touching_is_not_feasible`

### 2. Strict parity profile and upstream-like budgets

Add explicit strict-parity constants. Prefer these exact names so the smoke gate can verify them:

```rust
pub const SPARROW_PARITY_SEPARATOR_CONTAINER_SAMPLES: usize = 50;
pub const SPARROW_PARITY_SEPARATOR_FOCUSED_SAMPLES: usize = 25;
pub const SPARROW_PARITY_COORD_DESCENTS: usize = 3;
pub const SPARROW_PARITY_LBF_CONTAINER_SAMPLES: usize = 1000;
pub const SPARROW_PARITY_LBF_FOCUSED_SAMPLES: usize = 0;
pub const SPARROW_PARITY_ITER_NO_IMPROVE_LIMIT: usize = 200;
pub const SPARROW_PARITY_STRIKE_LIMIT: usize = 3;
pub const SPARROW_PARITY_WORKERS: usize = 3;
pub const SPARROW_PARITY_MAX_CONSEC_FAILED_ATTEMPTS: usize = 10;
pub const SPARROW_PARITY_SOLUTION_POOL_STDDEV: f64 = 0.25;
pub const SPARROW_PARITY_LARGE_ITEM_CH_AREA_CUTOFF_PERCENTILE: f64 = 0.75;
```

Wire strict profile so that:

- `lbf_sample_config()` uses 1000 / 0 / 3;
- separator `SampleConfig` uses 50 / 25 / 3;
- separator loop uses 200 / 3;
- worker count is 3;
- strict parity mode does **not** call or apply performance downscaling by instance count.

If fast mode remains, keep it explicit and separately named. The report must state which code path uses strict vs fast.

### 3. Worker ordering must match upstream in strict mode

In upstream, each worker collects all colliding items and shuffles them using the worker RNG. There is no worker-index strategy like worst-first, reverse, or least-loss-first.

In strict mode:

```text
colliding = tracker.colliding_indices()
rng.shuffle(&mut colliding)
```

No worker-specific ordering bias. Worker competition/load-back may still select the best worker by total weighted loss.

Add test:

- `strict_worker_orders_colliding_items_by_rng_shuffle_only`

### 4. Separator loop limits must match upstream in strict mode

Replace hard-coded local limits:

```text
no_improve_limit = 6
strike_limit = 4
```

with strict-profile values:

```text
iter_no_imprv_limit = 200
strike_limit = 3
```

Add test:

- `strict_separator_uses_upstream_loop_limits`

### 5. Exploration/disruption should follow upstream semantics where fixed-sheet does not forbid it

Keep fixed-sheet adaptation: no strip shrinking/widening. But the failure restore/disruption behavior should be upstream-like:

- infeasible pool sorted by raw loss;
- max consecutive failed attempts = 10 in strict profile;
- restore selection uses a normal-distribution-like bias toward lower-loss pool entries with stddev 0.25, not deterministic `(seed + attempt) % better_half`;
- large-item disruption selects a random pair from the large-item candidate pool, not always the top two largest-area items;
- the large-item cutoff should follow the 0.75 convex-hull-area percentile idea as closely as the local fixed-sheet model permits;
- contained-item relocation remains;
- cross-sheet and rotation kicks may remain only as explicitly documented fixed-sheet extensions after the upstream-like swap, not as the primary disruption substitute.

Add tests:

- `strict_explore_uses_biased_pool_restore_not_seed_modulo`
- `strict_disruption_selects_random_large_item_pair_not_always_top_two`
- `fixed_sheet_extensions_are_documented_after_upstream_swap`

### 6. Report and mapping correction

The Q25-R5 report must contain these exact sections:

```text
SGH-Q25-R5_STATUS
UPSTREAM_COMMIT
PRE_TASK_GIT_STATUS
PRE_TASK_DIRTY_FILES
PRE_EXISTING_OUT_OF_SCOPE_DIRTY_FILES
TASK_CHANGED_FILES
OUT_OF_SCOPE_NEW_CHANGES
STRICT_PROFILE_CONFIG_AUDIT
TOUCHING_POLICY_AUDIT
SAMPLE_BUDGET_AUDIT
WORKER_ORDERING_AUDIT
SEPARATOR_LOOP_AUDIT
EXPLORATION_DISRUPTION_AUDIT
FIXED_SHEET_ADAPTATION_BOUNDARY
LEGACY_CORE_REGRESSION_GATE
TESTS_ADDED_OR_UPDATED
BUILD_TEST_RESULTS
```

If PASS, include these exact tokens:

```text
SGH-Q25-R5_STATUS: PASS
STRICT_PROFILE_DEFAULT: SPARROW_STRICT_PARITY
TOUCHING_POLICY_STRICT: CDE_TOUCHING_IS_COLLISION
VRS_TOUCH_ALLOWED_POLICY: EXPLICIT_NON_PARITY_MODE
SAMPLE_BUDGETS: UPSTREAM_PARITY
INSTANCE_COUNT_DOWNSCALING: DISABLED_IN_STRICT_PROFILE
WORKER_ORDERING: RNG_SHUFFLE_ONLY_IN_STRICT_PROFILE
SEPARATOR_LIMITS: UPSTREAM_PARITY_200_3
EXPLORATION_RESTORE: NORMAL_BIASED_POOL_SELECTION
DISRUPTION_SWAP: RANDOM_LARGE_ITEM_PAIR
COMPRESSION_STATUS: DEFERRED_ONLY
LV8_BENCHMARK_STATUS: NOT_USED_AS_ACCEPTANCE
OUT_OF_SCOPE_NEW_CHANGES: NONE
```

## Acceptance gate

Run, in order:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.py
./scripts/check.sh
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md
```

The report must include the exact result of every command. If any command is skipped or fails, do not mark the task PASS.
