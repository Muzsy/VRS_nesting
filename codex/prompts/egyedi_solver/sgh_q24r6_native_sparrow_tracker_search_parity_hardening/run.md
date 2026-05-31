# SGH-Q24R6 — Native Sparrow tracker + search parity hardening

You are working in the VRS_nesting repository.

Q24R5 completed the architectural cutover: production `sparrow_cde` now runs through the native Sparrow core. Q24R6 must **not** redo the architecture task and must **not** backslide into the old VRS solver core.

This is a **coding-first algorithmic hardening task**. The target is jagua_rs/Sparrow parity in the native tracker/search/separation lifecycle, **with compression still excluded**.

## Non-negotiable controlling objective

After this task, production `sparrow_cde` must still use:

```text
SparrowProblem -> SparrowOptimizer::solve -> SparrowSolution / SparrowSolveResult
```

But the native core must be stronger:

```text
SparrowCollisionTracker: CDE-truth quantified pair/container loss
native search: multi-sheet/container + rotation + global/focused/refined candidates
native workers: snapshots -> candidate states -> best-worker load-back
native exploration: pool/restore/disruption on native state
native diagnostics: truthful tracker/search/worker evidence
```

Compression is excluded. Do not enable it. Do not use it to pass acceptance. For our fixed multisheet target, compression is a later last-sheet-only layer after the full solver core is complete.

## Forbidden regression

Do not reintroduce the old VRS core into production `sparrow_cde`:

```text
WorkingLayout
VrsCollisionTracker
SparrowSeparationKernel
search_position_for_target(&WorkingLayout, ...)
build_constructive_seed_layout(...)
PhaseOptimizer
MultiSheetManager
legacy / LBF fallback
crate::io::Placement as internal native layout state
```

The only allowed VRS boundary remains input/output conversion.

## Mandatory reading before coding

Read these current project files:

```text
codex/reports/egyedi_solver/sgh_q24r5_architectural_native_sparrow_cutover.md
codex/reports/egyedi_solver/sgh_q24r5_architectural_native_sparrow_cutover.verify.log
scripts/smoke_sgh_q24r5_architectural_native_sparrow_cutover.py
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/optimizer/sparrow/mod.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/optimizer/collision_severity.rs
rust/vrs_solver/src/optimizer/loss_model.rs
```

Read the local Sparrow reference:

```text
.cache/sparrow/src/optimizer/mod.rs
.cache/sparrow/src/optimizer/separator.rs
.cache/sparrow/src/optimizer/worker.rs
.cache/sparrow/src/optimizer/explore.rs
.cache/sparrow/src/sample/search.rs
.cache/sparrow/src/quantify/tracker.rs
```

If `.cache/sparrow` is missing, run:

```bash
./scripts/ensure_sparrow.sh
```

Skim `.cache/sparrow/src/optimizer/compress.rs` only to confirm compression is out of scope.

## Starting audit facts you must address

Current Q24R5 native core has the right architecture, but it is too shallow:

1. `SparrowCollisionTracker` stores pair/boundary loss as simple `1.0` proxies.
2. `native_search_placement` ranks candidates mostly by `colliding_layout_idxs.len()` and boundary boolean.
3. Search currently centers on the current sheet (`cur.sheet_index`) instead of all eligible containers/sheets.
4. Worker logic is a sequential worker-shaped loop, not a real multi-worker candidate competition/load-back.
5. Exploration disruption is mostly largest-item swap.
6. Diagnostics under-report global/focused/refined samples and native tracker incremental updates.
7. No LV8 12-type native smoke is required yet.

Q24R6 must fix these directly in the native core.

## Required implementation

### 1. Keep and preferably split the native Sparrow module

The current native implementation may still be one large `mod.rs`. You may split it into production modules if useful:

```text
rust/vrs_solver/src/optimizer/sparrow/mod.rs
rust/vrs_solver/src/optimizer/sparrow/problem.rs
rust/vrs_solver/src/optimizer/sparrow/layout.rs
rust/vrs_solver/src/optimizer/sparrow/solution.rs
rust/vrs_solver/src/optimizer/sparrow/tracker.rs
rust/vrs_solver/src/optimizer/sparrow/search.rs
rust/vrs_solver/src/optimizer/sparrow/worker.rs
rust/vrs_solver/src/optimizer/sparrow/explore.rs
rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs
rust/vrs_solver/src/optimizer/sparrow/rng.rs
```

Splitting is optional. Native behavior is mandatory.

### 2. Replace count-only tracker loss with CDE-truth quantified loss

Current bad pattern:

```rust
pair_loss.insert(key, 1.0);
boundary_loss[i] = 1.0;
score = res.colliding_layout_idxs.len() as f64 + boundary_bool;
```

This is not enough. It gives the optimizer almost no gradient. Implement quantified CDE-truth loss for pair and boundary/container violations.

Preferred approach:

- Port the useful idea from `collision_severity.rs` / CDE batch separation loss into the native core, but without `WorkingLayout` and without `crate::io::Placement` as internal state.
- For a colliding candidate, estimate the minimum translation distance to clear using a small set of directions with bracket + binary refinement, reusing a `CdeCandidateSession` or equivalent native CDE batch session.
- Use that distance as positive loss.
- Use the same or compatible quantified semantics for boundary/container violation.

Hard requirements:

- CDE remains the only positive collision truth.
- Bbox/AABB may only prune impossible collisions as no-collision, never produce positive loss truth.
- Pair/container raw loss must be numeric severity, not only count.
- Weighted loss must be raw quantified loss × GLS weights.
- Per-item loss must sum quantified touching records.
- Unsupported geometry must be treated honestly, not as no-collision.

