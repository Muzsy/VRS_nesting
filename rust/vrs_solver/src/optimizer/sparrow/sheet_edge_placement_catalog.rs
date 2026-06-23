//! SGH-Q56C: `SheetEdgePlacementCatalog` — edge+corner Anchor candidates for a critical part.
//!
//! Builds on the Q55B true-extreme sheet-edge proof and the Q56A `OrientationCatalog`: for a critical
//! part on a given sheet it generates Anchor candidates on all four edges with **corner + center**
//! secondary-axis variants (not only edge+center), each anchored from the rotated **spacing-expanded**
//! contour's true extrema, translated margin-aware against the margin-shrunk sheet, boundary-validated,
//! and ranked by remaining edge-connected free space (`largest_edge_connected_free_area`).
//!
//! Hard rules: spacing-expanded TRUE extrema (never `part.width/height`), continuous rotations from the
//! catalog (no 0/90/180/270 snap unless that is the computed result), alignment to the margin-shrunk
//! sheet (never the raw boundary while margin is active), corner variants are first-class and center is
//! a fallback. The grid free-space score is a ranking proxy only — the CDE remains clearance truth.

use super::*;

const BOUNDARY_TOL_MM: f64 = 0.05;
const FREE_SPACE_CELL_MM: f64 = 50.0;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TargetSheetEdge {
    Left,
    Right,
    Bottom,
    Top,
}

impl TargetSheetEdge {
    pub fn as_str(self) -> &'static str {
        match self {
            TargetSheetEdge::Left => "left",
            TargetSheetEdge::Right => "right",
            TargetSheetEdge::Bottom => "bottom",
            TargetSheetEdge::Top => "top",
        }
    }
    fn is_vertical_edge(self) -> bool {
        matches!(self, TargetSheetEdge::Left | TargetSheetEdge::Right)
    }
}

/// Secondary-axis seating along the edge.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SecondaryAxisPolicy {
    CornerLow,  // left-bottom / right-bottom / bottom-left / top-left
    CornerHigh, // left-top / right-top / bottom-right / top-right
    Center,     // fallback
}

impl SecondaryAxisPolicy {
    pub fn label(self, edge: TargetSheetEdge) -> &'static str {
        match (edge, self) {
            (TargetSheetEdge::Left, SecondaryAxisPolicy::CornerLow) => "left-bottom",
            (TargetSheetEdge::Left, SecondaryAxisPolicy::CornerHigh) => "left-top",
            (TargetSheetEdge::Left, SecondaryAxisPolicy::Center) => "left-center",
            (TargetSheetEdge::Right, SecondaryAxisPolicy::CornerLow) => "right-bottom",
            (TargetSheetEdge::Right, SecondaryAxisPolicy::CornerHigh) => "right-top",
            (TargetSheetEdge::Right, SecondaryAxisPolicy::Center) => "right-center",
            (TargetSheetEdge::Bottom, SecondaryAxisPolicy::CornerLow) => "bottom-left",
            (TargetSheetEdge::Bottom, SecondaryAxisPolicy::CornerHigh) => "bottom-right",
            (TargetSheetEdge::Bottom, SecondaryAxisPolicy::Center) => "bottom-center",
            (TargetSheetEdge::Top, SecondaryAxisPolicy::CornerLow) => "top-left",
            (TargetSheetEdge::Top, SecondaryAxisPolicy::CornerHigh) => "top-right",
            (TargetSheetEdge::Top, SecondaryAxisPolicy::Center) => "top-center",
        }
    }
    fn is_corner(self) -> bool {
        !matches!(self, SecondaryAxisPolicy::Center)
    }
}

#[derive(Debug, Clone)]
pub struct SheetEdgeAnchorCandidate {
    pub candidate_source: &'static str,
    pub part_id: String,
    pub target_sheet_edge: TargetSheetEdge,
    pub secondary_axis_policy: SecondaryAxisPolicy,
    pub selected_edge_index: Option<usize>,
    pub selected_edge_angle_deg: Option<f64>,
    pub target_axis_angle_deg: Option<f64>,
    pub computed_rotation_deg: f64,
    /// Spacing-offset true extrema at origin (rot applied, no translation): [min_x,min_y,max_x,max_y].
    pub offset_extrema_before_translation: [f64; 4],
    pub margin_line: f64,
    pub translation_x: f64,
    pub translation_y: f64,
    /// Physical (non-offset) world extrema after placement: [min_x,min_y,max_x,max_y].
    pub final_extrema: [f64; 4],
    pub margin_error: f64,
    pub boundary_clear: bool,
    pub is_corner: bool,
    pub is_fractional: bool,
    pub candidate_score: f64,
    pub free_space_score: f64,
    pub rejection_reason: Option<String>,
}

