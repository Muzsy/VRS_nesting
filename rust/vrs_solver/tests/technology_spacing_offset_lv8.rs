//! SGH-Q38 — robust spacing offset on real concave/high-vertex LV8 polygons.
//!
//! Loads the real LV8 parts from the committed canonical input
//! `artifacts/benchmarks/sgh_q32/inputs/case_01_2x1500x3000.json` and proves the Q38
//! robust straight-skeleton offset succeeds where the Q36 miter offset failed
//! (`Lv8_07919/07920/07921` at spacing 2/5/10), never self-intersects, and never falls
//! back to a raw/bbox contour.

use std::path::PathBuf;

use serde_json::Value;
use vrs_solver::adapter::solve;
use vrs_solver::geometry::Point;
use vrs_solver::io::SolverInput;
use vrs_solver::technology::spacing_geometry::{
    build_spacing_expanded_outer_polygon, validate_spacing_offset_outer_contour,
};

// ── helpers ──────────────────────────────────────────────────────────────────

fn canonical_input() -> Value {
    let p = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../artifacts/benchmarks/sgh_q32/inputs/case_01_2x1500x3000.json");
    serde_json::from_str(&std::fs::read_to_string(&p).expect("read canonical LV8 input")).unwrap()
}

fn part_polygon(part_id_contains: &str) -> Vec<Point> {
    let doc = canonical_input();
    for p in doc["parts"].as_array().unwrap() {
        let id = p["id"].as_str().unwrap_or("");
        if id.contains(part_id_contains) {
            let raw = p.get("prepared_outer_points").and_then(|v| v.as_array())
                .or_else(|| p.get("outer_points").and_then(|v| v.as_array()))
                .expect("part has outer_points");
            return raw
                .iter()
                .map(|pr| {
                    let a = pr.as_array().unwrap();
                    Point { x: a[0].as_f64().unwrap(), y: a[1].as_f64().unwrap() }
                })
                .collect();
        }
    }
    panic!("part containing {part_id_contains} not found");
}

fn poly_area(pts: &[Point]) -> f64 {
    let n = pts.len();
    let mut s = 0.0;
    for i in 0..n {
        let a = pts[i];
        let b = pts[(i + 1) % n];
        s += a.x * b.y - b.x * a.y;
    }
    (s / 2.0).abs()
}

fn bbox(pts: &[Point]) -> (f64, f64, f64, f64) {
    let mut mnx = f64::INFINITY;
    let mut mny = f64::INFINITY;
    let mut mxx = f64::NEG_INFINITY;
    let mut mxy = f64::NEG_INFINITY;
    for p in pts {
        mnx = mnx.min(p.x);
        mny = mny.min(p.y);
        mxx = mxx.max(p.x);
        mxy = mxy.max(p.y);
    }
    (mnx, mny, mxx, mxy)
}

fn rect(w: f64, h: f64) -> Vec<Point> {
    vec![
        Point { x: 0.0, y: 0.0 },
        Point { x: w, y: 0.0 },
        Point { x: w, y: h },
        Point { x: 0.0, y: h },
    ]
}

// ── Test 1: rectangle exact/simple sanity ──────────────────────────────────────

#[test]
fn rectangle_offset_valid() {
    let r = rect(20.0, 10.0);
    let out = build_spacing_expanded_outer_polygon(&r, 2.0).expect("offset");
    validate_spacing_offset_outer_contour(&r, &out).expect("valid");
    let (mnx, mny, mxx, mxy) = bbox(&out);
    // Outward by 2 on every side.
    assert!(mnx <= -2.0 + 1e-6 && mny <= -2.0 + 1e-6, "min {mnx},{mny}");
    assert!(mxx >= 22.0 - 1e-6 && mxy >= 12.0 - 1e-6, "max {mxx},{mxy}");
    assert!(poly_area(&out) > poly_area(&r));
}

// ── Test 2: simple concave (L-shape) at 2/5/10 ─────────────────────────────────

#[test]
fn concave_l_shape_offsets() {
    let l = vec![
        Point { x: 0.0, y: 0.0 },
        Point { x: 100.0, y: 0.0 },
        Point { x: 100.0, y: 50.0 },
        Point { x: 50.0, y: 50.0 },
        Point { x: 50.0, y: 100.0 },
        Point { x: 0.0, y: 100.0 },
    ];
    for spacing in [2.0, 5.0, 10.0] {
        let out = build_spacing_expanded_outer_polygon(&l, spacing / 2.0)
            .unwrap_or_else(|e| panic!("L-shape spacing {spacing}: {e}"));
        validate_spacing_offset_outer_contour(&l, &out)
            .unwrap_or_else(|e| panic!("L-shape validate spacing {spacing}: {e}"));
        assert!(poly_area(&out) > poly_area(&l));
    }
}

// ── Test 3: high-vertex LV8 failed parts at spacing 2/5/10 ─────────────────────