### 3. Strengthen `SparrowCollisionTracker`

Implement/verify these operations on native state:

```text
full_rebuild(layout)
update_after_move(item)
snapshot()
restore_keep_weights(snapshot)
total_raw_loss()
total_weighted_loss()
weighted_loss_for_item(item)
offending/colliding item ordering
final_validation(layout)
```

Diagnostics must expose actual solve-time values:

```text
native_tracker_full_rebuilds
native_tracker_incremental_updates
pair loss records
boundary/container loss records
quantified pair queries / boundary queries / unsupported queries
```

Do not emit only the final validation rebuild count; that hides real behavior.

### 4. Strengthen native search

`native_search_placement` or equivalent must evaluate candidates across eligible sheets/containers, not only the current sheet.

Required candidate sources:

- current placement candidate;
- focused samples around the current placement / collision neighborhood;
- global/container-wide grid or random samples on every eligible sheet;
- all allowed rotations;
- coordinate-descent/refinement on top candidates.

Required scoring:

- Use quantified CDE loss from the native tracker/search evaluator.
- Prefer zero-loss candidates.
- Tie-break deterministically with stable ordering.
- Track search diagnostics:
  - calls;
  - global samples;
  - focused samples;
  - refined samples;
  - coordinate descent steps;
  - unsupported samples;
  - best eval;
  - per-sheet candidates/evaluations if practical.

### 5. Implement real native worker competition

The current sequential pass is not enough. Implement a real native worker mechanism:

- Create multiple worker snapshots from the same master state.
- Give workers different deterministic target orders/seeds/candidate selection biases.
- Let each worker attempt a move batch on native layout/tracker.
- Compute each worker candidate raw and weighted loss.
- Select the best worker deterministically.
- Load the best worker state back into the master.
- Roll back rejected candidates cleanly.
- Preserve or update GLS weights with Sparrow-like semantics.

Minimum expected concepts, names can differ:

```text
WorkerCandidate
WorkerSnapshot / worker state clone
move_items_multi
run_worker_pass
compare_worker_candidates
load_best_worker
```

Diagnostics must report:

```text
worker_count
worker_passes
worker_candidates_evaluated
worker_commits
worker_rollbacks
worker_best_loss
multi_target_items_attempted
multi_target_items_accepted
multi_target_items_rejected
topk_target_count
```

### 6. Improve exploration/disruption, still without compression

Exploration must remain native:

- pool least-infeasible native layouts/states;
- biased restore from pool;
- disruption after restore;
- disruption must be stronger than only swapping the two largest items.

Add at least one of:

- move high-loss item to another eligible sheet/container;
- randomize high-loss cluster positions;
- rotate high-loss item to an alternate allowed rotation;
- contained-area / empty-space biased relocation;
- deterministic multi-item perturbation.

Do not implement strip-width shrink or compression for this task.

### 7. Keep medium gate and add LV8 12 type × 1 smoke

Medium gate remains hard:

```text
12/12 placed
final pairs 0
boundary 0
pipeline sparrow_cde
CDE backend used
native model active true
old core false
no fallback
compression zero/disabled
```

Add an LV8 smoke based on:

```text
tests/fixtures/nesting_engine/ne2_input_lv8jav.json
```

LV8 smoke requirements:

- outer-only for now;
- 12 part types × quantity 1;
- sheet from fixture, default 1500×3000 if missing;
- production `sparrow_cde`;
- CDE backend;
- orthogonal rotations from fixture;
- not full 276 yet;
- report status, placed/required, final pairs, boundary, runtime, native flags, search/tracker/worker diagnostics.

The LV8 12×1 smoke should be a gate if reasonable. If it fails due to a real geometry/CDE blocker, report the exact blocker and do not fake success.

## Required smoke script

Add:

```text
scripts/smoke_sgh_q24r6_native_sparrow_tracker_search_parity_hardening.py
```

It must include:

1. static anti-regression gate preserving Q24R5 architecture;
2. static gate rejecting binary count-only tracker/search patterns;
3. static gate requiring multi-sheet search and real worker snapshot/competition concepts;
4. runtime medium CDE gate;
5. runtime LV8 12 type × 1 smoke.

## Required commands

Run and capture evidence:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q24r6_native_sparrow_tracker_search_parity_hardening.py
./scripts/check.sh
```

## Required report

Write:

```text
codex/reports/egyedi_solver/sgh_q24r6_native_sparrow_tracker_search_parity_hardening.md
codex/reports/egyedi_solver/sgh_q24r6_native_sparrow_tracker_search_parity_hardening.verify.log
```

The report must include:

- final status: `PASS` or `REVISE`;
- exact files changed;
- what changed in tracker quantification;
- what changed in search;
- what changed in worker competition;
- what changed in exploration/disruption;
- exact medium CDE result;
- exact LV8 12×1 result;
- build/test/check evidence;
- known remaining gaps toward full jagua_rs/Sparrow parity.

## Acceptance

PASS only if:

- Q24R5 native architecture is preserved;
- production `sparrow_cde` remains native;
- tracker loss is no longer binary count-only;
- search considers multiple eligible sheets/containers;
- worker snapshot/competition/load-back exists;
- medium CDE passes without fallback/compression;
- LV8 12 type × 1 is attempted and reported;
- evidence is real, not only docs.

## Explicit non-goals

- Full LV8 276 acceptance.
- Compression hardening.
- Last-sheet compression.
- Hole/cavity production semantics.
- Removing all legacy files from unrelated explicit legacy pipelines.
