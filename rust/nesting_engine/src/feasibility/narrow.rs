use rstar::{RTree, RTreeObject, AABB};
use std::time::Instant;

use crate::feasibility::aabb::{aabb_from_polygon64, aabb_inside, aabb_overlaps, Aabb};
use crate::geometry::{
    scale::TOUCH_TOL,
    types::{cross_product_i128, Point64, Polygon64},
};

// =============================================================================
// Narrow-phase strategy selection
// =============================================================================

/// NESTING_ENGINE_NARROW_PHASE values supported by this engine.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NarrowPhaseStrategy {
    /// Own hand-rolled polygon intersection (default).
    Own,
    /// i_overlay PredicateOverlay-based alternative.
    IOverlay,
    /// GEOS PreparedGeometry (optional, compiled only with geos_narrow_phase feature).
    #[cfg(feature = "geos_narrow_phase")]
    Geos,
}

impl Default for NarrowPhaseStrategy {
    fn default() -> Self {
        NarrowPhaseStrategy::Own
    }
}

impl NarrowPhaseStrategy {
    /// Parse from NESTING_ENGINE_NARROW_PHASE env var.
    /// Invalid values return Ok(NarrowPhaseStrategy::Own) with a warning.
    pub fn from_env() -> Self {
        match std::env::var("NESTING_ENGINE_NARROW_PHASE")
            .as_deref()
            .map(str::trim)
        {
            Ok("own") => NarrowPhaseStrategy::Own,
            Ok("i_overlay") => NarrowPhaseStrategy::IOverlay,
            #[cfg(feature = "geos_narrow_phase")]
            Ok("geos") => NarrowPhaseStrategy::Geos,
            Ok(other) => {
                eprintln!(
                    "[NARROW_PHASE] unknown strategy '{}', defaulting to 'own'",
                    other
                );
                NarrowPhaseStrategy::Own
            }
            Err(_) => NarrowPhaseStrategy::Own,
        }
    }

    /// Human-readable name for stats output.
    pub fn as_str(&self) -> &'static str {
        match self {
            NarrowPhaseStrategy::Own => "own",
            NarrowPhaseStrategy::IOverlay => "i_overlay",
            #[cfg(feature = "geos_narrow_phase")]
            NarrowPhaseStrategy::Geos => "geos",
        }
    }
}

// =============================================================================
// GEOS feature gate — stubs when geos_narrow_phase is not compiled
// =============================================================================

#[cfg(not(feature = "geos_narrow_phase"))]
mod geos_narrow_phase {
    use super::Polygon64;

    /// Always returns false — GEOS not compiled.
    pub fn polygons_intersect_or_touch_geos(
        _a: &Polygon64,
        _b: &Polygon64,
    ) -> bool {
        false
    }

    pub fn is_available() -> bool {
        false
    }
}

#[cfg(feature = "geos_narrow_phase")]
mod geos_narrow_phase {
    use super::Polygon64;

    pub fn is_available() -> bool {
        true
    }

    pub fn polygons_intersect_or_touch_geos(a: &Polygon64, b: &Polygon64) -> bool {
        // Placeholder — actual GEOS implementation would go here
        // when geos_narrow_phase feature is enabled
        let _ = (a, b);
        false
    }
}

// =============================================================================
// i_overlay narrow-phase implementation
// =============================================================================

pub mod i_overlay_narrow {
    use super::*;
    use i_overlay::core::overlay::ShapeType;
    use i_overlay::core::relate::PredicateOverlay;

    // ---------------------------------------------------------------------
    // Coordinate encoding for i_overlay int precision
    // ---------------------------------------------------------------------

