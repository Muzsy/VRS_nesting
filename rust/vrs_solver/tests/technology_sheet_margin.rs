//! SGH-Q34 — Sheet margin enforcement tests for sparrow_cde_multisheet.
//!
//! Q34 applies TechnologyClearancePolicy::effective_sheet_margin_mm() as a sheet
//! boundary inset for RECTANGULAR stocks only. The solver core runs on the shrunk
//! sheet; placement coordinates stay in original sheet coordinates.
//!
//! Tests:
//!   1. Rect sheet shrink: 100×100 margin 10 → inset 10..90, 80×80, area 6400.
//!   2. Margin too large: 100×100 margin 50 → MARGIN_EXCEEDS_SHEET_DIMENSIONS.
//!   3. Irregular stock + nonzero margin → UNSUPPORTED_MARGIN_FOR_IRREGULAR_STOCK_Q34.
//!   4. Solver placement respects margin (full run, all placements inside inset rect).
//!   5. Part fits without margin but not with margin → not ok, 0 placed, 1 unplaced.
//!   6. Backwards compat: margin absent/0 → runs, technology_sheet_margin_applied == false.

use serde_json::{json, Value};
use vrs_solver::adapter::solve;
use vrs_solver::io::{Placement, SolverInput, SolverOutput};
use vrs_solver::item::Part;
use vrs_solver::rotation_policy::{dims_for_rotation_f64, rotated_bbox_min_offset_f64};
use vrs_solver::sheet::{
    apply_rectangular_sheet_margin, count_sheet_margin_violations, expand_sheets,
    find_sheet_margin_violations, Stock,
};

// ── Helpers ──────────────────────────────────────────────────────────────────

fn rect_stock(id: &str, qty: i64, w: f64, h: f64) -> Stock {
    serde_json::from_value(json!({
        "id": id, "quantity": qty, "width": w, "height": h
    }))
    .expect("parse rect stock")
}

fn irregular_stock(id: &str) -> Stock {
    // L-shape outer_points → has_irregular_outer = true
    serde_json::from_value(json!({
        "id": id,
        "quantity": 1,
        "outer_points": [[0,0],[100,0],[100,50],[50,50],[50,100],[0,100]]
    }))
    .expect("parse irregular stock")
}

fn ms_input(margin: Option<f64>, parts: Vec<Value>, stock_w: f64, stock_h: f64) -> SolverInput {
    let mut v = json!({
        "contract_version": "v1",
        "project_name": "q34_test",
        "seed": 42,
        "time_limit_s": 20,
        "optimizer_pipeline": "sparrow_cde_multisheet",
        "collision_backend": "cde",
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "stocks": [{"id": "S1", "quantity": 1, "width": stock_w, "height": stock_h}],
        "parts": parts,
    });
    if let Some(m) = margin {
        v["margin_mm"] = json!(m);
    }
    serde_json::from_value(v).expect("parse SolverInput")
}

fn rect_part(id: &str, qty: i64, w: f64, h: f64) -> Value {
    json!({
        "id": id, "quantity": qty, "width": w, "height": h,
        "allowed_rotations_deg": [0, 90],
        "outer_points": [[0,0],[w,0],[w,h],[0,h]]
    })
}

fn od(out: &SolverOutput) -> &vrs_solver::io::OptimizerDiagnosticsOutput {
    out.optimizer_diagnostics.as_ref().expect("optimizer_diagnostics present")
}

// ── Test 1: rect sheet shrink ─────────────────────────────────────────────────

#[test]
fn rect_sheet_shrink_100x100_margin_10() {
    let sheets = expand_sheets(&[rect_stock("S", 1, 100.0, 100.0)]).expect("expand");
    let shrunk = apply_rectangular_sheet_margin(&sheets, 10.0).expect("apply margin");
    assert_eq!(shrunk.len(), 1);
    let s = &shrunk[0];
    assert!((s.min_x - 10.0).abs() < 1e-9, "min_x={}", s.min_x);
    assert!((s.min_y - 10.0).abs() < 1e-9, "min_y={}", s.min_y);
    assert!((s.max_x - 90.0).abs() < 1e-9, "max_x={}", s.max_x);
    assert!((s.max_y - 90.0).abs() < 1e-9, "max_y={}", s.max_y);
    assert!((s.width - 80.0).abs() < 1e-9, "width={}", s.width);
    assert!((s.height - 80.0).abs() < 1e-9, "height={}", s.height);
    assert!((s.area - 6400.0).abs() < 1e-6, "area={}", s.area);
    assert!(!s.has_irregular_outer);
}

