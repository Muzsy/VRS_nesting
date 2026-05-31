# SGH-Q24R8 — Full native Sparrow core parity, compression excluded

You are working in `/home/muszy/projects/VRS_nesting`.

This task is a hard reset to the real objective. Do **not** treat it as Q24R7-R1 dense tuning. The goal is to complete the production `sparrow_cde` implementation by porting/adapting the missing native jagua_rs/Sparrow core logic.

Compression is explicitly out of scope.

## 0. Controlling objective

After this task, production `sparrow_cde` must be a real native Sparrow implementation, not a local simplified solver with Sparrow-shaped names.

The target production path is:

```text
VRS input boundary
→ SparrowProblem / SPInstance
→ native LBFBuilder-equivalent initial construction
→ native CollisionTracker with real CDE hazard quantification
→ native SeparationEvaluator / SampleEvaluator
→ native search_placement with BestSamples + uniform sampling + two-stage coordinate descent
→ native SeparatorWorker::move_items over all colliding items
→ native Separator Algorithm 9 + move_items_multi Algorithm 10
→ native exploration pool / biased restore / disruption Algorithm 12 adaptation
→ full CDE final validation
→ SparrowSolution
→ VRS output projection boundary
```

Do not implement compression. Do not add a compression pass. Do not harden the old VRS core.

## 1. Mandatory reading before coding

Read the current local implementation:

```text
rust/vrs_solver/src/optimizer/sparrow/mod.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/io.rs
codex/reports/egyedi_solver/sgh_q24r7r1_dense_first_sheet_real_run_fix.md
scripts/smoke_sgh_q24r7r1_dense_first_sheet_real_run_fix.py
tests/fixtures/nesting_engine/ne2_input_lv8jav.json
```

Then read the upstream/reference Sparrow code from the locally cloned ignored repo:

```text
.cache/sparrow/src/optimizer/mod.rs
.cache/sparrow/src/optimizer/lbf.rs
.cache/sparrow/src/optimizer/separator.rs
.cache/sparrow/src/optimizer/worker.rs
.cache/sparrow/src/optimizer/explore.rs
.cache/sparrow/src/sample/search.rs
.cache/sparrow/src/sample/best_samples.rs
.cache/sparrow/src/sample/coord_descent.rs
.cache/sparrow/src/sample/uniform_sampler.rs
.cache/sparrow/src/eval/sample_eval.rs
.cache/sparrow/src/eval/sep_evaluator.rs
.cache/sparrow/src/eval/lbf_evaluator.rs
.cache/sparrow/src/quantify/tracker.rs
.cache/sparrow/src/quantify/mod.rs
```

If `.cache/sparrow` is missing, stop and report `REVISE` with that blocker. Do not invent approximations.

## 2. Current implementation problems that must be fixed

The current Q24R7-R1 native solver still has these non-Sparrow shortcuts. Remove them from production `sparrow_cde` semantics:

```text
scaled_for_instance_count(instance_count >= 100) tiny dense config
is_dense_reference_case
max_targets = 1 for dense
others.truncate(24)
SparrowState::new_with_bounded_diag(..., 96)
final_validation_tracker_bounded(..., 192)
max_attempts = 1 for dense
polygon_overlap_surrogate_loss as primary pair loss
polygon_boundary_surrogate_loss as primary boundary loss
area row/grid seed as primary constructor
fixed 1x1 global grid / tiny focused sampling for dense
```

These may have been acceptable for proving a real run. They are not acceptable for complete Sparrow implementation.

## 3. Required implementation work

### 3.1 Split or structure the native Sparrow module around real concepts

You may keep a single file if necessary, but prefer splitting `rust/vrs_solver/src/optimizer/sparrow/` into focused modules such as:

```text
mod.rs
problem.rs
layout.rs
tracker.rs
sample_eval.rs
best_samples.rs
uniform_sampler.rs
coord_descent.rs
search.rs
lbf.rs
sep_evaluator.rs
worker.rs
separator.rs
explore.rs
solution.rs
```

