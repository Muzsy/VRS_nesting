use std::time::Instant;

use super::compress::CompressionPhase;
use super::explore::ExplorationPhase;
use super::score::{ScoreModel, ScoreResult, ScoreWeights};
use super::working::WorkingLayout;
use crate::io::CollisionBackendKind;
use crate::item::Part;
use crate::rotation_policy::RotationResolveContext;
use crate::sheet::SheetShape;

fn phase_timing_enabled() -> bool {
    std::env::var("VRS_CDE_OBSERVABILITY_TIMING").map(|v| v == "1").unwrap_or(false)
}

fn phase_t_start(enabled: bool) -> Option<Instant> {
    if enabled { Some(Instant::now()) } else { None }
}

fn phase_t_ms(start: Option<Instant>) -> Option<f64> {
    start.map(|t| t.elapsed().as_secs_f64() * 1000.0)
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PhaseStopReason {
    Converged,
    MaxIterations,
    TimeLimit,
    NoImprovement,
    InfeasibleOnly,
    BudgetExhausted,
}

impl std::fmt::Display for PhaseStopReason {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Converged => write!(f, "converged"),
            Self::MaxIterations => write!(f, "max_iterations"),
            Self::TimeLimit => write!(f, "time_limit"),
            Self::NoImprovement => write!(f, "no_improvement"),
            Self::InfeasibleOnly => write!(f, "infeasible_only"),
            Self::BudgetExhausted => write!(f, "budget_exhausted"),
        }
    }
}

impl Default for PhaseStopReason {
    fn default() -> Self {
        Self::Converged
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PhaseType {
    Exploration,
    Compression,
}

impl std::fmt::Display for PhaseType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Exploration => write!(f, "exploration"),
            Self::Compression => write!(f, "compression"),
        }
    }
}