#[test]
fn margin_zero_is_noop_clone() {
    let sheets = expand_sheets(&[rect_stock("S", 1, 100.0, 80.0)]).expect("expand");
    let shrunk = apply_rectangular_sheet_margin(&sheets, 0.0).expect("apply margin 0");
    assert_eq!(shrunk.len(), 1);
    assert!((shrunk[0].width - 100.0).abs() < 1e-9);
    assert!((shrunk[0].height - 80.0).abs() < 1e-9);
    assert!((shrunk[0].area - 8000.0).abs() < 1e-6);
}

#[test]
fn negative_margin_errors() {
    let sheets = expand_sheets(&[rect_stock("S", 1, 100.0, 100.0)]).expect("expand");
    let res = apply_rectangular_sheet_margin(&sheets, -1.0);
    assert!(res.is_err(), "negative margin must error");
}

// ── Test 2: margin too large ───────────────────────────────────────────────────

#[test]
fn margin_too_large_errors() {
    let sheets = expand_sheets(&[rect_stock("S", 1, 100.0, 100.0)]).expect("expand");
    let res = apply_rectangular_sheet_margin(&sheets, 50.0);
    assert!(res.is_err(), "margin 50 on 100×100 must error");
    let msg = res.unwrap_err();
    assert!(
        msg.contains("MARGIN_EXCEEDS_SHEET_DIMENSIONS"),
        "expected MARGIN_EXCEEDS_SHEET_DIMENSIONS, got: {msg}"
    );
}

// ── Test 3: irregular stock + nonzero margin ──────────────────────────────────

#[test]
fn irregular_stock_with_margin_errors() {
    let sheets = expand_sheets(&[irregular_stock("L")]).expect("expand");
    assert!(sheets[0].has_irregular_outer);
    let res = apply_rectangular_sheet_margin(&sheets, 5.0);
    assert!(res.is_err(), "irregular stock with margin must error");
    let msg = res.unwrap_err();
    assert!(
        msg.contains("UNSUPPORTED_MARGIN_FOR_IRREGULAR_STOCK_Q34"),
        "expected UNSUPPORTED_MARGIN_FOR_IRREGULAR_STOCK_Q34, got: {msg}"
    );
}

#[test]
fn irregular_stock_with_zero_margin_ok() {
    let sheets = expand_sheets(&[irregular_stock("L")]).expect("expand");
    // Zero margin is a no-op clone even for irregular stock.
    let res = apply_rectangular_sheet_margin(&sheets, 0.0);
    assert!(res.is_ok(), "irregular stock with zero margin should be a no-op clone");
}

// ── Test 4: solver placement respects margin ──────────────────────────────────

#[test]
fn solver_placement_respects_margin() {
    let input = ms_input(Some(10.0), vec![rect_part("P1", 2, 20.0, 20.0)], 100.0, 100.0);
    let out = solve(input).expect("solve");
    assert_eq!(out.status, "ok", "expected ok status");

    let d = od(&out);
    assert_eq!(d.technology_sheet_margin_applied, Some(true));
    assert_eq!(d.technology_margin_violation_count, Some(0));
    assert_eq!(d.sparrow_ms_final_pairs, Some(0));
    assert_eq!(d.sparrow_ms_boundary_violations, Some(0));

    // Every placement's rotated bbox must be within the inset rectangle [10, 90].
    for pl in &out.placements {
        // Both parts are 20×20; recompute the rotated bbox in world coords.
        let (min_off_x, min_off_y) = rotated_bbox_min_offset_f64(20.0, 20.0, pl.rotation_deg);
        let (bw, bh) = dims_for_rotation_f64(20.0, 20.0, pl.rotation_deg);
        let wmin_x = pl.x + min_off_x;
        let wmin_y = pl.y + min_off_y;
        let wmax_x = wmin_x + bw;
        let wmax_y = wmin_y + bh;
        const EPS: f64 = 1e-6;
        assert!(wmin_x >= 10.0 - EPS, "placement min_x {} < 10", wmin_x);
        assert!(wmin_y >= 10.0 - EPS, "placement min_y {} < 10", wmin_y);
        assert!(wmax_x <= 90.0 + EPS, "placement max_x {} > 90", wmax_x);
        assert!(wmax_y <= 90.0 + EPS, "placement max_y {} > 90", wmax_y);
    }
}

