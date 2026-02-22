use crate::feasibility::aabb::{Aabb, aabb_from_polygon64, aabb_inside, aabb_overlaps};
use crate::geometry::{scale::TOUCH_TOL, types::Polygon64};

#[derive(Debug, Clone)]
pub struct PlacedPart {
    pub inflated_polygon: Polygon64,
    pub aabb: Aabb,
}

pub fn can_place(candidate: &Polygon64, bin: &Polygon64, placed: &[PlacedPart]) -> bool {
    if candidate.outer.len() < 3 || bin.outer.len() < 3 {
        return false;
    }

    let candidate_aabb = aabb_from_polygon64(candidate);
    let bin_aabb = aabb_from_polygon64(bin);
    if !aabb_inside(&bin_aabb, &candidate_aabb) {
        return false;
    }

    // Narrow-phase containment against the actual bin contour.
    if !polygon_contained(candidate, bin) {
        return false;
    }

    let mut maybe_overlap: Vec<&PlacedPart> = placed
        .iter()
        .filter(|p| aabb_overlaps(&candidate_aabb, &p.aabb))
        .collect();
    if maybe_overlap.is_empty() {
        return true;
    }

    // Deterministic narrow-phase order.
    maybe_overlap.sort_by(|a, b| a.aabb.min_x.cmp(&b.aabb.min_x).then(a.aabb.min_y.cmp(&b.aabb.min_y)));

    for other in maybe_overlap {
        if polygons_overlap_or_touch(candidate, &other.inflated_polygon) {
            return false;
        }
    }
    true
}

fn polygon_contained(candidate: &Polygon64, bin: &Polygon64) -> bool {
    candidate
        .outer
        .iter()
        .all(|p| point_strictly_inside_polygon(p.x, p.y, &bin.outer))
}

fn polygons_overlap_or_touch(a: &Polygon64, b: &Polygon64) -> bool {
    for i in 0..a.outer.len() {
        let a0 = a.outer[i];
        let a1 = a.outer[(i + 1) % a.outer.len()];
        for j in 0..b.outer.len() {
            let b0 = b.outer[j];
            let b1 = b.outer[(j + 1) % b.outer.len()];
            if segments_intersect_or_touch(a0.x, a0.y, a1.x, a1.y, b0.x, b0.y, b1.x, b1.y) {
                return true;
            }
        }
    }

    // No edge crossings; one polygon may still be strictly inside the other.
    let a0 = a.outer[0];
    if point_strictly_inside_polygon(a0.x, a0.y, &b.outer) {
        return true;
    }
    let b0 = b.outer[0];
    if point_strictly_inside_polygon(b0.x, b0.y, &a.outer) {
        return true;
    }
    false
}

fn point_strictly_inside_polygon(px: i64, py: i64, poly: &[crate::geometry::types::Point64]) -> bool {
    // Boundary counts as outside for conservative touching policy.
    for i in 0..poly.len() {
        let a = poly[i];
        let b = poly[(i + 1) % poly.len()];
        if point_on_segment(px, py, a.x, a.y, b.x, b.y) {
            return false;
        }
    }

    let mut inside = false;
    for i in 0..poly.len() {
        let a = poly[i];
        let b = poly[(i + 1) % poly.len()];
        let yi = a.y as f64;
        let yj = b.y as f64;
        let intersects = (yi > py as f64) != (yj > py as f64);
        if intersects {
            let xi = a.x as f64;
            let xj = b.x as f64;
            let x_at_y = (xj - xi) * ((py as f64 - yi) / (yj - yi)) + xi;
            if x_at_y > px as f64 {
                inside = !inside;
            }
        }
    }
    inside
}

fn segments_intersect_or_touch(
    ax: i64,
    ay: i64,
    bx: i64,
    by: i64,
    cx: i64,
    cy: i64,
    dx: i64,
    dy: i64,
) -> bool {
    let o1 = orientation(ax, ay, bx, by, cx, cy);
    let o2 = orientation(ax, ay, bx, by, dx, dy);
    let o3 = orientation(cx, cy, dx, dy, ax, ay);
    let o4 = orientation(cx, cy, dx, dy, bx, by);

    if ((o1 > 0 && o2 < 0) || (o1 < 0 && o2 > 0)) && ((o3 > 0 && o4 < 0) || (o3 < 0 && o4 > 0))
    {
        return true;
    }
    if o1 == 0 && point_on_segment(cx, cy, ax, ay, bx, by) {
        return true;
    }
    if o2 == 0 && point_on_segment(dx, dy, ax, ay, bx, by) {
        return true;
    }
    if o3 == 0 && point_on_segment(ax, ay, cx, cy, dx, dy) {
        return true;
    }
    if o4 == 0 && point_on_segment(bx, by, cx, cy, dx, dy) {
        return true;
    }
    false
}

fn orientation(ax: i64, ay: i64, bx: i64, by: i64, cx: i64, cy: i64) -> i128 {
    let abx = bx as i128 - ax as i128;
    let aby = by as i128 - ay as i128;
    let acx = cx as i128 - ax as i128;
    let acy = cy as i128 - ay as i128;
    abx * acy - aby * acx
}

fn point_on_segment(px: i64, py: i64, ax: i64, ay: i64, bx: i64, by: i64) -> bool {
    if orientation(ax, ay, bx, by, px, py) != 0 {
        return false;
    }
    let min_x = ax.min(bx).saturating_sub(TOUCH_TOL);
    let max_x = ax.max(bx).saturating_add(TOUCH_TOL);
    let min_y = ay.min(by).saturating_sub(TOUCH_TOL);
    let max_y = ay.max(by).saturating_add(TOUCH_TOL);
    px >= min_x && px <= max_x && py >= min_y && py <= max_y
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
        assert!(can_place(&candidate, &bin, &[]));
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
        assert!(!can_place(&candidate, &bin, &[other]));
    }

    #[test]
    fn containment_case() {
        let bin = rect(0.0, 0.0, 100.0, 100.0);
        let candidate = rect(95.0, 95.0, 10.0, 10.0);
        assert!(!can_place(&candidate, &bin, &[]));
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
        assert!(!can_place(&candidate, &bin, &[other]));
    }
}
