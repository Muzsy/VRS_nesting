use serde::Deserialize;

use crate::geometry::EPS;
use crate::sheet::SheetShape;

#[derive(Debug, Deserialize, Clone)]
pub struct Part {
    pub id: String,
    pub width: f64,
    pub height: f64,
    pub quantity: i64,
    #[serde(default)]
    pub allowed_rotations_deg: Vec<i64>,
}

#[derive(Debug)]
pub struct Instance {
    pub instance_id: String,
    pub part_id: String,
    pub width: f64,
    pub height: f64,
    pub allowed_rotations_deg: Vec<i64>,
}

pub fn normalize_allowed_rotations(raw: &[i64]) -> Result<Vec<i64>, String> {
    if raw.is_empty() {
        return Err("part.allowed_rotations_deg must be non-empty".to_string());
    }

    let mut out = Vec::new();
    for r in raw {
        let rot = r.rem_euclid(360);
        if !matches!(rot, 0 | 90 | 180 | 270) {
            return Err(format!(
                "unsupported rotation in allowed_rotations_deg: {r} (normalized: {rot})"
            ));
        }
        if !out.contains(&rot) {
            out.push(rot);
        }
    }
    Ok(out)
}

pub fn dims_for_rotation(width: f64, height: f64, rot: i64) -> Option<(f64, f64)> {
    match rot.rem_euclid(360) {
        0 | 180 => Some((width, height)),
        90 | 270 => Some((height, width)),
        _ => None,
    }
}

pub fn rotated_bbox_min_offset(width: f64, height: f64, rot: i64) -> Option<(f64, f64)> {
    match rot.rem_euclid(360) {
        0 => Some((0.0, 0.0)),
        90 => Some((-height, 0.0)),
        180 => Some((-width, -height)),
        270 => Some((0.0, -width)),
        _ => None,
    }
}

pub fn placement_anchor_from_rect_min(
    rect_min_x: f64,
    rect_min_y: f64,
    width: f64,
    height: f64,
    rot: i64,
) -> Option<(f64, f64)> {
    let (bbox_min_x, bbox_min_y) = rotated_bbox_min_offset(width, height, rot)?;
    Some((rect_min_x - bbox_min_x, rect_min_y - bbox_min_y))
}

pub fn can_fit_any_stock(part: &Part, sheets: &[SheetShape]) -> Result<bool, String> {
    let allowed_rotations = normalize_allowed_rotations(&part.allowed_rotations_deg)?;
    for sheet in sheets {
        for rot in &allowed_rotations {
            let Some((w, h)) = dims_for_rotation(part.width, part.height, *rot) else {
                continue;
            };
            if w <= sheet.width + EPS && h <= sheet.height + EPS {
                return Ok(true);
            }
        }
    }
    Ok(false)
}

pub fn expand_instances(parts: &[Part]) -> Result<Vec<Instance>, String> {
    let mut instances = Vec::new();
    for part in parts {
        let allowed_rotations = normalize_allowed_rotations(&part.allowed_rotations_deg)?;
        for idx in 0..part.quantity {
            instances.push(Instance {
                instance_id: format!("{}__{:04}", part.id, idx + 1),
                part_id: part.id.clone(),
                width: part.width,
                height: part.height,
                allowed_rotations_deg: allowed_rotations.clone(),
            });
        }
    }
    instances.sort_by(|a, b| a.instance_id.cmp(&b.instance_id));
    Ok(instances)
}

#[cfg(test)]
mod tests {
    use super::{dims_for_rotation, placement_anchor_from_rect_min, rotated_bbox_min_offset};

    fn approx_eq(a: f64, b: f64) -> bool {
        (a - b).abs() <= 1e-9
    }

    #[test]
    fn rotated_bbox_min_offset_matches_expected_quadrants() {
        let width = 1000.0;
        let height = 2000.0;
        let expected = [
            (0, (0.0, 0.0)),
            (90, (-2000.0, 0.0)),
            (180, (-1000.0, -2000.0)),
            (270, (0.0, -1000.0)),
        ];

        for (rot, (exp_x, exp_y)) in expected {
            let (x, y) = rotated_bbox_min_offset(width, height, rot).expect("supported rotation");
            assert!(approx_eq(x, exp_x), "rot={rot} min_x={x} expected={exp_x}");
            assert!(approx_eq(y, exp_y), "rot={rot} min_y={y} expected={exp_y}");
        }
    }

    #[test]
    fn placement_anchor_from_rect_min_keeps_rotated_bbox_inside_target_rect() {
        let width = 1000.0;
        let height = 2000.0;
        let rect_min_x = 0.0;
        let rect_min_y = 480.0;

        for rot in [0, 90, 180, 270] {
            let (anchor_x, anchor_y) =
                placement_anchor_from_rect_min(rect_min_x, rect_min_y, width, height, rot)
                    .expect("supported rotation");
            let (min_off_x, min_off_y) =
                rotated_bbox_min_offset(width, height, rot).expect("supported rotation");
            let Some((rw, rh)) = dims_for_rotation(width, height, rot) else {
                panic!("unsupported rotation in test");
            };

            let placed_min_x = anchor_x + min_off_x;
            let placed_min_y = anchor_y + min_off_y;
            let placed_max_x = placed_min_x + rw;
            let placed_max_y = placed_min_y + rh;

            assert!(
                approx_eq(placed_min_x, rect_min_x),
                "rot={rot} placed_min_x={placed_min_x} rect_min_x={rect_min_x}"
            );
            assert!(
                approx_eq(placed_min_y, rect_min_y),
                "rot={rot} placed_min_y={placed_min_y} rect_min_y={rect_min_y}"
            );
            assert!(
                approx_eq(placed_max_x, rect_min_x + rw),
                "rot={rot} placed_max_x={placed_max_x} expected={}",
                rect_min_x + rw
            );
            assert!(
                approx_eq(placed_max_y, rect_min_y + rh),
                "rot={rot} placed_max_y={placed_max_y} expected={}",
                rect_min_y + rh
            );
        }
    }
}