impl Default for PhaseType {
    fn default() -> Self {
        Self::Exploration
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct PhaseBudget {
    pub max_iterations: usize,
    pub time_limit_s: f64,
}

impl Default for PhaseBudget {
    fn default() -> Self {
        Self::new(100, 60.0)
    }
}

impl PhaseBudget {
    pub fn new(max_iterations: usize, time_limit_s: f64) -> Self {
        Self {
            max_iterations,
            time_limit_s,
        }
    }

    pub fn unlimited() -> Self {
        Self {
            max_iterations: usize::MAX,
            time_limit_s: f64::MAX,
        }
    }
}

#[derive(Debug, Clone, Default)]
pub struct PhaseDiagnostics {
    pub phase_type: PhaseType,
    pub iterations_run: usize,
    pub exploration_iterations: usize,
    pub compression_iterations: usize,
    pub bpp_attempts: usize,
    pub stop_reason: PhaseStopReason,
    pub incumbent_preserved: bool,
    pub best_score: f64,
    pub initial_score: f64,
    pub pool_size: usize,
    pub disruption_attempts: usize,
    pub disruption_successes: usize,
    /// Q20: rotation refinement diagnostics (accumulated during CompressionPhase).
    pub rotation_refinement_enabled: bool,
    pub rotation_refinement_attempts: usize,
    pub rotation_refinement_accepts: usize,
    /// Best score improvement from a single accepted refinement. 0.0 if no accepts.
    pub rotation_refinement_best_delta: f64,
}

impl PhaseDiagnostics {
    pub fn new(phase_type: PhaseType) -> Self {
        Self {
            phase_type,
            stop_reason: PhaseStopReason::Converged,
            ..Default::default()
        }
    }

    pub fn summary(&self) -> String {
        format!(
            "phase={} iter={} stop={} preserved={} initial={:.3} best={:.3} pool={} disruption_att={} disruption_ok={} refine_enabled={} refine_att={} refine_ok={} refine_best_delta={:.4}",
            self.phase_type,
            self.iterations_run,
            self.stop_reason,
            self.incumbent_preserved,
            self.initial_score,
            self.best_score,
            self.pool_size,
            self.disruption_attempts,
            self.disruption_successes,
            self.rotation_refinement_enabled,
            self.rotation_refinement_attempts,
            self.rotation_refinement_accepts,
            self.rotation_refinement_best_delta,
        )
    }
}

#[derive(Debug, Clone)]
pub struct PhaseResult {
    pub layout: WorkingLayout,
    pub score: ScoreResult,
    pub initial_score: f64,
    pub best_score: f64,
    pub diagnostics: PhaseDiagnostics,
    pub unplaced: Vec<crate::io::Unplaced>,
    /// Per-phase wall-clock timing. Only populated when VRS_CDE_OBSERVABILITY_TIMING=1.
    pub exploration_ms: Option<f64>,
    pub compression_ms: Option<f64>,
    pub bpp_ms: Option<f64>,
}

impl PhaseResult {
    pub fn improved(&self) -> bool {
        self.best_score < self.initial_score
    }
}

#[derive(Debug, Clone)]
pub struct PhaseConfig {
    pub seed: i64,
    pub worker_count: usize,
    pub exploration_budget: PhaseBudget,
    pub compression_budget: PhaseBudget,
    pub bpp_budget: PhaseBudget,
    pub bpp_max_eliminations: usize,
    pub rotation_context: RotationResolveContext,
    pub score_weights: ScoreWeights,
    pub pool_capacity: usize,
    pub disruption_top_percentile: f64,
    pub disruption_max_attempts: usize,
    /// Collision backend to use for internal scoring, separator, and commit gates.
    /// Default: Bbox (unchanged from pre-Q11 behavior).
    pub collision_backend: CollisionBackendKind,
}

impl Default for PhaseConfig {
    fn default() -> Self {
        Self {
            seed: 0,
            worker_count: 1,
            exploration_budget: PhaseBudget::new(100, 60.0),
            compression_budget: PhaseBudget::new(50, 30.0),
            bpp_budget: PhaseBudget::new(16, 30.0),
            bpp_max_eliminations: 16,
            rotation_context: RotationResolveContext::legacy_default(),
            score_weights: ScoreWeights::default(),
            pool_capacity: 20,
            disruption_top_percentile: 0.2,
            disruption_max_attempts: 3,
            collision_backend: CollisionBackendKind::default(),
        }
    }
}

impl PhaseConfig {
    pub fn deterministic_default() -> Self {
        Self::default()
    }

    pub fn make_separator_config(&self) -> super::separator::VrsSeparatorConfig {
        super::separator::VrsSeparatorConfig {
            seed: self.seed as u64,
            worker_count: self.worker_count,
            rotation_context: self.rotation_context.clone(),
            collision_backend: self.collision_backend.clone(),
            ..super::separator::VrsSeparatorConfig::default()
        }
    }
}

pub struct PhaseOptimizer {
    config: PhaseConfig,
    score_model: ScoreModel,
}

impl PhaseOptimizer {
    pub fn new(config: PhaseConfig) -> Self {
        let score_model = ScoreModel::new(config.score_weights.clone());
        Self {
            config,
            score_model,
        }
    }

    pub fn run(&self, layout: WorkingLayout, parts: &[Part], sheets: &[SheetShape]) -> PhaseResult {
        let timing = phase_timing_enabled();

        let initial_score = self.score_model.score_with_backend(
            &layout.placements,
            &layout.unplaced,
            parts,
            sheets,
            &self.config.collision_backend,
        );
        let initial_score_val = initial_score.total_cost;

        let t_explore = phase_t_start(timing);
        let (explored_layout, exploration_diag) = self.run_exploration(layout, parts, sheets);
        let exploration_ms = phase_t_ms(t_explore);

        let t_compress = phase_t_start(timing);
        let (compressed_layout, compression_diag) =
            self.run_compression(explored_layout, parts, sheets);
        let compression_ms = phase_t_ms(t_compress);

        let t_bpp = phase_t_start(timing);
        let (bpp_layout, bpp_diag) = self.run_bpp(compressed_layout, parts, sheets);
        let bpp_ms = phase_t_ms(t_bpp);

        let unplaced = bpp_layout.unplaced.clone();
        let final_score = self.score_model.score_with_backend(
            &bpp_layout.placements,
            &bpp_layout.unplaced,
            parts,
            sheets,
            &self.config.collision_backend,
        );

        // PhaseResult.best_score == result.score.total_cost (the final layout score).
        // Best-seen during exploration/compression/BPP is tracked in per-phase diagnostics,
        // not surfaced here — claiming a score for a layout we don't return would be misleading.
        let best_score = final_score.total_cost;

        PhaseResult {
            layout: bpp_layout,
            score: final_score,
            initial_score: initial_score_val,
            best_score,
            diagnostics: PhaseDiagnostics {
                phase_type: PhaseType::Exploration,
                iterations_run: exploration_diag
                    .iterations_run
                    .saturating_add(compression_diag.iterations_run)
                    .saturating_add(bpp_diag.attempts),
                exploration_iterations: exploration_diag.iterations_run,
                compression_iterations: compression_diag.iterations_run,
                bpp_attempts: bpp_diag.attempts,
                stop_reason: PhaseStopReason::Converged,
                incumbent_preserved: true,
                best_score,
                initial_score: initial_score_val,
                pool_size: exploration_diag.pool_size,
                disruption_attempts: exploration_diag.disruption_attempts,
                disruption_successes: exploration_diag.disruption_successes,
                rotation_refinement_enabled: compression_diag.rotation_refinement_enabled,
                rotation_refinement_attempts: compression_diag.rotation_refinement_attempts,
                rotation_refinement_accepts: compression_diag.rotation_refinement_accepts,
                rotation_refinement_best_delta: compression_diag.rotation_refinement_best_delta,
            },
            unplaced,
            exploration_ms,
            compression_ms,
            bpp_ms,
        }
    }

    fn run_exploration(
        &self,
        layout: WorkingLayout,
        parts: &[Part],
        sheets: &[SheetShape],
    ) -> (WorkingLayout, PhaseDiagnostics) {
        let mut phase = ExplorationPhase::new(self.config.clone());
        phase.run(layout, parts, sheets)
    }

    fn run_compression(
        &self,
        layout: WorkingLayout,
        parts: &[Part],
        sheets: &[SheetShape],
    ) -> (WorkingLayout, PhaseDiagnostics) {
        let phase = CompressionPhase::new(self.config.clone());
        phase.run(layout, parts, sheets)
    }

    fn run_bpp(
        &self,
        layout: WorkingLayout,
        parts: &[Part],
        sheets: &[SheetShape],
    ) -> (WorkingLayout, super::bpp_phase::BppPhaseDiagnostics) {
        let phase = super::bpp_phase::BppPhase::new(self.config.clone());
        phase.run(layout, parts, sheets)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::io::Placement;
    use crate::optimizer::explore::make_test_sheet;
    use crate::optimizer::repair::find_violations;

    fn make_simple_layout() -> (
        WorkingLayout,
        Vec<crate::item::Part>,
        Vec<crate::sheet::SheetShape>,
    ) {
        let parts = vec![crate::item::Part {
            id: "A".into(),
            width: 20.0,
            height: 20.0,
            quantity: 2,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: None,
            prepared_outer_points: None,
            rotation_policy: None,
        }];
        let sheets = vec![make_test_sheet()];
        let placements = vec![
            Placement {
                instance_id: "A__0001".into(),
                part_id: "A".into(),
                sheet_index: 0,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
            Placement {
                instance_id: "A__0002".into(),
                part_id: "A".into(),
                sheet_index: 0,
                x: 20.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);
        (layout, parts, sheets)
    }

    fn small_budget_config() -> PhaseConfig {
        let mut cfg = PhaseConfig::deterministic_default();
        cfg.exploration_budget = PhaseBudget::new(2, 0.0);
        cfg.compression_budget = PhaseBudget::new(1, 0.0);
        cfg.bpp_budget = PhaseBudget::new(4, 0.0);
        cfg.bpp_max_eliminations = 4;
        cfg
    }

    /// Config with exploration/compression disabled so only BPP runs.
    fn bpp_only_config() -> PhaseConfig {
        let mut cfg = PhaseConfig::deterministic_default();
        cfg.exploration_budget = PhaseBudget::new(0, 0.0);
        cfg.compression_budget = PhaseBudget::new(0, 0.0);
        cfg.bpp_budget = PhaseBudget::new(512, 0.0);
        cfg.bpp_max_eliminations = 8;
        cfg
    }

    // -----------------------------------------------------------------------
    // SGH-Q18A-R1: phase timing tests
    // -----------------------------------------------------------------------

    #[test]
    fn phase_optimizer_timing_fields_absent_by_default() {
        // Without VRS_CDE_OBSERVABILITY_TIMING=1, all timing fields must be None.
        // This test relies on the env var NOT being set in the normal test environment.
        // If the env var is set externally, this test is intentionally skipped via the guard below.
        if std::env::var("VRS_CDE_OBSERVABILITY_TIMING").ok().as_deref() == Some("1") {
            return; // skip when timing is explicitly enabled by the test runner
        }
        let config = small_budget_config();
        let optimizer = PhaseOptimizer::new(config);
        let (layout, parts, sheets) = make_simple_layout();
        let result = optimizer.run(layout, &parts, &sheets);
        assert!(result.exploration_ms.is_none(), "exploration_ms must be None by default");
        assert!(result.compression_ms.is_none(), "compression_ms must be None by default");
        assert!(result.bpp_ms.is_none(), "bpp_ms must be None by default");
    }

    #[test]
    fn phase_timing_helpers_absent_when_disabled() {
        // phase_t_start(false) → None; phase_t_ms(None) → None.
        let start = phase_t_start(false);
        assert!(start.is_none(), "phase_t_start(false) must return None");
        let ms = phase_t_ms(None);
        assert!(ms.is_none(), "phase_t_ms(None) must return None");
    }

    #[test]
    fn phase_timing_helpers_present_when_enabled() {
        // phase_t_start(true) → Some; phase_t_ms(Some) → Some non-negative.
        let start = phase_t_start(true);
        assert!(start.is_some(), "phase_t_start(true) must return Some(Instant)");
        let ms = phase_t_ms(start);
        assert!(ms.is_some(), "phase_t_ms(Some) must return Some(f64)");
        assert!(ms.unwrap() >= 0.0, "timing must be non-negative");
    }

    #[test]
    fn phase_config_default_is_deterministic() {
        let cfg1 = PhaseConfig::deterministic_default();
        let cfg2 = PhaseConfig::deterministic_default();
        assert_eq!(cfg1.seed, cfg2.seed);
        assert_eq!(cfg1.worker_count, cfg2.worker_count);
    }

    #[test]
    fn phase_budget_unlimited() {
        let b = PhaseBudget::unlimited();
        assert_eq!(b.max_iterations, usize::MAX);
        assert_eq!(b.time_limit_s, f64::MAX);
    }

    #[test]
    fn phase_diagnostics_summary_contains_fields() {
        let d = PhaseDiagnostics::new(PhaseType::Exploration);
        let s = d.summary();
        assert!(s.contains("exploration"));
    }

    #[test]
    fn phase_optimizer_invokes_real_phases_non_stub_diagnostics() {
        let config = small_budget_config();
        let optimizer = PhaseOptimizer::new(config);
        let (layout, parts, sheets) = make_simple_layout();

        let result = optimizer.run(layout, &parts, &sheets);

        assert!(
            result.diagnostics.iterations_run > 0,
            "iterations_run must be > 0 when budget > 0; stub would return 0"
        );
    }

    #[test]
    fn phase_result_unplaced_matches_layout_unplaced() {
        let config = small_budget_config();
        let optimizer = PhaseOptimizer::new(config);
        let (layout, parts, sheets) = make_simple_layout();

        let result = optimizer.run(layout, &parts, &sheets);

        assert_eq!(
            result.unplaced.len(),
            result.layout.unplaced.len(),
            "PhaseResult.unplaced must match result.layout.unplaced"
        );
    }

    #[test]
    fn phase_result_score_matches_layout_score() {
        let config = small_budget_config();
        let score_model = crate::optimizer::score::ScoreModel::new(config.score_weights.clone());
        let optimizer = PhaseOptimizer::new(config);
        let (layout, parts, sheets) = make_simple_layout();

        let result = optimizer.run(layout, &parts, &sheets);

        let actual = score_model.score(
            &result.layout.placements,
            &result.layout.unplaced,
            &parts,
            &sheets,
        );
        assert!(
            (actual.total_cost - result.score.total_cost).abs() < 1e-9,
            "PhaseResult.score must match scoring the result layout: got {} vs {}",
            actual.total_cost,
            result.score.total_cost
        );
    }

    #[test]
    fn phase_optimizer_invokes_bpp_phase_loop() {
        // Layout with 2 items on 2 separate sheets; both fit on one 100×100 sheet.
        // With exploration/compression disabled, only BPP runs. It should reduce to 1 sheet.
        let parts = vec![crate::item::Part {
            id: "A".into(),
            width: 20.0,
            height: 20.0,
            quantity: 2,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: None,
            prepared_outer_points: None,
            rotation_policy: None,
        }];
        let sheets = vec![make_test_sheet(), make_test_sheet()];
        let placements = vec![
            Placement {
                instance_id: "A__0001".into(),
                part_id: "A".into(),
                sheet_index: 0,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
            Placement {
                instance_id: "A__0002".into(),
                part_id: "A".into(),
                sheet_index: 1,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
        ];
        let layout = WorkingLayout::new(placements, vec![], 2, 0);

        let config = bpp_only_config();
        let optimizer = PhaseOptimizer::new(config);
        let result = optimizer.run(layout, &parts, &sheets);

        use crate::optimizer::multisheet::compute_sheet_count_used;
        let final_sheet_count = compute_sheet_count_used(&result.layout.placements);
        assert_eq!(
            final_sheet_count, 1,
            "PhaseOptimizer must invoke BPP which consolidates 2 sheets to 1"
        );
        assert!(find_violations(&result.layout.placements, &parts, &sheets).is_empty());
    }

    #[test]
    fn phase_result_score_layout_consistency_after_bpp() {
        let config = bpp_only_config();
        let score_model = crate::optimizer::score::ScoreModel::new(config.score_weights.clone());
        let parts = vec![crate::item::Part {
            id: "A".into(),
            width: 20.0,
            height: 20.0,
            quantity: 2,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: None,
            prepared_outer_points: None,
            rotation_policy: None,
        }];
        let sheets = vec![make_test_sheet(), make_test_sheet()];
        let placements = vec![
            Placement {
                instance_id: "A__0001".into(),
                part_id: "A".into(),
                sheet_index: 0,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
            Placement {
                instance_id: "A__0002".into(),
                part_id: "A".into(),
                sheet_index: 1,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
        ];
        let layout = WorkingLayout::new(placements, vec![], 2, 0);

        let result = PhaseOptimizer::new(config).run(layout, &parts, &sheets);

        let actual_score = score_model.score(
            &result.layout.placements,
            &result.layout.unplaced,
            &parts,
            &sheets,
        );
        assert!(
            (actual_score.total_cost - result.score.total_cost).abs() < 1e-9,
            "result.score must match score(result.layout) after BPP: got {} vs {}",
            actual_score.total_cost,
            result.score.total_cost
        );
        assert_eq!(result.unplaced.len(), result.layout.unplaced.len());
    }

    #[test]
    fn phase_result_best_score_equals_final_layout_score_after_bpp() {
        let config = bpp_only_config();
        let parts = vec![crate::item::Part {
            id: "A".into(),
            width: 20.0,
            height: 20.0,
            quantity: 2,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: None,
            prepared_outer_points: None,
            rotation_policy: None,
        }];
        let sheets = vec![make_test_sheet(), make_test_sheet()];
        let placements = vec![
            Placement {
                instance_id: "A__0001".into(),
                part_id: "A".into(),
                sheet_index: 0,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
            Placement {
                instance_id: "A__0002".into(),
                part_id: "A".into(),
                sheet_index: 1,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
        ];
        let layout = WorkingLayout::new(placements, vec![], 2, 0);

        let result = PhaseOptimizer::new(config).run(layout, &parts, &sheets);

        assert_eq!(
            result.best_score.to_bits(),
            result.score.total_cost.to_bits(),
            "PhaseResult.best_score must equal result.score.total_cost: best={} score={}",
            result.best_score,
            result.score.total_cost
        );
    }

    #[test]
    fn same_seed_phase_optimizer_determinism() {
        let config = small_budget_config();
        let (layout, parts, sheets) = make_simple_layout();

        let r1 = PhaseOptimizer::new(config.clone()).run(layout.snapshot(), &parts, &sheets);
        let r2 = PhaseOptimizer::new(config).run(layout.snapshot(), &parts, &sheets);

        assert_eq!(
            r1.layout.placements.len(),
            r2.layout.placements.len(),
            "determinism: placement count"
        );
        for (a, b) in r1.layout.placements.iter().zip(r2.layout.placements.iter()) {
            assert_eq!(a.instance_id, b.instance_id, "determinism: instance_id");
            assert_eq!(a.sheet_index, b.sheet_index, "determinism: sheet_index");
            assert_eq!(a.rotation_deg, b.rotation_deg, "determinism: rotation_deg");
            assert_eq!(a.x.to_bits(), b.x.to_bits(), "determinism: x");
            assert_eq!(a.y.to_bits(), b.y.to_bits(), "determinism: y");
        }
        assert!(
            find_violations(&r1.layout.placements, &parts, &sheets).is_empty(),
            "determinism run must produce violation-free output"
        );
    }

    // -----------------------------------------------------------------------
    // SGH-Q11 tests
    // -----------------------------------------------------------------------

    #[test]
    fn phase_config_defaults_collision_backend_bbox() {
        use crate::io::CollisionBackendKind;
        let cfg = PhaseConfig::deterministic_default();
        assert!(
            matches!(cfg.collision_backend, CollisionBackendKind::Bbox),
            "PhaseConfig default must use Bbox collision backend"
        );
    }

    #[test]
    fn bbox_default_still_matches_legacy_score() {
        use crate::io::CollisionBackendKind;
        use crate::optimizer::score::ScoreModel;

        let parts = vec![crate::item::Part {
            id: "A".into(), width: 10.0, height: 10.0, quantity: 1,
            allowed_rotations_deg: vec![0], holes_points: None, prepared_holes_points: None,
            outer_points: None, prepared_outer_points: None, rotation_policy: None,
        }];
        let sheets = vec![make_test_sheet()];
        let placements = vec![Placement { instance_id: "A__0001".into(), part_id: "A".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 }];
        let model = ScoreModel::default();
        let legacy = model.score(&placements, &[], &parts, &sheets);
        let bbox = model.score_with_backend(&placements, &[], &parts, &sheets, &CollisionBackendKind::Bbox);

        assert_eq!(legacy.total_cost.to_bits(), bbox.total_cost.to_bits(),
            "Bbox backend must remain bit-compatible with legacy score()");
    }

    #[test]
    fn phase_optimizer_score_uses_backend_for_exact_notch() {
        use crate::io::CollisionBackendKind;
        use crate::optimizer::score::ScoreModel;

        let l_json = serde_json::json!([
            [0.0, 0.0], [40.0, 0.0], [40.0, 20.0],
            [20.0, 20.0], [20.0, 40.0], [0.0, 40.0]
        ]);
        let parts = vec![
            crate::item::Part {
                id: "L".into(), width: 40.0, height: 40.0, quantity: 1,
                allowed_rotations_deg: vec![0], holes_points: None, prepared_holes_points: None,
                outer_points: Some(l_json), prepared_outer_points: None, rotation_policy: None,
            },
            crate::item::Part {
                id: "B".into(), width: 15.0, height: 15.0, quantity: 1,
                allowed_rotations_deg: vec![0], holes_points: None, prepared_holes_points: None,
                outer_points: None, prepared_outer_points: None, rotation_policy: None,
            },
        ];
        let sheets = vec![make_test_sheet()];
        let placements = vec![
            Placement { instance_id: "L__0001".into(), part_id: "L".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 },
            Placement { instance_id: "B__0001".into(), part_id: "B".into(), sheet_index: 0, x: 22.0, y: 22.0, rotation_deg: 0.0 },
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);

        let mut config = PhaseConfig::deterministic_default();
        config.exploration_budget = PhaseBudget::new(0, 0.0);
        config.compression_budget = PhaseBudget::new(0, 0.0);
        config.bpp_budget = PhaseBudget::new(0, 0.0);
        config.bpp_max_eliminations = 0;
        config.collision_backend = CollisionBackendKind::JaguaPolygonExact;

        let expected = ScoreModel::new(config.score_weights.clone()).score_with_backend(
            &layout.placements, &layout.unplaced, &parts, &sheets, &config.collision_backend,
        );
        let bbox = ScoreModel::new(config.score_weights.clone()).score(
            &layout.placements, &layout.unplaced, &parts, &sheets,
        );
        assert!(bbox.breakdown.overlap_violations > expected.breakdown.overlap_violations,
            "fixture must expose a bbox false-positive that exact scoring removes");

        let result = PhaseOptimizer::new(config).run(layout, &parts, &sheets);
        assert!((result.initial_score - expected.total_cost).abs() < 1e-9,
            "PhaseOptimizer initial_score must use the selected exact backend");
    }
}
