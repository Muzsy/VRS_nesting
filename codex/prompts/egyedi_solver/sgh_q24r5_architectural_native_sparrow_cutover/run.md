# SGH-Q24R5 — Architectural native Sparrow cutover

You are working in the VRS_nesting repository.

This is a **coding-first architectural cut**. The previous Q24R4 run reported `REVISE` because it preserved the Q24R3 baseline and added only an enabling primitive. That was honest, but it did not complete the cutover. Q24R5 must now implement the cut.

Do **not** return another map-only REVISE. Do **not** spend the session on benchmarks, docs, bbox rhetoric, or compression. The task is to move the production solver core to a native Sparrow model.

## Controlling rule

Production `sparrow_cde` must stop running on:

```text
WorkingLayout
crate::io::Placement as internal layout item
VrsCollisionTracker
SparrowSeparationKernel over WorkingLayout
search_position_for_target(&WorkingLayout, ...)
WorkingLayout final commit
```

Production `sparrow_cde` must instead run on:

```text
SparrowProblem
SPInstance
SparrowPlacement
SparrowLayout
SparrowSolution / SparrowSolveResult
SparrowCollisionTracker
SparrowOptimizer
native separate / worker / search / exploration lifecycle
native final CDE validation
```

The only allowed compatibility boundary is:

```text
SolverInput / stocks / parts / rotation policy
  -> SparrowProblem
  -> SparrowOptimizer::solve(...)
  -> SparrowSolution
  -> SolverOutput projection
```

This is not “keeping a VRS adapter.” It is only API input/output conversion. The solver core must not retain the old VRS model.

## Compression is out of scope

Compression remains intentionally excluded. Do not harden it. Do not use it to pass acceptance. Default production `sparrow_cde` must still have compression disabled/zero-pass.

## Mandatory reference reading

Read before coding:

```text
codex/reports/egyedi_solver/sgh_q24r4_native_sparrow_model_cutover.md
docs/egyedi_solver/sgh_q24r4_native_sparrow_model_cutover_map.md
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/optimizer/sparrow.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/search_position.rs
rust/vrs_solver/src/io.rs
```

Read the local Sparrow clone:

```text
.cache/sparrow/src/optimizer/mod.rs
.cache/sparrow/src/optimizer/separator.rs
.cache/sparrow/src/optimizer/worker.rs
.cache/sparrow/src/optimizer/explore.rs
.cache/sparrow/src/sample/search.rs
.cache/sparrow/src/quantify/tracker.rs
```

Skim only, do not port now:

```text
.cache/sparrow/src/optimizer/compress.rs
```

If `.cache/sparrow` is missing:

```bash
./scripts/ensure_sparrow.sh
```

## Starting point you must address

Q24R4 report says:

```text
SGH-Q24R4_STATUS: REVISE
STATIC_CUTOVER_GATE: FAIL
RUNTIME_MEDIUM_CDE_GATE: PASS
```

The exact current anti-pattern is:

```rust
build_constructive_seed_layout(...)
let seed_layout = WorkingLayout::new(...)
let kernel = SparrowSeparationKernel::new(...)
let sparrow_result = kernel.run(seed_layout, ...)
```

That route must be removed from production `sparrow_cde`.

Q24R4 did add one useful primitive:

```rust
cde_adapter::prepare_shape_native(part, x, y, rotation_deg)
```

Use it for the native tracker/search. Do not fall back to `prepare_shape_from_placement` in native core.

## Required implementation

### 1. Replace/split the production Sparrow module

Preferred structure:

```text
rust/vrs_solver/src/optimizer/sparrow/mod.rs
rust/vrs_solver/src/optimizer/sparrow/problem.rs
rust/vrs_solver/src/optimizer/sparrow/instance.rs
rust/vrs_solver/src/optimizer/sparrow/layout.rs
rust/vrs_solver/src/optimizer/sparrow/solution.rs
rust/vrs_solver/src/optimizer/sparrow/tracker.rs
rust/vrs_solver/src/optimizer/sparrow/state.rs
rust/vrs_solver/src/optimizer/sparrow/optimizer.rs
rust/vrs_solver/src/optimizer/sparrow/separator.rs
rust/vrs_solver/src/optimizer/sparrow/worker.rs
rust/vrs_solver/src/optimizer/sparrow/explore.rs
rust/vrs_solver/src/optimizer/sparrow/search.rs
rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs
rust/vrs_solver/src/optimizer/sparrow/rng.rs
```

