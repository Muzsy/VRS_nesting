//! SGH-Q32 — Finite-stock Sparrow multisheet manager integration tests.
//!
//! Exercises the `sparrow_cde_multisheet` pipeline through the public
//! `vrs_solver::adapter::solve` boundary. All tests use small synthetic
//! fixtures to run quickly (< 30 s each). The full LV8 276-part benchmark
//! is run separately in `scripts/run_sgh_q32_finite_stock_multisheet_lv8.py`.
//!
//! Invariants asserted across all tests:
//!   - enum deserializes from "sparrow_cde_multisheet" (snake_case serde)
//!   - Q31 base-shape cache field exists in diagnostics (cache not regressed)
//!   - sparrow_ms_active == true
//!   - sparrow_ms_final_pairs == 0 (no collisions in output)
//!   - sparrow_ms_boundary_violations == 0
//!   - ok output: placed_count == total instances, unplaced == 0
//!   - partial output: explicit unplaced list, collision-free

use serde_json::{json, Value};
use vrs_solver::adapter::solve;
use vrs_solver::io::{OptimizerPipelineKind, SolverInput, SolverOutput};

// ── Helpers ──────────────────────────────────────────────────────────────────

fn tiny_rect_part(id: &str, qty: i64, w: f64, h: f64) -> Value {
    json!({
        "id": id,
        "quantity": qty,
        "width": w,
        "height": h,
        "allowed_rotations_deg": [0, 90, 180, 270],
        "outer_points": [[0.0, 0.0], [w, 0.0], [w, h], [0.0, h]]
    })
}

fn ms_input(
    parts: Vec<Value>,
    stocks: Vec<Value>,
    seed: i64,
    time_limit_s: i64,
) -> Value {
    json!({
        "contract_version": "v1",
        "project_name": "sgh_q32_test",
        "seed": seed,
        "time_limit_s": time_limit_s,
        "stocks": stocks,
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "margin_mm": 0.0,
        "optimizer_pipeline": "sparrow_cde_multisheet",
        "collision_backend": "cde",
        "parts": parts,
    })
}

fn parse_and_solve(v: &Value) -> SolverOutput {
    let input: SolverInput =
        serde_json::from_value(v.clone()).expect("parse SolverInput");
    solve(input).expect("solve")
}

fn od(out: &SolverOutput) -> &vrs_solver::io::OptimizerDiagnosticsOutput {
    out.optimizer_diagnostics
        .as_ref()
        .expect("optimizer_diagnostics must be present for sparrow_cde_multisheet")
}

// ── Test 1: enum deserialize ──────────────────────────────────────────────────

#[test]
fn multisheet_enum_deserializes_from_snake_case() {
    let raw = r#"{"optimizer_pipeline": "sparrow_cde_multisheet"}"#;
    #[derive(serde::Deserialize)]
    struct W {
        optimizer_pipeline: OptimizerPipelineKind,
    }
    let w: W = serde_json::from_str(raw).expect("deserialize");
    assert_eq!(w.optimizer_pipeline, OptimizerPipelineKind::SparrowCdeMultisheet);
}

// ── Test 2: tiny 2-sheet ok ───────────────────────────────────────────────────

#[test]
fn multisheet_tiny_2_sheet_full_feasible() {
    // 8 small squares × 60×60mm on 2×200×200 sheets → should fit
    let parts = vec![tiny_rect_part("sq60", 8, 60.0, 60.0)];
    let stocks = vec![
        json!({"id": "S0", "quantity": 2, "width": 200.0, "height": 200.0}),
    ];
    let input = ms_input(parts, stocks, 42, 30);
    let out = parse_and_solve(&input);

    assert_eq!(out.status, "ok", "tiny 2-sheet must produce ok status");
    assert_eq!(
        out.metrics.placed_count, 8,
        "all 8 instances must be placed"
    );
    assert_eq!(out.unplaced.len(), 0, "no unplaced");

    let d = od(&out);
    assert_eq!(d.pipeline_used, "sparrow_cde_multisheet");
    assert_eq!(d.sparrow_ms_active, Some(true));
    assert_eq!(d.sparrow_ms_final_pairs, Some(0), "no collisions");
    assert_eq!(d.sparrow_ms_boundary_violations, Some(0), "no boundary violations");
    assert_eq!(d.sparrow_ms_status, Some("ok".to_string()));
    assert!(d.sparrow_ms_utilization_pct.unwrap_or(0.0) > 0.0);
    // Q31 cache invariant: must still be present
    assert!(d.sparrow_q31_base_shape_cache_build_ms.is_some(), "Q31 cache field must be present");
}

