//! SGH-Q52 — Density-biased admission separation integration test.
//!
//! Exercises the opt-in `VRS_ADMISSION_DENSITY_BIAS` knob through the public `adapter::solve`
//! boundary on the `sparrow_cde_multisheet` (BPP) path, on top of the Q51 `VRS_SHEET_BUILDER`.
//! The density-biased separator is feasibility-gated and only replaces the overlap-minimising
//! co-movable step — so enabling it never regresses the result (it falls back exactly like Q51).
//!
//! Env vars are process-global, so both phases live in ONE sequential test (no intra-binary race):
//!   (1) builder ON, bias OFF (default)  → baseline used-sheet count.
//!   (2) builder ON, bias ON (w=2.0)     → still valid, fully placed, used_sheets ≤ baseline.

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
        "contract_version": "v1", "project_name": "sgh_q52_test", "seed": seed, "time_limit_s": t,
        "stocks": stocks, "solver_profile": "jagua_optimizer_phase1_outer_only", "margin_mm": 0.0,
        "optimizer_pipeline": "sparrow_cde_multisheet", "collision_backend": "cde", "parts": parts,
    })
}

fn solve_json(v: &Value) -> SolverOutput {
    let input: SolverInput = serde_json::from_value(v.clone()).expect("parse SolverInput");
    solve(input).expect("solve")
}

fn od(out: &SolverOutput) -> &OptimizerDiagnosticsOutput {
    out.optimizer_diagnostics
        .as_ref()
        .expect("optimizer_diagnostics present")
}

fn used_sheets(out: &SolverOutput) -> usize {
    out.placements
        .iter()
        .map(|p| p.sheet_index)
        .collect::<std::collections::BTreeSet<_>>()
        .len()
}

#[test]
fn density_bias_is_valid_and_no_regression_vs_builder_only() {
    let parts = vec![l_part("L", 4), rect_part("f", 12, 120.0, 120.0)];
    let stocks = vec![json!({"id": "S", "quantity": 3, "width": 3000.0, "height": 1500.0})];
    let input = ms_input(parts, stocks, 42, 40);

    // ── (1) baseline: builder ON, bias OFF (default) ────────────────────────────────────────────
    std::env::set_var("VRS_SHEET_BUILDER", "1");
    std::env::remove_var("VRS_ADMISSION_DENSITY_BIAS");
    let off = solve_json(&input);
    assert_eq!(
        off.status, "ok",
        "builder-only baseline must be valid: {}",
        off.status
    );
    assert_eq!(off.unplaced.len(), 0, "baseline fully placed");
    assert_eq!(
        od(&off).sparrow_ms_final_pairs,
        Some(0),
        "baseline collision-free"
    );
    let off_sheets = used_sheets(&off);

    // ── (2) builder ON, density bias ON (w=2.0) ─────────────────────────────────────────────────
    std::env::set_var("VRS_ADMISSION_DENSITY_BIAS", "2.0");
    let on = solve_json(&input);
    std::env::remove_var("VRS_ADMISSION_DENSITY_BIAS");

    assert_eq!(
        on.status, "ok",
        "density-biased admission must stay valid: {}",
        on.status
    );
    assert_eq!(
        on.unplaced.len(),
        0,
        "density-biased admission fully placed (fallback guarantees it)"
    );
    let d = od(&on);
    assert_eq!(
        d.sparrow_ms_final_pairs,
        Some(0),
        "no collisions with bias on"
    );
    assert_eq!(
        d.sparrow_ms_boundary_violations,
        Some(0),
        "no boundary violations with bias on"
    );
    assert!(
        used_sheets(&on) <= off_sheets,
        "density bias must not regress used-sheet count: on={} off={}",
        used_sheets(&on),
        off_sheets,
    );
}