// ── Test 5: part fits without margin but not with margin ──────────────────────

#[test]
fn part_too_big_with_margin_not_ok() {
    // 95×95 fits in 100×100 but not in the 80×80 margin-inset sheet.
    let input = ms_input(Some(10.0), vec![rect_part("P_BIG", 1, 95.0, 95.0)], 100.0, 100.0);
    let out = solve(input).expect("solve");
    assert_ne!(out.status, "ok", "must not report ok for unplaceable part");
    assert_eq!(out.metrics.placed_count, 0, "no placements expected");
    assert_eq!(out.metrics.unplaced_count, 1, "exactly one unplaced");
    assert!(!out.unplaced.is_empty(), "unplaced reason present");
    // Margin diagnostics still present.
    let d = od(&out);
    assert_eq!(d.technology_sheet_margin_applied, Some(true));
    assert_eq!(d.technology_margin_violation_count, Some(0));
}

// ── Test 6: backwards compatibility (no margin) ───────────────────────────────

#[test]
fn no_margin_backwards_compatible() {
    let input = ms_input(None, vec![rect_part("P1", 2, 20.0, 20.0)], 100.0, 100.0);
    let out = solve(input).expect("solve");
    assert_eq!(out.status, "ok");
    let d = od(&out);
    assert_eq!(d.technology_sheet_margin_applied, Some(false));
    // No margin applied → no usable/physical area override, violation count 0.
    assert_eq!(d.technology_margin_violation_count, Some(0));
    assert_eq!(d.technology_margin_usable_sheet_area, None);
}

#[test]
fn explicit_zero_margin_backwards_compatible() {
    let input = ms_input(Some(0.0), vec![rect_part("P1", 2, 20.0, 20.0)], 100.0, 100.0);
    let out = solve(input).expect("solve");
    assert_eq!(out.status, "ok");
    let d = od(&out);
    assert_eq!(d.technology_sheet_margin_applied, Some(false));
}

// ── SGH-Q34-R1: polygon-based final margin validator ──────────────────────────
//
// These tests prove the validator uses the actual transformed part POLYGON, not the
// declared width×height bounding box. Test 1 in particular fails with a bbox validator.

/// Build a Part with an explicit triangular outer_points polygon but a large declared
/// width/height bbox. The polygon is small; the bbox is large.
fn triangle_part_big_bbox(id: &str) -> Part {
    serde_json::from_value(json!({
        "id": id,
        "width": 100.0,
        "height": 100.0,
        "quantity": 1,
        "allowed_rotations_deg": [0],
        "outer_points": [[0.0, 0.0], [20.0, 0.0], [0.0, 20.0]]
    }))
    .expect("parse triangle part")
}

fn rect_part_no_polygon(id: &str, w: f64, h: f64) -> Part {
    // No outer_points → rectangle fallback path.
    serde_json::from_value(json!({
        "id": id,
        "width": w,
        "height": h,
        "quantity": 1,
        "allowed_rotations_deg": [0]
    }))
    .expect("parse rect part")
}

fn placement(instance_id: &str, part_id: &str, x: f64, y: f64, rot: f64) -> Placement {
    Placement {
        instance_id: instance_id.to_string(),
        part_id: part_id.to_string(),
        sheet_index: 0,
        x,
        y,
        rotation_deg: rot,
    }
}

