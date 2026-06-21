//! SGH-Q56 — One critical large part, sheet-edge placement with TRUE contour extrema and
//! CONTINUOUS rotation.
//!
//! This is deliberately narrow: place ONE priority/critical large part correctly against one sheet
//! edge using the part's real geometry. No multi-part nesting, no sheet-count optimisation.
//!
//! The placement is computed entirely from the **real spacing-offset contour** (the same offset
//! geometry the solver uses for collision/boundary), never from a bbox shortcut:
//!   1. The continuous rotation is derived from the part's real dominant contour edge.
//!   2. The rotated, spacing-offset contour's TRUE extrema (min/max of the world points) are used.
//!   3. The part is translated so the correct extremum lands exactly on the margin line.
//!   4. Boundary is validated against the exact rotated/offset world contour.

use crate::geometry::Point;
use crate::item::Part;
use crate::optimizer::cde_adapter::{
    prepare_base_shape_native, prepare_spacing_base_shape_native, transform_base_to_candidate,
};

use super::contour_features::ContourFeatureSet;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum SheetEdge {
    Left,
    Right,
    Bottom,
    Top,
}

impl SheetEdge {
    pub(crate) fn as_str(self) -> &'static str {
        match self {
            SheetEdge::Left => "left",
            SheetEdge::Right => "right",
            SheetEdge::Bottom => "bottom",
            SheetEdge::Top => "top",
        }
    }
    /// The sheet axis the part's dominant edge is aligned parallel to (deg, mod 180).
    fn target_axis_deg(self) -> f64 {
        match self {
            SheetEdge::Left | SheetEdge::Right => 90.0, // vertical edge → dominant edge vertical
            SheetEdge::Bottom | SheetEdge::Top => 0.0,  // horizontal edge → dominant edge horizontal
        }
    }
}

/// Full diagnostics for one sheet-edge placement (machine-readable; serialised to JSON by the test).
#[derive(Debug, Clone)]
pub(crate) struct EdgePlacement {
    pub candidate_source: &'static str,
    pub target_sheet_edge: &'static str,
    pub part_id: String,
    pub continuous_rotation: bool,
    pub selected_part_edge_index: usize,
    pub selected_part_edge_angle_deg: f64,
    pub selected_part_edge_length: f64,
    pub target_axis_angle_deg: f64,
    pub rotation_before_deg: f64,
    pub rotation_after_deg: f64,
    pub rotation_delta_deg: f64,
    pub spacing_mm: f64,
    pub margin_mm: f64,
    pub sheet_width: f64,
    pub sheet_height: f64,
    pub rotated_offset_min_x: f64,
    pub rotated_offset_max_x: f64,
    pub rotated_offset_min_y: f64,
    pub rotated_offset_max_y: f64,
    pub translation_x: f64,
    pub translation_y: f64,
    pub distance_to_target_margin_line: f64,
    pub boundary_clear: bool,
    pub collision_clear: bool,
    pub rejection_reason: Option<String>,
    /// The final placed spacing-offset contour in world coordinates (for the visual artifact).
    pub world_contour: Vec<[f64; 2]>,
}

/// The rotation (deg) that makes `edge_angle_deg` parallel to `target_axis_deg` (mod 180), i.e. the
/// continuous rotation that aligns the chosen part edge to the sheet axis. NOT snapped — if the
/// dominant edge is genuinely axis-aligned the result is a clean 0/90, otherwise it is continuous.
fn align_rotation(edge_angle_deg: f64, target_axis_deg: f64) -> f64 {
    (target_axis_deg - edge_angle_deg).rem_euclid(180.0)
}

/// SGH-Q56: how the continuous rotation is derived from the part's real geometry.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum RotationStrategy {
    /// Align the longest dominant contour edge to the sheet axis (≈90° for a vertical edge when the
    /// edge is axis-aligned; continuous otherwise).
    DominantEdge,
    /// Rotate to the orientation that minimises the part's extent PERPENDICULAR to the edge (the
    /// tight-against-edge orientation). Genuinely continuous — for LV8 the optimum is ≈92°, NOT 90°,
    /// which proves the rotation is computed, not snapped.
    MinWidthAgainstEdge,
}