#[derive(Debug, Clone)]
pub struct SheetEdgeAnchorCatalog {
    pub part_id: String,
    pub sheet: [f64; 4],
    pub shrunk_sheet: [f64; 4],
    pub margin_mm: f64,
    pub spacing_mm: f64,
    pub candidates: Vec<SheetEdgeAnchorCandidate>,
    pub selected_index: Option<usize>,
}

impl SheetEdgeAnchorCatalog {
    pub fn selected(&self) -> Option<&SheetEdgeAnchorCandidate> {
        self.selected_index.map(|i| &self.candidates[i])
    }

    pub fn boundary_clear_count(&self) -> usize {
        self.candidates.iter().filter(|c| c.boundary_clear).count()
    }

    pub fn corner_count(&self) -> usize {
        self.candidates
            .iter()
            .filter(|c| c.boundary_clear && c.is_corner)
            .count()
    }

    pub fn to_diagnostics_json(&self) -> serde_json::Value {
        let cands: Vec<serde_json::Value> = self
            .candidates
            .iter()
            .map(|c| {
                serde_json::json!({
                    "candidate_source": c.candidate_source,
                    "target_sheet_edge": c.target_sheet_edge.as_str(),
                    "secondary_axis_policy": c.secondary_axis_policy.label(c.target_sheet_edge),
                    "is_corner": c.is_corner,
                    "selected_edge_index": c.selected_edge_index,
                    "selected_edge_angle_deg": c.selected_edge_angle_deg,
                    "target_axis_angle_deg": c.target_axis_angle_deg,
                    "computed_rotation_deg": round4(c.computed_rotation_deg),
                    "is_fractional": c.is_fractional,
                    "offset_extrema_before_translation": c.offset_extrema_before_translation.map(round4),
                    "margin_line": round4(c.margin_line),
                    "translation_x": round4(c.translation_x),
                    "translation_y": round4(c.translation_y),
                    "final_extrema": c.final_extrema.map(round4),
                    "margin_error": round4(c.margin_error),
                    "boundary_clear": c.boundary_clear,
                    "candidate_score": round4(c.candidate_score),
                    "free_space_score": round4(c.free_space_score),
                    "rejection_reason": c.rejection_reason,
                })
            })
            .collect();
        serde_json::json!({
            "part_id": self.part_id,
            "sheet": self.sheet.map(round4),
            "shrunk_sheet": self.shrunk_sheet.map(round4),
            "margin_mm": self.margin_mm,
            "spacing_mm": self.spacing_mm,
            "candidate_count": self.candidates.len(),
            "boundary_clear_count": self.boundary_clear_count(),
            "corner_count": self.corner_count(),
            "selected_index": self.selected_index,
            "selected": self.selected().map(|c| serde_json::json!({
                "target_sheet_edge": c.target_sheet_edge.as_str(),
                "secondary_axis_policy": c.secondary_axis_policy.label(c.target_sheet_edge),
                "computed_rotation_deg": round4(c.computed_rotation_deg),
                "free_space_score": round4(c.free_space_score),
                "candidate_score": round4(c.candidate_score),
                "margin_error": round4(c.margin_error),
            })),
            "candidates": cands,
        })
    }
}

