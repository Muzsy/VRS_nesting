# SGH-Q24R1 — Native Sparrow parity lifecycle + LV8 gate completion

You are working in the VRS_nesting repository.

This is a hard REVISE-fix after SGH-Q24. Do not implement a small local speed patch and do not produce another report-only audit. The top priority is the complete and precise adoption of the original jagua_rs/Sparrow logic, adapted only where fixed-sheet nesting truly requires it.

## Read first

Read the current VRS state:

```text
codex/reports/egyedi_solver/sgh_q24_sparrow_parity_quality_hardening.md
codex/reports/egyedi_solver/sgh_q24_sparrow_parity_quality_hardening_measurements.md
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/optimizer/sparrow.rs
rust/vrs_solver/src/optimizer/search_position.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/optimizer/collision_severity.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/loss_model.rs
```

Then read the original Sparrow reference from the local clone:

```text
.cache/sparrow/src/optimizer/mod.rs
.cache/sparrow/src/optimizer/separator.rs
.cache/sparrow/src/optimizer/worker.rs
.cache/sparrow/src/sample/search.rs
.cache/sparrow/src/quantify/tracker.rs
.cache/sparrow/src/optimizer/explore.rs
.cache/sparrow/src/optimizer/compress.rs
```

The local `.cache/sparrow` clone is mandatory. If it is absent, mark the task `REVISE`; do not pretend to have compared the implementation.

## Non-negotiable goal

The goal is not merely to exclude bbox. The goal is a faithful jagua_rs/Sparrow-style solver.

BBox may remain only as broad-phase/hazard filtering. It must not be positive collision truth, production tracker/graph loss, final validity, or a fallback when CDE is expensive.

If CDE is too expensive, fix session reuse, active-set selection, and search lifecycle. Do not fall back to bbox/LBF/legacy.

## Q24 failure that must be fixed

Q24 status is `REVISE`:

- `lv8_12types_x1` timed out;
- `lv8_24_instances` timed out;
- exploration pool was not rewritten;
- compression was not rewritten;
- each candidate still effectively builds too much CDE state;
- production loss identity improved but tracker/graph still carries bbox-surrogate risk.

Q24R1 PASS is forbidden unless these are fixed.

## Required implementation

### 1. Write a Sparrow reference map in the report

Before or during implementation, map original Sparrow concepts to VRS files:

- Algorithm 11 optimize: `optimizer/mod.rs`
- Algorithm 9 separate: `optimizer/separator.rs`
- Algorithm 10 move_items_multi: `optimizer/separator.rs`
- Algorithm 5 worker move_items: `optimizer/worker.rs`
- Algorithm 6 search_placement: `sample/search.rs`
- Algorithm 8 tracker/update_weights: `quantify/tracker.rs`
- Algorithm 12 exploration: `optimizer/explore.rs`
- Algorithm 13 compression: `optimizer/compress.rs`

The report must state for each row whether VRS is `PARITY`, `FIXED_SHEET_ADAPTATION`, or `REVISE`.

### 2. CDE target-search session reuse

Implement a reusable per-target-search CDE session.

Bad current pattern:

```text
candidate sample → build CDE candidate session → evaluate → discard
candidate sample → build CDE candidate session → evaluate → discard
...
```

Required production pattern:

```text
worker target search → build CDE target-search session once
  focused samples reuse it
  container samples reuse it
  pre-refine CD reuses it
  final-refine CD reuses it
  separation probes reuse it where possible
```

Expected implementation direction:

```rust
struct CdeTargetSearchSession { ... }
```

or a clearly equivalent structure.

It must include active hazards, sheet exterior, hazard identity map, moving shape preparation, and reusable collector/query state where possible.

Diagnostics:

```text
cde_target_search_sessions
cde_candidate_session_builds
cde_candidate_evals_reused_session
cde_active_set_hazards_mean
cde_active_set_hazards_max
cde_collect_poly_collisions_calls
cde_separation_probe_calls
cde_session_reuse_ratio
cde_pairwise_fallback_queries
```

Hard gates:

```text
cde_pairwise_fallback_queries == 0
cde_session_reuse_ratio >= 0.80 on lv8_12types_x1 and lv8_24_instances
```

### 3. Active hazard set with full final validation

Implement active-set filtering for large LV8 layouts.

Allowed:

- bbox/AABB/spatial grid to choose possible hazards;
- deterministic expansion margin;
- same-sheet filtering;
- correctness-preserving hazard reduction.

Forbidden:

- declaring collision based on bbox;
- dropping possible hazards without proof;
- using active-set validation as final output validity.

Final commit must run full CDE validation of the emitted layout.

Diagnostics:

```text
active_set_candidates_considered
active_set_hazards_selected
active_set_full_validation_pairs
active_set_missed_collision_regressions
```

### 4. Worker `move_items` parity

The original Sparrow worker gives each currently colliding item a move opportunity in a worker-specific order. Implement the fixed-sheet equivalent.

Required:

- workers load master layout + tracker snapshot;
- collect all currently colliding/boundary-violating items;
- deterministic shuffle/order per worker;
- for each still-colliding item, call search placement;
- accept move only when weighted loss does not increase, except explicit disruption mode;
- after all workers finish, master loads best worker by weighted loss, raw loss, fixed-sheet objective, worker id.

Do not only move one target per iteration. Do not only try a small top-K once unless it is a documented bounded window and diagnostics prove enough colliding items were processed.

Diagnostics:

```text
sparrow_worker_colliding_items_seen
sparrow_worker_items_moved
sparrow_worker_items_skipped_clear
sparrow_worker_items_no_candidate
sparrow_worker_weighted_loss_nonincrease_violations
sparrow_worker_master_loads
sparrow_worker_best_selected
```

Hard gate:

```text
sparrow_worker_weighted_loss_nonincrease_violations == 0
sparrow_worker_colliding_items_seen > sparrow_worker_passes
```

on medium and LV8 hard rows.

### 5. Search placement parity

Implement original Sparrow-style search placement in VRS, not just a config bump.

Required behavior:

- focused sampler around current/reference placement;
- container-wide sampler;
- BestSamples/top-N retention;
- pre-refine coordinate descent on retained samples;
- final finer coordinate descent on the best sample;
- rotation wiggle only if the VRS rotation policy allows it.

Production `sparrow_cde` must not run with effectively disabled sampling.

Minimum diagnostics:

```text
search_container_samples
search_focused_samples
search_best_samples_retained
search_pre_refine_runs
search_final_refine_runs
search_rotation_wiggle_candidates
search_candidates_evaluated_total
```

Hard gate on medium and LV8 hard rows:

```text
search_container_samples > 0
search_focused_samples > 0
search_pre_refine_runs > 0
search_final_refine_runs > 0
```

### 6. Production CDE/shape-driven tracker loss

Q24 renamed the production loss identity but the tracker/graph still contains bbox-surrogate paths. Fix that.

Production `sparrow_cde` tracker/graph pair and boundary losses must be driven by CDE collision/separation information and shape scale, not bbox overlap/penetration.

Acceptable approaches:

- port Sparrow collision quantification from `.cache/sparrow/src/quantify` and adapt it to VRS/CDE;
- or implement a VRS CDE separation-distance quantifier that uses true CDE collision identities and shape geometry.

Forbidden:

- `dx * dy` area;
- bbox penetration depth as production graph/tracker loss;
- leaving `LossQualityRisk::SmoothBboxSurrogate` as the production CDE risk identity.

Diagnostics:

```text
loss_model_used
loss_bbox_proxy_used_as_primary
loss_bbox_proxy_queries
loss_cde_shape_queries
loss_boundary_cde_queries
```

Hard gates:

```text
loss_model_used != BboxAreaLoss
loss_model_used != PolePenetrationSmoothLoss
loss_bbox_proxy_queries == 0
loss_cde_shape_queries > 0
```

for production rows.

### 7. Exploration pool + disruption parity

Replace one-shot grid-spread restart with a real Sparrow exploration analogue.

Required:

