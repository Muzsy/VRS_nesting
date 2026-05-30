# SGH-Q24R1 — Native Sparrow parity lifecycle + LV8 gate completion

## Purpose

Complete the next step toward a faithful jagua_rs/Sparrow solver, adapted to VRS fixed-sheet nesting.

This is not a generic optimization task and not a CDE-only speed patch. The top priority is the **complete and precise adoption of the original jagua_rs/Sparrow logic** where it applies to our problem.

Q24 is `REVISE` because:

- `lv8_12types_x1` timed out;
- `lv8_24_instances` timed out;
- exploration pool was not rewritten;
- compression lifecycle was not rewritten;
- CDE session is still built per candidate instead of per target-search / active hazard set;
- the tracker/loss still contains bbox-derived surrogate paths in production CDE mode.

Q24R1 must address these as one coherent Sparrow-parity lifecycle change.

## Reference that must be used

The local repo contains a gitignored clone:

```text
.cache/sparrow
```

The executor must read it directly. Do not rely only on memory or previous reports.

Map and use at minimum these Sparrow files:

```text
.cache/sparrow/src/optimizer/mod.rs
.cache/sparrow/src/optimizer/separator.rs
.cache/sparrow/src/optimizer/worker.rs
.cache/sparrow/src/sample/search.rs
.cache/sparrow/src/quantify/tracker.rs
.cache/sparrow/src/optimizer/explore.rs
.cache/sparrow/src/optimizer/compress.rs
```

Also inspect `.cache/sparrow`'s jagua-rs usage and, if available locally, `.cache/jagua-rs` or the dependency sources used by `.cache/sparrow`.

Before implementation, produce a short internal reference map in the final report, naming which VRS files correspond to each Sparrow file.

## Current VRS files to inspect

```text
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/optimizer/sparrow.rs
rust/vrs_solver/src/optimizer/search_position.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/optimizer/collision_severity.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/loss_model.rs
scripts/smoke_sgh_q24_sparrow_parity_quality_hardening.py
scripts/bench_sgh_q24_sparrow_parity_quality_hardening.py
codex/reports/egyedi_solver/sgh_q24_sparrow_parity_quality_hardening.md
codex/reports/egyedi_solver/sgh_q24_sparrow_parity_quality_hardening_measurements.md
```

## Hard principle

The goal is not to exclude bbox. The goal is a faithful Sparrow solver.

BBox exclusion is only a consequence:

- bbox may be used for broad-phase candidate/hazard filtering only;
- bbox must not be positive collision truth;
- bbox must not be final validity;
- bbox must not be production `sparrow_cde` primary search loss;
- bbox must not be a fallback when CDE is expensive.

If CDE is too expensive, fix the CDE lifecycle/session/active-set architecture. Do not degrade the solver to bbox logic.

## Required implementation

### A. Sparrow reference map and acceptance guard

Add a report section mapping original Sparrow logic to VRS logic:

| Sparrow concept | Original file | VRS implementation | Status |
|---|---|---|---|
| Algorithm 11 optimize | optimizer/mod.rs | adapter + sparrow pipeline | ... |
| Algorithm 9 separate | optimizer/separator.rs | SparrowSeparationKernel | ... |
| Algorithm 10 move_items_multi | optimizer/separator.rs | worker pass | ... |
| Algorithm 5 worker move_items | optimizer/worker.rs | VRS worker target loop | ... |
| Algorithm 6 search_placement | sample/search.rs | search_position | ... |
| Algorithm 8 tracker/weights | quantify/tracker.rs | VrsCollisionTracker/SparrowGraph | ... |
| Algorithm 12 exploration | optimizer/explore.rs | VRS exploration pool | ... |
| Algorithm 13 compression | optimizer/compress.rs | VRS fixed-sheet compression | ... |

A `PASS` is forbidden unless every row except intentionally fixed-sheet-specific differences is implemented or explicitly justified.

### B. CDE search session reuse: per target-search, not per candidate

Q24's blocker was per-candidate CDE session cost. Fix this structurally.

Implement a reusable CDE search/evaluation session with this shape:

```rust
CdeTargetSearchSession
```

It must be built once per worker/target search and reused for:

- container-wide samples;
- focused samples;
- pre-refine coordinate descent;
- final refine coordinate descent;
- separation-distance probes where possible.

