use super::*;

// ---------------------------------------------------------------------------
// rng
// ---------------------------------------------------------------------------

/// Deterministic SplitMix64-style RNG (native, seed-controlled).
#[derive(Clone)]
pub struct DeterministicRng {
    state: u64,
}

impl DeterministicRng {
    pub fn new(seed: u64) -> Self {
        Self {
            state: seed ^ 0x9E37_79B9_7F4A_7C15,
        }
    }
    pub fn next_u64(&mut self) -> u64 {
        self.state = self.state.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.state;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
    pub fn next_f64(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 / (1u64 << 53) as f64
    }
    pub fn jitter(&mut self, span: f64) -> f64 {
        (self.next_f64() * 2.0 - 1.0) * span
    }
    /// Deterministic Fisher-Yates shuffle of `v`.
    pub fn shuffle<T>(&mut self, v: &mut [T]) {
        for k in (1..v.len()).rev() {
            let j = (self.next_u64() as usize) % (k + 1);
            v.swap(k, j);
        }
    }
}

// ---------------------------------------------------------------------------
// Config + Diagnostics
// ---------------------------------------------------------------------------

/// Native Sparrow solver configuration.
#[derive(Debug, Clone)]
pub struct SparrowConfig {
    pub time_limit_s: f64,
    pub collision_backend: CollisionBackendKind,
    pub rotation_context: RotationResolveContext,
    pub seed: u64,
    /// Number of competing workers per `move_items_multi` pass (>= 2 for real
    /// worker competition / best-worker load-back).
    pub worker_count: usize,
    /// Focused samples per target search around the current placement.
    pub focused_samples: usize,
    /// Coarse global grid resolution per axis per eligible sheet.
    pub global_grid_n: usize,
    /// Coordinate-descent refinement steps on the best candidate.
    pub coord_descent_steps: usize,
    /// Initial rotation-wiggle step (degrees) for coordinate-descent refinement.
    /// Only applied when the instance's rotation policy permits continuous/free
    /// rotation; discrete (orthogonal) instances keep their fixed rotation set.
    pub rotation_wiggle_deg: f64,
}

impl SparrowConfig {
    pub fn from_solver_input(
        time_limit_s: f64,
        backend: CollisionBackendKind,
        rotation_context: RotationResolveContext,
        seed: u64,
    ) -> Self {
        Self {
            time_limit_s: time_limit_s.max(0.1),
            collision_backend: backend,
            rotation_context,
            seed,
            worker_count: 3,
            focused_samples: 5,
            global_grid_n: 4,
            coord_descent_steps: 5,
            rotation_wiggle_deg: 6.0,
        }
    }

    pub fn scaled_for_instance_count(&self, instance_count: usize) -> Self {
        let mut cfg = self.clone();
        if instance_count >= 100 {
            cfg.worker_count = cfg.worker_count.clamp(2, 3);
            cfg.focused_samples = cfg.focused_samples.min(4).max(3);
            cfg.global_grid_n = cfg.global_grid_n.min(2).max(2);
            cfg.coord_descent_steps = cfg.coord_descent_steps.min(3).max(2);
        } else if instance_count >= 40 {
            cfg.worker_count = cfg.worker_count.min(2).max(2);
            cfg.focused_samples = cfg.focused_samples.min(3);
            cfg.global_grid_n = cfg.global_grid_n.min(2);
            cfg.coord_descent_steps = cfg.coord_descent_steps.min(2);
        }
        cfg
    }
}

/// Native Sparrow diagnostics surfaced to the adapter output projection.
/// Field names mirror the prior `sparrow_*` output contract plus the Q24R5
/// native-model proof flags and the Q24R6 search/worker/tracker evidence.
#[derive(Debug, Clone, Default)]
pub struct SparrowDiagnostics {
    pub invoked: bool,
    pub seed_placements: usize,
    pub seed_unplaced: usize,
    pub initial_raw_loss: f64,
    pub initial_weighted_loss: f64,
    pub final_raw_loss: f64,
    pub final_weighted_loss: f64,
    pub best_infeasible_raw_loss: f64,
    pub best_infeasible_weighted_loss: f64,
    pub iterations: usize,
    pub moves_attempted: usize,
    pub moves_accepted: usize,
    pub rollbacks: usize,
    pub gls_weight_updates: usize,
    pub converged: bool,
    pub collision_graph_initial_pairs: usize,
    pub collision_graph_final_pairs: usize,
    pub boundary_violations_initial: usize,
    pub boundary_violations_final: usize,
    // ── search activity ─────────────────────────────────────────────────────
    pub search_position_calls: usize,
    pub search_position_samples: usize,
    pub search_global_samples: usize,
    pub search_focused_samples: usize,
    pub search_refined_samples: usize,
    pub search_coord_descent_steps: usize,
    pub search_unsupported_samples: usize,
    pub search_cross_sheet_calls: usize,
    /// Nonzero rotation-wiggle refinement steps actually evaluated (continuous /
    /// free-rotation instances only).
    pub search_rotation_wiggle: usize,
    pub search_best_eval: f64,
    pub lbf_fallback_used: usize,
    // ── worker competition ──────────────────────────────────────────────────
    pub worker_count: usize,
    pub worker_passes: usize,
    pub worker_candidates_evaluated: usize,
    pub worker_commits: usize,
    pub worker_rollbacks: usize,
    pub worker_best_loss: f64,
    pub worker_colliding_items_seen: usize,
    pub worker_items_moved: usize,
    pub multi_target_items_attempted: usize,
    pub multi_target_items_accepted: usize,
    pub multi_target_items_rejected: usize,
    pub topk_target_count: usize,
    // ── separator / exploration ─────────────────────────────────────────────
    pub separator_invocations: usize,
    pub separator_strikes: usize,
    pub exploration_attempts: usize,
    pub exploration_pool_inserts: usize,
    pub exploration_pool_restores: usize,
    pub exploration_disruptions_large_item_swap: usize,
    pub exploration_disruptions_cross_sheet: usize,
    pub exploration_disruptions_rotation: usize,
    pub excluded_phase_passes: usize,
    // ── tracker quantification evidence ───────────────────────────────────────
    pub quantified_pair_queries: usize,
    pub quantified_boundary_queries: usize,
    pub unsupported_queries: usize,
    // ── Q24R5 native-model proof flags ──────────────────────────────────────
    pub native_model_active: bool,
    pub native_tracker_active: bool,
    pub old_core_used: bool,
    pub native_problem_instances: usize,
    pub native_tracker_full_rebuilds: usize,
    pub native_tracker_incremental_updates: usize,
    // ── dense reference-run diagnostics ─────────────────────────────────────
    pub dense_guard_used: bool,
    pub dense_real_run: bool,
    pub dense_partial_reason: Option<String>,
    pub dense_validated_placements: Option<usize>,
    pub dense_unresolved_instances: Vec<String>,
    pub dense_final_validation_ran: bool,
}
