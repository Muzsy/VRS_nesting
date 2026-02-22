use i_overlay::{
    core::fill_rule::FillRule,
    float::simplify::SimplifyShape,
    mesh::{
        outline::offset::OutlineOffset,
        style::{LineJoin, OutlineStyle},
    },
};

use crate::geometry::{
    scale::{i64_to_mm, mm_to_i64},
    types::{PartGeometry, Point64, Polygon64},
};

/// Errors that can occur during polygon offsetting.
#[derive(Debug)]
pub enum OffsetError {
    /// A hole polygon collapsed to an empty polygon after deflation.
    HoleCollapsed { hole_index: usize },
    /// The result polygon is self-intersecting (detected post-offset).
    SelfIntersection,
    /// An error occurred in the underlying offset library.
    ClipperError(String),
}

/// Internal 2-D point type used when communicating with i_overlay (mm coordinates).
type MmPt = [f64; 2];

/// A shape in i_overlay format: Vec of paths (first = outer CCW, rest = holes CW).
type MmShape = Vec<Vec<MmPt>>;

// ---------------------------------------------------------------------------
// Winding-direction helpers
// ---------------------------------------------------------------------------

/// Shoelace signed area (positive = CCW in standard math orientation).
fn signed_area_2d(pts: &[MmPt]) -> f64 {
    let n = pts.len();
    if n < 3 {
        return 0.0;
    }
    let mut area = 0.0_f64;
    for i in 0..n {
        let [x0, y0] = pts[i];
        let [x1, y1] = pts[(i + 1) % n];
        area += x0 * y1 - x1 * y0;
    }
    area * 0.5
}

/// Ensure points are in counter-clockwise (CCW) order.
/// i_overlay requires outer boundaries to be CCW.
fn ensure_ccw(mut pts: Vec<MmPt>) -> Vec<MmPt> {
    if signed_area_2d(&pts) < 0.0 {
        pts.reverse();
    }
    pts
}

/// Ensure points are in clockwise (CW) order.
/// i_overlay requires holes to be CW.
fn ensure_cw(mut pts: Vec<MmPt>) -> Vec<MmPt> {
    if signed_area_2d(&pts) > 0.0 {
        pts.reverse();
    }
    pts
}

// ---------------------------------------------------------------------------
// Coordinate conversion helpers
// ---------------------------------------------------------------------------

fn pts_to_mm(pts: &[Point64]) -> Vec<MmPt> {
    pts.iter()
        .map(|p| [i64_to_mm(p.x), i64_to_mm(p.y)])
        .collect()
}

fn mm_to_pts(path: &[MmPt]) -> Vec<Point64> {
    path.iter()
        .map(|&[x, y]| Point64 {
            x: mm_to_i64(x),
            y: mm_to_i64(y),
        })
        .collect()
}

// ---------------------------------------------------------------------------
// Core offset operation
// ---------------------------------------------------------------------------

