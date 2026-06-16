//! SGH-Q48 T1: interlock-aware density objective.
//!
//! A density score that **rewards** placing a part into the layout's existing free space /
//! concavities (compact, interlocked) over extending the layout. It is used to STEER the placement
//! search (T3 contour sampling, T4 density compaction); the CDE remains the sole collision truth,
//! continuous rotation stays continuous, and **no NFP is computed**. Lower score = denser.
//!
//! The score is intentionally a pure function of bounding geometry (cheap, deterministic, smooth
//! ⇒ coord-descent-able). The pole-proximity contact term (`w_contact`) is wired in T3/T4; T1 ships
//! the robust extent-growth + centroid-attraction terms.

use super::*;

const EPS: f64 = 1e-9;

/// Weights for the density score. Lower score = denser.
#[derive(Debug, Clone, Copy)]
pub struct DensityWeights {
    /// Penalty for growing the sheet's used bounding extent (normalised by the part's bbox area).
    pub w_extent: f64,
    /// Attraction: distance to the nearest neighbour centroid (normalised by the part diagonal).
    pub w_dist: f64,
    /// Pole-proximity contact reward (wired in T3/T4; 0.0 in T1).
    pub w_contact: f64,
}

impl Default for DensityWeights {
    fn default() -> Self {
        Self {
            w_extent: 1.0,
            w_dist: 0.5,
            w_contact: 0.0,
        }
    }
}

#[inline]
fn bbox_area(min_x: f64, min_y: f64, max_x: f64, max_y: f64) -> f64 {
    (max_x - min_x).max(0.0) * (max_y - min_y).max(0.0)
}

#[inline]
fn shape_centroid(s: &CdePreparedShape) -> (f64, f64) {
    ((s.min_x + s.max_x) * 0.5, (s.min_y + s.max_y) * 0.5)
}

#[inline]
fn shape_diag(s: &CdePreparedShape) -> f64 {
    let w = s.max_x - s.min_x;
    let h = s.max_y - s.min_y;
    (w * w + h * h).sqrt().max(EPS)
}

/// Density score for placing `candidate` among `neighbours` (the parts already on the sheet).
/// Lower = denser / more interlocked. Pure and deterministic.
///
/// - `extent_term` = growth of the neighbours' union bounding box caused by the candidate,
///   normalised by the candidate's bbox area. 0 ⇒ the candidate fits entirely inside the region
///   the layout already spans (tucked into a gap/concavity); larger ⇒ it sits further outside.
/// - `dist_term` = distance from the candidate to the nearest neighbour centroid, normalised by
///   the candidate diagonal (an attraction term that pulls parts together).
///
/// With no neighbours the score is 0.0 (density-neutral; the caller falls back to bottom-left for
/// the first part on a sheet).
pub fn density_candidate_score(
    candidate: &CdePreparedShape,
    neighbours: &[&CdePreparedShape],
    weights: &DensityWeights,
) -> f64 {
    if neighbours.is_empty() {
        return 0.0;
    }
    let cand_area =
        bbox_area(candidate.min_x, candidate.min_y, candidate.max_x, candidate.max_y).max(EPS);

    // Union bbox of the neighbours, and of the neighbours ∪ candidate.
    let (mut nx0, mut ny0, mut nx1, mut ny1) = (f64::MAX, f64::MAX, f64::MIN, f64::MIN);
    for n in neighbours {
        nx0 = nx0.min(n.min_x);
        ny0 = ny0.min(n.min_y);
        nx1 = nx1.max(n.max_x);
        ny1 = ny1.max(n.max_y);
    }
    let used = bbox_area(nx0, ny0, nx1, ny1);
    let used_with = bbox_area(
        nx0.min(candidate.min_x),
        ny0.min(candidate.min_y),
        nx1.max(candidate.max_x),
        ny1.max(candidate.max_y),
    );
    let extent_term = (used_with - used).max(0.0) / cand_area;

    let (cx, cy) = shape_centroid(candidate);
    let diag = shape_diag(candidate);
    let nearest = neighbours
        .iter()
        .map(|n| {
            let (nx, ny) = shape_centroid(n);
            ((cx - nx).powi(2) + (cy - ny).powi(2)).sqrt()
        })
        .fold(f64::MAX, f64::min);
    let dist_term = nearest / diag;

    weights.w_extent * extent_term + weights.w_dist * dist_term
}

/// Thin evaluator: scores a candidate prepared shape against a fixed neighbour set. Collision is
/// NOT checked here — the caller (T4 compaction) validates clearance via the CDE first, then ranks
/// clear candidates by this score. Keeps "CDE = collision truth" intact.
pub struct DensityEvaluator<'a> {
    pub neighbours: Vec<&'a CdePreparedShape>,
    pub weights: DensityWeights,
}

impl<'a> DensityEvaluator<'a> {
    pub fn new(neighbours: Vec<&'a CdePreparedShape>, weights: DensityWeights) -> Self {
        Self {
            neighbours,
            weights,
        }
    }

    /// Density score of a (already collision-checked) candidate. Lower = denser.
    pub fn score(&self, candidate: &CdePreparedShape) -> f64 {
        density_candidate_score(candidate, &self.neighbours, &self.weights)
    }
}

/// True when the candidate's bbox overlaps the neighbour's bbox. Combined with a CDE
/// polygon-clear result, this is the **interlock** signal (bbox-overlapping, polygon-clear).
pub fn bbox_overlaps(c: &CdePreparedShape, n: &CdePreparedShape) -> bool {
    c.min_x < n.max_x - EPS
        && c.max_x > n.min_x + EPS
        && c.min_y < n.max_y - EPS
        && c.max_y > n.min_y + EPS
}

