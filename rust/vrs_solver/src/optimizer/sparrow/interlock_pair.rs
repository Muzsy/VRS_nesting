//! SGH-Q57B: convert `PairCompatibilityIndex` candidates (Q57A) into Interlock placement seeds.
//!
//! Makes the Interlock role proactive: given a placed critical Anchor and a candidate critical part,
//! query the pair index, convert the pair's relative transform into a sheet placement seed against the
//! placed anchor, validate it (boundary against the sheet + clearance against the anchor via the
//! spacing-expanded contours), and rank by pair score + resulting free space. Falls back to the
//! existing neighbour-feature candidates when no pair-index seed succeeds (the fallback is reported).
//!
//! Hard rules: pair candidates are NOT mandatory superparts; the neighbour-feature fallback is never
//! removed; a pair transform is never accepted without a clearance check; no part-id hacks; bbox is a
//! prefilter only — the CDE remains the final clearance truth (this layer is a gated seed producer).

use super::*;
use crate::optimizer::sparrow::quantify::pair_matrix::{
    build_pair_compatibility_index, PairCompatibilityCandidate, PairIndexConfig,
};

const GRID_SAMPLES: usize = 48;

pub fn interlock_pair_enabled() -> bool {
    std::env::var("VRS_INTERLOCK_PAIR").ok().as_deref() == Some("1")
}

/// A placed Anchor on the sheet (anchor coordinates + rotation), in the same frame the pair index uses.
#[derive(Debug, Clone, Copy)]
pub struct PlacedAnchor {
    pub anchor_x: f64,
    pub anchor_y: f64,
    pub rotation_deg: f64,
    /// True when the placed anchor is part A of the pair (else it is part B and the relation inverts).
    pub anchor_is_part_a: bool,
}

#[derive(Debug, Clone)]
pub struct InterlockPairSeed {
    pub anchor_part_id: String,
    pub candidate_part_id: String,
    pub role: &'static str,
    pub accepted_candidate_source: String,
    pub accepted_rotation_deg: f64,
    pub accepted_x: f64,
    pub accepted_y: f64,
    pub pair_score: f64,
    pub cde_clear: bool,
    pub boundary_clear: bool,
    pub free_space_score_after: f64,
}

#[derive(Debug, Clone, Default)]
pub struct InterlockPairDiagnostics {
    pub pair_index_queries: usize,
    pub pair_candidates_generated: usize,
    pub pair_candidates_valid: usize,
    pub pair_candidates_accepted: usize,
    pub fallback_to_feature_candidates: bool,
    pub rejection_boundary_violation: usize,
    pub rejection_collision: usize,
    pub rejection_pair_not_found: usize,
    pub rejection_role_anchor_missing: usize,
    pub rejection_transform_invalid: usize,
    pub rejection_cde_not_clear: usize,
}

#[derive(Debug, Clone)]
pub struct InterlockPairAdmission {
    pub anchor_part_id: String,
    pub candidate_part_id: String,
    pub accepted: Option<InterlockPairSeed>,
    pub considered: Vec<InterlockPairSeed>,
    pub diagnostics: InterlockPairDiagnostics,
}

