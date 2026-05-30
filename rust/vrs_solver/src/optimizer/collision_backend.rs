use crate::geometry::{polygon_area, to_jag_polygon, Point, Rect, EPS};
use crate::io::Placement;
use crate::item::Part;
use crate::sheet::SheetShape;
use super::boundary::rect_within_boundary;
use super::initializer::bbox_from_placement;

// ---------------------------------------------------------------------------
// CollisionDecision
// ---------------------------------------------------------------------------

/// Result of a collision query from a CollisionBackend.
#[derive(Debug, Clone, PartialEq)]
pub enum CollisionDecision {
    /// The two shapes overlap (item-item) or the item violates the boundary.
    Collision,
    /// No collision detected.
    NoCollision,
    /// Backend cannot process this query (missing polygon data, not yet implemented).
    /// Do NOT silently treat as NoCollision — callers must handle this explicitly.
    Unsupported { reason: &'static str },
}

/// Diagnostics collected during a backend-aware layout validation pass.
#[derive(Debug, Clone, Default)]
pub struct BackendValidationDiagnostics {
    pub backend_name: String,
    /// Number of queries where the backend returned Unsupported.
    /// Callers use this to enforce no-silent-downgrade policy.
    pub unsupported_queries: usize,
    /// Number of queries where the caller fell back to bbox (checked path: always 0).
    pub bbox_fallback_queries: usize,
}

impl CollisionDecision {
    pub fn is_collision(&self) -> bool {
        matches!(self, CollisionDecision::Collision)
    }
    pub fn is_no_collision(&self) -> bool {
        matches!(self, CollisionDecision::NoCollision)
    }
    pub fn is_unsupported(&self) -> bool {
        matches!(self, CollisionDecision::Unsupported { .. })
    }
}

// ---------------------------------------------------------------------------
// CollisionBackend trait
// ---------------------------------------------------------------------------

/// VRS-owned collision backend abstraction.
///
/// Implementations must NOT silently fall back to bbox behavior when exact data
/// is unavailable — they must return `Unsupported` instead.
///
/// Jagua-rs types must not appear in the public optimizer API; this trait is
/// the boundary.
pub trait CollisionBackend {
    /// Human-readable backend name for diagnostics and logging.
    fn name(&self) -> &'static str;

    /// Returns Collision if placement `a` and placement `b` overlap.
    ///
    /// Only placements on the same sheet can collide; different sheet_index
    /// must return NoCollision.
    fn placement_overlaps(
        &self,
        a: &Placement,
        a_part: &Part,
        b: &Placement,
        b_part: &Part,
    ) -> CollisionDecision;

    /// Returns Collision if `placement` violates the sheet boundary (is fully or
    /// partially outside `sheet`).
    fn placement_within_sheet(
        &self,
        placement: &Placement,
        part: &Part,
        sheet: &SheetShape,
    ) -> CollisionDecision;
}

// ---------------------------------------------------------------------------
// BboxCollisionBackend
// ---------------------------------------------------------------------------

/// Bbox-only collision backend.
///
/// Preserves the pre-Q08 behavior exactly: PlacedBbox overlap for item-item,
/// rect_within_boundary for item-container. This is the default backend used by
/// `find_violations`.
pub struct BboxCollisionBackend;

impl CollisionBackend for BboxCollisionBackend {
    fn name(&self) -> &'static str {
        "bbox"
    }

    fn placement_overlaps(
        &self,
        a: &Placement,
        a_part: &Part,
        b: &Placement,
        b_part: &Part,
    ) -> CollisionDecision {
        if a.sheet_index != b.sheet_index {
            return CollisionDecision::NoCollision;
        }
        let bbox_a = bbox_from_placement(a, a_part.width, a_part.height);
        let bbox_b = bbox_from_placement(b, b_part.width, b_part.height);
        match (bbox_a, bbox_b) {
            (Some(ba), Some(bb)) => {
                if ba.overlaps(&bb) {
                    CollisionDecision::Collision
                } else {
                    CollisionDecision::NoCollision
                }
            }
            _ => CollisionDecision::Unsupported {
                reason: "bbox_from_placement failed for one or both placements",
            },
        }
    }

    fn placement_within_sheet(
        &self,
        placement: &Placement,
        part: &Part,
        sheet: &SheetShape,
    ) -> CollisionDecision {
        match bbox_from_placement(placement, part.width, part.height) {
            Some(bbox) => {
                let rect = Rect {
                    x1: bbox.x1,
                    y1: bbox.y1,
                    x2: bbox.x2,
                    y2: bbox.y2,
                };
                if rect_within_boundary(rect, sheet) {
                    CollisionDecision::NoCollision
                } else {
                    CollisionDecision::Collision
                }
            }
            None => CollisionDecision::Unsupported {
                reason: "bbox_from_placement failed",
            },
        }
    }
}

// ---------------------------------------------------------------------------
// JaguaPolygonExactBackend
// ---------------------------------------------------------------------------

/// Exact polygon collision backend using jagua-rs SPolygon + Edge primitives.
///
/// For parts without outer_points: falls back to bbox behavior (rect-rect is
/// exact for axis-aligned items regardless).
///
/// For parts with outer_points: builds world-coordinate polygons and performs
/// edge-edge intersection + point-in-polygon tests via jagua-rs.
///
/// Use this backend for exact polygon collision; see CdeCollisionBackend for
/// the CDEngine-based backend (final commit supported, per-call pilot).
pub struct JaguaPolygonExactBackend;

