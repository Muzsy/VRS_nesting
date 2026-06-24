//! SGH-Q48 — Interlock-aware density compaction integration tests.
//!
//! Exercises the opt-in `VRS_BPP_DENSITY_COMPACT` pass through the public `adapter::solve`
//! boundary on the `sparrow_cde_multisheet` (BPP) path. All tests enable the pass (same env value
//! ⇒ no intra-binary race); the OFF path is covered by the existing multisheet/shape_profile
//! suites (which run with the var unset). Asserts:
//!   - the density pass runs and preserves collision feasibility (CDE stays the truth);
//!   - the pass generates interlock (bbox-overlapping, polygon-clear) candidates on concave parts.

use serde_json::{json, Value};
use vrs_solver::adapter::solve;
use vrs_solver::io::{OptimizerDiagnosticsOutput, SolverInput, SolverOutput};

fn l_part(id: &str, qty: i64) -> Value {
    // Large concave "L" (bbox 1000×1000): has a concavity for neighbours to nest into.
    json!({
        "id": id,
        "quantity": qty,
        "width": 1000.0,
        "height": 1000.0,
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
        "contract_version": "v1", "project_name": "sgh_q48_test", "seed": seed, "time_limit_s": t,
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

#[test]
fn density_compaction_runs_and_preserves_feasibility() {
    std::env::set_var("VRS_BPP_DENSITY_COMPACT", "1");
    let parts = vec![l_part("L", 4), rect_part("f", 12, 120.0, 120.0)];
    let stocks = vec![json!({"id": "S", "quantity": 2, "width": 3000.0, "height": 1500.0})];
    let out = solve_json(&ms_input(parts, stocks, 42, 40));

    assert_eq!(out.status, "ok", "must place all: {}", out.status);
    assert_eq!(out.unplaced.len(), 0);
    let d = od(&out);
    assert_eq!(
        d.sparrow_ms_final_pairs,
        Some(0),
        "density pass keeps it collision-free"
    );
    assert_eq!(d.sparrow_ms_boundary_violations, Some(0));
    let bpp = d.bpp_reduction.as_ref().expect("bpp diagnostics");
    assert!(
        bpp.bpp_density_compaction_applied,
        "density pass must run when enabled"
    );
}

#[test]
fn lns_sheet_drop_runs_and_preserves_feasibility() {
    // SGH-Q50: with the LNS sheet-drop enabled, the pass runs and the layout stays valid
    // (collision-free, fully placed) whether or not a sheet is actually dropped.
    std::env::set_var("VRS_BPP_DENSITY_COMPACT", "1");
    std::env::set_var("VRS_BPP_LNS", "1");
    let parts = vec![l_part("L", 3), rect_part("f", 9, 130.0, 130.0)];
    let stocks = vec![json!({"id": "S", "quantity": 3, "width": 3000.0, "height": 1500.0})];
    let out = solve_json(&ms_input(parts, stocks, 5, 40));
    std::env::remove_var("VRS_BPP_LNS");

    assert_eq!(
        out.status, "ok",
        "LNS must keep the layout valid: {}",
        out.status
    );
    assert_eq!(out.unplaced.len(), 0);
    let d = od(&out);
    assert_eq!(d.sparrow_ms_final_pairs, Some(0), "no collisions");
    assert_eq!(d.sparrow_ms_boundary_violations, Some(0));
    let bpp = d.bpp_reduction.as_ref().expect("bpp diagnostics");
    assert!(bpp.bpp_lns_applied, "LNS pass must run when enabled");
}

#[test]
fn density_multi_sweep_processes_all_parts() {
    // SGH-Q49: with a reserved budget + multi-sweep, the density pass should sweep over the parts
    // at least once (parts_processed ≥ placed count) and run ≥ 1 sweep.
    std::env::set_var("VRS_BPP_DENSITY_COMPACT", "1");
    let parts = vec![l_part("L", 3), rect_part("f", 9, 130.0, 130.0)];
    let stocks = vec![json!({"id": "S", "quantity": 2, "width": 3000.0, "height": 1500.0})];
    let out = solve_json(&ms_input(parts, stocks, 11, 40));
    assert_eq!(out.status, "ok");
    let placed = out.metrics.placed_count;
    let bpp = od(&out)
        .bpp_reduction
        .as_ref()
        .expect("bpp diagnostics")
        .clone();
    assert!(bpp.bpp_density_sweeps >= 1, "at least one density sweep");
    assert!(
        bpp.bpp_density_parts_processed >= placed,
        "density must process ≥ all {} placed parts (got {})",
        placed,
        bpp.bpp_density_parts_processed
    );
    // Time-split diagnostics are populated when the pass runs.
    assert!(bpp.bpp_density_time_ms >= 0.0 && bpp.bpp_reduction_time_ms > 0.0);
}

#[test]
fn density_compaction_generates_interlock_candidates() {
    std::env::set_var("VRS_BPP_DENSITY_COMPACT", "1");
    // Concave anchors packed together ⇒ contour sampling should propose bbox-overlapping,
    // polygon-clear (interlock) placements.
    let parts = vec![l_part("L", 4), rect_part("f", 8, 150.0, 150.0)];
    let stocks = vec![json!({"id": "S", "quantity": 2, "width": 3000.0, "height": 1500.0})];
    let out = solve_json(&ms_input(parts, stocks, 7, 40));

    assert_eq!(out.status, "ok");
    let bpp = od(&out)
        .bpp_reduction
        .as_ref()
        .expect("bpp diagnostics")
        .clone();
    assert!(bpp.bpp_density_compaction_applied);
    assert!(
        bpp.bpp_interlock_candidates_generated > 0,
        "density search must generate interlock candidates on concave parts (got {})",
        bpp.bpp_interlock_candidates_generated
    );
}