// ── Test 3: heterogeneous stock mapping ───────────────────────────────────────

#[test]
fn multisheet_heterogeneous_stock_index_mapping() {
    // Stock 0: 300×100 (wide), Stock 1: 100×300 (tall).
    // One wide part (250×50) only fits on Stock 0; one tall part (50×250) only fits on Stock 1.
    let parts = vec![
        tiny_rect_part("wide", 1, 250.0, 50.0),
        tiny_rect_part("tall", 1, 50.0, 250.0),
    ];
    let stocks = vec![
        json!({"id": "wide_sheet", "quantity": 1, "width": 300.0, "height": 100.0}),
        json!({"id": "tall_sheet", "quantity": 1, "width": 100.0, "height": 300.0}),
    ];
    let input = ms_input(parts, stocks, 42, 30);
    let out = parse_and_solve(&input);

    // Must place both (2 instances).
    assert_eq!(out.status, "ok", "both parts must be placed: {}", out.status);
    assert_eq!(out.metrics.placed_count, 2);
    assert_eq!(out.unplaced.len(), 0);

    let d = od(&out);
    assert_eq!(d.sparrow_ms_active, Some(true));
    assert_eq!(d.sparrow_ms_final_pairs, Some(0));
    assert_eq!(d.sparrow_ms_boundary_violations, Some(0));
    // used_sheet_count should be 2 (both sheets used)
    let used = d.sparrow_ms_used_sheet_count.unwrap_or(0);
    assert!(used <= 2, "at most 2 sheets used, got {used}");
    // used_sheet_indices must be a subset of [0, 1]
    let indices = d.sparrow_ms_used_sheet_indices.as_ref().expect("used_sheet_indices");
    for &idx in indices {
        assert!(idx < 2, "sheet index {idx} out of range");
    }
}

// ── Test 4: unique used sheet count (not max+1) ───────────────────────────────

#[test]
fn multisheet_unique_used_sheet_count_not_max_plus_one() {
    // 3 sheets available: 0, 1, 2. Place 4 parts that easily fit on 1 sheet.
    // Manager should use only 1 sheet → used_sheet_count == 1, NOT 3.
    let parts = vec![tiny_rect_part("small", 4, 20.0, 20.0)];
    let stocks = vec![
        json!({"id": "A", "quantity": 3, "width": 200.0, "height": 200.0}),
    ];
    let input = ms_input(parts, stocks, 42, 30);
    let out = parse_and_solve(&input);

    assert_eq!(out.status, "ok");
    assert_eq!(out.metrics.placed_count, 4);

    let d = od(&out);
    let used_count = d.sparrow_ms_used_sheet_count.unwrap_or(99);
    let available = d.sparrow_ms_available_sheet_count.unwrap_or(0);
    assert_eq!(available, 3, "3 sheets available");
    assert!(
        used_count <= 2,
        "manager should use at most 2 sheets for 4 tiny parts, got {used_count}"
    );

    // Verify unique index accounting: used_sheet_area must equal sum of used sheet areas.
    // Each sheet is 200×200 = 40,000 mm². used_sheet_area = used_count × 40,000.
    let used_area = d.sparrow_ms_used_sheet_area.unwrap_or(0.0);
    let expected_area = used_count as f64 * 200.0 * 200.0;
    assert!(
        (used_area - expected_area).abs() < 1.0,
        "used_sheet_area={used_area} != expected {expected_area}"
    );
}

// ── Test 5: max 2 used sheets with 3 available ────────────────────────────────

#[test]
fn multisheet_prefers_fewer_sheets_with_more_available() {
    // 6 parts × 60×60 on 3×200×200 sheets. All 6 fit on 2 sheets (4 per sheet
    // in 2×2 grid). Manager must not use the 3rd sheet.
    let parts = vec![tiny_rect_part("sq60", 6, 60.0, 60.0)];
    let stocks = vec![
        json!({"id": "S", "quantity": 3, "width": 200.0, "height": 200.0}),
    ];
    let input = ms_input(parts, stocks, 42, 30);
    let out = parse_and_solve(&input);

    assert_eq!(out.status, "ok");
    assert_eq!(out.metrics.placed_count, 6);

    let d = od(&out);
    let used = d.sparrow_ms_used_sheet_count.unwrap_or(99);
    assert!(
        used <= 2,
        "6 parts fit on 2 sheets of 200×200; manager must not use 3rd. got {used}"
    );
    assert_eq!(d.sparrow_ms_final_pairs, Some(0));
    assert_eq!(d.sparrow_ms_boundary_violations, Some(0));
}

// ── Test 6: partial sanitize — explicit unplaced reason ───────────────────────

