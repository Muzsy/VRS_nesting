//! SGH-Q36 — Spacing-aware solver geometry: half-spacing outward-offset contours.
//!
//! The solver does part-part collision/search on a *spacing-expanded* contour: the
//! original outer polygon offset outward by `spacing_mm / 2`. When two such expanded
//! contours merely touch, the original contours are exactly `spacing_mm` apart.
//!
//! IMPORTANT geometry-role separation:
//!   - original geometry → sheet boundary / margin validation, output/export, final polygon;
//!   - spacing-expanded geometry → part-part collision / search ONLY.
//!
//! `spacing_mm` is NOT a sheet margin and `kerf_mm` is NOT part of the offset
//! (offset is strictly `spacing_mm / 2`).

use crate::geometry::{polygon_area, Point, EPS};

/// Which geometry a shape represents.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum SpacingGeometryRole {
    /// Boundary/container, output/export, final polygon.
    Original,
    /// Part-part collision/search only (outward offset by half-spacing).
    PartPartSpacingExpanded,
}

/// Resolved spacing offset configuration. `half_spacing_mm` is always `spacing_mm / 2`
/// — kerf is never folded in.
#[derive(Debug, Clone, PartialEq)]
pub struct SpacingOffsetConfig {
    pub spacing_mm: f64,
    pub half_spacing_mm: f64,
    pub tolerance_mm: f64,
}

impl SpacingOffsetConfig {
    /// Build from a part-spacing value. `half_spacing_mm = spacing_mm / 2`.
    pub fn from_spacing_mm(spacing_mm: f64) -> Self {
        Self {
            spacing_mm,
            half_spacing_mm: spacing_mm / 2.0,
            tolerance_mm: 1e-6,
        }
    }

    /// True when an outward offset must actually be built.
    pub fn is_active(&self) -> bool {
        self.spacing_mm > 0.0
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum SpacingGeometryError {
    /// The shape/offset is not supported by the offsetter (e.g. degenerate input or a
    /// geometry the robust buffer cannot offset safely).
    Unsupported(String),
    /// The input polygon is invalid (fewer than 3 vertices, zero area, non-finite).
    InvalidPolygon(String),
    /// The offset produced a self-intersecting / non-simple polygon.
    SelfIntersecting(String),
    /// SGH-Q38: the robust buffer produced more than one disjoint exterior contour.
    MultiContour(String),
    /// SGH-Q38: the robust buffer produced an empty result.
    Empty(String),
    /// SGH-Q38: the robust buffer / union operation failed or panicked.
    BufferFailed(String),
}

impl std::fmt::Display for SpacingGeometryError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            SpacingGeometryError::Unsupported(m) => {
                write!(f, "UNSUPPORTED_SPACING_OFFSET_Q36: {m}")
            }
            SpacingGeometryError::InvalidPolygon(m) => {
                write!(f, "INVALID_SPACING_OFFSET_POLYGON_Q36: {m}")
            }
            SpacingGeometryError::SelfIntersecting(m) => {
                write!(f, "SELF_INTERSECTING_SPACING_OFFSET_Q36: {m}")
            }
            SpacingGeometryError::MultiContour(m) => {
                write!(f, "MULTI_CONTOUR_SPACING_OFFSET_Q38: {m}")
            }
            SpacingGeometryError::Empty(m) => {
                write!(f, "EMPTY_SPACING_OFFSET_Q38: {m}")
            }
            SpacingGeometryError::BufferFailed(m) => {
                write!(f, "OFFSET_BOOLEAN_UNION_FAILED_Q38: {m}")
            }
        }
    }
}

