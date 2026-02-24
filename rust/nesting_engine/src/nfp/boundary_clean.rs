use crate::geometry::types::{cross_product_i128, is_ccw, Point64, Polygon64};

use super::NfpError;

/// Canonical, deterministic boundary cleanup for NFP output.
///
/// Guarantees:
/// - no closing duplicate vertex
/// - no consecutive duplicate points
/// - no zero-length edges
/// - no collinear middle points
/// - CCW orientation
/// - lexicographically minimal start point
/// - no self-intersection
pub fn clean_polygon_boundary(polygon: &Polygon64) -> Result<Polygon64, NfpError> {
    let mut ring = canonicalize_ring(&polygon.outer)?;

    if ring_has_self_intersection(&ring) {
        return Err(NfpError::NotSimpleOutput);
    }

    if !is_ccw(&ring) {
        ring.reverse();
    }
    rotate_to_lexicographic_min(&mut ring);

    if ring.len() < 3 || ring_has_self_intersection(&ring) {
        return Err(NfpError::NotSimpleOutput);
    }

    Ok(Polygon64 {
        outer: ring,
        holes: Vec::new(),
    })
}

/// Returns true when the ring has at least one self-intersection.
pub fn ring_has_self_intersection(points: &[Point64]) -> bool {
    let n = points.len();
    if n < 4 {
        return false;
    }

    for i in 0..n {
        let a0 = points[i];
        let a1 = points[(i + 1) % n];
        if a0 == a1 {
            return true;
        }

        for j in (i + 1)..n {
            let a_adjacent = j == i || (i + 1) % n == j || (j + 1) % n == i;
            if a_adjacent {
                continue;
            }

            let b0 = points[j];
            let b1 = points[(j + 1) % n];
            if segments_intersect(a0, a1, b0, b1) {
                return true;
            }
        }
    }

    false
}

pub fn canonicalize_ring(points: &[Point64]) -> Result<Vec<Point64>, NfpError> {
    let mut ring = dedup_closed_ring(points);
    if ring.len() < 3 {
        return Err(NfpError::EmptyPolygon);
    }

    simplify_ring(&mut ring);
    if ring.len() < 3 {
        return Err(NfpError::NotSimpleOutput);
    }

    Ok(ring)
}

fn dedup_closed_ring(points: &[Point64]) -> Vec<Point64> {
    if points.is_empty() {
        return Vec::new();
    }

    let mut out = Vec::with_capacity(points.len());
    for &p in points {
        if out.last().copied() != Some(p) {
            out.push(p);
        }
    }

    if out.len() > 1 && out.first() == out.last() {
        out.pop();
    }

    out
}

fn simplify_ring(ring: &mut Vec<Point64>) {
    loop {
        if ring.len() < 3 {
            return;
        }

        let mut changed = false;
        let n = ring.len();
        let mut keep = vec![true; n];

        for i in 0..n {
            let prev = ring[(i + n - 1) % n];
            let curr = ring[i];
            let next = ring[(i + 1) % n];

            if curr == prev || curr == next {
                keep[i] = false;
                changed = true;
                continue;
            }

            let cross = cross_product_i128(
                curr.x - prev.x,
                curr.y - prev.y,
                next.x - curr.x,
                next.y - curr.y,
            );
            if cross == 0 && point_on_segment_inclusive(prev, next, curr) {
                keep[i] = false;
                changed = true;
            }
        }

        if !changed {
            break;
        }

        let mut filtered = Vec::with_capacity(ring.len());
        for (idx, p) in ring.iter().enumerate() {
            if keep[idx] {
                filtered.push(*p);
            }
        }
        *ring = filtered;
    }
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

fn orientation(a: Point64, b: Point64, c: Point64) -> i8 {
    let v = cross_product_i128(b.x - a.x, b.y - a.y, c.x - a.x, c.y - a.y);
    if v > 0 {
        1
    } else if v < 0 {
        -1
    } else {
        0
    }
}

fn segments_intersect(a0: Point64, a1: Point64, b0: Point64, b1: Point64) -> bool {
    let o1 = orientation(a0, a1, b0);
    let o2 = orientation(a0, a1, b1);
    let o3 = orientation(b0, b1, a0);
    let o4 = orientation(b0, b1, a1);

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
    use super::{clean_polygon_boundary, ring_has_self_intersection};
    use crate::geometry::types::{is_ccw, Point64, Polygon64};
    use crate::nfp::NfpError;

    #[test]
    fn clean_removes_duplicates_collinear_and_canonicalizes() {
        let poly = Polygon64 {
            outer: vec![
                Point64 { x: 2, y: 0 },
                Point64 { x: 2, y: 0 },
                Point64 { x: 2, y: 2 },
                Point64 { x: 1, y: 2 },
                Point64 { x: 0, y: 2 },
                Point64 { x: 0, y: 0 },
                Point64 { x: 2, y: 0 },
            ],
            holes: Vec::new(),
        };

        let cleaned = clean_polygon_boundary(&poly).expect("cleaning should succeed");
        assert_eq!(
            cleaned.outer,
            vec![
                Point64 { x: 0, y: 0 },
                Point64 { x: 2, y: 0 },
                Point64 { x: 2, y: 2 },
                Point64 { x: 0, y: 2 },
            ]
        );
        assert!(is_ccw(&cleaned.outer));
    }

    #[test]
    fn clean_rejects_self_intersection() {
        let bow = Polygon64 {
            outer: vec![
                Point64 { x: 0, y: 0 },
                Point64 { x: 2, y: 2 },
                Point64 { x: 0, y: 2 },
                Point64 { x: 2, y: 0 },
            ],
            holes: Vec::new(),
        };
        let err = clean_polygon_boundary(&bow).expect_err("self intersection must fail");
        assert_eq!(err, NfpError::NotSimpleOutput);
    }

    #[test]
    fn self_intersection_detects_bow_tie() {
        let ring = vec![
            Point64 { x: 0, y: 0 },
            Point64 { x: 3, y: 3 },
            Point64 { x: 0, y: 3 },
            Point64 { x: 3, y: 0 },
        ];
        assert!(ring_has_self_intersection(&ring));
    }
}
