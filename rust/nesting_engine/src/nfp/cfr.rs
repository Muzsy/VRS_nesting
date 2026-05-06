#[cfg(test)]
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};

use i_overlay::{
    core::{
        fill_rule::FillRule,
        overlay::IntOverlayOptions,
        overlay::Overlay,
        overlay_rule::OverlayRule,
        solver::{Precision, Solver, Strategy},
    },
    i_float::int::point::IntPoint,
    i_shape::int::shape::{IntContour, IntShape},
};
use sha2::{Digest, Sha256};

use crate::geometry::types::{cross_product_i128, Point64, Polygon64};

#[cfg(test)]
static COMPONENT_HASH_CALLS: AtomicUsize = AtomicUsize::new(0);
#[cfg(test)]
static COMPONENT_HASH_COUNTING_ENABLED: AtomicBool = AtomicBool::new(false);

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
struct CfrComponentSortKeyV1 {
    min_x: i64,
    min_y: i64,
    abs_area: i128,
    vertex_count: usize,
    tiebreak_hash: u64,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct CfrStatsV1 {
    pub cfr_union_calls: u64,
    pub cfr_diff_calls: u64,
}

impl CfrStatsV1 {
    pub fn merge_from(&mut self, other: &Self) {
        self.cfr_union_calls = self.cfr_union_calls.saturating_add(other.cfr_union_calls);
        self.cfr_diff_calls = self.cfr_diff_calls.saturating_add(other.cfr_diff_calls);
    }
}

pub fn compute_cfr(ifp_rect: &Polygon64, nfp_polys: &[Polygon64]) -> Vec<Polygon64> {
    compute_cfr_internal(ifp_rect, nfp_polys, None)
}

pub fn compute_cfr_with_stats(
    ifp_rect: &Polygon64,
    nfp_polys: &[Polygon64],
    stats: &mut CfrStatsV1,
) -> Vec<Polygon64> {
    compute_cfr_internal(ifp_rect, nfp_polys, Some(stats))
}

fn compute_cfr_internal(
    ifp_rect: &Polygon64,
    nfp_polys: &[Polygon64],
    mut stats: Option<&mut CfrStatsV1>,
) -> Vec<Polygon64> {
    let mut ifp_canon = ifp_rect.clone();
    if !canonicalize_polygon64(&mut ifp_canon) {
        return Vec::new();
    }
    if nfp_polys.is_empty() {
        return vec![ifp_canon];
    }

    let mut all_polys = Vec::with_capacity(1 + nfp_polys.len());
    all_polys.push(ifp_rect);
    all_polys.extend(nfp_polys.iter());

    let Some(bounds) = OverlayBounds::from_polygons(&all_polys) else {
        return vec![ifp_canon];
    };

    let Some(ifp_shape) = encode_polygon(&ifp_canon, bounds) else {
        return vec![ifp_canon.clone()];
    };
    let nfp_shapes: Vec<IntShape> = nfp_polys
        .iter()
        .filter_map(|poly| encode_polygon(poly, bounds))
        .collect();

    if nfp_shapes.is_empty() {
        return vec![ifp_canon];
    }

    if let Some(cfr_stats) = stats.as_deref_mut() {
        cfr_stats.cfr_union_calls = cfr_stats.cfr_union_calls.saturating_add(1);
    }
    let union_shapes = run_overlay(&nfp_shapes, &[], OverlayRule::Union);
    if union_shapes.is_empty() {
        return vec![ifp_canon];
    }

    if let Some(cfr_stats) = stats.as_deref_mut() {
        cfr_stats.cfr_diff_calls = cfr_stats.cfr_diff_calls.saturating_add(1);
    }
    let diff_shapes = run_overlay(&[ifp_shape], &union_shapes, OverlayRule::Difference);
    if diff_shapes.is_empty() {
        return Vec::new();
    }

    let out: Vec<Polygon64> = diff_shapes
        .iter()
        .filter_map(|shape| decode_shape(shape, bounds))
        .filter_map(|mut poly| {
            if canonicalize_polygon64(&mut poly) {
                Some(poly)
            } else {
                None
            }
        })
        .collect();
    sort_components(out)
}

fn run_overlay(subject: &[IntShape], clip: &[IntShape], rule: OverlayRule) -> Vec<IntShape> {
    let mut overlay = Overlay::with_shapes_options(
        subject,
        clip,
        IntOverlayOptions::keep_all_points(),
        Solver::with_strategy_and_precision(Strategy::List, Precision::ABSOLUTE),
    );
    overlay.overlay(rule, FillRule::NonZero)
}

fn decode_shape(shape: &IntShape, bounds: OverlayBounds) -> Option<Polygon64> {
    if shape.is_empty() {
        return None;
    }

    let outer = decode_contour(&shape[0], bounds)?;
    let holes: Vec<Vec<Point64>> = shape
        .iter()
        .skip(1)
        .filter_map(|contour| decode_contour(contour, bounds))
        .collect();

    Some(Polygon64 { outer, holes })
}

fn encode_polygon(poly: &Polygon64, bounds: OverlayBounds) -> Option<IntShape> {
    let mut canonical = poly.clone();
    if !canonicalize_polygon64(&mut canonical) {
        return None;
    }

    let mut shape: IntShape = Vec::with_capacity(1 + poly.holes.len());
    shape.push(encode_contour(&canonical.outer, bounds)?);

    for hole in &canonical.holes {
        shape.push(encode_contour(hole, bounds)?);
    }
    Some(shape)
}

fn encode_contour(ring: &[Point64], bounds: OverlayBounds) -> Option<IntContour> {
    let mut contour = Vec::with_capacity(ring.len());
    for point in ring {
        let x = bounds.encode_x(point.x)?;
        let y = bounds.encode_y(point.y)?;
        contour.push(IntPoint::new(x, y));
    }
    Some(contour)
}

fn decode_contour(contour: &IntContour, bounds: OverlayBounds) -> Option<Vec<Point64>> {
    if contour.len() < 3 {
        return None;
    }
    let mut ring = Vec::with_capacity(contour.len());
    for point in contour {
        ring.push(Point64 {
            x: bounds.decode_x(point.x)?,
            y: bounds.decode_y(point.y)?,
        });
    }
    Some(ring)
}

fn canonicalize_polygon64(poly: &mut Polygon64) -> bool {
    if !canonicalize_ring(&mut poly.outer, true) {
        return false;
    }

    let mut holes: Vec<Vec<Point64>> = std::mem::take(&mut poly.holes)
        .into_iter()
        .filter_map(|mut hole| {
            if canonicalize_ring(&mut hole, false) {
                Some(hole)
            } else {
                None
            }
        })
        .collect();
    holes.sort_by(|a, b| compare_ring_lex(a, b));
    poly.holes = holes;

    component_area_abs(poly) > 0
}

fn canonicalize_ring(points: &mut Vec<Point64>, want_ccw: bool) -> bool {
    let mut ring = dedup_ring(points);
    if ring.len() < 3 {
        return false;
    }

    simplify_collinear(&mut ring);
    if ring.len() < 3 {
        return false;
    }

    let area2 = signed_area2_i128(&ring);
    if area2 == 0 {
        return false;
    }
    if (area2 > 0) != want_ccw {
        ring.reverse();
    }
    rotate_to_lexicographic_min(&mut ring);
    *points = ring;
    true
}

fn dedup_ring(points: &[Point64]) -> Vec<Point64> {
    let mut out = Vec::with_capacity(points.len());
    for &point in points {
        if out.last().copied() != Some(point) {
            out.push(point);
        }
    }
    if out.len() > 1 && out.first() == out.last() {
        out.pop();
    }
    out
}

fn simplify_collinear(ring: &mut Vec<Point64>) {
    loop {
        if ring.len() < 3 {
            return;
        }
        let mut changed = false;
        let n = ring.len();
        let mut keep = vec![true; n];

        for idx in 0..n {
            let prev = ring[(idx + n - 1) % n];
            let curr = ring[idx];
            let next = ring[(idx + 1) % n];
            if curr == prev || curr == next {
                keep[idx] = false;
                changed = true;
                continue;
            }

            let cross = cross_product_i128(
                curr.x - prev.x,
                curr.y - prev.y,
                next.x - curr.x,
                next.y - curr.y,
            );
            if cross == 0 && point_on_segment(prev, next, curr) {
                keep[idx] = false;
                changed = true;
            }
        }

        if !changed {
            break;
        }
        let mut filtered = Vec::with_capacity(ring.len());
        for (idx, point) in ring.iter().enumerate() {
            if keep[idx] {
                filtered.push(*point);
            }
        }
        *ring = filtered;
    }
}

fn rotate_to_lexicographic_min(points: &mut [Point64]) {
    if points.is_empty() {
        return;
    }
    let start_idx = points
        .iter()
        .enumerate()
        .min_by_key(|(_, p)| (p.x, p.y))
        .map(|(idx, _)| idx)
        .unwrap_or(0);
    points.rotate_left(start_idx);
}

fn point_on_segment(a: Point64, b: Point64, p: Point64) -> bool {
    let min_x = a.x.min(b.x);
    let max_x = a.x.max(b.x);
    let min_y = a.y.min(b.y);
    let max_y = a.y.max(b.y);
    p.x >= min_x && p.x <= max_x && p.y >= min_y && p.y <= max_y
}

fn sort_components(components: Vec<Polygon64>) -> Vec<Polygon64> {
    let mut decorated: Vec<(CfrComponentSortKeyV1, Polygon64)> = components
        .into_iter()
        .map(|poly| (build_sort_key_precomputed(&poly), poly))
        .collect();

    decorated.sort_by(|(ka, _), (kb, _)| ka.cmp(kb));

    decorated.into_iter().map(|(_, poly)| poly).collect()
}

fn build_sort_key_precomputed(poly: &Polygon64) -> CfrComponentSortKeyV1 {
    let min = min_point(poly);
    CfrComponentSortKeyV1 {
        min_x: min.x,
        min_y: min.y,
        abs_area: component_area_abs(poly),
        vertex_count: vertex_count(poly),
        tiebreak_hash: component_tiebreak_hash_u64(poly),
    }
}

fn component_tiebreak_hash_u64(poly: &Polygon64) -> u64 {
    #[cfg(test)]
    {
        if COMPONENT_HASH_COUNTING_ENABLED.load(Ordering::Relaxed) {
            COMPONENT_HASH_CALLS.fetch_add(1, Ordering::Relaxed);
        }
    }

    let mut hasher = Sha256::new();
    hasher.update(b"cfr_ring_hash_v1");
    hash_ring(&mut hasher, &poly.outer);
    let holes = &poly.holes;
    hasher.update((holes.len() as u64).to_le_bytes());
    for hole in holes {
        hash_ring(&mut hasher, hole);
    }
    let digest = hasher.finalize();
    let mut first8 = [0_u8; 8];
    first8.copy_from_slice(&digest[..8]);
    u64::from_be_bytes(first8)
}

fn hash_ring(hasher: &mut Sha256, ring: &[Point64]) {
    hasher.update((ring.len() as u64).to_le_bytes());
    for point in ring {
        hasher.update(point.x.to_le_bytes());
        hasher.update(point.y.to_le_bytes());
    }
}

fn min_point(poly: &Polygon64) -> Point64 {
    poly.outer
        .iter()
        .copied()
        .min_by_key(|p| (p.x, p.y))
        .unwrap_or(Point64 { x: 0, y: 0 })
}

fn vertex_count(poly: &Polygon64) -> usize {
    poly.outer.len() + poly.holes.iter().map(Vec::len).sum::<usize>()
}

fn component_area_abs(poly: &Polygon64) -> i128 {
    let outer = signed_area2_i128(&poly.outer).abs();
    let holes_sum: i128 = poly
        .holes
        .iter()
        .map(|hole| signed_area2_i128(hole).abs())
        .sum();
    outer.saturating_sub(holes_sum)
}

fn compare_ring_lex(a: &[Point64], b: &[Point64]) -> std::cmp::Ordering {
    let limit = a.len().min(b.len());
    for idx in 0..limit {
        let pa = a[idx];
        let pb = b[idx];
        let ord = pa.x.cmp(&pb.x).then(pa.y.cmp(&pb.y));
        if !ord.is_eq() {
            return ord;
        }
    }
    a.len().cmp(&b.len())
}

fn signed_area2_i128(points: &[Point64]) -> i128 {
    if points.len() < 3 {
        return 0;
    }
    let mut area2 = 0_i128;
    for idx in 0..points.len() {
        let p0 = points[idx];
        let p1 = points[(idx + 1) % points.len()];
        area2 += (p0.x as i128) * (p1.y as i128) - (p1.x as i128) * (p0.y as i128);
    }
    area2
}

#[cfg(test)]
fn reset_component_tiebreak_hash_call_count() {
    COMPONENT_HASH_CALLS.store(0, Ordering::Relaxed);
}

#[cfg(test)]
fn component_tiebreak_hash_call_count() -> usize {
    COMPONENT_HASH_CALLS.load(Ordering::Relaxed)
}

#[cfg(test)]
fn set_component_tiebreak_hash_counting(enabled: bool) {
    COMPONENT_HASH_COUNTING_ENABLED.store(enabled, Ordering::Relaxed);
}

#[derive(Debug, Clone, Copy)]
struct OverlayBounds {
    min_x: i64,
    min_y: i64,
    shift: u32,
}

impl OverlayBounds {
    fn from_polygons(polys: &[&Polygon64]) -> Option<Self> {
        let mut min_x = i64::MAX;
        let mut min_y = i64::MAX;
        let mut max_x = i64::MIN;
        let mut max_y = i64::MIN;

        for poly in polys {
            for point in &poly.outer {
                min_x = min_x.min(point.x);
                min_y = min_y.min(point.y);
                max_x = max_x.max(point.x);
                max_y = max_y.max(point.y);
            }
            for hole in &poly.holes {
                for point in hole {
                    min_x = min_x.min(point.x);
                    min_y = min_y.min(point.y);
                    max_x = max_x.max(point.x);
                    max_y = max_y.max(point.y);
                }
            }
        }

        if min_x == i64::MAX || min_y == i64::MAX {
            return None;
        }

        let span_x = max_x.checked_sub(min_x)?;
        let span_y = max_y.checked_sub(min_y)?;
        let mut max_span = span_x.max(span_y);
        let mut shift = 0_u32;
        while max_span > i32::MAX as i64 {
            max_span = (max_span + 1) >> 1;
            shift = shift.checked_add(1)?;
        }

        Some(Self {
            min_x,
            min_y,
            shift,
        })
    }

