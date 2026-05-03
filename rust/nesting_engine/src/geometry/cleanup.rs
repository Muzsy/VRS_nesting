use crate::geometry::types::{cross_product_i128, is_ccw, Point64, Polygon64};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CleanupError {
    EmptyPolygon,
    InvalidOrientationAfterCleanup(String),
    InsufficientVertices { count: usize },
}

#[derive(Debug, Clone, PartialEq)]
pub struct CleanupResult {
    pub polygon: Polygon64,
    pub vertex_count_before: usize,
    pub vertex_count_after: usize,
    pub null_edges_removed: usize,
    pub duplicate_vertices_removed: usize,
    pub collinear_merged: usize,
    pub orientation_fixed: bool,
}

pub fn remove_duplicate_vertices(poly: &Polygon64) -> Result<CleanupResult, CleanupError> {
    if poly.outer.len() < 3 {
        return Err(CleanupError::EmptyPolygon);
    }

    let mut duplicate_vertices_removed = 0usize;
    let outer = dedup_ring(&poly.outer, &mut duplicate_vertices_removed);
    ensure_ring_vertices(&outer)?;

    let mut holes = Vec::with_capacity(poly.holes.len());
    for hole in &poly.holes {
        let cleaned = dedup_ring(hole, &mut duplicate_vertices_removed);
        ensure_ring_vertices(&cleaned)?;
        holes.push(cleaned);
    }

    let cleaned = Polygon64 { outer, holes };
    Ok(CleanupResult {
        vertex_count_before: poly.outer.len(),
        vertex_count_after: cleaned.outer.len(),
        polygon: cleaned,
        null_edges_removed: 0,
        duplicate_vertices_removed,
        collinear_merged: 0,
        orientation_fixed: false,
    })
}

pub fn remove_null_edges(poly: &Polygon64) -> Result<CleanupResult, CleanupError> {
    if poly.outer.len() < 3 {
        return Err(CleanupError::EmptyPolygon);
    }

    let mut null_edges_removed = 0usize;
    let outer = remove_null_edges_ring(&poly.outer, &mut null_edges_removed);
    ensure_ring_vertices(&outer)?;

    let mut holes = Vec::with_capacity(poly.holes.len());
    for hole in &poly.holes {
        let cleaned = remove_null_edges_ring(hole, &mut null_edges_removed);
        ensure_ring_vertices(&cleaned)?;
        holes.push(cleaned);
    }

    let cleaned = Polygon64 { outer, holes };
    Ok(CleanupResult {
        vertex_count_before: poly.outer.len(),
        vertex_count_after: cleaned.outer.len(),
        polygon: cleaned,
        null_edges_removed,
        duplicate_vertices_removed: 0,
        collinear_merged: 0,
        orientation_fixed: false,
    })
}

pub fn merge_collinear_vertices(
    poly: &Polygon64,
    angle_threshold_deg: f64,
) -> Result<CleanupResult, CleanupError> {
    if poly.outer.len() < 3 {
        return Err(CleanupError::EmptyPolygon);
    }

    let threshold = if angle_threshold_deg.is_finite() && angle_threshold_deg >= 0.0 {
        angle_threshold_deg
    } else {
        0.0
    };

    let mut collinear_merged = 0usize;
    let outer = merge_collinear_ring(&poly.outer, threshold, &mut collinear_merged);
    ensure_ring_vertices(&outer)?;

    let mut holes = Vec::with_capacity(poly.holes.len());
    for hole in &poly.holes {
        let cleaned = merge_collinear_ring(hole, threshold, &mut collinear_merged);
        ensure_ring_vertices(&cleaned)?;
        holes.push(cleaned);
    }

    let cleaned = Polygon64 { outer, holes };
    Ok(CleanupResult {
        vertex_count_before: poly.outer.len(),
        vertex_count_after: cleaned.outer.len(),
        polygon: cleaned,
        null_edges_removed: 0,
        duplicate_vertices_removed: 0,
        collinear_merged,
        orientation_fixed: false,
    })
}