- bounded infeasible solution pool sorted by raw loss;
- failed local-best infeasible layouts inserted into pool;
- biased restore favoring low-loss layouts;
- repeated attempts until budget/strike limit;
- deterministic large-item disruption;
- disruption must swap/relocate two large items and adjust nearby/practically-contained items where feasible;
- fixed-sheet-specific pressure proposals are allowed, but must be documented.

Diagnostics:

```text
exploration_pool_inserts
exploration_pool_size_max
exploration_pool_restores
exploration_pool_restore_rank_mean
exploration_disruptions_large_item_swap
exploration_disruptions_cluster_move
exploration_attempts
exploration_failed_attempts
exploration_best_infeasible_loss
exploration_best_feasible_found
```

Hard gate:

```text
exploration_pool_inserts > 0 on LV8 hard rows unless they converge before any failed attempt
exploration_pool_restores > 0 on LV8 hard rows unless they converge before any failed attempt
exploration_disruptions_large_item_swap > 0 on at least one LV8 hard row
```

### 8. Fixed-sheet compression parity

Replace the Q23R3/Q24 1mm left/down compaction.

Required fixed-sheet compression lifecycle:

1. restore best feasible incumbent;
2. create compact/shrink/pressure proposal;
3. apply it, allowing temporary collisions;
4. call separation to restore feasibility;
5. accept if feasible and objective improves;
6. reject/rollback otherwise;
7. decay pressure after failed attempts;
8. repeat within budget.

Diagnostics:

```text
compression_restore_attempts
compression_pressure_proposals
compression_separation_calls
compression_accepts
compression_rejects
compression_step_decay_events
compression_objective_before
compression_objective_after
compression_feasible_after_separation
```

Hard gate:

```text
compression_separation_calls > 0
compression_objective_after <= compression_objective_before
```

on rows where feasibility is reached and compression is attempted.

### 9. LV8 hard gates

Keep Q24's LV8 ladder. These hard rows must pass:

```text
medium_10_to_20_items: ok 12/12
lv8_12types_x1: ok 12/12
lv8_24_instances: ok 24/24
```

No downgrade to soft gate. No denominator tricks.

Expected caps:

```text
medium <= 45s
lv8_12types_x1 <= 60s
lv8_24_instances <= 90s
```

The larger rows are honest benchmark rows, not mandatory PASS:

```text
lv8_50_instances
lv8_100_instances (--full)
lv8_full_276 (--full)
```

### 10. No fallback policy

For every production hard row:

```text
optimizer_pipeline_used = sparrow_cde
backend_used = cde_adapter
final_commit_backend_used = cde_adapter
bbox_fallback_queries = 0
lbf_fallback_used = 0
legacy_fallback_used = 0
cde_pairwise_fallback_queries = 0
final_collision_pairs = 0
final_boundary_violations = 0
```

## Scripts

Create/update:

```text
scripts/smoke_sgh_q24r1_native_sparrow_parity_lifecycle.py
scripts/bench_sgh_q24r1_native_sparrow_parity_lifecycle.py
```

The smoke must fail on any hard gate failure.

The bench must write:

```text
codex/reports/egyedi_solver/sgh_q24r1_native_sparrow_parity_lifecycle_measurements.json
codex/reports/egyedi_solver/sgh_q24r1_native_sparrow_parity_lifecycle_measurements.md
```

## Report

Write:

```text
codex/reports/egyedi_solver/sgh_q24r1_native_sparrow_parity_lifecycle.md
codex/reports/egyedi_solver/sgh_q24r1_native_sparrow_parity_lifecycle.verify.log
```

The first line must be exactly:

```text
PASS
```

or:

```text
REVISE
```

PASS is forbidden unless every hard gate passes.

## Verification commands

Run:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q24r1_native_sparrow_parity_lifecycle.py
python3 scripts/bench_sgh_q24r1_native_sparrow_parity_lifecycle.py --quick
./scripts/check.sh
```

If a command cannot run, document the exact reason and mark `REVISE` unless the hard gates are otherwise executed with equivalent evidence.