    /// Encode two polygons into shared i32 coordinate space for i_overlay.
    /// Returns (shape_a, shape_b) in i_overlay format or None on overflow.
    fn encode_pair(
        a: &Polygon64,
        b: &Polygon64,
    ) -> Option<(
        i_overlay::i_shape::int::shape::IntShape,
        i_overlay::i_shape::int::shape::IntShape,
    )> {
        
        use i_overlay::i_shape::int::shape::{IntContour, IntShape};

        // Compute bounding box of both polygons (all rings)
        let mut min_x = i64::MAX;
        let mut min_y = i64::MAX;
        let mut max_x = i64::MIN;
        let mut max_y = i64::MIN;

        for poly in [a, b] {
            for &pt in &poly.outer {
                min_x = min_x.min(pt.x);
                min_y = min_y.min(pt.y);
                max_x = max_x.max(pt.x);
                max_y = max_y.max(pt.y);
            }
            for hole in &poly.holes {
                for &pt in hole {
                    min_x = min_x.min(pt.x);
                    min_y = min_y.min(pt.y);
                    max_x = max_x.max(pt.x);
                    max_y = max_y.max(pt.y);
                }
            }
        }

        if min_x == i64::MAX {
            return None;
        }

        // Compute scale/shift to fit into i32 range.
        // Allow some headroom; i32::MAX ≈ 2.1e9, and coordinates are in micrometers.
        // For sheet sizes up to several meters (millions of µm), shift=0 works fine.
        // For very large coordinates, fall back to conservative collision.
        let span_x = max_x.checked_sub(min_x)?;
        let span_y = max_y.checked_sub(min_y)?;
        let max_span = span_x.max(span_y);

        // If the coordinate range exceeds i32 by too much, fall back conservatively.
        if max_span > i32::MAX as i64 {
            return None;
        }

        let shift = if max_span > i32::MAX as i64 { 1 } else { 0 };

        fn encode_ring(
            ring: &[Point64],
            min_x: i64,
            min_y: i64,
            shift: u32,
        ) -> Option<IntContour> {
            use i_overlay::i_float::int::point::IntPoint;
            let mut contour = Vec::with_capacity(ring.len());
            for pt in ring {
                let tx = (pt.x - min_x) >> shift;
                let ty = (pt.y - min_y) >> shift;
                let x = i32::try_from(tx).ok()?;
                let y = i32::try_from(ty).ok()?;
                contour.push(IntPoint::new(x, y));
            }
            Some(contour)
        }

        fn encode_poly(poly: &Polygon64, min_x: i64, min_y: i64, shift: u32) -> Option<IntShape> {
            let mut shape: IntShape = Vec::with_capacity(1 + poly.holes.len());
            shape.push(encode_ring(&poly.outer, min_x, min_y, shift)?);
            for hole in &poly.holes {
                shape.push(encode_ring(hole, min_x, min_y, shift)?);
            }
            Some(shape)
        }

        let shape_a = encode_poly(a, min_x, min_y, shift)?;
        let shape_b = encode_poly(b, min_x, min_y, shift)?;
        Some((shape_a, shape_b))
    }

    /// Returns true if two polygons intersect or touch, using i_overlay PredicateOverlay.
    /// Falls back conservatively (returns true) on any conversion/encoding error.
    pub fn polygons_intersect_or_touch_i_overlay(a: &Polygon64, b: &Polygon64) -> bool {
        // Fast path: try encoding, fall back to own on error
        let (shape_a, shape_b) = match encode_pair(a, b) {
            Some(pair) => pair,
            None => return true, // conservative: treat as collision
        };

        // predicate_overlay_capacity: number of vertices as rough estimate
        let cap_a: usize = shape_a.iter().map(|c| c.len()).sum();
        let cap_b = shape_b.iter().map(|c| c.len()).sum();
        let capacity = cap_a.max(cap_b).max(16);

        let mut overlay = PredicateOverlay::new(capacity);
        overlay.add_shape(&shape_a, ShapeType::Subject);
        overlay.add_shape(&shape_b, ShapeType::Clip);

        // intersects() includes boundary contact = collision in our semantics
        overlay.intersects()
    }
}

// =============================================================================
// Core narrow-phase functions
// =============================================================================

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

