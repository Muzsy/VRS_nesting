# SGH-Q12 — jagua-rs CDEngine Adapter Contract

## Status

**PASS** — genuine CDE collision detection implemented via per-call `CDEngine` construction.

## Overview

The `CdeCollisionBackend` (wired via `collision_backend: "cde"` in `SolverInput`) now delegates to a
real jagua-rs 0.6.4 `CDEngine` instance. It is **not** a bbox wrapper and **not** a
`JaguaPolygonExactBackend` rename.

## API Audit Results (jagua-rs 0.6.4)

| Symbol / API | Path | Visibility | Usable from vrs_solver? | Notes |
|---|---|---|---|---|
| `CDEngine` | `jagua_rs::collision_detection::CDEngine` | `pub struct` | Yes (per-call) | Stateful; requires ≥1 Exterior hazard |
| `CDEngine::detect_poly_collision` | same | `pub fn` | Yes | Queries all registered hazards |
| `CDEngine::detect_containment_collision` | same | `pub fn` | Yes | Handles A⊂B and B⊂A |
| `CDEConfig` | `jagua_rs::collision_detection::CDEConfig` | `pub struct` | Yes | quadtree_depth, cd_threshold, item_surrogate_config |
| `Hazard` | `jagua_rs::collision_detection::hazards::Hazard` | `pub struct` | Yes | `new(entity, shape, dynamic)` |
| `HazardEntity::Exterior` | same | `pub enum variant` | Yes | Forbidden zone = outside shape; use for sheet boundary |
| `HazardEntity::Hole { idx }` | same | `pub enum variant` | Yes | Forbidden zone = inside shape; use for placed item pair query |
| `HazardEntity::PlacedItem { pk: PItemKey }` | same | `pub enum variant` | Partial | Requires SlotMap PItemKey — needs full layout state |
| `NoFilter` | `jagua_rs::collision_detection::hazards::filter::NoFilter` | `pub struct` | Yes | All hazards relevant |
| `SPSurrogateConfig::none()` | `jagua_rs::geometry::fail_fast::SPSurrogateConfig` | `pub fn` | Yes | Zero-surrogate config for minimal CDEConfig |
| `SPolygon` | `jagua_rs::geometry::primitives::SPolygon` | `pub struct` | Yes (already used) | f32 coordinates; built via `to_jag_polygon` |
| `Rect` (jagua-rs) | `jagua_rs::geometry::primitives::Rect` | `pub struct` | Yes | `try_new(x_min, y_min, x_max, y_max: f32)` |

## VRS-Owned Adapter Types

### `CdeAdapterConfig`

```rust
pub struct CdeAdapterConfig {
    pub quadtree_depth: u8,   // default: 4
    pub cd_threshold: u8,     // default: 0
}
```

Configures the per-call `CDEngine`. Higher `quadtree_depth` improves precision but increases setup cost.

### `CdePreparedShape` (pub(crate))

```rust
pub(crate) struct CdePreparedShape {
    pub(crate) spoly: SPolygon,
    pub(crate) min_x: f64,
    pub(crate) min_y: f64,
    pub(crate) max_x: f64,
    pub(crate) max_y: f64,
}
```

Holds the jagua-rs SPolygon plus an f64 bounding box for union bbox computation.
jagua-rs types do NOT appear in the public optimizer API — this type is `pub(crate)` only.

### `CdeQueryResult`

```rust
pub enum CdeQueryResult {
    Collision,
    NoCollision,
    Unsupported { reason: &'static str },
}
```

`Unsupported` is returned when shape preparation fails (missing or invalid polygon data).
Callers must NOT treat `Unsupported` as `NoCollision`.

## Pair Query Implementation

For `CdeAdapter::query_pair(a, b)`:

1. Compute union bbox of A and B + 1.0 margin on all sides.
2. Create `Exterior` hazard from the union bbox rect (A and B are both inside this "valid zone").
3. Create `Hole { idx: 0 }` hazard from B's SPolygon (interior of B is forbidden).
4. `CDEngine::new(union_bbox, [exterior, b_hole], config)`
5. `detect_poly_collision(&a.spoly, &NoFilter)`

This correctly detects:
- Edge-edge intersection between A and B
- A ⊂ B containment (A's POI is inside B)
- B ⊂ A containment (B's bbox enclosed by A's bbox → A.contains(B.poi.center))

## Boundary Query Implementation

For `CdeAdapter::query_boundary(item, sheet)`:

1. CDEngine bbox = sheet bbox + 1.0 margin.
2. Register sheet polygon as `Exterior` hazard (items must be inside).
3. `detect_poly_collision(&item.spoly, &NoFilter)` → `true` = item violates boundary.

## Documented Semantic Difference

CDE uses `Edge::collides_with` with `proper_only=false`. Collinear/touching edges count as
Collision. `JaguaPolygonExactBackend` uses `segments_properly_intersect` which requires a strict
crossing (orientation test). Therefore:

- **Touching items** (shared edge): CDE → `Collision`, JaguaPolygonExact → `NoCollision`
- **L-shape notch** (item in notch): CDE → `NoCollision`, Bbox → `Collision` (false positive)
- **Actual overlap**: CDE → `Collision`, all backends agree

This difference is by design and consistent with jagua-rs's strictness guarantee.

## Performance Note (Per-Call CDEngine)

Per-call `CDEngine` construction is O(quadtree build) per pair query. For the pilot this is
acceptable. The production port plan is:

1. **Session-owned CDEngine**: build one CDEngine per sheet layout at the start of a phase iteration.
2. Register all placed items as `HazardEntity::Hole` or `HazardEntity::PlacedItem` (requires slotmap).
3. For each candidate placement, query without rebuilding the CDEngine.

This would reduce the overhead from O(n × quadtree build) to O(n × query).

## Geometry Preprocessing Connection

`CdePreparedShape` is built by `prepare_shape_from_placement`:
- Parts **without** `outer_points`: rect polygon from part dimensions, transformed by placement anchor.
- Parts **with** valid `outer_points`: local polygon transformed by placement anchor via `transform_polygon`.
- Parts with **invalid** `outer_points`: returns `Err` → `CollisionDecision::Unsupported`.

This builds on the `PreparedShape` / `PolygonExtraction` foundation from Q08 (`extract_polygon_from_part`).

What is already available:
- `PolygonExtraction::Absent | Invalid | Valid` — full polygon state
- `transform_polygon(local, anchor_x, anchor_y, rot_deg)` — rotation + translation
- `to_jag_polygon(points, label)` — f64 → SPolygon (f32)
- `polygon_bbox(points)` — bounding box

What is still missing for full Sparrow/jagua parity:
- Hole/cavity polygon support (currently not carried through CDE queries)
- `HazardEntity::PlacedItem` with layout slotmap (requires session-owned CDEngine)
- Quality zones (`HazardEntity::InferiorQualityZone`)
- SPSurrogate caching (currently `SPSurrogateConfig::none()`)

## No-Silent-Fallback Contract

- `collision_backend: "cde"` → `CdeCollisionBackend` → `CdeAdapter::query_pair / query_boundary`
- Never delegates to `BboxCollisionBackend`
- Never delegates to `JaguaPolygonExactBackend`
- Invalid geometry → `Unsupported { reason }`, not `NoCollision`
- `CdeCollisionBackend.name()` → `"cde_adapter"` (not `"cde_scaffold_blocked"`)

## Acceptance Outcome

**PASS** — Category A from the canvas:

> "valódi CdeCollisionBackend opt-in módon működik legalább rect + outer polygon placement overlap/boundary fixture-ökön."

Verified by 10 cde_adapter tests + updated collision_backend tests. 300 total library tests pass.
