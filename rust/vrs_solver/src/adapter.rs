use std::fmt;

use crate::io::{Metrics, Placement, SolverInput, SolverOutput, Unplaced};
use crate::item::{can_fit_any_stock, expand_instances, part_has_holes};
use crate::optimizer::{
    multisheet::MultiSheetManager,
    stopping::StoppingPolicy,
    try_place_on_sheet, SheetCursor,
};
use crate::sheet::{expand_sheets, stock_has_holes};

const PROFILE_PHASE1: &str = "jagua_optimizer_phase1_outer_only";

fn _unsupported_output(reason: &str, input: &SolverInput) -> SolverOutput {
    SolverOutput {
        contract_version: "v1".to_string(),
        status: "unsupported".to_string(),
        unsupported_reason: Some(reason.to_string()),
        placements: vec![],
        unplaced: vec![],
        metrics: Metrics {
            placed_count: 0,
            unplaced_count: input.parts.iter().map(|p| p.quantity as usize).sum(),
            sheet_count_used: 0,
            seed: input.seed,
            time_limit_s: input.time_limit_s,
            project_name: input.project_name.clone(),
        },
    }
}

pub fn solve(input: SolverInput) -> Result<SolverOutput, String> {
    if input.solver_profile.as_deref() == Some(PROFILE_PHASE1) {
        for part in &input.parts {
            if part_has_holes(part) {
                return Ok(_unsupported_output("UNSUPPORTED_PART_HOLES_PHASE1", &input));
            }
        }
        for stock in &input.stocks {
            if stock_has_holes(stock) {
                return Ok(_unsupported_output("UNSUPPORTED_STOCK_HOLES_PHASE1", &input));
            }
        }
        if let Some(margin_mm) = input.margin_mm {
            if margin_mm > 0.0 {
                return Ok(_unsupported_output("UNSUPPORTED_MARGIN_MM_RUNTIME", &input));
            }
        }
    }

    let sheets = expand_sheets(&input.stocks)?;
    let all_instances = expand_instances(&input.parts)?;
    let (placements, unplaced, diag) = if input.solver_profile.as_deref() == Some(PROFILE_PHASE1) {
        // Pre-filter: instances whose part cannot fit any sheet get PART_NEVER_FITS_STOCK.
        let mut pre_unplaced: Vec<Unplaced> = Vec::new();
        let mut instances: Vec<_> = Vec::new();
        for inst in all_instances {
            let part = input.parts.iter().find(|p| p.id == inst.part_id)
                .ok_or_else(|| format!("internal error: part not found: {}", inst.part_id))?;
            if !can_fit_any_stock(part, &sheets)? {
                pre_unplaced.push(Unplaced {
                    instance_id: inst.instance_id,
                    part_id: inst.part_id,
                    reason: "PART_NEVER_FITS_STOCK".to_string(),
                });
            } else {
                instances.push(inst);
            }
        }
        let repair_time_s = (input.time_limit_s as f64).max(1.0);
        let mut policy = StoppingPolicy::new(256, repair_time_s);
        let manager = MultiSheetManager::new(&input.parts, &sheets);
        let (p, mut u, ms_diag) = manager.run(&instances, &mut policy);
        u.extend(pre_unplaced);
        (p, u, Some(ms_diag))
    } else {
        // Row/cursor fallback for non-Phase1 profiles.
        let mut placements: Vec<Placement> = Vec::new();
        let mut unplaced: Vec<Unplaced> = Vec::new();
        let mut per_sheet_cursor: Vec<SheetCursor> = sheets
            .iter()
            .map(|_| SheetCursor { x: 0.0, y: 0.0, row_h: 0.0 })
            .collect();
        for instance in &all_instances {
            let part = input
                .parts
                .iter()
                .find(|p| p.id == instance.part_id)
                .ok_or_else(|| format!("internal error: part not found: {}", instance.part_id))?;
            if !can_fit_any_stock(part, &sheets)? {
                unplaced.push(Unplaced {
                    instance_id: instance.instance_id.clone(),
                    part_id: instance.part_id.clone(),
                    reason: "PART_NEVER_FITS_STOCK".to_string(),
                });
                continue;
            }
            let mut placed = None;
            for (idx, sheet) in sheets.iter().enumerate() {
                if let Some(c) = try_place_on_sheet(instance, sheet, &mut per_sheet_cursor[idx], idx) {
                    placed = Some(c);
                    break;
                }
            }
            if let Some(p) = placed {
                placements.push(p);
            } else {
                unplaced.push(Unplaced {
                    instance_id: instance.instance_id.clone(),
                    part_id: instance.part_id.clone(),
                    reason: "NO_CAPACITY".to_string(),
                });
            }
        }
        (placements, unplaced, None)
    };
    let _ = diag; // diagnostics available for future use; suppress unused warning
    let status = if unplaced.is_empty() { "ok" } else { "partial" }.to_string();
    let sheet_count_used = placements
        .iter()
        .map(|p| p.sheet_index)
        .max()
        .map(|v| v + 1)
        .unwrap_or(0);

    let placed_count = placements.len();
    let unplaced_count = unplaced.len();

    Ok(SolverOutput {
        contract_version: "v1".to_string(),
        status,
        unsupported_reason: None,
        placements,
        unplaced,
        metrics: Metrics {
            placed_count,
            unplaced_count,
            sheet_count_used,
            seed: input.seed,
            time_limit_s: input.time_limit_s,
            project_name: input.project_name,
        },
    })
}

