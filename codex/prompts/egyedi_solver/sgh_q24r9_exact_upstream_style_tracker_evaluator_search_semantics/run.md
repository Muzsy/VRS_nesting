# SGH-Q24R9 Exact upstream-style tracker/evaluator/search semantics, compression excluded

## Why this task exists

Q24R8 was a real step forward: production `sparrow_cde` stayed on the native `SparrowProblem -> SparrowOptimizer -> SparrowSolution` path, and the code now contains LBF/search/evaluator/worker/separator/exploration-like structures.

But Q24R8 did **not** complete the jagua_rs/Sparrow core port. It still contains proxy math and local shortcuts inside the supposedly native core.

The dense LV8 first-sheet probe improved, but it remains weak:

```text
required: 191
validated placements: 39
initial raw loss: 381928.401
final raw loss: 216263.248
initial pairs: 202
final pairs: 152
status: partial
```

This is not primarily a benchmark problem. It means the core evaluator/search/tracker semantics still do not match Sparrow strongly enough.

## Strategic correction

Do not add another broad feature mix. Do not tune dense constants. Do not implement compression.

Replace the remaining **proxy native Sparrow core** with **exact upstream-style tracker/evaluator/search semantics**, adapted only where fixed multisheet geometry requires it.

The correct direction is:

```text
native model already exists
-> make its tracker/evaluator/search mathematically Sparrow-like
-> then scale LV8
```

## Current Q24R8 gaps that must be closed

### 1. Pair/container quantification still uses bbox proxy

Current Q24R8 contains functions shaped like:

```rust
fn quantify_collision_poly_poly_native(candidate, fixed) -> f64 {
    let ix = ... max_x/min_x ...
    let iy = ... max_y/min_y ...
    let overlap_proxy = ix * iy;
    ...
}

fn quantify_collision_poly_container_native(candidate, sheet) -> f64 {
    let inside_x = ... max_x/min_x ...
    let inside_y = ... max_y/min_y ...
    let outside_proxy = bbox - inside_x * inside_y;
    ...
}
```

This is not jagua_rs/Sparrow tracker parity. CDE may confirm that a collision exists, but the loss magnitude is still bbox/AABB-derived.

Q24R9 must replace this with CDE/hazard/resolution-style quantification. If the exact upstream quantification functions are not directly exposed by local dependencies, port the relevant implementation from `.cache/sparrow/src/quantify` or implement an equivalent CDE-probe resolution metric that does not use bbox overlap as primary loss.

### 2. CDE probe helpers exist but are not the primary quantification path

Q24R8 has probe-style helpers, but warnings previously showed they were unused or not central. Q24R9 must make them part of the real tracker/evaluator path or replace them with a better upstream-port implementation.

### 3. SeparationEvaluator uses local weighting, not tracker/GLS semantics

The evaluator currently computes candidate loss by local base loss and ad hoc weights. It must use the native `SparrowCollisionTracker` pair/container entries and GLS weights as the authority.

### 4. Coord descent has no real rotation wiggle

The current refinement path uses translational axes; rotation delta is effectively zero. This is insufficient for the long-term target of 45-degree and continuous/all-rotation policies.

Q24R9 must implement rotation-aware refinement where the input rotation policy allows it. Orthogonal-only fixtures may still use discrete rotations, but the code must support nonzero rotation wiggle for continuous/all-rotation profiles.

### 5. Worker acceptance is too permissive

Q24R8 accepts moves if item weighted loss improves **or** total raw loss improves **or** pair count improves. Upstream semantics should be stricter: candidate evaluation should be driven by weighted collision loss and per-move tracker state, not loose global tie-ins that can increase local damage.

### 6. Dense result still proves weak search quality

Q24R9 is not expected to solve the full 191 first-sheet case perfectly, but it must show a clear improvement caused by exact semantics, not by constants only.

## Required implementation work

### A. Read upstream/reference files before coding

You must read the locally cloned Sparrow source:

```text
.cache/sparrow/src/quantify/tracker.rs
.cache/sparrow/src/quantify/mod.rs
.cache/sparrow/src/eval/sample_eval.rs
.cache/sparrow/src/eval/sep_evaluator.rs
.cache/sparrow/src/eval/lbf_evaluator.rs
.cache/sparrow/src/sample/search.rs
.cache/sparrow/src/sample/best_samples.rs
.cache/sparrow/src/sample/coord_descent.rs
.cache/sparrow/src/sample/uniform_sampler.rs
.cache/sparrow/src/optimizer/worker.rs
.cache/sparrow/src/optimizer/separator.rs
.cache/sparrow/src/optimizer/explore.rs
```

If `.cache/sparrow` is missing, stop and return `REVISE`. Do not invent a new local heuristic while claiming parity.

### B. Replace bbox-proxy quantification

Refactor the tracker quantification layer so production loss is not based on:

```text
ix * iy
inside_x * inside_y
bbox_area - inside_area
overlap_proxy
outside_proxy
```

Required behavior:

- pair collision truth comes from CDE;
- container collision truth comes from CDE;
- pair loss magnitude is CDE/hazard/resolution-distance based;
- container loss magnitude is CDE/hazard/resolution-distance based;
- quantification records diagnostic counters separately:
  - CDE pair truth queries,
  - CDE boundary truth queries,
  - pair quantification probes,
  - boundary quantification probes,
  - early-pruned evaluations;
