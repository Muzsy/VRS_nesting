/// Scale factor: 1 mm = 1_000_000 units (1 unit = 1 µm).
pub const SCALE: i64 = 1_000_000;

/// Touching tolerance: two polygons are considered touching if they share a
/// point within TOUCH_TOL units (1 µm). Touching is treated as infeasible
/// (conservative side, manufacturing safety).
pub const TOUCH_TOL: i64 = 1;

/// Convert millimetres (f64) to scaled integer coordinates.
/// The conversion is lossy but deterministic and reproducible.
pub fn mm_to_i64(mm: f64) -> i64 {
    (mm * SCALE as f64).round() as i64
}

/// Convert scaled integer coordinates to millimetres (f64).
pub fn i64_to_mm(scaled: i64) -> f64 {
    scaled as f64 / SCALE as f64
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn scale_round_trip() {
        let val = 10.5_f64;
        let result = i64_to_mm(mm_to_i64(val));
        assert!(
            (result - val).abs() < 1e-6,
            "round-trip error: |{result} - {val}| = {} >= 1e-6",
            (result - val).abs()
        );
    }
}
