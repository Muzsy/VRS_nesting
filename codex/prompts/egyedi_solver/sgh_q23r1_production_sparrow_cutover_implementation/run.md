# Runner — SGH-Q23R1 production Sparrow cutover implementation

You are working in the `VRS_nesting` repository.

This is an **implementation task**, not an audit task.

The goal is to complete the solver transition to a real jagua_rs/Sparrow-style production solver for fixed-sheet nesting. Do not deliver another report that only explains what remains. The implementation must replace the production solve path with `sparrow_cde` behavior and quarantine the old solvers behind explicit opt-in/debug settings.

## Non-negotiable target

Implement a production solver path whose core algorithmic behavior follows the local `.cache/sparrow` reference, adapted to fixed rectangular sheet nesting:

```text
infeasible-state feasibility solving
backend-confirmed collision graph
GLS / pair-weight search memory
search_position relocation and refinement
coordinate descent / local transform refinement
separation lifecycle
multi-target / multi-worker-style move pass, adapted to VRS
exploration and compression lifecycle, adapted to fixed sheet
CDE/Jagua geometry as source of truth
solve-scoped CDE/session/cache and incremental query reduction
fixed-sheet objective and final backend validation
legacy solver explicit opt-in only
```

This is not a bbox-removal task. Bbox/AABB restrictions are only a consequence of the Sparrow/CDE-first target. AABB may only broad-phase prune impossible collisions; it may never be positive collision truth, semantic score truth, or final validity.

## Required prior state

Read these first:

```text
codex/prompts/egyedi_solver/sgh_q23_full_sparrow_parity_cutover/run.md
codex/reports/egyedi_solver/sgh_q23_full_sparrow_parity_cutover.md
codex/reports/egyedi_solver/sgh_q23_full_sparrow_parity_cutover_measurements.json
codex/reports/egyedi_solver/sgh_q23_full_sparrow_parity_cutover_measurements.md
docs/egyedi_solver/sgh_q23_sparrow_reference_map.md
docs/egyedi_solver/sgh_q23_full_sparrow_parity_cutover.md
```

Q23 ended as `REVISE`, not PASS. Treat its own report as the baseline:

```text
SPARROW_PRODUCTION_STATUS: CDE_FIRST_PARTIAL_PRODUCTION_PATH_ESTABLISHED_MEDIUM_CDE_CONVERGENCE_BLOCKED
Q18B_RECOMMENDATION: REQUIRED_FOR_CDE_SCALE
```

Concrete Q23 measurement blocker:

```text
medium_10_to_20_items / sparrow_cde:
  status: unsupported
  placed_count: 0/12
  runtime_ms: ~25017.8
  sparrow_iterations: 5
  moves_attempted: 4
  collision_pairs_initial -> final: 66 -> 28
  cde_total_queries: 11236
  cde_engine_builds: 7650
  cde_broadphase_pruned: 3586
```

This R1 task must attack that blocker by porting the missing Sparrow mechanisms, not by falling back to bbox/legacy/PhaseOptimizer.

## Mandatory local Sparrow reference gate

`.cache/sparrow` is gitignored but must be present locally. Use it as the algorithmic reference.

If missing, the first report line must be:

```text
BLOCKED
reason: .cache/sparrow missing
```

If present, re-open the Q23 reference map and extend it as needed. Do not spend the whole run auditing. The reference check is only to guide implementation.

Run at minimum:

```bash
find .cache/sparrow -maxdepth 5 -type f | sed -n '1,420p'
rg -n "search_position|separation|separate|compress|compression|exploration|Guided|GLS|collision|CollisionTracker|CDE|jagua|Layout::cde|position|coordinate|descent|sample|worker|move_items|move_items_multi|feasibility|penalty|weight|Evaluator|sep_evaluator|Algorithm" .cache/sparrow
```

Update or create:

```text
docs/egyedi_solver/sgh_q23r1_sparrow_reference_delta.md
```

