use super::*;

// Explore pool/restore/disrupt logic mapped from upstream optimizer/explore.rs.
impl SparrowOptimizer {
    pub(super) fn disrupt(
        &self,
        state: &mut SparrowState,
        instances: &[SPInstance],
        sheets: &[SheetShape],
        rng: &mut DeterministicRng,
        diag: &mut SparrowDiagnostics,
    ) {
        let n = state.layout.placements.len();
        if n < 2 {
            return;
        }
        // (a) swap the two largest-area items.
        let mut by_area: Vec<(usize, f64)> = (0..n)
            .map(|i| {
                let inst = &instances[state.layout.placements[i].instance_idx];
                (i, inst.part.width * inst.part.height)
            })
            .collect();
        by_area.sort_by(|a, b| {
            b.1.partial_cmp(&a.1)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then(a.0.cmp(&b.0))
        });
        let (i, j) = (by_area[0].0, by_area[1].0);
        let pi = state.layout.placements[i].clone();
        let pj = state.layout.placements[j].clone();
        state.layout.placements[i].x = pj.x;
        state.layout.placements[i].y = pj.y;
        state.layout.placements[i].sheet_index = pj.sheet_index;
        state.layout.placements[j].x = pi.x;
        state.layout.placements[j].y = pi.y;
        state.layout.placements[j].sheet_index = pi.sheet_index;
        state
            .tracker
            .update_after_move(i, &state.layout, instances, sheets, diag);
        state
            .tracker
            .update_after_move(j, &state.layout, instances, sheets, diag);
        diag.exploration_disruptions_large_item_swap += 1;

        // (b) move the highest-loss item to a (different) eligible sheet at a
        //     randomized in-bounds anchor — escapes a saturated sheet.
        if sheets.len() > 1 {
            let worst = state.tracker.colliding_indices().into_iter().next();
            if let Some(w) = worst {
                let inst = &instances[state.layout.placements[w].instance_idx];
                let cur_sheet = state.layout.placements[w].sheet_index;
                let target_sheet = (cur_sheet + 1) % sheets.len();
                let rot = fitting_rotation(inst, sheets);
                let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, rot);
                let sh = &sheets[target_sheet];
                if rw <= sh.width + 1e-9 && rh <= sh.height + 1e-9 {
                    let max_rmx = (sh.width - rw).max(0.0);
                    let max_rmy = (sh.height - rh).max(0.0);
                    let rmx = sh.min_x + rng.next_f64() * max_rmx;
                    let rmy = sh.min_y + rng.next_f64() * max_rmy;
                    let (ax, ay) = placement_anchor_from_rect_min(
                        rmx,
                        rmy,
                        inst.part.width,
                        inst.part.height,
                        rot,
                    );
                    state.layout.placements[w] = SparrowPlacement {
                        instance_idx: inst.idx,
                        sheet_index: target_sheet,
                        x: ax,
                        y: ay,
                        rotation_deg: rot,
                    };
                    state
                        .tracker
                        .update_after_move(w, &state.layout, instances, sheets, diag);
                    diag.exploration_disruptions_cross_sheet += 1;
                }
            }
        }

        // (c) rotation kick: rotate the highest-loss item to an alternate allowed
        //     rotation in place (different footprint can break a deadlock).
        if let Some(w) = state.tracker.colliding_indices().into_iter().next() {
            let inst = &instances[state.layout.placements[w].instance_idx];
            if inst.allowed_rotations_deg.len() > 1 {
                let cur_rot = state.layout.placements[w].rotation_deg;
                let alt: Vec<f64> = inst
                    .allowed_rotations_deg
                    .iter()
                    .copied()
                    .filter(|r| (r - cur_rot).abs() > 1e-9)
                    .collect();
                if !alt.is_empty() {
                    let pick = alt[(rng.next_u64() as usize) % alt.len()];
                    let sheet_idx = state.layout.placements[w].sheet_index;
                    let sh = &sheets[sheet_idx];
                    let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, pick);
                    if rw <= sh.width + 1e-9 && rh <= sh.height + 1e-9 {
                        let rmx = state.layout.placements[w].x.clamp(sh.min_x, sh.max_x - rw);
                        let rmy = state.layout.placements[w].y.clamp(sh.min_y, sh.max_y - rh);
                        let (ax, ay) = placement_anchor_from_rect_min(
                            rmx,
                            rmy,
                            inst.part.width,
                            inst.part.height,
                            pick,
                        );
                        state.layout.placements[w] = SparrowPlacement {
                            instance_idx: inst.idx,
                            sheet_index: sheet_idx,
                            x: ax,
                            y: ay,
                            rotation_deg: pick,
                        };
                        state
                            .tracker
                            .update_after_move(w, &state.layout, instances, sheets, diag);
                        diag.exploration_disruptions_rotation += 1;
                    }
                }
            }
        }
    }
}
