use std::time::Instant;

use crate::geometry::types::Polygon64;

use super::blf::{InflatedPartSpec, blf_place};
use super::PlacementResult;

pub fn nfp_place(
    parts: &[InflatedPartSpec],
    bin_polygon: &Polygon64,
    grid_step_mm: f64,
    time_limit_sec: u64,
    started_at: Instant,
) -> PlacementResult {
    // TODO(F2-3): replace this bootstrap delegation with true NFP/CFR placement.
    blf_place(parts, bin_polygon, grid_step_mm, time_limit_sec, started_at)
}
