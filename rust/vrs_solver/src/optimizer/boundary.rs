//! VRS-owned boundary validation policy layer (JG-17).
//!
//! This module is the single auditable point for all placement boundary decisions.
//! All construction, repair, and score paths delegate through here.
//!
//! ## Boundary-touch policy (JG-17)
//!
//! **Rectangular stocks** (`has_irregular_outer = false`):
//! - Boundary check is bbox-only with EPS = 1e-9 tolerance.
//! - A rect edge exactly touching the sheet boundary is **accepted** (within EPS).
//!
//! **Irregular stocks** (`has_irregular_outer = true`):
//! - All 4 rect corners must satisfy `_outer_poly.collides_with(corner)` — i.e.,
//!   each corner must be inside the outer polygon.
//! - No rect edge may cross an outer polygon edge (`Edge.collides_with(Edge)`).
//! - Corner exactly on the outer polygon boundary: jagua `SPolygon.collides_with`
//!   semantics are not fully specified for on-boundary points. Safe-side policy:
//!   points nominally inside the polygon are accepted; boundary-exact touch may
//!   be accepted or rejected depending on floating-point precision. This is
//!   consistent with Phase 1 scope (no sub-mm boundary required).
//!
//! ## Proxy vs exact boundary
//!
//! - Proxy (Rust): `rect_within_boundary()` — fast, used during construction, repair,
//!   and scoring. For rectangular stocks this is exact; for irregular stocks it is
//!   a correct containment check using jagua SPolygon primitives.
//! - Exact (Python): `vrs_nesting.nesting.instances.validate_multi_sheet_output()` —
//!   uses Shapely `sheet_poly.covers(placement_poly)` for full polygon containment.
//!   This is the authoritative validation gate; any layout accepted by the solver
//!   must pass this check too. The Python validator also applies `margin_mm` via
//!   `buffer(-margin_mm)` if specified, which the Rust runtime does not (JG-16).
//!
//! ## Container holes
//!
//! Container holes (`Stock.holes_points`) remain unsupported in Phase 1 and are
//! rejected at the adapter level before construction begins (`UNSUPPORTED_STOCK_HOLES_PHASE1`).

use crate::geometry::Rect;
use crate::sheet::{rect_inside_sheet_shape, SheetShape};

// QUALITY_RISK: BboxBoundaryProxy
// Exact for: rectangular stocks (delegates to axis-aligned rect_inside_sheet_shape, which is exact)
// Proxy for: irregular outer shapes (outer polygon checked via SPolygon but no shape simplification or surrogate fast-fail)
// Parity: PROXY (F04, SGH-Q00)
/// Returns `true` if `rect` is entirely within the given sheet shape.
///
/// This is the canonical proxy boundary check for all optimizer paths.
/// See module-level documentation for the boundary-touch policy.
pub fn rect_within_boundary(rect: Rect, sheet: &SheetShape) -> bool {
    rect_inside_sheet_shape(rect, sheet)
}

/// Returns `true` if `sheet_index` is a valid index into `sheets`.
pub fn sheet_index_valid(sheet_index: usize, sheets: &[SheetShape]) -> bool {
    sheet_index < sheets.len()
}

