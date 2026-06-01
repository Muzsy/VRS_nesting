use super::*;

// Separator worker orchestration mapped from upstream optimizer/separator.rs.
impl SparrowOptimizer {
    pub(super) fn move_items_multi(
        &self,
        state: &mut SparrowState,
        instances: &[SPInstance],
        sheets: &[SheetShape],
        master_rng: &mut DeterministicRng,
        started: &Instant,
        deadline: f64,
        diag: &mut SparrowDiagnostics,
    ) {
        diag.worker_passes += 1;
        let colliding_seen = state.tracker.colliding_indices().len();
        diag.worker_colliding_items_seen += colliding_seen;
        diag.topk_target_count = diag.topk_target_count.max(colliding_seen);

        let worker_count = self.config.worker_count.max(1);
        let mut cands: Vec<SeparatorWorker> = Vec::with_capacity(worker_count);
        for w in 0..worker_count {
            let worker_seed =
                master_rng.next_u64() ^ ((w as u64).wrapping_mul(0x9E37_79B9_7F4A_7C15));
            let cand = run_worker_pass(
                w,
                state,
                instances,
                sheets,
                &self.config,
                worker_seed,
                started,
                deadline,
                diag,
            );
            cands.push(cand);
        }

        let best_idx = compare_worker_candidates(&cands).worker_idx;
        // Aggregate worker statistics (truthful evidence of the competition).
        for c in &cands {
            diag.worker_candidates_evaluated += c.evaluated;
            diag.multi_target_items_attempted += c.attempted;
            diag.multi_target_items_accepted += c.accepted;
            diag.multi_target_items_rejected += c.rejected;
        }
        diag.worker_count = worker_count;
        // Load the winning worker's state back into the master (Alg 10 load-back).
        let best = cands
            .into_iter()
            .find(|c| c.worker_idx == best_idx)
            .expect("best");
        diag.worker_commits += best.accepted;
        diag.worker_rollbacks += best.rejected + (worker_count - 1);
        diag.moves_attempted += best.attempted;
        diag.moves_accepted += best.accepted;
        diag.rollbacks += best.rejected;
        diag.worker_items_moved += best.accepted;
        diag.worker_best_loss = best.weighted_loss;
        load_best_worker(state, best);
    }

    /// Algorithm 9 native port: strike / no-improvement separation loop driven by
    /// the multi-worker competition, with GLS weight updates between iterations.
    pub(super) fn separate(
        &self,
        state: &mut SparrowState,
        instances: &[SPInstance],
        sheets: &[SheetShape],
        started: &Instant,
        deadline: f64,
        rng: &mut DeterministicRng,
        diag: &mut SparrowDiagnostics,
    ) -> bool {
        diag.separator_invocations += 1;
        let strike_limit = 4usize;
        let no_improve_limit = 6usize;
        let mut strikes = 0usize;
        let mut best_raw = state.tracker.total_raw_loss();
        let mut best_pairs = state.tracker.colliding_pairs();
        let mut best_snapshot = (state.layout.snapshot(), state.tracker.snapshot());

        while strikes < strike_limit && started.elapsed().as_secs_f64() < deadline {
            let initial_strike_loss = state.tracker.total_raw_loss();
            let mut no_improve = 0usize;
            while no_improve < no_improve_limit && started.elapsed().as_secs_f64() < deadline {
                diag.iterations += 1;
                if state.tracker.colliding_indices().is_empty() {
                    break;
                }
                self.move_items_multi(state, instances, sheets, rng, started, deadline, diag);
                state.refresh_incumbents();
                let raw = state.tracker.total_raw_loss();
                let pairs = state.tracker.colliding_pairs();
                if raw <= 1e-9 {
                    state.best_feasible = Some(state.layout.snapshot());
                    return true;
                } else if raw < best_raw - 1e-9 || pairs < best_pairs {
                    let old_best_raw = best_raw;
                    let old_best_pairs = best_pairs;
                    best_raw = raw;
                    best_pairs = pairs;
                    best_snapshot = (state.layout.snapshot(), state.tracker.snapshot());
                    if raw < old_best_raw * 0.98 || pairs < old_best_pairs {
                        no_improve = 0;
                    }
                } else {
                    no_improve += 1;
                }
                state.tracker.update_weights();
                diag.gls_weight_updates += 1;
            }
            if initial_strike_loss * 0.98 <= best_raw {
                strikes += 1;
                diag.separator_strikes += 1;
            } else {
                strikes = 0;
            }
            // Roll back to the least-infeasible incumbent, keep GLS weights.
            state.layout = best_snapshot.0.snapshot();
            state.tracker.restore_keep_weights(best_snapshot.1.clone());
            if best_raw <= 1e-9 {
                break;
            }
        }
        state.tracker.is_feasible()
    }

}
