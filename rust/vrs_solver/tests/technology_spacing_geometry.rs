//! SGH-Q36 — Spacing-aware solver geometry tests.
//!
//! Proves: half-spacing outward offset (exact for rects, true offset for polygons),
//! spacing-expanded touching ⇒ original spacing apart, spacing is NOT a sheet margin,
//! margin and spacing are independent, kerf is not folded into the offset, output stays
//! original, and the Q35 final validator remains active.

use serde_json::{json, Value};
use vrs_solver::adapter::solve;
use vrs_solver::geometry::Point;
use vrs_solver::io::{Placement, SolverInput, SolverOutput};
use vrs_solver::item::Part;
use vrs_solver::technology::spacing::{
    count_part_spacing_violations, find_part_spacing_violations,
};
use vrs_solver::technology::spacing_geometry::{
    build_spacing_expanded_outer_polygon, SpacingOffsetConfig,
};

// ── helpers ───────────────────────────────────────────────────────────────────

fn rect_pts(w: f64, h: f64) -> Vec<Point> {
    vec![
        Point { x: 0.0, y: 0.0 },
        Point { x: w, y: 0.0 },
        Point { x: w, y: h },
        Point { x: 0.0, y: h },
    ]
}

fn bbox(pts: &[Point]) -> (f64, f64, f64, f64) {
    let mut minx = f64::INFINITY;
    let mut miny = f64::INFINITY;
    let mut maxx = f64::NEG_INFINITY;
    let mut maxy = f64::NEG_INFINITY;
    for p in pts {
        minx = minx.min(p.x);
        miny = miny.min(p.y);
        maxx = maxx.max(p.x);
        maxy = maxy.max(p.y);
    }
    (minx, miny, maxx, maxy)
}

fn rect_part(id: &str, w: f64, h: f64) -> Part {
    serde_json::from_value(json!({
        "id": id, "width": w, "height": h, "quantity": 1,
        "allowed_rotations_deg": [0],
        "outer_points": [[0.0,0.0],[w,0.0],[w,h],[0.0,h]]
    }))
    .expect("parse rect part")
}

fn pl(instance_id: &str, part_id: &str, x: f64, y: f64) -> Placement {
    Placement {
        instance_id: instance_id.to_string(),
        part_id: part_id.to_string(),
        sheet_index: 0,
        x,
        y,
        rotation_deg: 0.0,
    }
}

fn ms_input(
    parts: Vec<Value>,
    w: f64,
    h: f64,
    margin: f64,
    spacing: f64,
    kerf: f64,
) -> SolverInput {
    serde_json::from_value(json!({
        "contract_version": "v1",
        "project_name": "q36_test",
        "seed": 42,
        "time_limit_s": 20,
        "optimizer_pipeline": "sparrow_cde_multisheet",
        "collision_backend": "cde",
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "margin_mm": margin,
        "spacing_mm": spacing,
        "kerf_mm": kerf,
        "stocks": [{"id": "S1", "quantity": 1, "width": w, "height": h}],
        "parts": parts,
    }))
    .expect("parse SolverInput")
}

fn rect_part_json(id: &str, qty: i64, w: f64, h: f64) -> Value {
    json!({
        "id": id, "quantity": qty, "width": w, "height": h,
        "allowed_rotations_deg": [0],
        "outer_points": [[0,0],[w,0],[w,h],[0,h]]
    })
}

fn od(out: &SolverOutput) -> &vrs_solver::io::OptimizerDiagnosticsOutput {
    out.optimizer_diagnostics
        .as_ref()
        .expect("optimizer_diagnostics present")
}

// ── Test 1: rectangle half-spacing offset exact ───────────────────────────────

#[test]
fn rectangle_half_spacing_offset_exact() {
    // 20×10 rectangle, spacing 4 ⇒ half 2 ⇒ extent x=-2..22, y=-2..12.
    let out = build_spacing_expanded_outer_polygon(&rect_pts(20.0, 10.0), 2.0).expect("offset");
    let (minx, miny, maxx, maxy) = bbox(&out);
    assert!((minx + 2.0).abs() < 1e-6, "minx={minx}");
    assert!((miny + 2.0).abs() < 1e-6, "miny={miny}");
    assert!((maxx - 22.0).abs() < 1e-6, "maxx={maxx}");
    assert!((maxy - 12.0).abs() < 1e-6, "maxy={maxy}");
}