pub fn normalize_orientation(poly: &Polygon64) -> Result<CleanupResult, CleanupError> {
    if poly.outer.len() < 3 {
        return Err(CleanupError::EmptyPolygon);
    }

    let mut orientation_fixed = false;

    let mut outer = poly.outer.clone();
    if !is_ccw(&outer) {
        outer.reverse();
        orientation_fixed = true;
    }
    rotate_to_lexicographic_min(&mut outer);

    let mut holes = Vec::with_capacity(poly.holes.len());
    for hole in &poly.holes {
        let mut h = hole.clone();
        if h.len() < 3 {
            return Err(CleanupError::InsufficientVertices { count: h.len() });
        }
        // Holes must be CW.
        if is_ccw(&h) {
            h.reverse();
            orientation_fixed = true;
        }
        rotate_to_lexicographic_min(&mut h);
        holes.push(h);
    }

    if !is_ccw(&outer) {
        return Err(CleanupError::InvalidOrientationAfterCleanup(
            "outer ring is not CCW after normalization".to_string(),
        ));
    }

    let cleaned = Polygon64 { outer, holes };
    Ok(CleanupResult {
        vertex_count_before: poly.outer.len(),
        vertex_count_after: cleaned.outer.len(),
        polygon: cleaned,
        null_edges_removed: 0,
        duplicate_vertices_removed: 0,
        collinear_merged: 0,
        orientation_fixed,
    })
}

pub fn run_cleanup_pipeline(
    poly: &Polygon64,
    angle_threshold_deg: f64,
) -> Result<CleanupResult, CleanupError> {
    let before = poly.outer.len();

    let step1 = remove_duplicate_vertices(poly)?;
    let step2 = remove_null_edges(&step1.polygon)?;
    let step3 = merge_collinear_vertices(&step2.polygon, angle_threshold_deg)?;
    let step4 = normalize_orientation(&step3.polygon)?;

    Ok(CleanupResult {
        vertex_count_before: before,
        vertex_count_after: step4.polygon.outer.len(),
        polygon: step4.polygon,
        null_edges_removed: step2.null_edges_removed,
        duplicate_vertices_removed: step1.duplicate_vertices_removed,
        collinear_merged: step3.collinear_merged,
        orientation_fixed: step4.orientation_fixed,
    })
}

fn ensure_ring_vertices(ring: &[Point64]) -> Result<(), CleanupError> {
    if ring.len() < 3 {
        return Err(CleanupError::InsufficientVertices { count: ring.len() });
    }
    Ok(())
}

fn dedup_ring(ring: &[Point64], removed: &mut usize) -> Vec<Point64> {
    if ring.is_empty() {
        return Vec::new();
    }

    let mut out = Vec::with_capacity(ring.len());
    for &point in ring {
        if out.last().copied() == Some(point) {
            *removed += 1;
            continue;
        }
        out.push(point);
    }

    if out.len() > 1 && out.first() == out.last() {
        out.pop();
        *removed += 1;
    }

    out
}

fn remove_null_edges_ring(ring: &[Point64], removed: &mut usize) -> Vec<Point64> {
    if ring.len() < 2 {
        return ring.to_vec();
    }

    let mut out = Vec::with_capacity(ring.len());
    for idx in 0..ring.len() {
        let curr = ring[idx];
        let next = ring[(idx + 1) % ring.len()];
        if curr == next {
            *removed += 1;
            continue;
        }
        out.push(curr);
    }

    out
}

