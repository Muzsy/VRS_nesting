use super::*;

/// If two samples are closer than this ratio of the item's min dimension they are
/// considered duplicates (upstream `UNIQUE_SAMPLE_THRESHOLD`).
pub(crate) const UNIQUE_SAMPLE_THRESHOLD: f64 = 0.05;

/// Sample budget for one `search_placement` call (upstream `SampleConfig`).
#[derive(Clone, Copy)]
pub(crate) struct SampleConfig {
    /// Focused samples around the reference/current placement.
    pub n_focused_samples: usize,
    /// Container-wide samples across the sheet.
    pub n_container_samples: usize,
    /// Number of best samples retained / first-refined (`BestSamples` size).
    pub n_coord_descents: usize,
}

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

/// Upstream `search_placement` (Algorithm 6 and Figure 7), run for one
/// sheet/evaluator. Generic over the evaluator so both the LBF builder
/// (`LBFEvaluator`, clear-only) and the separator (`SeparationEvaluator`) share
/// the exact same sampler + refinement logic.
///
/// Steps, exactly upstream:
/// 1. report the reference/current placement candidate (if any) as a starting
///    sample, and build a focused sampler around its footprint;
/// 2. focused sampling around the reference placement;
/// 3. container-wide sampling across the sheet;
/// 4. retain the best unique samples in `BestSamples` (item-min-dim threshold);
/// 5. first coordinate descent over all best samples;
/// 6. second/final coordinate descent over the single best sample;
/// rotation wiggle is enabled inside the coordinate descent where rotations allow.
#[allow(clippy::too_many_arguments)]
pub(crate) fn search_placement(
    evaluator: &mut impl SampleEvaluator,
    inst: &SPInstance,
    sheet: &SheetShape,
    ref_rect_min: Option<(f64, f64, f64)>,
    sample_config: SampleConfig,
    cfg: &SparrowConfig,
    rng: &mut DeterministicRng,
    started: &Instant,
    deadline: f64,
    diag: &mut SparrowDiagnostics,
) -> Option<ScoredPlacement> {
    let deadline_reached = |s: &Instant| s.elapsed().as_secs_f64() >= deadline;
    let item_min_dim = inst.part.width.min(inst.part.height).max(1.0);
    let mut best = BestSamples::new(
        sample_config.n_coord_descents.max(1),
        item_min_dim * UNIQUE_SAMPLE_THRESHOLD,
    );

    // 1. Reference/current placement candidate + focused sampler around it.
    let focused_sampler = match ref_rect_min {
        Some((rmx, rmy, rot)) => {
            if let Some(c) = evaluator.evaluate_sample(rmx, rmy, rot, Some(best.upper_bound()), diag) {
                best.report(c);
            }
            // Focused sample bbox = the item's current footprint at this rotation.
            let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, rot);
            UniformBBoxSampler::new((rmx, rmy, rmx + rw, rmy + rh), inst, sheet)
        }
        None => None,
    };
    let container_sampler = UniformBBoxSampler::new(
        (sheet.min_x, sheet.min_y, sheet.max_x, sheet.max_y),
        inst,
        sheet,
    );

    // 2. Focused sampling.
    if let Some(fs) = &focused_sampler {
        for _ in 0..sample_config.n_focused_samples {
            if deadline_reached(started) {
                break;
            }
            let (rmx, rmy, rot) = fs.sample(rng);
            diag.search_focused_samples += 1;
            if let Some(c) = evaluator.evaluate_sample(rmx, rmy, rot, Some(best.upper_bound()), diag) {
                best.report(c);
            }
        }
    }

    // 3. Container-wide sampling.
    if let Some(cs) = &container_sampler {
        for _ in 0..sample_config.n_container_samples {
            if deadline_reached(started) {
                break;
            }
            let (rmx, rmy, rot) = cs.sample(rng);
            diag.search_global_samples += 1;
            if let Some(c) = evaluator.evaluate_sample(rmx, rmy, rot, Some(best.upper_bound()), diag) {
                best.report(c);
            }
        }
    }

    // Two-stage coordinate-descent refinement (upstream): a coarse pre/first stage
    // over all retained best samples, then a fine final/second stage over the best.
    const PRE_REFINE_STAGE: bool = false;
    const FINAL_REFINE_STAGE: bool = true;
    let wiggle = inst.continuous_rotation;

    // 5. First (pre-) coordinate descent over all retained best samples.
    let starts = best.samples.clone();
    for s in starts {
        if deadline_reached(started) {
            break;
        }
        if let Some(d) = refine_coord_desc(
            s,
            evaluator,
            item_min_dim,
            cfg,
            rng,
            diag,
            PRE_REFINE_STAGE,
            wiggle,
            cfg.rotation_wiggle_deg,
        ) {
            best.report(d);
        }
    }

    // 6. Second/final, finer coordinate descent over the single best sample.
    if let Some(s) = best.best() {
        if !deadline_reached(started) {
            if let Some(d) = refine_coord_desc(
                s,
                evaluator,
                item_min_dim,
                cfg,
                rng,
                diag,
                FINAL_REFINE_STAGE,
                wiggle,
                cfg.rotation_wiggle_deg,
            ) {
                best.report(d);
            }
        }
    }

    best.best()
}