    fn encode_x(self, x: i64) -> Option<i32> {
        self.encode_coord(x, self.min_x)
    }

    fn encode_y(self, y: i64) -> Option<i32> {
        self.encode_coord(y, self.min_y)
    }

    fn decode_x(self, x: i32) -> Option<i64> {
        self.decode_coord(x, self.min_x)
    }

    fn decode_y(self, y: i32) -> Option<i64> {
        self.decode_coord(y, self.min_y)
    }

    fn encode_coord(self, value: i64, min: i64) -> Option<i32> {
        let translated = value.checked_sub(min)?;
        let scaled = if self.shift == 0 {
            translated
        } else {
            translated >> self.shift
        };
        i32::try_from(scaled).ok()
    }

    fn decode_coord(self, value: i32, min: i64) -> Option<i64> {
        let scaled = (value as i64).checked_shl(self.shift)?;
        min.checked_add(scaled)
    }
}

#[cfg(test)]
mod tests {
    use crate::geometry::types::{Point64, Polygon64};

    use super::{
        canonicalize_ring, component_tiebreak_hash_call_count, compute_cfr,
        reset_component_tiebreak_hash_call_count, set_component_tiebreak_hash_counting,
        sort_components,
    };

    fn rect(x0: i64, y0: i64, w: i64, h: i64) -> Polygon64 {
        Polygon64 {
            outer: vec![
                Point64 { x: x0, y: y0 },
                Point64 { x: x0 + w, y: y0 },
                Point64 {
                    x: x0 + w,
                    y: y0 + h,
                },
                Point64 { x: x0, y: y0 + h },
            ],
            holes: Vec::new(),
        }
    }

