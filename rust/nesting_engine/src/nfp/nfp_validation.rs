use crate::geometry::{
    scale::SCALE,
    types::{is_ccw, signed_area2_i128, Point64, Polygon64},
};

use super::boundary_clean::ring_has_self_intersection;

#[derive(Debug, Clone)]
pub struct ValidationReport {
    pub is_valid: bool,
    pub outer_ring_vertex_count: usize,
    pub outer_ring_ccw: bool,
    pub outer_ring_area_mm2: f64,
    pub self_intersection_detected: bool,
    pub holes_count: usize,
    pub degenerate_edges_count: usize,
    pub reason_if_invalid: Option<String>,
}

pub fn polygon_is_valid(poly: &Polygon64) -> bool {
    polygon_validation_report(poly).is_valid
}

pub fn polygon_validation_report(poly: &Polygon64) -> ValidationReport {
    let outer_ring_vertex_count = poly.outer.len();
    let outer_ring_ccw = if outer_ring_vertex_count >= 3 {
        is_ccw(&poly.outer)
    } else {
        false
    };
    let outer_ring_area_mm2 = ring_area_mm2(&poly.outer).abs();
    let outer_self_intersection = ring_has_self_intersection(&poly.outer);
    let degenerate_edges_count = count_degenerate_edges(poly);

    let mut reason_if_invalid = None;

    if outer_ring_vertex_count < 3 {
        reason_if_invalid = Some("outer ring has fewer than 3 vertices".to_string());
    } else if !outer_ring_ccw {
        reason_if_invalid = Some("outer ring is not CCW".to_string());
    } else if outer_ring_area_mm2 <= 0.0 {
        reason_if_invalid = Some("outer ring area is non-positive".to_string());
    } else if outer_self_intersection {
        reason_if_invalid = Some("outer ring has self-intersection".to_string());
    }

    if reason_if_invalid.is_none() {
        for (idx, hole) in poly.holes.iter().enumerate() {
            if hole.len() < 3 {
                reason_if_invalid = Some(format!("hole[{idx}] has fewer than 3 vertices"));
                break;
            }
            if is_ccw(hole) {
                reason_if_invalid = Some(format!("hole[{idx}] is not CW"));
                break;
            }
            if ring_area_mm2(hole).abs() <= 0.0 {
                reason_if_invalid = Some(format!("hole[{idx}] area is non-positive"));
                break;
            }
            if ring_has_self_intersection(hole) {
                reason_if_invalid = Some(format!("hole[{idx}] has self-intersection"));
                break;
            }
        }
    }

    if reason_if_invalid.is_none() && degenerate_edges_count > 0 {
        reason_if_invalid = Some(format!(
            "polygon contains {degenerate_edges_count} degenerate edge(s)"
        ));
    }

    ValidationReport {
        is_valid: reason_if_invalid.is_none(),
        outer_ring_vertex_count,
        outer_ring_ccw,
        outer_ring_area_mm2,
        self_intersection_detected: outer_self_intersection
            || poly.holes.iter().any(|h| ring_has_self_intersection(h)),
        holes_count: poly.holes.len(),
        degenerate_edges_count,
        reason_if_invalid,
    }
}

fn ring_area_mm2(ring: &[Point64]) -> f64 {
    let area2 = signed_area2_i128(ring) as f64;
    area2 / (2.0 * SCALE as f64 * SCALE as f64)
}

fn count_degenerate_edges(poly: &Polygon64) -> usize {
    let mut count = count_ring_degenerate_edges(&poly.outer);
    for hole in &poly.holes {
        count += count_ring_degenerate_edges(hole);
    }
    count
}

fn count_ring_degenerate_edges(ring: &[Point64]) -> usize {
    if ring.len() < 2 {
        return 0;
    }
    let mut count = 0usize;
    for i in 0..ring.len() {
        if ring[i] == ring[(i + 1) % ring.len()] {
            count += 1;
        }
    }
    count
}

#[cfg(test)]
mod tests {
    use super::{polygon_is_valid, polygon_validation_report};
    use crate::geometry::types::{Point64, Polygon64};

    #[test]
    fn nfp_validation_accepts_simple_ccw_outer() {
        let poly = Polygon64 {
            outer: vec![
                Point64 { x: 0, y: 0 },
                Point64 { x: 10, y: 0 },
                Point64 { x: 10, y: 10 },
                Point64 { x: 0, y: 10 },
            ],
            holes: Vec::new(),
        };
        let report = polygon_validation_report(&poly);
        assert!(report.is_valid);
        assert!(polygon_is_valid(&poly));
    }

    #[test]
    fn nfp_validation_rejects_self_intersection() {
        let poly = Polygon64 {
            outer: vec![
                Point64 { x: 0, y: 0 },
                Point64 { x: 4, y: 4 },
                Point64 { x: 0, y: 4 },
                Point64 { x: 4, y: 0 },
            ],
            holes: Vec::new(),
        };
        let report = polygon_validation_report(&poly);
        assert!(!report.is_valid);
        assert!(report.self_intersection_detected);
    }

    #[test]
    fn nfp_validation_rejects_ccw_hole() {
        let poly = Polygon64 {
            outer: vec![
                Point64 { x: 0, y: 0 },
                Point64 { x: 10, y: 0 },
                Point64 { x: 10, y: 10 },
                Point64 { x: 0, y: 10 },
            ],
            holes: vec![vec![
                Point64 { x: 2, y: 2 },
                Point64 { x: 4, y: 2 },
                Point64 { x: 4, y: 4 },
                Point64 { x: 2, y: 4 },
            ]],
        };
        let report = polygon_validation_report(&poly);
        assert!(!report.is_valid);
        assert!(report.reason_if_invalid.is_some());
    }
}