This delta must focus only on what Q23 missed and what R1 implemented.

## Implementation scope

### 1. Replace per-call CDE with solve-scoped CDE/session/cache

Q23 left VRS with a per-query `CDEngine::new` bottleneck. This is structurally incompatible with Sparrow-scale search.

Implement a solve-scoped CDE/Jagua backend layer. Preferred shape:

```text
rust/vrs_solver/src/optimizer/cde_session.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/optimizer/collision_backend.rs
```

Required behavior:

```text
prepared geometry cache by part/rotation/transform version
transformed placement cache by instance/version
pair decision cache by ordered pair + versions + backend config
boundary decision cache by instance/version + sheet version
active-set pair filtering before CDE query
incremental dirty invalidation when an item moves
engine/session lifecycle visible in diagnostics
CDE engine builds must no longer scale with every pair/boundary query
unsupported CDE results must not become NoCollision
```

Acceptable implementation strategies:

```text
A) true stateful CDE session modeled after local .cache/sparrow / jagua usage
B) VRS-side solve-scoped exact/CDE cache with dirty invalidation while keeping CDE adapter calls behind cache misses
C) direct architecture port from local Sparrow if license-compatible and documented
```

Unacceptable:

```text
per-call-only CDE remains the hot path for medium fixtures
bbox backend used because CDE is slow
turning unsupported into valid/no-collision
hiding engine builds or query counts from diagnostics
```

### 2. Implement incremental collision graph, not full O(n²) rebuild every loop

Current Q22/Q23 `CollisionGraphSnapshot::from_tracker` is an O(n²) derived snapshot. That is not enough for production Sparrow behavior.

Implement a maintained collision graph / tracker lifecycle:

```text
initial graph build
register_item_move / dirty item update
remove stale edges touching moved item
re-query only active-set candidate pairs touching moved item
update boundary violation for moved item
preserve GLS weights separately from transient collision edges
produce deterministic top-k graph snapshots for diagnostics
```

Use local Sparrow's collision tracker as the behavioral reference.

### 3. Implement Sparrow-style multi-target pass

Q23 still moves one worst target per iteration. A real Sparrow-style search must not be a single-target toy loop.

Implement a move pass that attempts movement for all currently relevant colliding items, deterministic but seed-aware. It may be sequential in Rust if parallelism is too invasive in this run, but it must follow the local Sparrow concept of a pass over colliding workers/items rather than one item per global iteration.

Required:

```text
select target set from weighted collision graph
stable deterministic ordering with seed-controlled tie breaks where appropriate
for each target: search_position + coordinate refinement + backend-oracle evaluate_transform
commit accepted move and update dirty graph incrementally
reject/rollback without corrupting GLS weights
collect pass-level stats
```

Diagnostics must include:

```text
sparrow_passes
sparrow_targets_considered
sparrow_targets_moved
sparrow_graph_incremental_updates
sparrow_graph_full_rebuilds
sparrow_cache_pair_hits/misses
sparrow_cache_boundary_hits/misses
sparrow_engine_builds_per_solve
```

### 4. Implement stagnation and GLS lifecycle properly

Do not only bump weights occasionally. Port the actual local Sparrow idea:

```text
weighted collision utility
penalize repeatedly problematic pairs/items
preserve weights across rollback/restore as intended
separate collision edge lifecycle from weight memory
stagnation detection
controlled disruption/restart when no improvement
best feasible incumbent
best infeasible incumbent
```

A PASS is not allowed if GLS is only a counter without search effect.

### 5. Implement fixed-sheet exploration/compression lifecycle

Q23 did not finish Sparrow exploration/compression parity. R1 must implement it for fixed sheet.

Adaptation:

```text
Sparrow strip length minimization -> fixed-sheet feasibility + compactness/utilization/spread objective
Exploration -> generate/repair candidate feasible layouts under fixed sheet constraints
Compression -> reduce spread/extent and improve utilization while preserving feasibility
```

