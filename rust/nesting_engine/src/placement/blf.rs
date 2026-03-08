use crate::feasibility::{
    aabb::{Aabb, aabb_from_polygon64},
    can_place, PlacedPart,
    narrow::PlacedIndex,
};
use crate::geometry::{
    scale::{i64_to_mm, mm_to_i64},
    trig_lut::{round_div_i128, normalize_deg, COS_Q, SIN_Q, TRIG_SCALE_I128},
    types::{Point64, Polygon64},
};
use crate::multi_bin::greedy::{PartInPartMode, PartOrderPolicy, StopPolicy};

const CAVITY_NUDGE_STEPS: [i64; 3] = [1, 2, 4];
const CAVITY_NUDGE_DIRS: [(i64, i64); 8] = [
    (1, 0),
    (0, 1),
    (1, 1),
    (-1, 0),
    (0, -1),
    (-1, -1),
    (-1, 1),
    (1, -1),
];

#[derive(Debug, Clone)]
pub struct InflatedPartSpec {
    pub id: String,
    pub quantity: usize,
    pub allowed_rotations_deg: Vec<i32>,
    pub inflated_polygon: Polygon64,
    pub nominal_bbox_area: i128,
}

#[derive(Debug, Clone, PartialEq)]
pub struct PlacedItem {
    pub part_id: String,
    pub instance: usize,
    pub sheet: usize,
    pub x_mm: f64,
    pub y_mm: f64,
    pub rotation_deg: i32,
}