impl InterlockPairAdmission {
    pub fn to_diagnostics_json(&self) -> serde_json::Value {
        let cand = |s: &InterlockPairSeed| {
            serde_json::json!({
                "anchor_part_id": s.anchor_part_id,
                "candidate_part_id": s.candidate_part_id,
                "role": s.role,
                "accepted_candidate_source": s.accepted_candidate_source,
                "accepted_rotation": round4(s.accepted_rotation_deg),
                "accepted_position": [round4(s.accepted_x), round4(s.accepted_y)],
                "pair_score": round4(s.pair_score),
                "cde_clear": s.cde_clear,
                "boundary_clear": s.boundary_clear,
                "free_space_score_after": round4(s.free_space_score_after),
            })
        };
        serde_json::json!({
            "anchor_part_id": self.anchor_part_id,
            "candidate_part_id": self.candidate_part_id,
            "role": "interlock",
            "pair_candidates_considered": self.considered.len(),
            "pair_index_queries": self.diagnostics.pair_index_queries,
            "pair_candidates_generated": self.diagnostics.pair_candidates_generated,
            "pair_candidates_valid": self.diagnostics.pair_candidates_valid,
            "pair_candidates_accepted": self.diagnostics.pair_candidates_accepted,
            "fallback_to_feature_candidates": self.diagnostics.fallback_to_feature_candidates,
            "rejection_summary": {
                "boundary_violation": self.diagnostics.rejection_boundary_violation,
                "collision": self.diagnostics.rejection_collision,
                "pair_not_found": self.diagnostics.rejection_pair_not_found,
                "role_anchor_missing": self.diagnostics.rejection_role_anchor_missing,
                "transform_invalid": self.diagnostics.rejection_transform_invalid,
                "cde_not_clear": self.diagnostics.rejection_cde_not_clear,
            },
            "accepted": self.accepted.as_ref().map(cand),
            "considered": self.considered.iter().map(cand).collect::<Vec<_>>(),
        })
    }
}

/// Convert a pair relative transform into a candidate (x, y, rotation) seed against a placed anchor.
///
/// The pair index expresses placements as `anchor = translation` of the origin-rotated frame (the same
/// convention as `SparrowPlacement` anchors). So if the placed anchor is part A:
///   candidate = (anchor_x + relative_dx, anchor_y + relative_dy, rotation_b)
/// If the placed anchor is part B, invert: the stored relation is B = A + (dx,dy), hence
///   candidate(A) = (anchor_x - relative_dx, anchor_y - relative_dy, rotation_a).
pub fn convert_pair_to_interlock_seed(
    anchor: PlacedAnchor,
    candidate: &PairCompatibilityCandidate,
) -> Option<(f64, f64, f64)> {
    let (dx, dy, rot) = if anchor.anchor_is_part_a {
        (candidate.relative_dx, candidate.relative_dy, candidate.rotation_b_deg)
    } else {
        (-candidate.relative_dx, -candidate.relative_dy, candidate.rotation_a_deg)
    };
    let x = anchor.anchor_x + dx;
    let y = anchor.anchor_y + dy;
    if !(x.is_finite() && y.is_finite() && rot.is_finite()) {
        return None;
    }
    Some((x, y, rot))
}

