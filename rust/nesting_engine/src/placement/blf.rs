use std::time::Instant;

use crate::feasibility::{
    aabb::aabb_from_polygon64,
    can_place, PlacedPart,
    narrow::PlacedIndex,
};
use crate::geometry::{
    scale::{i64_to_mm, mm_to_i64},
    trig_lut::{round_div_i128, normalize_deg, COS_Q, SIN_Q, TRIG_SCALE_I128},
    types::{Point64, Polygon64},
};

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
    time_limit_sec: u64,
    started_at: Instant,
) -> PlacementResult {
    let mut ordered = parts.to_vec();
    ordered.sort_by(|a, b| {
        b.nominal_bbox_area
            .cmp(&a.nominal_bbox_area)
            .then_with(|| a.id.cmp(&b.id))
    });

    let step = mm_to_i64(if grid_step_mm <= 0.0 { 1.0 } else { grid_step_mm }).max(1);
    let bin_aabb = aabb_from_polygon64(bin_polygon);
    let mut placed_state = PlacedIndex::new();
    let mut placed: Vec<PlacedItem> = Vec::new();
    let mut unplaced: Vec<UnplacedItem> = Vec::new();

    for part in &ordered {
        for instance in 0..part.quantity {
            if started_at.elapsed().as_secs() >= time_limit_sec {
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

            let mut ty = global_ty_min;
            while ty <= global_ty_max && !found {
                let mut tx = global_tx_min;
                while tx <= global_tx_max && !found {
                    for (rotation, rotated, rotated_aabb) in &rotation_candidates {
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
                                inflated_polygon: candidate,
                                aabb: candidate_aabb,
                            });
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
                    tx = tx.saturating_add(step);
                }
                ty = ty.saturating_add(step);
            }

            if !found {
                unplaced.push(UnplacedItem {
                    part_id: part.id.clone(),
                    instance,
                    reason: if started_at.elapsed().as_secs() >= time_limit_sec {
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
        let res = blf_place(&[part], &bin, 1.0, 30, Instant::now());
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
        let a = blf_place(&[part.clone()], &bin, 1.0, 30, Instant::now());
        let b = blf_place(&[part], &bin, 1.0, 30, Instant::now());
        assert_eq!(a.placed, b.placed);
        assert_eq!(a.unplaced, b.unplaced);
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
}
