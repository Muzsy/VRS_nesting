use crate::io::Placement;
use crate::item::Part;
use crate::sheet::SheetShape;
use super::score::{ScoreModel, ScoreResult, ScoreWeights};
use super::working::WorkingLayout;

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
        Self { max_iterations, time_limit_s }
    }

    pub fn unlimited() -> Self {
        Self { max_iterations: usize::MAX, time_limit_s: f64::MAX }
    }
}

#[derive(Debug, Clone, Default)]
pub struct PhaseDiagnostics {
    pub phase_type: PhaseType,
    pub iterations_run: usize,
    pub stop_reason: PhaseStopReason,
    pub incumbent_preserved: bool,
    pub best_score: f64,
    pub initial_score: f64,
    pub pool_size: usize,
    pub disruption_attempts: usize,
    pub disruption_successes: usize,
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
            "phase={} iter={} stop={} preserved={} initial={:.3} best={:.3} pool={} disruption_att={} disruption_ok={}",
            self.phase_type,
            self.iterations_run,
            self.stop_reason,
            self.incumbent_preserved,
            self.initial_score,
            self.best_score,
            self.pool_size,
            self.disruption_attempts,
            self.disruption_successes,
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
    pub score_weights: ScoreWeights,
    pub pool_capacity: usize,
    pub disruption_top_percentile: f64,
    pub disruption_max_attempts: usize,
}

impl Default for PhaseConfig {
    fn default() -> Self {
        Self {
            seed: 0,
            worker_count: 1,
            exploration_budget: PhaseBudget::new(100, 60.0),
            compression_budget: PhaseBudget::new(50, 30.0),
            score_weights: ScoreWeights::default(),
            pool_capacity: 20,
            disruption_top_percentile: 0.2,
            disruption_max_attempts: 3,
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
        Self { config, score_model }
    }

    pub fn run(
        &self,
        mut layout: WorkingLayout,
        parts: &[Part],
        sheets: &[SheetShape],
    ) -> PhaseResult {
        let initial_score = self.score_model.score(
            &layout.placements,
            &layout.unplaced,
            parts,
            sheets,
        );
        let mut best_score = initial_score.total_cost;
        let mut best_layout = layout.snapshot();
        let mut unplaced = layout.unplaced.clone();

        let exploration_diag = self.run_exploration(&mut layout, parts, sheets, &mut unplaced);
        let exploration_best = exploration_diag.best_score;

        if exploration_best < best_score {
            best_score = exploration_best;
            best_layout = layout.snapshot();
        }

        let compression_diag = self.run_compression(&mut layout, parts, sheets);
        let compression_best = compression_diag.best_score;

        if compression_best < best_score {
            best_score = compression_best;
            best_layout = layout.snapshot();
        }

        let final_score = self.score_model.score(
            &best_layout.placements,
            &best_layout.unplaced,
            parts,
            sheets,
        );

        PhaseResult {
            layout: best_layout,
            score: final_score.clone(),
            initial_score: initial_score.total_cost,
            best_score,
            diagnostics: PhaseDiagnostics {
                phase_type: PhaseType::Exploration,
                iterations_run: exploration_diag.iterations_run.saturating_add(compression_diag.iterations_run),
                stop_reason: PhaseStopReason::Converged,
                incumbent_preserved: true,
                best_score,
                initial_score: initial_score.total_cost,
                pool_size: exploration_diag.pool_size,
                disruption_attempts: exploration_diag.disruption_attempts,
                disruption_successes: exploration_diag.disruption_successes,
            },
            unplaced,
        }
    }

    fn run_exploration(
        &self,
        layout: &mut WorkingLayout,
        parts: &[Part],
        sheets: &[SheetShape],
        _unplaced: &mut Vec<crate::io::Unplaced>,
    ) -> PhaseDiagnostics {
        let mut diag = PhaseDiagnostics::new(PhaseType::Exploration);
        diag.initial_score = self.score_model.score(
            &layout.placements,
            &layout.unplaced,
            parts,
            sheets,
        ).total_cost;
        diag.best_score = diag.initial_score;
        diag
    }

    fn run_compression(
        &self,
        layout: &mut WorkingLayout,
        parts: &[Part],
        sheets: &[SheetShape],
    ) -> PhaseDiagnostics {
        let mut diag = PhaseDiagnostics::new(PhaseType::Compression);
        diag.initial_score = self.score_model.score(
            &layout.placements,
            &layout.unplaced,
            parts,
            sheets,
        ).total_cost;
        diag.best_score = diag.initial_score;
        diag
    }
}

#[cfg(test)]
mod tests {
    use super::*;

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
}
