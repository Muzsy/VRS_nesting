use crate::geometry::types::{cross_product_i128, is_ccw, is_convex, Point64, Polygon64};

use super::NfpError;

/// Compute NFP(A, B) for convex polygons via Minkowski-sum identity:
/// NFP(A, B) = A ⊕ (-B).
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

    use super::compute_convex_nfp;
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
}
