use vrs_solver::item::Part;
use vrs_solver::optimizer::sparrow::feature_candidate_generator::{
    generate_feature_candidate_seeds_debug, CandidateSeedSource, DebugPlacedNeighbour,
};
use vrs_solver::sheet::{stock_to_shape, SheetShape, Stock};

fn poly_part(id: &str, w: f64, h: f64, pts: serde_json::Value) -> Part {
    Part {
        id: id.to_string(),
        width: w,
        height: h,
        quantity: 1,
        allowed_rotations_deg: vec![0, 90, 180, 270],
        rotation_policy: None,
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
        width: Some(500.0),
        height: Some(320.0),
        outer_points: None,
        holes_points: None,
        cost_per_use: None,
    })
    .expect("rectangular stock")
}

fn bar_part() -> Part {
    poly_part(
        "bar",
        180.0,
        40.0,
        serde_json::json!([[0.0, 0.0], [180.0, 0.0], [180.0, 40.0], [0.0, 40.0]]),
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
    )
}

fn protrusion_part() -> Part {
    poly_part(
        "hook",
        120.0,
        110.0,
        serde_json::json!([
            [0.0, 25.0],
            [35.0, 0.0],
            [100.0, 0.0],
            [120.0, 30.0],
            [112.0, 78.0],
            [72.0, 110.0],
            [26.0, 96.0],
            [8.0, 62.0],
            [42.0, 58.0],
            [56.0, 76.0],
            [83.0, 72.0],
            [88.0, 42.0],
            [58.0, 24.0],
            [18.0, 28.0]
        ]),
    )
}

#[test]
fn feature_candidate_sheet_edge_alignment_exists_for_long_part() {
    let seeds = generate_feature_candidate_seeds_debug(&bar_part(), 0.0, &sheet(), &[], 24)
        .expect("feature seeds");
    assert!(
        seeds.iter().any(|seed| {
            seed.source == CandidateSeedSource::ContourFeature
                && seed.moving_feature_type == "dominant_edge"
                && seed.target_feature_type == "sheet_edge"
        }),
        "expected dominant-edge -> sheet-edge feature seed"
    );
}

#[test]
fn feature_candidate_neighbour_alignment_exists_for_concave_pair() {
    let seeds = generate_feature_candidate_seeds_debug(
        &protrusion_part(),
        0.0,
        &sheet(),
        &[DebugPlacedNeighbour {
            part: u_part(),
            x: 210.0,
            y: 80.0,
            rotation_deg: 0.0,
        }],
        48,
    )
    .expect("feature seeds");
    assert!(
        seeds.iter().any(|seed| {
            seed.target_feature_type == "concave_zone"
                || seed.target_feature_type == "dominant_edge"
                || seed.target_feature_type == "edge_projection"
        }),
        "expected at least one neighbour-driven contour feature alignment"
    );
}

#[test]
fn feature_candidate_debug_path_is_not_bbox_corner_primary() {
    let seeds = generate_feature_candidate_seeds_debug(
        &protrusion_part(),
        0.0,
        &sheet(),
        &[DebugPlacedNeighbour {
            part: u_part(),
            x: 210.0,
            y: 80.0,
            rotation_deg: 0.0,
        }],
        48,
    )
    .expect("feature seeds");
    assert!(!seeds.is_empty(), "expected some feature seeds");
    assert!(
        seeds.iter().all(|seed| {
            seed.source == CandidateSeedSource::ContourFeature
                && seed.moving_feature_type != "bbox_corner"
        }),
        "Q53B debug generator must not use moving bbox corners as the primary feature path"
    );
}
