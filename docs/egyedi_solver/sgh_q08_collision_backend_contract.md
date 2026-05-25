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

Status: **PASS** — exact polygon backend.

- `placement_overlaps`:
  - Both parts have `outer_points`: world-transformed polygon-polygon via edge-edge intersection (`Edge: CollidesWith<Edge>`) + point-in-polygon (`SPolygon: CollidesWith<Point>`).
  - One part rect: rect bbox corners treated as polygon.
  - Both rect: bbox overlap (exact for axis-aligned rectangles).
- `placement_within_sheet`:
  - Part has `outer_points`: all world polygon vertices checked against `sheet._outer_poly`, all item edges checked against sheet boundary edges.
  - Part rect: `rect_within_boundary` (same as BboxCollisionBackend).
- Returns `Unsupported` (not `NoCollision`) when polygon data is unavailable or degenerate.

**Key difference from bbox**: for an L-shaped item, the exact backend detects that a rect placed in the notch region does NOT collide with the L-shape, while bbox would report a false positive.

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
- On `Unsupported`: falls back to bbox check (conservative, transparent, not silent).
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

## Out of scope (Q08)

- Hole/cavity semantics
- DXF/preflight refactor
- New optimizer strategy
- Douglas-Peucker / offset simplification pipeline
- CDE hazard registration integration
