use std::cmp::Ordering;
use std::collections::{HashSet, hash_map::DefaultHasher};
use std::hash::Hasher;

use i_overlay::{
    core::{
        fill_rule::FillRule, overlay::IntOverlayOptions, overlay::Overlay,
        overlay_rule::OverlayRule,
        solver::{Precision, Solver, Strategy},
    },
    i_float::int::point::IntPoint,
    i_shape::int::shape::{IntContour, IntShape},
};

use crate::geometry::types::{
    cross_product_i128, is_ccw, is_convex, signed_area2_i128, Point64, Polygon64,
};
use crate::nfp::boundary_clean::{clean_polygon_boundary, ring_has_self_intersection};

use super::{NfpError, convex::compute_convex_nfp};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConcaveNfpMode {
    StableDefault,
    ExactOrbit,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ConcaveNfpOptions {
    pub mode: ConcaveNfpMode,
    pub max_steps: usize,
    pub enable_fallback: bool,
}

impl Default for ConcaveNfpOptions {
    fn default() -> Self {
        Self {
            mode: ConcaveNfpMode::StableDefault,
            max_steps: 1_024,
            enable_fallback: true,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct TouchingContact {
    edge_a: usize,
    edge_b: usize,
    point: Point64,
}

pub fn compute_concave_nfp(
    a: &Polygon64,
    b: &Polygon64,
    options: ConcaveNfpOptions,
) -> Result<Polygon64, NfpError> {
    match options.mode {
        ConcaveNfpMode::StableDefault => compute_stable_concave_nfp(a, b),
        ConcaveNfpMode::ExactOrbit => match compute_orbit_exact_nfp(a, b, options) {
            Ok(nfp) => Ok(nfp),
            Err(_) if options.enable_fallback => compute_stable_concave_nfp(a, b),
            Err(err) => Err(err),
        },
    }
}

pub fn compute_concave_nfp_default(a: &Polygon64, b: &Polygon64) -> Result<Polygon64, NfpError> {
    compute_concave_nfp(a, b, ConcaveNfpOptions::default())
}

fn compute_stable_concave_nfp(a: &Polygon64, b: &Polygon64) -> Result<Polygon64, NfpError> {
    if a.outer.len() < 3 || b.outer.len() < 3 {
        return Err(NfpError::EmptyPolygon);
    }
    if !a.holes.is_empty() || !b.holes.is_empty() {
        return Err(NfpError::DecompositionFailed);
    }

    let convex_parts_a = decompose_to_convex_parts(&a.outer)?;
    let convex_parts_b = decompose_to_convex_parts(&b.outer)?;
    if convex_parts_a.is_empty() || convex_parts_b.is_empty() {
        return Err(NfpError::DecompositionFailed);
    }

    let mut partial_nfpc: Vec<Polygon64> = Vec::new();
    for part_a in &convex_parts_a {
        for part_b in &convex_parts_b {
            let nfp = compute_convex_nfp(part_a, part_b)?;
            partial_nfpc.push(nfp);
        }
    }

    let unioned = union_nfp_fragments(&partial_nfpc)?;
    clean_polygon_boundary(&unioned)
}

fn compute_orbit_exact_nfp(
    a: &Polygon64,
    b: &Polygon64,
    options: ConcaveNfpOptions,
) -> Result<Polygon64, NfpError> {
    let ring_a = normalize_simple_ring(&a.outer)?;
    let ring_b = normalize_simple_ring(&b.outer)?;
    if ring_a.len() < 3 || ring_b.len() < 3 {
        return Err(NfpError::EmptyPolygon);
    }

    let mut orbit: Vec<Point64> = Vec::new();
    let start = Point64 {
        x: ring_a[0].x - ring_b[0].x,
        y: ring_a[0].y - ring_b[0].y,
    };
    let mut current = start;
    orbit.push(start);

    let mut visited: HashSet<u64> = HashSet::new();
    let max_steps = options.max_steps.max(1);

    for _ in 0..max_steps {
        let touching_group = build_touching_group(&ring_a, &ring_b, current);
        let signature = hash_state(current, &touching_group);
        if !visited.insert(signature) {
            return Err(NfpError::OrbitLoopDetected);
        }

        let candidates = build_candidate_slide_vectors(&ring_a, &ring_b, &touching_group);
        if candidates.is_empty() {
            return Err(NfpError::OrbitLoopDetected);
        }

        let mut moved = false;
        for delta in candidates {
            if delta.x == 0 && delta.y == 0 {
                continue;
            }
            let next = Point64 {
                x: current.x + delta.x,
                y: current.y + delta.y,
            };
            if next == current {
                continue;
            }

            if orbit.len() > 2 && next == start {
                orbit.push(next);
                let orbit_poly = Polygon64 {
                    outer: orbit,
                    holes: Vec::new(),
                };
                return clean_polygon_boundary(&orbit_poly);
            }

            current = next;
            orbit.push(current);
            moved = true;
            break;
        }

        if !moved {
            return Err(NfpError::OrbitLoopDetected);
        }
    }

    Err(NfpError::OrbitLoopDetected)
}

fn decompose_to_convex_parts(ring: &[Point64]) -> Result<Vec<Polygon64>, NfpError> {
    let ring = normalize_simple_ring(ring)?;
    if ring.len() < 3 {
        return Err(NfpError::DecompositionFailed);
    }

    if is_convex(&ring) {
        return Ok(vec![Polygon64 {
            outer: ring,
            holes: Vec::new(),
        }]);
    }

    let triangles = ear_clip_triangulate(&ring)?;
    if triangles.is_empty() {
        return Err(NfpError::DecompositionFailed);
    }

    let mut out = Vec::with_capacity(triangles.len());
    for tri in triangles {
        let mut outer = tri.to_vec();
        if !is_ccw(&outer) {
            outer.reverse();
        }
        out.push(Polygon64 {
            outer,
            holes: Vec::new(),
        });
    }

    Ok(out)
}

fn normalize_simple_ring(points: &[Point64]) -> Result<Vec<Point64>, NfpError> {
    let mut ring: Vec<Point64> = Vec::with_capacity(points.len());
    for &p in points {
        if ring.last().copied() != Some(p) {
            ring.push(p);
        }
    }
    if ring.len() > 1 && ring.first() == ring.last() {
        ring.pop();
    }
    if ring.len() < 3 {
        return Err(NfpError::EmptyPolygon);
    }

    if !is_ccw(&ring) {
        ring.reverse();
    }
    if ring_has_self_intersection(&ring) {
        return Err(NfpError::DecompositionFailed);
    }
    Ok(ring)
}

fn ear_clip_triangulate(ring: &[Point64]) -> Result<Vec<[Point64; 3]>, NfpError> {
    let n = ring.len();
    if n < 3 {
        return Err(NfpError::DecompositionFailed);
    }

    let mut remaining: Vec<usize> = (0..n).collect();
    let mut triangles = Vec::with_capacity(n.saturating_sub(2));
    let mut guard = 0usize;
    let max_guard = n * n * 4;

    while remaining.len() > 3 {
        if guard > max_guard {
            return Err(NfpError::DecompositionFailed);
        }
        guard += 1;

        let mut ear_found = false;
        let m = remaining.len();
        for i in 0..m {
            let prev_idx = remaining[(i + m - 1) % m];
            let curr_idx = remaining[i];
            let next_idx = remaining[(i + 1) % m];

            let prev = ring[prev_idx];
            let curr = ring[curr_idx];
            let next = ring[next_idx];

            let turn = cross_product_i128(
                curr.x - prev.x,
                curr.y - prev.y,
                next.x - curr.x,
                next.y - curr.y,
            );
            if turn <= 0 {
                continue;
            }

            let mut contains_other = false;
            for &other_idx in &remaining {
                if other_idx == prev_idx || other_idx == curr_idx || other_idx == next_idx {
                    continue;
                }
                if point_in_or_on_triangle(ring[other_idx], prev, curr, next) {
                    contains_other = true;
                    break;
                }
            }
            if contains_other {
                continue;
            }

            triangles.push([prev, curr, next]);
            remaining.remove(i);
            ear_found = true;
            break;
        }

        if !ear_found {
            return Err(NfpError::DecompositionFailed);
        }
    }

    if remaining.len() == 3 {
        triangles.push([ring[remaining[0]], ring[remaining[1]], ring[remaining[2]]]);
    }
    Ok(triangles)
}

fn point_in_or_on_triangle(p: Point64, a: Point64, b: Point64, c: Point64) -> bool {
    let o1 = orient(a, b, p);
    let o2 = orient(b, c, p);
    let o3 = orient(c, a, p);

    let has_pos = o1 > 0 || o2 > 0 || o3 > 0;
    let has_neg = o1 < 0 || o2 < 0 || o3 < 0;
    !(has_pos && has_neg)
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

fn union_nfp_fragments(fragments: &[Polygon64]) -> Result<Polygon64, NfpError> {
    if fragments.is_empty() {
        return Err(NfpError::DecompositionFailed);
    }

    let bounds =
        OverlayBounds::from_fragments(fragments).ok_or(NfpError::DecompositionFailed)?;
    let subject_shapes: Vec<IntShape> = fragments
        .iter()
        .map(|poly| encode_overlay_contour(&poly.outer, bounds).map(|contour| vec![contour]))
        .collect::<Result<Vec<_>, _>>()?;

    let empty_shapes: [IntShape; 0] = [];
    let mut overlay = Overlay::with_shapes_options(
        &subject_shapes,
        &empty_shapes,
        IntOverlayOptions::keep_all_points(),
        Solver::with_strategy_and_precision(Strategy::List, Precision::ABSOLUTE),
    );
    let unioned = overlay.overlay(OverlayRule::Union, FillRule::NonZero);

    let mut best: Option<(i128, Vec<Point64>, Polygon64)> = None;
    for shape in unioned {
        if shape.is_empty() {
            continue;
        }

        let outer = restore_axis_notches(&decode_overlay_contour(&shape[0], bounds)?, fragments);
        if outer.len() < 3 {
            continue;
        }
        let candidate = Polygon64 {
            outer: outer.clone(),
            holes: Vec::new(),
        };
        let area = signed_area2_i128(&outer).abs();
        let key = canonical_key(&outer);
        match &best {
            None => best = Some((area, key, candidate)),
            Some((best_area, best_key, _)) => {
                if area > *best_area || (area == *best_area && lex_less(&key, best_key)) {
                    best = Some((area, key, candidate));
                }
            }
        }
    }

    best.map(|(_, _, poly)| poly)
        .ok_or(NfpError::DecompositionFailed)
}

#[derive(Debug, Clone, Copy)]
struct OverlayBounds {
    min_x: i64,
    min_y: i64,
    shift: u32,
}

impl OverlayBounds {
    fn from_fragments(fragments: &[Polygon64]) -> Option<Self> {
        let mut min_x = i64::MAX;
        let mut min_y = i64::MAX;
        let mut max_x = i64::MIN;
        let mut max_y = i64::MIN;

        for fragment in fragments {
            for point in &fragment.outer {
                min_x = min_x.min(point.x);
                min_y = min_y.min(point.y);
                max_x = max_x.max(point.x);
                max_y = max_y.max(point.y);
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

fn encode_overlay_contour(points: &[Point64], bounds: OverlayBounds) -> Result<IntContour, NfpError> {
    let mut contour = Vec::with_capacity(points.len());
    for point in points {
        let x = bounds
            .encode_x(point.x)
            .ok_or(NfpError::DecompositionFailed)?;
        let y = bounds
            .encode_y(point.y)
            .ok_or(NfpError::DecompositionFailed)?;
        contour.push(IntPoint::new(x, y));
    }
    Ok(contour)
}

fn decode_overlay_contour(contour: &IntContour, bounds: OverlayBounds) -> Result<Vec<Point64>, NfpError> {
    let mut outer = Vec::with_capacity(contour.len());
    for point in contour {
        let x = bounds
            .decode_x(point.x)
            .ok_or(NfpError::DecompositionFailed)?;
        let y = bounds
            .decode_y(point.y)
            .ok_or(NfpError::DecompositionFailed)?;
        outer.push(Point64 { x, y });
    }
    Ok(outer)
}

fn restore_axis_notches(ring: &[Point64], fragments: &[Polygon64]) -> Vec<Point64> {
    let n = ring.len();
    if n < 3 {
        return ring.to_vec();
    }

    let mut out = Vec::with_capacity(n * 2);
    for i in 0..n {
        let prev = ring[(i + n - 1) % n];
        let curr = ring[i];
        let next = ring[(i + 1) % n];
        let next_next = ring[(i + 2) % n];
        out.push(curr);

        let dx = next.x - curr.x;
        let dy = next.y - curr.y;
        if dx == 0 || dy == 0 {
            continue;
        }
        if dx.abs() > 1 && dy.abs() > 1 {
            continue;
        }

        let candidates = [
            Point64 {
                x: curr.x,
                y: next.y,
            },
            Point64 {
                x: next.x,
                y: curr.y,
            },
        ];

        let mut chosen: Option<Point64> = None;
        for candidate in candidates {
            if candidate == curr
                || candidate == next
                || candidate == prev
                || candidate == next_next
            {
                continue;
            }
            if !point_in_any_fragment(candidate, fragments) {
                continue;
            }

            chosen = match chosen {
                None => Some(candidate),
                Some(current) => {
                    let current_key = (current.x, current.y);
                    let candidate_key = (candidate.x, candidate.y);
                    if candidate_key < current_key {
                        Some(candidate)
                    } else {
                        Some(current)
                    }
                }
            };
        }

        if let Some(candidate) = chosen {
            out.push(candidate);
        }
    }

    out
}

fn point_in_any_fragment(point: Point64, fragments: &[Polygon64]) -> bool {
    fragments
        .iter()
        .any(|fragment| point_in_or_on_ring(point, &fragment.outer))
}

fn point_in_or_on_ring(point: Point64, ring: &[Point64]) -> bool {
    let n = ring.len();
    if n < 3 {
        return false;
    }

    for i in 0..n {
        let a = ring[i];
        let b = ring[(i + 1) % n];
        if point_on_segment_inclusive(a, b, point) {
            return true;
        }
    }

    let mut winding = 0_i32;
    for i in 0..n {
        let a = ring[i];
        let b = ring[(i + 1) % n];

        if a.y <= point.y {
            if b.y > point.y {
                let cross =
                    cross_product_i128(b.x - a.x, b.y - a.y, point.x - a.x, point.y - a.y);
                if cross > 0 {
                    winding += 1;
                }
            }
        } else if b.y <= point.y {
            let cross = cross_product_i128(b.x - a.x, b.y - a.y, point.x - a.x, point.y - a.y);
            if cross < 0 {
                winding -= 1;
            }
        }
    }

    winding != 0
}

fn canonical_key(points: &[Point64]) -> Vec<Point64> {
    let mut ring = points.to_vec();
    if ring.len() > 1 && ring.first() == ring.last() {
        ring.pop();
    }
    if signed_area2_i128(&ring) < 0 {
        ring.reverse();
    }
    if ring.is_empty() {
        return ring;
    }

    let start = ring
        .iter()
        .enumerate()
        .min_by_key(|(_, p)| (p.x, p.y))
        .map(|(idx, _)| idx)
        .unwrap_or(0);
    ring.rotate_left(start);
    ring
}

fn lex_less(lhs: &[Point64], rhs: &[Point64]) -> bool {
    let n = lhs.len().min(rhs.len());
    for i in 0..n {
        let c = lhs[i].x.cmp(&rhs[i].x).then(lhs[i].y.cmp(&rhs[i].y));
        if c != Ordering::Equal {
            return c == Ordering::Less;
        }
    }
    lhs.len() < rhs.len()
}

fn build_touching_group(a: &[Point64], b: &[Point64], translation: Point64) -> Vec<TouchingContact> {
    let mut group = Vec::new();

    for edge_a in 0..a.len() {
        let a0 = a[edge_a];
        let a1 = a[(edge_a + 1) % a.len()];
        for edge_b in 0..b.len() {
            let b0 = translated_point(b[edge_b], translation);
            let b1 = translated_point(b[(edge_b + 1) % b.len()], translation);
            if segments_intersect_or_touch(a0, a1, b0, b1) {
                let point = min_lex_point([a0, a1, b0, b1]);
                group.push(TouchingContact {
                    edge_a,
                    edge_b,
                    point,
                });
            }
        }
    }

    group.sort_by(|lhs, rhs| {
        lhs.edge_a
            .cmp(&rhs.edge_a)
            .then(lhs.edge_b.cmp(&rhs.edge_b))
            .then(lhs.point.x.cmp(&rhs.point.x))
            .then(lhs.point.y.cmp(&rhs.point.y))
    });
    group.dedup();
    group
}

fn translated_point(p: Point64, translation: Point64) -> Point64 {
    Point64 {
        x: p.x + translation.x,
        y: p.y + translation.y,
    }
}

fn build_candidate_slide_vectors(
    a: &[Point64],
    b: &[Point64],
    touching_group: &[TouchingContact],
) -> Vec<Point64> {
    let mut vectors = Vec::new();

    for contact in touching_group {
        let edge_a = edge_vector(a, contact.edge_a);
        let edge_b = edge_vector(b, contact.edge_b);

        if let Some(v) = normalize_vector(edge_a) {
            vectors.push(v);
        }
        if let Some(v) = normalize_vector(Point64 {
            x: -edge_b.x,
            y: -edge_b.y,
        }) {
            vectors.push(v);
        }
    }

    if vectors.is_empty() {
        for edge_idx in 0..a.len().min(8) {
            if let Some(v) = normalize_vector(edge_vector(a, edge_idx)) {
                vectors.push(v);
            }
        }
        for edge_idx in 0..b.len().min(8) {
            if let Some(v) = normalize_vector(Point64 {
                x: -edge_vector(b, edge_idx).x,
                y: -edge_vector(b, edge_idx).y,
            }) {
                vectors.push(v);
            }
        }
    }

    vectors.sort_by(vector_angle_cmp);
    vectors.dedup();
    vectors
}

fn edge_vector(ring: &[Point64], edge_idx: usize) -> Point64 {
    let a = ring[edge_idx];
    let b = ring[(edge_idx + 1) % ring.len()];
    Point64 {
        x: b.x - a.x,
        y: b.y - a.y,
    }
}

fn normalize_vector(v: Point64) -> Option<Point64> {
    if v.x == 0 && v.y == 0 {
        return None;
    }
    let g = gcd_i64(v.x.abs(), v.y.abs()).max(1);
    Some(Point64 {
        x: v.x / g,
        y: v.y / g,
    })
}

fn vector_angle_cmp(lhs: &Point64, rhs: &Point64) -> Ordering {
    let lhs_half = if lhs.y > 0 || (lhs.y == 0 && lhs.x >= 0) {
        0
    } else {
        1
    };
    let rhs_half = if rhs.y > 0 || (rhs.y == 0 && rhs.x >= 0) {
        0
    } else {
        1
    };
    if lhs_half != rhs_half {
        return lhs_half.cmp(&rhs_half);
    }

    let cross = cross_product_i128(lhs.x, lhs.y, rhs.x, rhs.y);
    if cross > 0 {
        Ordering::Less
    } else if cross < 0 {
        Ordering::Greater
    } else {
        lhs.x.cmp(&rhs.x).then(lhs.y.cmp(&rhs.y))
    }
}

fn gcd_i64(mut a: i64, mut b: i64) -> i64 {
    while b != 0 {
        let r = a % b;
        a = b;
        b = r;
    }
    a.abs()
}

fn hash_state(translation: Point64, touching_group: &[TouchingContact]) -> u64 {
    let mut hasher = DefaultHasher::new();
    hasher.write_i64(translation.x);
    hasher.write_i64(translation.y);
    for contact in touching_group {
        hasher.write_usize(contact.edge_a);
        hasher.write_usize(contact.edge_b);
        hasher.write_i64(contact.point.x);
        hasher.write_i64(contact.point.y);
    }
    hasher.finish()
}

fn min_lex_point(points: [Point64; 4]) -> Point64 {
    points
        .into_iter()
        .min_by_key(|p| (p.x, p.y))
        .unwrap_or(Point64 { x: 0, y: 0 })
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
    use crate::geometry::types::Point64;

    use super::{
        ConcaveNfpMode, ConcaveNfpOptions, compute_concave_nfp, compute_concave_nfp_default,
        decompose_to_convex_parts,
    };
    use crate::nfp::boundary_clean::ring_has_self_intersection;
    use crate::geometry::types::Polygon64;

    fn poly(points: &[[i64; 2]]) -> Polygon64 {
        Polygon64 {
            outer: points
                .iter()
                .map(|p| Point64 { x: p[0], y: p[1] })
                .collect(),
            holes: Vec::new(),
        }
    }

    #[test]
    fn decomposition_splits_l_shape_into_triangles() {
        let l_shape = vec![
            Point64 { x: 0, y: 0 },
            Point64 { x: 4, y: 0 },
            Point64 { x: 4, y: 1 },
            Point64 { x: 1, y: 1 },
            Point64 { x: 1, y: 4 },
            Point64 { x: 0, y: 4 },
        ];
        let parts = decompose_to_convex_parts(&l_shape).expect("decomposition should succeed");
        assert!(parts.len() >= 2, "concave ring should be split to multiple parts");
    }

    #[test]
    fn stable_concave_nfp_is_deterministic_and_simple() {
        let a = poly(&[[0, 0], [4, 0], [4, 1], [1, 1], [1, 4], [0, 4]]);
        let b = poly(&[[0, 0], [2, 0], [2, 3], [1, 3], [1, 1], [0, 1]]);

        let nfp_1 = compute_concave_nfp_default(&a, &b).expect("stable concave nfp");
        let nfp_2 = compute_concave_nfp_default(&a, &b).expect("stable concave nfp");
        assert_eq!(nfp_1.outer, nfp_2.outer);
        assert!(!ring_has_self_intersection(&nfp_1.outer));
    }

    #[test]
    fn exact_mode_falls_back_to_stable_when_loop_detected() {
        let a = poly(&[[0, 0], [4, 0], [4, 1], [1, 1], [1, 4], [0, 4]]);
        let b = poly(&[[0, 0], [2, 0], [2, 3], [1, 3], [1, 1], [0, 1]]);

        let stable = compute_concave_nfp_default(&a, &b).expect("stable path");
        let exact = compute_concave_nfp(
            &a,
            &b,
            ConcaveNfpOptions {
                mode: ConcaveNfpMode::ExactOrbit,
                max_steps: 8,
                enable_fallback: true,
            },
        )
        .expect("exact mode with fallback should succeed");

        assert_eq!(stable.outer, exact.outer);
    }
}
