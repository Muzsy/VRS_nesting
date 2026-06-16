use super::*;

/// Pick a fitting seed rotation under which the part fits at least one sheet (rotation-aware:
/// parts that only fit rotated — e.g. a strip wider than the sheet at 0° — get a fitting rotation
/// instead of being dropped).
///
/// SGH-Q48 T5: a **continuous-rotation** part gets a **continuous** seed — the bbox-min-width
/// orientation that fits, found by a fine continuous scan (NOT snapped to a fixed discrete grid;
/// the downstream coord-descent keeps refining the rotation continuously). Discrete / legacy parts
/// are unchanged (first fitting allowed rotation).
pub(crate) fn fitting_rotation(inst: &SPInstance, sheets: &[SheetShape]) -> f64 {
    if inst.continuous_rotation {
        // Fine continuous scan: the smallest-bbox-width orientation that fits some sheet.
        let mut best: Option<(f64, f64)> = None; // (bbox_width, rotation)
        let mut a = 0.0_f64;
        while a < 180.0 {
            let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, a);
            let fits = sheets
                .iter()
                .any(|s| rw <= s.width + 1e-9 && rh <= s.height + 1e-9);
            if fits && best.as_ref().is_none_or(|(bw, _)| rw < *bw) {
                best = Some((rw, a));
            }
            a += 0.5;
        }
        return best.map(|(_, rot)| rot).unwrap_or(0.0);
    }
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

/// Build the initial constructive seed layout for the optimizer.
///
/// The clear placements come from the upstream-style [`LBFBuilder`]
/// (`search_placement` + `LBFEvaluator`, clear-only). Instances LBF could not
/// place clear (no collision-free position on any fixed sheet) are then handed to
/// [`fixed_sheet_separator_bootstrap`], the explicitly-named fixed-sheet
/// adaptation that seeds an in-bounds starting position so the separator (which
/// only moves already-placed items) can resolve them. This bootstrap lives
/// outside `LBFBuilder` and is never reported as LBF constructive success.
pub fn build_native_constructive_seed(problem: &SparrowProblem) -> SparrowLayout {
    let built = LBFBuilder::new(problem).construct();
    let mut layout = built.layout;
    if !built.unresolved.is_empty() {
        fixed_sheet_separator_bootstrap(problem, &mut layout, &built.unresolved);
    }
    layout.placements.sort_by_key(|p| p.instance_idx);
    layout
}

/// Fixed-sheet separator bootstrap — NOT upstream LBF parity.
///
/// Upstream guarantees every item a clear placement by widening the strip; on
/// fixed sheets that lever does not exist, so each instance LBF left unresolved
/// gets a deterministic in-bounds starting position here. These seeds are
/// deliberately allowed to be infeasible (overlapping); the separator resolves
/// them. This keeps every placeable instance in the layout without pretending the
/// infeasible seed was a constructive success.
fn fixed_sheet_separator_bootstrap(
    problem: &SparrowProblem,
    layout: &mut SparrowLayout,
    unresolved: &[usize],
) {
    let sheets = &problem.container.sheets;
    if sheets.is_empty() {
        return;
    }
    let mut rng = DeterministicRng::new(problem.config.seed ^ 0x5EED_F00D_1234_5678);
    for &instance_idx in unresolved {
        let inst = &problem.instances[instance_idx];
        let rot = fitting_rotation(inst, sheets);
        let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, rot);
        let Some((sheet_idx, sheet)) = sheets
            .iter()
            .enumerate()
            .find(|(_, s)| rw <= s.width + 1e-9 && rh <= s.height + 1e-9)
        else {
            continue;
        };
        let max_rmx = (sheet.max_x - rw).max(sheet.min_x);
        let max_rmy = (sheet.max_y - rh).max(sheet.min_y);
        let rmx = sheet.min_x + rng.next_f64() * (max_rmx - sheet.min_x).max(0.0);
        let rmy = sheet.min_y + rng.next_f64() * (max_rmy - sheet.min_y).max(0.0);
        let (ax, ay) =
            placement_anchor_from_rect_min(rmx, rmy, inst.part.width, inst.part.height, rot);
        layout.placements.push(SparrowPlacement {
            instance_idx,
            sheet_index: sheet_idx,
            x: ax,
            y: ay,
            rotation_deg: rot,
        });
    }
}
