/// Single point in scaled integer coordinates (1 unit = 1 µm = 1/SCALE mm).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Point64 {
    pub x: i64,
    pub y: i64,
}

/// Closed polygon: list of points; the last point implicitly connects back to the first.
/// Outer boundary must be counter-clockwise (CCW).
/// Holes must be clockwise (CW).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Polygon64 {
    pub outer: Vec<Point64>,
    pub holes: Vec<Vec<Point64>>,
}

/// Geometry of a single part (nominal or inflated).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PartGeometry {
    pub id: String,
    pub polygon: Polygon64,
}

/// Overflow-safe 2D cross product (deterministic integer math).
///
/// SCALE=1_000_000 mellett a szorzatok i64-en túlcsordulhatnak,
/// ezért minden orientációs számítás i128-on fut.
pub fn cross_product_i128(dx1: i64, dy1: i64, dx2: i64, dy2: i64) -> i128 {
    (dx1 as i128) * (dy2 as i128) - (dx2 as i128) * (dy1 as i128)
}

/// Twice the signed area of a polygon ring.
/// Positive => CCW, negative => CW.
pub fn signed_area2_i128(points: &[Point64]) -> i128 {
    let n = points.len();
    if n < 3 {
        return 0;
    }

    let mut area2: i128 = 0;
    for i in 0..n {
        let p0 = points[i];
        let p1 = points[(i + 1) % n];
        area2 += (p0.x as i128) * (p1.y as i128) - (p1.x as i128) * (p0.y as i128);
    }
    area2
}

/// Returns true when a ring is counter-clockwise.
pub fn is_ccw(points: &[Point64]) -> bool {
    signed_area2_i128(points) > 0
}

/// Convexity check for a simple polygon ring.
///
/// Collinear edges are allowed, but the ring must have at least one
/// non-zero turn and may not switch turn direction.
pub fn is_convex(points: &[Point64]) -> bool {
    let n = points.len();
    if n < 3 {
        return false;
    }

    let mut turn_sign = 0_i8;
    for i in 0..n {
        let p0 = points[i];
        let p1 = points[(i + 1) % n];
        let p2 = points[(i + 2) % n];
        let dx1 = p1.x - p0.x;
        let dy1 = p1.y - p0.y;
        let dx2 = p2.x - p1.x;
        let dy2 = p2.y - p1.y;
        let cross = cross_product_i128(dx1, dy1, dx2, dy2);
        if cross == 0 {
            continue;
        }
        let current = if cross > 0 { 1 } else { -1 };
        if turn_sign == 0 {
            turn_sign = current;
        } else if turn_sign != current {
            return false;
        }
    }

    turn_sign != 0
}

#[cfg(test)]
mod tests {
    use super::{cross_product_i128, is_ccw, is_convex, Point64};

    #[test]
    fn cross_product_uses_i128_range() {
        let dx = 20_000_000_000_i64;
        let dy = 20_000_000_000_i64;
        let cross = cross_product_i128(dx, dy, -dx, dy);
        assert!(cross > i64::MAX as i128);
    }

    #[test]
    fn ccw_and_convex_for_rectangle() {
        let rect = vec![
            Point64 { x: 0, y: 0 },
            Point64 { x: 10, y: 0 },
            Point64 { x: 10, y: 5 },
            Point64 { x: 0, y: 5 },
        ];
        assert!(is_ccw(&rect));
        assert!(is_convex(&rect));
    }

    #[test]
    fn cw_rectangle_reports_not_ccw() {
        let rect_cw = vec![
            Point64 { x: 0, y: 0 },
            Point64 { x: 0, y: 5 },
            Point64 { x: 10, y: 5 },
            Point64 { x: 10, y: 0 },
        ];
        assert!(!is_ccw(&rect_cw));
        assert!(is_convex(&rect_cw));
    }

    #[test]
    fn non_convex_ring_detected() {
        let concave = vec![
            Point64 { x: 0, y: 0 },
            Point64 { x: 4, y: 0 },
            Point64 { x: 2, y: 1 },
            Point64 { x: 4, y: 4 },
            Point64 { x: 0, y: 4 },
        ];
        assert!(!is_convex(&concave));
    }
}
