//! SGH-Q51 — Critical-aware constructive sheet builder integration tests.
//!
//! Exercises the opt-in `VRS_SHEET_BUILDER` path through the public `adapter::solve` boundary on
//! the `sparrow_cde_multisheet` (BPP) path. The builder seed is used only when it is complete and
//! fully feasible, otherwise it falls back to the LBF seed — so enabling it never regresses the
//! result. All tests set the same env value (no intra-binary race); the OFF path is covered by the
//! existing multisheet/density suites.

use serde_json::{json, Value};
use vrs_solver::adapter::solve;
use vrs_solver::io::{OptimizerDiagnosticsOutput, SolverInput, SolverOutput};

fn l_part(id: &str, qty: i64) -> Value {
    json!({
        "id": id, "quantity": qty, "width": 1000.0, "height": 1000.0,
        "allowed_rotations_deg": [0, 90, 180, 270],
        "outer_points": [
            [0.0, 0.0], [1000.0, 0.0], [1000.0, 300.0],
            [300.0, 300.0], [300.0, 1000.0], [0.0, 1000.0]
        ]
    })
}

fn rect_part(id: &str, qty: i64, w: f64, h: f64) -> Value {
    json!({
        "id": id, "quantity": qty, "width": w, "height": h,
        "allowed_rotations_deg": [0, 90, 180, 270],
        "outer_points": [[0.0, 0.0], [w, 0.0], [w, h], [0.0, h]]
    })
}

fn ms_input(parts: Vec<Value>, stocks: Vec<Value>, seed: i64, t: i64) -> Value {
    json!({
        "contract_version": "v1", "project_name": "sgh_q51_test", "seed": seed, "time_limit_s": t,
        "stocks": stocks, "solver_profile": "jagua_optimizer_phase1_outer_only", "margin_mm": 0.0,
        "optimizer_pipeline": "sparrow_cde_multisheet", "collision_backend": "cde", "parts": parts,
    })
}

fn solve_json(v: &Value) -> SolverOutput {
    let input: SolverInput = serde_json::from_value(v.clone()).expect("parse SolverInput");
    solve(input).expect("solve")
}

fn od(out: &SolverOutput) -> &OptimizerDiagnosticsOutput {
    out.optimizer_diagnostics.as_ref().expect("optimizer_diagnostics present")
}

#[test]
fn sheet_builder_produces_valid_layout() {
    std::env::set_var("VRS_SHEET_BUILDER", "1");
    let parts = vec![l_part("L", 4), rect_part("f", 12, 120.0, 120.0)];
    let stocks = vec![json!({"id": "S", "quantity": 3, "width": 3000.0, "height": 1500.0})];
    let out = solve_json(&ms_input(parts, stocks, 42, 40));

    assert_eq!(out.status, "ok", "builder path must produce a valid layout: {}", out.status);
    assert_eq!(out.unplaced.len(), 0, "no unplaced (fallback guarantees completeness)");
    let d = od(&out);
    assert_eq!(d.sparrow_ms_final_pairs, Some(0), "no collisions");
    assert_eq!(d.sparrow_ms_boundary_violations, Some(0));
    let bpp = d.bpp_reduction.as_ref().expect("bpp diagnostics");
    assert!(bpp.bpp_sheet_builder_applied, "the builder must run when enabled");
}

#[test]
fn sheet_builder_no_regression_on_fillers() {
    // A filler-heavy fixture: the builder admits the (few) critical parts then fills; the result
    // must be valid and fully placed regardless of how the admission fares.
    std::env::set_var("VRS_SHEET_BUILDER", "1");
    let parts = vec![l_part("L", 2), rect_part("f", 20, 100.0, 100.0)];
    let stocks = vec![json!({"id": "S", "quantity": 3, "width": 3000.0, "height": 1500.0})];
    let out = solve_json(&ms_input(parts, stocks, 7, 40));

    assert_eq!(out.status, "ok");
    assert_eq!(out.unplaced.len(), 0);
    assert_eq!(od(&out).sparrow_ms_final_pairs, Some(0));
}