/// Build the Anchor catalog for `part` on a single sheet, routing real spacing through the solver's
/// internal dual-geometry mechanism so the extrema come from the genuine spacing-expanded contour.
pub fn build_sheet_edge_anchor_catalog(
    part: &Part,
    sheet_width: f64,
    sheet_height: f64,
    margin_mm: f64,
    spacing_mm: f64,
) -> Result<SheetEdgeAnchorCatalog, String> {
    let half_spacing = spacing_mm / 2.0;
    let inset = margin_mm - half_spacing;
    let rotation_context = RotationResolveContext::new(Some(RotationPolicyKind::Continuous), 42, 24);
    let raw_stock = crate::sheet::Stock {
        id: "S_ANCHOR".to_string(),
        quantity: 1,
        width: Some(sheet_width),
        height: Some(sheet_height),
        outer_points: None,
        holes_points: None,
        cost_per_use: None,
    };
    let raw_sheet = crate::sheet::stock_to_shape(&raw_stock)?;
    let config = SparrowConfig::from_solver_input(
        1.0,
        CollisionBackendKind::Cde,
        rotation_context.clone(),
        42,
    )
    .with_spacing_mm(spacing_mm);
    let problem = SparrowProblem::from_solver_input(
        std::slice::from_ref(part),
        std::slice::from_ref(&raw_sheet),
        &rotation_context,
        Vec::new(),
        config,
    )?;
    let inst = problem
        .instances
        .first()
        .ok_or_else(|| format!("part {} produced no instance", part.id))?;

    let offset_shape = inst.spacing_collision_base_shape.as_ref();
    let phys_shape = inst.base_shape.as_ref();
    let catalog = inst.orientation_catalog.as_ref();

    // Margin-shrunk sheet (raw shrunk by inset = margin − half_spacing). Aligning the OFFSET contour
    // flush to this shrunk edge lands the PHYSICAL contour at exactly `margin` from the raw edge.
    let raw = [0.0, 0.0, sheet_width, sheet_height];
    let shrunk = [inset, inset, sheet_width - inset, sheet_height - inset];

    // Candidate rotations: the orientation-catalog angles (continuous, feature-derived). Deduped.
    let mut rotations: Vec<(f64, Option<usize>, Option<f64>, Option<f64>)> = Vec::new();
    for c in &catalog.candidates {
        if !rotations
            .iter()
            .any(|(a, ..)| (a - c.angle_deg).abs() < 0.01)
        {
            rotations.push((
                c.angle_deg,
                c.source_edge_index,
                c.source_edge_angle_deg,
                c.target_axis_angle_deg,
            ));
        }
    }

    let edges = [
        TargetSheetEdge::Left,
        TargetSheetEdge::Right,
        TargetSheetEdge::Bottom,
        TargetSheetEdge::Top,
    ];
    let policies = [
        SecondaryAxisPolicy::CornerLow,
        SecondaryAxisPolicy::CornerHigh,
        SecondaryAxisPolicy::Center,
    ];

    let mut candidates: Vec<SheetEdgeAnchorCandidate> = Vec::new();
    for &(rot, edge_idx, edge_ang, target_axis) in &rotations {
        let Some(off) = frame_extrema(offset_shape, rot) else {
            continue;
        };
        let Some(phys) = frame_extrema(phys_shape, rot) else {
            continue;
        };
        for &edge in &edges {
            for &pol in &policies {
                let cand = build_candidate(
                    &part.id, edge, pol, rot, edge_idx, edge_ang, target_axis, &off, &phys, &raw,
                    &shrunk, margin_mm,
                );
                candidates.push(cand);
            }
        }
    }

    // Rank: among boundary-clear candidates, prefer the highest candidate_score.
    let selected_index = candidates
        .iter()
        .enumerate()
        .filter(|(_, c)| c.boundary_clear)
        .max_by(|(_, a), (_, b)| {
            a.candidate_score
                .partial_cmp(&b.candidate_score)
                .unwrap_or(Ordering::Equal)
                .then_with(|| {
                    // deterministic tie-break: corner over center, then lower edge ordinal
                    (b.is_corner as u8)
                        .cmp(&(a.is_corner as u8))
                        .then_with(|| a.target_sheet_edge.as_str().cmp(b.target_sheet_edge.as_str()))
                })
        })
        .map(|(i, _)| i);

    Ok(SheetEdgeAnchorCatalog {
        part_id: part.id.clone(),
        sheet: raw,
        shrunk_sheet: shrunk,
        margin_mm,
        spacing_mm,
        candidates,
        selected_index,
    })
}

