use vrs_solver::item::Part;
use vrs_solver::optimizer::sparrow::feature_candidate_generator::{
    generate_feature_candidate_seeds_debug, refine_feature_candidate_debug, DebugPlacedNeighbour,
};
use vrs_solver::rotation_policy::RotationPolicyKind;
use vrs_solver::sheet::{stock_to_shape, SheetShape, Stock};

fn poly_part(
    id: &str,
    w: f64,
    h: f64,
    pts: serde_json::Value,
    rotation_policy: Option<RotationPolicyKind>,
    allowed_rotations_deg: Vec<i64>,
) -> Part {
    Part {
        id: id.to_string(),
        width: w,
        height: h,
        quantity: 1,
        allowed_rotations_deg,
        rotation_policy,
        holes_points: None,
        prepared_holes_points: None,
        outer_points: Some(pts),
        prepared_outer_points: None,
    }
}

fn sheet() -> SheetShape {
    stock_to_shape(&Stock {
        id: "S".to_string(),
        quantity: 1,
        width: Some(520.0),
        height: Some(320.0),
        outer_points: None,
        holes_points: None,
        cost_per_use: None,
    })
    .expect("rectangular stock")
}

fn long_bar_continuous() -> Part {
    poly_part(
        "bar_cont",
        180.0,
        40.0,
        serde_json::json!([[0.0, 0.0], [180.0, 0.0], [180.0, 40.0], [0.0, 40.0]]),
        Some(RotationPolicyKind::Continuous),
        vec![],
    )
}

fn long_bar_discrete() -> Part {
    poly_part(
        "bar_disc",
        180.0,
        40.0,
        serde_json::json!([[0.0, 0.0], [180.0, 0.0], [180.0, 40.0], [0.0, 40.0]]),
        None,
        vec![0, 90, 180, 270],
    )
}

fn u_part() -> Part {
    poly_part(
        "u",
        160.0,
        140.0,
        serde_json::json!([
            [0.0, 0.0],
            [160.0, 0.0],
            [160.0, 140.0],
            [110.0, 140.0],
            [110.0, 50.0],
            [50.0, 50.0],
            [50.0, 140.0],
            [0.0, 140.0]
        ]),
        None,
        vec![0, 90, 180, 270],
    )
}

fn approx_canonical_orthogonal(rot: f64) -> bool {
    [0.0, 90.0, 180.0, -90.0, 270.0]
        .iter()
        .any(|target| (rot - target).abs() < 1e-6)
}

#[test]
fn continuous_feature_refine_continuous_seed_can_wiggle_off_orthogonal() {
    let seeds = generate_feature_candidate_seeds_debug(
        &long_bar_continuous(),
        0.0,
        &sheet(),
        &[DebugPlacedNeighbour {
            part: u_part(),
            x: 220.0,
            y: 90.0,
            rotation_deg: 0.0,
        }],
        32,
        0.0,
    )
    .expect("feature seeds");
    assert!(
        seeds.iter().any(|seed| {
            seed.refine_success
                && approx_canonical_orthogonal(seed.seed_rotation_deg)
                && !approx_canonical_orthogonal(seed.rotation_seed_deg)
        }),
        "continuous refine should be able to move a feature seed off the canonical orthogonal angle"
    );
}

#[test]
fn continuous_feature_refine_discrete_policy_stays_allowed_only() {
    let seeds = generate_feature_candidate_seeds_debug(
        &long_bar_discrete(),
        0.0,
        &sheet(),
        &[DebugPlacedNeighbour {
            part: u_part(),
            x: 220.0,
            y: 90.0,
            rotation_deg: 0.0,
        }],
        32,
        0.0,
    )
    .expect("feature seeds");
    assert!(!seeds.is_empty());
    assert!(seeds.iter().all(|seed| {
        [0.0, 90.0, 180.0, 270.0]
            .iter()
            .any(|allowed| (seed.rotation_seed_deg - allowed).abs() < 1e-6)
    }));
}

#[test]
fn continuous_feature_refine_debug_api_reports_seed_and_refined_rotation() {
    let moving = long_bar_continuous();
    let neighbour = DebugPlacedNeighbour {
        part: u_part(),
        x: 220.0,
        y: 90.0,
        rotation_deg: 0.0,
    };
    let seed = generate_feature_candidate_seeds_debug(
        &moving,
        0.0,
        &sheet(),
        std::slice::from_ref(&neighbour),
        32,
        0.0,
    )
    .expect("feature seeds")
    .into_iter()
    .find(|seed| seed.refine_success)
    .expect("at least one refined feature seed");
    let diag =
        refine_feature_candidate_debug(&moving, &seed, &sheet(), std::slice::from_ref(&neighbour))
            .expect("refine debug");
    assert!(diag.refine_success);
    assert!(diag.refine_iterations > 0);
    assert!(diag.refined_rotation_deg.is_finite());
    assert!(diag.seed_rotation_deg.is_finite());
}
