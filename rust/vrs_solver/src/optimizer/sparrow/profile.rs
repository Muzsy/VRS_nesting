use std::time::Instant;

/// Reusable search-loop profiling module for the native Sparrow solver.
///
/// Enabled by `SGH_Q30_R1_EXCLUSIVE_PROFILE=1` (R1 exclusive timing tree)
/// or by `SGH_Q30_SEARCH_PROFILE=1` (Q30 mixed-with-notes mode, legacy).
/// Zero overhead when disabled.
///
/// # Timing accounting models
///
/// ## Q30-R1: `search_timing_accounting_mode = "exclusive"` (R1 exclusive flag)
///
/// All measured buckets in `search_accounted_ms` are mutually exclusive —
/// no nested fields. `search_unaccounted_ms = search_total_ms - search_accounted_ms`.
/// PASS requires `search_unaccounted_ratio_pct <= 15.0`.
///
/// ## Q30: `timing_accounting_mode = "mixed_with_notes"` (legacy flag only)
///
/// Some fields nested; `other_unaccounted_ms` uses the Q30 formula.
///
/// # Finalize
///
/// `finalize()` must be called on the solve path before the diagnostics are
/// read. It populates all derived fields (unaccounted ratios, averages, aliases).
///
/// # Future admin integration
///
/// After `finalize()` the snapshot can be exported via:
///   - `optimizer_diagnostics.sparrow_q30_profile_*` JSON fields (current path)
///   - sidecar artifact file (`serde_json::to_string(profiler)`)
///   - run-level admin observability stream (tracing subscriber)
#[derive(Debug, Clone, Default)]
pub struct SearchProfiler {
    /// True when `SGH_Q30_SEARCH_PROFILE=1` or `SGH_Q30_R1_EXCLUSIVE_PROFILE=1`.
    pub enabled: bool,
    /// True when `SGH_Q30_R1_EXCLUSIVE_PROFILE=1` (strict exclusive timing).
    pub r1_exclusive_enabled: bool,
    /// Set true by `native_search_placement` before entering `search_placement`,
    /// false afterwards. Prevents LBF seeding calls from contaminating separator
    /// timing buckets.
    pub profiling_scope_active: bool,

    // ── counters ─────────────────────────────────────────────────────────────
    pub native_search_calls: usize,
    pub evaluate_sample_calls: usize,
    pub evaluate_sample_calls_from_focused: usize,
    pub evaluate_sample_calls_from_global: usize,
    pub evaluate_sample_calls_from_coord_descent: usize,
    /// Candidates that passed the bbox broad-phase check.
    pub candidates_evaluated: usize,
    pub global_samples_generated: usize,
    pub focused_samples_generated: usize,
    pub coord_descent_runs: usize,
    pub coord_descent_steps: usize,
    pub coord_descent_ask_calls: usize,
    pub coord_descent_tell_calls: usize,
    pub best_samples_insert_attempts: usize,
    pub best_samples_inserted: usize,
    pub best_samples_dedup_rejects: usize,
    pub best_samples_best_calls: usize,
    pub best_samples_clone_calls: usize,
    pub deadline_checks: usize,
    pub sheet_loop_iterations: usize,
    /// = `global_samples_generated + focused_samples_generated` (derived).
    pub rng_shuffle_or_sample_loop_count: usize,
    pub early_termination_count: usize,
    pub broadphase_reject_count: usize,
    pub worker_passes: usize,
    pub worker_candidates_evaluated: usize,
    pub worker_candidates_accepted: usize,

