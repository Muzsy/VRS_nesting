use crate::geometry::Rect;
use crate::io::{Placement, Unplaced};
use crate::item::{
    dims_for_rotation, normalize_allowed_rotations, placement_anchor_from_rect_min,
    rotated_bbox_min_offset, Instance, Part,
};
use crate::sheet::SheetShape;
use super::boundary::rect_within_boundary;
use super::candidates::{generate_candidates, PlacedBbox};

/// Diagnostics collected during a single construction run.
#[derive(Debug, Default, Clone)]
pub struct ConstructionDiagnostics {
    pub candidates_tried: usize,
    pub rejected_out_of_sheet: usize,
    pub rejected_collision: usize,
    pub rejected_unsupported_rotation: usize,
    pub items_unplaced_no_candidate: usize,
}

impl ConstructionDiagnostics {
    pub fn summary(&self) -> String {
        format!(
            "candidates_tried={} out_of_sheet={} collision={} unsupported_rot={} no_candidate={}",
            self.candidates_tried,
            self.rejected_out_of_sheet,
            self.rejected_collision,
            self.rejected_unsupported_rotation,
            self.items_unplaced_no_candidate,
        )
    }
}

/// Sort instances for placement: descending area → descending max bbox dim → part_id asc → instance_id asc.
pub fn sort_instances_for_placement<'a>(instances: &'a [Instance], parts: &[Part]) -> Vec<&'a Instance> {
    let part_area = |inst: &&Instance| -> f64 {
        parts.iter().find(|p| p.id == inst.part_id)
            .map(|p| p.width * p.height)
            .unwrap_or(0.0)
    };
    let max_dim = |inst: &&Instance| -> f64 { inst.width.max(inst.height) };
    let mut v: Vec<&Instance> = instances.iter().collect();
    v.sort_by(|a, b| {
        part_area(b).partial_cmp(&part_area(a)).unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| max_dim(b).partial_cmp(&max_dim(a)).unwrap_or(std::cmp::Ordering::Equal))
            .then_with(|| a.part_id.cmp(&b.part_id))
            .then_with(|| a.instance_id.cmp(&b.instance_id))
    });
    v
}

/// Recover the bbox (bbox-min coords) from a v1 Placement and the original part dimensions.
pub fn bbox_from_placement(placement: &Placement, w: f64, h: f64) -> Option<PlacedBbox> {
    let (bx_off, by_off) = rotated_bbox_min_offset(w, h, placement.rotation_deg)?;
    let (rw, rh) = dims_for_rotation(w, h, placement.rotation_deg)?;
    let x1 = placement.x + bx_off;
    let y1 = placement.y + by_off;
    Some(PlacedBbox { sheet_index: placement.sheet_index, x1, y1, x2: x1 + rw, y2: y1 + rh })
}