The exact split is less important than the logic. But do not hide old shortcuts in one giant file.

### 3.2 Native LBFBuilder equivalent

Replace the row/grid constructive seed as the primary constructor.

Port/adapt upstream `LBFBuilder`:

- sort item types by `convex_hull_area * diameter` descending;
- expand by quantity;
- for each item, call native `search_placement` with native `LBFEvaluator`;
- place clear candidates first;
- for fixed sheets, search all eligible sheets;
- if no clear candidate exists, place the least-infeasible candidate honestly and let separation resolve it;
- do not pile everything into a row/grid seed.

### 3.3 Native CollisionTracker equivalent

Replace surrogate pair/container loss with real CDE/hazard-based quantification.

Port/adapt upstream tracker semantics:

- pair matrix or equivalent pair store;
- container collision store;
- `CTEntry { loss, weight }`;
- full rebuild from layout;
- register item move / recompute item;
- save snapshot;
- restore losses while keeping weights;
- get pair loss, container loss, item loss, weighted loss, total loss;
- update weights using current maximum loss, min/max increase ratio and decay/floor behavior.

Do not use `polygon_overlap_surrogate_loss` or `polygon_boundary_surrogate_loss` as the primary loss. If exact upstream quantification functions are not exposed by the `jagua-rs` crate, port the upstream quantification implementation from `.cache/sparrow/src/quantify` into this module.

### 3.4 Native search/evaluator equivalent

Port/adapt upstream search logic:

- `SampleEval` and `SampleEvaluator` traits/types;
- `BestSamples` with uniqueness threshold;
- `UniformBBoxSampler` for focused and whole-container samples;
- `search_placement` matching Sparrow Algorithm 6 / Figure 7;
- pre-refine coordinate descent over all best samples;
- final coordinate descent over the best sample;
- translation and rotation wiggle support where rotation policy allows continuous/all rotations;
- upper-bound pruning in evaluator;
- deterministic seeded RNG.

For fixed multisheet VRS, treat each sheet as a container candidate. The best sample must include `sheet_index` as part of the candidate state.

### 3.5 Native SeparationEvaluator and LBFEvaluator

Implement true evaluator parity:

- `SeparationEvaluator` evaluates candidate placement by CDE collision existence + quantified collision loss;
- pair/container weights come from `SparrowCollisionTracker`;
- clear candidates are ranked by deterministic secondary quality only after zero collision loss;
- `LBFEvaluator` prioritizes bottom-left/frontier style construction but still uses CDE truth.

Do not rank colliding candidates by AABB overlap, centroid proximity, or polygon vertex-count heuristics as primary loss.

### 3.6 Native worker / separator parity

Port/adapt upstream `SeparatorWorker`:

- worker loads master solution + tracker snapshot;
- collects all currently colliding items;
- shuffles them per worker RNG;
- for each still-colliding item, performs native `search_placement` with `SeparationEvaluator`;
- moves the item and registers tracker update;
- returns total moves/evals;
- no `max_targets=1` dense behavior.

Port/adapt `Separator::separate` Algorithm 9:

- strike loop;
- no-improvement loop;
- `move_items_multi`;
- min-loss solution/tracker snapshot;
- GLS update after iterations;
- rollback to min-loss solution while keeping weights;
- best feasible / least infeasible output.

`move_items_multi` Algorithm 10:

- all workers start from the same master state;
- each worker runs `move_items` independently;
- choose the worker with lowest weighted loss;
- load that worker state back into master.

Parallel workers with `rayon` are preferred if clean, but sequential workers are acceptable for this task if the semantics are identical and diagnostics report it honestly.

### 3.7 Exploration / disruption parity, compression excluded

Port/adapt upstream exploration phase, except strip-width shrink and compression:

- infeasible solution pool sorted by loss;
- biased random restore from better pool entries using distribution;
- disruption by swapping two large items based on convex-hull-area contribution cutoff;
- choose sufficiently different large items;
- after swap, move practically contained items from old large-item space using CDE/POI containment logic;
- restore/rebuild tracker correctly after disruption.

Fixed-sheet adaptation:

- no strip-width shrink;
- no compression;
- if a feasible layout is found, record it and stop or continue only if doing non-compression exploration improves feasibility robustness;
- do not fake strip-packing semantics.

## 4. Forbidden regressions

Reject the task if production `sparrow_cde` uses any of these as a core path:

```text
WorkingLayout
VrsCollisionTracker
SparrowSeparationKernel
search_position_for_target(&WorkingLayout, ...)
build_constructive_seed_layout(...)
PhaseOptimizer
MultiSheetManager
legacy fallback
LBF fallback outside native LBFBuilder concept
bbox/AABB positive collision truth
compression
crate::io::Placement as internal native layout state
```

`crate::io::Placement` is allowed only in `SparrowSolution::to_solver_projection` or equivalent output boundary.

## 5. Runtime acceptance

Create/update `scripts/smoke_sgh_q24r8_full_native_sparrow_core_parity_no_compression.py`.

It must fail on static shortcuts and run these checks:

### Static gates

- `optimizer/sparrow` contains native modules/concepts listed above.
- production code has no `WorkingLayout`, `VrsCollisionTracker`, `SparrowSeparationKernel`, `PhaseOptimizer`, `MultiSheetManager`.
- no `is_dense_reference_case` production branch.
- no `max_targets = 1` dense branch.
- no `others.truncate(24)` production path.
- no `final_validation_tracker_bounded` production final validation.
- no `polygon_overlap_surrogate_loss` / `polygon_boundary_surrogate_loss` as primary tracker loss.
- compression diagnostics remain zero / disabled.

### Runtime gates

Run through the existing solver CLI/API pattern used by earlier smoke scripts.

Required scenarios:

1. Medium native CDE smoke:
   - valid placement count: 12/12;
   - final pairs: 0;
   - boundary violations: 0;
   - old core used: false;
   - compression passes: 0.

2. LV8 12 types × 1:
   - valid placement count: 12/12;
   - final pairs: 0;
   - boundary violations: 0;
   - old core used: false;
   - compression passes: 0.

3. LV8 reference sheet-1 191:
   - real full search;
   - full final validation, not bounded;
   - runtime real;
   - search calls/samples/worker moves/CDE quantification scale beyond Q24R7-R1 tiny constants;
   - final raw loss < initial raw loss;
   - final pairs < initial pairs;
   - validated placements > 36;
   - if still partial, report exact unresolved blockers and partial reason.

The 191 case does not have to be fully solved in this task, but it must show real Sparrow-core progress. If it still worsens loss or only moves a handful of items, mark `REVISE`.

## 6. Required report

Write:

```text
codex/reports/egyedi_solver/sgh_q24r8_full_native_sparrow_core_parity_no_compression.md
```

Include:

```text
SGH-Q24R8_STATUS: PASS|REVISE
STATIC_CORE_PARITY_GATE: PASS|FAIL
RUNTIME_MEDIUM_CDE_GATE: PASS|FAIL
RUNTIME_LV8_12TYPES_X1_GATE: PASS|FAIL
RUNTIME_LV8_REFERENCE_SHEET1_191_PROGRESS_GATE: PASS|PARTIAL|FAIL
COMPRESSION_GATE: PASS|FAIL
```

Also include:

- upstream-to-local parity table;
- changed files;
- exact dense 191 metrics before/after compared to Q24R7-R1 baseline;
- proof no old VRS core is used;
- proof no dense bounded validation/shortcuts remain;
- proof compression remains disabled;
- open blockers.

## 7. Required commands

Run:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q24r8_full_native_sparrow_core_parity_no_compression.py
./scripts/check.sh
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q24r8_full_native_sparrow_core_parity_no_compression.md
```

If any command fails, the report must be `REVISE` with exact failure details.