impl CollisionBackend for JaguaPolygonExactBackend {
    fn name(&self) -> &'static str {
        "jagua_polygon_exact"
    }

    fn placement_overlaps(
        &self,
        a: &Placement,
        a_part: &Part,
        b: &Placement,
        b_part: &Part,
    ) -> CollisionDecision {
        if a.sheet_index != b.sheet_index {
            return CollisionDecision::NoCollision;
        }

        let a_world = match polygon_for_placement(a, a_part) {
            Ok(poly) => poly,
            Err(reason) => return CollisionDecision::Unsupported { reason },
        };
        let b_world = match polygon_for_placement(b, b_part) {
            Ok(poly) => poly,
            Err(reason) => return CollisionDecision::Unsupported { reason },
        };

        match polygons_collide(&a_world, &b_world) {
            Ok(true) => CollisionDecision::Collision,
            Ok(false) => CollisionDecision::NoCollision,
            Err(reason) => CollisionDecision::Unsupported { reason },
        }
    }

    fn placement_within_sheet(
        &self,
        placement: &Placement,
        part: &Part,
        sheet: &SheetShape,
    ) -> CollisionDecision {
        let world_pts = match polygon_for_placement(placement, part) {
            Ok(poly) => poly,
            Err(reason) => return CollisionDecision::Unsupported { reason },
        };

        match polygon_within_sheet(&world_pts, sheet) {
            Ok(true) => CollisionDecision::NoCollision,
            Ok(false) => CollisionDecision::Collision,
            Err(reason) => CollisionDecision::Unsupported { reason },
        }
    }
}

// ---------------------------------------------------------------------------
// CdeCollisionBackend — pilot implementation, final commit supported
// ---------------------------------------------------------------------------

/// CDEngine-based collision backend (pilot implementation).
///
/// Uses a per-call `CDEngine` built from jagua-rs 0.6.4. This is genuine CDE
/// collision detection — not a bbox or JaguaPolygonExact wrapper.
///
/// Semantic difference vs JaguaPolygonExactBackend: CDE uses
/// `Edge::collides_with` with `proper_only=false`, so collinear/touching edges
/// are counted as Collision. JaguaPolygonExact requires a proper edge crossing.
///
/// Performance note: per-call CDEngine construction is O(n) setup per query.
/// A session-owned CDEngine is the production port target (see contract doc).
pub struct CdeCollisionBackend;

impl CollisionBackend for CdeCollisionBackend {
    fn name(&self) -> &'static str {
        "cde_adapter"
    }

    fn placement_overlaps(
        &self,
        a: &Placement,
        a_part: &Part,
        b: &Placement,
        b_part: &Part,
    ) -> CollisionDecision {
        if a.sheet_index != b.sheet_index {
            crate::optimizer::cde_observability::inc_cross_sheet_skipped();
            return CollisionDecision::NoCollision;
        }
        crate::optimizer::cde_observability::inc_pair();
        let a_shape = match super::cde_adapter::prepare_shape_from_placement(a, a_part) {
            Ok(s) => s,
            Err(reason) => {
                crate::optimizer::cde_observability::inc_prepare_failure();
                crate::optimizer::cde_observability::inc_unsupported();
                return CollisionDecision::Unsupported { reason };
            }
        };
        let b_shape = match super::cde_adapter::prepare_shape_from_placement(b, b_part) {
            Ok(s) => s,
            Err(reason) => {
                crate::optimizer::cde_observability::inc_prepare_failure();
                crate::optimizer::cde_observability::inc_unsupported();
                return CollisionDecision::Unsupported { reason };
            }
        };
        let adapter = super::cde_adapter::CdeAdapter::with_defaults();
        match adapter.query_pair(&a_shape, &b_shape) {
            super::cde_adapter::CdeQueryResult::Collision => {
                crate::optimizer::cde_observability::inc_collision();
                CollisionDecision::Collision
            }
            super::cde_adapter::CdeQueryResult::NoCollision => {
                crate::optimizer::cde_observability::inc_no_collision();
                CollisionDecision::NoCollision
            }
            super::cde_adapter::CdeQueryResult::Unsupported { reason } => {
                crate::optimizer::cde_observability::inc_unsupported();
                CollisionDecision::Unsupported { reason }
            }
        }
    }

    fn placement_within_sheet(
        &self,
        placement: &Placement,
        part: &Part,
        sheet: &SheetShape,
    ) -> CollisionDecision {
        crate::optimizer::cde_observability::inc_boundary();
        let item_shape = match super::cde_adapter::prepare_shape_from_placement(placement, part) {
            Ok(s) => s,
            Err(reason) => {
                crate::optimizer::cde_observability::inc_prepare_failure();
                crate::optimizer::cde_observability::inc_unsupported();
                return CollisionDecision::Unsupported { reason };
            }
        };
        let sheet_shape = match super::cde_adapter::prepare_shape_from_sheet(sheet) {
            Ok(s) => s,
            Err(reason) => {
                crate::optimizer::cde_observability::inc_prepare_failure();
                crate::optimizer::cde_observability::inc_unsupported();
                return CollisionDecision::Unsupported { reason };
            }
        };
        let adapter = super::cde_adapter::CdeAdapter::with_defaults();
        match adapter.query_boundary(&item_shape, &sheet_shape) {
            super::cde_adapter::CdeQueryResult::Collision => {
                crate::optimizer::cde_observability::inc_collision();
                CollisionDecision::Collision
            }
            super::cde_adapter::CdeQueryResult::NoCollision => {
                crate::optimizer::cde_observability::inc_no_collision();
                CollisionDecision::NoCollision
            }
            super::cde_adapter::CdeQueryResult::Unsupported { reason } => {
                crate::optimizer::cde_observability::inc_unsupported();
                CollisionDecision::Unsupported { reason }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Private helpers
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub(crate) enum PolygonExtraction {
    Absent,
    Invalid { reason: &'static str },
    Valid(Vec<Point>),
}

/// Extract polygon data without merging absent and invalid states.
pub(crate) fn extract_polygon_from_part(part: &Part) -> PolygonExtraction {
    let Some(json) = part
        .prepared_outer_points
        .as_ref()
        .or(part.outer_points.as_ref())
    else {
        return PolygonExtraction::Absent;
    };

    let pts = match parse_points_json(json) {
        Ok(pts) => pts,
        Err(reason) => return PolygonExtraction::Invalid { reason },
    };
    match clean_valid_polygon(&pts) {
        Ok(cleaned) => PolygonExtraction::Valid(cleaned),
        Err(reason) => PolygonExtraction::Invalid { reason },
    }
}

/// Parse a serde_json::Value as an array of [x, y] or {x, y} points.
fn parse_points_json(v: &serde_json::Value) -> Result<Vec<Point>, &'static str> {
    let arr = v.as_array().ok_or("outer_points must be an array")?;
    let pts: Option<Vec<Point>> = arr
        .iter()
        .map(|item| {
            if let Some(pair) = item.as_array() {
                let x = pair.get(0)?.as_f64()?;
                let y = pair.get(1)?.as_f64()?;
                Some(Point { x, y })
            } else if item.is_object() {
                let x = item.get("x")?.as_f64()?;
                let y = item.get("y")?.as_f64()?;
                Some(Point { x, y })
            } else {
                None
            }
        })
        .collect();
    pts.ok_or("outer_points contains malformed point")
}

fn clean_valid_polygon(points: &[Point]) -> Result<Vec<Point>, &'static str> {
    if points.len() < 3 {
        return Err("polygon must have at least 3 points");
    }
    let mut out = Vec::with_capacity(points.len());
    for &p in points {
        if !p.x.is_finite() || !p.y.is_finite() {
            return Err("polygon point must be finite");
        }
        if out
            .last()
            .map_or(true, |prev: &Point| !points_equal(*prev, p))
        {
            out.push(p);
        }
    }
    if out.len() >= 2 && points_equal(out[0], out[out.len() - 1]) {
        out.pop();
    }
    if out.len() < 3 {
        return Err("polygon became degenerate after deduplication");
    }
    if polygon_area(&out) <= EPS {
        return Err("polygon has zero or near-zero area");
    }
    to_jag_polygon(&out, "exact_backend_polygon").map_err(|_| "SPolygon build failed")?;
    Ok(out)
}

fn polygon_for_placement(
    placement: &Placement,
    part: &Part,
) -> Result<Vec<Point>, &'static str> {
    match extract_polygon_from_part(part) {
        PolygonExtraction::Absent => rect_polygon_from_placement(placement, part.width, part.height),
        PolygonExtraction::Invalid { reason } => Err(reason),
        PolygonExtraction::Valid(local) => Ok(transform_polygon(
            &local,
            placement.x,
            placement.y,
            placement.rotation_deg,
        )),
    }
}

fn rect_polygon_from_placement(
    placement: &Placement,
    width: f64,
    height: f64,
) -> Result<Vec<Point>, &'static str> {
    if width <= 0.0 || height <= 0.0 || !width.is_finite() || !height.is_finite() {
        return Err("rect dimensions must be positive and finite");
    }
    let local = [
        Point { x: 0.0, y: 0.0 },
        Point { x: width, y: 0.0 },
        Point { x: width, y: height },
        Point { x: 0.0, y: height },
    ];
    Ok(transform_polygon(
        &local,
        placement.x,
        placement.y,
        placement.rotation_deg,
    ))
}

