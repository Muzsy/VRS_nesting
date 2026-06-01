use super::*;

/// Pick the first allowed rotation under which the part fits at least one sheet
/// (rotation-aware: parts that only fit rotated — e.g. a strip wider than the
/// sheet at 0° — get a fitting rotation instead of being dropped).
pub(crate) fn fitting_rotation(inst: &SPInstance, sheets: &[SheetShape]) -> f64 {
    let rots: Vec<f64> = if inst.allowed_rotations_deg.is_empty() {
        vec![0.0]
    } else {
        inst.allowed_rotations_deg.clone()
    };
    for &rot in &rots {
        let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, rot);
        if sheets
            .iter()
            .any(|s| rw <= s.width + 1e-9 && rh <= s.height + 1e-9)
        {
            return rot;
        }
    }
    rots[0]
}

pub(crate) fn rect_min_from_anchor(
    x: f64,
    y: f64,
    width: f64,
    height: f64,
    rot_deg: f64,
) -> (f64, f64) {
    let (ox, oy) = rotated_bbox_min_offset(width, height, rot_deg);
    (x + ox, y + oy)
}