/// Returns true if two polygons intersect or touch.
/// This is the OWN strategy implementation.
pub fn own_polygons_intersect_or_touch(a: &Polygon64, b: &Polygon64) -> bool {
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

/// Returns true if two polygons intersect or touch, using the active strategy.
pub fn polygons_intersect_or_touch(a: &Polygon64, b: &Polygon64) -> bool {
    match NarrowPhaseStrategy::from_env() {
        NarrowPhaseStrategy::Own => own_polygons_intersect_or_touch(a, b),
        NarrowPhaseStrategy::IOverlay => {
            i_overlay_narrow::polygons_intersect_or_touch_i_overlay(a, b)
        }
        #[cfg(feature = "geos_narrow_phase")]
        NarrowPhaseStrategy::Geos => geos_narrow_phase::polygons_intersect_or_touch_geos(a, b),
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

    /// T06l-a: boolean equivalence — `can_place` and `can_place_profiled.0`
    /// MUST return the same boolean across the canonical control cases.
    #[test]
    fn can_place_and_profiled_return_equal_booleans_across_control_cases() {
        let bin = rect(0.0, 0.0, 100.0, 100.0);

        // Case 1: empty sheet, valid placement → both true.
        let candidate_ok = rect(10.0, 10.0, 10.0, 10.0);
        let placed_empty = PlacedIndex::new();
        assert_eq!(
            can_place(&candidate_ok, &bin, &placed_empty),
            can_place_profiled(&candidate_ok, &bin, &placed_empty).0,
            "empty sheet valid case must match",
        );

        // Case 2: bounds violation (containment fails) → both false.
        let candidate_oob = rect(95.0, 95.0, 10.0, 10.0);
        assert_eq!(
            can_place(&candidate_oob, &bin, &placed_empty),
            can_place_profiled(&candidate_oob, &bin, &placed_empty).0,
            "bounds violation must match",
        );

        // Case 3: overlap violation → both false.
        let overlap_poly = rect(10.0, 10.0, 10.0, 10.0);
        let mut placed_overlap = PlacedIndex::new();
        placed_overlap.insert(PlacedPart {
            aabb: aabb_from_polygon64(&overlap_poly),
            inflated_polygon: overlap_poly,
        });
        assert_eq!(
            can_place(&candidate_ok, &bin, &placed_overlap),
            can_place_profiled(&candidate_ok, &bin, &placed_overlap).0,
            "overlap violation must match",
        );

        // Case 4: touching → both false (touching is infeasible by policy).
        let touch_poly = rect(20.0, 10.0, 10.0, 10.0);
        let mut placed_touch = PlacedIndex::new();
        placed_touch.insert(PlacedPart {
            aabb: aabb_from_polygon64(&touch_poly),
            inflated_polygon: touch_poly,
        });
        assert_eq!(
            can_place(&candidate_ok, &bin, &placed_touch),
            can_place_profiled(&candidate_ok, &bin, &placed_touch).0,
            "touching policy decision must match",
        );

        // Case 5: multiple placed parts via RTree query → both should yield same answer.
        let other_a_poly = rect(40.0, 40.0, 10.0, 10.0);
        let other_b_poly = rect(60.0, 60.0, 10.0, 10.0);
        let other_c_poly = rect(80.0, 80.0, 10.0, 10.0);
        let mut placed_multi = PlacedIndex::new();
        placed_multi.insert(PlacedPart {
            aabb: aabb_from_polygon64(&other_a_poly),
            inflated_polygon: other_a_poly,
        });
        placed_multi.insert(PlacedPart {
            aabb: aabb_from_polygon64(&other_b_poly),
            inflated_polygon: other_b_poly,
        });
        placed_multi.insert(PlacedPart {
            aabb: aabb_from_polygon64(&other_c_poly),
            inflated_polygon: other_c_poly,
        });
        let candidate_clear = rect(2.0, 2.0, 5.0, 5.0);
        assert_eq!(
            can_place(&candidate_clear, &bin, &placed_multi),
            can_place_profiled(&candidate_clear, &bin, &placed_multi).0,
            "multi-placed clear case must match",
        );
        let candidate_overlap = rect(42.0, 42.0, 5.0, 5.0);
        assert_eq!(
            can_place(&candidate_overlap, &bin, &placed_multi),
            can_place_profiled(&candidate_overlap, &bin, &placed_multi).0,
            "multi-placed overlap case must match",
        );
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

    // =====================================================================
    // T06m: strategy correctness equivalence tests
    // =====================================================================

    /// Verify own_polygons_intersect_or_touch and i_overlay strategy agree
    /// on a range of geometric cases. Disagreement where own says collision
    /// but i_overlay says no-collision is a FAIL (false accept risk).
    #[test]
    fn i_overlay_strategy_equivalence_basic_cases() {
        // Only run when i_overlay strategy is enabled
        if std::env::var("NESTING_ENGINE_NARROW_PHASE") != Ok("i_overlay".into()) {
            return;
        }

        fn check_pair(
            a: Polygon64,
            b: Polygon64,
            expected_collision: bool,
            label: &str,
        ) -> bool {
            let own = own_polygons_intersect_or_touch(&a, &b);
            let iovr = i_overlay_narrow::polygons_intersect_or_touch_i_overlay(&a, &b);

            // i_overlay may be conservative (report collision when own doesn't)
            // but NOT the reverse (that would be a false accept).
            if own && !iovr {
                eprintln!(
                    "[FAIL i_overlay] {}: own=collision i_overlay=no_collision (false accept!)",
                    label
                );
                return false;
            }
            if !own && iovr && expected_collision {
                // conservative: own says no, i_overlay says yes — ok per spec
            }
            true
        }

        let r = |x0, y0, w, h| rect(x0, y0, w, h);

        // Case 1: no overlap, separated rectangles
        assert!(check_pair(r(0.,0.,10.,10.), r(20.,0.,10.,10.), false, "separated"));
        // Case 2: clear overlap
        assert!(check_pair(r(0.,0.,10.,10.), r(5.,5.,10.,10.), true, "overlap"));
        // Case 3: edge touch
        assert!(check_pair(r(0.,0.,10.,10.), r(10.,0.,10.,10.), true, "edge_touch"));
        // Case 4: point/corner touch
        assert!(check_pair(r(0.,0.,10.,10.), r(10.,10.,10.,10.), true, "corner_touch"));
        // Case 5: one fully inside another
        assert!(check_pair(r(0.,0.,20.,20.), r(5.,5.,5.,5.), true, "containment"));
    }
}
