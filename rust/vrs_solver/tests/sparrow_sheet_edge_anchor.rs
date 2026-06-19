//! SGH-Q55A — Sheet-aware edge-anchor rotation tests.
//!
//! The sheet-edge anchor candidates must be SHEET-AWARE: align the part's dominant edge to BOTH the
//! sheet's long and short edge directions (with 180° flips), not a single part-axis seed. For a
//! continuous part the refined rotation stays continuous (no 90/270 snapping).

use serde_json::{json, Value};
use vrs_solver::item::Part;
use vrs_solver::optimizer::sparrow::feature_candidate_generator::generate_feature_candidate_seeds_debug;
use vrs_solver::rotation_policy::RotationPolicyKind;
use vrs_solver::sheet::{stock_to_shape, SheetShape, Stock};

fn continuous_part(id: &str, w: f64, h: f64, pts: Value) -> Part {
    Part {
        id: id.to_string(),
        width: w,
        height: h,
        quantity: 1,
        allowed_rotations_deg: vec![],
        rotation_policy: Some(RotationPolicyKind::Continuous),
        holes_points: None,
        prepared_holes_points: None,
        outer_points: Some(pts),
        prepared_outer_points: None,
    }
}

// A long, slightly skewed part (dominant long edge ~1° off-axis) — like the LV8 big part.
fn long_skewed_part() -> Part {
    continuous_part(
        "long",
        2400.0,
        700.0,
        json!([[0.0, 50.0], [2400.0, 0.0], [2400.0, 700.0], [0.0, 650.0]]),
    )
}

fn sheet_1500x3000() -> SheetShape {
    stock_to_shape(&Stock {
        id: "S".to_string(),
        quantity: 1,
        width: Some(1500.0),
        height: Some(3000.0),
        outer_points: None,
        holes_points: None,
        cost_per_use: None,
    })
    .expect("rectangular stock")
}

#[test]
fn sheet_edge_anchor_is_sheet_aware_long_and_short_with_flips() {
    let seeds = generate_feature_candidate_seeds_debug(
        &long_skewed_part(),
        0.0,
        &sheet_1500x3000(),
        &[],
        48,
        0.0,
    )
    .expect("feature seeds");

    let edge_seeds: Vec<_> = seeds
        .iter()
        .filter(|s| s.target_feature_type == "sheet_edge")
        .collect();
    assert!(!edge_seeds.is_empty(), "sheet-edge anchor candidates expected");

    // Sheet-aware: the dominant edge is aligned to BOTH sheet directions → the seed rotations span
    // more than one orientation family (long-edge ≈ 90°-ish AND short-edge ≈ 0°-ish, plus flips).
    let mut norm: Vec<i64> = edge_seeds
        .iter()
        .map(|s| ((s.seed_rotation_deg.rem_euclid(180.0)) * 10.0).round() as i64)
        .collect();
    norm.sort();
    norm.dedup();
    assert!(
        norm.len() >= 2,
        "sheet-aware anchor must span long+short edge orientations, got {norm:?}"
    );

    // Continuous: the sheet-aware seed aligns the part's slightly-skewed dominant edge to the sheet
    // edge at a CONTINUOUS angle (≈1.2° off the axis), NOT snapped to a multiple of 90°. (The full
    // CDE-clear sheet-edge anchor on real geometry is proven on the solver path in Q55C/F.)
    assert!(
        edge_seeds.iter().any(|s| {
            let r = s.seed_rotation_deg.rem_euclid(90.0);
            !(r < 0.5 || r > 89.5)
        }),
        "sheet-aware anchor seed must be continuous (sheet-edge-parallel, not 90-snapped)"
    );

    // The flip variants are present: rotations span both an "up" and a "down" family (≈180° apart).
    let has_flip = edge_seeds.iter().any(|a| {
        edge_seeds.iter().any(|b| {
            let d = (a.seed_rotation_deg - b.seed_rotation_deg).rem_euclid(360.0);
            (d - 180.0).abs() < 5.0
        })
    });
    assert!(has_flip, "sheet-aware anchor must include 180° flip variants");
}
