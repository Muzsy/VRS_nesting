use std::cmp::Ordering;

/// Default epsilon for millimeter-domain floating point comparisons.
pub const GEOM_EPS_MM: f64 = 1e-9;

/// Default epsilon for signed-area comparisons in mm^2 domain.
pub const AREA_EPS_MM2: f64 = 1e-12;

fn normalize_eps(eps: f64, fallback: f64) -> f64 {
    if eps.is_finite() && eps > 0.0 {
        eps
    } else {
        fallback
    }
}

/// Returns true when `value` is within epsilon distance from zero.
pub fn is_near_zero(value: f64, eps: f64) -> bool {
    value.abs() <= normalize_eps(eps, GEOM_EPS_MM)
}

/// Epsilon-aware equality.
pub fn eq_eps(a: f64, b: f64, eps: f64) -> bool {
    if a.is_nan() || b.is_nan() {
        return false;
    }
    (a - b).abs() <= normalize_eps(eps, GEOM_EPS_MM)
}

/// Deterministic epsilon-aware compare.
///
/// If the values are within epsilon they are considered equal.
/// NaN values are ordered via `total_cmp` for deterministic behavior.
pub fn cmp_eps(a: f64, b: f64, eps: f64) -> Ordering {
    if a.is_nan() || b.is_nan() {
        return a.total_cmp(&b);
    }
    if eq_eps(a, b, eps) {
        Ordering::Equal
    } else {
        a.total_cmp(&b)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn float_policy_cmp_eps_near_values_are_equal() {
        assert_eq!(cmp_eps(1.0, 1.0 + 5e-10, GEOM_EPS_MM), Ordering::Equal);
    }

    #[test]
    fn float_policy_cmp_eps_far_values_keep_total_order() {
        assert_eq!(cmp_eps(1.0, 1.0 + 1e-6, GEOM_EPS_MM), Ordering::Less);
        assert_eq!(cmp_eps(1.0 + 1e-6, 1.0, GEOM_EPS_MM), Ordering::Greater);
    }
}