It must hold:

- moving part prepared geometry;
- active same-sheet hazards;
- sheet exterior hazard;
- hazard identity map;
- reusable collector / CDE objects where jagua-rs allows it;
- deterministic counters.

Expected API direction:

```rust
let mut session = CdeTargetSearchSession::new(layout, target_idx, parts, sheets, active_set, ...)?;
let eval = session.evaluate_candidate(transform)?;
let sep_loss = session.separation_loss(transform, ...)?;
```

The old `CdeCandidateSession` may remain as a lower-level primitive, but production search must not build a new session for every candidate sample.

Diagnostics required:

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

Hard gate:

```text
cde_pairwise_fallback_queries == 0
cde_session_reuse_ratio >= 0.80 on lv8_12types_x1 and lv8_24_instances
```

### C. Active hazard set, CDE truth only

Introduce active-set filtering for large layouts.

Allowed:

- bbox / spatial grid / AABB broad-phase to choose possible hazards;
- deterministic safety expansion margin;
- cap active hazards by proximity only if correctness remains guaranteed by including all possible overlapping hazards.

Forbidden:

- treating broad-phase overlap as collision truth;
- dropping hazards without a correctness reason;
- final validity based on active-set only.

Final commit must still validate the full layout with CDE/exact backend.

Diagnostics:

```text
active_set_candidates_considered
active_set_hazards_selected
active_set_full_validation_pairs
active_set_missed_collision_regressions
```

Hard gate:

```text
active_set_missed_collision_regressions == 0
final_commit_backend_used == cde_adapter
```

### D. Replace the weak VRS worker loop with Sparrow-style worker `move_items`

The original Sparrow worker gives every currently colliding item a chance to move in a randomized order, with each worker using its own order/RNG, then the master accepts the worker with the best weighted loss.

Implement the fixed-sheet analogue:

- each worker starts from master layout + tracker snapshot;
- collect all currently colliding/boundary-violating items;
- deterministic seeded shuffle per worker;
- for each still-colliding item, run search placement;
- move item only if weighted loss does not increase, or if it is part of the explicitly documented escape/disruption rule;
- after all worker moves, choose best worker by weighted loss, then raw loss, then fixed-sheet objective, then deterministic worker id.

Do not only move top-1 or top-K once. Top-K may be used for priority, but each worker must be able to process the full colliding set or a documented bounded window with diagnostics.

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
sparrow_worker_colliding_items_seen > sparrow_worker_passes on medium and lv8_12types_x1
```

### E. Search placement parity

The original Sparrow `search_placement` uses:

- focused sampler around the current/reference placement;
- container-wide sampler;
- `BestSamples` top candidates;
- coordinate descent refinement of best samples;
- final finer coordinate descent refinement;
- rotation wiggle only when continuous rotation is allowed.

Implement this in VRS `search_position`, not as a fake config bump.

Minimum production profile for `sparrow_cde`:

```text
container_samples >= 32 for medium, adaptive higher for LV8
focused_samples >= 16
coord_descents >= 4
pre_refine_cd enabled
final_refine_cd enabled
rotation wiggle only when rotation policy permits it
```

Adaptive budgets are allowed, but reducing all of them to near-zero is forbidden.

Diagnostics:

```text
search_container_samples
search_focused_samples
search_best_samples_retained
search_pre_refine_runs
search_final_refine_runs
search_rotation_wiggle_candidates
search_candidates_evaluated_total
```

Hard gate:

```text
search_container_samples > 0
search_focused_samples > 0
search_pre_refine_runs > 0
search_final_refine_runs > 0
```

on medium and LV8 hard-gate rows.

### F. Collision quantification parity: remove bbox surrogate as production CDE tracker loss

Production `sparrow_cde` must not use bbox overlap/penetration as the tracker/graph pair loss.

Implement a CDE-backed quantifier for pair/container loss. It may use:

- CDE separation distance;
- shape scale from polygon/surrogate area;
- probe-based collision depth;
- jagua_rs/Sparrow-inspired shape penalty if ported from `.cache/sparrow`.

But it must be driven by CDE collision truth and shape geometry, not bbox overlap.

`LossQualityRisk` for production `CdeSeparation` must not remain `SmoothBboxSurrogate`. Introduce a production identity such as:

```rust
CdeShapeSeparation
```

or equivalent.

Diagnostics:

```text
loss_model_used = CdeShapeSeparationLoss or equivalent
loss_bbox_proxy_used_as_primary = false
loss_bbox_proxy_queries = 0 for production tracker/graph loss
loss_cde_shape_queries > 0
loss_boundary_cde_queries > 0 when boundary violations exist
```

Hard gate:

```text
loss_bbox_proxy_queries == 0
loss_model_used != BboxAreaLoss
loss_model_used != PolePenetrationSmoothLoss
```

for production `sparrow_cde` rows.

### G. Exploration pool and disruption parity

Replace the Q23R3/Q24 one-shot grid restart with a real Sparrow exploration analogue.

Required:

- bounded infeasible solution pool sorted by raw loss;
- insertion of failed local-best infeasible solutions;
- biased restore from pool, favoring lower loss;
- deterministic large-item disruption;
- disruption must swap/relocate two large items and move practically-contained/nearby items where applicable;
- repeated attempts until time/attempt/strike limit, not one restart.

Because VRS is fixed-sheet, strip-width shrink becomes fixed-sheet pressure:

- try tighter occupied extent / compaction envelope;
- try sheet redistribution pressure;
- try cluster spread/split pressure;
- then call separation.

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

### H. Compression parity for fixed sheets

Replace one-millimeter left/down compaction with a Sparrow compression analogue.

Original Sparrow compression is restore incumbent → shrink → separate → accept feasible / reject infeasible. Fixed-sheet analogue:

1. restore best feasible incumbent;
2. propose a compacted virtual envelope / sheet pressure / cluster compression;
3. apply the proposal, possibly creating collisions;
4. run full separation to restore feasibility;
5. accept only if feasible and fixed-sheet objective improves;
6. reject/rollback otherwise;
7. decay step/pressure after failed attempts;
8. repeat under budget.

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
compression_separation_calls > 0 on medium and LV8 hard rows that reach feasibility
compression_objective_after <= compression_objective_before on accepted compression
```