/// SGH-Q38: Build the spacing-expanded outer polygon — the original local polygon offset
/// OUTWARD by `half_spacing_mm` using a **robust straight-skeleton buffer** (`geo-buffer`),
/// which handles concave / high-vertex real polygons that the previous per-edge miter
/// offset could not.
///
/// Pipeline: normalise original → `buffer_polygon(+half)` (outward) → require exactly ONE
/// exterior contour → extract exterior ring → `validate_spacing_offset_outer_contour`.
///
/// - `half_spacing_mm <= 0` → returns a clone of the original (no offset).
/// - NEVER falls back to the raw/original contour or a bbox-expand on failure: any failure
///   returns an explicit `SpacingGeometryError`.
pub fn build_spacing_expanded_outer_polygon(
    original_local_polygon: &[Point],
    half_spacing_mm: f64,
) -> Result<Vec<Point>, SpacingGeometryError> {
    if !half_spacing_mm.is_finite() || half_spacing_mm < 0.0 {
        return Err(SpacingGeometryError::Unsupported(format!(
            "half_spacing_mm {half_spacing_mm} must be finite and >= 0"
        )));
    }
    if half_spacing_mm <= EPS {
        return Ok(original_local_polygon.to_vec());
    }

    let pts = clean_ring(original_local_polygon)?;

    // Build a geo::Polygon with a closed exterior ring, oriented to the standard winding
    // (exterior CCW) so `buffer_polygon(+d)` inflates outward deterministically.
    use geo::algorithm::orient::{Direction, Orient};
    let mut ring: Vec<geo::Coord<f64>> =
        pts.iter().map(|p| geo::Coord { x: p.x, y: p.y }).collect();
    ring.push(ring[0]); // close
    let poly = geo::Polygon::new(geo::LineString::from(ring), vec![]);
    let poly = poly.orient(Direction::Default);

    // Robust outward buffer (straight skeleton). Guard against any internal panic on a
    // pathological polygon and map it to an explicit error (never a silent raw fallback).
    let mp = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        geo_buffer::buffer_polygon(&poly, half_spacing_mm)
    }))
    .map_err(|_| {
        SpacingGeometryError::BufferFailed("geo-buffer straight-skeleton panicked".to_string())
    })?;

    let polys: Vec<geo::Polygon<f64>> = mp.0;
    if polys.is_empty() {
        return Err(SpacingGeometryError::Empty(
            "buffer produced no polygon".to_string(),
        ));
    }
    if polys.len() > 1 {
        return Err(SpacingGeometryError::MultiContour(format!(
            "buffer produced {} disjoint exterior contours",
            polys.len()
        )));
    }

    // Extract the single exterior ring (drop the closing duplicate vertex).
    let ext = polys[0].exterior();
    let mut out: Vec<Point> = ext.coords().map(|c| Point { x: c.x, y: c.y }).collect();
    if out.len() >= 2 {
        let f = out[0];
        let l = out[out.len() - 1];
        if (f.x - l.x).abs() <= EPS && (f.y - l.y).abs() <= EPS {
            out.pop();
        }
    }

    // The downstream CDE SPolygon stores vertices in f32; the straight-skeleton can emit
    // consecutive vertices that collapse to identical f32 points (rejected by SPolygon as
    // "duplicate points"). Drop consecutive vertices that are EQUAL in f32 space — this is
    // exactly what the collision engine sees, so it moves no boundary and is Q35-safe.
    let out = dedup_ring_f32(out);

    validate_spacing_offset_outer_contour(&pts, &out)?;
    Ok(out)
}

/// SGH-Q38: validate a spacing-offset outer contour against its original polygon.
///
/// Checks: ≥3 vertices; all coordinates finite; no degenerate duplicate-close; area > 0;
/// offset area ≥ original area (outward); bbox not smaller than the original bbox; a single
/// non-self-intersecting exterior ring. Returns an explicit error otherwise.
pub fn validate_spacing_offset_outer_contour(
    original: &[Point],
    offset: &[Point],
) -> Result<(), SpacingGeometryError> {
    if offset.len() < 3 {
        return Err(SpacingGeometryError::InvalidPolygon(
            "offset contour has < 3 vertices".to_string(),
        ));
    }
    for p in offset {
        if !p.x.is_finite() || !p.y.is_finite() {
            return Err(SpacingGeometryError::Unsupported(
                "offset produced non-finite vertex".to_string(),
            ));
        }
    }
    // No degenerate duplicate vertices (consecutive coincident points).
    let n = offset.len();
    for i in 0..n {
        let a = offset[i];
        let b = offset[(i + 1) % n];
        if (a.x - b.x).abs() <= EPS && (a.y - b.y).abs() <= EPS {
            return Err(SpacingGeometryError::InvalidPolygon(
                "offset contour has a degenerate duplicate vertex".to_string(),
            ));
        }
    }
    let off_area = polygon_area(offset).abs();
    let orig_area = polygon_area(original).abs();
    if off_area <= EPS {
        return Err(SpacingGeometryError::InvalidPolygon(
            "offset contour has zero area".to_string(),
        ));
    }
    if off_area + 1e-6 < orig_area {
        return Err(SpacingGeometryError::SelfIntersecting(
            "offset area smaller than original (not an outward offset)".to_string(),
        ));
    }
    // Outward offset bbox must not be smaller than the original bbox.
    let (omin_x, omin_y, omax_x, omax_y) = bbox(original);
    let (fmin_x, fmin_y, fmax_x, fmax_y) = bbox(offset);
    if fmin_x > omin_x + EPS
        || fmin_y > omin_y + EPS
        || fmax_x < omax_x - EPS
        || fmax_y < omax_y - EPS
    {
        return Err(SpacingGeometryError::SelfIntersecting(
            "offset bbox is smaller than original bbox (not outward)".to_string(),
        ));
    }
    if is_self_intersecting(offset) {
        return Err(SpacingGeometryError::SelfIntersecting(
            "offset polygon edges cross".to_string(),
        ));
    }
    Ok(())
}