/// SGH-Q56: continuous rotation minimising the offset contour's extent perpendicular to `edge`.
/// Coarse 0.25° scan + 0.01° refine over the real rotated offset geometry (no bbox of the part —
/// the extent is measured on the actual rotated world points). Never snapped.
fn min_perpendicular_width_rotation(offset: &crate::optimizer::cde_adapter::CdeBaseShape, edge: SheetEdge) -> f64 {
    let perp_extent = |rot: f64| -> f64 {
        match transform_base_to_candidate(offset, 0.0, 0.0, rot) {
            Some(s) => match edge {
                // vertical edge → perpendicular extent is the X span; horizontal edge → Y span.
                SheetEdge::Left | SheetEdge::Right => s.max_x - s.min_x,
                SheetEdge::Bottom | SheetEdge::Top => s.max_y - s.min_y,
            },
            None => f64::MAX,
        }
    };
    let mut best = 0.0_f64;
    let mut best_w = f64::MAX;
    let mut a = 0.0;
    while a < 180.0 {
        let w = perp_extent(a);
        if w < best_w {
            best_w = w;
            best = a;
        }
        a += 0.25;
    }
    // refine ±0.25° at 0.01°
    let mut a = best - 0.25;
    while a <= best + 0.25 {
        let w = perp_extent(a);
        if w < best_w {
            best_w = w;
            best = a;
        }
        a += 0.01;
    }
    best.rem_euclid(180.0)
}

