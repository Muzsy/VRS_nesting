use crate::geometry::types::{cross_product_i128, is_ccw, is_convex, Point64, Polygon64};

use super::NfpError;

/// Fast O(n+m) convex NFP via edge-vector merge on NFP(A, B) = A ⊕ (-B).
pub fn compute_convex_nfp(a: &Polygon64, b: &Polygon64) -> Result<Polygon64, NfpError> {
    let mut a_outer = normalize_ring(&a.outer);
    let mut b_outer = normalize_ring(&b.outer);

    if a_outer.len() < 3 || b_outer.len() < 3 {
        return Err(NfpError::EmptyPolygon);
    }

    debug_assert!(is_ccw(&a_outer), "convex NFP expects CCW polygon A");
    debug_assert!(is_ccw(&b_outer), "convex NFP expects CCW polygon B");

    if !is_convex(&a_outer) || !is_convex(&b_outer) {
        return Err(NfpError::NotConvex);
    }

    // Keep behavior deterministic even in release when debug asserts are disabled.
    if !is_ccw(&a_outer) {
        a_outer.reverse();
    }
    if !is_ccw(&b_outer) {
        b_outer.reverse();
    }

    let mut b_neg: Vec<Point64> = b_outer
        .iter()
        .map(|p| Point64 { x: -p.x, y: -p.y })
        .collect();

    let start_a = argmin_lex(&a_outer);
    let start_b = argmin_lex(&b_neg);
    a_outer.rotate_left(start_a);
    b_neg.rotate_left(start_b);

    let a_edges = edge_vectors(&a_outer);
    let b_edges = edge_vectors(&b_neg);

    let mut merged_edges: Vec<Point64> = Vec::with_capacity(a_edges.len() + b_edges.len());
    let mut i = 0usize;
    let mut j = 0usize;

    while i < a_edges.len() || j < b_edges.len() {
        if i == a_edges.len() {
            merged_edges.push(b_edges[j]);
            j += 1;
            continue;
        }
        if j == b_edges.len() {
            merged_edges.push(a_edges[i]);
            i += 1;
            continue;
        }

        let edge_a = a_edges[i];
        let edge_b = b_edges[j];
        let cross = cross_product_i128(edge_a.x, edge_a.y, edge_b.x, edge_b.y);

        if cross > 0 {
            merged_edges.push(edge_a);
            i += 1;
        } else if cross < 0 {
            merged_edges.push(edge_b);
            j += 1;
        } else {
            merged_edges.push(Point64 {
                x: edge_a.x + edge_b.x,
                y: edge_a.y + edge_b.y,
            });
            i += 1;
            j += 1;
        }
    }

    let mut current = Point64 {
        x: a_outer[0].x + b_neg[0].x,
        y: a_outer[0].y + b_neg[0].y,
    };

    let mut contour = Vec::with_capacity(merged_edges.len() + 1);
    contour.push(current);
    for edge in merged_edges {
        current = Point64 {
            x: current.x + edge.x,
            y: current.y + edge.y,
        };
        contour.push(current);
    }

    let contour = normalize_ring(&contour);
    if contour.len() < 3 {
        return Err(NfpError::NotConvex);
    }

    Ok(Polygon64 {
        outer: contour,
        holes: Vec::new(),
    })
}