/// Apply rotation (degrees) around local origin, then translate by (anchor_x, anchor_y).
///
/// The placement anchor (placement.x, placement.y) is the rotation center — local (0,0)
/// maps to world (anchor_x, anchor_y).
pub(crate) fn transform_polygon(
    local_points: &[Point],
    anchor_x: f64,
    anchor_y: f64,
    rot_deg: f64,
) -> Vec<Point> {
    let theta = rot_deg.to_radians();
    let cos_t = theta.cos();
    let sin_t = theta.sin();
    local_points
        .iter()
        .map(|p| Point {
            x: anchor_x + p.x * cos_t - p.y * sin_t,
            y: anchor_y + p.x * sin_t + p.y * cos_t,
        })
        .collect()
}

/// Test whether two world-coordinate polygons collide.
///
/// Checks:
/// 1. Edge-edge intersection (any edge of A crosses any edge of B).
/// 2. A vertex inside B (one vertex from each to catch containment cases).
/// 3. B vertex inside A.
/// 4. Identical/coincident polygon coverage. This is required because
///    touching-only predicates deliberately ignore boundary contacts, but a
///    duplicate placement with the exact same rectangle is a positive-area
///    overlap and must be rejected by exact backend commit gates.
pub(crate) fn polygons_collide(a: &[Point], b: &[Point]) -> Result<bool, &'static str> {
    let a = clean_valid_polygon(a)?;
    let b = clean_valid_polygon(b)?;
    let na = a.len();
    let nb = b.len();

    // 1. True edge crossing means positive-area overlap. Touching does not.
    for i in 0..na {
        let a0 = a[i];
        let a1 = a[(i + 1) % na];
        for j in 0..nb {
            let b0 = b[j];
            let b1 = b[(j + 1) % nb];
            if segments_properly_intersect(a0, a1, b0, b1) {
                return Ok(true);
            }
        }
    }

    // 2. Strict containment catches positive-area overlap without edge crossing.
    if b.iter().any(|&p| point_strictly_inside_polygon(p, &a)) {
        return Ok(true);
    }
    if a.iter().any(|&p| point_strictly_inside_polygon(p, &b)) {
        return Ok(true);
    }
    if edge_midpoints(&a)
        .iter()
        .any(|&p| point_strictly_inside_polygon(p, &b))
    {
        return Ok(true);
    }
    if edge_midpoints(&b)
        .iter()
        .any(|&p| point_strictly_inside_polygon(p, &a))
    {
        return Ok(true);
    }

    // Coincident/equal polygons have positive overlapping area even though
    // every vertex and edge lies exactly on the other polygon's boundary.
    // They would otherwise slip through as "touching only".
    if polygons_have_same_boundary_coverage(&a, &b) {
        return Ok(true);
    }

    Ok(false)
}

fn polygons_have_same_boundary_coverage(a: &[Point], b: &[Point]) -> bool {
    (polygon_area(a).abs() - polygon_area(b).abs()).abs() <= EPS
        && a.iter().all(|&p| point_on_polygon_boundary(p, b))
        && b.iter().all(|&p| point_on_polygon_boundary(p, a))
}

