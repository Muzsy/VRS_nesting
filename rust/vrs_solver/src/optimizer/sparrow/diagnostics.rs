use super::*;
use crate::optimizer::sparrow::profile::SearchProfiler;

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
    pub profile: SparrowProfile,
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

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SparrowProfile {
    SparrowStrictParity,
    VrsFast,
    /// Reduced per-iteration budget for 100+ instance dense runs: same GLS
    /// semantics as SparrowStrictParity but with fewer samples per search
    /// call, allowing 4-5× more iterations within the same time budget.
    SparrowDenseLargeScale,
}

pub const SPARROW_PARITY_SEPARATOR_CONTAINER_SAMPLES: usize = 50;
pub const SPARROW_PARITY_SEPARATOR_FOCUSED_SAMPLES: usize = 25;
pub const SPARROW_PARITY_COORD_DESCENTS: usize = 3;
pub const SPARROW_PARITY_LBF_CONTAINER_SAMPLES: usize = 1000;
pub const SPARROW_PARITY_LBF_FOCUSED_SAMPLES: usize = 0;
pub const SPARROW_PARITY_ITER_NO_IMPROVE_LIMIT: usize = 200;
pub const SPARROW_PARITY_STRIKE_LIMIT: usize = 3;
pub const SPARROW_PARITY_WORKERS: usize = 3;
pub const SPARROW_PARITY_MAX_CONSEC_FAILED_ATTEMPTS: usize = 10;
pub const SPARROW_PARITY_SOLUTION_POOL_STDDEV: f64 = 0.25;
/// Dense large-scale (100+ instances) reduced search budget constants.
pub const SPARROW_DENSE_WORKER_COUNT: usize = 2;
pub const SPARROW_DENSE_FOCUSED_SAMPLES: usize = 8;
pub const SPARROW_DENSE_CONTAINER_SAMPLES: usize = 8;
pub const SPARROW_DENSE_GLOBAL_GRID_N: usize = 2;
/// Keep 4 best samples for coord-descent — same depth as parity to maintain
/// placement quality. The dominant cost per search call is the ~360ms CDE
/// session build (O(N) items), making eval savings from fewer coord-descent
/// rounds negligible. Good quality per call leads to faster collision resolution
/// and therefore fewer colliding items in subsequent passes.
pub const SPARROW_DENSE_COORD_DESCENTS: usize = 4;
/// Use the same no-improve limit as parity: the deadline governs, not this
/// counter (at ~40s/iter, 200 iterations >> 900s budget).
pub const SPARROW_DENSE_NO_IMPROVE_LIMIT: usize = 200;
pub const SPARROW_DENSE_MAX_CONSEC_FAILED_ATTEMPTS: usize = 15;
pub const SPARROW_PARITY_LARGE_ITEM_CH_AREA_CUTOFF_PERCENTILE: f64 = 0.75;

impl SparrowConfig {
    pub fn from_solver_input(
        time_limit_s: f64,
        backend: CollisionBackendKind,
        rotation_context: RotationResolveContext,
        seed: u64,
    ) -> Self {
        Self {
            profile: SparrowProfile::SparrowStrictParity,
            time_limit_s: time_limit_s.max(0.1),
            collision_backend: backend,
            rotation_context,
            seed,
            worker_count: SPARROW_PARITY_WORKERS,
            focused_samples: SPARROW_PARITY_SEPARATOR_FOCUSED_SAMPLES,
            global_grid_n: 4,
            coord_descent_steps: SPARROW_PARITY_COORD_DESCENTS,
            rotation_wiggle_deg: 6.0,
        }
    }

    pub fn with_profile(mut self, profile: SparrowProfile) -> Self {
        self.profile = profile;
        if profile == SparrowProfile::SparrowStrictParity {
            self.worker_count = SPARROW_PARITY_WORKERS;
            self.focused_samples = SPARROW_PARITY_SEPARATOR_FOCUSED_SAMPLES;
            self.coord_descent_steps = SPARROW_PARITY_COORD_DESCENTS;
        }
        self
    }