// ── Test 2: spacing_mm == 0 uses original geometry ────────────────────────────

#[test]
fn zero_spacing_uses_original_geometry() {
    let cfg = SpacingOffsetConfig::from_spacing_mm(0.0);
    assert!(!cfg.is_active());
    let orig = rect_pts(20.0, 10.0);
    let out = build_spacing_expanded_outer_polygon(&orig, 0.0).expect("offset");
    assert_eq!(out.len(), orig.len());
    for (a, b) in out.iter().zip(orig.iter()) {
        assert!((a.x - b.x).abs() < 1e-12 && (a.y - b.y).abs() < 1e-12);
    }
}

// ── Test 3: expanded touching means original spacing ──────────────────────────

#[test]
fn expanded_touching_means_original_spacing() {
    // A original at x=0, B original at x=30, spacing 10 ⇒ half 5.
    // A expanded x=-5..25, B expanded x=25..55 → expanded contours touch at x=25.
    // The ORIGINAL contours are exactly 10 apart ⇒ Q35 validator: no violation.
    let a = build_spacing_expanded_outer_polygon(&rect_pts(20.0, 20.0), 5.0).expect("a");
    let (_, _, a_maxx, _) = bbox(&a);
    // B's expanded min-x when B original is at 30: 30 - 5 = 25.
    assert!(
        (a_maxx - 25.0).abs() < 1e-6,
        "A expanded maxx should be 25, got {a_maxx}"
    );

    let parts = vec![rect_part("P", 20.0, 20.0)];
    let placements = vec![pl("A", "P", 0.0, 0.0), pl("B", "P", 30.0, 0.0)];
    assert_eq!(
        count_part_spacing_violations(&placements, &parts, 10.0),
        0,
        "original distance is exactly spacing ⇒ no violation"
    );
}

// ── Test 4: expanded overlap means spacing violation ──────────────────────────

#[test]
fn expanded_overlap_means_spacing_violation() {
    // A at x=0, B at x=29.9, spacing 10 ⇒ original gap 9.9 < 10 ⇒ expanded overlap.
    let parts = vec![rect_part("P", 20.0, 20.0)];
    let placements = vec![pl("A", "P", 0.0, 0.0), pl("B", "P", 29.9, 0.0)];
    let v = find_part_spacing_violations(&placements, &parts, 10.0);
    assert_eq!(v.len(), 1, "original gap < spacing ⇒ violation");
}

// ── Test 5: spacing must not become sheet margin ──────────────────────────────

#[test]
fn spacing_must_not_become_sheet_margin() {
    // Single 20×20 part, sheet 100×100, margin 0, spacing 10.
    // The part may sit at the sheet edge (original geometry); the spacing-expanded
    // contour extending outside the sheet must NOT create a boundary violation.
    let input = ms_input(
        vec![rect_part_json("P1", 1, 20.0, 20.0)],
        100.0,
        100.0,
        0.0,
        10.0,
        0.0,
    );
    let out = solve(input).expect("solve");
    assert_eq!(out.status, "ok", "single part must place ok");
    let d = od(&out);
    assert_eq!(d.technology_spacing_geometry_applied, Some(true));
    assert_eq!(
        d.sparrow_ms_boundary_violations,
        Some(0),
        "spacing must not cause boundary violation"
    );
    assert_eq!(
        d.technology_spacing_boundary_uses_original_geometry,
        Some(true)
    );
    // Part can be placed touching the sheet edge (within EPS): proves no half-spacing inset.
    let p = &out.placements[0];
    assert!(
        p.x <= 1.0 && p.y <= 1.0,
        "part should sit near the sheet edge, got x={} y={}",
        p.x,
        p.y
    );
}

// ── Test 6: margin and spacing are independent ────────────────────────────────

