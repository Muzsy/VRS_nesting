# SGH-Q18A — CDE correctness/runtime observability contract

## Purpose

Q18A makes CDE backend usage measurable and auditable. This contract documents:
- what counters are emitted and where,
- how the output diagnostics were extended (backward-compatible),
- timing policy (determinism-safe),
- test and smoke coverage.

## Predecessor

SGH-Q16 fixed the CDE final commit gate: `validate_and_commit_with_backend(Cde)` now uses
genuine `CdeCollisionBackend` instead of the blanket `CDE_BACKEND_UNSUPPORTED` scaffold.

## New module: `optimizer::cde_observability`

File: `rust/vrs_solver/src/optimizer/cde_observability.rs`

Thread-local `CdeCounters` struct:

| Field | Meaning |
|---|---|
| `pair_queries` | Item-vs-item pair queries reaching `CdeCollisionBackend::placement_overlaps` |
| `boundary_queries` | Item-vs-sheet queries reaching `CdeCollisionBackend::placement_within_sheet` |
| `total_queries` | `pair_queries + boundary_queries` |
| `engine_builds` | `CDEngine::new(...)` constructions (one per successful pair or boundary query) |
| `collision_results` | Queries returning `CollisionDecision::Collision` |
| `no_collision_results` | Queries returning `CollisionDecision::NoCollision` |
| `unsupported_results` | Queries returning `CollisionDecision::Unsupported` |
| `prepare_failures` | `prepare_shape_from_placement` failures before CDEngine stage |
| `cross_sheet_skipped` | Cross-sheet pair queries skipped before any CDEngine build |

Public API: `reset()`, `snapshot() -> CdeCounters`.
Internal increment functions are `pub(crate)`.

Thread-local storage prevents race conditions under parallel `cargo test --test-threads=N`.

## Instrumentation points

### `CdeCollisionBackend::placement_overlaps` (collision_backend.rs)

1. Cross-sheet early return → `inc_cross_sheet_skipped()` (no pair counter increment)
2. Enter → `inc_pair()`
3. `prepare_shape_from_placement` Err → `inc_prepare_failure()` + `inc_unsupported()`, return
4. `query_pair` result: Collision → `inc_collision()`, NoCollision → `inc_no_collision()`, Unsupported → `inc_unsupported()`

### `CdeCollisionBackend::placement_within_sheet` (collision_backend.rs)

1. Enter → `inc_boundary()`
2. `prepare_shape_from_placement` Err → `inc_prepare_failure()` + `inc_unsupported()`, return
3. `query_boundary` result: same pattern as above

### `CdeAdapter::query_pair` (cde_adapter.rs)

- Just before `CDEngine::new(...)` → `inc_engine_build()`

### `CdeAdapter::query_boundary` (cde_adapter.rs)

- Just before `CDEngine::new(...)` → `inc_engine_build()`

## Extended output diagnostics

`CollisionBackendDiagnosticsOutput` (io.rs) extended backward-compatibly.

Existing fields preserved:

| Field | Preserved |
|---|---|
| `backend_used` | ✓ always present |
| `unsupported_queries` | ✓ always present |
| `bbox_fallback_queries` | ✓ always present |

New fields (all `Option`, absent when backend is not CDE):

| Field | Description |
|---|---|
| `final_commit_backend_used` | Backend name used for final commit |
| `final_commit_unsupported_queries` | Unsupported query count during final commit |
| `final_commit_bbox_fallback_queries` | Bbox fallback count during final commit (always 0 for CDE) |
| `cde_pair_queries` | CDE pair query count |
| `cde_boundary_queries` | CDE boundary query count |
| `cde_total_queries` | CDE total query count |
| `cde_engine_builds` | CDEngine build count |
| `cde_collision_results` | Collision result count |
| `cde_no_collision_results` | NoCollision result count |
| `cde_unsupported_results` | Unsupported result count |
| `cde_prepare_failures` | prepare_shape failure count |
| `cde_cross_sheet_skipped` | Cross-sheet skip count |
| `cde_observability_scope` | `"final_commit_only"` (legacy_multisheet) or `"full_solve"` (phase_optimizer) |
| `final_commit_validation_ms` | Wall-clock timing for final commit (only when `VRS_CDE_OBSERVABILITY_TIMING=1`) |

## Observability scopes

**`final_commit_only`** (LegacyMultisheet + CDE):
- MultiSheetManager uses Bbox internally; CDE counters only accumulate during
  `validate_and_commit_with_backend` called at the end.
- Reset: just before `validate_and_commit_with_backend`.

**`full_solve`** (PhaseOptimizer + CDE):
- `PhaseConfig.collision_backend = Cde` → CDE used during scoring, separator, and final commit.
- Reset: just before `PhaseOptimizer::new(config).run(...)`.
- Snapshot: after `validate_and_commit_with_backend`.

## Timing policy

Wall-clock timing is non-deterministic. Existing determinism tests must not regress.

Policy:
- `final_commit_validation_ms` is only serialized when `VRS_CDE_OBSERVABILITY_TIMING=1`.
- Default SolverOutput JSON contains no timing fields.
- Deterministic query counts are always present for CDE backend.

## Unsupported output preservation

When CDE backend produces `UnsupportedBackend { reason: "CDE_BACKEND_UNSUPPORTED_QUERY" }`,
the output includes `collision_backend_diagnostics` with the accumulated CDE counters.
This is implemented via `_unsupported_output_with_backend_diag` in `adapter.rs`.

## Files modified

| File | Change |
|---|---|
| `rust/vrs_solver/src/optimizer/mod.rs` | `pub mod cde_observability;` added |
| `rust/vrs_solver/src/optimizer/cde_observability.rs` | New module: thread-local CDE counters |
| `rust/vrs_solver/src/optimizer/cde_adapter.rs` | `inc_engine_build()` before each `CDEngine::new(...)` |
| `rust/vrs_solver/src/optimizer/collision_backend.rs` | CDE methods fully instrumented |
| `rust/vrs_solver/src/io.rs` | `CollisionBackendDiagnosticsOutput` extended backward-compatibly |
| `rust/vrs_solver/src/adapter.rs` | CDE reset/snapshot/diag helpers; extended commit paths; Q18A tests |

## Test coverage

See Q18A report for the full list of 350 passing tests.
