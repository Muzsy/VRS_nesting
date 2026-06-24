//! SGH-Q33 — TechnologyClearancePolicy integration tests.
//!
//! Tests:
//!   1. Legacy margin_mm-only input: spacing_mm defaults to margin_mm, kerf_mm defaults to 0.
//!   2. Explicit margin_mm + spacing_mm + kerf_mm: all fields parsed correctly.
//!   3. Negative margin_mm / spacing_mm / kerf_mm: each returns an error.
//!   4. sparrow_cde_multisheet diagnostics contain technology_policy_active=true and correct values.
//!   5. Backwards compatibility: Q32-style inputs (no spacing_mm/kerf_mm) deserialize fine.

use serde_json::{json, Value};
use vrs_solver::adapter::solve;
use vrs_solver::io::SolverInput;
use vrs_solver::technology::TechnologyClearancePolicy;

// ── Helpers ──────────────────────────────────────────────────────────────────

fn make_input(
    margin_mm: Option<f64>,
    spacing_mm: Option<f64>,
    kerf_mm: Option<f64>,
) -> SolverInput {
    let mut v = json!({
        "contract_version": "v1",
        "project_name": "q33_test",
        "seed": 1,
        "time_limit_s": 5,
        "stocks": [{"id": "S1", "quantity": 1, "width": 300.0, "height": 200.0}],
        "parts": [{
            "id": "P1",
            "quantity": 1,
            "width": 50.0,
            "height": 30.0,
            "allowed_rotations_deg": [0],
            "outer_points": [[0,0],[50,0],[50,30],[0,30]]
        }],
        "optimizer_pipeline": "sparrow_cde_multisheet",
        "collision_backend": "cde",
        "solver_profile": "jagua_optimizer_phase1_outer_only"
    });
    if let Some(m) = margin_mm {
        v["margin_mm"] = json!(m);
    }
    if let Some(s) = spacing_mm {
        v["spacing_mm"] = json!(s);
    }
    if let Some(k) = kerf_mm {
        v["kerf_mm"] = json!(k);
    }
    serde_json::from_value(v).expect("parse SolverInput")
}

fn make_policy(
    margin_mm: Option<f64>,
    spacing_mm: Option<f64>,
    kerf_mm: Option<f64>,
) -> TechnologyClearancePolicy {
    let input = make_input(margin_mm, spacing_mm, kerf_mm);
    TechnologyClearancePolicy::from_solver_input(&input).expect("policy should succeed")
}

// ── Test 1: legacy margin_mm-only input ──────────────────────────────────────

#[test]
fn legacy_margin_only_defaults() {
    let policy = make_policy(Some(5.0), None, None);
    assert_eq!(policy.margin_mm, 5.0);
    // spacing defaults to margin_mm when absent
    assert_eq!(policy.spacing_mm, 5.0);
    // kerf defaults to 0.0 when absent
    assert_eq!(policy.kerf_mm, 0.0);
    assert_eq!(policy.effective_sheet_margin_mm(), 5.0);
    assert_eq!(policy.effective_part_spacing_mm(), 5.0);
    assert_eq!(policy.effective_kerf_mm(), 0.0);
}

#[test]
fn legacy_no_fields_gives_zero_defaults() {
    let policy = make_policy(None, None, None);
    assert_eq!(policy.margin_mm, 0.0);
    assert_eq!(policy.spacing_mm, 0.0);
    assert_eq!(policy.kerf_mm, 0.0);
}

// ── Test 2: explicit fields ───────────────────────────────────────────────────

#[test]
fn explicit_fields_parsed_correctly() {
    let policy = make_policy(Some(10.0), Some(2.0), Some(0.15));
    assert_eq!(policy.margin_mm, 10.0);
    assert_eq!(policy.spacing_mm, 2.0);
    assert_eq!(policy.kerf_mm, 0.15);
    assert_eq!(policy.effective_sheet_margin_mm(), 10.0);
    assert_eq!(policy.effective_part_spacing_mm(), 2.0);
    assert_eq!(policy.effective_kerf_mm(), 0.15);
}

#[test]
fn zero_values_are_valid() {
    let policy = make_policy(Some(0.0), Some(0.0), Some(0.0));
    assert_eq!(policy.margin_mm, 0.0);
    assert_eq!(policy.spacing_mm, 0.0);
    assert_eq!(policy.kerf_mm, 0.0);
    policy.validate().expect("zero values should be valid");
}

// ── Test 3: negative values return errors ─────────────────────────────────────

