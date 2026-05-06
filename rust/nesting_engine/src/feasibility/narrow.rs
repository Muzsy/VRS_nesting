use rstar::{RTree, RTreeObject, AABB};

use crate::feasibility::aabb::{aabb_from_polygon64, aabb_inside, aabb_overlaps, Aabb};
use crate::geometry::{
    scale::TOUCH_TOL,
    types::{cross_product_i128, Point64, Polygon64},
};

#[derive(Debug, Clone)]
pub struct PlacedPart {
    pub inflated_polygon: Polygon64,
    pub aabb: Aabb,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum PointLocation {
    Outside,
    Inside,
    OnBoundary,
}

#[derive(Debug, Clone, Copy)]
struct PlacedPartEnvelope {
    idx: usize,
    aabb: Aabb,
}

impl RTreeObject for PlacedPartEnvelope {
    type Envelope = AABB<[i64; 2]>;

    fn envelope(&self) -> Self::Envelope {
        AABB::from_corners(
            [self.aabb.min_x, self.aabb.min_y],
            [self.aabb.max_x, self.aabb.max_y],
        )
    }
}

#[derive(Debug, Clone, Default)]
pub struct PlacedIndex {
    parts: Vec<PlacedPart>,
    tree: RTree<PlacedPartEnvelope>,
}

impl PlacedIndex {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn insert(&mut self, part: PlacedPart) {
        let idx = self.parts.len();
        let aabb = part.aabb;
        self.parts.push(part);
        self.tree.insert(PlacedPartEnvelope { idx, aabb });
    }

    pub fn query_overlaps(&self, aabb: &Aabb) -> Vec<usize> {
        let envelope = AABB::from_corners(
            [
                aabb.min_x.saturating_sub(TOUCH_TOL),
                aabb.min_y.saturating_sub(TOUCH_TOL),
            ],
            [
                aabb.max_x.saturating_add(TOUCH_TOL),
                aabb.max_y.saturating_add(TOUCH_TOL),
            ],
        );
        self.tree
            .locate_in_envelope_intersecting(&envelope)
            .map(|entry| entry.idx)
            .collect()
    }