    pub fn scaled_for_instance_count(&self, instance_count: usize) -> Self {
        let mut cfg = self.clone();
        if cfg.profile == SparrowProfile::SparrowStrictParity {
            cfg.worker_count = SPARROW_PARITY_WORKERS;
            cfg.focused_samples = SPARROW_PARITY_SEPARATOR_FOCUSED_SAMPLES;
            cfg.coord_descent_steps = SPARROW_PARITY_COORD_DESCENTS;
            return cfg;
        }
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
///
/// `Default` checks `SGH_Q29_CDE_PROFILE=1` to enable profiling fields.
/// All profiling fields are zero when `profiling_enabled` is false.
#[derive(Debug, Clone)]
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
    // ── SGH-Q29 CDE hotspot profiler (active only when SGH_Q29_CDE_PROFILE=1) ─
    /// True when SGH_Q29_CDE_PROFILE=1 was set at solver startup.
    pub profiling_enabled: bool,
    /// Total wall-time spent inside `native_search_placement` calls (ms).
    pub profile_search_total_ms: f64,
    /// Wall-time for `build_sheet_session` (fallback fresh-session builds, ms).
    pub profile_session_build_ms: f64,
    /// Wall-time for `deregister_item` calls inside `native_search_placement` (ms).
    pub profile_deregister_ms: f64,
    /// Wall-time for `transform_base_to_candidate` (candidate shape prep, ms).
    pub profile_candidate_transform_ms: f64,
    /// Wall-time inside `collect_poly_collisions_in_detector_custom` (CDE query+collect, ms).
    pub profile_cde_query_collect_ms: f64,
    /// Wall-time for loss quantification inside the hazard collector (hazard_loss, ms).
    /// In our impl quantification happens inside collect_poly_collisions; this is a
    /// subset of profile_cde_query_collect_ms separated by timing the quantify calls.
    pub profile_hazard_loss_ms: f64,
    /// Wall-time for the bbox fit check (boundary/broadphase pre-check) in score_candidate (ms).
    pub profile_boundary_check_ms: f64,
    /// Number of candidates rejected by bbox fit check before any CDE work.
    pub profile_broadphase_reject_count: usize,
    /// Number of times `collect_poly_collisions_in_detector_custom` returned early due to loss bound.
    pub profile_early_termination_count: usize,
    // ── SGH-Q30 reusable search profiler (active only when SGH_Q30_SEARCH_PROFILE=1) ──
    pub q30_profile: SearchProfiler,
}

impl Default for SparrowDiagnostics {
    fn default() -> Self {
        let profiling_enabled = std::env::var("SGH_Q29_CDE_PROFILE").as_deref() == Ok("1");
        Self {
            invoked: false,
            seed_placements: 0,
            seed_unplaced: 0,
            initial_raw_loss: 0.0,
            initial_weighted_loss: 0.0,
            final_raw_loss: 0.0,
            final_weighted_loss: 0.0,
            best_infeasible_raw_loss: 0.0,
            best_infeasible_weighted_loss: 0.0,
            iterations: 0,
            moves_attempted: 0,
            moves_accepted: 0,
            rollbacks: 0,
            gls_weight_updates: 0,
            converged: false,
            collision_graph_initial_pairs: 0,
            collision_graph_final_pairs: 0,
            boundary_violations_initial: 0,
            boundary_violations_final: 0,
            search_position_calls: 0,
            search_position_samples: 0,
            search_global_samples: 0,
            search_focused_samples: 0,
            search_refined_samples: 0,
            search_coord_descent_steps: 0,
            search_unsupported_samples: 0,
            search_cross_sheet_calls: 0,
            search_rotation_wiggle: 0,
            search_best_eval: 0.0,
            lbf_fallback_used: 0,
            worker_count: 0,
            worker_passes: 0,
            worker_candidates_evaluated: 0,
            worker_commits: 0,
            worker_rollbacks: 0,
            worker_best_loss: 0.0,
            worker_colliding_items_seen: 0,
            worker_items_moved: 0,
            multi_target_items_attempted: 0,
            multi_target_items_accepted: 0,
            multi_target_items_rejected: 0,
            topk_target_count: 0,
            separator_invocations: 0,
            separator_strikes: 0,
            exploration_attempts: 0,
            exploration_pool_inserts: 0,
            exploration_pool_restores: 0,
            exploration_disruptions_large_item_swap: 0,
            exploration_disruptions_cross_sheet: 0,
            exploration_disruptions_rotation: 0,
            excluded_phase_passes: 0,
            quantified_pair_queries: 0,
            quantified_boundary_queries: 0,
            unsupported_queries: 0,
            native_model_active: false,
            native_tracker_active: false,
            old_core_used: false,
            native_problem_instances: 0,
            native_tracker_full_rebuilds: 0,
            native_tracker_incremental_updates: 0,
            dense_guard_used: false,
            dense_real_run: false,
            dense_partial_reason: None,
            dense_validated_placements: None,
            dense_unresolved_instances: Vec::new(),
            dense_final_validation_ran: false,
            profiling_enabled,
            profile_search_total_ms: 0.0,
            profile_session_build_ms: 0.0,
            profile_deregister_ms: 0.0,
            profile_candidate_transform_ms: 0.0,
            profile_cde_query_collect_ms: 0.0,
            profile_hazard_loss_ms: 0.0,
            profile_boundary_check_ms: 0.0,
            profile_broadphase_reject_count: 0,
            profile_early_termination_count: 0,
            q30_profile: SearchProfiler::new_from_env(),
        }
    }
}
