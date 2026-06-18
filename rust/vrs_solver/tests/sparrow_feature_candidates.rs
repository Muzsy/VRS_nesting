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
    let seeds = generate_feature_candidate_seeds_debug(&bar_part(), 0.0, &sheet(), &[], 24, 0.0)
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
        0.0,
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
        0.0,
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

#[test]
fn q54b_clearance_offsets_neighbour_seeds_off_point_on_point() {
    // SGH-Q54B: with a clearance the neighbour feature alignment seeds the part with a GAP (so the
    // two spacing-expanded contours just touch) instead of point-on-point — the Q53 root cause of
    // `seed_not_clear`. Concretely: NO clearance>0 seed lands on a clearance=0 (point-on-point)
    // position for the same alignment kind, and the offset magnitude matches the clearance.
    const C: f64 = 6.0;
    let neighbours = || {
        vec![DebugPlacedNeighbour {
            part: u_part(),
            x: 210.0,
            y: 80.0,
            rotation_deg: 0.0,
        }]
    };
    let neighbour_seeds = |clearance: f64| -> Vec<(f64, f64, f64, &'static str)> {
        generate_feature_candidate_seeds_debug(&protrusion_part(), 0.0, &sheet(), &neighbours(), 64, clearance)
            .expect("feature seeds")
            .into_iter()
            .filter(|s| s.target_feature_type != "sheet_edge") // neighbour-driven only
            .map(|s| (s.x, s.y, s.seed_rotation_deg, s.alignment_kind))
            .collect()
    };

    let s0 = neighbour_seeds(0.0);
    let s_c = neighbour_seeds(C);
    assert!(!s0.is_empty() && !s_c.is_empty(), "neighbour-driven feature seeds expected");

    // No clearance=C seed coincides with a clearance=0 seed of the same kind+rotation (it moved).
    let key = |x: f64, y: f64| ((x * 100.0).round() as i64, (y * 100.0).round() as i64);
    for (cx, cy, crot, ckind) in &s_c {
        let coincides = s0.iter().any(|(x, y, rot, kind)| {
            key(*x, *y) == key(*cx, *cy) && (rot - crot).abs() < 1e-6 && kind == ckind
        });
        assert!(
            !coincides,
            "clearance must offset the {ckind} seed off the Q53 point-on-point position"
        );
    }

    // The offset magnitude matches the clearance: at least one clearance=C seed has a
    // same-kind/rotation clearance=0 seed exactly C away (the target was pulled out by `clearance`).
    // (Not every seed, because finalize clamps/dedups some — but the mechanism is unambiguous.)
    let any_exact_offset = s_c.iter().any(|(cx, cy, crot, ckind)| {
        s0.iter().any(|(x, y, rot, kind)| {
            kind == ckind
                && (rot - crot).abs() < 1e-6
                && (((x - cx).powi(2) + (y - cy).powi(2)).sqrt() - C).abs() < 1e-3
        })
    });
    assert!(any_exact_offset, "at least one seed must be offset by exactly the clearance ({C})");
}
