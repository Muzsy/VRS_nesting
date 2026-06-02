use super::*;

// Explore pool/restore/disrupt logic mapped from upstream optimizer/explore.rs.
impl SparrowOptimizer {
    /// Upstream `exploration_phase` (Algorithm 12), adapted to fixed sheets.
    ///
    /// Upstream alternates separation with strip-width shrinking; on fixed sheets
    /// the strip cannot shrink, so this drives repeated separation attempts and,
    /// on each failure, maintains an infeasible-solution pool ordered by total
    /// raw loss, performs a biased restore from the better half of that pool, and
    /// disrupts the restored layout before retrying. Returns `true` as soon as a
    /// fully separated (feasible) layout is found.
    #[allow(clippy::too_many_arguments)]
    pub(super) fn exploration_phase(
        &self,
        state: &mut SparrowState,
        instances: &[SPInstance],
        sheets: &[SheetShape],
        started: &Instant,
        deadline: f64,
        rng: &mut DeterministicRng,
        diag: &mut SparrowDiagnostics,
    ) -> bool {
        let max_attempts = SPARROW_PARITY_MAX_CONSEC_FAILED_ATTEMPTS;
        // Infeasible-solution pool, kept sorted ascending by total raw loss so the
        // better (lower-loss) solutions are at the front for the biased restore.
        let mut infeas_sol_pool: Vec<(f64, SparrowLayout)> = Vec::new();

        for _attempt in 0..max_attempts {
            if started.elapsed().as_secs_f64() >= deadline {
                break;
            }
            diag.exploration_attempts += 1;
            if self.separate(state, instances, sheets, started, deadline, rng, diag) {
                return true;
            }
            // Separation failed: pool the least-infeasible state, biased-restore one
            // from the better half, disrupt it, and retry.
            let raw = state.tracker.total_raw_loss();
            let at = infeas_sol_pool
                .binary_search_by(|(l, _)| {
                    l.partial_cmp(&raw).unwrap_or(std::cmp::Ordering::Equal)
                })
                .unwrap_or_else(|e| e);
            infeas_sol_pool.insert(at, (raw, state.layout.snapshot()));
            infeas_sol_pool.truncate(8);
            diag.exploration_pool_inserts += 1;
            if !infeas_sol_pool.is_empty() {
                let sel = self.select_biased_pool_index(infeas_sol_pool.len(), rng);
                let restored = infeas_sol_pool[sel].1.snapshot();
                diag.exploration_pool_restores += 1;
                *state = SparrowState::new_with_diag(restored, instances, sheets, diag);
                self.disrupt(state, instances, sheets, rng, diag);
            }
        }
        false
    }

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
        let Some((i, j)) = self.select_large_item_swap_pair(state, instances, rng) else {
            return;
        };
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

        self.relocate_practically_contained_items(state, instances, sheets, i, Some(j), &pi, diag);
        self.relocate_practically_contained_items(state, instances, sheets, j, Some(i), &pj, diag);

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

    pub(super) fn select_biased_pool_index(
        &self,
        pool_len: usize,
        rng: &mut DeterministicRng,
    ) -> usize {
        if pool_len == 0 {
            return 0;
        }
        let sample = normal_abs_sample(rng, SPARROW_PARITY_SOLUTION_POOL_STDDEV).min(0.999);
        (sample * pool_len as f64) as usize
    }

    pub(super) fn select_large_item_swap_pair(
        &self,
        state: &SparrowState,
        instances: &[SPInstance],
        rng: &mut DeterministicRng,
    ) -> Option<(usize, usize)> {
        let n = state.layout.placements.len();
        if n < 2 {
            return None;
        }
        let total_area: f64 = state
            .layout
            .placements
            .iter()
            .map(|p| {
                let inst = &instances[p.instance_idx];
                inst.part.width * inst.part.height
            })
            .sum();
        let cutoff_target =
            total_area * SPARROW_PARITY_LARGE_ITEM_CH_AREA_CUTOFF_PERCENTILE;
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
        let mut cumulative = 0.0;
        let mut cutoff = 0.0;
        for (_, area) in &by_area {
            cumulative += *area;
            if cumulative > cutoff_target {
                cutoff = *area;
                break;
            }
        }
        let large: Vec<usize> = by_area
            .iter()
            .filter(|(_, area)| *area >= cutoff)
            .map(|(idx, _)| *idx)
            .collect();
        let pool = if large.len() >= 3 {
            large
        } else {
            (0..n).collect()
        };
        let first_pos = (rng.next_u64() as usize) % pool.len();
        let first = pool[first_pos];
        let mut second_candidates: Vec<usize> =
            pool.iter().copied().filter(|idx| *idx != first).collect();
        if second_candidates.is_empty() {
            second_candidates = (0..n).filter(|idx| *idx != first).collect();
        }
        let second = second_candidates[(rng.next_u64() as usize) % second_candidates.len()];
        Some((first, second))
    }

    fn relocate_practically_contained_items(
        &self,
        state: &mut SparrowState,
        instances: &[SPInstance],
        sheets: &[SheetShape],
        moved_idx: usize,
        excluded_idx: Option<usize>,
        opened_space: &SparrowPlacement,
        diag: &mut SparrowDiagnostics,
    ) {
        let contained = self.practically_contained_items(
            &state.layout,
            instances,
            moved_idx,
            excluded_idx,
            diag,
        );
        if contained.is_empty() {
            return;
        }
        let moved_now = state.layout.placements[moved_idx].clone();
        let dx = opened_space.x - moved_now.x;
        let dy = opened_space.y - moved_now.y;
        for idx in contained {
            let current = state.layout.placements[idx].clone();
            let inst = &instances[current.instance_idx];
            let relocated = closest_fixed_sheet_transform(
                inst,
                &current,
                opened_space.sheet_index,
                current.x + dx,
                current.y + dy,
                current.rotation_deg,
                sheets,
            );
            if relocated.sheet_index != current.sheet_index {
                diag.exploration_disruptions_cross_sheet += 1;
            }
            if (relocated.rotation_deg - current.rotation_deg).abs() > 1e-9 {
                diag.exploration_disruptions_rotation += 1;
            }
            state.layout.placements[idx] = relocated;
            state
                .tracker
                .update_after_move(idx, &state.layout, instances, sheets, diag);
        }
    }