/// Build a focused Interlock pair-admission for `anchor_part` + `candidate_part` on a sheet. Places the
/// anchor flush at the bottom-left of the margin-shrunk sheet, then admits the best valid pair-index
/// interlock seed. Falls back (reported) when no pair seed is valid.
pub fn admit_interlock_pair(
    anchor_part: &Part,
    candidate_part: &Part,
    sheet_width: f64,
    sheet_height: f64,
    spacing_mm: f64,
) -> Result<InterlockPairAdmission, String> {
    let mut diag = InterlockPairDiagnostics::default();

    // Build the pair index over the two parts (Q57A) and the per-part spacing geometry.
    let parts = unique_parts(anchor_part, candidate_part);
    let index = build_pair_compatibility_index(&parts, sheet_width, sheet_height, spacing_mm, PairIndexConfig::default())?;
    diag.pair_index_queries += 1;

    let (anchor_shape, anchor_frame_at) = part_spacing_shape(anchor_part, sheet_width, sheet_height, spacing_mm)?;
    let (cand_shape, cand_frame_at) = part_spacing_shape(candidate_part, sheet_width, sheet_height, spacing_mm)?;

    // Place the anchor flush bottom-left of the sheet at rotation 0 (deterministic reference anchor).
    let anchor_rot = 0.0;
    let af = anchor_frame_at(anchor_rot);
    let anchor_x = -af[0];
    let anchor_y = -af[1];
    let anchor = PlacedAnchor {
        anchor_x,
        anchor_y,
        rotation_deg: anchor_rot,
        anchor_is_part_a: true,
    };

    let sheet = [0.0, 0.0, sheet_width, sheet_height];
    let anchor_box = [af[0] + anchor_x, af[1] + anchor_y, af[2] + anchor_x, af[3] + anchor_y];

    let mut considered: Vec<InterlockPairSeed> = Vec::new();
    for c in &index.candidates {
        // Restrict to candidates that involve the anchor part as A and the candidate part as B.
        let matches_roles = c.part_a_id == anchor_part.id && c.part_b_id == candidate_part.id;
        if !matches_roles {
            continue;
        }
        diag.pair_candidates_generated += 1;
        let Some((cx, cy, crot)) = convert_pair_to_interlock_seed(anchor, c) else {
            diag.rejection_transform_invalid += 1;
            continue;
        };
        let cf = cand_frame_at(crot);
        let cand_box = [cf[0] + cx, cf[1] + cy, cf[2] + cx, cf[3] + cy];
        // Boundary check against the sheet.
        let boundary_clear = cand_box[0] >= sheet[0] - 0.05
            && cand_box[1] >= sheet[1] - 0.05
            && cand_box[2] <= sheet[2] + 0.05
            && cand_box[3] <= sheet[3] + 0.05;
        if !boundary_clear {
            diag.rejection_boundary_violation += 1;
            continue;
        }
        // Clearance against the placed anchor (spacing-expanded contour grid proxy).
        let bbox_overlap = !(anchor_box[2] <= cand_box[0]
            || cand_box[2] <= anchor_box[0]
            || anchor_box[3] <= cand_box[1]
            || cand_box[3] <= anchor_box[1]);
        let cde_clear = if !bbox_overlap {
            true
        } else {
            !contours_overlap(&anchor_shape, anchor_rot, anchor_x, anchor_y, &cand_shape, crot, cx, cy)
        };
        if !cde_clear {
            diag.rejection_cde_not_clear += 1;
            diag.rejection_collision += 1;
            continue;
        }
        diag.pair_candidates_valid += 1;
        // Free space after placing both (proxy).
        let free = crate::optimizer::sparrow::sheet_skeleton::largest_edge_connected_free_area(
            &[anchor_box, cand_box],
            sheet[0], sheet[1], sheet[2], sheet[3], 50.0,
        );
        considered.push(InterlockPairSeed {
            anchor_part_id: anchor_part.id.clone(),
            candidate_part_id: candidate_part.id.clone(),
            role: "interlock",
            accepted_candidate_source: c.candidate_source.as_str().to_string(),
            accepted_rotation_deg: crot,
            accepted_x: cx,
            accepted_y: cy,
            pair_score: c.score,
            cde_clear,
            boundary_clear,
            free_space_score_after: free,
        });
    }

    if considered.is_empty() {
        diag.rejection_pair_not_found += 1;
        diag.fallback_to_feature_candidates = true;
    }

    // Rank by pair_score then resulting free space.
    considered.sort_by(|a, b| {
        b.pair_score
            .partial_cmp(&a.pair_score)
            .unwrap_or(Ordering::Equal)
            .then_with(|| {
                b.free_space_score_after
                    .partial_cmp(&a.free_space_score_after)
                    .unwrap_or(Ordering::Equal)
            })
    });
    let accepted = considered.first().cloned();
    if accepted.is_some() {
        diag.pair_candidates_accepted = 1;
    }

    Ok(InterlockPairAdmission {
        anchor_part_id: anchor_part.id.clone(),
        candidate_part_id: candidate_part.id.clone(),
        accepted,
        considered,
        diagnostics: diag,
    })
}

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

fn unique_parts(a: &Part, b: &Part) -> Vec<Part> {
    if a.id == b.id {
        vec![a.clone()]
    } else {
        vec![a.clone(), b.clone()]
    }
}