/// Reference / fallback: pairwise vertex sums + Andrew monotone chain hull.
/// O(n×m×log(n×m)). Used for cross-checks and fallback paths.
pub fn compute_convex_nfp_reference(a: &Polygon64, b: &Polygon64) -> Result<Polygon64, NfpError> {
    let mut a_outer = normalize_ring(&a.outer);
    let mut b_outer = normalize_ring(&b.outer);

    if a_outer.len() < 3 || b_outer.len() < 3 {
        return Err(NfpError::EmptyPolygon);
    }

    debug_assert!(is_ccw(&a_outer), "convex NFP expects CCW polygon A");
    debug_assert!(is_ccw(&b_outer), "convex NFP expects CCW polygon B");

    if !is_convex(&a_outer) || !is_convex(&b_outer) {
        return Err(NfpError::NotConvex);
    }

    // Keep behavior deterministic even in release when debug asserts are disabled.
    if !is_ccw(&a_outer) {
        a_outer.reverse();
    }
    if !is_ccw(&b_outer) {
        b_outer.reverse();
    }

    let b_neg: Vec<Point64> = b_outer
        .iter()
        .map(|p| Point64 { x: -p.x, y: -p.y })
        .collect();

    let mut pairwise_sums = Vec::with_capacity(a_outer.len() * b_neg.len());
    for pa in &a_outer {
        for pb in &b_neg {
            pairwise_sums.push(Point64 {
                x: pa.x + pb.x,
                y: pa.y + pb.y,
            });
        }
    }

    let hull = convex_hull(pairwise_sums);
    if hull.len() < 3 {
        return Err(NfpError::NotConvex);
    }

    Ok(Polygon64 {
        outer: hull,
        holes: Vec::new(),
    })
}

fn argmin_lex(points: &[Point64]) -> usize {
    points
        .iter()
        .enumerate()
        .min_by_key(|(_, p)| (p.x, p.y))
        .map(|(idx, _)| idx)
        .unwrap_or(0)
}

fn edge_vectors(points: &[Point64]) -> Vec<Point64> {
    let n = points.len();
    let mut edges = Vec::with_capacity(n);
    for i in 0..n {
        let p0 = points[i];
        let p1 = points[(i + 1) % n];
        edges.push(Point64 {
            x: p1.x - p0.x,
            y: p1.y - p0.y,
        });
    }
    edges
}