- bbox/AABB may remain only as broad-phase candidate generation or direction hint, not as loss magnitude.

### C. Make `SparrowCollisionTracker` the evaluator authority

The tracker must expose upstream-style functions or equivalents:

```text
pair_loss(i, j)
pair_weight(i, j)
container_loss(i)
container_weight(i)
item_raw_loss(i)
item_weighted_loss(i)
total_raw_loss()
total_weighted_loss()
colliding_indices()
snapshot()
restore_keep_weights()
update_weights_gls()
register_item_move()/update_after_move()
```

`SeparationEvaluator` and `LBFEvaluator` must consume these weights instead of inventing local weights from `base` loss.

### D. Implement upstream-style `SeparationEvaluator`

The evaluator must:

- build a CDE session for the target sheet/container;
- query candidate shape;
- collect candidate pair/container hazards;
- quantify only the candidate hazards;
- apply tracker weights;
- support upper-bound early termination;
- rank clear candidates by deterministic secondary quality only after zero collision loss;
- never use bbox overlap/centroid/vertex-count as primary loss.

### E. Implement upstream-style `LBFEvaluator`

The initial constructor must use an LBF evaluator that still respects CDE truth. If no clear sample exists, the least-infeasible candidate must be chosen from CDE-quantified candidates, not an AABB overlap fallback.

### F. Implement rotation-aware coordinate descent

`refine_coord_desc` must support nonzero rotation delta when the part/input rotation policy allows it.

Acceptance evidence must include a tiny synthetic continuous/all-rotation probe or unit test where the code path executes nonzero rotation steps. The LV8 orthogonal case alone is not enough.

### G. Tighten worker acceptance semantics

Replace loose acceptance rules such as:

```rust
new_w <= old_w || new_total < old_total || new_pairs < old_pairs
```

with upstream-style acceptance driven by candidate weighted loss and tracker state. If tie-breakers are needed, they must be deterministic and must not allow the moved item’s weighted loss to get worse just because global pair count happens to drop.

### H. Keep native architecture and compression exclusion

Do not regress:

```text
SparrowProblem -> SparrowOptimizer::solve -> SparrowSolution
```

Do not reintroduce:

```text
WorkingLayout
VrsCollisionTracker
SparrowSeparationKernel
PhaseOptimizer
MultiSheetManager
legacy fallback
crate::io::Placement as internal native layout state
```

Do not implement or enable compression in this task.

## Acceptance gates

### Static gates

The smoke must fail if production `optimizer/sparrow` still contains any of these as primary semantics:

```text
overlap_proxy
outside_proxy
inside_x
inside_y
bbox_area(candidate) in quantification
candidate.max_x.min(fixed.max_x) in pair loss
candidate.max_x.min(sheet.max_x) in container loss
new_total < old_total || new_pairs < old_pairs worker acceptance
rotation delta always 0.0 in coord descent
polygon_overlap_surrogate_loss
polygon_boundary_surrogate_loss
```

### Runtime gates

Run:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q24r9_exact_upstream_style_tracker_evaluator_search_semantics.py
./scripts/check.sh
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q24r9_exact_upstream_style_tracker_evaluator_search_semantics.md
```

The smoke must include:

1. **Medium native CDE regression**
   - status `ok`;
   - 12/12 placed;
   - final pairs 0;
   - boundary violations 0;
   - compression passes 0.

2. **LV8 12 types × 1 regression**
   - status `ok`;
   - 12/12 placed;
   - final pairs 0;
   - boundary violations 0.

3. **LV8 reference sheet 1 / 191 progress gate**
   - real runtime, not guarded partial;
   - full final validation;
   - final raw loss < initial raw loss;
   - final pairs < initial pairs;
   - validated placements > Q24R8 baseline `39`;
   - target improvement for this task:
     - final pairs <= 120, or explain exact blocker in report if not achieved;
     - validated placements >= 60, or explain exact blocker in report if not achieved;
   - partial status is allowed, but must be honest and include unresolved instance IDs/reasons.

4. **Continuous/rotation wiggle micro-probe**
   - a small synthetic fixture or unit test must exercise nonzero rotation refinement;
   - this may be a diagnostic/unit smoke if the public input schema cannot yet express continuous rotation cleanly;
   - do not claim continuous rotation parity without evidence.

## Required report

Write:

```text
codex/reports/egyedi_solver/sgh_q24r9_exact_upstream_style_tracker_evaluator_search_semantics.md
```

It must include:

- `SGH-Q24R9_STATUS: PASS|REVISE`;
- upstream-to-local parity map for tracker/evaluator/search;
- exact changed files;
- proof that bbox-proxy loss is not primary;
- proof that CDE/hazard quantification is primary;
- medium/LV8 runtime metrics;
- dense 191 metrics compared to Q24R8;
- explicit compression disabled proof;
- blockers if 191 is still partial.

## Reject conditions

Return `REVISE` if any of these are true:

- `.cache/sparrow` was not read and no upstream parity map was produced;
- pair/container loss is still bbox-overlap/outside-area proxy;
- evaluator still uses local ad hoc weights instead of tracker/GLS weights;
- worker still accepts moves by loose `new_total/new_pairs` improvement while moved item gets worse;
- coordinate descent has no nonzero rotation path;
- dense 191 smoke is guarded/short-circuited/fake placed metric;
- compression is implemented or enabled;
- production `sparrow_cde` returns to old VRS core.