Minimum production lifecycle:

```text
seed infeasible layout
exploration pass loop with restarts/disruption
separation pass until feasible or budget exhausted
compression pass on best feasible incumbent
final CDE validation
return partial/unsupported only with complete diagnostics
```

Do not call PhaseOptimizer compression from production `sparrow_cde` unless it is explicitly refactored into a backend-oracle Sparrow-compatible module and documented. Calling old PhaseOptimizer as a black-box postpass is not a full cutover.

### 6. Make `sparrow_cde` the production default path

The old solver must not remain the default production behavior.

Required code changes:

```text
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/adapter.rs
web/worker/adapter code if it emits or defaults optimizer_pipeline
scripts and smoke fixtures that create production solver input
```

Desired behavior:

```text
missing optimizer_pipeline -> sparrow_cde for production solve inputs
explicit optimizer_pipeline = "phase_optimizer" -> legacy/debug comparison only
explicit optimizer_pipeline = "legacy_multisheet" or equivalent -> legacy/debug comparison only
explicit optimizer_pipeline = "sparrow_experimental" -> debug/development only
```

If changing the global default would break unrelated web/API contracts, implement a clearly named production config switch and wire all normal production run configs to `sparrow_cde`; then document the remaining compatibility default as temporary and non-production. Do not leave the normal run path ambiguous.

### 7. Legacy quarantine

Production `sparrow_cde` may not silently use old solver logic.

Required assertions/tests:

```text
phase_optimizer is not invoked by sparrow_cde
legacy_multisheet is not invoked by sparrow_cde
LBF/finite-candidate fallback is not invoked by sparrow_cde
bbox backend request is ignored/overridden for sparrow_cde
final commit uses active CDE/Jagua backend
unsupported/timeout returns complete diagnostics, not legacy result
```

Legacy code may remain for comparison only.

### 8. Medium fixture must converge or expose exact remaining algorithmic blocker

The medium Q23 fixture is the first hard R1 gate.

Required smoke/bench updates:

```text
scripts/smoke_sgh_q23r1_production_sparrow_cutover.py
scripts/bench_sgh_q23r1_production_sparrow_cutover.py
```

Minimum fixture gates:

```text
tiny_cde_must_converge
two_rect_overlap_cde_must_separate
boundary_recovery_cde_must_recover
continuous_rotation_rescue_cde
medium_10_to_20_items_cde_must_converge_without_timeout
production_default_is_sparrow_cde_or_normal_run_config_routes_to_sparrow_cde
production_sparrow_uses_backend_oracle_evaluation
production_sparrow_no_legacy_fallback
production_sparrow_incremental_graph_and_cache_metrics_present
production_sparrow_preserves_full_diagnostics_on_failure
```

Benchmark accounting must include every production run in denominators:

```text
ok
partial
unsupported
timeout
error
```

### 9. Acceptance thresholds

These are hard gates for PASS:

```text
medium_10_to_20_items / sparrow_cde:
  status: ok
  placed_count: required_count
  sparrow_converged: true
  bbox_fallback_queries: 0
  lbf_fallback_used: 0
  backend_used: cde_adapter or jagua_cde_session
  runtime: must not hit timeout
  cde_engine_builds: must be reduced by at least 80% vs Q23 baseline 7650, or replaced by session metric proving engine reuse
  cache hit/miss/invalidation metrics present
  incremental collision graph metrics present
```

Additional PASS gates:

```text
production path no longer depends on PhaseOptimizer/legacy fallback
normal production route uses sparrow_cde
all final results CDE/Jagua validated
all failure results keep optimizer diagnostics
reference delta documents concrete local Sparrow concepts used
cargo tests pass
smoke passes
quick benchmark writes JSON and Markdown with denominator accounting
```

If these cannot all be met, report `REVISE`, but only after implementing the maximum possible code changes in this run. A report-only REVISE is unacceptable unless blocked by missing `.cache/sparrow` or compilation-breaking external dependency issues.