fn normalize_ring(points: &[Point64]) -> Vec<Point64> {
    if points.is_empty() {
        return Vec::new();
    }

    let mut out: Vec<Point64> = Vec::with_capacity(points.len());
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

fn turn(a: Point64, b: Point64, c: Point64) -> i128 {
    cross_product_i128(b.x - a.x, b.y - a.y, c.x - a.x, c.y - a.y)
}

fn convex_hull(mut points: Vec<Point64>) -> Vec<Point64> {
    if points.len() <= 1 {
        return points;
    }

    points.sort_by(|lhs, rhs| lhs.x.cmp(&rhs.x).then(lhs.y.cmp(&rhs.y)));
    points.dedup();
    if points.len() <= 2 {
        return points;
    }

    let mut lower: Vec<Point64> = Vec::new();
    for &p in &points {
        while lower.len() >= 2 {
            let n = lower.len();
            if turn(lower[n - 2], lower[n - 1], p) <= 0 {
                lower.pop();
            } else {
                break;
            }
        }
        lower.push(p);
    }

    let mut upper: Vec<Point64> = Vec::new();
    for &p in points.iter().rev() {
        while upper.len() >= 2 {
            let n = upper.len();
            if turn(upper[n - 2], upper[n - 1], p) <= 0 {
                upper.pop();
            } else {
                break;
            }
        }
        upper.push(p);
    }

    lower.pop();
    upper.pop();
    lower.extend(upper);
    lower
}

#[cfg(test)]
mod tests {
    use crate::geometry::types::{Point64, Polygon64};

    use super::{compute_convex_nfp, compute_convex_nfp_reference};
    use crate::nfp::NfpError;

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
    fn rect_rect_manual_reference() {
        let a = rect(0, 0, 100, 50);
        let b = rect(0, 0, 60, 30);

        let nfp = compute_convex_nfp(&a, &b).expect("rect-rect NFP should be valid");
        assert_eq!(
            nfp.outer,
            vec![
                Point64 { x: -60, y: -30 },
                Point64 { x: 100, y: -30 },
                Point64 { x: 100, y: 50 },
                Point64 { x: -60, y: 50 },
            ]
        );
    }

    #[test]
    fn rect_square_manual_reference() {
        let a = rect(0, 0, 100, 50);
        let b = rect(0, 0, 40, 40);

        let nfp = compute_convex_nfp(&a, &b).expect("rect-square NFP should be valid");
        assert_eq!(
            nfp.outer,
            vec![
                Point64 { x: -40, y: -40 },
                Point64 { x: 100, y: -40 },
                Point64 { x: 100, y: 50 },
                Point64 { x: -40, y: 50 },
            ]
        );
    }

    #[test]
    fn square_square_manual_reference() {
        let a = rect(0, 0, 50, 50);
        let b = rect(0, 0, 50, 50);

        let nfp = compute_convex_nfp(&a, &b).expect("square-square NFP should be valid");
        assert_eq!(
            nfp.outer,
            vec![
                Point64 { x: -50, y: -50 },
                Point64 { x: 50, y: -50 },
                Point64 { x: 50, y: 50 },
                Point64 { x: -50, y: 50 },
            ]
        );
    }

    #[test]
    fn rect_rect_different_ratio_reference() {
        let a = rect(0, 0, 120, 40);
        let b = rect(0, 0, 30, 10);

        let nfp = compute_convex_nfp(&a, &b).expect("rect-rect ratio NFP should be valid");
        assert_eq!(
            nfp.outer,
            vec![
                Point64 { x: -30, y: -10 },
                Point64 { x: 120, y: -10 },
                Point64 { x: 120, y: 40 },
                Point64 { x: -30, y: 40 },
            ]
        );
    }

    #[test]
    fn parallel_edges_collinear_merge_keeps_minimal_vertices() {
        let a = rect(0, 0, 80, 20);
        let b = rect(0, 0, 80, 20);

        let nfp = compute_convex_nfp(&a, &b).expect("parallel-edge merge should be valid");
        assert_eq!(
            nfp.outer,
            vec![
                Point64 { x: -80, y: -20 },
                Point64 { x: 80, y: -20 },
                Point64 { x: 80, y: 20 },
                Point64 { x: -80, y: 20 },
            ]
        );
        assert_eq!(nfp.outer.len(), 4);
    }

    #[test]
    fn non_convex_input_returns_not_convex() {
        let concave = Polygon64 {
            outer: vec![
                Point64 { x: 0, y: 0 },
                Point64 { x: 4, y: 0 },
                Point64 { x: 2, y: 1 },
                Point64 { x: 4, y: 4 },
                Point64 { x: 0, y: 4 },
            ],
            holes: Vec::new(),
        };
        let b = rect(0, 0, 2, 2);

        let err = compute_convex_nfp(&concave, &b).expect_err("concave polygon must be rejected");
        assert_eq!(err, NfpError::NotConvex);
    }

    #[test]
    fn empty_polygon_returns_empty_error() {
        let a = Polygon64 {
            outer: Vec::new(),
            holes: Vec::new(),
        };
        let b = rect(0, 0, 10, 10);

        let err = compute_convex_nfp(&a, &b).expect_err("empty polygon must fail");
        assert_eq!(err, NfpError::EmptyPolygon);
    }

    #[test]
    fn deterministic_for_same_input() {
        let a = rect(0, 0, 73, 41);
        let b = rect(0, 0, 19, 11);

        let first = compute_convex_nfp(&a, &b).expect("first run");
        let second = compute_convex_nfp(&a, &b).expect("second run");
        assert_eq!(first.outer, second.outer);
    }

    #[test]
    fn edge_merge_matches_reference_hull_on_manual_case() {
        let a = rect(0, 0, 100, 50);
        let b = rect(0, 0, 60, 30);

        let fast = compute_convex_nfp(&a, &b).expect("fast path");
        let reference = compute_convex_nfp_reference(&a, &b).expect("reference path");
        assert_eq!(fast.outer, reference.outer);
    }
}