#[test]
fn lv8_failed_parts_offset_ok() {
    for pid in ["07919", "07920", "07921"] {
        let poly = part_polygon(pid);
        for spacing in [2.0, 5.0, 10.0] {
            let out = build_spacing_expanded_outer_polygon(&poly, spacing / 2.0)
                .unwrap_or_else(|e| panic!("LV8 {pid} spacing {spacing}: {e}"));
            validate_spacing_offset_outer_contour(&poly, &out)
                .unwrap_or_else(|e| panic!("LV8 {pid} validate spacing {spacing}: {e}"));
        }
    }
}

// ── Test 4: large spacing stress (20/40) — Ok or explicit, never self-intersecting ─

#[test]
fn lv8_large_spacing_stress() {
    for pid in ["07919", "07920", "07921"] {
        let poly = part_polygon(pid);
        for spacing in [20.0, 40.0] {
            match build_spacing_expanded_outer_polygon(&poly, spacing / 2.0) {
                Ok(out) => {
                    // If accepted, it MUST be valid (never a self-intersecting output).
                    validate_spacing_offset_outer_contour(&poly, &out)
                        .unwrap_or_else(|e| panic!("LV8 {pid} spacing {spacing} accepted but invalid: {e}"));
                }
                Err(_) => { /* explicit supported failure is acceptable at large spacing */ }
            }
        }
    }
}

// ── Test 5: no bbox fallback (triangle offset is not a bbox rectangle) ─────────

#[test]
fn triangle_offset_is_not_bbox() {
    let tri = vec![
        Point { x: 0.0, y: 0.0 },
        Point { x: 20.0, y: 0.0 },
        Point { x: 0.0, y: 20.0 },
    ];
    let out = build_spacing_expanded_outer_polygon(&tri, 2.0).expect("offset");
    validate_spacing_offset_outer_contour(&tri, &out).expect("valid");
    // A bbox-expand would be a rectangle of area ~ (24*24)=576. A true offset of a right
    // triangle (area 200) stays well below the bbox-rectangle area.
    let a = poly_area(&out);
    assert!(a > 200.0 && a < 560.0, "offset area {a} looks bbox-expanded");
}

// ── Test 6: kerf independence (offset config is spacing/2, never +kerf) ─────────

#[test]
fn kerf_independent_offset() {
    use vrs_solver::technology::spacing_geometry::SpacingOffsetConfig;
    let cfg = SpacingOffsetConfig::from_spacing_mm(10.0);
    assert_eq!(cfg.half_spacing_mm, 5.0); // not 6.5 (=+kerf 3 → 13/2), not 13
}

// ── Test 7: solver-path regression (spacing 10, kerf 3) ────────────────────────

fn ms_input(margin: f64, spacing: f64, kerf: f64, qty: i64, w: f64, h: f64, sheet_w: f64, sheet_h: f64) -> SolverInput {
    let v = serde_json::json!({
        "contract_version": "v1",
        "project_name": "q38_solver_regression",
        "seed": 42,
        "time_limit_s": 10,
        "optimizer_pipeline": "sparrow_cde_multisheet",
        "collision_backend": "cde",
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "margin_mm": margin,
        "spacing_mm": spacing,
        "kerf_mm": kerf,
        "stocks": [{"id": "S1", "quantity": 1, "width": sheet_w, "height": sheet_h}],
        "parts": [{
            "id": "P1", "quantity": qty, "width": w, "height": h,
            "allowed_rotations_deg": [0],
            "outer_points": [[0.0,0.0],[w,0.0],[w,h],[0.0,h]]
        }],
    });
    serde_json::from_value(v).expect("parse")
}

#[test]
fn solver_spacing10_kerf3_offset_is_half_spacing() {
    let input = ms_input(0.0, 10.0, 3.0, 1, 20.0, 20.0, 200.0, 200.0);
    let out = solve(input).expect("solve");
    let d = out.optimizer_diagnostics.as_ref().expect("diag");
    assert_eq!(d.technology_spacing_offset_mm, Some(5.0)); // spacing/2, NOT (spacing+kerf)/2
    assert_eq!(d.technology_kerf_mm, Some(3.0));            // kerf separate
    assert_eq!(d.technology_spacing_offset_failure_count, Some(0));
}

// ── Test 8: Q36 no sheet-margin regression (spacing != margin) ─────────────────

#[test]
fn spacing_is_not_sheet_margin() {
    // Single part near the sheet edge, spacing 10, margin 0 → must place ok, boundary 0.
    let input = ms_input(0.0, 10.0, 0.0, 1, 20.0, 20.0, 100.0, 100.0);
    let out = solve(input).expect("solve");
    assert_eq!(out.status, "ok", "single part with spacing>0 must still place (spacing is not a margin)");
    let d = out.optimizer_diagnostics.as_ref().expect("diag");
    assert_eq!(d.sparrow_ms_boundary_violations, Some(0));
    assert_eq!(d.technology_spacing_boundary_uses_original_geometry, Some(true));
}