/// Combined check: `sheet_index` is valid AND `rect` is within the sheet boundary.
///
/// Used by validation paths that need a single boolean result for a placement.
pub fn is_placement_boundary_valid(rect: Rect, sheet_index: usize, sheets: &[SheetShape]) -> bool {
    sheet_index_valid(sheet_index, sheets) && rect_within_boundary(rect, &sheets[sheet_index])
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::geometry::PointInput;
    use crate::sheet::{expand_sheets, Stock};

    fn rect_stock(id: &str, w: f64, h: f64) -> Stock {
        Stock {
            id: id.to_string(),
            quantity: 1,
            width: Some(w),
            height: Some(h),
            outer_points: None,
            holes_points: None,
            cost_per_use: None,
        }
    }

    fn l_shape_stock() -> Stock {
        Stock {
            id: "L".to_string(),
            quantity: 1,
            width: None,
            height: None,
            outer_points: Some(vec![
                PointInput::Pair([0.0, 0.0]),
                PointInput::Pair([100.0, 0.0]),
                PointInput::Pair([100.0, 50.0]),
                PointInput::Pair([50.0, 50.0]),
                PointInput::Pair([50.0, 100.0]),
                PointInput::Pair([0.0, 100.0]),
            ]),
            holes_points: None,
            cost_per_use: None,
        }
    }

    fn r(x1: f64, y1: f64, x2: f64, y2: f64) -> Rect {
        Rect { x1, y1, x2, y2 }
    }

    // -------------------------------------------------------------------------
    // rect_within_boundary — rectangular stock
    // -------------------------------------------------------------------------

    #[test]
    fn boundary_rect_stock_inside_pass() {
        let sheets = expand_sheets(&[rect_stock("R", 100.0, 80.0)]).unwrap();
        assert!(rect_within_boundary(r(10.0, 10.0, 50.0, 40.0), &sheets[0]));
    }

    #[test]
    fn boundary_rect_stock_outside_fail() {
        let sheets = expand_sheets(&[rect_stock("R", 100.0, 80.0)]).unwrap();
        assert!(!rect_within_boundary(r(90.0, 70.0, 110.0, 90.0), &sheets[0]));
    }

    // -------------------------------------------------------------------------
    // rect_within_boundary — L-shape stock (irregular)
    // -------------------------------------------------------------------------

    #[test]
    fn boundary_l_shape_inside_pass() {
        // Item 20×20 at (10,10): fully inside L bottom-left region
        let sheets = expand_sheets(&[l_shape_stock()]).unwrap();
        assert!(rect_within_boundary(r(10.0, 10.0, 30.0, 30.0), &sheets[0]),
            "item inside L-shape must pass");
    }

    #[test]
    fn boundary_l_shape_notch_fail() {
        // Item 20×20 at (60,60): in the top-right notch — bbox passes, outer poly fails
        let sheets = expand_sheets(&[l_shape_stock()]).unwrap();
        assert!(!rect_within_boundary(r(60.0, 60.0, 80.0, 80.0), &sheets[0]),
            "notch placement must fail boundary check");
    }

    #[test]
    fn boundary_l_shape_origin_pass() {
        // Item at (0,0): corner on polygon vertex — interior is inside L, must be accepted.
        let sheets = expand_sheets(&[l_shape_stock()]).unwrap();
        assert!(rect_within_boundary(r(0.0, 0.0, 20.0, 15.0), &sheets[0]),
            "origin placement on polygon vertex must be accepted");
    }

    // -------------------------------------------------------------------------
    // sheet_index_valid
    // -------------------------------------------------------------------------

    #[test]
    fn sheet_index_valid_pass() {
        let sheets = expand_sheets(&[rect_stock("A", 100.0, 100.0), rect_stock("B", 100.0, 100.0)]).unwrap();
        assert!(sheet_index_valid(0, &sheets));
        assert!(sheet_index_valid(1, &sheets));
    }

    #[test]
    fn sheet_index_valid_out_of_bounds() {
        let sheets = expand_sheets(&[rect_stock("A", 100.0, 100.0)]).unwrap();
        assert!(!sheet_index_valid(1, &sheets));
        assert!(!sheet_index_valid(999, &sheets));
    }

    // -------------------------------------------------------------------------
    // is_placement_boundary_valid
    // -------------------------------------------------------------------------

    #[test]
    fn placement_boundary_valid_combined() {
        let sheets = expand_sheets(&[rect_stock("R", 100.0, 80.0)]).unwrap();
        assert!(is_placement_boundary_valid(r(10.0, 10.0, 50.0, 40.0), 0, &sheets));
        assert!(!is_placement_boundary_valid(r(10.0, 10.0, 50.0, 40.0), 1, &sheets));
        assert!(!is_placement_boundary_valid(r(90.0, 70.0, 110.0, 90.0), 0, &sheets));
    }
}