    #[test]
    fn empty_nfp_returns_ifp_single_component() {
        let ifp = rect(10, 20, 30, 40);
        let cfr = compute_cfr(&ifp, &[]);
        assert_eq!(cfr.len(), 1);
        assert_eq!(
            cfr[0].outer,
            vec![
                Point64 { x: 10, y: 20 },
                Point64 { x: 40, y: 20 },
                Point64 { x: 40, y: 60 },
                Point64 { x: 10, y: 60 },
            ]
        );
    }

    #[test]
    fn rect_minus_rect_is_deterministic_and_not_empty() {
        let ifp = rect(0, 0, 20, 20);
        let blocker = rect(6, 6, 4, 4);
        let a = compute_cfr(&ifp, std::slice::from_ref(&blocker));
        let b = compute_cfr(&ifp, std::slice::from_ref(&blocker));

        assert_eq!(a, b, "CFR must be deterministic");
        assert!(
            !a.is_empty(),
            "CFR must keep at least one feasible component"
        );
        assert!(
            a.iter().any(|poly| !poly.holes.is_empty()) || a.len() > 1,
            "rect-minus-rect should keep a stable hole/component structure"
        );
    }

    #[test]
    fn canonicalize_ring_normalizes_startpoint() {
        let mut a = vec![
            Point64 { x: 0, y: 0 },
            Point64 { x: 4, y: 0 },
            Point64 { x: 4, y: 3 },
            Point64 { x: 0, y: 3 },
        ];
        let mut b = vec![
            Point64 { x: 4, y: 3 },
            Point64 { x: 0, y: 3 },
            Point64 { x: 0, y: 0 },
            Point64 { x: 4, y: 0 },
        ];

        assert!(canonicalize_ring(&mut a, true));
        assert!(canonicalize_ring(&mut b, true));
        assert_eq!(a, b);
        assert_eq!(a[0], Point64 { x: 0, y: 0 });
    }