    // ── search timing (ms) ───────────────────────────────────────────────────
    pub search_total_ms: f64,
    /// R1 exclusive: `prepare_base_shape_native` (once per search call).
    pub prepare_base_shape_native_ms: f64,
    /// R1 exclusive: `tracker.shapes.clone()` (once per search call).
    pub fixed_shapes_clone_ms: f64,
    /// R1 exclusive: sheet order vec construction inside native_search_placement.
    pub sheet_order_build_ms: f64,
    pub sample_generation_ms: f64,
    pub best_samples_insert_dedup_ms: f64,
    /// R1 exclusive: `BestSamples::best()` calls.
    pub best_samples_best_ms: f64,
    /// R1 exclusive: `best.samples.clone()` before pre-stage coord descent.
    pub best_samples_clone_ms: f64,
    /// NESTED (informational): all `refine_coord_desc` calls incl. evals within.
    pub coord_descent_total_ms: f64,
    /// R1 exclusive: `CoordinateDescent::ask()` calls.
    pub coord_descent_ask_ms: f64,
    /// R1 exclusive: `CoordinateDescent::tell()` calls.
    pub coord_descent_tell_ms: f64,
    /// EXCLUSIVE: ALL `evaluate_sample` calls regardless of caller.
    pub evaluate_sample_total_ms: f64,
    /// DERIVED: evaluate_sample_total - boundary_check - transform - cde_query.
    pub evaluator_orchestration_ms: f64,
    /// ALIAS: = `sample_generation_ms` (derived).
    pub rng_shuffle_sample_loop_ms: f64,
    /// ALIAS: = `sample_generation_ms` (R1 naming, derived).
    pub rng_sample_generation_ms: f64,
    pub candidate_transform_prepare_ms: f64,
    pub cde_query_collect_ms: f64,
    /// ALIAS: = `cde_query_collect_ms` (derived).
    pub specialized_pipeline_ms: f64,
    pub hazard_loss_ms: f64,
    pub boundary_check_ms: f64,
    pub session_build_ms: f64,
    pub deregister_reregister_ms: f64,

    // ── R1 exclusive search accounting (derived in finalize) ─────────────────
    pub search_accounted_ms: f64,
    pub search_unaccounted_ms: f64,
    pub search_unaccounted_ratio_pct: f64,
    /// Q30 legacy unaccounted (Q30 formula, derived in finalize).
    pub other_unaccounted_ms: f64,
    /// DERIVED: evaluate_sample_total / candidates_evaluated.
    pub per_candidate_avg_ms: f64,
    /// DERIVED: evaluate_sample_total / evaluate_sample_calls.
    pub per_evaluate_sample_avg_ms: f64,
    /// DERIVED: search_total / native_search_calls.
    pub per_search_avg_ms: f64,

    // ── Q31 base-shape cache diagnostics (populated from SparrowProblem) ───────
    /// Wall-time spent building the per-part base-shape cache in from_solver_input.
    pub base_shape_cache_build_ms: f64,
    /// Cache hits: instances that reused a pre-built base shape (exclusive, not hotpath).
    pub base_shape_cache_hits: usize,
    /// Cache misses: unique part IDs for which base shape was successfully built.
    pub base_shape_cache_misses: usize,
    pub base_shape_cache_unique_parts: usize,
    /// = cache_hits (instances minus unique parts).
    pub base_shape_cache_reused_instances: usize,
    /// Hot-path calls to prepare_base_shape_native that should be 0 after Q31.
    pub prepare_base_shape_native_hotpath_calls: usize,
    /// Hot-path ms spent in prepare_base_shape_native (should be ~0 after Q31).
    pub prepare_base_shape_native_hotpath_ms: f64,
    pub tracker_transform_from_base_ms: f64,
    pub lbf_base_shape_cache_hits: usize,
    pub search_base_shape_cache_hits: usize,

    // ── total solver runtime timing (Q30-R1) ─────────────────────────────────
    pub total_solver_runtime_ms: f64,
    pub adapter_solve_total_ms: f64,
    pub sparrow_optimizer_solve_total_ms: f64,
    pub seed_lbf_total_ms: f64,
    pub tracker_initial_build_ms: f64,
    pub exploration_total_ms: f64,
    pub separator_total_ms: f64,
    pub separator_iteration_total_ms: f64,
    pub worker_competition_total_ms: f64,
    pub worker_pass_total_ms: f64,
    pub tracker_final_validation_ms: f64,
    pub output_mapping_ms: f64,
    pub other_solver_unaccounted_ms: f64,
    pub other_solver_unaccounted_ratio_pct: f64,
}

impl SearchProfiler {
    /// Construct with env-var check.
    /// `SGH_Q30_R1_EXCLUSIVE_PROFILE=1` enables strict R1 exclusive timing.
    /// `SGH_Q30_SEARCH_PROFILE=1` enables Q30 legacy mode (also enables R1 timers).
    pub fn new_from_env() -> Self {
        let r1_exclusive = std::env::var("SGH_Q30_R1_EXCLUSIVE_PROFILE").as_deref() == Ok("1");
        let q30_legacy = std::env::var("SGH_Q30_SEARCH_PROFILE").as_deref() == Ok("1");
        let enabled = r1_exclusive || q30_legacy;
        Self {
            enabled,
            r1_exclusive_enabled: r1_exclusive,
            ..Default::default()
        }
    }

