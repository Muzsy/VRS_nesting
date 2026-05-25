//! MultiSheetManager V1 — Phase 1 multi-sheet coordination layer.
//!
//! Provides explicit orchestration of construction + repair across multiple
//! sheet slots, with stable `sheet_count_used` semantics and per-sheet
//! diagnostics. The underlying construction and repair algorithms are
//! unchanged — this module adds a single, testable coordination boundary.

use crate::io::{Placement, Unplaced};
use crate::item::{Instance, Part};
use crate::rotation_policy::RotationResolveContext;
use crate::sheet::SheetShape;
use super::initializer::{
    bbox_from_placement, build_initial_layout_with_rotation_context, ConstructionDiagnostics,
};
use super::repair::{run_repair_with_rotation_context, RepairDiagnostics};
use super::sheet_elimination::{SheetEliminationDiagnostics, SheetEliminationEngine};
use super::stopping::StoppingPolicy;

// ---------------------------------------------------------------------------
// compute_sheet_count_used — stable helper, tested independently
// ---------------------------------------------------------------------------

/// Return the number of sheet slots used by a placement list.
///
/// Contract: `max(sheet_index) + 1` over all placements, or 0 if empty.
/// This is a "highest slot + 1" metric, not a "distinct count" metric.
/// A layout with only `sheet_index=1` returns 2, consistent with the v1
/// output contract.
pub fn compute_sheet_count_used(placements: &[Placement]) -> usize {
    placements
        .iter()
        .map(|p| p.sheet_index)
        .max()
        .map(|v| v + 1)
        .unwrap_or(0)
}

// ---------------------------------------------------------------------------
// Per-sheet summary
// ---------------------------------------------------------------------------

/// Per-sheet placement summary within a `MultiSheetDiagnostics`.
#[derive(Debug, Clone, Default)]
pub struct SheetSummary {
    pub sheet_index: usize,
    pub placed_count: usize,
    /// Sum of (rotated_w * rotated_h) for items placed on this sheet.
    pub placed_area: f64,
    /// Usable area of the sheet (polygon area; JG-19).
    pub sheet_usable_area: f64,
}

// ---------------------------------------------------------------------------
// MultiSheetDiagnostics
// ---------------------------------------------------------------------------

/// Diagnostics collected by a single `MultiSheetManager::run` call.
#[derive(Debug, Clone)]
pub struct MultiSheetDiagnostics {
    /// Total sheet slots available (from `expand_sheets`).
    pub sheet_count_available: usize,
    /// Used sheet slots after all passes: `max(sheet_index) + 1`, or 0 if nothing placed.
    pub sheet_count_used: usize,
    /// Total instances placed.
    pub total_placed: usize,
    /// Total instances left unplaced.
    pub total_unplaced: usize,
    /// Per-sheet summaries for used slots (reflects post-elimination state).
    pub per_sheet: Vec<SheetSummary>,
    /// Diagnostics from the initial construction pass.
    pub construction_diag: ConstructionDiagnostics,
    /// Diagnostics from the repair pass.
    pub repair_diag: RepairDiagnostics,
    /// Diagnostics from the sheet elimination pass (JG-13).
    pub elim_diag: SheetEliminationDiagnostics,
}

impl MultiSheetDiagnostics {
    pub fn summary(&self) -> String {
        format!(
            "sheets_avail={} sheets_used={} placed={} unplaced={} elim={}",
            self.sheet_count_available,
            self.sheet_count_used,
            self.total_placed,
            self.total_unplaced,
            self.elim_diag.summary(),
        )
    }
}

// ---------------------------------------------------------------------------
// MultiSheetManager
// ---------------------------------------------------------------------------

/// Coordinates Phase 1 construction + repair across multiple sheet slots.
///
/// Determinism: ordering is determined entirely by `instances` order (stable
/// after `sort_instances_for_placement` in the initializer) and
/// `generate_candidates` (deterministic sort). No random decisions here.
///
/// Invariant maintained: `total_placed + total_unplaced == instances.len()`.
pub struct MultiSheetManager<'a> {
    parts: &'a [Part],
    sheets: &'a [SheetShape],
    rotation_context: RotationResolveContext,
}

impl<'a> MultiSheetManager<'a> {
    pub fn new(parts: &'a [Part], sheets: &'a [SheetShape]) -> Self {
        Self::new_with_rotation_context(parts, sheets, RotationResolveContext::legacy_default())
    }