/// Build the initial layout using candidate-point placement.
///
/// Item ordering: area desc → max_dim desc → part_id asc → instance_id asc.
/// Candidate points per iteration: sheet origins + placed-bbox right/top/top-right corners.
/// Boundary: `rect_inside_sheet_shape` (JaguaAdapter-backed, exact).
/// Collision: rect-rect overlap (exact for Phase 1 rectangular items at 0/90/180/270°).
///
/// Invariant: `placed.len() + unplaced.len() == instances.len()`.
pub fn build_initial_layout(
    instances: &[Instance],
    parts: &[Part],
    sheets: &[SheetShape],
) -> (Vec<Placement>, Vec<Unplaced>, ConstructionDiagnostics) {
    let mut placements: Vec<Placement> = Vec::new();
    let mut unplaced_list: Vec<Unplaced> = Vec::new();
    let mut diag = ConstructionDiagnostics::default();
    let mut placed_bboxes: Vec<PlacedBbox> = Vec::new();

    let ordered = sort_instances_for_placement(instances, parts);

    for instance in ordered {
        let part = match parts.iter().find(|p| p.id == instance.part_id) {
            Some(p) => p,
            None => {
                unplaced_list.push(Unplaced {
                    instance_id: instance.instance_id.clone(),
                    part_id: instance.part_id.clone(),
                    reason: "INTERNAL_PART_NOT_FOUND".to_string(),
                });
                continue;
            }
        };

        let allowed_rotations = match normalize_allowed_rotations(&instance.allowed_rotations_deg) {
            Ok(r) => r,
            Err(_) => {
                diag.rejected_unsupported_rotation += 1;
                unplaced_list.push(Unplaced {
                    instance_id: instance.instance_id.clone(),
                    part_id: instance.part_id.clone(),
                    reason: "UNSUPPORTED_ROTATION".to_string(),
                });
                continue;
            }
        };

        let candidates = generate_candidates(sheets.len(), &placed_bboxes);
        let mut result = None;

        'outer: for candidate in &candidates {
            let sheet = &sheets[candidate.sheet_index];
            for &rot in &allowed_rotations {
                diag.candidates_tried += 1;
                let Some((rw, rh)) = dims_for_rotation(part.width, part.height, rot) else {
                    diag.rejected_unsupported_rotation += 1;
                    continue;
                };
                let rect = Rect {
                    x1: candidate.x,
                    y1: candidate.y,
                    x2: candidate.x + rw,
                    y2: candidate.y + rh,
                };
                if !rect_within_boundary(rect, sheet) {
                    diag.rejected_out_of_sheet += 1;
                    continue;
                }
                let candidate_bbox = PlacedBbox {
                    sheet_index: candidate.sheet_index,
                    x1: candidate.x,
                    y1: candidate.y,
                    x2: candidate.x + rw,
                    y2: candidate.y + rh,
                };
                if placed_bboxes.iter().any(|pb| pb.overlaps(&candidate_bbox)) {
                    diag.rejected_collision += 1;
                    continue;
                }
                let Some((anchor_x, anchor_y)) = placement_anchor_from_rect_min(
                    candidate.x, candidate.y, part.width, part.height, rot,
                ) else {
                    continue;
                };
                result = Some((
                    Placement {
                        instance_id: instance.instance_id.clone(),
                        part_id: instance.part_id.clone(),
                        sheet_index: candidate.sheet_index,
                        x: anchor_x,
                        y: anchor_y,
                        rotation_deg: rot,
                    },
                    candidate_bbox,
                ));
                break 'outer;
            }
        }

        if let Some((p, bbox)) = result {
            placed_bboxes.push(bbox);
            placements.push(p);
        } else {
            diag.items_unplaced_no_candidate += 1;
            unplaced_list.push(Unplaced {
                instance_id: instance.instance_id.clone(),
                part_id: instance.part_id.clone(),
                reason: "NO_CANDIDATE".to_string(),
            });
        }
    }

    (placements, unplaced_list, diag)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::item::expand_instances;
    use crate::sheet::{expand_sheets, Stock};

    fn make_part(id: &str, w: f64, h: f64, qty: i64, rots: Vec<i64>) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: qty,
            allowed_rotations_deg: rots,
            holes_points: None,
            prepared_holes_points: None,
            outer_points: None,
            prepared_outer_points: None,
        }
    }

    fn make_stock(id: &str, w: f64, h: f64, qty: i64) -> Stock {
        Stock { id: id.to_string(), quantity: qty, width: Some(w), height: Some(h), outer_points: None, holes_points: None }
    }

    #[test]
    fn sort_instances_area_descending() {
        let parts = vec![
            make_part("A", 10.0, 10.0, 1, vec![0]),
            make_part("B", 20.0, 20.0, 1, vec![0]),
        ];
        let instances = expand_instances(&parts).expect("expand");
        let sorted = sort_instances_for_placement(&instances, &parts);
        assert_eq!(sorted[0].part_id, "B");
        assert_eq!(sorted[1].part_id, "A");
    }

    #[test]
    fn small_fixture_all_placed() {
        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (placed, unplaced, _diag) = build_initial_layout(&instances, &parts, &sheets);
        assert_eq!(placed.len(), 2);
        assert!(unplaced.is_empty());
    }

    #[test]
    fn no_capacity_item_goes_to_unplaced() {
        let parts = vec![make_part("A", 200.0, 200.0, 1, vec![0])];
        let stocks = vec![make_stock("S", 50.0, 50.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (placed, unplaced, _diag) = build_initial_layout(&instances, &parts, &sheets);
        assert!(placed.is_empty());
        assert_eq!(unplaced.len(), 1);
        assert_eq!(unplaced[0].reason, "NO_CANDIDATE");
    }

    #[test]
    fn placed_plus_unplaced_equals_total() {
        let parts = vec![make_part("A", 60.0, 60.0, 3, vec![0])];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (placed, unplaced, _diag) = build_initial_layout(&instances, &parts, &sheets);
        assert_eq!(placed.len() + unplaced.len(), 3);
    }

    #[test]
    fn rotation_90_only_fits() {
        // 80×30 part, 40×100 sheet: rot=0 (80×30) → 80>40, fails; rot=90 (30×80) → fits
        let parts = vec![make_part("P", 80.0, 30.0, 1, vec![0, 90])];
        let stocks = vec![make_stock("S", 40.0, 100.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (placed, unplaced, _diag) = build_initial_layout(&instances, &parts, &sheets);
        assert_eq!(placed.len(), 1);
        assert_eq!(placed[0].rotation_deg, 90);
        assert!(unplaced.is_empty());
    }

    #[test]
    fn deterministic_two_runs_identical() {
        let parts = vec![
            make_part("A", 40.0, 40.0, 2, vec![0]),
            make_part("B", 40.0, 40.0, 1, vec![0]),
        ];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (p1, _, _) = build_initial_layout(&instances, &parts, &sheets);
        let (p2, _, _) = build_initial_layout(&instances, &parts, &sheets);
        let key = |p: &Placement| (p.instance_id.clone(), p.x.to_bits(), p.y.to_bits(), p.rotation_deg);
        assert_eq!(
            p1.iter().map(key).collect::<Vec<_>>(),
            p2.iter().map(key).collect::<Vec<_>>(),
        );
    }

    #[test]
    fn bbox_from_placement_rot0() {
        let p = Placement { instance_id: "A__0001".into(), part_id: "A".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0 };
        let bb = bbox_from_placement(&p, 100.0, 40.0).expect("bbox");
        assert!((bb.x2 - 100.0).abs() < 1e-9);
        assert!((bb.y2 - 40.0).abs() < 1e-9);
    }

    #[test]
    fn bbox_from_placement_rot90() {
        // anchor=(40,0), rot=90, w=100, h=40: offset=(-40,0) → bbox_min=(0,0), rw=40, rh=100
        let p = Placement { instance_id: "A__0001".into(), part_id: "A".into(), sheet_index: 0, x: 40.0, y: 0.0, rotation_deg: 90 };
        let bb = bbox_from_placement(&p, 100.0, 40.0).expect("bbox");
        assert!((bb.x1 - 0.0).abs() < 1e-9);
        assert!((bb.x2 - 40.0).abs() < 1e-9);
        assert!((bb.y2 - 100.0).abs() < 1e-9);
    }
}