/// Check whether `item_pts` is fully within the polygon defined by `sheet_pts`.
///
/// Returns `Ok(true)` if all item vertices are inside-or-on the sheet polygon and no item edge
/// properly crosses any sheet edge (touching the boundary counts as within — NoCollision).
/// Returns `Ok(false)` if any vertex is outside or any edge properly crosses the boundary.
/// Returns `Err` if either polygon is degenerate.
pub(crate) fn polygon_within_sheet_pts(item_pts: &[Point], sheet_pts: &[Point]) -> Result<bool, &'static str> {
    let item = clean_valid_polygon(item_pts)?;
    let sheet = clean_valid_polygon(sheet_pts)?;

    for &p in &item {
        if !point_inside_or_on_polygon(p, &sheet) {
            return Ok(false);
        }
    }

    for i in 0..item.len() {
        let a0 = item[i];
        let a1 = item[(i + 1) % item.len()];
        for j in 0..sheet.len() {
            let b0 = sheet[j];
            let b1 = sheet[(j + 1) % sheet.len()];
            if segments_properly_intersect(a0, a1, b0, b1) {
                return Ok(false);
            }
        }
    }

    Ok(true)
}

fn polygon_within_sheet(points: &[Point], sheet: &SheetShape) -> Result<bool, &'static str> {
    let item = clean_valid_polygon(points)?;
    let sheet_poly = sheet_polygon_points(sheet);
    let sheet_poly = clean_valid_polygon(&sheet_poly)?;

    for &p in &item {
        if !point_inside_or_on_polygon(p, &sheet_poly) {
            return Ok(false);
        }
    }

    for i in 0..item.len() {
        let a0 = item[i];
        let a1 = item[(i + 1) % item.len()];
        for j in 0..sheet_poly.len() {
            let b0 = sheet_poly[j];
            let b1 = sheet_poly[(j + 1) % sheet_poly.len()];
            if segments_properly_intersect(a0, a1, b0, b1) {
                return Ok(false);
            }
        }
    }

    Ok(true)
}

fn sheet_polygon_points(sheet: &SheetShape) -> Vec<Point> {
    if sheet.has_irregular_outer {
        sheet.outer_vertices.clone()
    } else {
        vec![
            Point { x: sheet.min_x, y: sheet.min_y },
            Point { x: sheet.max_x, y: sheet.min_y },
            Point { x: sheet.max_x, y: sheet.max_y },
            Point { x: sheet.min_x, y: sheet.max_y },
        ]
    }
}

fn points_equal(a: Point, b: Point) -> bool {
    (a.x - b.x).abs() <= EPS && (a.y - b.y).abs() <= EPS
}

fn orient(a: Point, b: Point, c: Point) -> f64 {
    (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)
}

fn point_on_segment(p: Point, a: Point, b: Point) -> bool {
    orient(a, b, p).abs() <= EPS
        && p.x >= a.x.min(b.x) - EPS
        && p.x <= a.x.max(b.x) + EPS
        && p.y >= a.y.min(b.y) - EPS
        && p.y <= a.y.max(b.y) + EPS
}

fn segments_properly_intersect(a0: Point, a1: Point, b0: Point, b1: Point) -> bool {
    let o1 = orient(a0, a1, b0);
    let o2 = orient(a0, a1, b1);
    let o3 = orient(b0, b1, a0);
    let o4 = orient(b0, b1, a1);

    o1 * o2 < -EPS && o3 * o4 < -EPS
}

fn point_inside_or_on_polygon(p: Point, poly: &[Point]) -> bool {
    point_on_polygon_boundary(p, poly) || point_strictly_inside_polygon(p, poly)
}

fn point_on_polygon_boundary(p: Point, poly: &[Point]) -> bool {
    (0..poly.len()).any(|i| point_on_segment(p, poly[i], poly[(i + 1) % poly.len()]))
}

fn point_strictly_inside_polygon(p: Point, poly: &[Point]) -> bool {
    if point_on_polygon_boundary(p, poly) {
        return false;
    }
    let mut inside = false;
    let n = poly.len();
    let mut j = n - 1;
    for i in 0..n {
        let pi = poly[i];
        let pj = poly[j];
        let intersects = (pi.y > p.y) != (pj.y > p.y)
            && p.x < (pj.x - pi.x) * (p.y - pi.y) / (pj.y - pi.y) + pi.x;
        if intersects {
            inside = !inside;
        }
        j = i;
    }
    inside
}