    pub fn new_with_rotation_context(
        parts: &'a [Part],
        sheets: &'a [SheetShape],
        rotation_context: RotationResolveContext,
    ) -> Self {
        Self {
            parts,
            sheets,
            rotation_context,
        }
    }

    /// Run construction then repair; return `(placements, unplaced, diagnostics)`.
    ///
    /// The output satisfies:
    /// - `placed.len() + unplaced.len() == instances.len()`
    /// - all `placement.sheet_index` are in `[0, sheets.len())`
    /// - `diagnostics.sheet_count_used == compute_sheet_count_used(&placements)`
    pub fn run(
        &self,
        instances: &[Instance],
        policy: &mut StoppingPolicy,
    ) -> (Vec<Placement>, Vec<Unplaced>, MultiSheetDiagnostics) {
        // Phase 1: initial construction across all available sheet slots.
        let (init_p, init_u, construction_diag) = build_initial_layout_with_rotation_context(
            instances,
            self.parts,
            self.sheets,
            &self.rotation_context,
        );

        // Phase 2: repair pass — tries to fix violations and reinsert unplaced items.
        let (rep_placements, rep_unplaced, repair_diag) = run_repair_with_rotation_context(
            init_p,
            init_u,
            self.parts,
            self.sheets,
            policy,
            &self.rotation_context,
        );

        // Phase 3: sheet elimination pass — tries to reduce sheet_count_used by one.
        let engine = SheetEliminationEngine::new_with_rotation_context(
            self.parts,
            self.sheets,
            self.rotation_context.clone(),
        );
        let (placements, unplaced, elim_diag) =
            engine.run(rep_placements, rep_unplaced, policy);

        // Build per-sheet summaries from the final post-elimination layout.
        let sheet_count_used = compute_sheet_count_used(&placements);
        let mut per_sheet: Vec<SheetSummary> = (0..sheet_count_used)
            .map(|i| SheetSummary {
                sheet_index: i,
                placed_count: 0,
                placed_area: 0.0,
                sheet_usable_area: if i < self.sheets.len() { self.sheets[i].area } else { 0.0 },
            })
            .collect();

        for p in &placements {
            let area = self
                .parts
                .iter()
                .find(|pt| pt.id == p.part_id)
                .and_then(|pt| bbox_from_placement(p, pt.width, pt.height))
                .map(|bb| (bb.x2 - bb.x1) * (bb.y2 - bb.y1))
                .unwrap_or(0.0);
            if p.sheet_index < per_sheet.len() {
                per_sheet[p.sheet_index].placed_count += 1;
                per_sheet[p.sheet_index].placed_area += area;
            }
        }

        let diag = MultiSheetDiagnostics {
            sheet_count_available: self.sheets.len(),
            sheet_count_used,
            total_placed: placements.len(),
            total_unplaced: unplaced.len(),
            per_sheet,
            construction_diag,
            repair_diag,
            elim_diag,
        };

        (placements, unplaced, diag)
    }
}

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::io::Placement;
    use crate::item::{expand_instances, Part};
    use crate::sheet::{expand_sheets, Stock};
    use super::super::stopping::StoppingPolicy;

    fn make_part(id: &str, w: f64, h: f64, qty: i64) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: qty,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: None,
            prepared_outer_points: None,
            rotation_policy: None,
        }
    }

    fn make_stock(id: &str, w: f64, h: f64, qty: i64) -> Stock {
        Stock {
            id: id.to_string(),
            quantity: qty,
            width: Some(w),
            height: Some(h),
            outer_points: None,
            holes_points: None,
            cost_per_use: None,
        }
    }

    fn p(instance_id: &str, sheet_index: usize) -> Placement {
        Placement {
            instance_id: instance_id.to_string(),
            part_id: "P".to_string(),
            sheet_index,
            x: 0.0,
            y: 0.0,
            rotation_deg: 0.0,
        }
    }

    // --- compute_sheet_count_used ---

    #[test]
    fn test_sheet_count_used_empty() {
        assert_eq!(compute_sheet_count_used(&[]), 0);
    }

    #[test]
    fn test_sheet_count_used_only_sheet0() {
        let pl = vec![p("A__0001", 0), p("A__0002", 0)];
        assert_eq!(compute_sheet_count_used(&pl), 1);
    }

    #[test]
    fn test_sheet_count_used_sheets_0_and_1() {
        let pl = vec![p("A__0001", 0), p("A__0002", 1)];
        assert_eq!(compute_sheet_count_used(&pl), 2);
    }

    #[test]
    fn test_sheet_count_used_only_sheet1_returns_2() {
        // max+1 contract: highest index=1 → used=2
        let pl = vec![p("A__0001", 1)];
        assert_eq!(compute_sheet_count_used(&pl), 2);
    }

    // --- MultiSheetManager integration ---

    #[test]
    fn test_single_sheet_all_placed() {
        let parts = vec![make_part("A", 30.0, 30.0, 2)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let mut policy = StoppingPolicy::new(64, 10.0);
        let manager = MultiSheetManager::new(&parts, &sheets);
        let (placed, unplaced, diag) = manager.run(&instances, &mut policy);
        assert_eq!(placed.len() + unplaced.len(), 2, "invariant");
        assert_eq!(placed.len(), 2, "both placed on single sheet");
        assert_eq!(diag.sheet_count_used, 1);
        assert_eq!(diag.sheet_count_available, 1);
    }

    #[test]
    fn test_multi_sheet_items_distributed() {
        // 100×100 sheet cannot fit two 80×80 items.
        // With 2 sheets → 1 placed per sheet.
        let parts = vec![make_part("A", 80.0, 80.0, 4)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 2)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let mut policy = StoppingPolicy::new(64, 10.0);
        let manager = MultiSheetManager::new(&parts, &sheets);
        let (placed, unplaced, diag) = manager.run(&instances, &mut policy);
        assert_eq!(placed.len() + unplaced.len(), 4, "invariant");
        assert_eq!(placed.len(), 2, "one per sheet");
        assert_eq!(unplaced.len(), 2, "two overflow");
        assert_eq!(diag.sheet_count_used, 2);
        assert_eq!(diag.per_sheet.len(), 2);
        assert_eq!(diag.per_sheet[0].placed_count, 1);
        assert_eq!(diag.per_sheet[1].placed_count, 1);
    }

    #[test]
    fn test_placed_plus_unplaced_equals_total() {
        let parts = vec![make_part("A", 60.0, 60.0, 5)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 2)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let mut policy = StoppingPolicy::new(64, 10.0);
        let manager = MultiSheetManager::new(&parts, &sheets);
        let (placed, unplaced, _diag) = manager.run(&instances, &mut policy);
        assert_eq!(placed.len() + unplaced.len(), 5, "invariant must hold");
    }

    #[test]
    fn test_sheet_index_within_bounds() {
        let parts = vec![make_part("A", 40.0, 40.0, 6)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 2)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let mut policy = StoppingPolicy::new(64, 10.0);
        let manager = MultiSheetManager::new(&parts, &sheets);
        let (placed, _unplaced, _diag) = manager.run(&instances, &mut policy);
        for p in &placed {
            assert!(
                p.sheet_index < sheets.len(),
                "sheet_index {} out of bounds (sheets.len={})",
                p.sheet_index,
                sheets.len()
            );
        }
    }

    #[test]
    fn test_deterministic_two_runs() {
        let parts = vec![
            make_part("A", 40.0, 40.0, 3),
            make_part("B", 60.0, 30.0, 2),
        ];
        let stocks = vec![make_stock("S", 150.0, 100.0, 2)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");

        let run = || {
            let mut policy = StoppingPolicy::new(64, 10.0);
            let manager = MultiSheetManager::new(&parts, &sheets);
            manager.run(&instances, &mut policy)
        };

        let (p1, u1, _) = run();
        let (p2, u2, _) = run();

        assert_eq!(p1.len(), p2.len(), "placed count deterministic");
        assert_eq!(u1.len(), u2.len(), "unplaced count deterministic");

        for (a, b) in p1.iter().zip(p2.iter()) {
            assert_eq!(a.instance_id, b.instance_id);
            assert_eq!(a.sheet_index, b.sheet_index);
            assert_eq!(a.x.to_bits(), b.x.to_bits());
            assert_eq!(a.y.to_bits(), b.y.to_bits());
            assert_eq!(a.rotation_deg, b.rotation_deg);
        }
    }

    #[test]
    fn test_per_sheet_summary_areas_positive() {
        let parts = vec![make_part("A", 50.0, 50.0, 4)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 2)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let mut policy = StoppingPolicy::new(64, 10.0);
        let manager = MultiSheetManager::new(&parts, &sheets);
        let (placed, _unplaced, diag) = manager.run(&instances, &mut policy);
        if !placed.is_empty() {
            for s in &diag.per_sheet {
                if s.placed_count > 0 {
                    assert!(s.placed_area > 0.0, "placed area must be positive");
                }
            }
        }
    }
}