/// Place one critical large `part` against `edge` of a `sheet_w × sheet_h` sheet, using continuous
/// rotation from the part's real geometry (`strategy`), the real spacing-offset contour, true
/// extrema, and exact margin positioning. Returns rich diagnostics + the placed world contour.
pub(crate) fn place_critical_on_sheet_edge(
    part: &Part,
    spacing_mm: f64,
    margin_mm: f64,
    sheet_w: f64,
    sheet_h: f64,
    edge: SheetEdge,
    strategy: RotationStrategy,
) -> Result<EdgePlacement, String> {
    let half_spacing = spacing_mm * 0.5;
    // Real geometry: true contour (for the dominant edge) + spacing-offset contour (for placement).
    let base = prepare_base_shape_native(part).map_err(|e| e.to_string())?;
    let offset = prepare_spacing_base_shape_native(part, half_spacing)?;

    // Dominant contour edge = the longest dominant edge of the REAL outer contour (extreme-supported,
    // not a bbox side). Continuous rotation is derived from its real angle.
    let feats = ContourFeatureSet::extract(&base);
    let dom = feats
        .dominant_edges
        .iter()
        .max_by(|a, b| a.length.partial_cmp(&b.length).unwrap_or(std::cmp::Ordering::Equal))
        .ok_or("no dominant edge on contour")?;
    let edge_angle = dom.angle_deg;
    let target = edge.target_axis_deg();
    let rot = match strategy {
        RotationStrategy::DominantEdge => align_rotation(edge_angle, target),
        RotationStrategy::MinWidthAgainstEdge => min_perpendicular_width_rotation(&offset, edge),
    };

    // Rotate the offset contour at the origin → TRUE extrema of the rotated offset geometry.
    let r0 = transform_base_to_candidate(&offset, 0.0, 0.0, rot)
        .ok_or("rotate-at-origin transform failed")?;
    let (min_x0, max_x0, min_y0, max_y0) = (r0.min_x, r0.max_x, r0.min_y, r0.max_y);

    // Translate: land the correct true extremum exactly on the margin line; centre the free axis.
    let (tx, ty) = match edge {
        SheetEdge::Left => (margin_mm - min_x0, sheet_h * 0.5 - (min_y0 + max_y0) * 0.5),
        SheetEdge::Right => (sheet_w - margin_mm - max_x0, sheet_h * 0.5 - (min_y0 + max_y0) * 0.5),
        SheetEdge::Bottom => (sheet_w * 0.5 - (min_x0 + max_x0) * 0.5, margin_mm - min_y0),
        SheetEdge::Top => (sheet_w * 0.5 - (min_x0 + max_x0) * 0.5, sheet_h - margin_mm - max_y0),
    };

    let placed = transform_base_to_candidate(&offset, tx, ty, rot)
        .ok_or("final placement transform failed")?;

    // Exact boundary validation against the rotated/offset world contour (no bbox substitute).
    let eps = 1e-6;
    let boundary_clear = placed.world_pts.iter().all(|p: &Point| {
        p.x >= -eps && p.x <= sheet_w + eps && p.y >= -eps && p.y <= sheet_h + eps
    });
    // Distance of the aligned extremum to its target margin line (should be ~0).
    let distance_to_target_margin_line = match edge {
        SheetEdge::Left => placed.min_x - margin_mm,
        SheetEdge::Right => (sheet_w - margin_mm) - placed.max_x,
        SheetEdge::Bottom => placed.min_y - margin_mm,
        SheetEdge::Top => (sheet_h - margin_mm) - placed.max_y,
    };

    let world_contour: Vec<[f64; 2]> = placed.world_pts.iter().map(|p| [p.x, p.y]).collect();

    Ok(EdgePlacement {
        candidate_source: match strategy {
            RotationStrategy::DominantEdge => "sheet_edge.true_extreme.dominant_edge",
            RotationStrategy::MinWidthAgainstEdge => "sheet_edge.true_extreme.min_width_continuous",
        },
        target_sheet_edge: edge.as_str(),
        part_id: part.id.clone(),
        continuous_rotation: true,
        selected_part_edge_index: dom.edge_index,
        selected_part_edge_angle_deg: edge_angle,
        selected_part_edge_length: dom.length,
        target_axis_angle_deg: target,
        rotation_before_deg: 0.0,
        rotation_after_deg: rot,
        rotation_delta_deg: rot,
        spacing_mm,
        margin_mm,
        sheet_width: sheet_w,
        sheet_height: sheet_h,
        rotated_offset_min_x: min_x0,
        rotated_offset_max_x: max_x0,
        rotated_offset_min_y: min_y0,
        rotated_offset_max_y: max_y0,
        translation_x: tx,
        translation_y: ty,
        distance_to_target_margin_line,
        boundary_clear,
        collision_clear: true, // single part on an empty sheet → no neighbour pairs
        rejection_reason: if boundary_clear {
            None
        } else {
            Some("contour outside sheet boundary".to_string())
        },
        world_contour,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use std::path::PathBuf;

    fn lv8_part() -> Part {
        let base = std::fs::read_to_string(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../artifacts/benchmarks/sgh_q32/inputs/case_01_2x1500x3000.json"
        ))
        .expect("fixture");
        let v: serde_json::Value = serde_json::from_str(&base).unwrap();
        let p = v["parts"]
            .as_array()
            .unwrap()
            .iter()
            .find(|x| x["id"].as_str().unwrap_or("").starts_with("Lv8_11612"))
            .expect("Lv8_11612");
        Part {
            id: p["id"].as_str().unwrap().to_string(),
            width: p["width"].as_f64().unwrap(),
            height: p["height"].as_f64().unwrap(),
            quantity: 1,
            allowed_rotations_deg: vec![],
            rotation_policy: Some(crate::rotation_policy::RotationPolicyKind::Continuous),
            holes_points: None,
            prepared_holes_points: None,
            outer_points: Some(p["outer_points"].clone()),
            prepared_outer_points: None,
        }
    }

    fn dump(pl: &EdgePlacement, dir: &PathBuf, tag: &str) {
        let j = json!({
            "candidate_source": pl.candidate_source,
            "target_sheet_edge": pl.target_sheet_edge,
            "part_id": pl.part_id,
            "continuous_rotation": pl.continuous_rotation,
            "selected_part_edge_index": pl.selected_part_edge_index,
            "selected_part_edge_angle_deg": pl.selected_part_edge_angle_deg,
            "selected_part_edge_length": pl.selected_part_edge_length,
            "target_axis_angle_deg": pl.target_axis_angle_deg,
            "rotation_before_deg": pl.rotation_before_deg,
            "rotation_after_deg": pl.rotation_after_deg,
            "rotation_delta_deg": pl.rotation_delta_deg,
            "spacing_mm": pl.spacing_mm,
            "margin_mm": pl.margin_mm,
            "sheet_width": pl.sheet_width,
            "sheet_height": pl.sheet_height,
            "rotated_offset_min_x": pl.rotated_offset_min_x,
            "rotated_offset_max_x": pl.rotated_offset_max_x,
            "rotated_offset_min_y": pl.rotated_offset_min_y,
            "rotated_offset_max_y": pl.rotated_offset_max_y,
            "translation_x": pl.translation_x,
            "translation_y": pl.translation_y,
            "distance_to_target_margin_line": pl.distance_to_target_margin_line,
            "boundary_clear": pl.boundary_clear,
            "collision_clear": pl.collision_clear,
            "rejection_reason": pl.rejection_reason,
            "accepted_sheet_edge_alignment": pl.boundary_clear && pl.distance_to_target_margin_line.abs() < 1e-3,
            "world_contour": pl.world_contour,
        });
        std::fs::create_dir_all(dir).unwrap();
        std::fs::write(
            dir.join(format!("placement_{}_{}.json", tag, pl.target_sheet_edge)),
            serde_json::to_string_pretty(&j).unwrap(),
        )
        .unwrap();
    }

    #[test]
    fn lv8_critical_part_sheet_edge_placement_all_edges() {
        let part = lv8_part();
        let (spacing, margin, sw, sh) = (5.0, 5.0, 1500.0, 3000.0);
        let out_dir = PathBuf::from(concat!(env!("CARGO_MANIFEST_DIR"), "/../../artifacts/benchmarks/sgh_q56"));

        let mut any_ok = false;
        // (a) dominant-edge strategy for all four edges (left/right valid; bottom/top correctly
        // rejected — the 2522 mm long part cannot lie horizontally on a 1500 mm-wide sheet).
        for edge in [SheetEdge::Left, SheetEdge::Right, SheetEdge::Bottom, SheetEdge::Top] {
            let pl = place_critical_on_sheet_edge(&part, spacing, margin, sw, sh, edge, RotationStrategy::DominantEdge).unwrap();
            dump(&pl, &out_dir, "dominant");
            eprintln!(
                "[Q56][dominant] {} | edge_angle={:.4} rot={:.4} margin_dist={:.6} boundary_clear={}",
                pl.target_sheet_edge, pl.selected_part_edge_angle_deg, pl.rotation_after_deg,
                pl.distance_to_target_margin_line, pl.boundary_clear
            );
            if pl.boundary_clear && pl.distance_to_target_margin_line.abs() < 1e-3 {
                any_ok = true;
            }
        }
        // (b) min-width continuous strategy on the left edge — proves the rotation is genuinely
        // computed (≈92°, NOT a 90° snap) and gives the tight against-edge fit.
        for edge in [SheetEdge::Left, SheetEdge::Right] {
            let pl = place_critical_on_sheet_edge(&part, spacing, margin, sw, sh, edge, RotationStrategy::MinWidthAgainstEdge).unwrap();
            dump(&pl, &out_dir, "minwidth");
            eprintln!(
                "[Q56][minwidth] {} | rot={:.4} (continuous) margin_dist={:.6} boundary_clear={} x_extent={:.2}",
                pl.target_sheet_edge, pl.rotation_after_deg, pl.distance_to_target_margin_line,
                pl.boundary_clear, pl.rotated_offset_max_x - pl.rotated_offset_min_x
            );
            assert!(
                (pl.rotation_after_deg - 90.0).abs() > 0.1 && (pl.rotation_after_deg - 0.0).abs() > 0.1,
                "min-width rotation must be genuinely continuous (not snapped to 0/90): got {}",
                pl.rotation_after_deg
            );
            if pl.boundary_clear && pl.distance_to_target_margin_line.abs() < 1e-3 {
                any_ok = true;
            }
        }
        assert!(any_ok, "at least one valid sheet-edge placement (boundary-clear + margin-exact)");
    }
}
