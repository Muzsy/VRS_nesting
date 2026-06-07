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
    CdeCandidateSession::build_with_policy(
        others,
        sheet_shape,
        crate::optimizer::cde_adapter::CdeTouchingPolicy::SparrowStrict,
    )
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
                best.report(c, diag);
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

    let prof_active = diag.q30_profile.enabled && diag.q30_profile.profiling_scope_active;

    let r1_active = diag.q30_profile.r1_active();

    // 2. Focused sampling.
    if let Some(fs) = &focused_sampler {
        for _ in 0..sample_config.n_focused_samples {
            if deadline_reached(started) {
                break;
            }
            let t_sample = ProfileTimer::start_if(prof_active);
            let (rmx, rmy, rot) = fs.sample(rng);
            t_sample.add_to(&mut diag.q30_profile.sample_generation_ms);
            diag.search_focused_samples += 1;
            if prof_active { diag.q30_profile.focused_samples_generated += 1; }
            if let Some(c) = evaluator.evaluate_sample(rmx, rmy, rot, Some(best.upper_bound()), diag) {
                if r1_active { diag.q30_profile.evaluate_sample_calls_from_focused += 1; }
                best.report(c, diag);
            }
        }
    }

    // 3. Container-wide sampling.
    if let Some(cs) = &container_sampler {
        for _ in 0..sample_config.n_container_samples {
            if deadline_reached(started) {
                break;
            }
            let t_sample = ProfileTimer::start_if(prof_active);
            let (rmx, rmy, rot) = cs.sample(rng);
            t_sample.add_to(&mut diag.q30_profile.sample_generation_ms);
            diag.search_global_samples += 1;
            if prof_active { diag.q30_profile.global_samples_generated += 1; }
            if let Some(c) = evaluator.evaluate_sample(rmx, rmy, rot, Some(best.upper_bound()), diag) {
                if r1_active { diag.q30_profile.evaluate_sample_calls_from_global += 1; }
                best.report(c, diag);
            }
        }
    }

    // Two-stage coordinate-descent refinement (upstream): a coarse pre/first stage
    // over all retained best samples, then a fine final/second stage over the best.
    const PRE_REFINE_STAGE: bool = false;
    const FINAL_REFINE_STAGE: bool = true;
    let wiggle = inst.continuous_rotation;

    // 5. First (pre-) coordinate descent over all retained best samples.
    // R1: time best.samples.clone() — clones the small BestSamples vec for iteration.
    let t_bclone = ProfileTimer::start_if(r1_active);
    let starts = best.samples.clone();
    t_bclone.add_to(&mut diag.q30_profile.best_samples_clone_ms);
    if r1_active { diag.q30_profile.best_samples_clone_calls += 1; }
    for s in starts {
        if deadline_reached(started) {
            break;
        }
        if prof_active { diag.q30_profile.coord_descent_runs += 1; }
        let t_cd = ProfileTimer::start_if(prof_active);
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
            t_cd.add_to(&mut diag.q30_profile.coord_descent_total_ms);
            best.report(d, diag);
        } else {
            t_cd.add_to(&mut diag.q30_profile.coord_descent_total_ms);
        }
    }

    // 6. Second/final, finer coordinate descent over the single best sample.
    // R1: time best.best() call — retrieves the current best sample.
    let t_best = ProfileTimer::start_if(r1_active);
    let best_sample = best.best();
    t_best.add_to(&mut diag.q30_profile.best_samples_best_ms);
    if r1_active { diag.q30_profile.best_samples_best_calls += 1; }
    if let Some(s) = best_sample {
        if !deadline_reached(started) {
            if prof_active { diag.q30_profile.coord_descent_runs += 1; }
            let t_cd = ProfileTimer::start_if(prof_active);
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
                t_cd.add_to(&mut diag.q30_profile.coord_descent_total_ms);
                best.report(d, diag);
            } else {
                t_cd.add_to(&mut diag.q30_profile.coord_descent_total_ms);
            }
        }
    }

    best.best()
}

/// Separation sample budget derived from the solver config.
pub(crate) fn separator_sample_config(cfg: &SparrowConfig) -> SampleConfig {
    if cfg.profile == SparrowProfile::SparrowStrictParity {
        SampleConfig {
            n_focused_samples: SPARROW_PARITY_SEPARATOR_FOCUSED_SAMPLES,
            n_container_samples: SPARROW_PARITY_SEPARATOR_CONTAINER_SAMPLES,
            n_coord_descents: SPARROW_PARITY_COORD_DESCENTS,
        }
    } else if cfg.profile == SparrowProfile::SparrowDenseLargeScale {
        SampleConfig {
            n_focused_samples: SPARROW_DENSE_FOCUSED_SAMPLES,
            n_container_samples: SPARROW_DENSE_CONTAINER_SAMPLES,
            n_coord_descents: SPARROW_DENSE_COORD_DESCENTS,
        }
    } else {
        SampleConfig {
            n_focused_samples: cfg.focused_samples.max(1),
            n_container_samples: (cfg.global_grid_n * cfg.global_grid_n + 2 * cfg.global_grid_n).max(8),
            n_coord_descents: 8,
        }
    }
}