/// Apply an outline offset to a shape (outer CCW + holes CW).
///
/// `delta_mm` is applied uniformly:
///   positive → outer expands outward, holes contract inward.
///   negative → outer contracts inward.
///
/// Uses `LineJoin::Round` for corner rounding.
fn do_offset(shape: MmShape, delta_mm: f64) -> Result<MmShape, OffsetError> {
    let style: OutlineStyle<f64> =
        OutlineStyle::new(delta_mm).line_join(LineJoin::Round(0.1_f64));

    let result = shape.outline(&style);

    result
        .into_iter()
        .next()
        .ok_or_else(|| OffsetError::ClipperError("outline produced empty result".into()))
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/// Inflate the outer contour of a polygon outward by `delta_mm`.
/// Holes are simultaneously deflated inward by the same delta.
///
/// Winding direction is enforced before the call:
///   outer → CCW, holes → CW (i_overlay requirement).
pub fn inflate_outer(polygon: &Polygon64, delta_mm: f64) -> Result<Polygon64, OffsetError> {
    let outer = ensure_ccw(pts_to_mm(&polygon.outer));
    let mut shape: MmShape = vec![outer];
    for hole in &polygon.holes {
        shape.push(ensure_cw(pts_to_mm(hole)));
    }

    let result_shape = do_offset(shape, delta_mm)?;

    let mut paths = result_shape.into_iter();
    let outer_pts = paths
        .next()
        .ok_or_else(|| OffsetError::ClipperError("no outer contour in result".into()))?;
    let outer = mm_to_pts(&outer_pts);
    let holes: Vec<Vec<Point64>> = paths.map(|h| mm_to_pts(&h)).collect();

    Ok(Polygon64 { outer, holes })
}

/// Deflate a single hole polygon inward by `delta_mm`.
///
/// The hole is treated as a standalone outer boundary (CCW) and contracted
/// by applying a negative offset (`-delta_mm`).
/// Returns `HoleCollapsed` if the result is empty.
pub fn deflate_hole(hole: &[Point64], delta_mm: f64) -> Result<Vec<Point64>, OffsetError> {
    if hole.is_empty() {
        return Err(OffsetError::HoleCollapsed { hole_index: 0 });
    }
    // Treat the hole as a standalone CCW outer boundary and shrink it.
    let outer = ensure_ccw(pts_to_mm(hole));
    let shape: MmShape = vec![outer];

    let result_shape = do_offset(shape, -delta_mm)
        .map_err(|_| OffsetError::HoleCollapsed { hole_index: 0 })?;

    let outer_pts = result_shape
        .into_iter()
        .next()
        .ok_or(OffsetError::HoleCollapsed { hole_index: 0 })?;

    if outer_pts.is_empty() {
        return Err(OffsetError::HoleCollapsed { hole_index: 0 });
    }
    Ok(mm_to_pts(&outer_pts))
}

/// Inflate the full geometry of a part:
///   - outer contour: expands outward by `delta_mm`
///   - every hole: contracts inward by `delta_mm`
///
/// **Preprocessing:** `simplify_shape` is applied before the offset to
/// remove self-intersections and degenerate vertices that may come from
/// DXF import. Without simplification, i_overlay may produce silently
/// incorrect results for invalid polygons.
///
/// **Winding direction** is enforced: outer CCW, holes CW.
///
/// Returns `HoleCollapsed { hole_index }` if a hole disappears after offset.
pub fn inflate_part(geom: &PartGeometry, delta_mm: f64) -> Result<PartGeometry, OffsetError> {
    // Build shape with correct winding directions.
    let outer = ensure_ccw(pts_to_mm(&geom.polygon.outer));
    let mut shape: MmShape = vec![outer];
    for hole in &geom.polygon.holes {
        shape.push(ensure_cw(pts_to_mm(hole)));
    }

    // Simplify before offset: removes degenerate / self-intersecting geometry.
    let simplified = shape.simplify_shape(FillRule::NonZero);
    let shape_to_offset: MmShape = simplified.into_iter().next().unwrap_or(shape);

    let result_shape = do_offset(shape_to_offset, delta_mm)?;

    let mut paths = result_shape.into_iter();
    let outer_pts = paths
        .next()
        .ok_or_else(|| OffsetError::ClipperError("no outer contour in result".into()))?;
    let outer = mm_to_pts(&outer_pts);

    let mut holes = Vec::new();
    for (idx, hole_path) in paths.enumerate() {
        if hole_path.is_empty() {
            return Err(OffsetError::HoleCollapsed { hole_index: idx });
        }
        holes.push(mm_to_pts(&hole_path));
    }

    Ok(PartGeometry {
        id: geom.id.clone(),
        polygon: Polygon64 { outer, holes },
    })
}

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::geometry::{
        scale::mm_to_i64,
        types::{PartGeometry, Point64, Polygon64},
    };

    /// Build a simple axis-aligned rectangle as a Vec<Point64>.
    fn rect_pts(w_mm: f64, h_mm: f64) -> Vec<Point64> {
        vec![
            Point64 { x: mm_to_i64(0.0), y: mm_to_i64(0.0) },
            Point64 { x: mm_to_i64(w_mm), y: mm_to_i64(0.0) },
            Point64 { x: mm_to_i64(w_mm), y: mm_to_i64(h_mm) },
            Point64 { x: mm_to_i64(0.0), y: mm_to_i64(h_mm) },
        ]
    }

    /// Compute (width_mm, height_mm) bounding box of a Point64 slice.
    fn bbox_mm(pts: &[Point64]) -> (f64, f64) {
        let xs: Vec<f64> = pts.iter().map(|p| i64_to_mm(p.x)).collect();
        let ys: Vec<f64> = pts.iter().map(|p| i64_to_mm(p.y)).collect();
        let w = xs.iter().cloned().fold(f64::NEG_INFINITY, f64::max)
            - xs.iter().cloned().fold(f64::INFINITY, f64::min);
        let h = ys.iter().cloned().fold(f64::NEG_INFINITY, f64::max)
            - ys.iter().cloned().fold(f64::INFINITY, f64::min);
        (w, h)
    }

    /// Inflate outer: 100×200 mm rectangle, delta = 1.0 mm.
    /// Expected: bounding box >= 101.9 × 201.9 mm.
    #[test]
    fn inflate_outer_100x200_1mm() {
        let poly = Polygon64 {
            outer: rect_pts(100.0, 200.0),
            holes: vec![],
        };
        let result = inflate_outer(&poly, 1.0).expect("inflate_outer failed");
        let (w, h) = bbox_mm(&result.outer);
        assert!(w >= 101.9, "bbox width {w:.4} mm < 101.9 mm after inflate");
        assert!(h >= 201.9, "bbox height {h:.4} mm < 201.9 mm after inflate");
    }

    /// Deflate hole: 50×50 mm polygon, delta = 1.0 mm (inward).
    /// Expected: bounding box <= 48.1 × 48.1 mm.
    #[test]
    fn deflate_hole_50x50_1mm() {
        let hole = rect_pts(50.0, 50.0);
        let result = deflate_hole(&hole, 1.0).expect("deflate_hole failed");
        let (w, h) = bbox_mm(&result);
        assert!(w <= 48.1, "deflated hole bbox width {w:.4} mm > 48.1 mm");
        assert!(h <= 48.1, "deflated hole bbox height {h:.4} mm > 48.1 mm");
    }

    /// Determinism: two consecutive inflate_part calls with identical input
    /// must produce bit-identical outer contours.
    #[test]
    fn inflate_part_determinism() {
        let geom = PartGeometry {
            id: "det_test".to_string(),
            polygon: Polygon64 {
                outer: rect_pts(100.0, 200.0),
                holes: vec![],
            },
        };
        let result_a = inflate_part(&geom, 1.0).expect("inflate_part (a) failed");
        let result_b = inflate_part(&geom, 1.0).expect("inflate_part (b) failed");
        assert_eq!(
            result_a.polygon.outer,
            result_b.polygon.outer,
            "inflate_part is not deterministic: two identical calls produced different outer contours"
        );
    }
}
