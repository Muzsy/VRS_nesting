# SGH-Q10 CollisionBackend Policy Contract

## Overview

Q10 introduces explicit, backward-compatible collision backend selection for production acceptance gates. The `CollisionBackend` layer created in Q08 is now a first-class production policy rather than a test/helper-only feature.

## Accepted JSON values

`SolverInput.collision_backend` accepts the following string values:

| Value | Backend | Behavior |
|---|---|---|
| `"bbox"` | BboxCollisionBackend | Pre-Q08 behavior, exact bbox overlap + rect boundary |
| `"jagua_polygon_exact"` | JaguaPolygonExactBackend | Exact polygon collision; blocks on invalid/missing geometry |
| `"cde"` | CdeCollisionBackend | Always Unsupported (scaffold only, not yet implemented) |

Missing field or `null`: defaults to `bbox` (backward-compatible).

## Default policy

Missing `collision_backend` field → equivalent to `"bbox"`. No output change for existing callers.

## Exact backend no-silent-downgrade policy

When `collision_backend: "jagua_polygon_exact"` is selected:

- If `polygon_for_placement` returns an error for any placed item (malformed `outer_points`, degenerate polygon, etc.), the backend returns `CollisionDecision::Unsupported`.
- `validate_placements_with_backend_checked` counts `unsupported_queries` separately. It does NOT fall back to bbox.
- `validate_and_commit_with_backend` returns `WorkingCommitError::UnsupportedBackend { reason: "JAGUA_POLYGON_EXACT_UNSUPPORTED_QUERY", ... }` if `unsupported_queries > 0`.
- The adapter produces `status: "unsupported", unsupported_reason: "JAGUA_POLYGON_EXACT_UNSUPPORTED_QUERY"`.

Parts with no `outer_points` field: the JaguaPolygonExact backend uses a rect polygon path (`rect_polygon_from_placement`), which is exact for axis-aligned items and rotation-aware. These parts do NOT trigger Unsupported.

## CDE unsupported policy

When `collision_backend: "cde"` is selected:

- `CdeCollisionBackend` always returns `Unsupported` for all placement queries.
- `validate_and_commit_with_backend` immediately returns `WorkingCommitError::UnsupportedBackend { reason: "CDE_BACKEND_UNSUPPORTED", ... }`.
- The adapter produces `status: "unsupported", unsupported_reason: "CDE_BACKEND_UNSUPPORTED"`.
- This is the documented behavior; CDE is a scaffold pending CDEngine API adaptation.

## Which paths are wired in Q10

| Path | Backend gate |
|---|---|
| Phase1 + LegacyMultisheet | Backend gate added for non-bbox backends only |
| Phase1 + PhaseOptimizer | Single `validate_and_commit_with_backend` replaces double `find_violations` + `validate_and_commit` |
| Non-Phase1 (row/cursor fallback) | Unchanged; no backend gate |

For bbox backend (default), the LegacyMultisheet path is unchanged (no extra validation gate added).

## Optional output diagnostics

If a backend gate runs, `SolverOutput` may include:

```json
"collision_backend_diagnostics": {
  "backend_used": "bbox",
  "unsupported_queries": 0,
  "bbox_fallback_queries": 0
}
```

For bbox default on legacy_multisheet, this field is absent (`null`). For explicit non-bbox backends (successful or failed), it is populated.

## Out-of-scope (Q10)

The following are NOT part of Q10:

- Separator/loss-model scoring via exact backend (still bbox-based) — see QUALITY_RISK below
- CDE full implementation
- Exact backend as default
- Hole/cavity semantics
- DXF/preflight refactor
- New optimizer algorithms

## QUALITY_RISK

The separator, compress, BPP, and explore phases all use `find_violations` (bbox) internally for candidate scoring and move evaluation. Even when `collision_backend: "jagua_polygon_exact"` is selected, the internal search heuristic remains bbox-based. The production **acceptance gate** is exact, but the **search quality** is bbox-bounded.

This means exact-backend sessions may accept placements that are bbox-infeasible but exact-feasible (notch exploitation), but the optimizer is unlikely to discover such placements because its internal scoring still uses bbox.

This gap is tracked as QUALITY_RISK-Q11 and deferred to a backend-aware scoring/separator loss path.

## Checked validation invariant

`validate_placements_with_backend_checked`:
- bbox: 0 unsupported_queries for valid geometry; violations match `find_violations` output
- jagua_polygon_exact: unsupported_queries counts invalid/unsupported geometry; no bbox fallback
- cde: all queries return Unsupported; unsupported_queries = total boundary + overlap query count
- `bbox_fallback_queries` is always 0 in the checked path