    #[test]
    fn canonicalize_ring_normalizes_orientation() {
        let mut ccw = vec![
            Point64 { x: 0, y: 0 },
            Point64 { x: 5, y: 0 },
            Point64 { x: 5, y: 2 },
            Point64 { x: 0, y: 2 },
        ];
        let mut cw = vec![
            Point64 { x: 0, y: 0 },
            Point64 { x: 0, y: 2 },
            Point64 { x: 5, y: 2 },
            Point64 { x: 5, y: 0 },
        ];

        assert!(canonicalize_ring(&mut ccw, true));
        assert!(canonicalize_ring(&mut cw, true));
        assert_eq!(ccw, cw);
    }

    #[test]
    fn cfr_component_order_is_stable_for_permuted_nfp_inputs() {
        let ifp = rect(0, 0, 30, 10);
        let blocker_a = rect(9, 0, 2, 10);
        let blocker_b = rect(19, 0, 2, 10);

        let ab = compute_cfr(&ifp, &[blocker_a.clone(), blocker_b.clone()]);
        let ba = compute_cfr(&ifp, &[blocker_b, blocker_a]);

        assert_eq!(ab, ba, "component ordering must be stable");
        assert!(
            ab.len() >= 2,
            "fixture must produce multiple CFR components"
        );
    }