/// Drop consecutive (and wraparound) vertices that are equal once narrowed to f32 — the
/// representation the downstream CDE `SPolygon` uses. Removes f32-duplicate points without
/// moving the f32 boundary.
fn dedup_ring_f32(pts: Vec<Point>) -> Vec<Point> {
    if pts.len() < 2 {
        return pts;
    }
    let same_f32 = |a: &Point, b: &Point| (a.x as f32 == b.x as f32) && (a.y as f32 == b.y as f32);
    let mut out: Vec<Point> = Vec::with_capacity(pts.len());
    for p in pts {
        if out.last().map_or(true, |q| !same_f32(q, &p)) {
            out.push(p);
        }
    }
    while out.len() >= 2 && same_f32(&out[0], &out[out.len() - 1]) {
        out.pop();
    }
    out
}

fn bbox(pts: &[Point]) -> (f64, f64, f64, f64) {
    let mut minx = f64::INFINITY;
    let mut miny = f64::INFINITY;
    let mut maxx = f64::NEG_INFINITY;
    let mut maxy = f64::NEG_INFINITY;
    for p in pts {
        minx = minx.min(p.x);
        miny = miny.min(p.y);
        maxx = maxx.max(p.x);
        maxy = maxy.max(p.y);
    }
    (minx, miny, maxx, maxy)
}

// ── helpers ───────────────────────────────────────────────────────────────────

fn clean_ring(points: &[Point]) -> Result<Vec<Point>, SpacingGeometryError> {
    if points.len() < 3 {
        return Err(SpacingGeometryError::InvalidPolygon(
            "polygon must have >= 3 vertices".to_string(),
        ));
    }
    let mut out: Vec<Point> = Vec::with_capacity(points.len());
    for &p in points {
        if !p.x.is_finite() || !p.y.is_finite() {
            return Err(SpacingGeometryError::InvalidPolygon(
                "polygon vertex must be finite".to_string(),
            ));
        }
        if out.last().map_or(true, |q: &Point| {
            (q.x - p.x).abs() > EPS || (q.y - p.y).abs() > EPS
        }) {
            out.push(p);
        }
    }
    if out.len() >= 2 {
        let first = out[0];
        let last = out[out.len() - 1];
        if (first.x - last.x).abs() <= EPS && (first.y - last.y).abs() <= EPS {
            out.pop();
        }
    }
    if out.len() < 3 {
        return Err(SpacingGeometryError::InvalidPolygon(
            "polygon degenerate after dedup".to_string(),
        ));
    }
    if polygon_area(&out).abs() <= EPS {
        return Err(SpacingGeometryError::InvalidPolygon(
            "polygon has zero area".to_string(),
        ));
    }
    Ok(out)
}

/// Basic non-simple detection: any pair of non-adjacent edges properly intersect.
fn is_self_intersecting(pts: &[Point]) -> bool {
    let n = pts.len();
    if n < 4 {
        return false;
    }
    for i in 0..n {
        let a0 = pts[i];
        let a1 = pts[(i + 1) % n];
        for j in (i + 1)..n {
            // Skip adjacent (sharing a vertex) edges.
            if j == i || (j + 1) % n == i || (i + 1) % n == j {
                continue;
            }
            let b0 = pts[j];
            let b1 = pts[(j + 1) % n];
            if segments_properly_intersect(a0, a1, b0, b1) {
                return true;
            }
        }
    }
    false
}