#[test]
fn margin_and_spacing_are_independent() {
    // sheet 100×100, margin 10, spacing 6 (offset 3), one 20×20 part.
    let input = ms_input(
        vec![rect_part_json("P1", 1, 20.0, 20.0)],
        100.0,
        100.0,
        10.0,
        6.0,
        0.0,
    );
    let out = solve(input).expect("solve");
    let d = od(&out);
    assert_eq!(
        d.technology_effective_sheet_margin_mm,
        Some(10.0),
        "margin stays 10"
    );
    assert_eq!(
        d.technology_spacing_offset_mm,
        Some(3.0),
        "spacing offset is 6/2=3, not added to margin"
    );
    assert_eq!(d.technology_margin_violation_count, Some(0));
    // Boundary uses margin 10 on original geometry: part must be inside [10, 90].
    if out.status == "ok" {
        let p = &out.placements[0];
        assert!(
            p.x >= 10.0 - 1e-6 && p.y >= 10.0 - 1e-6,
            "margin-inset placement, got x={} y={}",
            p.x,
            p.y
        );
    }
}

// ── Test 7: non-rect polygon offset is not bbox ───────────────────────────────

#[test]
fn non_rect_polygon_offset_is_not_bbox() {
    let tri = vec![
        Point { x: 0.0, y: 0.0 },
        Point { x: 20.0, y: 0.0 },
        Point { x: 0.0, y: 20.0 },
    ];
    let out = build_spacing_expanded_outer_polygon(&tri, 2.0).expect("offset");
    // A bbox-expand would yield 4 corners; a true polygon offset keeps 3 vertices.
    assert_eq!(
        out.len(),
        3,
        "triangle offset must remain a triangle (not a bbox rect): {out:?}"
    );
}

// ── Test 8: output geometry remains original ──────────────────────────────────

#[test]
fn output_geometry_remains_original() {
    let input = ms_input(
        vec![rect_part_json("P1", 2, 20.0, 20.0)],
        200.0,
        100.0,
        0.0,
        10.0,
        0.0,
    );
    let out = solve(input).expect("solve");
    let d = od(&out);
    assert_eq!(
        d.technology_spacing_output_uses_original_geometry,
        Some(true)
    );
    // The output records original part placements (x/y/rotation only); spacing-expanded
    // geometry is never emitted. Two placed parts must be >= spacing apart (original).
    if out.status == "ok" {
        let parts = vec![rect_part("P1", 20.0, 20.0)];
        assert_eq!(
            count_part_spacing_violations(&out.placements, &parts, 10.0),
            0,
            "spacing-aware solver output respects original spacing"
        );
    }
}

// ── Test 9: kerf independence ─────────────────────────────────────────────────

#[test]
fn kerf_independence() {
    // spacing 5, kerf 2 ⇒ offset 2.5 (NOT 3.5, NOT spacing+kerf).
    let cfg = SpacingOffsetConfig::from_spacing_mm(5.0);
    assert_eq!(cfg.half_spacing_mm, 2.5);

    let input = ms_input(
        vec![rect_part_json("P1", 1, 20.0, 20.0)],
        100.0,
        100.0,
        0.0,
        5.0,
        2.0,
    );
    let out = solve(input).expect("solve");
    let d = od(&out);
    assert_eq!(
        d.technology_spacing_offset_mm,
        Some(2.5),
        "offset must be spacing/2, kerf excluded"
    );
    assert_eq!(
        d.technology_kerf_mm,
        Some(2.0),
        "kerf stays a separate diagnostic value"
    );
}

// ── Test 10: Q35 final validator remains active ───────────────────────────────

#[test]
fn q35_final_validator_remains_active() {
    // The Q35 validator must still flag a too-close original layout regardless of Q36.
    let parts = vec![rect_part("P", 20.0, 20.0)];
    let touching = vec![pl("A", "P", 0.0, 0.0), pl("B", "P", 20.0, 0.0)]; // distance 0
    assert_eq!(
        count_part_spacing_violations(&touching, &parts, 5.0),
        1,
        "Q35 PART_SPACING_VIOLATION still triggers on touching originals at positive spacing"
    );
}