#[derive(Debug, Clone, PartialEq)]
pub struct UnplacedItem {
    pub part_id: String,
    pub instance: usize,
    pub reason: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct PlacementResult {
    pub placed: Vec<PlacedItem>,
    pub unplaced: Vec<UnplacedItem>,
}

pub fn blf_place(
    parts: &[InflatedPartSpec],
    bin_polygon: &Polygon64,
    grid_step_mm: f64,
    stop: &mut StopPolicy,
    order_policy: PartOrderPolicy,
    part_in_part_mode: PartInPartMode,
) -> PlacementResult {
    let ordered = order_parts_for_policy(parts, order_policy);

    let step = mm_to_i64(if grid_step_mm <= 0.0 { 1.0 } else { grid_step_mm }).max(1);
    let bin_aabb = aabb_from_polygon64(bin_polygon);
    let mut placed_state = PlacedIndex::new();
    let mut placed_polygons: Vec<Polygon64> = Vec::new();
    let mut placed: Vec<PlacedItem> = Vec::new();
    let mut unplaced: Vec<UnplacedItem> = Vec::new();

    for part in &ordered {
        'instance_loop: for instance in 0..part.quantity {
            if stop.should_stop() {
                unplaced.push(UnplacedItem {
                    part_id: part.id.clone(),
                    instance,
                    reason: "TIME_LIMIT_EXCEEDED".to_string(),
                });
                continue;
            }

            let mut found = false;
            let rotation_candidates: Vec<(i32, Polygon64, crate::feasibility::aabb::Aabb)> = part
                .allowed_rotations_deg
                .iter()
                .map(|&rotation| {
                    let rotated = rotate_polygon(&part.inflated_polygon, rotation);
                    let rotated_aabb = aabb_from_polygon64(&rotated);
                    (rotation, rotated, rotated_aabb)
                })
                .collect();
            if rotation_candidates.is_empty() {
                unplaced.push(UnplacedItem {
                    part_id: part.id.clone(),
                    instance,
                    reason: "PART_NEVER_FITS_SHEET".to_string(),
                });
                continue;
            }

            let mut global_tx_min = i64::MAX;
            let mut global_ty_min = i64::MAX;
            let mut global_tx_max = i64::MIN;
            let mut global_ty_max = i64::MIN;
            for (_, _, aabb) in &rotation_candidates {
                global_tx_min = global_tx_min.min(bin_aabb.min_x - aabb.min_x);
                global_ty_min = global_ty_min.min(bin_aabb.min_y - aabb.min_y);
                global_tx_max = global_tx_max.max(bin_aabb.max_x - aabb.max_x);
                global_ty_max = global_ty_max.max(bin_aabb.max_y - aabb.max_y);
            }

            let mut timed_out_current = false;
            if part_in_part_mode == PartInPartMode::Auto {
                'cavity_rotation: for (rotation, rotated, rotated_aabb) in &rotation_candidates {
                    let tx_min = bin_aabb.min_x - rotated_aabb.min_x;
                    let ty_min = bin_aabb.min_y - rotated_aabb.min_y;
                    let tx_max = bin_aabb.max_x - rotated_aabb.max_x;
                    let ty_max = bin_aabb.max_y - rotated_aabb.max_y;

                    let cavity_candidates = collect_cavity_candidates(
                        &placed_polygons,
                        *rotated_aabb,
                        tx_min,
                        ty_min,
                        tx_max,
                        ty_max,
                    );
                    for (tx, ty) in cavity_candidates {
                        if stop.consume(1) {
                            timed_out_current = true;
                            break 'cavity_rotation;
                        }

                        let candidate = translate_polygon(rotated, tx, ty);
                        if can_place(&candidate, bin_polygon, &placed_state) {
                            let candidate_aabb = aabb_from_polygon64(&candidate);
                            placed_state.insert(PlacedPart {
                                inflated_polygon: candidate.clone(),
                                aabb: candidate_aabb,
                            });
                            placed_polygons.push(candidate);
                            placed.push(PlacedItem {
                                part_id: part.id.clone(),
                                instance,
                                sheet: 0,
                                x_mm: i64_to_mm(tx),
                                y_mm: i64_to_mm(ty),
                                rotation_deg: *rotation,
                            });
                            found = true;
                            break 'cavity_rotation;
                        }
                    }
                }
            }

            if found {
                continue;
            }

            let mut ty = global_ty_min;
            while ty <= global_ty_max && !found {
                if stop.consume(1) {
                    timed_out_current = true;
                    break;
                }
                let mut tx = global_tx_min;
                while tx <= global_tx_max && !found {
                    if stop.consume(1) {
                        timed_out_current = true;
                        break;
                    }
                    for (rotation, rotated, rotated_aabb) in &rotation_candidates {
                        if stop.consume(1) {
                            timed_out_current = true;
                            break;
                        }
                        let tx_min = bin_aabb.min_x - rotated_aabb.min_x;
                        let ty_min = bin_aabb.min_y - rotated_aabb.min_y;
                        let tx_max = bin_aabb.max_x - rotated_aabb.max_x;
                        let ty_max = bin_aabb.max_y - rotated_aabb.max_y;
                        if tx < tx_min || tx > tx_max || ty < ty_min || ty > ty_max {
                            continue;
                        }

                        let candidate = translate_polygon(rotated, tx, ty);
                        if can_place(&candidate, bin_polygon, &placed_state) {
                            let candidate_aabb = aabb_from_polygon64(&candidate);
                            placed_state.insert(PlacedPart {
                                inflated_polygon: candidate.clone(),
                                aabb: candidate_aabb,
                            });
                            placed_polygons.push(candidate);
                            placed.push(PlacedItem {
                                part_id: part.id.clone(),
                                instance,
                                sheet: 0,
                                x_mm: i64_to_mm(tx),
                                y_mm: i64_to_mm(ty),
                                rotation_deg: *rotation,
                            });
                            found = true;
                            break;
                        }
                    }
                    if timed_out_current {
                        break;
                    }
                    tx = tx.saturating_add(step);
                }
                if timed_out_current {
                    break;
                }
                ty = ty.saturating_add(step);
            }

            if timed_out_current {
                for remaining_instance in instance..part.quantity {
                    unplaced.push(UnplacedItem {
                        part_id: part.id.clone(),
                        instance: remaining_instance,
                        reason: "TIME_LIMIT_EXCEEDED".to_string(),
                    });
                }
                break 'instance_loop;
            }

            if !found {
                unplaced.push(UnplacedItem {
                    part_id: part.id.clone(),
                    instance,
                    reason: if stop.should_stop() {
                        "TIME_LIMIT_EXCEEDED".to_string()
                    } else {
                        "PART_NEVER_FITS_SHEET".to_string()
                    },
                });
            }
        }
    }

    PlacementResult { placed, unplaced }
}