    /// True when R1 exclusive profiling is active and within a search scope.
    #[inline(always)]
    pub fn r1_active(&self) -> bool {
        self.r1_exclusive_enabled && self.profiling_scope_active
    }

    /// Populate all derived / aliased fields. Must be called on the solve path
    /// before the diagnostics are read.
    pub fn finalize(&mut self) {
        self.rng_shuffle_or_sample_loop_count =
            self.global_samples_generated + self.focused_samples_generated;
        self.rng_shuffle_sample_loop_ms = self.sample_generation_ms;
        self.rng_sample_generation_ms = self.sample_generation_ms;
        self.specialized_pipeline_ms = self.cde_query_collect_ms;
        self.evaluator_orchestration_ms = (self.evaluate_sample_total_ms
            - self.boundary_check_ms
            - self.candidate_transform_prepare_ms
            - self.cde_query_collect_ms)
            .max(0.0);

        // Q30 legacy other_unaccounted (mixed_with_notes formula).
        let exclusive_q30 = self.session_build_ms
            + self.deregister_reregister_ms
            + self.evaluate_sample_total_ms
            + self.sample_generation_ms
            + self.best_samples_insert_dedup_ms;
        self.other_unaccounted_ms = (self.search_total_ms - exclusive_q30).max(0.0);

        // R1 exclusive accounting: all exclusive non-nested search buckets.
        self.search_accounted_ms = self.prepare_base_shape_native_ms
            + self.fixed_shapes_clone_ms
            + self.sheet_order_build_ms
            + self.deregister_reregister_ms
            + self.session_build_ms
            + self.evaluate_sample_total_ms
            + self.sample_generation_ms
            + self.best_samples_insert_dedup_ms
            + self.best_samples_clone_ms
            + self.best_samples_best_ms
            + self.coord_descent_ask_ms
            + self.coord_descent_tell_ms;
        self.search_unaccounted_ms = (self.search_total_ms - self.search_accounted_ms).max(0.0);
        if self.search_total_ms > 0.0 {
            self.search_unaccounted_ratio_pct =
                self.search_unaccounted_ms / self.search_total_ms * 100.0;
        }

        // Total solver runtime accounting (top-level exclusive buckets).
        let runtime_accounted = self.seed_lbf_total_ms
            + self.tracker_initial_build_ms
            + self.exploration_total_ms
            + self.tracker_final_validation_ms
            + self.output_mapping_ms;
        self.other_solver_unaccounted_ms =
            (self.total_solver_runtime_ms - runtime_accounted).max(0.0);
        if self.total_solver_runtime_ms > 0.0 {
            self.other_solver_unaccounted_ratio_pct =
                self.other_solver_unaccounted_ms / self.total_solver_runtime_ms * 100.0;
        }

        if self.native_search_calls > 0 {
            self.per_search_avg_ms = self.search_total_ms / self.native_search_calls as f64;
        }
        if self.evaluate_sample_calls > 0 {
            self.per_evaluate_sample_avg_ms =
                self.evaluate_sample_total_ms / self.evaluate_sample_calls as f64;
        }
        if self.candidates_evaluated > 0 {
            self.per_candidate_avg_ms =
                self.evaluate_sample_total_ms / self.candidates_evaluated as f64;
        }
    }
}

/// Zero-overhead conditional timer.
///
/// ```no_run
/// # use vrs_solver::optimizer::sparrow::profile::{ProfileTimer, SearchProfiler};
/// let mut profiler = SearchProfiler::new_from_env();
/// let t = ProfileTimer::start_if(profiler.enabled);
/// // do_work();
/// t.add_to(&mut profiler.search_total_ms);
/// ```
pub struct ProfileTimer(Option<Instant>);

impl ProfileTimer {
    #[inline(always)]
    pub fn start_if(enabled: bool) -> Self {
        Self(if enabled { Some(Instant::now()) } else { None })
    }

    #[inline(always)]
    pub fn add_to(&self, acc: &mut f64) {
        if let Some(t) = self.0 {
            *acc += t.elapsed().as_secs_f64() * 1000.0;
        }
    }
}
