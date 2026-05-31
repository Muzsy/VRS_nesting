# SGH-Q24R3 — Native Sparrow lifecycle parity without compression

## Purpose

Bring the VRS production `sparrow_cde` solver to actual jagua_rs/Sparrow lifecycle parity, **excluding compression**.

Q24R2 was a good coding-first step: it moved the implementation into `rust/vrs_solver/src/optimizer/sparrow.rs` and introduced the right high-level functions:

```text
run
exploration_phase
separate
move_items_multi
worker_move_items
compression_phase
finalize
```

But Q24R2 is still not the full Sparrow implementation. The next task must close the decisive gaps in the production `sparrow_cde` path.

## Controlling rule

> Implement the current jagua_rs/Sparrow exploration/separation/search/tracker lifecycle in VRS fixed-sheet form. Do not spend this task on compression.

Compression is intentionally excluded. In strip packing it is generally useful because the strip length/width is the direct objective. In VRS fixed-sheet multisheet nesting it should only come back later, mainly for the last partially used sheet. For now, it must not distract from the real solver lifecycle.

## Current audited state after Q24R2

### What is already acceptable

- Q24R2 genuinely changed `rust/vrs_solver/src/optimizer/sparrow.rs`.
- The old single-loop/grid-restart style was replaced with a Sparrow-like skeleton.
- The following functions exist in the current code:

```text
SparrowSeparationKernel::run
SparrowSeparationKernel::exploration_phase
SparrowSeparationKernel::separate
SparrowSeparationKernel::move_items_multi
SparrowSeparationKernel::worker_move_items
SparrowSeparationKernel::compression_phase
SparrowSeparationKernel::finalize
```

- The production `sparrow_cde` route forces CDE in `rust/vrs_solver/src/adapter.rs`.
- No legacy/LBF fallback is intended in the `sparrow_cde` path.

### What is still not acceptable

1. **CDE medium convergence is not a hard PASS yet.**  
   Q24R2 explicitly allowed medium CDE 12 items to return without convergence. This cannot remain true if we claim full Sparrow lifecycle parity.

2. **The initial solution is still primitive.**  
   `build_sparrow_seed_layout` places every fittable instance at the first sheet / first rotation / origin. The original Sparrow uses a constructive initial solution (`LBFBuilder`) before exploration. VRS needs an equivalent fixed-sheet constructive seed or warm-start path. This does not mean BLF becomes the solver; it is only an initial solution builder.

3. **The VRS state model is still adapter-heavy.**  
   The original Sparrow works with `SPInstance`, `SPProblem`, `SPSolution`, stable placement keys, layout restore/save, and a collision tracker directly attached to the layout/CDE lifecycle. VRS still uses `WorkingLayout`, `Placement`, `Part`, `SheetShape`, `VrsCollisionTracker`, and `CdeAdapter`. That may remain as an adaptation, but it must become a complete fixed-sheet Sparrow problem/layout lifecycle, not a loose approximation.

4. **The tracker/loss model is not yet native CDE quantification.**  
   For CDE production, decisive separation loss must come from CDE collision/container quantification. Bbox or smooth bbox loss may exist only as broad-phase/diagnostic/support, not as the decisive CDE separation loss.

5. **Search depth is still toy-sized in production config.**  
   The current adapter config uses small budgets such as `global_grid_n: 2`, `focused_sample_count: 2`, `coord_descent_max_steps: 3`, `coord_descent_top_k: 2`. This proves activity, but it is not Sparrow-like search quality. Restore meaningful search depth using active-set/session support to avoid timeout.

6. **Worker model is structurally right but still simplified.**  
   It uses deterministic sequential workers and no persistent worker state comparable to Sparrow's `SeparatorWorker`. Sequential is acceptable short-term, but the worker/master/load/restore logic must be semantically equivalent.

7. **Exploration phase is skeleton-level.**  
   Pool, biased restore and disruption exist, but the fixed-sheet adaptation is still weak. The task must make it operational under CDE, not just structurally present.

8. **Compression exists but must not be the focus now.**  
   The current Q24R2 compression should be gated out of the default production `sparrow_cde` lifecycle for this task unless needed for compatibility diagnostics. Do not improve compression now.

## Mandatory reference reading

Read the local Sparrow clone first. It is gitignored but present locally:

```text
.cache/sparrow/src/optimizer/mod.rs
.cache/sparrow/src/optimizer/separator.rs
.cache/sparrow/src/optimizer/worker.rs
.cache/sparrow/src/optimizer/explore.rs
.cache/sparrow/src/sample/search.rs
.cache/sparrow/src/quantify/tracker.rs
```

Compression reference may be skimmed for context but must not drive this task:

```text
.cache/sparrow/src/optimizer/compress.rs
```

If `.cache/sparrow` is absent, run:

```bash
./scripts/ensure_sparrow.sh
```

Then read the current VRS implementation:

```text
codex/reports/egyedi_solver/sgh_q24r2_native_sparrow_core_port.md
rust/vrs_solver/src/optimizer/sparrow.rs
rust/vrs_solver/src/optimizer/search_position.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/collision_severity.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/io.rs
```

## Required implementation

### 1. Produce a precise Sparrow-to-VRS code map before changing code

Create or update:

```text
docs/egyedi_solver/sgh_q24r3_sparrow_reference_map.md
```

It must map current `.cache/sparrow` functions to VRS production equivalents:

```text
Sparrow optimize               -> VRS optimizer orchestration
LBFBuilder initial solution    -> VRS fixed-sheet constructive seed/warm start
exploration_phase              -> VRS exploration phase
Separator::separate            -> VRS separator
Separator::move_items_multi    -> VRS worker-master loop
SeparatorWorker::move_items    -> VRS worker item loop
search::search_placement       -> VRS search_position/search placement
CollisionTracker               -> VRS CDE-backed tracker/loss
SPSolution save/restore        -> VRS layout/tracker snapshot/restore
```

This map must be grounded in file paths and function names. It is not a replacement for coding; it is the guardrail that prevents drift.

### 2. Introduce or complete a fixed-sheet native Sparrow state/problem layer

Implement one of these two acceptable approaches:

#### Preferred: explicit fixed-sheet Sparrow module tree

```text
rust/vrs_solver/src/optimizer/sparrow/mod.rs
rust/vrs_solver/src/optimizer/sparrow/problem.rs
rust/vrs_solver/src/optimizer/sparrow/state.rs
rust/vrs_solver/src/optimizer/sparrow/tracker.rs
rust/vrs_solver/src/optimizer/sparrow/separator.rs
rust/vrs_solver/src/optimizer/sparrow/worker.rs
rust/vrs_solver/src/optimizer/sparrow/explore.rs
rust/vrs_solver/src/optimizer/sparrow/search.rs
```

#### Acceptable: keep `sparrow.rs`, but make the abstractions explicit

If the file is not split, it must still contain real abstractions equivalent to:

```rust
FixedSheetSparrowProblem
FixedSheetSparrowLayout
FixedSheetPlacementKey
FixedSheetSparrowSolution
FixedSheetSparrowTracker
FixedSheetSeparator
FixedSheetSeparatorWorker
```

Hard requirements:

- stable placement keys or a rigorously documented equivalent;
- save/restore of layout and tracker as a single consistent state;
- move/remove/place or equivalent update lifecycle;
- worker load from master snapshot;
- tracker restore preserving GLS weights where Sparrow preserves memory;
- no accidental mismatch between layout, graph, tracker and CDE sessions.

### 3. Replace primitive initial solution with a Sparrow-compatible fixed-sheet seed

The current all-at-origin seed is not enough.

Implement a constructive initial solution builder equivalent in role to Sparrow's `LBFBuilder`, adapted to fixed sheets.

Hard rules:

- It is only a seed builder, not a final solver/fallback.
- It must place all fittable instances into a deterministic initial layout if possible, even if infeasible overlaps remain.
- It must support warm-start when a valid initial layout is provided or later added.
- It must distribute instances across allowed sheets/regions better than “all at origin”.
- It must respect rotation policy.
- It must preserve every instance; no silent dropping.

Acceptable fixed-sheet seed strategies:

- deterministic left-bottom fill over sheets as a seed;
- area/size sorted placement into sheets with overlap allowed only as last resort;
- coarse grid/spread assignment per sheet;
- hybrid: LBF-like seed, then controlled infeasible overlap if needed.

Forbidden:

- BLF/LBF as final success fallback;
- row/cursor legacy path as production `sparrow_cde` solver;
- dropping hard cases to make tests pass.

### 4. Make CDE-backed tracker/loss quantification real

Implement decisive CDE loss based on collision/container quantification.

Hard requirements:

- pair collisions must be obtained from CDE-backed geometry checks/collector or equivalent CDE-backed query path;
- pair loss must be a shape/CDE separation/penetration/severity measure, not bbox area as the primary CDE loss;
- sheet/container violations must be quantified from actual placement vs fixed-sheet container, not only bbox surrogate where exact CDE container information is available;
- GLS pair and boundary weights must use these real losses;
- `colliding_indices`, `weighted_loss_for_item`, `total_loss`, `total_weighted_loss`, `snapshot_loss`, `restore_but_keep_weights`, and item update must all use the same CDE-backed truth;
- final commit validation remains full CDE validation over all placements.

If jagua-rs exposes a usable collision quantification routine locally, adapt it directly. If the exact function is not reusable, implement the closest VRS equivalent and document the delta in the Q24R3 report.

### 5. Restore Sparrow-like search placement depth under CDE

The production CDE search must no longer rely on toy budgets.

Required search components:

- container/sheet-wide sampling;
- focused/local sampling around the current placement;
- best-samples retention and deterministic dedupe;
- pre-refinement coordinate descent over top candidates;
- final finer coordinate descent on the best candidate;
- continuous rotation refinement when the rotation policy allows it;
- deterministic worker-specific RNG;
- evaluator returns CDE-backed weighted separation loss.

