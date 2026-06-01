use super::*;

pub(crate) fn build_sheet_session(
    target: usize,
    sheet_idx: usize,
    layout: &SparrowLayout,
    tracker: &SparrowCollisionTracker,
    sheet_shape: &CdePreparedShape,
) -> Option<CdeCandidateSession> {
    let others: Vec<(usize, Rc<CdePreparedShape>)> = (0..layout.placements.len())
        .filter(|&j| j != target && layout.placements[j].sheet_index == sheet_idx)
        .filter_map(|j| tracker.shapes[j].clone().map(|s| (j, s)))
        .collect();
    CdeCandidateSession::build(others, sheet_shape)
}

/// Native CDE-backed search for a clear (or least-colliding) placement of the
/// target instance across EVERY eligible sheet, all allowed rotations, with
/// focused, global-grid and coordinate-descent candidates, scored by the
/// `SeparationEvaluator` (upstream overlap-proxy quantification × tracker GLS
/// weights) — Sparrow Algorithm 6.
#[allow(clippy::too_many_arguments)]
pub(crate) fn native_search_placement(
    target: usize,
    layout: &SparrowLayout,
    instances: &[SPInstance],
    tracker: &SparrowCollisionTracker,
    sheets: &[SheetShape],
    cfg: &SparrowConfig,
    rng: &mut DeterministicRng,
    started: &Instant,
    deadline: f64,
    diag: &mut SparrowDiagnostics,
) -> Option<SparrowPlacement> {
    diag.search_position_calls += 1;
    let deadline_reached =
        |started: &Instant, deadline: f64| started.elapsed().as_secs_f64() >= deadline;
    let cur = &layout.placements[target];
    let inst = &instances[cur.instance_idx];
    let rotations: Vec<f64> = if inst.allowed_rotations_deg.is_empty() {
        vec![cur.rotation_deg]
    } else {
        inst.allowed_rotations_deg.clone()
    };

    let fixed_shapes = tracker.shapes.clone();

    let mut best_samples =
        BestSamples::new(8, inst.part.width.min(inst.part.height).max(1.0) * 0.10);

    // Sheet search order: current sheet first, then the rest (cross-sheet).
    let mut sheet_order: Vec<usize> = vec![cur.sheet_index];
    for sheet_idx in 0..sheets.len() {
        if sheet_idx != cur.sheet_index {
            sheet_order.push(sheet_idx);
        }
    }

    let candidate_pool = sheet_order;
    for (rank, &sheet_idx) in candidate_pool.iter().enumerate() {
        if deadline_reached(started, deadline) {
            break;
        }
        if rank > 0 {
            diag.search_cross_sheet_calls += 1;
        }
        let sheet = &sheets[sheet_idx];
        let Some(sheet_shape) = tracker.sheet_shapes.get(sheet_idx).and_then(|s| s.clone()) else {
            continue;
        };
        let Some(session) = build_sheet_session(target, sheet_idx, layout, tracker, &sheet_shape)
        else {
            continue;
        };
        let mut evaluator = SeparationEvaluator {
            target,
            inst,
            sheet,
            sheet_idx,
            sheet_shape: &sheet_shape,
            session: &session,
            fixed_shapes: &fixed_shapes,
            tracker,
            n_evals: 0,
        };
        let sampler = UniformBBoxSampler::new(sheet, inst);

        // Focused samples around the current placement (only on the current sheet).
        if sheet_idx == cur.sheet_index {
            let span = (sheet.width.min(sheet.height)) * 0.15;
            for &rot in &rotations {
                if deadline_reached(started, deadline) {
                    break;
                }
                if let Some(c) = evaluator.evaluate_sample(
                    cur.x,
                    cur.y,
                    rot,
                    Some(best_samples.upper_bound()),
                    diag,
                ) {
                    best_samples.report(c);
                }
                for _ in 0..cfg.focused_samples {
                    if deadline_reached(started, deadline) {
                        break;
                    }
                    let nx = cur.x + rng.jitter(span);
                    let ny = cur.y + rng.jitter(span);
                    diag.search_focused_samples += 1;
                    if let Some(c) = evaluator.evaluate_sample(
                        nx,
                        ny,
                        rot,
                        Some(best_samples.upper_bound()),
                        diag,
                    ) {
                        best_samples.report(c);
                    }
                    if best_samples
                        .best()
                        .as_ref()
                        .map(|b| b.is_clear && b.placement.sheet_index == sheet_idx)
                        .unwrap_or(false)
                    {
                        break;
                    }
                }
            }
        }

        // Coarse global grid on this sheet, every rotation.
        for &rot in &rotations {
            for (rmx, rmy) in sampler.samples_for(rot, cfg.global_grid_n, rng) {
                if deadline_reached(started, deadline) {
                    break;
                }
                diag.search_global_samples += 1;
                if let Some(c) =
                    evaluator.evaluate_sample(rmx, rmy, rot, Some(best_samples.upper_bound()), diag)
                {
                    best_samples.report(c);
                }
            }
        }

        // Two-stage coordinate descent: pre-refine retained best samples, then
        // final-refine the current best. This mirrors Sparrow Algorithm 6.
        let wiggle = inst.continuous_rotation;
        let item_min_dim = inst.part.width.min(inst.part.height);
        let starts = best_samples.samples.clone();
        for s in starts {
            if deadline_reached(started, deadline) {
                break;
            }
            if let Some(desc) = refine_coord_desc(
                s,
                &mut evaluator,
                item_min_dim,
                cfg,
                rng,
                diag,
                false,
                wiggle,
                cfg.rotation_wiggle_deg,
            ) {
                best_samples.report(desc);
            }
        }
        if let Some(s) = best_samples.best() {
            if !deadline_reached(started, deadline) {
                if let Some(desc) = refine_coord_desc(
                    s,
                    &mut evaluator,
                    item_min_dim,
                    cfg,
                    rng,
                    diag,
                    true,
                    wiggle,
                    cfg.rotation_wiggle_deg,
                ) {
                    best_samples.report(desc);
                }
            }
        }
    }

    let best = best_samples.best();
    if let Some(b) = &best {
        if b.collision_loss < diag.search_best_eval || diag.search_best_eval == 0.0 {
            diag.search_best_eval = b.collision_loss;
        }
    }
    best.map(|b| b.placement)
}