/// Build the spacing-expanded shape for one part (via the solver path) plus a closure that returns its
/// rotated true-extrema frame.
fn part_spacing_shape(
    part: &Part,
    sheet_width: f64,
    sheet_height: f64,
    spacing_mm: f64,
) -> Result<(Rc<CdeBaseShape>, impl Fn(f64) -> [f64; 4]), String> {
    let rotation_context = RotationResolveContext::new(Some(RotationPolicyKind::Continuous), 42, 24);
    let raw_stock = crate::sheet::Stock {
        id: "S_INTERLOCK".to_string(),
        quantity: 1,
        width: Some(sheet_width),
        height: Some(sheet_height),
        outer_points: None,
        holes_points: None,
        cost_per_use: None,
    };
    let raw_sheet = crate::sheet::stock_to_shape(&raw_stock)?;
    let cfg = SparrowConfig::from_solver_input(1.0, CollisionBackendKind::Cde, rotation_context.clone(), 42)
        .with_spacing_mm(spacing_mm);
    let problem = SparrowProblem::from_solver_input(
        std::slice::from_ref(part),
        std::slice::from_ref(&raw_sheet),
        &rotation_context,
        Vec::new(),
        cfg,
    )?;
    let inst = problem.instances.into_iter().next().ok_or_else(|| format!("no instance for {}", part.id))?;
    let shape = inst.spacing_collision_base_shape;
    let shape_for_closure = Rc::clone(&shape);
    let closure = move |rot: f64| frame(&shape_for_closure, rot).unwrap_or([0.0, 0.0, 0.0, 0.0]);
    Ok((shape, closure))
}

fn frame(shape: &CdeBaseShape, rot: f64) -> Option<[f64; 4]> {
    if shape.local_pts.is_empty() {
        return None;
    }
    let t = rot.to_radians();
    let (c, s) = (t.cos(), t.sin());
    let (mut mnx, mut mny, mut mxx, mut mxy) = (f64::MAX, f64::MAX, f64::MIN, f64::MIN);
    for p in &shape.local_pts {
        let rx = p.x * c - p.y * s;
        let ry = p.x * s + p.y * c;
        mnx = mnx.min(rx);
        mny = mny.min(ry);
        mxx = mxx.max(rx);
        mxy = mxy.max(ry);
    }
    Some([mnx, mny, mxx, mxy])
}

fn rotated_translated(shape: &CdeBaseShape, rot: f64, dx: f64, dy: f64) -> Vec<(f64, f64)> {
    let t = rot.to_radians();
    let (c, s) = (t.cos(), t.sin());
    shape.local_pts.iter().map(|p| (p.x * c - p.y * s + dx, p.x * s + p.y * c + dy)).collect()
}

fn contours_overlap(
    sa: &CdeBaseShape,
    rot_a: f64,
    ax: f64,
    ay: f64,
    sb: &CdeBaseShape,
    rot_b: f64,
    bx: f64,
    by: f64,
) -> bool {
    let pa = rotated_translated(sa, rot_a, ax, ay);
    let pb = rotated_translated(sb, rot_b, bx, by);
    let (amnx, amny, amxx, amxy) = pts_bbox(&pa);
    let (bmnx, bmny, bmxx, bmxy) = pts_bbox(&pb);
    let ox0 = amnx.max(bmnx);
    let oy0 = amny.max(bmny);
    let ox1 = amxx.min(bmxx);
    let oy1 = amxy.min(bmxy);
    if ox0 >= ox1 || oy0 >= oy1 {
        return false;
    }
    for j in 0..GRID_SAMPLES {
        let y = oy0 + (j as f64 + 0.5) / GRID_SAMPLES as f64 * (oy1 - oy0);
        for i in 0..GRID_SAMPLES {
            let x = ox0 + (i as f64 + 0.5) / GRID_SAMPLES as f64 * (ox1 - ox0);
            if point_in_poly(x, y, &pa) && point_in_poly(x, y, &pb) {
                return true;
            }
        }
    }
    false
}