    pub fn get(&self, idx: usize) -> &PlacedPart {
        &self.parts[idx]
    }
}

pub fn can_place(candidate: &Polygon64, bin: &Polygon64, placed: &PlacedIndex) -> bool {
    if !polygon_has_valid_rings(candidate) || !polygon_has_valid_rings(bin) {
        return false;
    }

    let candidate_aabb = aabb_from_polygon64(candidate);
    let bin_aabb = aabb_from_polygon64(bin);
    if !aabb_inside(&bin_aabb, &candidate_aabb) {
        return false;
    }

    if !poly_strictly_within(candidate, bin) {
        return false;
    }

    let mut maybe_overlap: Vec<(usize, &PlacedPart)> = placed
        .query_overlaps(&candidate_aabb)
        .into_iter()
        .map(|idx| (idx, placed.get(idx)))
        .filter(|(_, p)| aabb_overlaps(&candidate_aabb, &p.aabb))
        .collect();
    if maybe_overlap.is_empty() {
        return true;
    }

    // Deterministic narrow-phase order for reproducibility.
    maybe_overlap.sort_by(|a, b| {
        a.1.aabb
            .min_x
            .cmp(&b.1.aabb.min_x)
            .then(a.1.aabb.min_y.cmp(&b.1.aabb.min_y))
            .then(a.1.aabb.max_x.cmp(&b.1.aabb.max_x))
            .then(a.1.aabb.max_y.cmp(&b.1.aabb.max_y))
            .then(a.0.cmp(&b.0))
    });

    for (_, other) in maybe_overlap {
        // Touching is treated as infeasible by policy.
        if polygons_intersect_or_touch(candidate, &other.inflated_polygon) {
            return false;
        }
    }
    true
}

/// Profiled variant of `can_place` that returns timing breakdown.
/// Returns (result, CanPlaceProfile).
#[derive(Debug, Clone, Copy, Default)]
pub struct CanPlaceProfile {
    pub poly_within_ns: u64,
    pub poly_within_called: bool,
    pub overlap_query_ns: u64,
    pub overlap_candidates: u32,
    pub narrow_phase_ns: u64,
    pub narrow_phase_pairs: u32,
    pub segment_pair_checks: u64,
    pub rejected_by_aabb: bool,
    pub rejected_by_within: bool,
    pub rejected_by_narrow: bool,
}

pub fn can_place_profiled(
    candidate: &Polygon64,
    bin: &Polygon64,
    placed: &PlacedIndex,
) -> (bool, CanPlaceProfile) {
    use std::time::Instant;
    let mut prof = CanPlaceProfile::default();

    if !polygon_has_valid_rings(candidate) || !polygon_has_valid_rings(bin) {
        return (false, prof);
    }

    let candidate_aabb = aabb_from_polygon64(candidate);
    let bin_aabb = aabb_from_polygon64(bin);
    if !aabb_inside(&bin_aabb, &candidate_aabb) {
        prof.rejected_by_aabb = true;
        return (false, prof);
    }

    let t0 = Instant::now();
    let within = poly_strictly_within(candidate, bin);
    prof.poly_within_ns = t0.elapsed().as_nanos() as u64;
    prof.poly_within_called = true;
    if !within {
        prof.rejected_by_within = true;
        return (false, prof);
    }

    let t1 = Instant::now();
    let mut maybe_overlap: Vec<(usize, &PlacedPart)> = placed
        .query_overlaps(&candidate_aabb)
        .into_iter()
        .map(|idx| (idx, placed.get(idx)))
        .filter(|(_, p)| aabb_overlaps(&candidate_aabb, &p.aabb))
        .collect();
    prof.overlap_query_ns = t1.elapsed().as_nanos() as u64;
    prof.overlap_candidates = maybe_overlap.len() as u32;

    if maybe_overlap.is_empty() {
        return (true, prof);
    }

    maybe_overlap.sort_by(|a, b| {
        a.1.aabb
            .min_x
            .cmp(&b.1.aabb.min_x)
            .then(a.1.aabb.min_y.cmp(&b.1.aabb.min_y))
            .then(a.1.aabb.max_x.cmp(&b.1.aabb.max_x))
            .then(a.1.aabb.max_y.cmp(&b.1.aabb.max_y))
            .then(a.0.cmp(&b.0))
    });

    let t2 = Instant::now();
    for (_, other) in &maybe_overlap {
        prof.narrow_phase_pairs += 1;
        let cand_rings: usize = 1 + candidate.holes.len();
        let other_rings: usize = 1 + other.inflated_polygon.holes.len();
        let cand_segs: usize =
            candidate.outer.len() + candidate.holes.iter().map(|h| h.len()).sum::<usize>();
        let other_segs: usize = other.inflated_polygon.outer.len()
            + other
                .inflated_polygon
                .holes
                .iter()
                .map(|h| h.len())
                .sum::<usize>();
        prof.segment_pair_checks += (cand_segs as u64)
            * (other_segs as u64)
            * (cand_rings as u64).max(1)
            * (other_rings as u64).max(1)
            / ((cand_rings as u64).max(1) * (other_rings as u64).max(1));
        // Simplified: actual worst case is sum of ring_a_len * ring_b_len for all ring pairs
        // More accurate count:
        prof.segment_pair_checks = prof
            .segment_pair_checks
            .wrapping_sub(prof.segment_pair_checks); // reset
        for ring_a in polygon_rings(candidate) {
            for ring_b in polygon_rings(&other.inflated_polygon) {
                prof.segment_pair_checks += (ring_a.len() as u64) * (ring_b.len() as u64);
            }
        }

        if polygons_intersect_or_touch(candidate, &other.inflated_polygon) {
            prof.narrow_phase_ns = t2.elapsed().as_nanos() as u64;
            prof.rejected_by_narrow = true;
            return (false, prof);
        }
    }
    prof.narrow_phase_ns = t2.elapsed().as_nanos() as u64;

    (true, prof)
}

fn polygon_has_valid_rings(poly: &Polygon64) -> bool {
    poly.outer.len() >= 3 && poly.holes.iter().all(|ring| ring.len() >= 3)
}

fn poly_strictly_within(candidate: &Polygon64, container: &Polygon64) -> bool {
    if !polygon_has_valid_rings(candidate) || !polygon_has_valid_rings(container) {
        return false;
    }

    for &vertex in &candidate.outer {
        if point_in_polygon(vertex, container) != PointLocation::Inside {
            return false;
        }
    }

    if ring_intersects_polygon_boundaries(&candidate.outer, container) {
        return false;
    }

    for hole in &container.holes {
        if point_in_polygon(hole[0], candidate) != PointLocation::Outside {
            return false;
        }
    }

    true
}

fn polygons_intersect_or_touch(a: &Polygon64, b: &Polygon64) -> bool {
    if !polygon_has_valid_rings(a) || !polygon_has_valid_rings(b) {
        return true;
    }

    for ring_a in polygon_rings(a) {
        for ring_b in polygon_rings(b) {
            if ring_intersects_ring_or_touch(ring_a, ring_b) {
                return true;
            }
        }
    }

    point_in_polygon(a.outer[0], b) != PointLocation::Outside
        || point_in_polygon(b.outer[0], a) != PointLocation::Outside
}

fn polygon_rings(poly: &Polygon64) -> impl Iterator<Item = &[Point64]> {
    std::iter::once(poly.outer.as_slice()).chain(poly.holes.iter().map(Vec::as_slice))
}

fn ring_intersects_polygon_boundaries(ring: &[Point64], poly: &Polygon64) -> bool {
    polygon_rings(poly).any(|other| ring_intersects_ring_or_touch(ring, other))
}

fn ring_intersects_ring_or_touch(a: &[Point64], b: &[Point64]) -> bool {
    if a.len() < 2 || b.len() < 2 {
        return false;
    }

    for i in 0..a.len() {
        let a0 = a[i];
        let a1 = a[(i + 1) % a.len()];
        for j in 0..b.len() {
            let b0 = b[j];
            let b1 = b[(j + 1) % b.len()];
            if segments_intersect_or_touch(a0, a1, b0, b1) {
                return true;
            }
        }
    }
    false
}

fn point_in_polygon(point: Point64, poly: &Polygon64) -> PointLocation {
    match point_in_ring(point, &poly.outer) {
        PointLocation::Outside => PointLocation::Outside,
        PointLocation::OnBoundary => PointLocation::OnBoundary,
        PointLocation::Inside => {
            for hole in &poly.holes {
                match point_in_ring(point, hole) {
                    PointLocation::Outside => {}
                    PointLocation::OnBoundary => return PointLocation::OnBoundary,
                    PointLocation::Inside => return PointLocation::Outside,
                }
            }
            PointLocation::Inside
        }
    }
}

fn point_in_ring(point: Point64, ring: &[Point64]) -> PointLocation {
    if ring.len() < 3 {
        return PointLocation::Outside;
    }

    for idx in 0..ring.len() {
        let start = ring[idx];
        let end = ring[(idx + 1) % ring.len()];
        if point_on_segment_inclusive(start, end, point) {
            return PointLocation::OnBoundary;
        }
    }

    let mut winding = 0_i32;
    for idx in 0..ring.len() {
        let start = ring[idx];
        let end = ring[(idx + 1) % ring.len()];

        if start.y <= point.y {
            if end.y > point.y {
                let cross = cross_product_i128(
                    end.x - start.x,
                    end.y - start.y,
                    point.x - start.x,
                    point.y - start.y,
                );
                if cross > 0 {
                    winding += 1;
                }
            }
        } else if end.y <= point.y {
            let cross = cross_product_i128(
                end.x - start.x,
                end.y - start.y,
                point.x - start.x,
                point.y - start.y,
            );
            if cross < 0 {
                winding -= 1;
            }
        }
    }

    if winding == 0 {
        PointLocation::Outside
    } else {
        PointLocation::Inside
    }
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

fn orient(a: Point64, b: Point64, c: Point64) -> i8 {
    let v = cross_product_i128(b.x - a.x, b.y - a.y, c.x - a.x, c.y - a.y);
    if v > 0 {
        1
    } else if v < 0 {
        -1
    } else {
        0
    }
}

fn segments_intersect_or_touch(a0: Point64, a1: Point64, b0: Point64, b1: Point64) -> bool {
    let o1 = orient(a0, a1, b0);
    let o2 = orient(a0, a1, b1);
    let o3 = orient(b0, b1, a0);
    let o4 = orient(b0, b1, a1);

    if o1 == 0 && point_on_segment_inclusive(a0, a1, b0) {
        return true;
    }
    if o2 == 0 && point_on_segment_inclusive(a0, a1, b1) {
        return true;
    }
    if o3 == 0 && point_on_segment_inclusive(b0, b1, a0) {
        return true;
    }
    if o4 == 0 && point_on_segment_inclusive(b0, b1, a1) {
        return true;
    }
    o1 != o2 && o3 != o4
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::feasibility::aabb::aabb_from_polygon64;
    use crate::geometry::scale::mm_to_i64;
    use crate::geometry::types::{Point64, Polygon64};

    fn rect(x0: f64, y0: f64, w: f64, h: f64) -> Polygon64 {
        let p = |x: f64, y: f64| Point64 {
            x: mm_to_i64(x),
            y: mm_to_i64(y),
        };
        Polygon64 {
            outer: vec![p(x0, y0), p(x0 + w, y0), p(x0 + w, y0 + h), p(x0, y0 + h)],
            holes: Vec::new(),
        }
    }

    fn poly(points: &[(f64, f64)]) -> Polygon64 {
        Polygon64 {
            outer: points
                .iter()
                .map(|(x, y)| Point64 {
                    x: mm_to_i64(*x),
                    y: mm_to_i64(*y),
                })
                .collect(),
            holes: Vec::new(),
        }
    }

    #[test]
    fn ok_case() {
        let bin = rect(0.0, 0.0, 100.0, 100.0);
        let candidate = rect(10.0, 10.0, 10.0, 10.0);
        let placed = PlacedIndex::new();
        assert!(can_place(&candidate, &bin, &placed));
    }

    #[test]
    fn overlap_case() {
        let bin = rect(0.0, 0.0, 100.0, 100.0);
        let candidate = rect(10.0, 10.0, 10.0, 10.0);
        let other_poly = rect(10.0, 10.0, 10.0, 10.0);
        let other = PlacedPart {
            aabb: aabb_from_polygon64(&other_poly),
            inflated_polygon: other_poly,
        };
        let mut placed = PlacedIndex::new();
        placed.insert(other);
        assert!(!can_place(&candidate, &bin, &placed));
    }

    #[test]
    fn containment_case() {
        let bin = rect(0.0, 0.0, 100.0, 100.0);
        let candidate = rect(95.0, 95.0, 10.0, 10.0);
        let placed = PlacedIndex::new();
        assert!(!can_place(&candidate, &bin, &placed));
    }

    #[test]
    fn touching_case() {
        let bin = rect(0.0, 0.0, 100.0, 100.0);
        let candidate = rect(10.0, 10.0, 10.0, 10.0);
        let other_poly = rect(20.0, 10.0, 10.0, 10.0);
        let other = PlacedPart {
            aabb: aabb_from_polygon64(&other_poly),
            inflated_polygon: other_poly,
        };
        let mut placed = PlacedIndex::new();
        placed.insert(other);
        assert!(!can_place(&candidate, &bin, &placed));
    }

    #[test]
    fn touching_policy_part_part_touching_is_infeasible() {
        let bin = rect(0.0, 0.0, 100.0, 100.0);
        let candidate = rect(10.0, 10.0, 10.0, 10.0);
        let other_poly = rect(20.0, 10.0, 10.0, 10.0);
        let other = PlacedPart {
            aabb: aabb_from_polygon64(&other_poly),
            inflated_polygon: other_poly,
        };
        let mut placed = PlacedIndex::new();
        placed.insert(other);
        assert!(!can_place(&candidate, &bin, &placed));
    }

    #[test]
    fn broad_phase_query_result_is_deterministic_after_sort() {
        let bin = rect(0.0, 0.0, 100.0, 100.0);
        let candidate = rect(10.0, 10.0, 10.0, 10.0);

        let other_a_poly = rect(20.0, 20.0, 10.0, 10.0);
        let other_b_poly = rect(25.0, 20.0, 10.0, 10.0);
        let other_a = PlacedPart {
            aabb: aabb_from_polygon64(&other_a_poly),
            inflated_polygon: other_a_poly,
        };
        let other_b = PlacedPart {
            aabb: aabb_from_polygon64(&other_b_poly),
            inflated_polygon: other_b_poly,
        };

        let mut placed_ab = PlacedIndex::new();
        placed_ab.insert(other_a.clone());
        placed_ab.insert(other_b.clone());

        let mut placed_ba = PlacedIndex::new();
        placed_ba.insert(other_b);
        placed_ba.insert(other_a);

        let res_ab = can_place(&candidate, &bin, &placed_ab);
        let res_ba = can_place(&candidate, &bin, &placed_ba);
        assert_eq!(res_ab, res_ba);
    }

    #[test]
    fn can_place_rejects_touching_bin_boundary() {
        let bin = rect(0.0, 0.0, 100.0, 100.0);
        let candidate = rect(0.0, 10.0, 10.0, 10.0);
        let placed = PlacedIndex::new();
        assert!(!can_place(&candidate, &bin, &placed));
    }

    #[test]
    fn touching_policy_bin_boundary_touching_is_infeasible() {
        let bin = rect(0.0, 0.0, 100.0, 100.0);
        let candidate = rect(0.0, 10.0, 10.0, 10.0);
        let placed = PlacedIndex::new();
        assert!(!can_place(&candidate, &bin, &placed));
    }

    #[test]
    fn narrow_float_policy_mm_rounding_near_touching_is_deterministic() {
        let bin = rect(0.0, 0.0, 100.0, 100.0);
        let candidate = rect(10.0, 10.0, 10.0, 10.0);

        let touching_after_round_poly = rect(20.00000049, 10.0, 10.0, 10.0);
        let touching_after_round = PlacedPart {
            aabb: aabb_from_polygon64(&touching_after_round_poly),
            inflated_polygon: touching_after_round_poly,
        };
        let mut placed_touch = PlacedIndex::new();
        placed_touch.insert(touching_after_round);
        assert!(
            !can_place(&candidate, &bin, &placed_touch),
            "rounding-near touching candidate must stay infeasible"
        );

        let one_micron_gap_poly = rect(20.00000051, 10.0, 10.0, 10.0);
        let one_micron_gap = PlacedPart {
            aabb: aabb_from_polygon64(&one_micron_gap_poly),
            inflated_polygon: one_micron_gap_poly,
        };
        let mut placed_gap = PlacedIndex::new();
        placed_gap.insert(one_micron_gap);
        assert!(
            can_place(&candidate, &bin, &placed_gap),
            "1um gap after scaling should remain feasible"
        );
    }

    #[test]
    fn narrow_float_policy_identical_input_is_stable() {
        let bin = rect(0.0, 0.0, 100.0, 100.0);
        let candidate = rect(10.0, 10.0, 10.0, 10.0);
        let other_poly = rect(20.00000049, 10.0, 10.0, 10.0);
        let other = PlacedPart {
            aabb: aabb_from_polygon64(&other_poly),
            inflated_polygon: other_poly,
        };
        let mut placed = PlacedIndex::new();
        placed.insert(other);

        let first = can_place(&candidate, &bin, &placed);
        let second = can_place(&candidate, &bin, &placed);
        assert_eq!(first, second);
    }

    #[test]
    fn can_place_is_deterministic_for_identical_aabb_ties() {
        let bin = rect(0.0, 0.0, 100.0, 100.0);
        let candidate = rect(32.0, 32.0, 2.0, 2.0);

        let overlap_poly = poly(&[(30.0, 30.0), (40.0, 30.0), (30.0, 40.0)]);
        let clear_poly = poly(&[(30.0, 40.0), (40.0, 40.0), (40.0, 30.0)]);

        let overlap_part = PlacedPart {
            aabb: aabb_from_polygon64(&overlap_poly),
            inflated_polygon: overlap_poly,
        };
        let clear_part = PlacedPart {
            aabb: aabb_from_polygon64(&clear_poly),
            inflated_polygon: clear_poly,
        };

        let mut placed_overlap_first = PlacedIndex::new();
        placed_overlap_first.insert(overlap_part.clone());
        placed_overlap_first.insert(clear_part.clone());

        let mut placed_clear_first = PlacedIndex::new();
        placed_clear_first.insert(clear_part);
        placed_clear_first.insert(overlap_part);

        let res_overlap_first = can_place(&candidate, &bin, &placed_overlap_first);
        let res_clear_first = can_place(&candidate, &bin, &placed_clear_first);
        assert_eq!(res_overlap_first, res_clear_first);
    }
}
