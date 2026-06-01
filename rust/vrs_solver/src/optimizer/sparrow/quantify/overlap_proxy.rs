use super::*;
use jagua_rs::geometry::fail_fast::SPSurrogateConfig;
use std::f64::consts::PI;

const OVERLAP_PROXY_EPSILON_DIAM_RATIO: f64 = 0.01;

#[derive(Clone, Copy)]
struct PoleProxy {
    x: f64,
    y: f64,
    radius: f64,
}

/// Upstream Algorithm 4: pair collision loss = sqrt(overlap-proxy + epsilon²) ×
/// shape penalty. Pure value (no diagnostics side effects); used by the bounded
/// visitor collector which counts its own quantification calls.
pub(crate) fn quantify_collision_poly_poly_value(
    a: &CdePreparedShape,
    b: &CdePreparedShape,
) -> f64 {
    let epsilon = a.spoly.diameter.max(b.spoly.diameter) as f64 * OVERLAP_PROXY_EPSILON_DIAM_RATIO;
    let proxy = overlap_area_proxy(a, b, epsilon) + epsilon.powi(2);
    proxy.max(1e-12).sqrt() * calc_shape_penalty(a, b)
}

/// Upstream container loss = 2 × sqrt(outside/intersection-area) × shape penalty.
/// Pure value (no diagnostics side effects).
pub(crate) fn quantify_collision_poly_container_value(
    shape: &CdePreparedShape,
    sheet: &CdePreparedShape,
) -> f64 {
    let shape_area = bbox_area(shape).max(1.0);
    let overlap = match bbox_intersection_area(shape, sheet) {
        Some(intersection) => (shape_area - intersection).max(0.0) + 0.0001 * shape_area,
        None => shape_area + bbox_centroid_distance(shape, sheet),
    };
    2.0 * overlap.max(1e-12).sqrt() * calc_shape_penalty(shape, shape)
}

pub(crate) fn quantify_collision_poly_poly(
    a: &CdePreparedShape,
    b: &CdePreparedShape,
    diag: &mut SparrowDiagnostics,
) -> f64 {
    diag.quantified_pair_queries += 1;
    quantify_collision_poly_poly_value(a, b)
}

pub(crate) fn quantify_collision_poly_container(
    shape: &CdePreparedShape,
    sheet: &CdePreparedShape,
    diag: &mut SparrowDiagnostics,
) -> f64 {
    diag.quantified_boundary_queries += 1;
    quantify_collision_poly_container_value(shape, sheet)
}

/// Upstream Algorithm 3 overlap proxy, adapted to VRS prepared shapes.
pub(crate) fn overlap_area_proxy(a: &CdePreparedShape, b: &CdePreparedShape, epsilon: f64) -> f64 {
    let poles_a = surrogate_poles(a);
    let poles_b = surrogate_poles(b);
    if poles_a.is_empty() || poles_b.is_empty() {
        return bbox_intersection_area(a, b)
            .unwrap_or(0.0)
            .max(epsilon.powi(2));
    }

    let mut total_overlap = 0.0;
    for p1 in &poles_a {
        for p2 in &poles_b {
            let dx = p1.x - p2.x;
            let dy = p1.y - p2.y;
            let center_dist = (dx * dx + dy * dy).sqrt();
            let penetration_depth = (p1.radius + p2.radius) - center_dist;
            let decayed = if penetration_depth >= epsilon {
                penetration_depth
            } else {
                epsilon.powi(2) / (-penetration_depth + 2.0 * epsilon)
            };
            total_overlap += decayed * p1.radius.min(p2.radius);
        }
    }
    (total_overlap * PI).max(epsilon.powi(2))
}

pub(crate) fn calc_shape_penalty(a: &CdePreparedShape, b: &CdePreparedShape) -> f64 {
    let ca = convex_hull_area(a).sqrt();
    let cb = convex_hull_area(b).sqrt();
    (ca * cb).sqrt().max(1.0)
}

fn surrogate_config() -> SPSurrogateConfig {
    SPSurrogateConfig {
        n_pole_limits: [(64, 0.0), (16, 0.8), (8, 0.9)],
        n_ff_poles: 1,
        n_ff_piers: 0,
    }
}

fn surrogate_poles(shape: &CdePreparedShape) -> Vec<PoleProxy> {
    let mut spoly = shape.spoly.clone();
    if spoly.surrogate.is_none() && spoly.generate_surrogate(surrogate_config()).is_err() {
        return fallback_poles(shape);
    }
    spoly
        .surrogate()
        .poles
        .iter()
        .map(|p| PoleProxy {
            x: p.center.0 as f64,
            y: p.center.1 as f64,
            radius: p.radius as f64,
        })
        .filter(|p| p.radius.is_finite() && p.radius > 0.0)
        .collect()
}

fn fallback_poles(shape: &CdePreparedShape) -> Vec<PoleProxy> {
    let w = (shape.max_x - shape.min_x).max(0.0);
    let h = (shape.max_y - shape.min_y).max(0.0);
    vec![PoleProxy {
        x: (shape.min_x + shape.max_x) * 0.5,
        y: (shape.min_y + shape.max_y) * 0.5,
        radius: 0.5 * w.min(h).max(1.0),
    }]
}

fn convex_hull_area(shape: &CdePreparedShape) -> f64 {
    let mut spoly = shape.spoly.clone();
    if spoly.surrogate.is_none() && spoly.generate_surrogate(surrogate_config()).is_err() {
        return bbox_area(shape);
    }
    (spoly.surrogate().convex_hull_area as f64).max(1.0)
}

fn bbox_area(shape: &CdePreparedShape) -> f64 {
    ((shape.max_x - shape.min_x).max(0.0) * (shape.max_y - shape.min_y).max(0.0)).max(0.0)
}

fn bbox_intersection_area(a: &CdePreparedShape, b: &CdePreparedShape) -> Option<f64> {
    let w = a.max_x.min(b.max_x) - a.min_x.max(b.min_x);
    let h = a.max_y.min(b.max_y) - a.min_y.max(b.min_y);
    if w > 0.0 && h > 0.0 {
        Some(w * h)
    } else {
        None
    }
}

fn bbox_centroid_distance(a: &CdePreparedShape, b: &CdePreparedShape) -> f64 {
    let ax = (a.min_x + a.max_x) * 0.5;
    let ay = (a.min_y + a.max_y) * 0.5;
    let bx = (b.min_x + b.max_x) * 0.5;
    let by = (b.min_y + b.max_y) * 0.5;
    ((ax - bx).powi(2) + (ay - by).powi(2)).sqrt()
}
