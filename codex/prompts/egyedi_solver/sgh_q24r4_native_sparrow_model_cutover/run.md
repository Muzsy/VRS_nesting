# SGH-Q24R4 — Native Sparrow model cutover

You are working in the VRS_nesting repository.

This is a **coding-first, model-cutover task**. The target is not another Sparrow-shaped wrapper around the old VRS solver. The target is a real native Sparrow solver model in production `sparrow_cde`.

## Controlling rule

Production `sparrow_cde` must stop using the old VRS solver-core truth model.

The old core model is:

```text
WorkingLayout
crate::io::Placement as internal placement
VrsCollisionTracker
adapter-style CDE calls around old state
WorkingLayout final commit as the solver state truth
```

After this task, production `sparrow_cde` must run on native Sparrow concepts:

```text
SparrowProblem / FixedSheetSparrowProblem
SPInstance / SparrowItemInstance
SparrowLayout
SparrowSolution
SparrowCollisionTracker
SparrowOptimizer / Separator / Worker / Explore / Search
```

The only allowed VRS compatibility is at the I/O boundary:

```text
SolverInput + stocks + parts + rotation policy
  -> native SparrowProblem
  -> native Sparrow optimizer lifecycle
  -> native SparrowSolution
  -> SolverOutput-compatible projection
```

Do not preserve an internal VRS adapter model. Do not create a new wrapper that hides the old model. Do not keep a production escape hatch that lets future tasks build on the old core.

## Compression is out of scope

Compression remains deliberately excluded from the PASS criteria. Do not spend the task on `compress.rs` or fixed-sheet compression. Default production `sparrow_cde` must still pass the medium CDE gate without compression.

## Mandatory reference reading

Before coding, read the local Sparrow clone:

```text
.cache/sparrow/src/optimizer/mod.rs
.cache/sparrow/src/optimizer/separator.rs
.cache/sparrow/src/optimizer/worker.rs
.cache/sparrow/src/optimizer/explore.rs
.cache/sparrow/src/sample/search.rs
.cache/sparrow/src/quantify/tracker.rs
```

Skim only to understand what is intentionally out of scope:

```text
.cache/sparrow/src/optimizer/compress.rs
```

If `.cache/sparrow` is missing, run:

```bash
./scripts/ensure_sparrow.sh
```

Then read current VRS files:

```text
codex/reports/egyedi_solver/sgh_q24r3_native_sparrow_lifecycle_parity_no_compression.md
docs/egyedi_solver/sgh_q24r3_sparrow_reference_map.md
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/optimizer/sparrow.rs
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/search_position.rs
rust/vrs_solver/src/optimizer/collision_severity.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/io.rs
scripts/smoke_sgh_q24r3_native_sparrow_lifecycle_parity_no_compression.py
```

## Audited starting point

Q24R3 is accepted as a milestone because:

- lifecycle functions exist;
- constructive seed exists;
- medium CDE 12/12 passes without compression;
- CDE is forced on production `sparrow_cde`;
- legacy fallback is not used by the Q24R3 smoke.

But Q24R3 is still not the full jagua_rs/Sparrow model because the production solver still starts from and returns through `WorkingLayout`, uses `crate::io::Placement` as its internal layout object, and uses `VrsCollisionTracker` as the tracker-like object.

That is the exact problem to solve in Q24R4.

## Required work

### 1. Write a model cutover map first

Create:

```text
docs/egyedi_solver/sgh_q24r4_native_sparrow_model_cutover_map.md
```

It must contain a table with at least these rows:

```text
Q24R3 / old core concept        Q24R4 native replacement
WorkingLayout                   SparrowLayout / SparrowSolution state
crate::io::Placement internal   Native placement record with instance index/key
VrsCollisionTracker             SparrowCollisionTracker
SparrowState wrapping layout    Native state owning layout + tracker + weights
build_constructive_seed_layout  Native initial Solution builder
run_sparrow_pipeline seed step  SolverInput -> SparrowProblem conversion
search_position_for_target      Native search over SparrowLayout + tracker
final WorkingLayout commit      Native final validation + output projection
```

The map must explicitly say which old code becomes legacy-only and which functions are removed from production `sparrow_cde`.

### 2. Convert `optimizer/sparrow` into a native module tree

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

If Rust module resolution conflicts with `rust/vrs_solver/src/optimizer/sparrow.rs`, remove/rename the old file and expose the new module directory from `optimizer/mod.rs`.

Do not create empty modules. Every module must contain real production implementation or real shared types used by production code.

### 3. Define native problem and instance types

Implement native types equivalent to:

```rust
SparrowProblem
SPInstance
SparrowItemGeometry
SparrowContainer / FixedSheetContainer
SparrowRotationDomain
```

Hard requirements:

- expanded instances must have stable index and stable external `instance_id` mapping;
- part geometry and rotation metadata must be native fields, not lookups through `crate::io::Placement`;
- stock/sheet/container data must be native fields;
- pre-unplaced / never-fits cases must be represented at the boundary without silently dropping them;
- allowed rotations, continuous rotation context, deterministic seed, and profile config must be part of the native problem/config boundary.

### 4. Define native layout and solution types

Implement native types equivalent to:

```rust
SparrowPlacement
SparrowLayout
SparrowSolution
SparrowIncumbent
```

Hard requirements:

- `SparrowPlacement` must not be `crate::io::Placement`.
- Layout must index placements by `SPInstance` index/key.
- Layout update must support remove/place/update semantics needed by the tracker.
- Snapshot/restore must preserve layout and tracker coherence.
- Feasible and infeasible incumbents must be native solutions.
- Projection to `crate::io::Placement` is allowed only at the output boundary.

### 5. Replace `VrsCollisionTracker` with native `SparrowCollisionTracker`

Implement a real native tracker. It may reuse low-level CDE query functions, but it must not be a wrapper around `VrsCollisionTracker`.

Hard requirements:

- owns pair collision records;
- owns boundary/container violation records;
- owns GLS weights;
- computes raw loss, weighted loss, per-item weighted loss;
- provides colliding/offending item indices;
- supports update-after-move for one item;
- supports full rebuild for debug/validation;
- supports snapshot/restore with GLS semantics equivalent to Sparrow;
- exposes final full CDE validation status.

Low-level helpers allowed:

```text
cde_adapter
cde_session
collision_severity CDE primitives
geometry conversion helpers
```

Forbidden:

```text
VrsCollisionTracker as field
VrsCollisionTracker as delegated engine
WorkingLayout as tracker input state
bbox loss as decisive CDE truth
```

### 6. Cut over `run_sparrow_pipeline`

Modify `rust/vrs_solver/src/adapter.rs` so the production `sparrow_cde` branch no longer builds `WorkingLayout` before entering the Sparrow optimizer.

Target shape:

```rust
let problem = SparrowProblem::from_solver_input(input, sheets, rotation_context, pre_unplaced)?;
let optimizer = SparrowOptimizer::new(config);
let result = optimizer.solve(problem);
let projected = result.to_solver_output_projection(...)?;
```

The exact names can differ, but the dataflow must be this shape.

Forbidden in production `sparrow_cde` pipeline:

```rust
WorkingLayout::new(...)
PhaseOptimizer
MultiSheetManager
build_initial_layout_with_rotation_context
legacy row/cursor fallback
```

`WorkingLayout` may continue to exist temporarily for legacy pipelines/tests, but it must not be reachable from the production `sparrow_cde` solve path.

### 7. Port lifecycle functions onto native state

Move Q24R3 behavior onto the native types:

- constructive initial solution builder;
- `exploration_phase`;
- `separate`;
- `move_items_multi`;
- worker `move_items` over offending/colliding items;
- search placement;
- restore/disrupt/separate;
- best feasible/infeasible tracking;
- final validation.

Do not simply pass native wrappers into old functions that unwrap back into `WorkingLayout`.

### 8. Preserve Q24R3 runtime behavior

After the model cutover, the existing Q24R3 medium CDE behavior must still pass:

```text
medium fixture
production sparrow_cde
CDE backend used even if bbox requested
12/12 placed
0 final collision pairs
0 final boundary violations
compression passes 0 or explicit compression disabled
no bbox fallback
no LBF/legacy fallback
```

If this regresses, fix the native implementation. Do not restore the old VRS model to recover the test.

### 9. Add a static anti-hybrid smoke

Create:

```text
scripts/smoke_sgh_q24r4_native_sparrow_model_cutover.py
```

The script must perform static checks and the medium runtime gate.

Static checks must fail if production native Sparrow modules import/use the old core:

```text
WorkingLayout
VrsCollisionTracker
PhaseOptimizer
MultiSheetManager
build_initial_layout_with_rotation_context
```

The script must also check that native files exist and contain these concepts or accepted equivalents:

```text
SparrowProblem
SPInstance
SparrowLayout
SparrowSolution
SparrowCollisionTracker
SparrowOptimizer
```

Allow `crate::io::Placement` only in explicit projection/boundary files/functions. It must not be the internal native layout placement type.

### 10. Write report and evidence

Create:

```text
codex/reports/egyedi_solver/sgh_q24r4_native_sparrow_model_cutover.md
codex/reports/egyedi_solver/sgh_q24r4_native_sparrow_model_cutover.verify.log
```

Report must include:

- list of `.cache/sparrow` files read;
- model cutover map path;
- exact files changed;
- old core concepts removed from production path;
- native types introduced;
- proof that `run_sparrow_pipeline` no longer creates `WorkingLayout` for `sparrow_cde`;
- proof that native tracker replaced `VrsCollisionTracker` in production path;
- Q24R3 medium CDE result after cutover;
- build/test/smoke commands and outputs;
- explicit statement that compression stayed disabled/out of scope.

## Required commands

Run at least:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q24r4_native_sparrow_model_cutover.py
./scripts/check.sh
```

If a command fails because of pre-existing unrelated issues, document it with exact output and still complete the Rust implementation work.

## PASS definition

Q24R4 is PASS only if:

```text
production sparrow_cde has native Sparrow Problem/Layout/Solution/Tracker state
production sparrow_cde no longer uses WorkingLayout/VrsCollisionTracker internally
production sparrow_cde still passes the Q24R3 medium CDE gate without compression
static anti-hybrid smoke passes
build/tests/check evidence is written
```

## REJECT definition

Reject if:

- the old VRS core remains the real production state;
- new native types are merely aliases/wrappers over old core types;
- production `sparrow_cde` still constructs `WorkingLayout` before solve;
- `VrsCollisionTracker` remains the production tracker;
- `crate::io::Placement` remains the internal layout placement type;
- task mainly changes docs/reports/scripts;
- task mainly changes compression;
- task weakens the medium gate;
- task re-enables legacy fallback.