fn orient(a: Point, b: Point, c: Point) -> f64 {
    (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)
}

fn segments_properly_intersect(a0: Point, a1: Point, b0: Point, b1: Point) -> bool {
    let d1 = orient(b0, b1, a0);
    let d2 = orient(b0, b1, a1);
    let d3 = orient(a0, a1, b0);
    let d4 = orient(a0, a1, b1);
    ((d1 > EPS && d2 < -EPS) || (d1 < -EPS && d2 > EPS))
        && ((d3 > EPS && d4 < -EPS) || (d3 < -EPS && d4 > EPS))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rect(w: f64, h: f64) -> Vec<Point> {
        vec![
            Point { x: 0.0, y: 0.0 },
            Point { x: w, y: 0.0 },
            Point { x: w, y: h },
            Point { x: 0.0, y: h },
        ]
    }

    fn bbox(pts: &[Point]) -> (f64, f64, f64, f64) {
        let mut minx = f64::INFINITY;
        let mut miny = f64::INFINITY;
        let mut maxx = f64::NEG_INFINITY;
        let mut maxy = f64::NEG_INFINITY;
        for p in pts {
            minx = minx.min(p.x);
            miny = miny.min(p.y);
            maxx = maxx.max(p.x);
            maxy = maxy.max(p.y);
        }
        (minx, miny, maxx, maxy)
    }

    #[test]
    fn rectangle_half_spacing_exact() {
        let r = rect(20.0, 10.0);
        let out = build_spacing_expanded_outer_polygon(&r, 2.0).expect("offset");
        let (minx, miny, maxx, maxy) = bbox(&out);
        assert!((minx - -2.0).abs() < 1e-6, "minx={minx}");
        assert!((miny - -2.0).abs() < 1e-6, "miny={miny}");
        assert!((maxx - 22.0).abs() < 1e-6, "maxx={maxx}");
        assert!((maxy - 12.0).abs() < 1e-6, "maxy={maxy}");
    }

    #[test]
    fn zero_offset_returns_original() {
        let r = rect(20.0, 10.0);
        let out = build_spacing_expanded_outer_polygon(&r, 0.0).expect("offset");
        assert_eq!(out.len(), r.len());
        for (a, b) in out.iter().zip(r.iter()) {
            assert!((a.x - b.x).abs() < 1e-12 && (a.y - b.y).abs() < 1e-12);
        }
    }

    #[test]
    fn triangle_offset_is_not_bbox() {
        let tri = vec![
            Point { x: 0.0, y: 0.0 },
            Point { x: 20.0, y: 0.0 },
            Point { x: 0.0, y: 20.0 },
        ];
        let out = build_spacing_expanded_outer_polygon(&tri, 2.0).expect("offset");
        validate_spacing_offset_outer_contour(&tri, &out).expect("valid");
        // A bbox-expand would yield a rectangle of area ~ (24*24)=576. A true (robust)
        // offset of a right triangle (area 200) stays well below that bbox-rectangle area.
        let area = polygon_area(&out).abs();
        assert!(
            area > 200.0 && area < 560.0,
            "offset area {area} should be a true offset, not bbox"
        );
    }

    #[test]
    fn negative_offset_errors() {
        let r = rect(10.0, 10.0);
        assert!(build_spacing_expanded_outer_polygon(&r, -1.0).is_err());
    }

    #[test]
    fn degenerate_polygon_errors() {
        let bad = vec![Point { x: 0.0, y: 0.0 }, Point { x: 1.0, y: 1.0 }];
        assert!(build_spacing_expanded_outer_polygon(&bad, 1.0).is_err());
    }

    #[test]
    fn config_half_spacing_and_kerf_independence() {
        let cfg = SpacingOffsetConfig::from_spacing_mm(5.0);
        assert_eq!(cfg.half_spacing_mm, 2.5);
        assert!(cfg.is_active());
        // kerf is never part of this config — only spacing_mm / 2.
        let cfg0 = SpacingOffsetConfig::from_spacing_mm(0.0);
        assert!(!cfg0.is_active());
    }
}