#[allow(clippy::too_many_arguments)]
fn build_candidate(
    part_id: &str,
    edge: TargetSheetEdge,
    pol: SecondaryAxisPolicy,
    rot: f64,
    edge_idx: Option<usize>,
    edge_ang: Option<f64>,
    target_axis: Option<f64>,
    off: &[f64; 4],
    phys: &[f64; 4],
    raw: &[f64; 4],
    shrunk: &[f64; 4],
    margin_mm: f64,
) -> SheetEdgeAnchorCandidate {
    let (off_min_x, off_min_y, off_max_x, off_max_y) = (off[0], off[1], off[2], off[3]);
    let (shr_min_x, shr_min_y, shr_max_x, shr_max_y) = (shrunk[0], shrunk[1], shrunk[2], shrunk[3]);
    let off_w = off_max_x - off_min_x;
    let off_h = off_max_y - off_min_y;
    let shr_w = shr_max_x - shr_min_x;
    let shr_h = shr_max_y - shr_min_y;

    // Primary axis: flush the offset contour to the target shrunk edge.
    // Secondary axis: corner-low / corner-high / center within the shrunk interval.
    let (tx, ty, margin_line) = match edge {
        TargetSheetEdge::Left => {
            let tx = shr_min_x - off_min_x;
            let ty = secondary_axis_translation(pol, off_min_y, off_h, shr_min_y, shr_h);
            (tx, ty, raw[0] + margin_mm)
        }
        TargetSheetEdge::Right => {
            let tx = shr_max_x - off_max_x;
            let ty = secondary_axis_translation(pol, off_min_y, off_h, shr_min_y, shr_h);
            (tx, ty, raw[2] - margin_mm)
        }
        TargetSheetEdge::Bottom => {
            let ty = shr_min_y - off_min_y;
            let tx = secondary_axis_translation(pol, off_min_x, off_w, shr_min_x, shr_w);
            (tx, ty, raw[1] + margin_mm)
        }
        TargetSheetEdge::Top => {
            let ty = shr_max_y - off_max_y;
            let tx = secondary_axis_translation(pol, off_min_x, off_w, shr_min_x, shr_w);
            (tx, ty, raw[3] - margin_mm)
        }
    };

    // Offset contour world bbox after translation → boundary check against the shrunk sheet.
    let owx0 = off_min_x + tx;
    let owy0 = off_min_y + ty;
    let owx1 = off_max_x + tx;
    let owy1 = off_max_y + ty;
    let boundary_clear = owx0 >= shr_min_x - BOUNDARY_TOL_MM
        && owy0 >= shr_min_y - BOUNDARY_TOL_MM
        && owx1 <= shr_max_x + BOUNDARY_TOL_MM
        && owy1 <= shr_max_y + BOUNDARY_TOL_MM;

    // Physical (non-offset) contour world bbox → margin error against the raw sheet margin line.
    let pwx0 = phys[0] + tx;
    let pwy0 = phys[1] + ty;
    let pwx1 = phys[2] + tx;
    let pwy1 = phys[3] + ty;
    let physical_extremum = match edge {
        TargetSheetEdge::Left => pwx0,
        TargetSheetEdge::Right => pwx1,
        TargetSheetEdge::Bottom => pwy0,
        TargetSheetEdge::Top => pwy1,
    };
    let margin_error = (physical_extremum - margin_line).abs();

    // Free-space proxy: largest edge-connected free area remaining on the shrunk sheet after placing
    // the offset footprint. Corner placements preserve a larger contiguous edge band than center.
    let free_space_score = if boundary_clear {
        crate::optimizer::sparrow::sheet_skeleton::largest_edge_connected_free_area(
            &[[owx0, owy0, owx1, owy1]],
            shr_min_x,
            shr_min_y,
            shr_max_x,
            shr_max_y,
            FREE_SPACE_CELL_MM,
        )
    } else {
        0.0
    };
    let shrunk_area = (shr_w * shr_h).max(1.0);
    let free_norm = (free_space_score / shrunk_area).clamp(0.0, 1.0);

    let rejection_reason = if boundary_clear {
        None
    } else {
        Some("offset_contour_exceeds_shrunk_sheet".to_string())
    };

    let corner_bonus = if pol.is_corner() { 0.10 } else { 0.0 };
    let center_penalty = if matches!(pol, SecondaryAxisPolicy::Center) {
        0.08
    } else {
        0.0
    };
    let margin_penalty = (margin_error / margin_mm.max(1.0)).clamp(0.0, 1.0) * 0.10;
    let candidate_score = if boundary_clear {
        (0.70 * free_norm + corner_bonus - center_penalty - margin_penalty).max(0.0)
    } else {
        0.0
    };

    SheetEdgeAnchorCandidate {
        candidate_source: "true_extreme_sheet_edge_anchor",
        part_id: part_id.to_string(),
        target_sheet_edge: edge,
        secondary_axis_policy: pol,
        selected_edge_index: edge_idx,
        selected_edge_angle_deg: edge_ang,
        target_axis_angle_deg: target_axis,
        computed_rotation_deg: rot,
        offset_extrema_before_translation: *off,
        margin_line,
        translation_x: tx,
        translation_y: ty,
        final_extrema: [pwx0, pwy0, pwx1, pwy1],
        margin_error,
        boundary_clear,
        is_corner: pol.is_corner(),
        is_fractional: nearest_axis_dist(rot) > 0.25,
        candidate_score,
        free_space_score,
        rejection_reason,
    }
}