fn edge_midpoints(poly: &[Point]) -> Vec<Point> {
    (0..poly.len())
        .map(|i| {
            let a = poly[i];
            let b = poly[(i + 1) % poly.len()];
            Point {
                x: (a.x + b.x) * 0.5,
                y: (a.y + b.y) * 0.5,
            }
        })
        .collect()
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::io::Placement;
    use crate::sheet::{expand_sheets, Stock};

    fn make_part(id: &str, w: f64, h: f64) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: 1,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: None,
            prepared_outer_points: None,
            rotation_policy: None,
        }
    }

    fn make_part_with_polygon(id: &str, w: f64, h: f64, outer: serde_json::Value) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: 1,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: Some(outer),
            prepared_outer_points: None,
            rotation_policy: None,
        }
    }

    fn pl(part_id: &str, sheet: usize, x: f64, y: f64) -> Placement {
        pl_rot(part_id, sheet, x, y, 0.0)
    }

    fn pl_rot(part_id: &str, sheet: usize, x: f64, y: f64, rotation_deg: f64) -> Placement {
        Placement {
            instance_id: format!("{}__{:04}", part_id, 1),
            part_id: part_id.to_string(),
            sheet_index: sheet,
            x,
            y,
            rotation_deg,
        }
    }

    fn rect_sheet(w: f64, h: f64) -> Vec<crate::sheet::SheetShape> {
        let stock = Stock {
            id: "R".to_string(),
            quantity: 1,
            width: Some(w),
            height: Some(h),
            outer_points: None,
            holes_points: None,
            cost_per_use: None,
        };
        expand_sheets(&[stock]).expect("expand_sheets")
    }

    fn l_shape_sheet() -> Vec<crate::sheet::SheetShape> {
        use crate::geometry::PointInput;
        let stock = Stock {
            id: "L".to_string(),
            quantity: 1,
            width: None,
            height: None,
            outer_points: Some(vec![
                PointInput::Pair([0.0, 0.0]),
                PointInput::Pair([100.0, 0.0]),
                PointInput::Pair([100.0, 50.0]),
                PointInput::Pair([50.0, 50.0]),
                PointInput::Pair([50.0, 100.0]),
                PointInput::Pair([0.0, 100.0]),
            ]),
            holes_points: None,
            cost_per_use: None,
        };
        expand_sheets(&[stock]).expect("expand_sheets")
    }

    // -------------------------------------------------------------------------
    // bbox_backend_matches_existing_rect_overlap_behavior
    // -------------------------------------------------------------------------

    #[test]
    fn bbox_backend_matches_existing_rect_overlap_behavior() {
        let backend = BboxCollisionBackend;
        let part = make_part("A", 30.0, 30.0);

        // Two overlapping placements on same sheet.
        let p1 = pl("A", 0, 0.0, 0.0);
        let p2 = pl("A", 0, 15.0, 15.0); // overlaps p1 (30x30 bbox)
        assert!(
            backend.placement_overlaps(&p1, &part, &p2, &part).is_collision(),
            "bbox backend: overlapping rects → Collision"
        );

        // Two adjacent non-overlapping placements.
        let p3 = pl("A", 0, 30.0, 0.0); // adjacent, touching boundary
        assert!(
            backend.placement_overlaps(&p1, &part, &p3, &part).is_no_collision(),
            "bbox backend: adjacent (touching) rects → NoCollision"
        );

        // Different sheets → no collision.
        let p4 = pl("A", 1, 0.0, 0.0);
        assert!(
            backend.placement_overlaps(&p1, &part, &p4, &part).is_no_collision(),
            "bbox backend: different sheets → NoCollision"
        );
    }

    // -------------------------------------------------------------------------
    // find_violations_default_matches_pre_q08_behavior
    // -------------------------------------------------------------------------

    #[test]
    fn find_violations_default_matches_pre_q08_behavior() {
        use crate::optimizer::repair::{find_violations, find_violations_with_backend};

        let parts = vec![make_part("A", 30.0, 30.0)];
        let sheets = rect_sheet(100.0, 100.0);

        // Clean layout: no violations expected.
        let placements = vec![
            Placement { instance_id: "A__0001".into(), part_id: "A".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 },
            Placement { instance_id: "A__0002".into(), part_id: "A".into(), sheet_index: 0, x: 30.0, y: 0.0, rotation_deg: 0.0 },
        ];

        let v_old = find_violations(&placements, &parts, &sheets);
        let backend = BboxCollisionBackend;
        let v_new = find_violations_with_backend(&placements, &parts, &sheets, &backend);
        assert_eq!(v_old.len(), v_new.len(), "clean layout: old and new must agree");

        // Layout with overlap.
        let placements_overlap = vec![
            Placement { instance_id: "A__0001".into(), part_id: "A".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 },
            Placement { instance_id: "A__0002".into(), part_id: "A".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 },
        ];
        let v_old2 = find_violations(&placements_overlap, &parts, &sheets);
        let v_new2 = find_violations_with_backend(&placements_overlap, &parts, &sheets, &backend);
        assert_eq!(v_old2.len(), v_new2.len(), "overlap layout: old and new must agree");
        assert_eq!(v_old2.len(), 1, "overlap layout must produce exactly 1 violation");
    }

    // -------------------------------------------------------------------------
    // jagua_or_cde_backend_detects_polygon_overlap
    // -------------------------------------------------------------------------

    #[test]
    fn jagua_or_cde_backend_detects_polygon_overlap() {
        // Two L-shapes placed such that they actually overlap.
        // L-shape: [(0,0),(40,0),(40,20),(20,20),(20,40),(0,40)]
        let l_json = serde_json::json!([
            [0.0, 0.0], [40.0, 0.0], [40.0, 20.0],
            [20.0, 20.0], [20.0, 40.0], [0.0, 40.0]
        ]);

        let part_a = make_part_with_polygon("L", 40.0, 40.0, l_json.clone());
        let part_b = make_part_with_polygon("L2", 40.0, 40.0, l_json);

        // Place B overlapping A's bottom-left region.
        let p_a = Placement { instance_id: "L__0001".into(), part_id: "L".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 };
        let p_b = Placement { instance_id: "L2__0001".into(), part_id: "L2".into(), sheet_index: 0, x: 5.0, y: 5.0, rotation_deg: 0.0 };

        let backend = JaguaPolygonExactBackend;
        let result = backend.placement_overlaps(&p_a, &part_a, &p_b, &part_b);
        assert!(
            result.is_collision(),
            "JaguaPolygonExactBackend must detect overlap when L-shapes share area: {:?}",
            result
        );
    }

    // -------------------------------------------------------------------------
    // jagua_or_cde_backend_rejects_l_shape_notch_or_irregular_outside
    // (also serves as the smoke/benchmark matrix gate)
    // -------------------------------------------------------------------------

    #[test]
    fn jagua_or_cde_backend_rejects_l_shape_notch_or_irregular_outside() {
        // L-shaped item A: [(0,0),(40,0),(40,20),(20,20),(20,40),(0,40)]
        // Bounding box: (0,0,40,40).
        // Notch (missing region): (20,20,40,40).
        let l_json = serde_json::json!([
            [0.0, 0.0], [40.0, 0.0], [40.0, 20.0],
            [20.0, 20.0], [20.0, 40.0], [0.0, 40.0]
        ]);
        let part_a = make_part_with_polygon("L", 40.0, 40.0, l_json);

        // Rect item B: 15×15, placed at (22,22) — entirely inside A's notch.
        let part_b = make_part("B", 15.0, 15.0);

        let p_a = Placement { instance_id: "L__0001".into(), part_id: "L".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 };
        let p_b = Placement { instance_id: "B__0001".into(), part_id: "B".into(), sheet_index: 0, x: 22.0, y: 22.0, rotation_deg: 0.0 };

        // --- Smoke matrix ---

        // BboxCollisionBackend: A bbox (0,0,40,40) overlaps B bbox (22,22,37,37) → Collision (false positive).
        let bbox_backend = BboxCollisionBackend;
        let bbox_result = bbox_backend.placement_overlaps(&p_a, &part_a, &p_b, &part_b);
        assert!(
            bbox_result.is_collision(),
            "BboxCollisionBackend must report Collision for L-shape bbox overlap (expected false positive)"
        );

        // JaguaPolygonExactBackend: B is in the notch → no actual polygon overlap → NoCollision.
        let exact_backend = JaguaPolygonExactBackend;
        let exact_result = exact_backend.placement_overlaps(&p_a, &part_a, &p_b, &part_b);
        assert!(
            exact_result.is_no_collision(),
            "JaguaPolygonExactBackend must report NoCollision when B is in L-shape notch: {:?}",
            exact_result
        );

        // This proves exact backend is NOT just a renamed bbox backend.
        assert_ne!(
            bbox_result, exact_result,
            "bbox and exact backends must disagree for L-shape notch fixture"
        );
    }

    // -------------------------------------------------------------------------
    // geometry_preprocessing_rejects_invalid_polygon — tested in geometry_preprocessing.rs
    // geometry_preprocessing_dedupes_consecutive_duplicate_points — tested in geometry_preprocessing.rs
    // -------------------------------------------------------------------------

    // -------------------------------------------------------------------------
    // backend_does_not_silently_fallback_to_bbox_when_exact_unavailable
    // -------------------------------------------------------------------------

    #[test]
    fn backend_does_not_silently_fallback_to_bbox_when_exact_unavailable() {
        // CdeCollisionBackend performs genuine polygon queries, not bbox fallback.
        // Proof via L-shape notch fixture: BboxCollisionBackend gives Collision
        // (false positive) but CdeCollisionBackend gives NoCollision.
        let l_json = serde_json::json!([
            [0.0, 0.0], [40.0, 0.0], [40.0, 20.0],
            [20.0, 20.0], [20.0, 40.0], [0.0, 40.0]
        ]);
        let l_part = make_part_with_polygon("L", 40.0, 40.0, l_json);
        let small_part = make_part("B", 15.0, 15.0);
        let p_l = pl("L", 0, 0.0, 0.0);
        let p_small = pl("B", 0, 22.0, 22.0); // inside L-shape notch

        let bbox_result = BboxCollisionBackend.placement_overlaps(&p_l, &l_part, &p_small, &small_part);
        let cde_result = CdeCollisionBackend.placement_overlaps(&p_l, &l_part, &p_small, &small_part);

        assert!(bbox_result.is_collision(), "Bbox must give false positive for L-notch fixture");
        assert!(
            cde_result.is_no_collision(),
            "CDE must not fallback to bbox; expected NoCollision for notch fixture, got {:?}",
            cde_result
        );
        assert_ne!(bbox_result, cde_result, "CDE and bbox must disagree for notch fixture");
    }

    // -------------------------------------------------------------------------
    // Additional coverage: boundary checks
    // -------------------------------------------------------------------------

    #[test]
    fn bbox_backend_boundary_check_rect_sheet() {
        let backend = BboxCollisionBackend;
        let part = make_part("A", 30.0, 30.0);
        let sheets = rect_sheet(100.0, 100.0);

        let inside = pl("A", 0, 0.0, 0.0);
        assert!(backend.placement_within_sheet(&inside, &part, &sheets[0]).is_no_collision());

        let outside = Placement { instance_id: "A__0001".into(), part_id: "A".into(), sheet_index: 0, x: 90.0, y: 90.0, rotation_deg: 0.0 };
        assert!(backend.placement_within_sheet(&outside, &part, &sheets[0]).is_collision());
    }

    #[test]
    fn exact_backend_boundary_check_l_shape_sheet_notch() {
        // An item placed in the notch of an L-shaped sheet must be rejected.
        let backend = JaguaPolygonExactBackend;
        let part = make_part("A", 20.0, 20.0);
        let sheets = l_shape_sheet();

        // Inside the L region: (10,10,30,30) → valid.
        let inside = pl("A", 0, 10.0, 10.0);
        assert!(backend.placement_within_sheet(&inside, &part, &sheets[0]).is_no_collision(),
            "item inside L-shape region must be valid");

        // In the notch: (60,60,80,80) → invalid.
        let notch = Placement { instance_id: "A__0001".into(), part_id: "A".into(), sheet_index: 0, x: 60.0, y: 60.0, rotation_deg: 0.0 };
        assert!(backend.placement_within_sheet(&notch, &part, &sheets[0]).is_collision(),
            "item in L-shape notch must be a boundary violation");
    }

    #[test]
    fn exact_backend_malformed_outer_points_returns_unsupported_not_bbox_fallback() {
        let backend = JaguaPolygonExactBackend;
        let malformed = make_part_with_polygon("BAD", 40.0, 40.0, serde_json::json!([["x", 0.0]]));
        let rect = make_part("R", 10.0, 10.0);
        let p_bad = pl("BAD", 0, 0.0, 0.0);
        let p_rect = pl("R", 0, 1.0, 1.0);

        let result = backend.placement_overlaps(&p_bad, &malformed, &p_rect, &rect);
        assert!(result.is_unsupported(), "malformed polygon must be Unsupported: {:?}", result);
    }

    #[test]
    fn exact_backend_degenerate_polygon_returns_unsupported_not_no_collision() {
        let backend = JaguaPolygonExactBackend;
        let degenerate = make_part_with_polygon(
            "DEG",
            40.0,
            40.0,
            serde_json::json!([[0.0, 0.0], [10.0, 0.0], [20.0, 0.0]]),
        );
        let rect = make_part("R", 10.0, 10.0);
        let result = backend.placement_overlaps(&pl("DEG", 0, 0.0, 0.0), &degenerate, &pl("R", 0, 1.0, 1.0), &rect);
        assert!(result.is_unsupported(), "degenerate polygon must be Unsupported: {:?}", result);
    }

    #[test]
    fn exact_backend_rotated_rect_vs_rect_uses_true_rotated_geometry_not_aabb() {
        let backend = JaguaPolygonExactBackend;
        let bbox_backend = BboxCollisionBackend;
        let long = make_part("A", 100.0, 20.0);
        let small = make_part("B", 5.0, 5.0);
        let rotated = pl_rot("A", 0, 0.0, 0.0, 45.0);
        let in_rotated_aabb_corner = pl("B", 0, -10.0, 70.0);

        assert!(bbox_backend.placement_overlaps(&rotated, &long, &in_rotated_aabb_corner, &small).is_collision());
        assert!(backend.placement_overlaps(&rotated, &long, &in_rotated_aabb_corner, &small).is_no_collision());
    }

    #[test]
    fn exact_backend_rotated_rect_vs_irregular_uses_true_rotated_geometry_not_aabb() {
        let backend = JaguaPolygonExactBackend;
        let bbox_backend = BboxCollisionBackend;
        let long = make_part("A", 100.0, 20.0);
        let square = make_part_with_polygon(
            "P",
            5.0,
            5.0,
            serde_json::json!([[0.0, 0.0], [5.0, 0.0], [5.0, 5.0], [0.0, 5.0]]),
        );
        let rotated = pl_rot("A", 0, 0.0, 0.0, 45.0);
        let in_rotated_aabb_corner = pl("P", 0, -10.0, 70.0);

        assert!(bbox_backend.placement_overlaps(&rotated, &long, &in_rotated_aabb_corner, &square).is_collision());
        assert!(backend.placement_overlaps(&rotated, &long, &in_rotated_aabb_corner, &square).is_no_collision());
    }

    #[test]
    fn exact_backend_rect_boundary_check_is_rotation_aware() {
        let backend = JaguaPolygonExactBackend;
        let part = make_part("A", 100.0, 20.0);
        let sheets = rect_sheet(90.0, 90.0);
        let placement = pl_rot("A", 0, std::f64::consts::SQRT_2 * 10.0, 0.0, 45.0);

        let result = backend.placement_within_sheet(&placement, &part, &sheets[0]);
        assert!(result.is_no_collision(), "45-degree 100x20 rect should fit in 90x90: {:?}", result);
    }

    #[test]
    fn touching_rect_edges_are_not_collision() {
        let backend = JaguaPolygonExactBackend;
        let part = make_part("A", 10.0, 10.0);
        assert!(
            backend
                .placement_overlaps(&pl("A", 0, 0.0, 0.0), &part, &pl("A", 0, 10.0, 0.0), &part)
                .is_no_collision()
        );
    }

    #[test]
    fn touching_rect_corners_are_not_collision() {
        let backend = JaguaPolygonExactBackend;
        let part = make_part("A", 10.0, 10.0);
        assert!(
            backend
                .placement_overlaps(&pl("A", 0, 0.0, 0.0), &part, &pl("A", 0, 10.0, 10.0), &part)
                .is_no_collision()
        );
    }

    #[test]
    fn positive_area_overlap_is_collision() {
        let backend = JaguaPolygonExactBackend;
        let part = make_part("A", 10.0, 10.0);
        assert!(
            backend
                .placement_overlaps(&pl("A", 0, 0.0, 0.0), &part, &pl("A", 0, 9.999, 0.0), &part)
                .is_collision()
        );
    }

    #[test]
    fn identical_rect_placements_are_collision_for_exact_backend() {
        let backend = JaguaPolygonExactBackend;
        let part = make_part("A", 10.0, 10.0);
        assert!(
            backend
                .placement_overlaps(&pl("A", 0, 0.0, 0.0), &part, &pl("A", 0, 0.0, 0.0), &part)
                .is_collision(),
            "exact backend must reject duplicate same-area placements, not classify them as touching"
        );
    }

    #[test]
    fn identical_irregular_polygon_placements_are_collision_for_exact_backend() {
        let backend = JaguaPolygonExactBackend;
        let poly = serde_json::json!([[0.0, 0.0], [20.0, 0.0], [20.0, 10.0], [0.0, 10.0]]);
        let part = make_part_with_polygon("P", 20.0, 10.0, poly);
        assert!(
            backend
                .placement_overlaps(&pl("P", 0, 5.0, 7.0), &part, &pl("P", 0, 5.0, 7.0), &part)
                .is_collision(),
            "exact backend must reject duplicate coincident irregular polygons"
        );
    }

    #[test]
    fn exact_backend_validation_rejects_duplicate_rect_layout() {
        use crate::io::CollisionBackendKind;
        use crate::optimizer::repair::validate_placements_for_backend;

        let part = make_part("A", 10.0, 10.0);
        let placements = vec![pl("A", 0, 0.0, 0.0), pl("A", 0, 0.0, 0.0)];
        let sheets = rect_sheet(100.0, 100.0);

        let violations = validate_placements_for_backend(
            &placements,
            &[part],
            &sheets,
            &CollisionBackendKind::JaguaPolygonExact,
        );
        assert!(
            !violations.is_empty(),
            "backend-aware validation must reject duplicate rect placements"
        );
    }

    #[test]
    fn invalid_polygon_does_not_become_no_collision() {
        let backend = JaguaPolygonExactBackend;
        let invalid = make_part_with_polygon("BAD", 40.0, 40.0, serde_json::json!("not-points"));
        let rect = make_part("R", 10.0, 10.0);
        let result = backend.placement_overlaps(&pl("BAD", 0, 100.0, 100.0), &invalid, &pl("R", 0, 0.0, 0.0), &rect);
        assert!(result.is_unsupported());
        assert!(!result.is_no_collision());
    }

    #[test]
    fn bbox_backend_still_matches_existing_behavior() {
        let backend = BboxCollisionBackend;
        let part = make_part("A", 10.0, 10.0);
        assert!(backend.placement_overlaps(&pl("A", 0, 0.0, 0.0), &part, &pl("A", 0, 10.0, 0.0), &part).is_no_collision());
        assert!(backend.placement_overlaps(&pl("A", 0, 0.0, 0.0), &part, &pl("A", 0, 9.0, 0.0), &part).is_collision());
    }

    #[test]
    fn cde_backend_returns_unsupported_for_invalid_polygon() {
        // CdeCollisionBackend must return Unsupported for invalid geometry,
        // not silently return NoCollision or delegate to bbox.
        let backend = CdeCollisionBackend;
        let invalid = make_part_with_polygon("BAD", 40.0, 40.0, serde_json::json!("not-points"));
        let rect = make_part("R", 10.0, 10.0);
        let result = backend.placement_overlaps(
            &pl("BAD", 0, 0.0, 0.0), &invalid,
            &pl("R",   0, 1.0, 1.0), &rect,
        );
        assert!(result.is_unsupported(), "invalid polygon must be Unsupported: {:?}", result);
        assert!(!result.is_no_collision());
        assert!(!result.is_collision());
    }

    // -----------------------------------------------------------------------
    // SGH-Q18A: CDE observability counter tests
    // -----------------------------------------------------------------------

    #[test]
    fn cde_observability_pair_query_increments_pair_and_total() {
        crate::optimizer::cde_observability::reset();
        let part = make_part("A", 20.0, 20.0);
        let p1 = pl("A", 0, 0.0, 0.0);
        let p2 = pl("A", 0, 10.0, 10.0); // overlap
        CdeCollisionBackend.placement_overlaps(&p1, &part, &p2, &part);
        let snap = crate::optimizer::cde_observability::snapshot();
        assert_eq!(snap.pair_queries, 1, "one pair query must be counted");
        assert_eq!(snap.boundary_queries, 0);
        assert_eq!(snap.total_queries, 1);
    }

    #[test]
    fn cde_observability_boundary_query_increments_boundary_and_total() {
        crate::optimizer::cde_observability::reset();
        let part = make_part("A", 20.0, 20.0);
        let sheets = {
            let stock = Stock { id: "R".into(), quantity: 1, width: Some(100.0), height: Some(100.0),
                outer_points: None, holes_points: None, cost_per_use: None };
            expand_sheets(&[stock]).expect("sheets")
        };
        CdeCollisionBackend.placement_within_sheet(&pl("A", 0, 10.0, 10.0), &part, &sheets[0]);
        let snap = crate::optimizer::cde_observability::snapshot();
        assert_eq!(snap.boundary_queries, 1, "one boundary query must be counted");
        assert_eq!(snap.pair_queries, 0);
        assert_eq!(snap.total_queries, 1);
    }

    #[test]
    fn cde_observability_engine_builds_counted_for_pair_query() {
        crate::optimizer::cde_observability::reset();
        // SGH-Q23: use an OVERLAPPING pair so the query reaches the CDEngine.
        // AABB-separated pairs are now resolved by broad-phase without an engine
        // build (see cde_q23_broadphase_* tests); this test validates that a pair
        // that survives broad-phase does build an engine.
        let part = make_part("A", 20.0, 20.0);
        let p1 = pl("A", 0, 0.0, 0.0);
        let p2 = pl("A", 0, 10.0, 10.0); // 10×10 overlap → not broad-phase prunable
        CdeCollisionBackend.placement_overlaps(&p1, &part, &p2, &part);
        let snap = crate::optimizer::cde_observability::snapshot();
        assert!(snap.engine_builds >= 1, "at least one CDEngine must be built per overlapping pair query");
    }

    #[test]
    fn cde_observability_engine_builds_counted_for_boundary_query() {
        crate::optimizer::cde_observability::reset();
        let part = make_part("A", 20.0, 20.0);
        let sheets = {
            let stock = Stock { id: "R".into(), quantity: 1, width: Some(100.0), height: Some(100.0),
                outer_points: None, holes_points: None, cost_per_use: None };
            expand_sheets(&[stock]).expect("sheets")
        };
        CdeCollisionBackend.placement_within_sheet(&pl("A", 0, 10.0, 10.0), &part, &sheets[0]);
        let snap = crate::optimizer::cde_observability::snapshot();
        assert!(snap.engine_builds >= 1, "at least one CDEngine must be built per boundary query");
    }

    #[test]
    fn cde_observability_prepare_failure_counted_for_invalid_polygon() {
        crate::optimizer::cde_observability::reset();
        let invalid = make_part_with_polygon("BAD", 40.0, 40.0, serde_json::json!("not-points"));
        let rect = make_part("R", 10.0, 10.0);
        CdeCollisionBackend.placement_overlaps(
            &pl("BAD", 0, 0.0, 0.0), &invalid,
            &pl("R",   0, 1.0, 1.0), &rect,
        );
        let snap = crate::optimizer::cde_observability::snapshot();
        assert!(snap.prepare_failures >= 1, "prepare_failure must be counted for invalid polygon");
        assert!(snap.unsupported_results >= 1, "unsupported_results must be counted for prepare failure");
    }

    #[test]
    fn cde_observability_cross_sheet_skip_counted() {
        crate::optimizer::cde_observability::reset();
        let part = make_part("A", 20.0, 20.0);
        let p_sheet0 = pl("A", 0, 0.0, 0.0);
        let p_sheet1 = Placement { instance_id: "A__0002".into(), part_id: "A".into(),
            sheet_index: 1, x: 0.0, y: 0.0, rotation_deg: 0.0 };
        let result = CdeCollisionBackend.placement_overlaps(&p_sheet0, &part, &p_sheet1, &part);
        let snap = crate::optimizer::cde_observability::snapshot();
        assert!(result.is_no_collision(), "cross-sheet items must be NoCollision");
        assert_eq!(snap.cross_sheet_skipped, 1, "cross-sheet skip must be counted");
        assert_eq!(snap.pair_queries, 0, "cross-sheet skip must not count as pair query");
    }

    #[test]
    fn bbox_backend_does_not_increment_cde_observability_counters() {
        crate::optimizer::cde_observability::reset();
        let part = make_part("A", 20.0, 20.0);
        let p1 = pl("A", 0, 0.0, 0.0);
        let p2 = pl("A", 0, 10.0, 10.0);
        BboxCollisionBackend.placement_overlaps(&p1, &part, &p2, &part);
        let snap = crate::optimizer::cde_observability::snapshot();
        assert_eq!(snap.pair_queries, 0, "bbox backend must not increment CDE pair counter");
        assert_eq!(snap.total_queries, 0, "bbox backend must not increment CDE total counter");
        assert_eq!(snap.engine_builds, 0, "bbox backend must not increment CDE engine_builds");
    }
}