    #[test]
    fn cfr_sort_key_precompute_hash_called_once_per_component() {
        fn poly(points: &[[i64; 2]]) -> Polygon64 {
            Polygon64 {
                outer: points
                    .iter()
                    .map(|p| Point64 { x: p[0], y: p[1] })
                    .collect(),
                holes: Vec::new(),
            }
        }

        let components = vec![
            poly(&[[0, 0], [20, 0], [20, 5], [0, 5]]),
            poly(&[[0, 0], [10, 0], [10, 10], [0, 10]]),
            poly(&[[0, 0], [25, 0], [25, 4], [0, 4]]),
            poly(&[[0, 0], [5, 0], [5, 20], [0, 20]]),
            poly(&[[0, 0], [50, 0], [50, 2], [0, 2]]),
            poly(&[[0, 0], [4, 0], [4, 25], [0, 25]]),
        ];
        let expected = components.len();

        set_component_tiebreak_hash_counting(true);
        reset_component_tiebreak_hash_call_count();
        let sorted = sort_components(components);
        set_component_tiebreak_hash_counting(false);
        assert_eq!(sorted.len(), expected);

        let calls = component_tiebreak_hash_call_count();
        assert_eq!(
            calls, expected,
            "component_tiebreak_hash_u64 should be called exactly once per component"
        );
    }
}
