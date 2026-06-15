//! SGH-Q47 — Shape Profile Priority Layer integration tests.
//!
//! Exercises the profile decision-diagnostics + profile-aware ordering end-to-end through the
//! public `vrs_solver::adapter::solve` boundary on the `sparrow_cde_multisheet` (BPP) path.
//! Small synthetic fixtures (< 30 s). Asserts:
//!   - `shape_profiles` is emitted on the BPP path, one record per unique part type;
//!   - `priority_rank` is contiguous and deterministic;
//!   - a large concave low-fill anchor outranks (lower rank than) a tiny filler;
//!   - the profile layer does not change collision semantics (status ok, no collisions).

use serde_json::{json, Value};
use vrs_solver::adapter::solve;
use vrs_solver::io::{OptimizerDiagnosticsOutput, SolverInput, SolverOutput};

fn rect_part(id: &str, qty: i64, w: f64, h: f64) -> Value {
    json!({
        "id": id,
        "quantity": qty,
        "width": w,
        "height": h,
        "allowed_rotations_deg": [0, 90, 180, 270],
        "outer_points": [[0.0, 0.0], [w, 0.0], [w, h], [0.0, h]]
    })
}

/// Large concave "L" (bbox 1000×1000, fill ~0.36) → large_anchor + concave_like.
fn l_anchor_part(id: &str, qty: i64) -> Value {
    json!({
        "id": id,
        "quantity": qty,
        "width": 1000.0,
        "height": 1000.0,
        "allowed_rotations_deg": [0, 90, 180, 270],
        "outer_points": [
            [0.0, 0.0], [1000.0, 0.0], [1000.0, 200.0],
            [200.0, 200.0], [200.0, 1000.0], [0.0, 1000.0]
        ]
    })
}

fn ms_input(parts: Vec<Value>, stocks: Vec<Value>, seed: i64, time_limit_s: i64) -> Value {
    json!({
        "contract_version": "v1",
        "project_name": "sgh_q47_test",
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
    let input: SolverInput = serde_json::from_value(v.clone()).expect("parse SolverInput");
    solve(input).expect("solve")
}

fn od(out: &SolverOutput) -> &OptimizerDiagnosticsOutput {
    out.optimizer_diagnostics
        .as_ref()
        .expect("optimizer_diagnostics must be present for sparrow_cde_multisheet")
}

#[test]
fn shape_profiles_emitted_for_bpp_path() {
    let parts = vec![
        l_anchor_part("L", 2),
        rect_part("tiny", 8, 30.0, 30.0),
    ];
    let stocks = vec![json!({"id": "S", "quantity": 2, "width": 3000.0, "height": 1500.0})];
    let out = parse_and_solve(&ms_input(parts, stocks, 42, 30));

    assert_eq!(out.status, "ok", "all parts must place: {}", out.status);
    let d = od(&out);
    let profiles = d
        .shape_profiles
        .as_ref()
        .expect("shape_profiles must be present on the BPP path");

    // one record per unique part type
    assert_eq!(profiles.len(), 2, "one record per part type");
    let ids: Vec<&str> = profiles.iter().map(|p| p.part_id.as_str()).collect();
    assert!(ids.contains(&"L") && ids.contains(&"tiny"));

    // priority_rank contiguous 0..n and deterministic (sorted ascending == 0,1)
    let mut ranks: Vec<usize> = profiles.iter().map(|p| p.priority_rank).collect();
    ranks.sort_unstable();
    assert_eq!(ranks, vec![0, 1], "priority_rank must be contiguous");

    // instance_count == declared, all placed
    for p in profiles {
        assert_eq!(p.instance_count, p.declared_quantity, "{} instance_count", p.part_id);
        assert_eq!(p.placed_count, p.instance_count, "{} all placed", p.part_id);
    }
}

#[test]
fn anchor_outranks_tiny_filler_end_to_end() {
    let parts = vec![
        rect_part("tiny", 8, 30.0, 30.0),
        l_anchor_part("L", 2),
    ];
    let stocks = vec![json!({"id": "S", "quantity": 2, "width": 3000.0, "height": 1500.0})];
    let out = parse_and_solve(&ms_input(parts, stocks, 7, 30));
    let d = od(&out);
    let profiles = d.shape_profiles.as_ref().expect("shape_profiles present");

    let l = profiles.iter().find(|p| p.part_id == "L").expect("L profile");
    let tiny = profiles.iter().find(|p| p.part_id == "tiny").expect("tiny profile");

    assert!(
        l.priority_rank < tiny.priority_rank,
        "anchor L (rank {}) must be ordered before tiny filler (rank {})",
        l.priority_rank,
        tiny.priority_rank
    );
    assert!(
        l.priority_score > tiny.priority_score,
        "anchor L score {} must exceed tiny score {}",
        l.priority_score,
        tiny.priority_score
    );
    assert!(
        l.classes.iter().any(|c| c == "large_anchor"),
        "L must be classed large_anchor, got {:?}",
        l.classes
    );
    assert!(
        tiny.classes.iter().any(|c| c == "tiny_filler"),
        "tiny must be classed tiny_filler, got {:?}",
        tiny.classes
    );
}

#[test]
fn profile_layer_preserves_collision_feasibility() {
    // The profile layer only reorders; the CDE remains the collision truth. The on-path must
    // still produce a collision-free, fully-placed layout (no-collision-semantics-change).
    let parts = vec![l_anchor_part("L", 2), rect_part("tiny", 10, 40.0, 40.0)];
    let stocks = vec![json!({"id": "S", "quantity": 2, "width": 3000.0, "height": 1500.0})];
    let out = parse_and_solve(&ms_input(parts, stocks, 99, 30));

    assert_eq!(out.status, "ok");
    assert_eq!(out.unplaced.len(), 0, "no unplaced");
    let d = od(&out);
    assert_eq!(d.sparrow_ms_final_pairs, Some(0), "no collisions");
    assert_eq!(d.sparrow_ms_boundary_violations, Some(0), "no boundary violations");
}