/// Test 1 (the key regression): polygon inside, declared bbox outside.
/// Triangle [(0,0),(20,0),(0,20)] at (65,65) → world extent x/y 65..85, inside [10,90].
/// The declared 100×100 bbox would extend to 165 (outside) — a bbox validator would
/// wrongly flag this. The polygon validator must report NO violation.
#[test]
fn polygon_inside_declared_bbox_outside_no_violation() {
    let sheets = expand_sheets(&[rect_stock("S", 1, 100.0, 100.0)]).expect("expand");
    let parts = vec![triangle_part_big_bbox("T")];
    let placements = vec![placement("T#0", "T", 65.0, 65.0, 0.0)];

    let v = find_sheet_margin_violations(&placements, &parts, &sheets, 10.0);
    assert!(v.is_empty(), "polygon is inside inset; expected no violation, got {v:?}");
    assert_eq!(count_sheet_margin_violations(&placements, &parts, &sheets, 10.0), 0);
}

/// Test 2: polygon actually violates margin. Triangle at (75,75) → world max 95 > 90.
#[test]
fn polygon_actually_violates_margin() {
    let sheets = expand_sheets(&[rect_stock("S", 1, 100.0, 100.0)]).expect("expand");
    let parts = vec![triangle_part_big_bbox("T")];
    let placements = vec![placement("T#0", "T", 75.0, 75.0, 0.0)];

    let v = find_sheet_margin_violations(&placements, &parts, &sheets, 10.0);
    assert_eq!(v, vec!["T#0".to_string()], "polygon exceeds inset; expected violation");
    assert_eq!(count_sheet_margin_violations(&placements, &parts, &sheets, 10.0), 1);
}

/// Test 3: rotated polygon containment. A triangle rotated 45° — placed so the rotated
/// vertices stay inside vs. cross the inset boundary.
#[test]
fn rotated_polygon_containment() {
    let sheets = expand_sheets(&[rect_stock("S", 1, 100.0, 100.0)]).expect("expand");
    let parts = vec![triangle_part_big_bbox("T")];

    // Triangle [(0,0),(20,0),(0,20)] rotated 45° about origin:
    //   (0,0)->(0,0); (20,0)->(14.14,14.14); (0,20)->(-14.14,14.14)
    // Anchored at (50,50): vertices (50,50),(64.14,64.14),(35.86,64.14) — all in [10,90].
    let inside = vec![placement("T#0", "T", 50.0, 50.0, 45.0)];
    assert!(
        find_sheet_margin_violations(&inside, &parts, &sheets, 10.0).is_empty(),
        "rotated polygon fully inside inset must not violate"
    );

    // Anchored near the left edge so the (-14.14,14.14) vertex crosses inset_min_x=10:
    //   anchor (15,50) → vertex x = 15 - 14.14 = 0.86 < 10 → violation.
    let outside = vec![placement("T#0", "T", 15.0, 50.0, 45.0)];
    assert_eq!(
        find_sheet_margin_violations(&outside, &parts, &sheets, 10.0),
        vec!["T#0".to_string()],
        "rotated polygon vertex outside inset must violate"
    );
}

/// Test 4: rectangle fallback (no outer_points) still works.
#[test]
fn rectangle_fallback_still_works() {
    let sheets = expand_sheets(&[rect_stock("S", 1, 100.0, 100.0)]).expect("expand");
    let parts = vec![rect_part_no_polygon("R", 20.0, 20.0)];

    // Inside: anchor (10,10) → world 10..30, inside [10,90].
    let inside = vec![placement("R#0", "R", 10.0, 10.0, 0.0)];
    assert!(
        find_sheet_margin_violations(&inside, &parts, &sheets, 10.0).is_empty(),
        "rect fallback inside must not violate"
    );

    // Outside: anchor (75,75) → world 75..95, 95 > 90 → violation.
    let outside = vec![placement("R#0", "R", 75.0, 75.0, 0.0)];
    assert_eq!(
        count_sheet_margin_violations(&outside, &parts, &sheets, 10.0),
        1,
        "rect fallback outside must violate"
    );
}

/// Margin 0 → validator is a no-op (returns empty).
#[test]
fn zero_margin_no_violations() {
    let sheets = expand_sheets(&[rect_stock("S", 1, 100.0, 100.0)]).expect("expand");
    let parts = vec![triangle_part_big_bbox("T")];
    let placements = vec![placement("T#0", "T", 75.0, 75.0, 0.0)];
    assert!(find_sheet_margin_violations(&placements, &parts, &sheets, 0.0).is_empty());
}
