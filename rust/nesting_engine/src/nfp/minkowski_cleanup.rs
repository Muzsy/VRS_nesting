use crate::geometry::{
    cleanup::{merge_collinear_vertices, normalize_orientation},
    types::{signed_area2_i128, Point64, Polygon64},
};

use super::{
    boundary_clean::ring_has_self_intersection, nfp_validation::polygon_validation_report,
};

#[derive(Debug, Clone)]
pub struct CleanupOptions {
    pub min_edge_length_units: i64,
    pub min_area_units2: i64,
    pub collinear_angle_deg_threshold: f64,
    pub sliver_aspect_ratio_threshold: f64,
}

impl Default for CleanupOptions {
    fn default() -> Self {
        Self {
            min_edge_length_units: 100,
            min_area_units2: 1000,
            collinear_angle_deg_threshold: 0.5,
            sliver_aspect_ratio_threshold: 0.01,
        }
    }
}

#[derive(Debug, Clone)]
pub enum CleanupError {
    InvalidAfterCleanup(String),
    EmptyInput,
    AllLoopsRemoved,
}

#[derive(Debug, Clone)]
pub struct CleanupResult {
    pub polygon: Option<Polygon64>,
    pub loops_removed_zero_area: usize,
    pub internal_edges_removed: usize,
    pub micro_edges_removed: usize,
    pub collinear_merged: usize,
    pub slivers_detected: usize,
    pub self_intersections_detected: usize,
    pub is_valid: bool,
    pub error: Option<CleanupError>,
}

pub fn run_minkowski_cleanup(raw_nfp: &Polygon64, options: &CleanupOptions) -> CleanupResult {
    if raw_nfp.outer.len() < 3 {
        return fail(CleanupError::EmptyInput, 0, 0, 0, 0, 0, 0);
    }

    // 1) duplicate_vertex_removal
    let mut poly = remove_duplicate_vertices_polygon(raw_nfp);

    // 2) null_edge_removal
    let (poly_after_null, null_removed) = remove_null_edges_polygon(&poly);
    poly = poly_after_null;

    // 3) micro_edge_removal
    let (poly_after_micro, micro_removed) =
        remove_micro_edges_polygon(&poly, options.min_edge_length_units);
    poly = poly_after_micro;

    // 4) loop_classification (orientation normalization + coarse self-intersection telemetry)
    let mut self_intersections_detected = 0usize;
    if ring_has_self_intersection(&poly.outer) {
        self_intersections_detected += 1;
    }
    for hole in &poly.holes {
        if ring_has_self_intersection(hole) {
            self_intersections_detected += 1;
        }
    }
    poly = match normalize_orientation(&poly) {
        Ok(res) => res.polygon,
        Err(err) => {
            return fail(
                CleanupError::InvalidAfterCleanup(format!(
                    "orientation normalization failed: {err:?}"
                )),
                0,
                null_removed,
                micro_removed,
                0,
                0,
                self_intersections_detected,
            )
        }
    };

    // 5) zero_area_loop_removal
    let (poly_after_zero, zero_removed_outer, zero_removed_holes) =
        remove_zero_area_loops(&poly, options.min_area_units2);
    poly = poly_after_zero;

    if zero_removed_outer {
        if self_intersections_detected > 0 {
            return fail(
                CleanupError::InvalidAfterCleanup(
                    "outer loop removed after self-intersection detection".to_string(),
                ),
                zero_removed_holes + 1,
                null_removed,
                micro_removed,
                0,
                0,
                self_intersections_detected,
            );
        }
        return fail(
            CleanupError::AllLoopsRemoved,
            zero_removed_holes + 1,
            null_removed,
            micro_removed,
            0,
            0,
            self_intersections_detected,
        );
    }

    // 6) internal_edge_removal
    let (poly_after_internal, internal_removed) = remove_internal_edges_placeholder(&poly);
    poly = poly_after_internal;

    // 7) collinear_merge
    let (poly_after_merge, collinear_merged) =
        match merge_collinear_vertices(&poly, options.collinear_angle_deg_threshold) {
            Ok(res) => (res.polygon, res.collinear_merged),
            Err(err) => {
                return fail(
                    CleanupError::InvalidAfterCleanup(format!("collinear merge failed: {err:?}")),
                    zero_removed_holes,
                    null_removed + internal_removed,
                    micro_removed,
                    0,
                    0,
                    self_intersections_detected,
                )
            }
        };
    poly = poly_after_merge;

    // 8) sliver_detection
    let (poly_after_sliver, slivers_detected) =
        detect_and_remove_sliver_holes(&poly, options.sliver_aspect_ratio_threshold);
    poly = poly_after_sliver;

    // 9) polygon_validity_check
    let validation = polygon_validation_report(&poly);
    if !validation.is_valid {
        return fail(
            CleanupError::InvalidAfterCleanup(
                validation
                    .reason_if_invalid
                    .unwrap_or_else(|| "unknown validation error".to_string()),
            ),
            zero_removed_holes,
            null_removed + internal_removed,
            micro_removed,
            collinear_merged,
            slivers_detected,
            self_intersections_detected,
        );
    }

    CleanupResult {
        polygon: Some(poly),
        loops_removed_zero_area: zero_removed_holes,
        internal_edges_removed: null_removed + internal_removed,
        micro_edges_removed: micro_removed,
        collinear_merged,
        slivers_detected,
        self_intersections_detected,
        is_valid: true,
        error: None,
    }
}