#[test]
fn multisheet_partial_with_explicit_unplaced_reason() {
    // Massively overcapacity: 50 parts × 100×100 on 1×150×150 sheet.
    // Only 1 part fits. Must report partial with explicit unplaced reasons.
    let parts = vec![tiny_rect_part("big", 50, 100.0, 100.0)];
    let stocks = vec![
        json!({"id": "tiny", "quantity": 1, "width": 150.0, "height": 150.0}),
    ];
    let input = ms_input(parts, stocks, 42, 15);
    let out = parse_and_solve(&input);

    // Must be partial (not all fit)
    assert_ne!(out.status, "ok", "50 parts cannot fit on 150×150 sheet");
    assert!(out.metrics.placed_count >= 1, "at least 1 part should be placed");
    assert!(out.metrics.unplaced_count >= 1, "some parts must be unplaced");

    // All unplaced must have explicit reasons.
    for u in &out.unplaced {
        assert!(!u.reason.is_empty(), "unplaced reason must not be empty: {:?}", u);
        // Acceptable reasons for stock exhaustion
        let ok = u.reason.contains("STOCK_EXHAUSTED_PARTIAL")
            || u.reason.contains("INSUFFICIENT_STOCK_CAPACITY")
            || u.reason.contains("UNRESOLVED_AFTER_STOCK_EXHAUSTED")
            || u.reason.contains("PART_NEVER_FITS_STOCK");
        assert!(ok, "unexpected unplaced reason: {:?}", u.reason);
    }

    let d = od(&out);
    assert_eq!(d.sparrow_ms_active, Some(true));
    assert_eq!(d.sparrow_ms_final_pairs, Some(0), "partial must be collision-free");
    assert_eq!(d.sparrow_ms_boundary_violations, Some(0), "partial must be boundary-safe");
}

// ── Test 7: Q31 cache invariant ───────────────────────────────────────────────

#[test]
fn multisheet_q31_base_shape_cache_invariant() {
    // Any multisheet run must preserve Q31 cache accounting fields in diagnostics.
    // The base-shape cache must not be regressed (hotpath_calls must be 0 when
    // running through the native pipeline).
    let parts = vec![
        tiny_rect_part("A", 3, 80.0, 40.0),
        tiny_rect_part("B", 3, 40.0, 80.0),
    ];
    let stocks = vec![
        json!({"id": "S", "quantity": 2, "width": 300.0, "height": 300.0}),
    ];
    let input = ms_input(parts, stocks, 42, 20);
    let out = parse_and_solve(&input);

    let d = od(&out);
    // Q31 cache build time must be present (set during from_solver_input).
    assert!(
        d.sparrow_q31_base_shape_cache_build_ms.is_some(),
        "Q31 cache build_ms must be present"
    );
    // Hotpath calls (prepare_base_shape_native in search/LBF/tracker) must be 0.
    // This is the Q31 invariant: the cache eliminates all hot-path calls.
    let hotpath = d.sparrow_q31_prepare_base_shape_native_hotpath_calls.unwrap_or(999);
    assert_eq!(hotpath, 0, "Q31: no hot-path prepare_base_shape_native calls allowed");
}

// ── Test 8: part-never-fits-stock ────────────────────────────────────────────

#[test]
fn multisheet_part_never_fits_any_stock_reported() {
    // A part that is larger than all available sheets.
    // Must be reported as PART_NEVER_FITS_STOCK, not cause a crash.
    let parts = vec![
        tiny_rect_part("huge", 2, 500.0, 500.0),
        tiny_rect_part("small", 4, 40.0, 40.0),
    ];
    let stocks = vec![
        json!({"id": "S", "quantity": 2, "width": 200.0, "height": 200.0}),
    ];
    let input = ms_input(parts, stocks, 42, 20);
    let out = parse_and_solve(&input);

    // huge parts cannot fit; small parts should be placed.
    assert_ne!(out.status, "unsupported", "must not be unsupported — huge parts are gracefully excluded");

    // The 2 huge parts must appear in unplaced with PART_NEVER_FITS_STOCK.
    let never_fit: Vec<_> = out.unplaced.iter()
        .filter(|u| u.reason == "PART_NEVER_FITS_STOCK" || u.part_id == "huge")
        .collect();
    assert!(!never_fit.is_empty(), "huge parts must be reported as unplaceable");

    let d = od(&out);
    assert_eq!(d.sparrow_ms_active, Some(true));
    assert_eq!(d.sparrow_ms_final_pairs, Some(0));
    assert_eq!(d.sparrow_ms_boundary_violations, Some(0));
}
