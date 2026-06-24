//! SGH-Q56C — SheetEdgePlacementCatalog integration test + real-LV8 visual artifact.
//!
//! Loads the REAL critical LV8 part, builds the edge+corner Anchor catalog on the real 1500×3000 sheet
//! with the real margin (5) / spacing (8), and proves: candidates on all four edges, first-class corner
//! variants, a boundary-clear selected candidate with a recorded free-space score, and spacing-expanded
//! true extrema (offset contour within the margin-shrunk sheet). Emits JSON + SVG under
//! `artifacts/benchmarks/sgh_q56c/`.

use std::path::PathBuf;

use vrs_solver::item::Part;
use vrs_solver::optimizer::sparrow::sheet_edge_placement_catalog::build_sheet_edge_anchor_catalog;
use vrs_solver::rotation_policy::RotationPolicyKind;

const SHEET_W: f64 = 1500.0;
const SHEET_H: f64 = 3000.0;
const MARGIN_MM: f64 = 5.0;
const SPACING_MM: f64 = 8.0;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
}

fn load_lv8_critical_part() -> Part {
    let fixture = repo_root().join("artifacts/benchmarks/sgh_q51/inputs/q51_6big_sp8.json");
    let raw = std::fs::read_to_string(&fixture)
        .unwrap_or_else(|e| panic!("read fixture {}: {e}", fixture.display()));
    let doc: serde_json::Value = serde_json::from_str(&raw).expect("parse fixture json");
    let p = &doc["parts"][0];
    Part {
        id: p["id"].as_str().expect("id").to_string(),
        width: p["width"].as_f64().expect("w"),
        height: p["height"].as_f64().expect("h"),
        quantity: 1,
        allowed_rotations_deg: vec![],
        rotation_policy: Some(RotationPolicyKind::Continuous),
        holes_points: None,
        prepared_holes_points: None,
        outer_points: Some(p["outer_points"].clone()),
        prepared_outer_points: None,
    }
}

fn out_dir() -> PathBuf {
    let d = repo_root().join("artifacts/benchmarks/sgh_q56c");
    std::fs::create_dir_all(&d).expect("create out dir");
    d
}

#[test]
fn lv8_sheet_edge_anchor_catalog_has_edge_corner_variants_and_scored_selection() {
    let part = load_lv8_critical_part();
    let cat = build_sheet_edge_anchor_catalog(&part, SHEET_W, SHEET_H, MARGIN_MM, SPACING_MM)
        .expect("anchor catalog for real LV8 part");

    // Candidates on all four edges.
    for edge in ["left", "right", "bottom", "top"] {
        assert!(
            cat.candidates
                .iter()
                .any(|c| c.boundary_clear && c.target_sheet_edge.as_str() == edge),
            "missing boundary-clear candidate on edge {edge}"
        );
    }
    // Corner variants are first-class.
    assert!(cat.corner_count() >= 1, "corner variants must exist");
    // A scored, boundary-clear selection.
    let sel = cat.selected().expect("a selected candidate");
    assert!(sel.boundary_clear);
    assert!(
        sel.free_space_score > 0.0,
        "selected candidate must record a free-space score"
    );
    // Center is not the only secondary policy among boundary-clear candidates.
    let clear_corner = cat
        .candidates
        .iter()
        .filter(|c| c.boundary_clear && c.is_corner)
        .count();
    assert!(
        clear_corner > 0,
        "center must not be the only Anchor secondary policy"
    );

    // Artifacts.
    let json = cat.to_diagnostics_json();
    let dir = out_dir();
    std::fs::write(
        dir.join("sheet_edge_anchor_candidates.json"),
        serde_json::to_string_pretty(&json).expect("ser"),
    )
    .expect("write json");
    std::fs::write(
        dir.join("sheet_edge_anchor_candidates.svg"),
        render_svg(&cat),
    )
    .expect("write svg");
    assert!(dir.join("sheet_edge_anchor_candidates.svg").exists());
}

fn render_svg(
    cat: &vrs_solver::optimizer::sparrow::sheet_edge_placement_catalog::SheetEdgeAnchorCatalog,
) -> String {
    let scale = 0.22_f64;
    let pad = 40.0;
    let w = SHEET_W * scale + 2.0 * pad;
    let h = SHEET_H * scale + 2.0 * pad + 40.0;
    let tx = |x: f64| pad + x * scale;
    let ty = |y: f64| pad + 20.0 + (SHEET_H - y) * scale;
    let mut s = String::new();
    s.push_str(&format!(
        "<svg xmlns='http://www.w3.org/2000/svg' width='{w:.0}' height='{h:.0}' font-family='sans-serif'>\n"
    ));
    s.push_str(&format!(
        "<text x='{:.0}' y='18' font-size='14'>Q56C SheetEdgePlacementCatalog — {} (edge+corner Anchor candidates)</text>\n",
        pad, cat.part_id
    ));
    // raw sheet
    s.push_str(&format!(
        "<rect x='{:.1}' y='{:.1}' width='{:.1}' height='{:.1}' fill='none' stroke='red' stroke-width='1.5'/>\n",
        tx(cat.sheet[0]), ty(cat.sheet[3]), (cat.sheet[2]-cat.sheet[0])*scale, (cat.sheet[3]-cat.sheet[1])*scale
    ));
    // shrunk (margin) sheet
    s.push_str(&format!(
        "<rect x='{:.1}' y='{:.1}' width='{:.1}' height='{:.1}' fill='none' stroke='green' stroke-dasharray='4 3'/>\n",
        tx(cat.shrunk_sheet[0]), ty(cat.shrunk_sheet[3]), (cat.shrunk_sheet[2]-cat.shrunk_sheet[0])*scale, (cat.shrunk_sheet[3]-cat.shrunk_sheet[1])*scale
    ));
    // boundary-clear candidate offset bboxes
    for c in &cat.candidates {
        if !c.boundary_clear {
            continue;
        }
        let e = c.final_extrema;
        s.push_str(&format!(
            "<rect x='{:.1}' y='{:.1}' width='{:.1}' height='{:.1}' fill='none' stroke='#88a' stroke-width='0.6' opacity='0.7'/>\n",
            tx(e[0]), ty(e[3]), (e[2]-e[0])*scale, (e[3]-e[1])*scale
        ));
    }
    // selected highlighted
    if let Some(sel) = cat.selected() {
        let e = sel.final_extrema;
        s.push_str(&format!(
            "<rect x='{:.1}' y='{:.1}' width='{:.1}' height='{:.1}' fill='#3b7' fill-opacity='0.25' stroke='#1a5' stroke-width='2'/>\n",
            tx(e[0]), ty(e[3]), (e[2]-e[0])*scale, (e[3]-e[1])*scale
        ));
        s.push_str(&format!(
            "<text x='{:.0}' y='{:.0}' font-size='11' fill='#1a5'>selected: {} / {} rot={:.2}° free={:.0} score={:.3}</text>\n",
            pad, h - 12.0,
            sel.target_sheet_edge.as_str(),
            sel.secondary_axis_policy.label(sel.target_sheet_edge),
            sel.computed_rotation_deg, sel.free_space_score, sel.candidate_score
        ));
    }
    s.push_str("</svg>\n");
    s
}
