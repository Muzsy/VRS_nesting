//! SGH-Q59 — BandInsert true-extreme slot-edge integration test + real-LV8 JSON/SVG artifact.

use std::path::PathBuf;

use vrs_solver::item::Part;
use vrs_solver::optimizer::sparrow::band_insert_slot_edge::{
    build_band_insert_slot_edge_candidates, BandInsertSlotEdgeResult,
};
use vrs_solver::rotation_policy::RotationPolicyKind;

const SHEET: [f64; 4] = [0.0, 0.0, 1500.0, 3000.0];

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
}

fn lv8() -> Part {
    let fixture = repo_root().join("artifacts/benchmarks/sgh_q51/inputs/q51_6big_sp8.json");
    let raw = std::fs::read_to_string(&fixture).expect("read fixture");
    let doc: serde_json::Value = serde_json::from_str(&raw).expect("parse");
    let p = &doc["parts"][0];
    Part {
        id: p["id"].as_str().unwrap().to_string(),
        width: p["width"].as_f64().unwrap(),
        height: p["height"].as_f64().unwrap(),
        quantity: 1,
        allowed_rotations_deg: vec![],
        rotation_policy: Some(RotationPolicyKind::Continuous),
        holes_points: None,
        prepared_holes_points: None,
        outer_points: Some(p["outer_points"].clone()),
        prepared_outer_points: None,
    }
}

#[test]
fn lv8_band_insert_true_extreme_slot_edge_fits_a_vertical_band() {
    let part = lv8();
    // A tall band slot that fits the LV8 part only in a near-vertical (continuous) orientation.
    let slot = [20.0, 20.0, 820.0, 2620.0];
    let res = build_band_insert_slot_edge_candidates(&part, slot, SHEET, 8.0, &[]).expect("res");

    assert!(
        res.valid_count() >= 1,
        "LV8 must fit the vertical band slot via a true-extreme candidate"
    );
    let sel = res.selected().expect("selected");
    assert!(sel.boundary_clear && sel.collision_clear);
    assert_eq!(sel.candidate_source, "true_extreme_slot_edge_band_insert");
    // The accepted candidate uses a continuous (likely fractional) rotation, not a forced orthogonal one.
    assert!(
        res.candidates.iter().any(|c| c.is_fractional),
        "continuous BandInsert must expose fractional rotations"
    );

    let dir = repo_root().join("artifacts/benchmarks/sgh_q59");
    std::fs::create_dir_all(&dir).expect("mkdir");
    std::fs::write(
        dir.join("band_insert_slot_edge_candidates.json"),
        serde_json::to_string_pretty(&res.to_diagnostics_json()).expect("ser"),
    )
    .expect("write json");
    std::fs::write(
        dir.join("band_insert_slot_edge_candidates.svg"),
        render_svg(&res),
    )
    .expect("write svg");
    assert!(dir.join("band_insert_slot_edge_candidates.svg").exists());
}

fn render_svg(res: &BandInsertSlotEdgeResult) -> String {
    let scale = 0.22_f64;
    let pad = 40.0;
    let w = (SHEET[2] - SHEET[0]) * scale + 2.0 * pad;
    let h = (SHEET[3] - SHEET[1]) * scale + 2.0 * pad + 40.0;
    let tx = |x: f64| pad + x * scale;
    let ty = |y: f64| pad + 20.0 + (SHEET[3] - y) * scale;
    let mut s = String::new();
    s.push_str(&format!(
        "<svg xmlns='http://www.w3.org/2000/svg' width='{w:.0}' height='{h:.0}' font-family='sans-serif'>\n"
    ));
    s.push_str(&format!(
        "<text x='{:.0}' y='18' font-size='14'>Q59 BandInsert true-extreme slot-edge — {}</text>\n",
        pad, res.part_id
    ));
    // sheet
    s.push_str(&format!(
        "<rect x='{:.1}' y='{:.1}' width='{:.1}' height='{:.1}' fill='none' stroke='red' stroke-width='1.5'/>\n",
        tx(SHEET[0]), ty(SHEET[3]), (SHEET[2]-SHEET[0])*scale, (SHEET[3]-SHEET[1])*scale
    ));
    // slot
    s.push_str(&format!(
        "<rect x='{:.1}' y='{:.1}' width='{:.1}' height='{:.1}' fill='#eef' stroke='blue' stroke-dasharray='5 3'/>\n",
        tx(res.slot_bbox[0]), ty(res.slot_bbox[3]), (res.slot_bbox[2]-res.slot_bbox[0])*scale, (res.slot_bbox[3]-res.slot_bbox[1])*scale
    ));
    for c in &res.candidates {
        if !(c.boundary_clear && c.collision_clear) {
            continue;
        }
        let e = c.final_extrema;
        s.push_str(&format!(
            "<rect x='{:.1}' y='{:.1}' width='{:.1}' height='{:.1}' fill='none' stroke='#88a' stroke-width='0.6' opacity='0.6'/>\n",
            tx(e[0]), ty(e[3]), (e[2]-e[0])*scale, (e[3]-e[1])*scale
        ));
    }
    if let Some(sel) = res.selected() {
        let e = sel.final_extrema;
        s.push_str(&format!(
            "<rect x='{:.1}' y='{:.1}' width='{:.1}' height='{:.1}' fill='#3b7' fill-opacity='0.25' stroke='#1a5' stroke-width='2'/>\n",
            tx(e[0]), ty(e[3]), (e[2]-e[0])*scale, (e[3]-e[1])*scale
        ));
        s.push_str(&format!(
            "<text x='{:.0}' y='{:.0}' font-size='11' fill='#1a5'>selected: {} / {} rot={:.2}° frac={} score={:.3}</text>\n",
            pad, h - 12.0, sel.target_slot_edge.as_str(), sel.secondary_axis_policy.as_str(),
            sel.rotation_deg, sel.is_fractional, sel.score
        ));
    }
    s.push_str("</svg>\n");
    s
}
