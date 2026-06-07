use std::time::Instant;

/// Reusable search-loop profiling module for the native Sparrow solver.
///
/// Enabled by `SGH_Q30_SEARCH_PROFILE=1`. Zero overhead when disabled.
///
/// # Timing accounting model (`timing_accounting_mode = "mixed_with_notes"`)
///
/// **Exclusive** sub-buckets of `search_total_ms` (their sum ≤ search_total):
///   - `session_build_ms`            fallback fresh-session builds only
///   - `deregister_reregister_ms`    deregister_item calls (reregister is in worker.rs)
///   - `evaluate_sample_total_ms`    ALL evaluate_sample calls, incl. from coord_descent
///   - `sample_generation_ms`        UniformBBoxSampler.sample() calls
///   - `best_samples_insert_dedup_ms` BestSamples.report() calls
///
/// **Nested** (informational; NOT subtracted in `other_unaccounted_ms`):
///   - `coord_descent_total_ms`           wraps evaluate_sample calls within
///   - `cde_query_collect_ms`             sub of each evaluate_sample
///   - `candidate_transform_prepare_ms`   sub of each evaluate_sample
///   - `boundary_check_ms`               sub of each evaluate_sample
///
/// `other_unaccounted_ms` = search_total
///   - session_build_ms - deregister_reregister_ms
///   - evaluate_sample_total_ms - sample_generation_ms - best_samples_insert_dedup_ms
///
/// # Future admin integration
///
/// `finalize()` populates all derived fields. The snapshot can be exported via:
///   - `optimizer_diagnostics.sparrow_q30_profile_*` JSON fields (current path)
///   - sidecar artifact file (call site writes `serde_json::to_string(profiler)`)
///   - run-level admin observability stream (pass snapshot to a tracing subscriber)
#[derive(Debug, Clone, Default)]
pub struct SearchProfiler {
    /// True when `SGH_Q30_SEARCH_PROFILE=1` was set at solver startup.
    pub enabled: bool,
    /// Set true by `native_search_placement` (separator path) before entering
    /// `search_placement`, false afterwards. Prevents LBF seeding calls (via
    /// `lbf.rs`) from contaminating separator-only timing buckets.
    pub profiling_scope_active: bool,

    // ── counters ─────────────────────────────────────────────────────────────
    /// Total `native_search_placement` invocations.
    pub native_search_calls: usize,
    /// Total `evaluate_sample` calls (includes calls from coord_descent).
    pub evaluate_sample_calls: usize,
    /// Candidates that passed the bbox broad-phase check (= `search_position_samples`).
    pub candidates_evaluated: usize,
    pub global_samples_generated: usize,
    pub focused_samples_generated: usize,
    /// Total `refine_coord_desc` invocations.
    pub coord_descent_runs: usize,
    /// Total coord-descent axis-evaluation steps (each `ask()` produces 2 candidates).
    pub coord_descent_steps: usize,
    pub best_samples_insert_attempts: usize,
    pub best_samples_inserted: usize,
    /// Attempts rejected because a spatial duplicate with better eval already exists.
    /// Note: not separately measurable from upper-bound-exceeded rejects without an
    /// enum return from `BestSamples::report()`. Populated by `best_samples.rs`.
    pub best_samples_dedup_rejects: usize,
    /// = `global_samples_generated + focused_samples_generated` (derived at `finalize`).
    pub rng_shuffle_or_sample_loop_count: usize,
    pub early_termination_count: usize,
    pub broadphase_reject_count: usize,

    // ── timing (ms) ──────────────────────────────────────────────────────────
    /// Total wall-time inside all `native_search_placement` calls.
    pub search_total_ms: f64,
    /// Wall-time for `UniformBBoxSampler::sample()` calls (RNG + clip).
    pub sample_generation_ms: f64,
    /// Wall-time for `BestSamples::report()` calls (insert + dedup + sort).
    pub best_samples_insert_dedup_ms: f64,
    /// NESTED: total wall-time for all `refine_coord_desc` calls (incl. evaluate_sample within).
    pub coord_descent_total_ms: f64,
    /// EXCLUSIVE: total wall-time for ALL `evaluate_sample` calls regardless of caller.
    pub evaluate_sample_total_ms: f64,
    /// DERIVED: evaluate_sample_total - boundary_check - candidate_transform - cde_query.
    pub evaluator_orchestration_ms: f64,
    /// ALIAS: = `sample_generation_ms` (derived at `finalize`).
    pub rng_shuffle_sample_loop_ms: f64,
    /// Sub of evaluate_sample: `transform_base_to_candidate` cost.
    pub candidate_transform_prepare_ms: f64,
    /// Sub of evaluate_sample: `collect_poly_collisions_in_detector_custom` cost.
    pub cde_query_collect_ms: f64,
    /// ALIAS: = `cde_query_collect_ms` (same code path; derived at `finalize`).
    pub specialized_pipeline_ms: f64,
    /// Sub of cde_query: hazard quantification (not separately timed in current impl).
    /// Currently always 0.0; future instrumentation point.
    pub hazard_loss_ms: f64,
    /// Sub of evaluate_sample: bbox fit check (broad-phase, before CDE work).
    pub boundary_check_ms: f64,
    /// Fallback fresh-session builds only (primary live session is built in `worker.rs`).
    pub session_build_ms: f64,
    /// `deregister_item` calls inside `native_search_placement` (reregister is in worker.rs).
    pub deregister_reregister_ms: f64,
    /// DERIVED: search_total minus all exclusive sub-buckets.
    pub other_unaccounted_ms: f64,
    /// DERIVED: evaluate_sample_total / candidates_evaluated.
    pub per_candidate_avg_ms: f64,
    /// DERIVED: evaluate_sample_total / evaluate_sample_calls.
    pub per_evaluate_sample_avg_ms: f64,
    /// DERIVED: search_total / native_search_calls.
    pub per_search_avg_ms: f64,
}

impl SearchProfiler {
    /// Construct with env-var check. Checks `SGH_Q30_SEARCH_PROFILE=1`.
    pub fn new_from_env() -> Self {
        let enabled = std::env::var("SGH_Q30_SEARCH_PROFILE").as_deref() == Ok("1");
        Self {
            enabled,
            ..Default::default()
        }
    }

    /// Populate all derived / aliased fields. Call once after measurements complete.
    pub fn finalize(&mut self) {
        self.rng_shuffle_or_sample_loop_count =
            self.global_samples_generated + self.focused_samples_generated;
        self.rng_shuffle_sample_loop_ms = self.sample_generation_ms;
        self.specialized_pipeline_ms = self.cde_query_collect_ms;
        self.evaluator_orchestration_ms = (self.evaluate_sample_total_ms
            - self.boundary_check_ms
            - self.candidate_transform_prepare_ms
            - self.cde_query_collect_ms)
            .max(0.0);
        let exclusive_measured = self.session_build_ms
            + self.deregister_reregister_ms
            + self.evaluate_sample_total_ms
            + self.sample_generation_ms
            + self.best_samples_insert_dedup_ms;
        self.other_unaccounted_ms = (self.search_total_ms - exclusive_measured).max(0.0);
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