Do not solve timeout by disabling search depth. Instead implement support needed to make CDE search affordable.

### 6. Add active-set/session support only as a servant of lifecycle parity

CDE is expensive. Add enough active-set/session support to allow real search depth.

Acceptable support:

- per-target hazard active set;
- spatial/proximity prefilter before expensive CDE query;
- sheet-local hazard sets;
- candidate session reuse scoped to worker/search call;
- shape/transform cache reuse;
- final full validation over all hazards before returning success.

Forbidden:

- active-set as a replacement for full final CDE validation;
- CDE micro-optimization without fixing search/tracker/lifecycle behavior;
- treating bbox broad-phase as final truth.

### 7. Make exploration operational under CDE

Keep the Q24R2 structure but make it strong enough to solve the medium CDE hard gate.

Required behavior:

- bounded infeasible pool sorted by loss;
- biased restore toward better infeasible states;
- at least two real disruption strategies, including one large-item strategy and one sheet/cluster redistribution strategy;
- repeated restore/disrupt/separate attempts under budget;
- best feasible and best infeasible state tracking;
- no single grid-spread restart as the hidden core algorithm.

Fixed-sheet disruption examples:

- swap transforms of two large offending items;
- move a large offending item to another sheet region;
- move a dense-cluster item away from its nearest collision cluster;
- redistribute a high-loss item to a lower-density sheet.

### 8. Disable or gate compression for this task

Compression is not the goal.

For this task, production `sparrow_cde` should use:

```text
initial solution -> exploration/separation/search -> final full CDE validation
```

Compression may remain as dormant/optional code behind explicit config, but:

- it must not consume default `sparrow_cde` runtime;
- it must not be required for any PASS gate;
- it must not be the main Rust diff;
- it must not hide search/separation weakness;
- if diagnostics expose compression, default production Q24R3 smoke should show compression disabled or zero passes.

Add a TODO/comment only if useful:

```text
Future: fixed-sheet multisheet compression only after full lifecycle parity, primarily on the last partially used sheet.
```

### 9. Restore CDE medium convergence as a hard gate

The Q24R2 task deferred this. Q24R3 must not.

Hard gate:

```text
medium_10_to_20_items
pipeline: sparrow_cde
backend: forced CDE
items: 12/12
status: ok
sparrow_converged: true
final collision pairs: 0
final boundary violations: 0
no bbox fallback
no LBF/legacy fallback
runtime within configured smoke timeout
compression not required / disabled by default
```

This is a coding gate, not a benchmark campaign.

### 10. Do not make full LV8 the PASS gate yet

Full LV8 remains the later industrial target:

```text
276 / 276 instances
2 × 1500 × 3000 sheets
CDE-valid
zero overlap
zero boundary violation
```

Q24R3 may include a small LV8 subset smoke if useful, but full LV8 is not required for this task. The required hard gate is medium CDE convergence plus structural Sparrow parity excluding compression.

## Required verification

After coding, run at minimum:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q24r3_native_sparrow_lifecycle_parity_no_compression.py
./scripts/check.sh
```

If a command cannot run, report the exact blocker and do not claim PASS for that gate.

## Required report

Create:

```text
codex/reports/egyedi_solver/sgh_q24r3_native_sparrow_lifecycle_parity_no_compression.md
```

The report must include:

- PASS/REVISE verdict;
- exact Rust files changed;
- Sparrow reference files read from `.cache/sparrow`;
- function-by-function mapping from Sparrow to VRS;
- what was changed in state/problem/tracker/search/exploration;
- explicit statement that compression is disabled/gated and not the claimed deliverable;
- test command outputs;
- medium CDE hard-gate result;
- remaining limitations.

## PASS criteria

PASS only if all are true:

- production `sparrow_cde` still forces CDE and no legacy fallback;
- fixed-sheet Sparrow lifecycle maps to current `.cache/sparrow` optimizer functions excluding compression;
- initial solution builder is no longer all-at-origin only;
- worker-master and worker move-items behavior remain active and process all colliding items;
- CDE tracker/loss is decisive and not bbox-surrogate primary;
- search depth is meaningful and CDE-affordable through active-set/session support;
- exploration can solve the medium CDE hard gate;
- default production `sparrow_cde` does not rely on compression;
- tests and smoke pass.

## REVISE triggers

Automatic REVISE if any of these happen:

- main diff is docs/reports/scripts only;
- main diff is compression;
- main diff is bbox removal rhetoric;
- medium CDE 12/12 remains deferred;
- search depth is reduced to pass runtime;
- CDE loss remains bbox/surrogate primary;
- final success can be emitted without full CDE validation;
- instances are dropped silently;
- legacy row/cursor/BLF final fallback is used in `sparrow_cde`;
- `.cache/sparrow` was not read and no honest blocker was reported.