fn fail(
    err: CleanupError,
    loops_removed_zero_area: usize,
    internal_edges_removed: usize,
    micro_edges_removed: usize,
    collinear_merged: usize,
    slivers_detected: usize,
    self_intersections_detected: usize,
) -> CleanupResult {
    CleanupResult {
        polygon: None,
        loops_removed_zero_area,
        internal_edges_removed,
        micro_edges_removed,
        collinear_merged,
        slivers_detected,
        self_intersections_detected,
        is_valid: false,
        error: Some(err),
    }
}

fn remove_duplicate_vertices_polygon(poly: &Polygon64) -> Polygon64 {
    Polygon64 {
        outer: dedup_ring(&poly.outer),
        holes: poly.holes.iter().map(|h| dedup_ring(h)).collect(),
    }
}

fn remove_null_edges_polygon(poly: &Polygon64) -> (Polygon64, usize) {
    let mut removed = 0usize;
    let outer = remove_null_edges_ring(&poly.outer, &mut removed);
    let holes = poly
        .holes
        .iter()
        .map(|h| remove_null_edges_ring(h, &mut removed))
        .collect();
    (Polygon64 { outer, holes }, removed)
}

fn remove_micro_edges_polygon(poly: &Polygon64, min_edge_len: i64) -> (Polygon64, usize) {
    if min_edge_len <= 1 {
        return (poly.clone(), 0);
    }
    let mut removed = 0usize;
    let outer = filter_micro_edges(&poly.outer, min_edge_len, &mut removed);
    let holes = poly
        .holes
        .iter()
        .map(|h| filter_micro_edges(h, min_edge_len, &mut removed))
        .collect();
    (Polygon64 { outer, holes }, removed)
}

fn remove_zero_area_loops(poly: &Polygon64, min_area_units2: i64) -> (Polygon64, bool, usize) {
    let outer_area2 = signed_area2_i128(&poly.outer).abs();
    let outer_removed = outer_area2 <= min_area_units2 as i128 || poly.outer.len() < 3;

    let mut holes_removed = 0usize;
    let mut holes = Vec::new();
    for hole in &poly.holes {
        let area2 = signed_area2_i128(hole).abs();
        if hole.len() < 3 || area2 <= min_area_units2 as i128 {
            holes_removed += 1;
            continue;
        }
        holes.push(hole.clone());
    }

    let out = if outer_removed {
        Polygon64 {
            outer: Vec::new(),
            holes: Vec::new(),
        }
    } else {
        Polygon64 {
            outer: poly.outer.clone(),
            holes,
        }
    };

    (out, outer_removed, holes_removed)
}

fn remove_internal_edges_placeholder(poly: &Polygon64) -> (Polygon64, usize) {
    // Prototype-safe no-op: internal edge graph extraction is deferred,
    // but the step remains explicit in the T06 pipeline.
    (poly.clone(), 0)
}

fn detect_and_remove_sliver_holes(poly: &Polygon64, threshold: f64) -> (Polygon64, usize) {
    if threshold <= 0.0 {
        return (poly.clone(), 0);
    }

    let mut slivers = 0usize;
    let mut holes = Vec::new();
    for hole in &poly.holes {
        if is_sliver(hole, threshold) {
            slivers += 1;
            continue;
        }
        holes.push(hole.clone());
    }

    (
        Polygon64 {
            outer: poly.outer.clone(),
            holes,
        },
        slivers,
    )
}

