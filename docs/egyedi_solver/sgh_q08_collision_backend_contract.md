# SGH-Q08 — CollisionBackend Contract

## Overview

Q08 introduces a modular collision/geometry backend layer for VRS. This document is the authoritative contract for the new API.

## CollisionDecision

```rust
pub enum CollisionDecision {
    /// Shapes overlap / item violates boundary.
    Collision,
    /// No collision detected.
    NoCollision,
    /// Backend cannot process this query.
    /// MUST NOT be treated as NoCollision by callers.
    Unsupported { reason: &'static str },
}
```

**Invariant**: callers must explicitly handle `Unsupported`. Silent treatment as `NoCollision` is prohibited.

## CollisionBackend trait

```rust
pub trait CollisionBackend {
    fn name(&self) -> &'static str;

    fn placement_overlaps(
        &self,
        a: &Placement, a_part: &Part,
        b: &Placement, b_part: &Part,
    ) -> CollisionDecision;

    fn placement_within_sheet(
        &self,
        placement: &Placement, part: &Part, sheet: &SheetShape,
    ) -> CollisionDecision;
}
```

**Semantic rules**:
- `placement_overlaps` with `a.sheet_index != b.sheet_index` → `NoCollision`.
- `placement_within_sheet` returns `Collision` when the item is fully or partially outside.
- Jagua-rs types must not appear in the public optimizer API.

## Backends

### BboxCollisionBackend

Status: **PASS** — default backend.

- `placement_overlaps`: `PlacedBbox::overlaps` (EPS = 1e-9, touching boundary = NoCollision).
- `placement_within_sheet`: `rect_within_boundary` (delegates to `rect_inside_sheet_shape`).
- Preserves all pre-Q08 behavior exactly.

### JaguaPolygonExactBackend

Status: **PARTIAL/PASS** — exact for the supported outer-boundary rectangle/polygon scope.

- `placement_overlaps`:
  - `outer_points` / `prepared_outer_points` extraction is three-state: `Absent`, `Invalid`, `Valid`.
  - `Absent`: the part is treated as a rectangle and converted to a rotation-aware world polygon.
  - `Invalid`: returns `Unsupported`, never bbox fallback and never `NoCollision`.
  - `Valid`: local polygon is transformed by placement anchor + `rotation_deg`.
  - Rect-vs-rect, rect-vs-polygon, and polygon-vs-polygon all use polygon geometry in the exact backend.
- `placement_within_sheet`:
  - Rect item: rotation-aware world rectangle polygon.
  - Irregular item: transformed world polygon.
  - The same polygon-within-sheet policy is used for both.
- Touching policy:
  - Shared edge -> `NoCollision`.
  - Shared point -> `NoCollision`.
  - Boundary touch while fully inside -> `NoCollision`.
  - Positive-area overlap or true boundary crossing -> `Collision`.
- Returns `Unsupported` for malformed, too-short, zero-area, degenerate, or jagua-unbuildable polygon data.

**Key difference from bbox**: for an L-shaped item, the exact backend detects that a rect placed in the notch region does NOT collide with the L-shape, while bbox would report a false positive. For rotated rectangles, the exact backend uses the true rotated rectangle polygon, not the rotated AABB.

### CdeCollisionBackend

Status: **BLOCKED** — scaffold only.

All methods return `Unsupported`. CDEngine requires hazard registration and does not expose a synchronous placement-level query API compatible with VRS's pattern.

## find_violations_with_backend

```rust
pub fn find_violations_with_backend(
    placements: &[Placement],
    parts: &[Part],
    sheets: &[SheetShape],
    backend: &dyn CollisionBackend,
) -> Vec<(usize, ViolationType)>
```

- Semantically equivalent to `find_violations` when using `BboxCollisionBackend`.
- On `Unsupported`: falls back to bbox check in the wrapper only (conservative, explicit, not backend-silent). Exact backend methods themselves must return `Unsupported` for invalid exact geometry.
- `find_violations` remains the default backward-compatible wrapper.

## GeometryPreprocessing

```rust
pub struct PreparedShape {
    pub vertex_count: usize,
    pub bbox: Option<(f64, f64, f64, f64)>,
    pub area: f64,
    pub has_irregular_shape: bool,
    pub simplification_tolerance: Option<f64>, // None = no simplification applied
    pub backend_readiness: BackendReadiness,
}

pub struct BackendReadiness {
    pub bbox: bool,
    pub jagua_polygon: bool,
    pub cde: bool, // always false in Q08
}

pub fn preprocess_polygon(points: &[Point]) -> Result<PreparedShape, String>;
pub fn preprocess_rect(w: f64, h: f64) -> Result<PreparedShape, String>;
```

**Invariants**:
- `preprocess_polygon` returns `Err` for < 3 points, zero-area, or degenerate after dedup.
- `preprocess_rect` returns `Err` for non-positive dimensions.
- `simplification_tolerance` is always `None` in Q08 (QUALITY_RISK: simplification pipeline not yet implemented).
- `backend_readiness.cde` is always `false` in Q08.

## No-downgrade policy

Production default remains `BboxCollisionBackend` (via `find_violations`). Switching the production default to `JaguaPolygonExactBackend` requires a no-downgrade gate (regression verification on the full benchmark matrix). This is deferred to a future task.

## SGH-Q08R clarifications

- `JaguaPolygonExactBackend` is not full CDE parity.
- `JaguaPolygonExactBackend` is not hole-aware; hole/cavity semantics remain out of scope.
- Invalid exact geometry must not silently downgrade to bbox behavior inside the backend.
- Invalid exact geometry must not become `NoCollision`.
- The exact rectangle path is rotation-aware.
- No-positive-area touching is `NoCollision`.

## Out of scope (Q08)

- Hole/cavity semantics
- DXF/preflight refactor
- New optimizer strategy
- Douglas-Peucker / offset simplification pipeline
- CDE hazard registration integration
