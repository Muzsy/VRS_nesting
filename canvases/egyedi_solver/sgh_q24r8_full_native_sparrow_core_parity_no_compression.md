# SGH-Q24R8 — Full native Sparrow core parity, compression excluded

## Why this task exists

Q24R5 successfully cut production `sparrow_cde` over to a native model. Q24R6 and Q24R7 added tracker/search/sampler pieces. Q24R7-R1 removed a fake dense guard and proved that the 191-instance first-sheet LV8 case now runs a real bounded search.

But the result exposed the real problem: the native core is still a simplified local implementation, not a complete jagua_rs/Sparrow logic port.

The 191 first-sheet probe was honest but weak:

```text
required: 191
validated placements: 36
unresolved/colliding: 155
final pairs: 178
initial raw loss: 5477.48
final raw loss: 9098.82
search calls: 6
worker candidates: 6
```

That is not an optimization-quality problem only. It means multiple core Sparrow mechanisms are still approximated, capped, bounded, or replaced by local surrogates.

## Strategic correction

Stop improving the current shortcuts. Port the missing native Sparrow core logic.

The target is not “a VRS solver that behaves a bit like Sparrow”. The target is a production `sparrow_cde` solver whose internals match the current jagua_rs/Sparrow architecture, except compression.

Compression remains explicitly out of scope. In this project, compression will be revisited later and only for the last used sheet in multisheet fixed-sheet nesting.

## Current gaps found in the repo

### 1. Dense search is artificially throttled

Current code contains dense-specific caps such as:

```rust
scaled_for_instance_count(instance_count >= 100):
worker_count = 2
focused_samples = 2
global_grid_n = 1
coord_descent_steps = 1

run_worker_pass(...):
max_targets = 1 for dense reference case

build_sheet_session(...):
others.truncate(24)

solve(... dense):
SparrowState::new_with_bounded_diag(..., 96)
final_validation_tracker_bounded(..., 192)
max_attempts = 1
```

These are not full Sparrow logic. They are diagnostic throttles.

### 2. Tracker loss is still surrogate-based

The module has `polygon_overlap_surrogate_loss` and `polygon_boundary_surrogate_loss`. This is not equivalent to Sparrow’s collision tracker, which uses CDE hazard collection and collision quantification.

The Q24R8 implementation must port/adapt real quantified loss:

```text
quantify_collision_poly_poly
quantify_collision_poly_container
CTEntry loss/weight
PairMatrix-equivalent storage
restore_but_keep_weights
register_item_move
loss/weighted_loss per item and total
GLS weight update proportional to current maximum loss
```

If the exact upstream functions are not directly available from the dependency, port the relevant implementation from `.cache/sparrow` into the native VRS Sparrow module.

### 3. Search is not full Sparrow search

Current `native_search_placement` is still a custom grid/focused/CD loop.

Q24R8 must port/adapt Sparrow’s search structure:

```text
SampleConfig
SampleEval
SampleEvaluator
BestSamples with uniqueness threshold
UniformBBoxSampler for container-wide samples
focused sampler around reference placement
pre-refine coordinate descent over best samples
final coordinate descent over best sample
rotation wiggle support for continuous/all-rotation cases
upper-bound pruning in evaluator
```

For fixed multisheet VRS, apply this per eligible sheet/container and keep sheet index as part of the candidate transformation.

### 4. Candidate evaluation is not SeparationEvaluator parity

Current `CandidateEvaluator` scores clear candidates with a bottom-left-ish quality and colliding candidates with local polygon surrogates.

Q24R8 must implement a real native `SeparationEvaluator` equivalent:

```text
candidate score = CDE collision existence + quantified pair/container loss
pair weights and container weights come from SparrowCollisionTracker
upper_bound pruning supported
clear candidates rank by deterministic quality only after collision loss is zero
```

### 5. Worker model is still too small

Current dense path moves only one target per worker and runs very few samples. Sparrow worker logic gives every currently colliding item a chance in a randomized order, then `move_items_multi` loads back the best worker state.

Q24R8 must implement the full logic:

```text
SeparatorWorker::load(master solution, tracker)
move_items() over all still-colliding items in shuffled order
search_placement(..., SeparationEvaluator, ...)
move_item remove/place/register_item_move
parallel or sequential workers allowed initially, but semantics must match
move_items_multi chooses lowest weighted-loss worker and loads it back
```

Sequential workers are acceptable if parallelization is too risky in this task, but `max_targets=1` and dense single-target shortcuts are not acceptable.

### 6. Separator loop contains local approximations/bugs

The separation loop must follow Sparrow Algorithm 9:

```text
min_loss_sol = current save + tracker snapshot
while strikes < strike_limit and not timeout:
  while iter_no_improvement < limit:
    move_items_multi
    if loss == 0 -> success
    else if loss < min_loss -> store best; reset no-improvement if substantial
    else no_improvement += 1
    update GLS weights
  update strikes based on strike loss improvement
  rollback to min-loss solution while keeping weights
```

Fix any local logic that makes substantial-improvement detection impossible or stale.

### 7. Exploration/disruption is only a skeleton

Q24R8 must port/adapt the non-compression part of Sparrow exploration:

```text
infeasible solution pool sorted by loss
biased random restore using a distribution favoring better solutions
large-item selection by convex-hull-area contribution percentile
swap two large sufficiently different items
move practically-contained items from old large-item space using CDE/POI containment logic
restore tracker correctly after disruption
```

For fixed-sheet multisheet: do not shrink strip width. The strip-shrink part is not applicable here. But the pool/restore/disrupt lifecycle is applicable and required.

### 8. Initial solution is still not LBFBuilder parity

Replace area-row/grid seed as the primary initial constructor.

Port/adapt Sparrow LBFBuilder:

```text
sort item types by convex_hull_area * diameter descending
repeat by quantity
for each item: search_placement with LBFEvaluator
place clear candidate
for fixed sheets: search eligible sheets; if not clear, place least-infeasible candidate honestly, not row-grid pileup
```

## Hard acceptance criteria

### Architecture

- Production `sparrow_cde` remains native: `SparrowProblem -> SparrowOptimizer::solve -> SparrowSolution`.
- No `WorkingLayout`, `VrsCollisionTracker`, `SparrowSeparationKernel`, `PhaseOptimizer`, `MultiSheetManager`, or old VRS solver core in production `optimizer/sparrow`.
- `crate::io::Placement` appears only at output projection/API boundary.

### Full core parity, compression excluded

Must implement or port these native modules/concepts:

- `LBFBuilder` equivalent.
- `CollisionTracker` equivalent with real CDE/hazard-based quantified loss.
- `SampleEval`, `SampleEvaluator`, `BestSamples`, `UniformBBoxSampler`, `coord_descent`, `search_placement` equivalent.
- `SeparationEvaluator` equivalent.
- `SeparatorWorker` equivalent.
- `Separator` Alg. 9 and `move_items_multi` Alg. 10 equivalent.
- `exploration_phase` / disruption Alg. 12 equivalent adapted to fixed sheets, with strip-shrink omitted.

### Forbidden shortcuts

Reject if any of these remains in the production `sparrow_cde` solve path:

```text
is_dense_reference_case
scaled_for_instance_count reducing dense to tiny search
max_targets = 1
others.truncate(24)
SparrowState::new_with_bounded_diag as production dense state
final_validation_tracker_bounded as production final validation
polygon_overlap_surrogate_loss as primary pair loss
polygon_boundary_surrogate_loss as primary boundary loss
row/grid constructive seed as primary initial solution
bbox/AABB as positive collision truth
compression
```

Bounded diagnostics may exist only in explicit test-only utilities, not in production acceptance/validation.

### Runtime gates

Run and report:

1. `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release`
2. `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`
3. `python3 scripts/smoke_sgh_q24r8_full_native_sparrow_core_parity_no_compression.py`
4. `./scripts/check.sh`
5. `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q24r8_full_native_sparrow_core_parity_no_compression.md`

Smoke expectations:

- Medium native CDE: 12/12 valid, final pairs 0, boundary 0.
- LV8 12 types × 1: 12/12 valid, final pairs 0, boundary 0.
- LV8 reference sheet-1 191 case: real full search/validation, not bounded/truncated. It may still be partial, but:
  - final raw loss must be lower than initial raw loss;
  - final collision pairs must be lower than initial collision pairs;
  - validated placements must be higher than Q24R7-R1 baseline 36;
  - search calls, evaluated samples, worker moves and CDE quantified queries must scale with the number of colliding items, not stay at `6`/`74`/`6`;
  - no fake solved metric from seed/output placement count.

## Report requirement

Write:

```text
codex/reports/egyedi_solver/sgh_q24r8_full_native_sparrow_core_parity_no_compression.md
```

Include:

- status line: `SGH-Q24R8_STATUS: PASS|REVISE`
- exact source files changed;
- a table mapping upstream Sparrow concept -> VRS native implementation file/function;
- proof that compression is still disabled;
- proof that dense caps/bounded validation/surrogate primary loss were removed;
- runtime metrics for medium, LV8 12×1, and LV8 first-sheet 191;
- explicit statement if 191 remains partial and why.
