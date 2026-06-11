//! SGH-Q35 — Part-part spacing final validator.
//!
//! This is a FINAL VALIDATOR + SAFETY GATE, not a spacing-aware solver geometry and
//! not a polygon offset engine. When `spacing_mm > 0`, two placements on the SAME sheet
//! must have at least `spacing_mm` Euclidean distance between their transformed outer
//! polygons. If not, the output cannot be `ok`.
//!
//! Geometry uses the SAME canonical helpers as the CDE/Sparrow placement path
//! (`extract_polygon_from_part` + `transform_polygon`). No new rotation/anchor
//! convention is invented, and the decision is NEVER bbox-based.
//!
//! `kerf_mm` is independent: it is never added to `spacing_mm` here.

use crate::geometry::Point;
use crate::optimizer::collision_backend::{
    extract_polygon_from_part, polygons_collide, transform_polygon, PolygonExtraction,
};

/// Epsilon for spacing distance comparisons (looser than geometry EPS to absorb
/// floating-point error from rotation transforms).
const SPACING_EPS: f64 = 1e-6;

/// A single part-part spacing violation between two placements on the same sheet.
#[derive(Debug, Clone, PartialEq)]
pub struct PartSpacingViolation {
    pub sheet_index: usize,
    pub a_instance_id: String,
    pub b_instance_id: String,
    pub a_part_id: String,
    pub b_part_id: String,
    pub distance_mm: f64,
    pub required_spacing_mm: f64,
}

/// Find all part-part spacing violations for `spacing_mm > 0`.
///
/// Only placements on the SAME `sheet_index` are compared. Two placements violate when
/// the minimum Euclidean distance between their transformed outer polygons is
/// `< spacing_mm` (within `SPACING_EPS`). Touching/overlap/containment → distance 0.
///
/// Local polygon source (same precedence as the CDE/Sparrow path):
///   - `prepared_outer_points` → `outer_points`;
///   - rectangle fallback `[(0,0),(w,0),(w,h),(0,h)]` ONLY when the part has no polygon;
///   - a malformed polygon is treated CONSERVATIVELY as a violation (distance 0).
pub fn find_part_spacing_violations(
    placements: &[crate::io::Placement],
    parts: &[crate::item::Part],
    spacing_mm: f64,
) -> Vec<PartSpacingViolation> {
    if spacing_mm <= 0.0 {
        return Vec::new();
    }

    // Precompute each placement's world polygon once. `None` = invalid/unbuildable.
    let world: Vec<Option<Vec<Point>>> = placements
        .iter()
        .map(|pl| world_polygon_for_placement(pl, parts))
        .collect();

    let mut violations = Vec::new();
    let n = placements.len();
    for i in 0..n {
        for j in (i + 1)..n {
            // Same-sheet only.
            if placements[i].sheet_index != placements[j].sheet_index {
                continue;
            }
            // Distance: invalid polygon on either side → conservative 0.
            let dist = match (&world[i], &world[j]) {
                (Some(a), Some(b)) => polygon_distance_mm(a, b),
                _ => 0.0,
            };
            if dist + SPACING_EPS < spacing_mm {
                violations.push(PartSpacingViolation {
                    sheet_index: placements[i].sheet_index,
                    a_instance_id: placements[i].instance_id.clone(),
                    b_instance_id: placements[j].instance_id.clone(),
                    a_part_id: placements[i].part_id.clone(),
                    b_part_id: placements[j].part_id.clone(),
                    distance_mm: dist,
                    required_spacing_mm: spacing_mm,
                });
            }
        }
    }
    violations
}

/// Count part-part spacing violation pairs. Thin wrapper over
/// [`find_part_spacing_violations`].
pub fn count_part_spacing_violations(
    placements: &[crate::io::Placement],
    parts: &[crate::item::Part],
    spacing_mm: f64,
) -> usize {
    find_part_spacing_violations(placements, parts, spacing_mm).len()
}