// ---------------------------------------------------------------------------
// JaguaAdapter contract — VRS-owned PoC boundary (JG-04)
// Jagua-rs types stay internal; only VRS geometry types cross the public API.
// ---------------------------------------------------------------------------

/// VRS-owned error categories for the jagua backend boundary.
/// No jagua-rs types appear here.
#[derive(Debug)]
pub enum JaguaAdapterError {
    /// Input geometry could not be converted to jagua internal representation.
    ConversionError(String),
    /// A jagua backend operation returned an unexpected runtime error.
    BackendError(String),
    /// The requested operation is not yet supported by the adapter PoC.
    Unsupported(String),
}

impl fmt::Display for JaguaAdapterError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::ConversionError(s) => write!(f, "conversion_error: {s}"),
            Self::BackendError(s) => write!(f, "backend_error: {s}"),
            Self::Unsupported(s) => write!(f, "unsupported: {s}"),
        }
    }
}

/// Thin VRS adapter to the jagua-rs collision/geometry backend.
/// Accepts VRS-owned point slices; jagua types never appear in the public API.
/// Precision note: f64 VRS coordinates are narrowed to f32 for jagua (documented).
pub struct JaguaAdapter;

impl JaguaAdapter {
    /// Returns `true` if the two polygons (given as VRS Point slices) collide.
    ///
    /// Detection strategy (composing known jagua primitives):
    /// 1. Any corner of poly_b inside poly_a → collision.
    /// 2. Any corner of poly_a inside poly_b → collision.
    /// 3. Any edge of poly_a intersects any edge of poly_b → collision.
    pub fn check_polygon_collision(
        poly_a: &[crate::geometry::Point],
        poly_b: &[crate::geometry::Point],
    ) -> Result<bool, JaguaAdapterError> {
        use jagua_rs::geometry::geo_traits::CollidesWith;
        use crate::geometry::{jag_edge_from_points, to_jag_point, to_jag_polygon};

        let spoly_a = to_jag_polygon(poly_a, "poly_a")
            .map_err(JaguaAdapterError::ConversionError)?;
        let spoly_b = to_jag_polygon(poly_b, "poly_b")
            .map_err(JaguaAdapterError::ConversionError)?;

        // Point containment: any corner of B inside A?
        for p in poly_b {
            if spoly_a.collides_with(&to_jag_point(*p)) {
                return Ok(true);
            }
        }
        // Point containment: any corner of A inside B?
        for p in poly_a {
            if spoly_b.collides_with(&to_jag_point(*p)) {
                return Ok(true);
            }
        }
        // Edge-edge intersection
        let n_a = poly_a.len();
        let n_b = poly_b.len();
        for i in 0..n_a {
            let Some(edge_a) = jag_edge_from_points(poly_a[i], poly_a[(i + 1) % n_a]) else {
                continue;
            };
            for j in 0..n_b {
                let Some(edge_b) = jag_edge_from_points(poly_b[j], poly_b[(j + 1) % n_b]) else {
                    continue;
                };
                if edge_a.collides_with(&edge_b) {
                    return Ok(true);
                }
            }
        }
        Ok(false)
    }

    /// Returns `true` if the rectangular item fits entirely inside the sheet shape.
    /// Delegates to `optimizer::boundary::rect_within_boundary` — the canonical
    /// boundary policy point for all construction, repair, and scoring paths.
    pub fn check_rect_in_sheet(
        item_rect: crate::geometry::Rect,
        sheet: &crate::sheet::SheetShape,
    ) -> bool {
        crate::optimizer::boundary::rect_within_boundary(item_rect, sheet)
    }
}
