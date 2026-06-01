use super::*;

pub struct SparrowOptimizer {
    pub config: SparrowConfig,
}

impl SparrowOptimizer {
    pub fn new(config: SparrowConfig) -> Self {
        Self { config }
    }

    pub fn solve(&self, problem: SparrowProblem) -> SparrowSolveResult {
        let active_config = self
            .config
            .scaled_for_instance_count(problem.instances.len());
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
        crate::optimizer::cde_adapter::reset_query_cache();
        set_quant_config(active_config.clone());

        let instances = &problem.instances;
        let sheets = &problem.container.sheets;
        let started = Instant::now();
        let deadline = self.config.time_limit_s.max(0.1);
        let mut rng = DeterministicRng::new(self.config.seed);

        let seed_layout = build_native_constructive_seed(&problem);
        diag.seed_placements = seed_layout.placements.len();
        diag.seed_unplaced = problem.pre_unplaced.len();
        let dense_reference_run = instances.len() >= 100 && sheets.len() == 1;
        diag.dense_real_run = dense_reference_run;
        let mut state = SparrowState::new_with_diag(seed_layout, instances, sheets, &mut diag);
        diag.initial_raw_loss = state.tracker.total_raw_loss();
        diag.initial_weighted_loss = state.tracker.total_weighted_loss();
        diag.collision_graph_initial_pairs = state.tracker.colliding_pairs();
        diag.boundary_violations_initial = state.tracker.boundary_violations();
        diag.best_infeasible_raw_loss = state.best_infeasible_raw_loss;

        // Exploration: separate; on failure, pool the least-infeasible state,
        // biased-restore one, disrupt, and retry.
        let max_attempts = 10usize;
        let mut feasible = false;
        let mut pool: Vec<(f64, SparrowLayout)> = Vec::new();
        for attempt in 0..max_attempts {
            if started.elapsed().as_secs_f64() >= deadline {
                break;
            }
            diag.exploration_attempts += 1;
            if active_optimizer.separate(
                &mut state, instances, sheets, &started, deadline, &mut rng, &mut diag,
            ) {
                feasible = true;
                break;
            }
            // Pool insert (least-infeasible), biased restore, disrupt.
            let raw = state.tracker.total_raw_loss();
            let at = pool
                .binary_search_by(|(l, _)| l.partial_cmp(&raw).unwrap_or(std::cmp::Ordering::Equal))
                .unwrap_or_else(|e| e);
            pool.insert(at, (raw, state.layout.snapshot()));
            pool.truncate(8);
            diag.exploration_pool_inserts += 1;
            if !pool.is_empty() {
                // Biased restore: pick from the better half of the pool.
                let sel = (self.config.seed as usize).wrapping_add(attempt)
                    % ((pool.len() + 1) / 2).max(1);
                let restored = pool[sel].1.snapshot();
                diag.exploration_pool_restores += 1;
                state = SparrowState::new_with_diag(restored, instances, sheets, &mut diag);
                active_optimizer.disrupt(&mut state, instances, sheets, &mut rng, &mut diag);
            }
        }

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
        let final_tracker =
            SparrowCollisionTracker::final_validation_tracker(&final_layout, instances, sheets);
        let validated = final_tracker.is_feasible();
        diag.collision_graph_final_pairs = final_tracker.colliding_pairs();
        diag.boundary_violations_final = final_tracker.boundary_violations();
        diag.final_raw_loss = final_tracker.total_raw_loss();
        diag.final_weighted_loss = final_tracker.total_weighted_loss();
        diag.best_infeasible_raw_loss = state.best_infeasible_raw_loss;
        diag.best_infeasible_weighted_loss = state.best_infeasible_raw_loss;
        diag.converged = feasible && validated && final_tracker.is_feasible();
        diag.native_tracker_full_rebuilds += final_tracker.full_rebuilds;
        diag.search_position_samples = diag.search_position_samples.max(
            diag.search_focused_samples + diag.search_global_samples + diag.search_refined_samples,
        );
        diag.iterations = diag.iterations.max(1);
        diag.dense_final_validation_ran = dense_reference_run;
        if dense_reference_run {
            let unresolved_layout_indices = final_tracker.colliding_indices();
            let unresolved: Vec<String> = unresolved_layout_indices
                .iter()
                .filter_map(|&layout_idx| final_layout.placements.get(layout_idx))
                .filter_map(|p| instances.get(p.instance_idx))
                .map(|inst| inst.instance_id.clone())
                .collect();
            diag.dense_validated_placements =
                Some(final_layout.placements.len().saturating_sub(unresolved.len()));
            diag.dense_unresolved_instances = unresolved;
            diag.dense_partial_reason = if validated && final_tracker.is_feasible() {
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
        let placements = solution.to_solver_projection(instances);
        SparrowSolveResult {
            placements,
            unplaced: problem.pre_unplaced,
            feasible: feasible_final,
            solution,
            diagnostics: diag,
        }
    }
}