/// True when the candidate's bbox overlaps at least one neighbour's bbox.
pub fn is_interlock_candidate(c: &CdePreparedShape, neighbours: &[&CdePreparedShape]) -> bool {
    neighbours.iter().any(|n| bbox_overlaps(c, n))
}

/// SGH-Q48 T3: contour-near rect-min candidates. For each neighbour vertex, propose the four ways
/// to abut a part of size `(rw, rh)` against that vertex (corner-to-vertex). These positions place
/// the part touching a neighbour's contour — the interlock candidates a uniform sampler misses.
/// This is NFP-free (it samples *near* vertices, it does not compute a no-fit polygon). Bounded by
/// `max_total`; collisions are filtered later by the CDE clear-check.
pub fn contour_near_rect_mins(
    neighbours: &[&CdePreparedShape],
    rw: f64,
    rh: f64,
    sheet: &SheetShape,
    max_total: usize,
) -> Vec<(f64, f64)> {
    let mut out: Vec<(f64, f64)> = Vec::new();
    if neighbours.is_empty() || max_total == 0 {
        return out;
    }
    let per_neighbour = (max_total / neighbours.len()).max(4);
    for n in neighbours {
        // Subsample vertices to stay within budget.
        let pts = &n.world_pts;
        if pts.is_empty() {
            continue;
        }
        let stride = (pts.len() / (per_neighbour / 4).max(1)).max(1);
        for (i, v) in pts.iter().enumerate() {
            if i % stride != 0 {
                continue;
            }
            for &(ox, oy) in &[(-rw, 0.0), (0.0, 0.0), (-rw, -rh), (0.0, -rh)] {
                let rmx = v.x + ox;
                let rmy = v.y + oy;
                if rmx >= sheet.min_x - EPS
                    && rmy >= sheet.min_y - EPS
                    && rmx + rw <= sheet.max_x + EPS
                    && rmy + rh <= sheet.max_y + EPS
                {
                    out.push((rmx, rmy));
                }
                if out.len() >= max_total {
                    return out;
                }
            }
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn part(id: &str, w: f64, h: f64, pts: serde_json::Value) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: 1,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: Some(pts),
            prepared_outer_points: None,
            rotation_policy: None,
        }
    }

    /// A "U" with a concave mouth: walls at x∈[0,30] & [70,100], floor y∈[0,30], mouth empty.
    fn u_shape() -> CdePreparedShape {
        let p = part(
            "U",
            100.0,
            100.0,
            serde_json::json!([
                [0.0, 0.0], [100.0, 0.0], [100.0, 100.0], [70.0, 100.0],
                [70.0, 30.0], [30.0, 30.0], [30.0, 100.0], [0.0, 100.0]
            ]),
        );
        let base = prepare_base_shape_native(&p).expect("U preparable");
        transform_base_to_candidate(&base, 0.0, 0.0, 0.0).expect("U transform")
    }

    fn square_at(world_min_x: f64, world_min_y: f64) -> CdePreparedShape {
        let p = part(
            "SQ",
            20.0,
            20.0,
            serde_json::json!([[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]]),
        );
        let base = prepare_base_shape_native(&p).expect("SQ preparable");
        // Read the local bbox by transforming at the origin, then anchor so the world-min lands
        // exactly at (world_min_x, world_min_y) — robust to any centring convention.
        let at0 = transform_base_to_candidate(&base, 0.0, 0.0, 0.0).expect("SQ transform");
        let ax = world_min_x - at0.min_x;
        let ay = world_min_y - at0.min_y;
        transform_base_to_candidate(&base, ax, ay, 0.0).expect("SQ transform2")
    }

    #[test]
    fn interlocked_placement_scores_better_than_separated() {
        let u = u_shape();
        let cx = (u.min_x + u.max_x) * 0.5;
        let cy = (u.min_y + u.max_y) * 0.5;
        // inside the mouth (nestled into the concavity): square centred on the U bbox centre
        let inside = square_at(cx - 10.0, cy - 10.0);
        // far outside to the right of the U
        let outside = square_at(u.max_x + 20.0, cy - 10.0);
        let w = DensityWeights::default();
        let s_in = density_candidate_score(&inside, &[&u], &w);
        let s_out = density_candidate_score(&outside, &[&u], &w);
        assert!(
            s_in < s_out,
            "interlocked score {s_in} must be < separated score {s_out}"
        );
    }

    #[test]
    fn score_is_deterministic() {
        let u = u_shape();
        let sq = square_at(40.0, 40.0);
        let w = DensityWeights::default();
        let a = density_candidate_score(&sq, &[&u], &w);
        let b = density_candidate_score(&sq, &[&u], &w);
        assert_eq!(a.to_bits(), b.to_bits());
    }

    #[test]
    fn no_neighbours_is_density_neutral() {
        let sq = square_at(0.0, 0.0);
        let w = DensityWeights::default();
        assert_eq!(density_candidate_score(&sq, &[], &w), 0.0);
    }

    #[test]
    fn evaluator_matches_free_function() {
        let u = u_shape();
        let sq = square_at(40.0, 40.0);
        let w = DensityWeights::default();
        let ev = DensityEvaluator::new(vec![&u], w);
        assert_eq!(
            ev.score(&sq).to_bits(),
            density_candidate_score(&sq, &[&u], &w).to_bits()
        );
    }
}
