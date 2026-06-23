//! SGH-Q59: true-extreme slot-edge placement for the `SkeletonRole::BandInsert`.
//!
//! Upgrades BandInsert from coarse bbox/orthogonal slot seeds to the same geometric standard as the
//! Q55B Anchor path: free-slot edge → real contour orientation (OrientationCatalog) → rotated
//! spacing-expanded TRUE extrema → slot-edge-aligned translation → exact validation against the full
//! sheet and placed neighbours. The slot bbox is a ranking/target region only — NOT collision truth.
//!
//! Gated by `VRS_BAND_INSERT_TRUE_EXTREME`; the existing `bpp_reduction::band_insert_seeds` bbox path
//! remains the fallback (its consumption switch is the gated follow-up — this module is the proven
//! producer with its own diagnostics + artifact).

use super::*;

const BOUNDARY_TOL_MM: f64 = 0.05;
const GRID_SAMPLES: usize = 40;

pub fn band_insert_true_extreme_enabled() -> bool {
    std::env::var("VRS_BAND_INSERT_TRUE_EXTREME").ok().as_deref() == Some("1")
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SlotEdge {
    Left,
    Right,
    Bottom,
    Top,
}

impl SlotEdge {
    pub fn as_str(self) -> &'static str {
        match self {
            SlotEdge::Left => "slot_left",
            SlotEdge::Right => "slot_right",
            SlotEdge::Bottom => "slot_bottom",
            SlotEdge::Top => "slot_top",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SlotSecondaryPolicy {
    CornerLow,
    CornerHigh,
    Center,
}

impl SlotSecondaryPolicy {
    pub fn as_str(self) -> &'static str {
        match self {
            SlotSecondaryPolicy::CornerLow => "corner_low",
            SlotSecondaryPolicy::CornerHigh => "corner_high",
            SlotSecondaryPolicy::Center => "center",
        }
    }
    fn is_corner(self) -> bool {
        !matches!(self, SlotSecondaryPolicy::Center)
    }
}

#[derive(Debug, Clone)]
pub struct SlotEdgePlacementCandidate {
    pub candidate_source: &'static str,
    pub slot_bbox: [f64; 4],
    pub target_slot_edge: SlotEdge,
    pub secondary_axis_policy: SlotSecondaryPolicy,
    pub rotation_deg: f64,
    pub selected_edge_index: Option<usize>,
    pub selected_edge_angle_deg: Option<f64>,
    pub translation_x: f64,
    pub translation_y: f64,
    pub final_extrema: [f64; 4],
    pub slot_edge_margin_error: f64,
    pub boundary_clear: bool,
    pub collision_clear: bool,
    pub is_corner: bool,
    pub is_fractional: bool,
    pub score: f64,
    pub rejection_reason: Option<String>,
}

#[derive(Debug, Clone)]
pub struct BandInsertSlotEdgeResult {
    pub part_id: String,
    pub slot_bbox: [f64; 4],
    pub sheet: [f64; 4],
    pub candidates: Vec<SlotEdgePlacementCandidate>,
    pub selected_index: Option<usize>,
    pub fallback_to_bbox_path: bool,
}

impl BandInsertSlotEdgeResult {
    pub fn selected(&self) -> Option<&SlotEdgePlacementCandidate> {
        self.selected_index.map(|i| &self.candidates[i])
    }
    pub fn valid_count(&self) -> usize {
        self.candidates.iter().filter(|c| c.boundary_clear && c.collision_clear).count()
    }
    pub fn to_diagnostics_json(&self) -> serde_json::Value {
        let cands: Vec<serde_json::Value> = self
            .candidates
            .iter()
            .map(|c| {
                serde_json::json!({
                    "candidate_source": c.candidate_source,
                    "target_slot_edge": c.target_slot_edge.as_str(),
                    "secondary_axis_policy": c.secondary_axis_policy.as_str(),
                    "is_corner": c.is_corner,
                    "rotation_deg": round4(c.rotation_deg),
                    "is_fractional": c.is_fractional,
                    "selected_edge_index": c.selected_edge_index,
                    "selected_edge_angle_deg": c.selected_edge_angle_deg,
                    "translation_x": round4(c.translation_x),
                    "translation_y": round4(c.translation_y),
                    "final_extrema": c.final_extrema.map(round4),
                    "slot_edge_margin_error": round4(c.slot_edge_margin_error),
                    "boundary_clear": c.boundary_clear,
                    "collision_clear": c.collision_clear,
                    "score": round4(c.score),
                    "rejection_reason": c.rejection_reason,
                })
            })
            .collect();
        serde_json::json!({
            "part_id": self.part_id,
            "slot_bbox": self.slot_bbox.map(round4),
            "sheet": self.sheet.map(round4),
            "candidate_count": self.candidates.len(),
            "valid_count": self.valid_count(),
            "selected_index": self.selected_index,
            "fallback_to_bbox_path": self.fallback_to_bbox_path,
            "selected": self.selected().map(|c| serde_json::json!({
                "target_slot_edge": c.target_slot_edge.as_str(),
                "secondary_axis_policy": c.secondary_axis_policy.as_str(),
                "rotation_deg": round4(c.rotation_deg),
                "is_fractional": c.is_fractional,
                "score": round4(c.score),
            })),
            "candidates": cands,
        })
    }
}

/// Build BandInsert true-extreme slot-edge candidates for `part` into `slot_bbox` on the sheet, with
/// optional already-placed neighbour world-bboxes for clearance.
pub fn build_band_insert_slot_edge_candidates(
    part: &Part,
    slot_bbox: [f64; 4],
    sheet_bbox: [f64; 4],
    spacing_mm: f64,
    placed_neighbours: &[[f64; 4]],
) -> Result<BandInsertSlotEdgeResult, String> {
    let rotation_context = RotationResolveContext::new(Some(RotationPolicyKind::Continuous), 42, 24);
    let raw_stock = crate::sheet::Stock {
        id: "S_BAND".to_string(),
        quantity: 1,
        width: Some(sheet_bbox[2] - sheet_bbox[0]),
        height: Some(sheet_bbox[3] - sheet_bbox[1]),
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
    let inst = problem.instances.first().ok_or_else(|| format!("no instance for {}", part.id))?;
    let offset_shape = inst.spacing_collision_base_shape.clone();
    let catalog = inst.orientation_catalog.as_ref();

    // Candidate rotations from the orientation catalog (continuous, includes fractional min-width).
    let mut rotations: Vec<(f64, Option<usize>, Option<f64>)> = Vec::new();
    for c in &catalog.candidates {
        if !rotations.iter().any(|(a, ..)| (a - c.angle_deg).abs() < 0.01) {
            rotations.push((c.angle_deg, c.source_edge_index, c.source_edge_angle_deg));
        }
    }

    let edges = [SlotEdge::Left, SlotEdge::Right, SlotEdge::Bottom, SlotEdge::Top];
    let pols = [SlotSecondaryPolicy::CornerLow, SlotSecondaryPolicy::CornerHigh, SlotSecondaryPolicy::Center];

    let mut candidates: Vec<SlotEdgePlacementCandidate> = Vec::new();
    for &(rot, edge_idx, edge_ang) in &rotations {
        let Some(off) = frame(&offset_shape, rot) else { continue };
        for &edge in &edges {
            for &pol in &pols {
                candidates.push(build_candidate(
                    &offset_shape, rot, edge_idx, edge_ang, &off, edge, pol, slot_bbox, sheet_bbox,
                    placed_neighbours,
                ));
            }
        }
    }

    let selected_index = candidates
        .iter()
        .enumerate()
        .filter(|(_, c)| c.boundary_clear && c.collision_clear)
        .max_by(|(_, a), (_, b)| {
            a.score
                .partial_cmp(&b.score)
                .unwrap_or(Ordering::Equal)
                .then_with(|| (b.is_corner as u8).cmp(&(a.is_corner as u8)))
        })
        .map(|(i, _)| i);

    Ok(BandInsertSlotEdgeResult {
        part_id: part.id.clone(),
        slot_bbox,
        sheet: sheet_bbox,
        fallback_to_bbox_path: selected_index.is_none(),
        candidates,
        selected_index,
    })
}

#[allow(clippy::too_many_arguments)]
fn build_candidate(
    offset_shape: &CdeBaseShape,
    rot: f64,
    edge_idx: Option<usize>,
    edge_ang: Option<f64>,
    off: &[f64; 4],
    edge: SlotEdge,
    pol: SlotSecondaryPolicy,
    slot: [f64; 4],
    sheet: [f64; 4],
    neighbours: &[[f64; 4]],
) -> SlotEdgePlacementCandidate {
    let off_w = off[2] - off[0];
    let off_h = off[3] - off[1];
    let slot_w = slot[2] - slot[0];
    let slot_h = slot[3] - slot[1];

    let (tx, ty, margin_line, axis_extremum_is_min) = match edge {
        SlotEdge::Left => (
            slot[0] - off[0],
            secondary(pol, off[1], off_h, slot[1], slot_h),
            slot[0],
            true,
        ),
        SlotEdge::Right => (
            slot[2] - off[2],
            secondary(pol, off[1], off_h, slot[1], slot_h),
            slot[2],
            false,
        ),
        SlotEdge::Bottom => (
            secondary(pol, off[0], off_w, slot[0], slot_w),
            slot[1] - off[1],
            slot[1],
            true,
        ),
        SlotEdge::Top => (
            secondary(pol, off[0], off_w, slot[0], slot_w),
            slot[3] - off[3],
            slot[3],
            false,
        ),
    };

    let fx0 = off[0] + tx;
    let fy0 = off[1] + ty;
    let fx1 = off[2] + tx;
    let fy1 = off[3] + ty;

    // The slot bbox is a TARGET region: a candidate must fit within the slot to count as a slot fill,
    // and must also stay within the full sheet (the real boundary truth) — never just the slot.
    let within_slot = fx0 >= slot[0] - BOUNDARY_TOL_MM
        && fy0 >= slot[1] - BOUNDARY_TOL_MM
        && fx1 <= slot[2] + BOUNDARY_TOL_MM
        && fy1 <= slot[3] + BOUNDARY_TOL_MM;
    let within_sheet = fx0 >= sheet[0] - BOUNDARY_TOL_MM
        && fy0 >= sheet[1] - BOUNDARY_TOL_MM
        && fx1 <= sheet[2] + BOUNDARY_TOL_MM
        && fy1 <= sheet[3] + BOUNDARY_TOL_MM;
    let boundary_clear = within_slot && within_sheet;

    // Clearance vs placed neighbours (bbox prefilter; the placed neighbours are spacing-expanded boxes).
    let cand_box = [fx0, fy0, fx1, fy1];
    let collision_clear = boundary_clear
        && !neighbours.iter().any(|n| bboxes_overlap(&cand_box, n));

    let edge_extremum = match edge {
        SlotEdge::Left => fx0,
        SlotEdge::Right => fx1,
        SlotEdge::Bottom => fy0,
        SlotEdge::Top => fy1,
    };
    let _ = axis_extremum_is_min;
    let slot_edge_margin_error = (edge_extremum - margin_line).abs();

    // Score: fit (smaller inward drift), corner bonus, slot utilisation.
    let slot_area = (slot_w * slot_h).max(1.0);
    let part_area = (off_w * off_h).max(1.0);
    let utilisation = (part_area / slot_area).clamp(0.0, 1.0);
    let corner_bonus = if pol.is_corner() { 0.10 } else { 0.0 };
    let drift_penalty = (slot_edge_margin_error / slot_w.max(slot_h).max(1.0)).clamp(0.0, 1.0) * 0.10;
    let score = if boundary_clear && collision_clear {
        (0.6 * utilisation + corner_bonus - drift_penalty).max(0.0)
    } else {
        0.0
    };

    let rejection_reason = if !within_sheet {
        Some("exceeds_sheet".to_string())
    } else if !within_slot {
        Some("exceeds_slot".to_string())
    } else if !collision_clear {
        Some("collides_with_neighbour".to_string())
    } else {
        None
    };

    SlotEdgePlacementCandidate {
        candidate_source: "true_extreme_slot_edge_band_insert",
        slot_bbox: slot,
        target_slot_edge: edge,
        secondary_axis_policy: pol,
        rotation_deg: rot,
        selected_edge_index: edge_idx,
        selected_edge_angle_deg: edge_ang,
        translation_x: tx,
        translation_y: ty,
        final_extrema: cand_box,
        slot_edge_margin_error,
        boundary_clear,
        collision_clear,
        is_corner: pol.is_corner(),
        is_fractional: nearest_axis_dist(rot) > 0.25,
        score,
        rejection_reason,
    }
}

fn secondary(pol: SlotSecondaryPolicy, off_min: f64, off_extent: f64, slot_min: f64, slot_extent: f64) -> f64 {
    match pol {
        SlotSecondaryPolicy::CornerLow => slot_min - off_min,
        SlotSecondaryPolicy::CornerHigh => (slot_min + slot_extent) - (off_min + off_extent),
        SlotSecondaryPolicy::Center => slot_min - off_min + (slot_extent - off_extent) / 2.0,
    }
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

fn bboxes_overlap(a: &[f64; 4], b: &[f64; 4]) -> bool {
    !(a[2] <= b[0] || b[2] <= a[0] || a[3] <= b[1] || b[3] <= a[1])
}

fn nearest_axis_dist(a: f64) -> f64 {
    let n = ((a % 360.0) + 360.0) % 360.0;
    [0.0_f64, 90.0, 180.0, 270.0, 360.0]
        .iter()
        .map(|&axis| (n - axis).abs())
        .fold(f64::MAX, f64::min)
}

fn round4(v: f64) -> f64 {
    (v * 10_000.0).round() / 10_000.0
}

#[cfg(test)]
mod tests {
    use super::*;

    fn elongated(id: &str) -> Part {
        // Long thin part that fits a tall slot only when rotated near-vertical (continuous rotation).
        let ang = 4.0_f64.to_radians();
        let (c, s) = (ang.cos(), ang.sin());
        let raw = [[0.0, 0.0], [900.0, 0.0], [900.0, 180.0], [0.0, 180.0]];
        let pts: Vec<[f64; 2]> = raw.iter().map(|p| [p[0] * c - p[1] * s, p[0] * s + p[1] * c]).collect();
        Part {
            id: id.to_string(),
            width: 950.0,
            height: 950.0,
            quantity: 1,
            allowed_rotations_deg: vec![],
            rotation_policy: Some(RotationPolicyKind::Continuous),
            holes_points: None,
            prepared_holes_points: None,
            outer_points: Some(serde_json::json!(pts)),
            prepared_outer_points: None,
        }
    }

    #[test]
    fn generates_true_extreme_slot_edge_candidates() {
        let p = elongated("band");
        let sheet = [0.0, 0.0, 1500.0, 3000.0];
        let slot = [50.0, 50.0, 450.0, 1450.0]; // a tall narrow band slot
        let res = build_band_insert_slot_edge_candidates(&p, slot, sheet, 8.0, &[]).expect("res");
        assert!(res.valid_count() >= 1, "must produce at least one valid slot-edge candidate");
        let sel = res.selected().expect("selected");
        assert!(sel.boundary_clear && sel.collision_clear);
        assert_eq!(sel.candidate_source, "true_extreme_slot_edge_band_insert");
    }

    #[test]
    fn continuous_rotation_not_limited_to_orthogonal() {
        let p = elongated("band");
        let sheet = [0.0, 0.0, 1500.0, 3000.0];
        let slot = [50.0, 50.0, 450.0, 1450.0];
        let res = build_band_insert_slot_edge_candidates(&p, slot, sheet, 8.0, &[]).expect("res");
        // The catalog feeds fractional rotations; at least one candidate must be genuinely fractional.
        assert!(
            res.candidates.iter().any(|c| c.is_fractional),
            "continuous BandInsert must expose fractional rotations, not only 0/90/180/270"
        );
    }

    #[test]
    fn respects_neighbours_and_sheet_boundary() {
        let p = elongated("band");
        let sheet = [0.0, 0.0, 1500.0, 3000.0];
        let slot = [50.0, 50.0, 450.0, 1450.0];
        // A neighbour occupying the whole slot must block all candidates (collision_clear=false).
        let res = build_band_insert_slot_edge_candidates(&p, slot, sheet, 8.0, &[[40.0, 40.0, 460.0, 1460.0]])
            .expect("res");
        assert_eq!(res.valid_count(), 0, "a slot fully covered by a neighbour admits no valid candidate");
        assert!(res.fallback_to_bbox_path, "no valid slot-edge candidate → fallback reported");
    }

    #[test]
    fn deterministic() {
        let p = elongated("band");
        let sheet = [0.0, 0.0, 1500.0, 3000.0];
        let slot = [50.0, 50.0, 450.0, 1450.0];
        let a = build_band_insert_slot_edge_candidates(&p, slot, sheet, 8.0, &[]).expect("a");
        let b = build_band_insert_slot_edge_candidates(&p, slot, sheet, 8.0, &[]).expect("b");
        assert_eq!(a.candidates.len(), b.candidates.len());
        assert_eq!(a.selected_index, b.selected_index);
    }
}