fn collect_cavity_candidates(
    placed_polygons: &[Polygon64],
    rotated_aabb: Aabb,
    tx_min: i64,
    ty_min: i64,
    tx_max: i64,
    ty_max: i64,
) -> Vec<(i64, i64)> {
    let mut out: Vec<(i64, i64)> = Vec::new();
    let mut seen: std::collections::BTreeSet<(i64, i64)> = std::collections::BTreeSet::new();

    for placed in placed_polygons {
        let mut hole_meta: Vec<(usize, Aabb, i128)> = placed
            .holes
            .iter()
            .enumerate()
            .filter_map(|(idx, hole)| {
                if hole.is_empty() {
                    return None;
                }
                let bbox = ring_bbox(hole);
                let area = (bbox.max_x as i128 - bbox.min_x as i128)
                    * (bbox.max_y as i128 - bbox.min_y as i128);
                Some((idx, bbox, area))
            })
            .collect();

        hole_meta.sort_by(|a, b| {
            a.1.min_x
                .cmp(&b.1.min_x)
                .then(a.1.min_y.cmp(&b.1.min_y))
                .then(a.2.cmp(&b.2))
                .then(a.0.cmp(&b.0))
        });

        for (hole_idx, hole_bbox, _) in hole_meta {
            let hole = &placed.holes[hole_idx];
            for anchor in hole_anchor_points(hole, hole_bbox) {
                let tx = anchor.x - rotated_aabb.min_x;
                let ty = anchor.y - rotated_aabb.min_y;

                if tx < tx_min || tx > tx_max || ty < ty_min || ty > ty_max {
                    continue;
                }
                if seen.insert((tx, ty)) {
                    out.push((tx, ty));
                }
            }
        }
    }

    out
}

fn hole_anchor_points(hole: &[Point64], hole_bbox: Aabb) -> Vec<Point64> {
    let mut out: Vec<Point64> = Vec::new();

    // Lower-left anchor with deterministic inward nudges.
    for step in CAVITY_NUDGE_STEPS {
        out.push(Point64 {
            x: hole_bbox.min_x.saturating_add(step),
            y: hole_bbox.min_y.saturating_add(step),
        });
    }

    // Center anchor plus deterministic nudge cloud.
    let center_x = hole_bbox.min_x + ((hole_bbox.max_x - hole_bbox.min_x) / 2);
    let center_y = hole_bbox.min_y + ((hole_bbox.max_y - hole_bbox.min_y) / 2);
    out.push(Point64 {
        x: center_x,
        y: center_y,
    });
    for step in CAVITY_NUDGE_STEPS {
        for (dx, dy) in CAVITY_NUDGE_DIRS {
            out.push(Point64 {
                x: center_x.saturating_add(dx.saturating_mul(step)),
                y: center_y.saturating_add(dy.saturating_mul(step)),
            });
        }
    }

    // Vertex anchors plus deterministic nudges to avoid touching-only placements.
    for vertex in hole {
        for step in CAVITY_NUDGE_STEPS {
            for (dx, dy) in CAVITY_NUDGE_DIRS {
                out.push(Point64 {
                    x: vertex.x.saturating_add(dx.saturating_mul(step)),
                    y: vertex.y.saturating_add(dy.saturating_mul(step)),
                });
            }
        }
    }

    out
}

fn ring_bbox(ring: &[Point64]) -> Aabb {
    let first = ring[0];
    let mut min_x = first.x;
    let mut min_y = first.y;
    let mut max_x = first.x;
    let mut max_y = first.y;

    for point in &ring[1..] {
        min_x = min_x.min(point.x);
        min_y = min_y.min(point.y);
        max_x = max_x.max(point.x);
        max_y = max_y.max(point.y);
    }

    Aabb {
        min_x,
        min_y,
        max_x,
        max_y,
    }
}

fn order_parts_for_policy(
    parts: &[InflatedPartSpec],
    order_policy: PartOrderPolicy,
) -> Vec<InflatedPartSpec> {
    let mut ordered = parts.to_vec();
    if order_policy == PartOrderPolicy::ByArea {
        ordered.sort_by(|a, b| {
            b.nominal_bbox_area
                .cmp(&a.nominal_bbox_area)
                .then_with(|| a.id.cmp(&b.id))
        });
    }
    ordered
}

fn rotate_polygon(poly: &Polygon64, rotation_deg: i32) -> Polygon64 {
    Polygon64 {
        outer: poly.outer.iter().map(|p| rotate_point(*p, rotation_deg)).collect(),
        holes: poly
            .holes
            .iter()
            .map(|h| h.iter().map(|p| rotate_point(*p, rotation_deg)).collect())
            .collect(),
    }
}

pub(crate) fn rotated_inflated_aabb(inflated_polygon: &Polygon64, rotation_deg: i32) -> Aabb {
    let rotated = rotate_polygon(inflated_polygon, rotation_deg);
    aabb_from_polygon64(&rotated)
}