fn dedup_ring(ring: &[Point64]) -> Vec<Point64> {
    if ring.is_empty() {
        return Vec::new();
    }
    let mut out = Vec::with_capacity(ring.len());
    for &p in ring {
        if out.last().copied() == Some(p) {
            continue;
        }
        out.push(p);
    }
    if out.len() > 1 && out.first() == out.last() {
        out.pop();
    }
    out
}

fn remove_null_edges_ring(ring: &[Point64], removed: &mut usize) -> Vec<Point64> {
    if ring.len() < 2 {
        return ring.to_vec();
    }
    let mut out = Vec::with_capacity(ring.len());
    for i in 0..ring.len() {
        let curr = ring[i];
        let next = ring[(i + 1) % ring.len()];
        if curr == next {
            *removed += 1;
            continue;
        }
        out.push(curr);
    }
    out
}

fn filter_micro_edges(ring: &[Point64], min_edge_len: i64, removed: &mut usize) -> Vec<Point64> {
    if ring.len() < 3 {
        return ring.to_vec();
    }
    let min2 = (min_edge_len as i128) * (min_edge_len as i128);
    let mut out = Vec::with_capacity(ring.len());

    for i in 0..ring.len() {
        let curr = ring[i];
        let next = ring[(i + 1) % ring.len()];
        let dx = (next.x - curr.x) as i128;
        let dy = (next.y - curr.y) as i128;
        if dx * dx + dy * dy < min2 {
            *removed += 1;
            continue;
        }
        out.push(curr);
    }

    if out.len() < 3 {
        ring.to_vec()
    } else {
        out
    }
}

fn is_sliver(ring: &[Point64], threshold: f64) -> bool {
    if ring.len() < 3 {
        return true;
    }

    let mut min_x = i64::MAX;
    let mut min_y = i64::MAX;
    let mut max_x = i64::MIN;
    let mut max_y = i64::MIN;

    for p in ring {
        min_x = min_x.min(p.x);
        min_y = min_y.min(p.y);
        max_x = max_x.max(p.x);
        max_y = max_y.max(p.y);
    }

    let w = (max_x - min_x).abs() as f64;
    let h = (max_y - min_y).abs() as f64;
    if w == 0.0 || h == 0.0 {
        return true;
    }

    let ratio = (w.min(h) / w.max(h)).abs();
    ratio < threshold
}

#[cfg(test)]
mod tests {
    use super::{run_minkowski_cleanup, CleanupError, CleanupOptions};
    use crate::geometry::types::{Point64, Polygon64};

    #[test]
    fn minkowski_cleanup_invalid_after_cleanup_polygon_is_none() {
        let poly = Polygon64 {
            outer: vec![
                Point64 { x: 0, y: 0 },
                Point64 { x: 4, y: 4 },
                Point64 { x: 0, y: 4 },
                Point64 { x: 4, y: 0 },
            ],
            holes: Vec::new(),
        };
        let out = run_minkowski_cleanup(&poly, &CleanupOptions::default());
        assert!(!out.is_valid);
        assert!(out.polygon.is_none());
        assert!(matches!(
            out.error,
            Some(CleanupError::InvalidAfterCleanup(_))
        ));
    }

    #[test]
    fn minkowski_cleanup_empty_input_returns_error() {
        let poly = Polygon64 {
            outer: vec![Point64 { x: 0, y: 0 }, Point64 { x: 1, y: 1 }],
            holes: Vec::new(),
        };
        let out = run_minkowski_cleanup(&poly, &CleanupOptions::default());
        assert!(!out.is_valid);
        assert!(out.polygon.is_none());
        assert!(matches!(out.error, Some(CleanupError::EmptyInput)));
    }

    #[test]
    fn minkowski_cleanup_valid_square_stays_valid() {
        let poly = Polygon64 {
            outer: vec![
                Point64 { x: 0, y: 0 },
                Point64 { x: 1000, y: 0 },
                Point64 { x: 1000, y: 1000 },
                Point64 { x: 0, y: 1000 },
            ],
            holes: Vec::new(),
        };
        let out = run_minkowski_cleanup(&poly, &CleanupOptions::default());
        assert!(out.is_valid);
        assert!(out.error.is_none());
        assert!(out.polygon.is_some());
    }
}