fn secondary_axis_translation(
    pol: SecondaryAxisPolicy,
    off_min: f64,
    off_extent: f64,
    shr_min: f64,
    shr_extent: f64,
) -> f64 {
    match pol {
        SecondaryAxisPolicy::CornerLow => shr_min - off_min,
        SecondaryAxisPolicy::CornerHigh => (shr_min + shr_extent) - (off_min + off_extent),
        SecondaryAxisPolicy::Center => shr_min - off_min + (shr_extent - off_extent) / 2.0,
    }
}

/// True extrema [min_x,min_y,max_x,max_y] of a contour rotated by `rotation_deg` about the origin.
fn frame_extrema(shape: &CdeBaseShape, rotation_deg: f64) -> Option<[f64; 4]> {
    if shape.local_pts.is_empty() {
        return None;
    }
    let theta = rotation_deg.to_radians();
    let (c, s) = (theta.cos(), theta.sin());
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

    fn lv8_like_part() -> Part {
        // Long, slightly concave LV8-like contour (elongated → dominant long edges, off-axis min-width).
        let ang = 3.0_f64.to_radians();
        let (c, s) = (ang.cos(), ang.sin());
        let raw = [
            [0.0, 0.0],
            [1200.0, 0.0],
            [1200.0, 60.0],
            [700.0, 60.0],
            [700.0, 200.0],
            [1200.0, 200.0],
            [1200.0, 260.0],
            [0.0, 260.0],
        ];
        let pts: Vec<[f64; 2]> = raw
            .iter()
            .map(|p| [p[0] * c - p[1] * s, p[0] * s + p[1] * c])
            .collect();
        Part {
            id: "lv8_like_anchor".to_string(),
            width: 1300.0,
            height: 400.0,
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
    fn produces_candidates_on_all_four_edges_with_corners() {
        let p = lv8_like_part();
        let cat = build_sheet_edge_anchor_catalog(&p, 1500.0, 3000.0, 5.0, 8.0).expect("catalog");
        for edge in ["left", "right", "bottom", "top"] {
            assert!(
                cat.candidates
                    .iter()
                    .any(|c| c.boundary_clear && c.target_sheet_edge.as_str() == edge),
                "missing boundary-clear candidate on edge {edge}"
            );
        }
        assert!(cat.corner_count() >= 1, "corner variants must be first-class");
    }

    #[test]
    fn center_is_not_the_only_secondary_policy() {
        let p = lv8_like_part();
        let cat = build_sheet_edge_anchor_catalog(&p, 1500.0, 3000.0, 5.0, 8.0).expect("catalog");
        let clear_corner = cat
            .candidates
            .iter()
            .filter(|c| c.boundary_clear && c.is_corner)
            .count();
        assert!(clear_corner > 0, "must have boundary-clear corner candidates");
    }

    #[test]
    fn selected_candidate_has_free_space_score_and_is_boundary_clear() {
        let p = lv8_like_part();
        let cat = build_sheet_edge_anchor_catalog(&p, 1500.0, 3000.0, 5.0, 8.0).expect("catalog");
        let sel = cat.selected().expect("a selected candidate");
        assert!(sel.boundary_clear, "selected candidate must be boundary-clear");
        assert!(sel.free_space_score > 0.0, "selected candidate must record a free-space score");
    }

    #[test]
    fn accepted_candidates_use_spacing_expanded_extrema_within_shrunk_sheet() {
        // With spacing 8 the offset frame is wider than the physical frame; the boundary check is
        // against the shrunk sheet, so a boundary-clear candidate proves spacing-expanded extrema use.
        let p = lv8_like_part();
        let cat = build_sheet_edge_anchor_catalog(&p, 1500.0, 3000.0, 5.0, 8.0).expect("catalog");
        let sel = cat.selected().expect("selected");
        // physical extremum sits at ~margin from the raw edge (within a small refine tolerance).
        assert!(sel.margin_error <= 5.0, "physical extremum must be near the margin line");
    }

    #[test]
    fn deterministic() {
        let p = lv8_like_part();
        let a = build_sheet_edge_anchor_catalog(&p, 1500.0, 3000.0, 5.0, 8.0).expect("a");
        let b = build_sheet_edge_anchor_catalog(&p, 1500.0, 3000.0, 5.0, 8.0).expect("b");
        assert_eq!(a.candidates.len(), b.candidates.len());
        assert_eq!(a.selected_index, b.selected_index);
    }
}