/// Separation sample budget derived from the solver config.
pub(crate) fn separator_sample_config(cfg: &SparrowConfig) -> SampleConfig {
    SampleConfig {
        n_focused_samples: cfg.focused_samples.max(1),
        // Container coverage scales with the configured grid resolution (a budget,
        // not an algorithm switch); the range sampler draws this many random
        // rect-min/rotation samples across the sheet.
        n_container_samples: (cfg.global_grid_n * cfg.global_grid_n + 2 * cfg.global_grid_n).max(8),
        n_coord_descents: 8,
    }
}

/// Native CDE-backed search wrapping the upstream `search_placement` for each
/// eligible fixed sheet (the multisheet adaptation): the current sheet first,
/// then the others. The sampler / evaluator / refinement logic is the shared
/// upstream Algorithm 6 — only the per-sheet wrapper and the global-best pick are
/// fixed-sheet additions. Returns the lowest-eval placement across all sheets.
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
    let cur = &layout.placements[target];
    let inst = &instances[cur.instance_idx];
    let fixed_shapes = tracker.shapes.clone();
    let sample_config = separator_sample_config(cfg);
    // Build the per-instance base shape once (POI + surrogate); every candidate is
    // a cheap rigid transform of it.
    let base = prepare_base_shape_native(&inst.part).ok()?;

    // Sheet search order: current sheet first, then the rest (cross-sheet).
    let mut sheet_order: Vec<usize> = vec![cur.sheet_index];
    for sheet_idx in 0..sheets.len() {
        if sheet_idx != cur.sheet_index {
            sheet_order.push(sheet_idx);
        }
    }

    let mut global_best: Option<ScoredPlacement> = None;
    for (rank, &sheet_idx) in sheet_order.iter().enumerate() {
        if started.elapsed().as_secs_f64() >= deadline {
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
            base: &base,
            tracker,
            n_evals: 0,
        };
        // Reference (current) placement only contributes its focused sampler on its
        // own sheet, expressed in rect-min coordinates.
        let ref_rect_min = if sheet_idx == cur.sheet_index {
            let (rmx, rmy) = rect_min_from_anchor(
                cur.x,
                cur.y,
                inst.part.width,
                inst.part.height,
                cur.rotation_deg,
            );
            Some((rmx, rmy, cur.rotation_deg))
        } else {
            None
        };
        if let Some(local) = search_placement(
            &mut evaluator,
            inst,
            sheet,
            ref_rect_min,
            sample_config,
            cfg,
            rng,
            started,
            deadline,
            diag,
        ) {
            global_best = match global_best {
                None => Some(local),
                Some(g) if local.eval() < g.eval() => Some(local),
                other => other,
            };
        }
    }

    if let Some(b) = &global_best {
        if b.collision_loss < diag.search_best_eval || diag.search_best_eval == 0.0 {
            diag.search_best_eval = b.collision_loss;
        }
    }
    global_best.map(|b| b.placement)
}
