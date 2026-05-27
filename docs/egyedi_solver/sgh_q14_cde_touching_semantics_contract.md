# SGH-Q14 — CDE Touching Semantics Contract

## Status

**PASS** — CDE touching semantics match VRS/Q08R policy. 323 library tests pass.

## Overview

SGH-Q14 fixed a semantics mismatch between raw CDE collision detection and VRS policy:
raw jagua-rs `Edge::collides_with(proper_only=false)` reports collinear/touching edges as
Collision. VRS policy (established in Q08R) requires touching = NoCollision, positive-area
overlap = Collision.

The fix applies a VRS-side post-policy layer in `cde_adapter.rs` whenever CDE raw reports
Collision — reclassifying touching-only cases as NoCollision.

## VRS Touching Policy (from Q08R)

```text
shared edge touch          -> NoCollision
shared corner touch        -> NoCollision
boundary touch while fully inside  -> NoCollision
positive-area overlap      -> Collision
proper crossing / outside  -> Collision
unsupported geometry       -> Unsupported
```

## Root Cause

jagua-rs `CDEngine::detect_poly_collision` calls `Edge::collides_with(proper_only=false)`,
which returns `true` for collinear edges and corner contacts. There is no public flag to
switch to `proper_only=true` without forking jagua-rs.

## Post-Policy Architecture

### Pair query post-policy (`query_pair`)

```text
CDE raw: NoCollision → NoCollision (fast path, no post-check needed)
CDE raw: Collision   → run polygons_collide(a.world_pts, b.world_pts)
    polygons_collide = false → NoCollision (touching only, no positive area)
    polygons_collide = true  → Collision   (proper crossing / positive area)
    Err(reason)              → Unsupported { reason }
```

`polygons_collide` uses:
- `segments_properly_intersect` — edges that properly cross (not collinear/touching)
- `point_strictly_inside_polygon` — containment without boundary

### Boundary query post-policy (`query_boundary`)

```text
CDE raw: NoCollision → NoCollision (fast path)
CDE raw: Collision   → run polygon_within_sheet_pts(item.world_pts, sheet.world_pts)
    within = true  → NoCollision (item fully inside, may touch boundary)
    within = false → Collision   (item truly outside or crossing sheet boundary)
    Err(reason)    → Unsupported { reason }
```

`polygon_within_sheet_pts` checks:
- All item vertices satisfy `point_inside_or_on_polygon` (inside OR on boundary)
- No item edge properly crosses any sheet edge (using `segments_properly_intersect`)

### `CdePreparedShape.world_pts`

```rust
pub(crate) struct CdePreparedShape {
    pub(crate) spoly: jagua_rs::geometry::primitives::SPolygon,
    pub(crate) min_x: f64,
    pub(crate) min_y: f64,
    pub(crate) max_x: f64,
    pub(crate) max_y: f64,
    pub(crate) world_pts: Vec<Point>,  // f64 world-coord polygon for VRS post-policy
}
```

`world_pts` stores the item's polygon vertices in world coordinates, derived from the
same placement transformation used to build `spoly`. This avoids jagua-rs type leakage
while enabling the post-policy VRS geometry helpers.

## No-Regression Guarantees

| Backend | Touching behaviour | Changed? |
|---|---|---|
| BboxDefault | touching = depends on bbox logic | No — Bbox arm untouched |
| JaguaPolygonExact | touching = NoCollision (Q08R policy) | No — exact arm untouched |
| CDE | touching = Collision (raw) → NoCollision (post-policy) | Fixed in Q14 |

## Geometry Helpers

| Function | Location | Semantics |
|---|---|---|
| `polygons_collide` | `collision_backend.rs` | `true` only for positive-area overlap / proper crossing |
| `polygon_within_sheet_pts` | `collision_backend.rs` | `true` if item fully inside (boundary touch OK) |
| `segments_properly_intersect` | `collision_backend.rs` | `true` only for proper crossing, not collinear/touching |
| `point_strictly_inside_polygon` | `collision_backend.rs` | `true` only for strict interior |
| `point_inside_or_on_polygon` | `collision_backend.rs` | `true` for interior + boundary |

## Modified Files

```
rust/vrs_solver/src/optimizer/cde_adapter.rs       — post-policy in query_pair/query_boundary; world_pts field
rust/vrs_solver/src/optimizer/collision_backend.rs  — polygons_collide pub(crate); polygon_within_sheet_pts new
rust/vrs_solver/src/optimizer/separator.rs         — 2 Q14 regression-fix tests
rust/vrs_solver/src/optimizer/moves.rs             — 1 Q14 regression-fix test rename
rust/vrs_solver/src/optimizer/sheet_elimination.rs — 1 Q14 regression-fix test inversion
```

## Acceptance Outcome

323 library tests pass. 13 Q14 required tests pass. Bbox and JaguaPolygonExact
semantics unchanged. verify.sh exits 0.