    fn practically_contained_items(
        &self,
        layout: &SparrowLayout,
        instances: &[SPInstance],
        moved_idx: usize,
        excluded_idx: Option<usize>,
        diag: &mut SparrowDiagnostics,
    ) -> Vec<usize> {
        let moved = &layout.placements[moved_idx];
        let moved_inst = &instances[moved.instance_idx];
        let Ok(moved_shape) =
            prepare_shape_native(&moved_inst.part, moved.x, moved.y, moved.rotation_deg)
        else {
            diag.unsupported_queries += 1;
            return Vec::new();
        };
        let adapter = CdeAdapter::with_sparrow_strict();
        let mut out = Vec::new();
        for (idx, placement) in layout.placements.iter().enumerate() {
            if idx == moved_idx
                || Some(idx) == excluded_idx
                || placement.sheet_index != moved.sheet_index
            {
                continue;
            }
            let inst = &instances[placement.instance_idx];
            let Ok(shape) =
                prepare_shape_native(&inst.part, placement.x, placement.y, placement.rotation_deg)
            else {
                diag.unsupported_queries += 1;
                continue;
            };
            match adapter.query_pair(&moved_shape, &shape) {
                CdeQueryResult::Collision => {
                    let center = Point {
                        x: (shape.min_x + shape.max_x) * 0.5,
                        y: (shape.min_y + shape.max_y) * 0.5,
                    };
                    if point_inside_or_on_polygon(center, &moved_shape.world_pts) {
                        out.push(idx);
                    }
                }
                CdeQueryResult::NoCollision => {}
                CdeQueryResult::Unsupported { .. } => diag.unsupported_queries += 1,
            }
        }
        out
    }
}

fn closest_fixed_sheet_transform(
    inst: &SPInstance,
    current: &SparrowPlacement,
    preferred_sheet: usize,
    x: f64,
    y: f64,
    rotation_deg: f64,
    sheets: &[SheetShape],
) -> SparrowPlacement {
    let mut sheet_index = preferred_sheet.min(sheets.len().saturating_sub(1));
    let mut rot = rotation_deg;
    if !fits_sheet(inst, &sheets[sheet_index], rot) {
        rot = fitting_rotation(inst, sheets);
        if !fits_sheet(inst, &sheets[sheet_index], rot) {
            if let Some((idx, _)) = sheets
                .iter()
                .enumerate()
                .find(|(_, sheet)| fits_sheet(inst, sheet, rot))
            {
                sheet_index = idx;
            } else {
                sheet_index = current.sheet_index;
                rot = current.rotation_deg;
            }
        }
    }
    let sheet = &sheets[sheet_index];
    let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, rot);
    let (rmx, rmy) = rect_min_from_anchor(x, y, inst.part.width, inst.part.height, rot);
    let clamped_x = rmx.clamp(sheet.min_x, (sheet.max_x - rw).max(sheet.min_x));
    let clamped_y = rmy.clamp(sheet.min_y, (sheet.max_y - rh).max(sheet.min_y));
    let (ax, ay) = placement_anchor_from_rect_min(
        clamped_x,
        clamped_y,
        inst.part.width,
        inst.part.height,
        rot,
    );
    SparrowPlacement {
        instance_idx: current.instance_idx,
        sheet_index,
        x: ax,
        y: ay,
        rotation_deg: rot,
    }
}

fn normal_abs_sample(rng: &mut DeterministicRng, stddev: f64) -> f64 {
    let u1 = rng.next_f64().clamp(f64::MIN_POSITIVE, 1.0);
    let u2 = rng.next_f64();
    let z0 = (-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos();
    (z0 * stddev).abs()
}

fn fits_sheet(inst: &SPInstance, sheet: &SheetShape, rot: f64) -> bool {
    let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, rot);
    rw <= sheet.width + 1e-9 && rh <= sheet.height + 1e-9
}

fn point_inside_or_on_polygon(p: Point, poly: &[Point]) -> bool {
    if poly.len() < 3 {
        return false;
    }
    if (0..poly.len()).any(|i| point_on_segment(p, poly[i], poly[(i + 1) % poly.len()])) {
        return true;
    }
    let mut inside = false;
    let mut j = poly.len() - 1;
    for i in 0..poly.len() {
        let a = poly[i];
        let b = poly[j];
        let crosses = (a.y > p.y) != (b.y > p.y);
        if crosses {
            let x_intersect = (b.x - a.x) * (p.y - a.y) / (b.y - a.y) + a.x;
            if p.x < x_intersect {
                inside = !inside;
            }
        }
        j = i;
    }
    inside
}

fn point_on_segment(p: Point, a: Point, b: Point) -> bool {
    let cross = (p.y - a.y) * (b.x - a.x) - (p.x - a.x) * (b.y - a.y);
    if cross.abs() > 1e-7 {
        return false;
    }
    let dot = (p.x - a.x) * (b.x - a.x) + (p.y - a.y) * (b.y - a.y);
    if dot < -1e-7 {
        return false;
    }
    let len2 = (b.x - a.x).powi(2) + (b.y - a.y).powi(2);
    dot <= len2 + 1e-7
}