### I. LV8 hard gates

Keep Q24's LV8 ladder and make these hard gates pass:

```text
medium_10_to_20_items: ok 12/12
lv8_12types_x1: ok 12/12
lv8_24_instances: ok 24/24
```

Full `lv8_50_instances`, `lv8_100_instances`, and `lv8_full_276` are not mandatory PASS in Q24R1, but must be counted honestly when run.

Runtime caps:

```text
medium: <= 45s
lv8_12types_x1: <= 60s
lv8_24_instances: <= 90s
```

If local hardware is slower, use proportional reporting, but do not mark PASS if the rows time out under the task runner's explicit caps.

### J. Result truth and fallback policy

For every production row:

```text
optimizer_pipeline_used = sparrow_cde
backend_used = cde_adapter
final_commit_backend_used = cde_adapter
bbox_fallback_queries = 0
lbf_fallback_used = 0
legacy_fallback_used = 0
cde_pairwise_fallback_queries = 0
status must be ok for hard rows
```

No hidden denominator reduction. Timeouts/errors count.

## Required scripts

Create or update:

```text
scripts/smoke_sgh_q24r1_native_sparrow_parity_lifecycle.py
scripts/bench_sgh_q24r1_native_sparrow_parity_lifecycle.py
```

The smoke script must exit non-zero if any hard gate fails.

The bench script must write:

```text
codex/reports/egyedi_solver/sgh_q24r1_native_sparrow_parity_lifecycle_measurements.json
codex/reports/egyedi_solver/sgh_q24r1_native_sparrow_parity_lifecycle_measurements.md
```

## Required report

Write:

```text
codex/reports/egyedi_solver/sgh_q24r1_native_sparrow_parity_lifecycle.md
codex/reports/egyedi_solver/sgh_q24r1_native_sparrow_parity_lifecycle.verify.log
```

The report must start with exactly one of:

```text
PASS
REVISE
```

`PASS` is forbidden unless all hard gates pass.

## Verification commands

Run at minimum:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q24r1_native_sparrow_parity_lifecycle.py
python3 scripts/bench_sgh_q24r1_native_sparrow_parity_lifecycle.py --quick
./scripts/check.sh
```

If a command cannot run, document the exact reason. Do not mark PASS without the Q24R1 smoke and hard LV8 gates.