If `rust/vrs_solver/src/optimizer/sparrow.rs` conflicts with the directory module, move the old file out of the production module path. If you must keep it temporarily, quarantine it as legacy-only under a clearly named module that production `sparrow_cde` cannot import. Prefer deleting/replacing rather than preserving.

Do not create empty modules. Every new module must be used by production or by real tests for production types.

### 2. Define native problem and instance model

Implement production-native types equivalent to:

```rust
pub struct SparrowProblem { ... }
pub struct SPInstance { ... }
pub struct SparrowContainer { ... }
pub struct SparrowRotationDomain { ... }
pub struct SparrowConfig { ... }
```

Hard requirements:

- `SparrowProblem::from_solver_input(...)` or equivalent converts input once.
- Expanded instances have stable native index and stable external `instance_id`.
- Part geometry, dimensions, allowed rotations, and part index are native fields/references.
- Sheet/container info is native.
- Seed/time budget/rotation context/backend config are native config fields.
- `pre_unplaced` / never-fits cases are retained and projected back; no silent drops.

### 3. Define native layout and solution model

Implement:

```rust
pub struct SparrowPlacement { ... }
pub struct SparrowLayout { ... }
pub struct SparrowSolution { ... }
pub struct SparrowSolveResult { ... }
```

Hard requirements:

- `SparrowPlacement` is not `crate::io::Placement` and does not store one internally.
- Layout is keyed by native `SPInstance` index/key.
- Layout supports place/remove/update, same-sheet iteration, snapshot/restore.
- `SparrowSolution` can project to `Vec<crate::io::Placement>` only at the output boundary.
- No `WorkingLayout` inside native layout/solution/state.

### 4. Implement native `SparrowCollisionTracker`

This is the most important part. It must not delegate to `VrsCollisionTracker`.

Required tracker behavior:

- owns pair collision records;
- owns boundary/container violation records;
- owns GLS weights;
- computes raw loss, weighted loss, per-item weighted loss;
- exposes colliding/offending item indices;
- supports full rebuild;
- supports update-after-move for one item;
- supports snapshot/restore while preserving/handling GLS semantics like Sparrow;
- exposes final full CDE validation status.

Allowed low-level primitives:

```text
cde_adapter::prepare_shape_native
cde_adapter::prepare_shape_from_sheet
CdeAdapter::query_pair
CdeAdapter::query_boundary
CdeCandidateSession::build/query, or a native equivalent built from native prepared shapes
cde_observability counters
```

Forbidden:

```text
VrsCollisionTracker as field
VrsCollisionTracker as delegated engine
WorkingLayout as tracker input state
crate::io::Placement as tracker placement state
bbox-area as decisive positive collision truth
```

AABB broad-phase may remain only as a safe no-collision pruning optimization before CDE; it must never produce positive collision truth.

### 5. Implement native search/separation/exploration vertical slice

Port the Q24R3 behavior onto native state, not by wrapping old functions:

- native constructive initial solution builder;
- native `separate` over `SparrowLayout + SparrowCollisionTracker`;
- native `move_items_multi` worker loop;
- native worker snapshots and load-back;
- native candidate search over `SparrowPlacement` candidates;
- CDE-backed candidate evaluation;
- GLS weight update;
- best feasible/infeasible tracking;
- exploration pool / restore / disruption on native `SparrowSolution` / state;
- final validation.

Do not call:

```text
search_position_for_target(&WorkingLayout, ...)
SparrowSeparationKernel::run(WorkingLayout, ...)
VrsCollisionTracker::build_with_model(...)
```

### 6. Cut over `run_sparrow_pipeline`

Modify `rust/vrs_solver/src/adapter.rs` so production `sparrow_cde` dataflow is this shape:

```rust
let problem = SparrowProblem::from_solver_input(input, sheets, rotation_context, pre_unplaced, backend_kind)?;
let optimizer = SparrowOptimizer::new(SparrowConfig::from_solver_input(...));
let result = optimizer.solve(problem);
let (placements, unplaced) = result.solution.to_solver_projection(...)?;
```

The exact names can differ. The shape cannot.

Forbidden inside `run_sparrow_pipeline`:

```rust
WorkingLayout::new(...)
SparrowSeparationKernel
build_constructive_seed_layout(...)
PhaseOptimizer
MultiSheetManager
build_initial_layout_with_rotation_context(...)
```

### 7. Add native-model diagnostics

Extend diagnostics with explicit proof fields, for example:

```rust
sparrow_native_model_active: Option<bool>
sparrow_native_tracker_active: Option<bool>
sparrow_old_core_used: Option<bool>
sparrow_native_problem_instances: Option<usize>
sparrow_native_tracker_full_rebuilds: Option<usize>
sparrow_native_tracker_incremental_updates: Option<usize>
```

The names may differ, but the runtime output must prove that production `sparrow_cde` used the native model and did not use the old core.

### 8. Keep Q24R3 medium CDE behavior passing

After cutover, the medium production gate must pass without compression:

```text
optimizer_pipeline = sparrow_cde
collision_backend requested = bbox, but production forces cde_adapter
12/12 placed
sparrow_converged = true
final collision pairs = 0
final boundary violations = 0
backend_used = cde_adapter
bbox_fallback_queries = 0
lbf_fallback = 0
compression disabled or compression passes = 0
native_model_active = true
native_tracker_active = true
old_core_used = false
```

If it regresses, fix the native implementation. Do not restore the old VRS model to recover the test.

### 9. Add Q24R5 smoke

Create:

```text
scripts/smoke_sgh_q24r5_architectural_native_sparrow_cutover.py
```

It must combine static and runtime gates.

Static gate must fail if production `optimizer/sparrow` source contains these old-core tokens outside comments/tests:

```text
WorkingLayout
VrsCollisionTracker
SparrowSeparationKernel
search_position_for_target
build_constructive_seed_layout
PhaseOptimizer
MultiSheetManager
build_initial_layout_with_rotation_context
```

It must also fail if `run_sparrow_pipeline` contains:

```text
WorkingLayout::new
SparrowSeparationKernel
build_constructive_seed_layout
PhaseOptimizer
MultiSheetManager
build_initial_layout_with_rotation_context
```

Runtime gate must run the medium CDE fixture and check the native diagnostics described above.

### 10. Report

Create:

```text
codex/reports/egyedi_solver/sgh_q24r5_architectural_native_sparrow_cutover.md
codex/reports/egyedi_solver/sgh_q24r5_architectural_native_sparrow_cutover.verify.log
```

Report must include:

- `SGH-Q24R5_STATUS: PASS` or `REVISE`, with no fake pass;
- exact `.cache/sparrow` files read;
- exact files changed;
- old-core files/functions removed from production path;
- native types introduced;
- proof that `run_sparrow_pipeline` no longer creates `WorkingLayout`;
- proof that `VrsCollisionTracker` is not used by production `sparrow_cde`;
- static smoke output;
- runtime medium CDE output;
- build/test/check outputs;
- explicit statement that compression stayed disabled/out of scope.

A report-only REVISE is not acceptable unless the codebase genuinely cannot compile after a serious implementation attempt. The main work must be Rust implementation.

## Required commands

Run at least:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q24r5_architectural_native_sparrow_cutover.py
./scripts/check.sh
```

If `./scripts/check.sh` fails due to unrelated existing issues, document exact output, but do not weaken the Q24R5 static/runtime gates.

## PASS definition

Q24R5 is PASS only if all are true:

```text
production sparrow_cde runs on native SparrowProblem/Layout/Solution/Tracker/Optimizer
run_sparrow_pipeline does not construct WorkingLayout
production optimizer/sparrow does not use VrsCollisionTracker or WorkingLayout
SparrowPlacement is native and not crate::io::Placement
native tracker owns loss/GLS/pair/boundary state
CDE remains decisive truth
Q24R3 medium CDE gate still passes without compression
static anti-hybrid smoke passes
build/test/check evidence exists
```

## REJECT definition

Reject if any is true:

- old VRS core remains the real production state;
- new native types wrap/alias the old core;
- production `sparrow_cde` still creates `WorkingLayout`;
- `VrsCollisionTracker` remains the production tracker;
- `crate::io::Placement` remains the internal layout placement type;
- old `SparrowSeparationKernel` remains the production solve engine;
- task mainly changes docs/reports/scripts;
- compression is used to pass acceptance;
- legacy/LBF fallback remains reachable from production `sparrow_cde`;
- runtime gate is weakened.