/// Native CDE-backed search wrapping the upstream `search_placement` for each
/// eligible fixed sheet (the multisheet adaptation): the current sheet first,
/// then the others. The sampler / evaluator / refinement logic is the shared
/// upstream Algorithm 6 — only the per-sheet wrapper and the global-best pick are
/// fixed-sheet additions. Returns the lowest-eval placement across all sheets.
///
/// `live_session`: when `Some`, the caller owns a long-lived `CdeCandidateSession`
/// for the current sheet. On rank-0 the target is deregistered before search and
/// left deregistered on return (the caller handles reregister based on accept/reject).
/// Cross-sheet passes always build a fresh session regardless.
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
    live_session: Option<&mut CdeCandidateSession>,
) -> Option<SparrowPlacement> {
    diag.search_position_calls += 1;
    diag.q30_profile.native_search_calls += 1;
    diag.q30_profile.profiling_scope_active = diag.q30_profile.enabled;
    let search_t0 = if diag.profiling_enabled { Some(Instant::now()) } else { None };
    let t_search = ProfileTimer::start_if(diag.q30_profile.enabled);
    // Deregister the target BEFORE any early-return or deadline check so that the
    // invariant holds: when live_session is Some, the target is always deregistered
    // when this function returns, regardless of early exits or deadline expiry.
    // The caller (run_worker_pass) always reregisters after the call.
    let mut live_session = live_session;
    if let Some(ref mut ls) = live_session {
        let dereg_t0 = if diag.profiling_enabled { Some(Instant::now()) } else { None };
        let t_dereg = ProfileTimer::start_if(diag.q30_profile.enabled);
        ls.deregister_item(target);
        if let Some(t) = dereg_t0 {
            diag.profile_deregister_ms += t.elapsed().as_secs_f64() * 1000.0;
        }
        t_dereg.add_to(&mut diag.q30_profile.deregister_reregister_ms);
    }
    let cur = &layout.placements[target];
    let inst = &instances[cur.instance_idx];
    let r1 = diag.q30_profile.r1_active();
    // R1: time tracker.shapes.clone() — Vec of Rc<CdePreparedShape> for all items.
    let t_clone = ProfileTimer::start_if(r1);
    let fixed_shapes = tracker.shapes.clone();
    t_clone.add_to(&mut diag.q30_profile.fixed_shapes_clone_ms);
    let sample_config = separator_sample_config(cfg);
    // Q31: use the per-instance cached CDE base shape (built once in from_solver_input).
    // Every candidate is produced by transform_base_to_candidate (called in SeparationEvaluator).
    let base = inst.base_shape.clone();
    if r1 { diag.q30_profile.search_base_shape_cache_hits += 1; }
    // Verify the current anchor is reachable; if the base shape is degenerate, skip.
    if transform_base_to_candidate(&base, cur.x, cur.y, cur.rotation_deg).is_none() {
        t_search.add_to(&mut diag.q30_profile.search_total_ms);
        diag.q30_profile.profiling_scope_active = false;
        return None;
    }

    // R1: time sheet order construction.
    let t_order = ProfileTimer::start_if(r1);
    // Sheet search order: current sheet first, then the rest (cross-sheet).
    let mut sheet_order: Vec<usize> = vec![cur.sheet_index];
    for sheet_idx in 0..sheets.len() {
        if sheet_idx != cur.sheet_index {
            sheet_order.push(sheet_idx);
        }
    }
    t_order.add_to(&mut diag.q30_profile.sheet_order_build_ms);

    let mut global_best: Option<ScoredPlacement> = None;
    for (rank, &sheet_idx) in sheet_order.iter().enumerate() {
        if started.elapsed().as_secs_f64() >= deadline {
            break;
        }
        if r1 { diag.q30_profile.sheet_loop_iterations += 1; }
        if rank > 0 {
            diag.search_cross_sheet_calls += 1;
        }
        let sheet = &sheets[sheet_idx];
        let Some(sheet_shape) = tracker.sheet_shapes.get(sheet_idx).and_then(|s| s.clone()) else {
            continue;
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

        // Rank-0 with a live session: target already deregistered above, search
        // in-place, leave deregistered — caller reregisters based on accept/reject.
        if rank == 0 {
            if let Some(ref mut ls) = live_session {
                let mut evaluator = SeparationEvaluator {
                    target,
                    inst,
                    sheet,
                    sheet_idx,
                    sheet_shape: &sheet_shape,
                    session: &**ls,
                    fixed_shapes: &fixed_shapes,
                    base: &base,
                    tracker,
                    n_evals: 0,
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
                continue;
            }
        }

        // Fallback: build a fresh session for this sheet (None case or cross-sheet).
        let sess_t0 = if diag.profiling_enabled { Some(Instant::now()) } else { None };
        let t_sess = ProfileTimer::start_if(diag.q30_profile.enabled);
        let Some(session) = build_sheet_session(target, sheet_idx, layout, tracker, &sheet_shape)
        else {
            continue;
        };
        if let Some(t) = sess_t0 {
            diag.profile_session_build_ms += t.elapsed().as_secs_f64() * 1000.0;
        }
        t_sess.add_to(&mut diag.q30_profile.session_build_ms);
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
    if let Some(t) = search_t0 {
        diag.profile_search_total_ms += t.elapsed().as_secs_f64() * 1000.0;
    }
    t_search.add_to(&mut diag.q30_profile.search_total_ms);
    diag.q30_profile.profiling_scope_active = false;
    global_best.map(|b| b.placement)
}