pub(crate) fn placed_extents_max_xy_i64(
    inflated_polygon: &Polygon64,
    rotation_deg: i32,
    tx: i64,
    ty: i64,
) -> (i64, i64) {
    let rotated_aabb = rotated_inflated_aabb(inflated_polygon, rotation_deg);
    (
        tx.saturating_add(rotated_aabb.max_x),
        ty.saturating_add(rotated_aabb.max_y),
    )
}

fn rotate_point(p: Point64, rotation_deg: i32) -> Point64 {
    let norm = normalize_deg(rotation_deg);
    match norm {
        0 => p,
        90 => Point64 { x: -p.y, y: p.x },
        180 => Point64 { x: -p.x, y: -p.y },
        270 => Point64 { x: p.y, y: -p.x },
        _ => {
            let c = COS_Q[norm] as i128;
            let s = SIN_Q[norm] as i128;
            let x = p.x as i128;
            let y = p.y as i128;
            Point64 {
                x: round_div_i128((x * c) - (y * s), TRIG_SCALE_I128),
                y: round_div_i128((x * s) + (y * c), TRIG_SCALE_I128),
            }
        }
    }
}

fn translate_polygon(poly: &Polygon64, tx: i64, ty: i64) -> Polygon64 {
    Polygon64 {
        outer: poly.outer.iter().map(|p| Point64 { x: p.x + tx, y: p.y + ty }).collect(),
        holes: poly
            .holes
            .iter()
            .map(|h| h.iter().map(|p| Point64 { x: p.x + tx, y: p.y + ty }).collect())
            .collect(),
    }
}

pub fn bbox_area(pts: &[Point64]) -> i128 {
    let first = pts[0];
    let mut min_x = first.x;
    let mut min_y = first.y;
    let mut max_x = first.x;
    let mut max_y = first.y;
    for p in &pts[1..] {
        min_x = min_x.min(p.x);
        min_y = min_y.min(p.y);
        max_x = max_x.max(p.x);
        max_y = max_y.max(p.y);
    }
    (max_x as i128 - min_x as i128) * (max_y as i128 - min_y as i128)
}