/// Build the world-coordinate outer polygon for a placement using the canonical
/// extraction + transform. Returns `None` when the part is missing or its polygon
/// is malformed (caller treats `None` conservatively as a violation).
fn world_polygon_for_placement(
    pl: &crate::io::Placement,
    parts: &[crate::item::Part],
) -> Option<Vec<Point>> {
    let part = parts.iter().find(|p| p.id == pl.part_id)?;
    let local: Vec<Point> = match extract_polygon_from_part(part) {
        PolygonExtraction::Valid(local) => local,
        PolygonExtraction::Absent => {
            if part.width <= 0.0 || part.height <= 0.0 {
                return None;
            }
            vec![
                Point { x: 0.0, y: 0.0 },
                Point { x: part.width, y: 0.0 },
                Point { x: part.width, y: part.height },
                Point { x: 0.0, y: part.height },
            ]
        }
        PolygonExtraction::Invalid { .. } => return None,
    };
    Some(transform_polygon(&local, pl.x, pl.y, pl.rotation_deg))
}

/// Minimum Euclidean distance between two simple polygons (world coordinates).
///
/// Returns 0.0 for overlapping/containing/coincident polygons (via `polygons_collide`)
/// and for touching edges/vertices (via the segment-segment minimum). Otherwise the
/// minimum segment-segment distance between the polygon boundaries.
pub fn polygon_distance_mm(a: &[Point], b: &[Point]) -> f64 {
    // Overlap / strict containment / coincident → distance 0.
    match polygons_collide(a, b) {
        Ok(true) => return 0.0,
        Ok(false) => {}
        Err(_) => return 0.0, // degenerate → conservative
    }
    let na = a.len();
    let nb = b.len();
    if na < 2 || nb < 2 {
        return 0.0;
    }
    let mut min_d = f64::INFINITY;
    for i in 0..na {
        let a0 = a[i];
        let a1 = a[(i + 1) % na];
        for j in 0..nb {
            let b0 = b[j];
            let b1 = b[(j + 1) % nb];
            let d = segment_segment_distance(a0, a1, b0, b1);
            if d < min_d {
                min_d = d;
            }
        }
    }
    if min_d.is_finite() {
        min_d
    } else {
        0.0
    }
}

/// Distance between two line segments. 0 if they intersect.
fn segment_segment_distance(p1: Point, p2: Point, p3: Point, p4: Point) -> f64 {
    if segments_intersect(p1, p2, p3, p4) {
        return 0.0;
    }
    let d1 = point_segment_distance(p1, p3, p4);
    let d2 = point_segment_distance(p2, p3, p4);
    let d3 = point_segment_distance(p3, p1, p2);
    let d4 = point_segment_distance(p4, p1, p2);
    d1.min(d2).min(d3).min(d4)
}

/// Shortest distance from point `p` to segment `[a, b]`.
fn point_segment_distance(p: Point, a: Point, b: Point) -> f64 {
    let dx = b.x - a.x;
    let dy = b.y - a.y;
    let len_sq = dx * dx + dy * dy;
    if len_sq <= f64::EPSILON {
        return ((p.x - a.x).powi(2) + (p.y - a.y).powi(2)).sqrt();
    }
    let t = (((p.x - a.x) * dx + (p.y - a.y) * dy) / len_sq).clamp(0.0, 1.0);
    let proj_x = a.x + t * dx;
    let proj_y = a.y + t * dy;
    ((p.x - proj_x).powi(2) + (p.y - proj_y).powi(2)).sqrt()
}

fn orient(a: Point, b: Point, c: Point) -> f64 {
    (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)
}

fn on_segment(a: Point, b: Point, p: Point) -> bool {
    p.x >= a.x.min(b.x) - SPACING_EPS
        && p.x <= a.x.max(b.x) + SPACING_EPS
        && p.y >= a.y.min(b.y) - SPACING_EPS
        && p.y <= a.y.max(b.y) + SPACING_EPS
}

/// Proper-or-touching segment intersection test (used only to short-circuit distance to 0).
fn segments_intersect(p1: Point, p2: Point, p3: Point, p4: Point) -> bool {
    let d1 = orient(p3, p4, p1);
    let d2 = orient(p3, p4, p2);
    let d3 = orient(p1, p2, p3);
    let d4 = orient(p1, p2, p4);
    if ((d1 > 0.0 && d2 < 0.0) || (d1 < 0.0 && d2 > 0.0))
        && ((d3 > 0.0 && d4 < 0.0) || (d3 < 0.0 && d4 > 0.0))
    {
        return true;
    }
    (d1.abs() <= SPACING_EPS && on_segment(p3, p4, p1))
        || (d2.abs() <= SPACING_EPS && on_segment(p3, p4, p2))
        || (d3.abs() <= SPACING_EPS && on_segment(p1, p2, p3))
        || (d4.abs() <= SPACING_EPS && on_segment(p1, p2, p4))
}