## Files to create/update

Expected touched areas include, but are not limited to:

```text
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/optimizer/sparrow.rs
rust/vrs_solver/src/optimizer/cde_session.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/optimizer/collision_backend.rs
rust/vrs_solver/src/optimizer/collision_severity.rs
rust/vrs_solver/src/optimizer/search_position.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/loss_model.rs
rust/vrs_solver/src/optimizer/mod.rs
scripts/smoke_sgh_q23r1_production_sparrow_cutover.py
scripts/bench_sgh_q23r1_production_sparrow_cutover.py
docs/egyedi_solver/sgh_q23r1_sparrow_reference_delta.md
docs/egyedi_solver/sgh_q23r1_production_sparrow_cutover_implementation.md
codex/reports/egyedi_solver/sgh_q23r1_production_sparrow_cutover_implementation.md
codex/reports/egyedi_solver/sgh_q23r1_production_sparrow_cutover_implementation.verify.log
codex/reports/egyedi_solver/sgh_q23r1_production_sparrow_cutover_measurements.json
codex/reports/egyedi_solver/sgh_q23r1_production_sparrow_cutover_measurements.md
```

## Required commands

Run at minimum:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::sparrow
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::cde_session
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_severity
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::search_position
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator
cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q23r1_production_sparrow_cutover.py
python3 scripts/bench_sgh_q23r1_production_sparrow_cutover.py --quick
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q23r1_production_sparrow_cutover_implementation.md
```

If a command is too slow, run the most targeted replacement and explain exactly why. Do not omit the medium CDE convergence gate.

## Report format

Create:

```text
codex/reports/egyedi_solver/sgh_q23r1_production_sparrow_cutover_implementation.md
```

First line must be exactly one of:

```text
PASS
REVISE
BLOCKED
```

Required markers:

```text
SGH-Q23R1_STATUS: READY_FOR_AUDIT|REVISE|BLOCKED
SPARROW_PRODUCTION_STATUS: FULL_CUTOVER_FIXED_SHEET_CDE|PARTIAL_WITH_EXPLICIT_BLOCKERS|BLOCKED
PRODUCTION_DEFAULT_STATUS: SPARROW_CDE_DEFAULT|SPARROW_CDE_NORMAL_RUN_CONFIG|LEGACY_STILL_DEFAULT_REVISE
CDE_SESSION_STATUS: STATEFUL_SESSION_OR_CACHE_ACTIVE|PARTIAL_REVISE|BLOCKED
INCREMENTAL_GRAPH_STATUS: ACTIVE|PARTIAL_REVISE|BLOCKED
LEGACY_SOLVER_STATUS: EXPLICIT_OPT_IN_ONLY|LEAKING_REVISE
MEDIUM_CDE_STATUS: CONVERGED|NOT_CONVERGED_REVISE|BLOCKED
Q19_STATUS: HOLD
```

PASS final markers must include:

```text
SGH-Q23R1_STATUS: READY_FOR_AUDIT
SPARROW_PRODUCTION_STATUS: FULL_CUTOVER_FIXED_SHEET_CDE
PRODUCTION_DEFAULT_STATUS: SPARROW_CDE_DEFAULT|SPARROW_CDE_NORMAL_RUN_CONFIG
CDE_SESSION_STATUS: STATEFUL_SESSION_OR_CACHE_ACTIVE
INCREMENTAL_GRAPH_STATUS: ACTIVE
LEGACY_SOLVER_STATUS: EXPLICIT_OPT_IN_ONLY
MEDIUM_CDE_STATUS: CONVERGED
Q19_STATUS: HOLD
```

## Final instruction

Implement the solver transition. Do not stop at explaining the transition. Do not center the task around bbox. The central acceptance is that production fixed-sheet solving now follows the local jagua_rs/Sparrow algorithmic model with CDE/Jagua geometry truth and can pass the medium CDE gate without legacy fallback.
