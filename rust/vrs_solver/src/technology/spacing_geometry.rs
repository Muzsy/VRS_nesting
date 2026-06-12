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
    /// The shape/offset is not supported by the Q36 offsetter (e.g. degenerate input,
    /// non-finite vertices, or a reflex geometry the miter offset cannot handle safely).
    Unsupported(String),
    /// The input polygon is invalid (fewer than 3 vertices, zero area, non-finite).
    InvalidPolygon(String),
    /// The offset produced a self-intersecting / non-simple polygon.
    SelfIntersecting(String),
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
        }
    }
}

/// Build the spacing-expanded outer polygon: the original local polygon offset
/// OUTWARD by `half_spacing_mm` via a miter-join edge offset.
///
/// - `half_spacing_mm <= 0` → returns a clone of the original (no offset).
/// - Exact for axis-aligned rectangles; supports simple convex/closed polygons.
/// - Detects degenerate / self-intersecting results and returns an explicit error
///   (never silently falls back to the raw/original contour).
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
    let n = pts.len();

    // Orient CCW so the outward normal of edge (p_i -> p_{i+1}) is the right normal
    // (e.y, -e.x). signed_area > 0 ⇒ CCW.
    let signed = signed_area(&pts);
    let ccw: Vec<Point> = if signed > 0.0 {
        pts.clone()
    } else {
        pts.iter().rev().cloned().collect()
    };

    // Each edge i: from ccw[i] to ccw[i+1]. Offset its supporting line outward by d.
    // New vertex i = intersection of offset(edge i-1) and offset(edge i).
    let d = half_spacing_mm;
    let mut offset_lines: Vec<(Point, Point)> = Vec::with_capacity(n); // (point_on_line, direction)
    for i in 0..n {
        let a = ccw[i];
        let b = ccw[(i + 1) % n];
        let ex = b.x - a.x;
        let ey = b.y - a.y;
        let len = (ex * ex + ey * ey).sqrt();
        if len <= EPS {
            return Err(SpacingGeometryError::InvalidPolygon(
                "zero-length edge in polygon".to_string(),
            ));
        }
        // Outward (right) normal for CCW polygon.
        let nx = ey / len;
        let ny = -ex / len;
        let pa = Point {
            x: a.x + d * nx,
            y: a.y + d * ny,
        };
        // Direction along the edge.
        let dir = Point { x: ex, y: ey };
        offset_lines.push((pa, dir));
    }

    let mut out: Vec<Point> = Vec::with_capacity(n);
    for i in 0..n {
        let prev = (i + n - 1) % n;
        let (p0, d0) = offset_lines[prev];
        let (p1, d1) = offset_lines[i];
        match line_intersection(p0, d0, p1, d1) {
            Some(v) => out.push(v),
            None => {
                // Parallel offset lines (collinear edges): use the endpoint pushed
                // along the current edge's outward normal.
                let a = ccw[i];
                let ex = d1.x;
                let ey = d1.y;
                let len = (ex * ex + ey * ey).sqrt();
                let nx = ey / len;
                let ny = -ex / len;
                out.push(Point {
                    x: a.x + d * nx,
                    y: a.y + d * ny,
                });
            }
        }
    }

    // Validate the result.
    for p in &out {
        if !p.x.is_finite() || !p.y.is_finite() {
            return Err(SpacingGeometryError::Unsupported(
                "offset produced non-finite vertex".to_string(),
            ));
        }
    }
    let out_area = signed_area(&out).abs();
    let in_area = signed.abs();
    if out_area + EPS < in_area {
        // Offset shrank the polygon — wrong direction / reflex blow-up.
        return Err(SpacingGeometryError::SelfIntersecting(
            "offset area smaller than original (reflex/self-intersection)".to_string(),
        ));
    }
    if is_self_intersecting(&out) {
        return Err(SpacingGeometryError::SelfIntersecting(
            "offset polygon edges cross".to_string(),
        ));
    }
    Ok(out)
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

fn signed_area(pts: &[Point]) -> f64 {
    let n = pts.len();
    let mut s = 0.0;
    for i in 0..n {
        let a = pts[i];
        let b = pts[(i + 1) % n];
        s += a.x * b.y - b.x * a.y;
    }
    s / 2.0
}

/// Intersection of two lines given as (point, direction). Returns None when parallel.
fn line_intersection(p0: Point, d0: Point, p1: Point, d1: Point) -> Option<Point> {
    let denom = d0.x * d1.y - d0.y * d1.x;
    if denom.abs() <= 1e-12 {
        return None;
    }
    let dx = p1.x - p0.x;
    let dy = p1.y - p0.y;
    let t = (dx * d1.y - dy * d1.x) / denom;
    Some(Point {
        x: p0.x + t * d0.x,
        y: p0.y + t * d0.y,
    })
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
        // A bbox-expand would yield 4 corners of a rectangle; a true offset keeps 3
        // vertices and the hypotenuse stays diagonal (its midpoint is not axis-aligned).
        assert_eq!(out.len(), 3, "triangle offset must remain a triangle, got {out:?}");
        let area = signed_area(&out).abs();
        // Triangle area 200 grows but stays well below the bbox-rect area (24*24=576).
        assert!(area > 200.0 && area < 576.0, "offset area {area} should be a true offset, not bbox");
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
