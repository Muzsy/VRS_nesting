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

        // Upstream Algorithm 10: the winning worker is the one with the lowest
        // total *weighted* loss. Raw loss, colliding-pair count and worker index
        // are deterministic tie-breakers / diagnostics only — never the primary
        // selection criterion.
        let best_idx = cands
            .iter()
            .min_by(|a, b| {
                a.weighted_loss
                    .partial_cmp(&b.weighted_loss)
                    .unwrap_or(std::cmp::Ordering::Equal)
                    .then(
                        a.raw_loss
                            .partial_cmp(&b.raw_loss)
                            .unwrap_or(std::cmp::Ordering::Equal),
                    )
                    .then(usize::cmp(&a.colliding_pair_total, &b.colliding_pair_total))
                    .then(a.worker_idx.cmp(&b.worker_idx))
            })
            .expect("at least one worker")
            .worker_idx;
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
        let strike_limit = match self.config.profile {
            SparrowProfile::SparrowStrictParity => SPARROW_PARITY_STRIKE_LIMIT,
            SparrowProfile::SparrowDenseLargeScale => SPARROW_PARITY_STRIKE_LIMIT,
            SparrowProfile::VrsFast => 4usize,
        };
        let no_improve_limit = match self.config.profile {
            SparrowProfile::SparrowStrictParity => SPARROW_PARITY_ITER_NO_IMPROVE_LIMIT,
            SparrowProfile::SparrowDenseLargeScale => SPARROW_DENSE_NO_IMPROVE_LIMIT,
            SparrowProfile::VrsFast => 6usize,
        };
        let mut strikes = 0usize;
        // Upstream Algorithm 9 drives improvement/strike decisions off the total
        // RAW loss (`get_total_loss`). Colliding-pair count is a diagnostic only.
        let mut best_raw = state.tracker.total_raw_loss();
        let mut best_snapshot = (state.layout.snapshot(), state.tracker.snapshot());

        while strikes < strike_limit && started.elapsed().as_secs_f64() < deadline {
            let initial_strike_loss = state.tracker.total_raw_loss();
            let mut no_improve = 0usize;
            while no_improve < no_improve_limit && started.elapsed().as_secs_f64() < deadline {
                diag.iterations += 1;
                if state.tracker.colliding_indices().is_empty() {
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
                                &self.config,
                                &mut probe_rng,
                                started,
                                f64::INFINITY,
                                diag,
                                None,
                            );
                        }
                    }
                    break;
                }
                self.move_items_multi(state, instances, sheets, rng, started, deadline, diag);
                state.refresh_incumbents();
                let raw = state.tracker.total_raw_loss();
                if raw <= 1e-9 {
                    state.best_feasible = Some(state.layout.snapshot());
                    return true;
                } else if raw < best_raw - 1e-9 {
                    // New best by total raw loss (upstream Algorithm 9 semantics).
                    let old_best_raw = best_raw;
                    best_raw = raw;
                    best_snapshot = (state.layout.snapshot(), state.tracker.snapshot());
                    // Reset the no-improvement counter only on a substantial (>2%) drop.
                    if raw < old_best_raw * 0.98 {
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