fn merge_collinear_ring(ring: &[Point64], threshold_deg: f64, merged: &mut usize) -> Vec<Point64> {
    let mut out = ring.to_vec();
    loop {
        if out.len() < 4 {
            break;
        }

        let mut changed = false;
        let n = out.len();
        let mut keep = vec![true; n];

        for i in 0..n {
            let prev = out[(i + n - 1) % n];
            let curr = out[i];
            let next = out[(i + 1) % n];

            if !is_collinear(prev, curr, next) {
                continue;
            }
            if !point_on_segment_inclusive(prev, next, curr) {
                continue;
            }
            let angle = vertex_angle_deg(prev, curr, next);
            if (180.0 - angle).abs() <= threshold_deg {
                keep[i] = false;
                *merged += 1;
                changed = true;
            }
        }

        if !changed {
            break;
        }

        let mut filtered = Vec::with_capacity(out.len());
        for (idx, point) in out.iter().enumerate() {
            if keep[idx] {
                filtered.push(*point);
            }
        }
        out = filtered;
    }

    out
}

fn is_collinear(a: Point64, b: Point64, c: Point64) -> bool {
    cross_product_i128(b.x - a.x, b.y - a.y, c.x - b.x, c.y - b.y) == 0
}

fn point_on_segment_inclusive(a: Point64, b: Point64, p: Point64) -> bool {
    let cross = cross_product_i128(b.x - a.x, b.y - a.y, p.x - a.x, p.y - a.y);
    if cross != 0 {
        return false;
    }

    let min_x = a.x.min(b.x);
    let max_x = a.x.max(b.x);
    let min_y = a.y.min(b.y);
    let max_y = a.y.max(b.y);

    p.x >= min_x && p.x <= max_x && p.y >= min_y && p.y <= max_y
}

fn vertex_angle_deg(prev: Point64, curr: Point64, next: Point64) -> f64 {
    let v1x = (prev.x - curr.x) as f64;
    let v1y = (prev.y - curr.y) as f64;
    let v2x = (next.x - curr.x) as f64;
    let v2y = (next.y - curr.y) as f64;

    let n1 = (v1x * v1x + v1y * v1y).sqrt();
    let n2 = (v2x * v2x + v2y * v2y).sqrt();
    if n1 == 0.0 || n2 == 0.0 {
        return 0.0;
    }

    let cos_theta = ((v1x * v2x + v1y * v2y) / (n1 * n2)).clamp(-1.0, 1.0);
    cos_theta.acos().to_degrees()
}

fn rotate_to_lexicographic_min(points: &mut [Point64]) {
    if points.is_empty() {
        return;
    }
    let min_idx = points
        .iter()
        .enumerate()
        .min_by_key(|(_, p)| (p.x, p.y))
        .map(|(idx, _)| idx)
        .unwrap_or(0);
    points.rotate_left(min_idx);
}

#[cfg(test)]
mod tests {
    use super::{run_cleanup_pipeline, CleanupError};
    use crate::geometry::types::{Point64, Polygon64};

    #[test]
    fn cleanup_pipeline_removes_duplicates_and_collinear() {
        let poly = Polygon64 {
            outer: vec![
                Point64 { x: 0, y: 0 },
                Point64 { x: 1, y: 0 },
                Point64 { x: 2, y: 0 },
                Point64 { x: 2, y: 1 },
                Point64 { x: 0, y: 1 },
                Point64 { x: 0, y: 0 },
            ],
            holes: Vec::new(),
        };

        let cleaned = run_cleanup_pipeline(&poly, 1.0).expect("cleanup should succeed");
        assert!(cleaned.vertex_count_after <= cleaned.vertex_count_before);
        assert!(cleaned.polygon.outer.len() >= 3);
    }

    #[test]
    fn cleanup_rejects_short_ring() {
        let poly = Polygon64 {
            outer: vec![Point64 { x: 0, y: 0 }, Point64 { x: 1, y: 0 }],
            holes: Vec::new(),
        };
        let err = run_cleanup_pipeline(&poly, 0.5).expect_err("must fail");
        assert!(matches!(err, CleanupError::EmptyPolygon));
    }
}