fn pts_bbox(pts: &[(f64, f64)]) -> (f64, f64, f64, f64) {
    let (mut mnx, mut mny, mut mxx, mut mxy) = (f64::MAX, f64::MAX, f64::MIN, f64::MIN);
    for &(x, y) in pts {
        mnx = mnx.min(x);
        mny = mny.min(y);
        mxx = mxx.max(x);
        mxy = mxy.max(y);
    }
    (mnx, mny, mxx, mxy)
}

fn point_in_poly(x: f64, y: f64, poly: &[(f64, f64)]) -> bool {
    let n = poly.len();
    if n < 3 {
        return false;
    }
    let mut inside = false;
    let mut j = n - 1;
    for i in 0..n {
        let (xi, yi) = poly[i];
        let (xj, yj) = poly[j];
        if ((yi > y) != (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi) {
            inside = !inside;
        }
        j = i;
    }
    inside
}

fn round4(v: f64) -> f64 {
    (v * 10_000.0).round() / 10_000.0
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rect(id: &str, w: f64, h: f64, qty: i64) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: qty,
            allowed_rotations_deg: vec![],
            rotation_policy: Some(RotationPolicyKind::Continuous),
            holes_points: None,
            prepared_holes_points: None,
            outer_points: Some(serde_json::json!([[0.0, 0.0], [w, 0.0], [w, h], [0.0, h]])),
            prepared_outer_points: None,
        }
    }

    #[test]
    fn converts_pair_transform_to_seed_against_anchor() {
        let anchor = PlacedAnchor { anchor_x: 100.0, anchor_y: 50.0, rotation_deg: 0.0, anchor_is_part_a: true };
        let cand = PairCompatibilityCandidate {
            part_a_id: "A".into(),
            part_b_id: "B".into(),
            rotation_a_deg: 0.0,
            rotation_b_deg: 90.0,
            relative_dx: 300.0,
            relative_dy: 0.0,
            candidate_source: crate::optimizer::sparrow::quantify::pair_matrix::PairCandidateSource::DominantEdgeParallel,
            compactness_gain: 0.1,
            bbox_area_reduction: 0.0,
            interlock_depth_score: 0.0,
            spacing_clear: true,
            cde_clear: true,
            score: 0.5,
            rejection_reason: None,
        };
        let (x, y, rot) = convert_pair_to_interlock_seed(anchor, &cand).expect("seed");
        assert_eq!((x, y, rot), (400.0, 50.0, 90.0));
        // Inverted relation when the anchor is part B.
        let anchor_b = PlacedAnchor { anchor_is_part_a: false, ..anchor };
        let (xb, yb, rotb) = convert_pair_to_interlock_seed(anchor_b, &cand).expect("seed b");
        assert_eq!((xb, yb, rotb), (-200.0, 50.0, 0.0));
    }

    #[test]
    fn same_part_admission_yields_a_valid_interlock_seed_or_reports_fallback() {
        let a = rect("big", 1200.0, 300.0, 6);
        let adm = admit_interlock_pair(&a, &a, 1500.0, 3000.0, 8.0).expect("admission");
        // Either a valid pair seed is accepted, or the fallback is explicitly reported (never silent).
        if adm.accepted.is_some() {
            let s = adm.accepted.unwrap();
            assert!(s.cde_clear && s.boundary_clear);
            assert_eq!(adm.diagnostics.pair_candidates_accepted, 1);
        } else {
            assert!(adm.diagnostics.fallback_to_feature_candidates, "no-seed path must report fallback");
        }
    }

    #[test]
    fn admission_queries_pair_index() {
        let a = rect("big", 1200.0, 300.0, 6);
        let b = rect("mid", 600.0, 400.0, 2);
        let adm = admit_interlock_pair(&a, &b, 1500.0, 3000.0, 8.0).expect("admission");
        assert_eq!(adm.diagnostics.pair_index_queries, 1);
    }
}
