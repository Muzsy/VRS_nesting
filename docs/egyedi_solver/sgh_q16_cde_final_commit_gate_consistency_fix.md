# SGH-Q16 — CDE Final Commit Gate Consistency Fix

## Status

**PASS** — CDE final commit gate consistent. 334 tests pass.

## Overview

SGH-Q16 fixed the last remaining CDE scaffold: `WorkingLayout::validate_and_commit_with_backend(CollisionBackendKind::Cde)` was returning a blanket `CDE_BACKEND_UNSUPPORTED` error for every placement without ever calling `CdeCollisionBackend`. While the rest of the repo (repair.rs, separator.rs, sheet_elimination.rs) already used genuine CDE collision detection, the final acceptance gate was broken.

After Q16, the CDE branch uses `CdeCollisionBackend` via a shared `commit_with_checked_backend` helper, matching the pattern already used for `JaguaPolygonExact`.

## Contract

### CDE final commit policy

```
valid layout          → Ok(BackendCommitResult { backend_diagnostics.backend_name == "cde_adapter",
                                                  unsupported_queries == 0,
                                                  bbox_fallback_queries == 0 })
unsupported geometry  → Err(UnsupportedBackend { reason: "CDE_BACKEND_UNSUPPORTED_QUERY", ... })
collision/boundary    → Err(Violations(...))
```

### Invariants

- `bbox_fallback_queries == 0` always in CDE commit path.
- No silent bbox or JaguaPolygonExact fallback.
- `CDE_BACKEND_UNSUPPORTED` (blanket, Q16-pre) no longer appears for valid geometry.
- CDE remains opt-in: `collision_backend: "cde"` must be set explicitly.
- CDE remains outer-only in the main solver: `MAIN_SOLVER_MUST_BE_HOLE_FREE` invariant from Q15 is unchanged.

## Architecture

### Before Q16

```rust
CollisionBackendKind::Cde => {
    let placement_count = self.placements.len();
    Err(WorkingCommitError::UnsupportedBackend {
        reason: "CDE_BACKEND_UNSUPPORTED".to_string(),
        unsupported_queries: placement_count,  // always all placements
    })
}
```

### After Q16

```rust
CollisionBackendKind::Cde => self.commit_with_checked_backend(
    parts, sheets, &CdeCollisionBackend, "CDE_BACKEND_UNSUPPORTED_QUERY",
),
```

The `commit_with_checked_backend` helper calls `validate_placements_with_backend_checked` and enforces:
- `unsupported_queries > 0` → `UnsupportedBackend { reason: unsupported_reason }`
- `violations non-empty` → `Violations`
- `valid` → `BackendCommitResult`

## Files changed

```
rust/vrs_solver/src/optimizer/working.rs    — CDE commit gate fix, commit_with_checked_backend helper, 7 Q16 tests
rust/vrs_solver/src/io.rs                  — stale "always Unsupported (scaffold only)" comment updated
rust/vrs_solver/src/optimizer/collision_backend.rs — "scaffold / BLOCKED" section header updated
rust/vrs_solver/src/adapter.rs             — updated + 4 new adapter-level Q16 tests
```

## Remaining work (not Q16)

- **CDE per-call performance**: `CdeCollisionBackend` builds a `CDEngine` per query call. O(n) setup cost per placement pair. Session-owned CDEngine is the production port target.
- **Q18A observability**: measure `backend_used`, CDE query count, unsupported count, per-phase runtime, and final commit backend evidence.
- **Q18B session/cache**: only if Q18A measurements show the per-call adapter is a real bottleneck.

## Dependency chain

```
Q14 CDE touching semantics → Q15 MAIN_SOLVER_MUST_BE_HOLE_FREE → Q16 CDE final commit gate → Q18A observability
```