#[test]
fn negative_margin_mm_errors() {
    let input = make_input(Some(-1.0), None, None);
    let result = TechnologyClearancePolicy::from_solver_input(&input);
    assert!(result.is_err(), "negative margin_mm must return Err");
    let msg = result.unwrap_err();
    assert!(
        msg.contains("margin_mm"),
        "error should mention margin_mm, got: {}",
        msg
    );
}

#[test]
fn negative_spacing_mm_errors() {
    let input = make_input(Some(0.0), Some(-0.5), None);
    let result = TechnologyClearancePolicy::from_solver_input(&input);
    assert!(result.is_err(), "negative spacing_mm must return Err");
    let msg = result.unwrap_err();
    assert!(
        msg.contains("spacing_mm"),
        "error should mention spacing_mm, got: {}",
        msg
    );
}

#[test]
fn negative_kerf_mm_errors() {
    let input = make_input(Some(0.0), Some(0.0), Some(-0.01));
    let result = TechnologyClearancePolicy::from_solver_input(&input);
    assert!(result.is_err(), "negative kerf_mm must return Err");
    let msg = result.unwrap_err();
    assert!(
        msg.contains("kerf_mm"),
        "error should mention kerf_mm, got: {}",
        msg
    );
}

// ── Test 4: sparrow_cde_multisheet diagnostics contain technology_* fields ────

fn full_ms_input_v(margin_mm: f64, spacing_mm: f64, kerf_mm: f64) -> Value {
    json!({
        "contract_version": "v1",
        "project_name": "q33_diag_test",
        "seed": 42,
        "time_limit_s": 15,
        "stocks": [{"id": "S1", "quantity": 1, "width": 300.0, "height": 200.0}],
        "parts": [{
            "id": "P1",
            "quantity": 2,
            "width": 40.0,
            "height": 30.0,
            "allowed_rotations_deg": [0, 90],
            "outer_points": [[0,0],[40,0],[40,30],[0,30]]
        }],
        "optimizer_pipeline": "sparrow_cde_multisheet",
        "collision_backend": "cde",
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "margin_mm": margin_mm,
        "spacing_mm": spacing_mm,
        "kerf_mm": kerf_mm,
    })
}

#[test]
fn sparrow_cde_multisheet_diagnostics_contain_technology_fields() {
    let v = full_ms_input_v(10.0, 2.0, 0.15);
    let input: SolverInput = serde_json::from_value(v).expect("parse");
    let output = solve(input).expect("solve");
    let diag = output
        .optimizer_diagnostics
        .as_ref()
        .expect("optimizer_diagnostics must be present");

    assert_eq!(diag.technology_policy_active, Some(true));
    assert_eq!(diag.technology_margin_mm, Some(10.0));
    assert_eq!(diag.technology_spacing_mm, Some(2.0));
    assert_eq!(diag.technology_kerf_mm, Some(0.15));
    assert_eq!(diag.technology_effective_sheet_margin_mm, Some(10.0));
    assert_eq!(diag.technology_effective_part_spacing_mm, Some(2.0));
    assert_eq!(diag.technology_effective_kerf_mm, Some(0.15));
}

// ── Test 5: backwards compatibility with Q32 inputs ───────────────────────────

#[test]
fn q32_input_without_spacing_kerf_deserializes_and_runs() {
    // Q32-style input: has margin_mm but no spacing_mm/kerf_mm.
    let v = json!({
        "contract_version": "v1",
        "project_name": "q32_compat_test",
        "seed": 1,
        "time_limit_s": 10,
        "stocks": [{"id": "S1", "quantity": 1, "width": 500.0, "height": 400.0}],
        "parts": [{
            "id": "P1",
            "quantity": 3,
            "width": 60.0,
            "height": 40.0,
            "allowed_rotations_deg": [0, 90],
            "outer_points": [[0,0],[60,0],[60,40],[0,40]]
        }],
        "optimizer_pipeline": "sparrow_cde_multisheet",
        "collision_backend": "cde",
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "margin_mm": 0.0
        // no spacing_mm, no kerf_mm
    });
    let input: SolverInput = serde_json::from_value(v).expect("Q32 input must deserialize");
    // spacing_mm/kerf_mm should be None (absent)
    assert_eq!(input.spacing_mm, None);
    assert_eq!(input.kerf_mm, None);
    let output = solve(input).expect("solve must succeed");
    // Run must succeed; technology policy defaults to 0/0/0.
    let diag = output
        .optimizer_diagnostics
        .as_ref()
        .expect("diagnostics present");
    assert_eq!(diag.technology_policy_active, Some(true));
    assert_eq!(diag.technology_margin_mm, Some(0.0));
    // spacing defaults to margin_mm (0.0) when absent
    assert_eq!(diag.technology_spacing_mm, Some(0.0));
    assert_eq!(diag.technology_kerf_mm, Some(0.0));
}
