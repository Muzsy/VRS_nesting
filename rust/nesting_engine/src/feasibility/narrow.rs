use i_overlay::{
    core::{fill_rule::FillRule, solver::Solver},
    float::relate::FloatPredicateOverlay,
};
use rstar::{AABB, RTree, RTreeObject};

use crate::feasibility::aabb::{Aabb, aabb_from_polygon64, aabb_inside, aabb_overlaps};
use crate::geometry::{scale::{i64_to_mm, TOUCH_TOL}, types::Polygon64};

type MmPt = [f64; 2];
type MmShape = Vec<Vec<MmPt>>;

#[derive(Debug, Clone)]
pub struct PlacedPart {
    pub inflated_polygon: Polygon64,
    pub aabb: Aabb,
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
    if candidate.outer.len() < 3 || bin.outer.len() < 3 {
        return false;
    }

    let candidate_aabb = aabb_from_polygon64(candidate);
    let bin_aabb = aabb_from_polygon64(bin);
    if !aabb_inside(&bin_aabb, &candidate_aabb) {
        return false;
    }

    let Some(candidate_shape) = polygon_to_mm_shape(candidate) else {
        return false;
    };
    let Some(bin_shape) = polygon_to_mm_shape(bin) else {
        return false;
    };

    // i_overlay containment: candidate must be fully inside bin.
    let mut containment = FloatPredicateOverlay::with_subj_and_clip_custom(
        &candidate_shape,
        &bin_shape,
        FillRule::NonZero,
        Solver::AUTO,
    );
    if !containment.within() {
        return false;
    }

    let mut maybe_overlap: Vec<&PlacedPart> = placed
        .query_overlaps(&candidate_aabb)
        .into_iter()
        .map(|idx| placed.get(idx))
        .filter(|p| aabb_overlaps(&candidate_aabb, &p.aabb))
        .collect();
    if maybe_overlap.is_empty() {
        return true;
    }

    // Deterministic narrow-phase order for reproducibility.
    maybe_overlap.sort_by(|a, b| {
        a.aabb
            .min_x
            .cmp(&b.aabb.min_x)
            .then(a.aabb.min_y.cmp(&b.aabb.min_y))
            .then(a.aabb.max_x.cmp(&b.aabb.max_x))
            .then(a.aabb.max_y.cmp(&b.aabb.max_y))
    });

    for other in maybe_overlap {
        let Some(other_shape) = polygon_to_mm_shape(&other.inflated_polygon) else {
            return false;
        };
        let mut overlap = FloatPredicateOverlay::with_subj_and_clip_custom(
            &candidate_shape,
            &other_shape,
            FillRule::NonZero,
            Solver::AUTO,
        );
        // intersects() treats both touching and interior overlap as infeasible.
        if overlap.intersects() {
            return false;
        }
    }
    true
}

fn polygon_to_mm_shape(poly: &Polygon64) -> Option<MmShape> {
    if poly.outer.len() < 3 {
        return None;
    }
    let mut shape: MmShape = Vec::with_capacity(1 + poly.holes.len());
    shape.push(ensure_ccw(
        poly.outer
            .iter()
            .map(|p| [i64_to_mm(p.x), i64_to_mm(p.y)])
            .collect(),
    ));

    for hole in &poly.holes {
        if hole.len() < 3 {
            return None;
        }
        shape.push(ensure_cw(
            hole.iter()
                .map(|p| [i64_to_mm(p.x), i64_to_mm(p.y)])
                .collect(),
        ));
    }
    Some(shape)
}

fn signed_area_2d(pts: &[MmPt]) -> f64 {
    if pts.len() < 3 {
        return 0.0;
    }
    let mut area = 0.0_f64;
    for i in 0..pts.len() {
        let [x0, y0] = pts[i];
        let [x1, y1] = pts[(i + 1) % pts.len()];
        area += x0 * y1 - x1 * y0;
    }
    area * 0.5
}

fn ensure_ccw(mut pts: Vec<MmPt>) -> Vec<MmPt> {
    if signed_area_2d(&pts) < 0.0 {
        pts.reverse();
    }
    pts
}

fn ensure_cw(mut pts: Vec<MmPt>) -> Vec<MmPt> {
    if signed_area_2d(&pts) > 0.0 {
        pts.reverse();
    }
    pts
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
}
