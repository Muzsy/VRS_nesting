//! SGH-Q68 - focused live-instance artifact for Anchor catalog authority cutover.

use std::path::PathBuf;

use vrs_solver::io::CollisionBackendKind;
use vrs_solver::item::Part;
use vrs_solver::optimizer::sparrow::feature_candidate_generator::{
    generate_feature_candidate_seeds_debug, CandidateSeed,
};
use vrs_solver::optimizer::sparrow::sheet_edge_placement_catalog::anchor_candidates_for_instance;
use vrs_solver::optimizer::sparrow::{SparrowConfig, SparrowProblem};
use vrs_solver::rotation_policy::{RotationPolicyKind, RotationResolveContext};
use vrs_solver::sheet::{stock_to_shape, Stock};

const SP0: &str = "artifacts/benchmarks/sgh_q51/inputs/q51_6big_sp0.json";

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
}

fn load_fixture_part_and_stock() -> (Part, Stock) {
    let raw = std::fs::read_to_string(repo_root().join(SP0)).expect("read fixture");
    let doc: serde_json::Value = serde_json::from_str(&raw).expect("parse fixture");
    let mut part: Part = serde_json::from_value(doc["parts"][0].clone()).expect("part");
    part.quantity = 1;
    part.rotation_policy = Some(RotationPolicyKind::Continuous);
    let mut stock: Stock = serde_json::from_value(doc["stocks"][0].clone()).expect("stock");
    stock.quantity = 1;
    (part, stock)
}

fn live_instance_fixture() -> (
    Part,
    vrs_solver::sheet::SheetShape,
    vrs_solver::optimizer::sparrow::SPInstance,
) {
    let (part, stock) = load_fixture_part_and_stock();
    let sheet = stock_to_shape(&stock).expect("sheet");
    let rotation_context =
        RotationResolveContext::new(Some(RotationPolicyKind::Continuous), 42, 24);
    let cfg = SparrowConfig::from_solver_input(
        30.0,
        CollisionBackendKind::Cde,
        rotation_context.clone(),
        42,
    );
    let problem = SparrowProblem::from_solver_input(
        std::slice::from_ref(&part),
        std::slice::from_ref(&sheet),
        &rotation_context,
        Vec::new(),
        cfg,
    )
    .expect("problem");
    let inst = problem.instances.into_iter().next().expect("instance");
    (part, sheet, inst)
}

fn seed_json(seed: &CandidateSeed) -> serde_json::Value {
    serde_json::json!({
        "x": seed.x,
        "y": seed.y,
        "seed_rotation_deg": seed.seed_rotation_deg,
        "rotation_seed_deg": seed.rotation_seed_deg,
        "source": format!("{:?}", seed.source),
        "moving_feature_type": seed.moving_feature_type,
        "target_feature_type": seed.target_feature_type,
        "alignment_kind": seed.alignment_kind,
        "source_score": seed.source_score,
        "refine_success": seed.refine_success,
        "selected_edge_index": seed.selected_edge_index,
        "selected_edge_angle_deg": seed.selected_edge_angle_deg,
        "target_axis_angle_deg": seed.target_axis_angle_deg,
    })
}

#[test]
fn focused_anchor_catalog_runner_writes_cutover_artifact() {
    let (part, sheet, inst) = live_instance_fixture();
    let anchor_candidates = anchor_candidates_for_instance(&inst, &sheet);
    let feature_seeds =
        generate_feature_candidate_seeds_debug(&part, 0.0, &sheet, &[], 24, 0.0).expect("seeds");
    let sheet_edge_feature_seeds: Vec<&CandidateSeed> = feature_seeds
        .iter()
        .filter(|seed| seed.target_feature_type == "sheet_edge")
        .collect();

    assert!(
        !anchor_candidates.is_empty(),
        "live anchor catalog must generate candidates for the real LV8 instance"
    );
    assert!(
        !sheet_edge_feature_seeds.is_empty(),
        "live sheet-edge feature path must still generate anchor-role seeds"
    );

    let artifact = serde_json::json!({
        "fixture": SP0,
        "part_id": part.id,
        "sheet_size": {
            "width": sheet.width,
            "height": sheet.height,
        },
        "orientation_catalog_angles_deg": inst
            .orientation_catalog
            .candidates
            .iter()
            .map(|c| c.angle_deg)
            .collect::<Vec<_>>(),
        "anchor_catalog": {
            "candidates_generated": anchor_candidates.len(),
            "preview": anchor_candidates
                .iter()
                .take(8)
                .map(|c| serde_json::json!({
                    "rect_min_x": c.rect_min_x,
                    "rect_min_y": c.rect_min_y,
                    "rotation_deg": c.rotation_deg,
                    "target_sheet_edge": c.target_sheet_edge,
                    "secondary_axis_policy": c.secondary_axis_policy,
                    "source": c.source,
                    "source_edge_index": c.source_edge_index,
                    "is_corner": c.is_corner,
                    "is_fractional": c.is_fractional,
                }))
                .collect::<Vec<_>>(),
        },
        "feature_path": {
            "seeds_generated": feature_seeds.len(),
            "sheet_edge_seeds_generated": sheet_edge_feature_seeds.len(),
            "preview": sheet_edge_feature_seeds
                .iter()
                .take(8)
                .map(|seed| seed_json(seed))
                .collect::<Vec<_>>(),
        },
        "authority_policy_examples": {
            "feature_10_catalog_10": "catalog",
            "feature_10_catalog_10_5": "catalog",
            "feature_10_catalog_9_5": "feature",
        }
    });
    let dir = repo_root().join("artifacts/benchmarks/sgh_q68");
    std::fs::create_dir_all(&dir).expect("mkdir");
    std::fs::write(
        dir.join("anchor_catalog_production_cutover.json"),
        serde_json::to_string_pretty(&artifact).expect("serialize artifact"),
    )
    .expect("write artifact");
    assert!(dir.join("anchor_catalog_production_cutover.json").exists());
}