#[cfg(test)]
pub fn rect_poly(w_mm: f64, h_mm: f64) -> Polygon64 {
    Polygon64 {
        outer: vec![
            Point64 {
                x: mm_to_i64(0.0),
                y: mm_to_i64(0.0),
            },
            Point64 {
                x: mm_to_i64(w_mm),
                y: mm_to_i64(0.0),
            },
            Point64 {
                x: mm_to_i64(w_mm),
                y: mm_to_i64(h_mm),
            },
            Point64 {
                x: mm_to_i64(0.0),
                y: mm_to_i64(h_mm),
            },
        ],
        holes: Vec::new(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::multi_bin::{
        greedy::{PartInPartMode, PartOrderPolicy, PlacerKind, StopPolicy},
        greedy_multi_sheet,
    };
    use std::time::Instant;

    fn rect_with_hole_poly(
        outer_w_mm: f64,
        outer_h_mm: f64,
        hole_min_x_mm: f64,
        hole_min_y_mm: f64,
        hole_max_x_mm: f64,
        hole_max_y_mm: f64,
    ) -> Polygon64 {
        Polygon64 {
            outer: vec![
                Point64 {
                    x: mm_to_i64(0.0),
                    y: mm_to_i64(0.0),
                },
                Point64 {
                    x: mm_to_i64(outer_w_mm),
                    y: mm_to_i64(0.0),
                },
                Point64 {
                    x: mm_to_i64(outer_w_mm),
                    y: mm_to_i64(outer_h_mm),
                },
                Point64 {
                    x: mm_to_i64(0.0),
                    y: mm_to_i64(outer_h_mm),
                },
            ],
            holes: vec![vec![
                Point64 {
                    x: mm_to_i64(hole_min_x_mm),
                    y: mm_to_i64(hole_min_y_mm),
                },
                Point64 {
                    x: mm_to_i64(hole_max_x_mm),
                    y: mm_to_i64(hole_min_y_mm),
                },
                Point64 {
                    x: mm_to_i64(hole_max_x_mm),
                    y: mm_to_i64(hole_max_y_mm),
                },
                Point64 {
                    x: mm_to_i64(hole_min_x_mm),
                    y: mm_to_i64(hole_max_y_mm),
                },
            ]],
        }
    }

    fn offgrid_fixture_parts() -> Vec<InflatedPartSpec> {
        let frame_poly = rect_with_hole_poly(100.0, 100.0, 20.3, 20.4, 30.8, 31.1);
        let small_poly = rect_poly(10.2, 10.2);
        vec![
            InflatedPartSpec {
                id: "frame".to_string(),
                quantity: 1,
                allowed_rotations_deg: vec![0],
                nominal_bbox_area: bbox_area(&frame_poly.outer),
                inflated_polygon: frame_poly,
            },
            InflatedPartSpec {
                id: "small".to_string(),
                quantity: 1,
                allowed_rotations_deg: vec![0],
                nominal_bbox_area: bbox_area(&small_poly.outer),
                inflated_polygon: small_poly,
            },
        ]
    }

    #[test]
    fn basic_placement() {
        let part = InflatedPartSpec {
            id: "p".to_string(),
            quantity: 2,
            allowed_rotations_deg: vec![0],
            inflated_polygon: rect_poly(10.0, 10.0),
            nominal_bbox_area: bbox_area(&rect_poly(10.0, 10.0).outer),
        };
        let bin = rect_poly(30.0, 30.0);
        let mut stop = StopPolicy::wall_clock_for_test(30, Instant::now());
        let res = blf_place(
            &[part],
            &bin,
            1.0,
            &mut stop,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
        );
        assert_eq!(res.placed.len(), 2);
    }

    #[test]
    fn determinism() {
        let part = InflatedPartSpec {
            id: "p".to_string(),
            quantity: 3,
            allowed_rotations_deg: vec![0, 90],
            inflated_polygon: rect_poly(10.0, 8.0),
            nominal_bbox_area: bbox_area(&rect_poly(10.0, 8.0).outer),
        };
        let bin = rect_poly(40.0, 40.0);
        let mut stop_a = StopPolicy::wall_clock_for_test(30, Instant::now());
        let a = blf_place(
            &[part.clone()],
            &bin,
            1.0,
            &mut stop_a,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
        );
        let mut stop_b = StopPolicy::wall_clock_for_test(30, Instant::now());
        let b = blf_place(
            &[part],
            &bin,
            1.0,
            &mut stop_b,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
        );
        assert_eq!(a.placed, b.placed);
        assert_eq!(a.unplaced, b.unplaced);
    }

    #[test]
    fn blf_budget_stop_is_deterministic() {
        let part = InflatedPartSpec {
            id: "p".to_string(),
            quantity: 120,
            allowed_rotations_deg: vec![0, 90],
            inflated_polygon: rect_poly(10.0, 8.0),
            nominal_bbox_area: bbox_area(&rect_poly(10.0, 8.0).outer),
        };
        let bin = rect_poly(40.0, 40.0);
        let mut stop_a = StopPolicy::work_budget_for_test(30, 2_500, 1_000, Instant::now());
        let out_a = blf_place(
            &[part.clone()],
            &bin,
            1.0,
            &mut stop_a,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
        );

        let mut stop_b = StopPolicy::work_budget_for_test(30, 2_500, 1_000, Instant::now());
        let out_b = blf_place(
            &[part],
            &bin,
            1.0,
            &mut stop_b,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
        );

        assert_eq!(out_a.placed, out_b.placed);
        assert_eq!(out_a.unplaced, out_b.unplaced);
        assert!(
            out_a
                .unplaced
                .iter()
                .any(|u| u.reason == "TIME_LIMIT_EXCEEDED"),
            "work-budget test expects cutoff to happen"
        );
    }

    #[test]
    fn rotate_point_non_orthogonal_is_fixed_point_deterministic() {
        let p = Point64 {
            x: 12_345_678,
            y: -9_876_543,
        };
        let out = rotate_point(p, 17);
        assert_eq!(
            out,
            Point64 {
                x: 14_693_852,
                y: -5_835_458,
            }
        );
    }

    #[test]
    fn order_policy_by_input_order_preserves_input_order() {
        let small_poly = rect_poly(8.0, 8.0);
        let large_poly = rect_poly(20.0, 20.0);
        let medium_poly = rect_poly(15.0, 10.0);
        let parts = vec![
            InflatedPartSpec {
                id: "small".to_string(),
                quantity: 1,
                allowed_rotations_deg: vec![0],
                inflated_polygon: small_poly.clone(),
                nominal_bbox_area: bbox_area(&small_poly.outer),
            },
            InflatedPartSpec {
                id: "large".to_string(),
                quantity: 1,
                allowed_rotations_deg: vec![0],
                inflated_polygon: large_poly.clone(),
                nominal_bbox_area: bbox_area(&large_poly.outer),
            },
            InflatedPartSpec {
                id: "medium".to_string(),
                quantity: 1,
                allowed_rotations_deg: vec![0],
                inflated_polygon: medium_poly.clone(),
                nominal_bbox_area: bbox_area(&medium_poly.outer),
            },
        ];

        let by_input = order_parts_for_policy(&parts, PartOrderPolicy::ByInputOrder);
        let by_area = order_parts_for_policy(&parts, PartOrderPolicy::ByArea);

        let by_input_ids: Vec<&str> = by_input.iter().map(|p| p.id.as_str()).collect();
        let by_area_ids: Vec<&str> = by_area.iter().map(|p| p.id.as_str()).collect();

        assert_eq!(by_input_ids, vec!["small", "large", "medium"]);
        assert_eq!(by_area_ids, vec!["large", "medium", "small"]);
    }

    #[test]
    fn blf_part_in_part_off_mode_preserves_baseline() {
        let parts = vec![
            InflatedPartSpec {
                id: "a".to_string(),
                quantity: 2,
                allowed_rotations_deg: vec![0],
                inflated_polygon: rect_poly(10.0, 10.0),
                nominal_bbox_area: bbox_area(&rect_poly(10.0, 10.0).outer),
            },
            InflatedPartSpec {
                id: "b".to_string(),
                quantity: 1,
                allowed_rotations_deg: vec![0],
                inflated_polygon: rect_poly(8.0, 8.0),
                nominal_bbox_area: bbox_area(&rect_poly(8.0, 8.0).outer),
            },
        ];
        let bin = rect_poly(40.0, 20.0);
        let mut off_stop = StopPolicy::wall_clock_for_test(30, Instant::now());
        let off_out = blf_place(
            &parts,
            &bin,
            1.0,
            &mut off_stop,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
        );
        let mut auto_stop = StopPolicy::wall_clock_for_test(30, Instant::now());
        let auto_out = blf_place(
            &parts,
            &bin,
            1.0,
            &mut auto_stop,
            PartOrderPolicy::ByArea,
            PartInPartMode::Auto,
        );

        assert_eq!(off_out, auto_out);
    }

    #[test]
    fn blf_part_in_part_offgrid_hole_improves_sheet_count() {
        let parts = offgrid_fixture_parts();
        let bin = rect_poly(102.0, 102.0);

        let (off_result, _) = greedy_multi_sheet(
            &parts,
            &bin,
            1.0,
            30,
            PlacerKind::Blf,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
        );
        let (auto_result, _) = greedy_multi_sheet(
            &parts,
            &bin,
            1.0,
            30,
            PlacerKind::Blf,
            PartOrderPolicy::ByArea,
            PartInPartMode::Auto,
        );

        assert_eq!(
            off_result.sheets_used, 2,
            "off mode should miss the off-grid cavity and spill to a second sheet"
        );
        assert_eq!(
            auto_result.sheets_used, 1,
            "auto mode should place the small part into the cavity on sheet 1"
        );
    }

    #[test]
    fn blf_part_in_part_hole_collapsed_like_outer_only_source_is_ignored() {
        let frame_outer_only = rect_poly(100.0, 100.0);
        let small = rect_poly(10.2, 10.2);
        let parts = vec![
            InflatedPartSpec {
                id: "outer_only".to_string(),
                quantity: 1,
                allowed_rotations_deg: vec![0],
                nominal_bbox_area: bbox_area(&frame_outer_only.outer),
                inflated_polygon: frame_outer_only,
            },
            InflatedPartSpec {
                id: "small".to_string(),
                quantity: 1,
                allowed_rotations_deg: vec![0],
                nominal_bbox_area: bbox_area(&small.outer),
                inflated_polygon: small,
            },
        ];
        let bin = rect_poly(102.0, 102.0);

        let (off_result, _) = greedy_multi_sheet(
            &parts,
            &bin,
            1.0,
            30,
            PlacerKind::Blf,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
        );
        let (auto_result, _) = greedy_multi_sheet(
            &parts,
            &bin,
            1.0,
            30,
            PlacerKind::Blf,
            PartOrderPolicy::ByArea,
            PartInPartMode::Auto,
        );

        assert_eq!(off_result, auto_result);
        assert_eq!(
            auto_result.sheets_used, 2,
            "outer-only placed source (hole-collapsed-like) must not create cavity candidates"
        );
    }
}
