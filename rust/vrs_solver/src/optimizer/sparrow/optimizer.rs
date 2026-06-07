use super::*;

pub struct SparrowOptimizer {
    pub config: SparrowConfig,
}

impl SparrowOptimizer {
    pub fn new(config: SparrowConfig) -> Self {
        Self { config }
    }

    pub fn solve(&self, problem: SparrowProblem) -> SparrowSolveResult {
        let mut active_config = self
            .config
            .scaled_for_instance_count(problem.instances.len());
        // For dense (100+ instance) single-sheet runs, reduce the per-iteration
        // search budget so the solver completes 4-5× more iterations within the
        // same time budget. GLS semantics (shuffle ordering, weighted-loss
        // selection, strike/exploration cycling) are preserved.
        if problem.instances.len() >= 100 {
            active_config.profile = SparrowProfile::SparrowDenseLargeScale;
            active_config.worker_count = SPARROW_DENSE_WORKER_COUNT;
            active_config.focused_samples = SPARROW_DENSE_FOCUSED_SAMPLES;
            active_config.global_grid_n = SPARROW_DENSE_GLOBAL_GRID_N;
            active_config.coord_descent_steps = SPARROW_DENSE_COORD_DESCENTS;
        }
        let active_optimizer = SparrowOptimizer::new(active_config.clone());
        let mut diag = SparrowDiagnostics {
            invoked: true,
            native_model_active: true,
            native_tracker_active: true,
            old_core_used: false,
            native_problem_instances: problem.instances.len(),
            worker_count: active_config.worker_count,
            ..SparrowDiagnostics::default()
        };
        diag.excluded_phase_passes = 0;
        crate::optimizer::cde_adapter::reset_query_cache();
        set_quant_config(active_config.clone());

        let started = Instant::now();
        let deadline = self.config.time_limit_s.max(0.1);
        let mut rng = DeterministicRng::new(self.config.seed);
        let r1 = diag.q30_profile.r1_exclusive_enabled;

        let t_lbf = ProfileTimer::start_if(r1);
        let seed_layout = build_native_constructive_seed(&problem);
        t_lbf.add_to(&mut diag.q30_profile.seed_lbf_total_ms);
        let instances = &problem.instances;
        let sheets = &problem.container.sheets;
        diag.seed_placements = seed_layout.placements.len();
        diag.seed_unplaced = problem.pre_unplaced.len();
        let dense_reference_run = instances.len() >= 100 && sheets.len() == 1;
        diag.dense_real_run = dense_reference_run;
        let t_tracker_init = ProfileTimer::start_if(r1);
        let mut state = SparrowState::new_with_diag(seed_layout, instances, sheets, &mut diag);
        t_tracker_init.add_to(&mut diag.q30_profile.tracker_initial_build_ms);
        diag.initial_raw_loss = state.tracker.total_raw_loss();
        diag.initial_weighted_loss = state.tracker.total_weighted_loss();
        diag.collision_graph_initial_pairs = state.tracker.colliding_pairs();
        diag.boundary_violations_initial = state.tracker.boundary_violations();
        diag.best_infeasible_raw_loss = state.best_infeasible_raw_loss;

        if diag.search_rotation_wiggle == 0 {
            if let Some(target) = state
                .layout
                .placements
                .iter()
                .position(|p| instances[p.instance_idx].continuous_rotation)
            {
                let mut probe_rng = DeterministicRng::new(rng.next_u64());
                let _ = native_search_placement(
                    target,
                    &state.layout,
                    instances,
                    &state.tracker,
                    sheets,
                    &active_config,
                    &mut probe_rng,
                    &started,
                    f64::INFINITY,
                    &mut diag,
                    None,
                );
            }
        }

        // Exploration phase (Algorithm 12, fixed-sheet adaptation): separate; on
        // failure, pool the least-infeasible state, biased-restore one, disrupt,
        // and retry. Owned by `explore.rs`.
        let t_explore = ProfileTimer::start_if(r1);
        let feasible = active_optimizer.exploration_phase(
            &mut state, instances, sheets, &started, deadline, &mut rng, &mut diag,
        );
        t_explore.add_to(&mut diag.q30_profile.exploration_total_ms);

        // Pick the layout to validate/emit: feasible incumbent if any, else the
        // least-infeasible incumbent by pair count/raw loss. If the active state
        // was just disrupted near the deadline, keep it when it has fewer pairs.
        let final_layout = if let Some(feasible_layout) = state.best_feasible.clone() {
            feasible_layout
        } else if state.tracker.colliding_pairs() < state.best_infeasible_pair_count
            || (state.tracker.colliding_pairs() == state.best_infeasible_pair_count
                && state.tracker.total_raw_loss() <= state.best_infeasible_raw_loss)
        {
            state.layout.snapshot()
        } else {
            state
                .best_infeasible
                .clone()
                .unwrap_or_else(|| state.layout.snapshot())
        };
        let t_final_val = ProfileTimer::start_if(r1);
        let final_tracker =
            SparrowCollisionTracker::final_validation_tracker(&final_layout, instances, sheets);
        t_final_val.add_to(&mut diag.q30_profile.tracker_final_validation_ms);
        let validated = final_tracker.is_feasible();
        diag.collision_graph_final_pairs = final_tracker.colliding_pairs();
        diag.boundary_violations_final = final_tracker.boundary_violations();
        diag.final_raw_loss = final_tracker.total_raw_loss();
        diag.final_weighted_loss = final_tracker.total_weighted_loss();
        diag.best_infeasible_raw_loss = state.best_infeasible_raw_loss;
        diag.best_infeasible_weighted_loss = state.best_infeasible_raw_loss;
        let all_instances_placed = final_layout.placements.len() == instances.len();
        diag.converged =
            feasible && validated && final_tracker.is_feasible() && all_instances_placed;
        diag.native_tracker_full_rebuilds += final_tracker.full_rebuilds;
        diag.search_position_samples = diag.search_position_samples.max(
            diag.search_focused_samples + diag.search_global_samples + diag.search_refined_samples,
        );
        diag.iterations = diag.iterations.max(1);
        diag.dense_final_validation_ran = dense_reference_run;
        if dense_reference_run {
            let unresolved_layout_indices = final_tracker.colliding_indices();
            let mut unresolved: Vec<String> = unresolved_layout_indices
                .iter()
                .filter_map(|&layout_idx| final_layout.placements.get(layout_idx))
                .filter_map(|p| instances.get(p.instance_idx))
                .map(|inst| inst.instance_id.clone())
                .collect();
            let colliding_unresolved_count = unresolved.len();
            let placed_instance_indices: Vec<usize> = final_layout
                .placements
                .iter()
                .map(|p| p.instance_idx)
                .collect();
            unresolved.extend(
                instances
                    .iter()
                    .filter(|inst| !placed_instance_indices.contains(&inst.idx))
                    .map(|inst| inst.instance_id.clone()),
            );
            let unplaced_count = instances
                .len()
                .saturating_sub(final_layout.placements.len());
            diag.dense_validated_placements = Some(
                final_layout
                    .placements
                    .len()
                    .saturating_sub(colliding_unresolved_count),
            );
            diag.dense_unresolved_instances = unresolved;
            diag.dense_partial_reason = if unplaced_count > 0 {
                Some("unplaced_instances".to_string())
            } else if validated && final_tracker.is_feasible() {
                None
            } else if started.elapsed().as_secs_f64() >= deadline {
                Some("time_budget_exhausted".to_string())
            } else if final_tracker.colliding_pairs() > 0 {
                Some("unresolved_collisions".to_string())
            } else if final_tracker.boundary_violations() > 0 {
                Some("boundary_violations".to_string())
            } else if final_tracker.unsupported {
                Some("unsupported_geometry".to_string())
            } else {
                Some("no_feasible_candidate".to_string())
            };
        }

        let feasible_final = diag.converged;
        let solution = SparrowSolution {
            layout: final_layout,
            feasible: feasible_final,
        };
        let t_output = ProfileTimer::start_if(r1);
        let placements = solution.to_solver_projection(instances);
        t_output.add_to(&mut diag.q30_profile.output_mapping_ms);
        diag.q30_profile.sparrow_optimizer_solve_total_ms =
            started.elapsed().as_secs_f64() * 1000.0;
        diag.q30_profile.total_solver_runtime_ms =
            diag.q30_profile.sparrow_optimizer_solve_total_ms;
        // Call finalize on the solve path before diagnostics are read.
        diag.q30_profile.finalize();
        SparrowSolveResult {
            placements,
            unplaced: problem.pre_unplaced,
            feasible: feasible_final,
            solution,
            diagnostics: diag,
        }
    }
}
