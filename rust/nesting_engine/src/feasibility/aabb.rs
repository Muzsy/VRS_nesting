use crate::geometry::{
    scale::TOUCH_TOL,
    types::{Point64, Polygon64},
};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Aabb {
    pub min_x: i64,
    pub min_y: i64,
    pub max_x: i64,
    pub max_y: i64,
}

pub fn aabb_from_polygon(points: &[Point64]) -> Aabb {
    let first = points
        .first()
        .copied()
        .expect("aabb_from_polygon requires at least one point");
    let mut min_x = first.x;
    let mut min_y = first.y;
    let mut max_x = first.x;
    let mut max_y = first.y;
    for p in &points[1..] {
        min_x = min_x.min(p.x);
        min_y = min_y.min(p.y);
        max_x = max_x.max(p.x);
        max_y = max_y.max(p.y);
    }
    Aabb {
        min_x,
        min_y,
        max_x,
        max_y,
    }
}

pub fn aabb_overlaps(a: &Aabb, b: &Aabb) -> bool {
    // Touching is treated as overlap (conservative policy).
    a.max_x.saturating_add(TOUCH_TOL) >= b.min_x.saturating_sub(TOUCH_TOL)
        && b.max_x.saturating_add(TOUCH_TOL) >= a.min_x.saturating_sub(TOUCH_TOL)
        && a.max_y.saturating_add(TOUCH_TOL) >= b.min_y.saturating_sub(TOUCH_TOL)
        && b.max_y.saturating_add(TOUCH_TOL) >= a.min_y.saturating_sub(TOUCH_TOL)
}

pub fn aabb_inside(container: &Aabb, inner: &Aabb) -> bool {
    inner.min_x >= container.min_x
        && inner.min_y >= container.min_y
        && inner.max_x <= container.max_x
        && inner.max_y <= container.max_y
}

pub fn aabb_from_polygon64(poly: &Polygon64) -> Aabb {
    aabb_from_polygon(&poly.outer)
}
