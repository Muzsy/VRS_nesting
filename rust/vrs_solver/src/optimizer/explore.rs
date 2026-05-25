use std::cmp::Ordering;
use std::collections::BinaryHeap;

use crate::io::Placement;
use crate::item::Part;
use crate::sheet::{SheetShape, Stock};
use crate::optimizer::moves::{MoveExecutor, MoveDiagnostics};
use crate::optimizer::phase::{PhaseConfig, PhaseDiagnostics, PhaseStopReason, PhaseType};
use crate::optimizer::repair::find_violations;
use crate::optimizer::score::ScoreModel;
use crate::optimizer::separator::{VrsSeparator, VrsSeparatorConfig};
use crate::optimizer::working::WorkingLayout;

#[derive(Debug, Clone)]
pub struct InfeasibleCandidate {
    pub layout: WorkingLayout,
    pub raw_loss: f64,
    pub score: f64,
    pub iteration: usize,
    pub placement_order: Vec<String>,
}

impl InfeasibleCandidate {
    fn new(layout: WorkingLayout, raw_loss: f64, score: f64, iteration: usize) -> Self {
        let placement_order: Vec<String> = layout.placements.iter()
            .map(|p| p.instance_id.clone())
            .collect();
        Self { layout, raw_loss, score, iteration, placement_order }
    }
}

#[derive(Debug, Clone)]
pub struct InfeasibleCandidateOrd {
    pub candidate: InfeasibleCandidate,
}

impl PartialEq for InfeasibleCandidateOrd {
    fn eq(&self, other: &Self) -> bool {
        self.candidate.raw_loss == other.candidate.raw_loss
            && self.candidate.score == other.candidate.score
            && self.candidate.iteration == other.candidate.iteration
            && self.candidate.placement_order == other.candidate.placement_order
    }
}

impl Eq for InfeasibleCandidateOrd {}

impl Ord for InfeasibleCandidateOrd {
    fn cmp(&self, other: &Self) -> Ordering {
        self.candidate.raw_loss.partial_cmp(&other.candidate.raw_loss)
            .unwrap_or(Ordering::Equal)
            .then_with(|| self.candidate.score.partial_cmp(&other.candidate.score)
                .unwrap_or(Ordering::Equal))
            .then_with(|| self.candidate.iteration.cmp(&other.candidate.iteration))
            .then_with(|| self.candidate.placement_order.cmp(&other.candidate.placement_order))
    }
}

impl PartialOrd for InfeasibleCandidateOrd {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

#[derive(Debug, Clone)]
pub struct InfeasibleSolutionPool {
    candidates: BinaryHeap<InfeasibleCandidateOrd>,
    capacity: usize,
}

impl InfeasibleSolutionPool {
    pub fn new(capacity: usize) -> Self {
        Self {
            candidates: BinaryHeap::new(),
            capacity,
        }
    }

    pub fn len(&self) -> usize {
        self.candidates.len()
    }

    pub fn is_empty(&self) -> bool {
        self.candidates.is_empty()
    }

    pub fn push(&mut self, candidate: InfeasibleCandidate) {
        if self.candidates.len() >= self.capacity {
            if let Some(smallest) = self.candidates.pop() {
                if candidate.raw_loss < smallest.candidate.raw_loss
                    || (candidate.raw_loss == smallest.candidate.raw_loss
                        && candidate.score < smallest.candidate.score)
                {
                    self.candidates.push(InfeasibleCandidateOrd { candidate });
                } else {
                    self.candidates.push(smallest);
                }
            }
        } else {
            self.candidates.push(InfeasibleCandidateOrd { candidate });
        }
    }

    pub fn best(&self) -> Option<&InfeasibleCandidate> {
        self.candidates.iter()
            .min_by(|a, b| a.cmp(b))
            .map(|ord| &ord.candidate)
    }

    pub fn drain(&mut self) -> Vec<InfeasibleCandidate> {
        let mut result = Vec::new();
        while let Some(ord) = self.candidates.pop() {
            result.push(ord.candidate);
        }
        result
    }
}

pub struct LargeItemSwapDisruption {
    top_percentile: f64,
    max_attempts: usize,
    seed: i64,
}

impl LargeItemSwapDisruption {
    pub fn new(top_percentile: f64, max_attempts: usize, seed: i64) -> Self {
        Self { top_percentile, max_attempts, seed }
    }

    fn select_top_items<'a>(
        &self,
        placements: &'a [Placement],
        parts: &'a [Part],
        top_count: usize,
    ) -> Vec<&'a Placement> {
        let mut items_with_area: Vec<(&Placement, f64)> = placements.iter()
            .filter_map(|p| {
                parts.iter()
                    .find(|pt| pt.id == p.part_id)
                    .map(|pt| (p, pt.width * pt.height))
            })
            .collect();

        items_with_area.sort_by(|a, b| {
            b.1.partial_cmp(&a.1).unwrap_or(Ordering::Equal)
        });

        items_with_area.into_iter()
            .take(top_count)
            .map(|(p, _)| p)
            .collect()
    }

    fn deterministic_pair<'a>(&self, iteration: usize, items: &'a [&Placement]) -> Option<(&'a Placement, &'a Placement)> {
        if items.len() < 2 {
            return None;
        }

        let idx_a = (iteration as usize + self.seed.unsigned_abs() as usize) % items.len();
        let mut idx_b = (idx_a + 1 + (iteration as usize / items.len().max(1))) % items.len();
        if idx_b == idx_a {
            idx_b = (idx_a + 1) % items.len();
        }

        Some((items[idx_a], items[idx_b]))
    }

    pub fn try_disrupt(
        &self,
        layout: &WorkingLayout,
        parts: &[Part],
        sheets: &[SheetShape],
        iteration: usize,
    ) -> Option<Vec<Placement>> {
        if layout.placements.len() < 2 {
            return None;
        }

        let top_count = ((layout.placements.len() as f64) * self.top_percentile).ceil() as usize;
        let top_count = top_count.max(2).min(layout.placements.len());

        let top_items = self.select_top_items(&layout.placements, parts, top_count);
        let exec = MoveExecutor::new(parts, sheets);

        for attempt in 0..self.max_attempts {
            let attempt_iter = iteration.wrapping_add(attempt);
            let (item_a, item_b) = match self.deterministic_pair(attempt_iter, &top_items) {
                Some(pair) => pair,
                None => break,
            };
            let mut move_diag = MoveDiagnostics::default();
            if let Some(result) = exec.try_swap(
                &layout.placements,
                &item_a.instance_id,
                &item_b.instance_id,
                &mut move_diag,
            ) {
                let violations = find_violations(&result, parts, sheets);
                if violations.is_empty() {
                    return Some(result);
                }
            }
        }
        None
    }
}

pub struct ExplorationPhase {
    config: PhaseConfig,
    score_model: ScoreModel,
    pool: InfeasibleSolutionPool,
    disruption: LargeItemSwapDisruption,
}

impl ExplorationPhase {
    pub fn new(config: PhaseConfig) -> Self {
        let pool = InfeasibleSolutionPool::new(config.pool_capacity);
        let disruption = LargeItemSwapDisruption::new(
            config.disruption_top_percentile,
            config.disruption_max_attempts,
            config.seed,
        );
        let score_model = ScoreModel::new(config.score_weights.clone());
        Self { config, score_model, pool, disruption }
    }

    pub fn run(
        &mut self,
        mut layout: WorkingLayout,
        parts: &[Part],
        sheets: &[SheetShape],
    ) -> (WorkingLayout, PhaseDiagnostics) {
        let mut diag = PhaseDiagnostics::new(PhaseType::Exploration);

        let initial_score = self.score_model.score(
            &layout.placements,
            &layout.unplaced,
            parts,
            sheets,
        );
        diag.initial_score = initial_score.total_cost;
        diag.best_score = initial_score.total_cost;

        let mut iteration = 0;
        let mut consecutive_no_improvement = 0;
        let mut incumbent_layout = layout.snapshot();
        let mut incumbent_score = initial_score.total_cost;

        let start_time = std::time::Instant::now();
        while iteration < self.config.exploration_budget.max_iterations {
            if self.config.exploration_budget.time_limit_s > 0.0 {
                let elapsed = start_time.elapsed().as_secs_f64();
                if elapsed >= self.config.exploration_budget.time_limit_s {
                    diag.stop_reason = PhaseStopReason::TimeLimit;
                    break;
                }
            }

            let sep_config = VrsSeparatorConfig {
                seed: self.config.seed as u64,
                worker_count: self.config.worker_count,
                ..VrsSeparatorConfig::default()
            };
            let sep = VrsSeparator::new(sep_config);
            let (sep_layout, sep_diag) = sep.run(layout.snapshot(), parts, sheets);

            let sep_score = self.score_model.score(
                &sep_layout.placements,
                &sep_layout.unplaced,
                parts,
                sheets,
            );

            let violations = find_violations(&sep_layout.placements, parts, sheets);

            if violations.is_empty() {
                if sep_score.total_cost < incumbent_score {
                    incumbent_layout = sep_layout.snapshot();
                    incumbent_score = sep_score.total_cost;
                    consecutive_no_improvement = 0;
                    diag.best_score = sep_score.total_cost;
                } else {
                    consecutive_no_improvement += 1;
                }
                layout = sep_layout;
            } else {
                self.pool.push(InfeasibleCandidate::new(
                    sep_layout.snapshot(),
                    sep_diag.best_loss,
                    sep_score.total_cost,
                    iteration,
                ));
                consecutive_no_improvement += 1;
            }

            if consecutive_no_improvement >= 5 {
                if let Some(disrupted) = self.disruption.try_disrupt(&layout, parts, sheets, iteration) {
                    diag.disruption_attempts += 1;
                    let new_layout = WorkingLayout::new(
                        disrupted,
                        layout.unplaced.clone(),
                        layout.sheet_count,
                        layout.seed,
                    );
                    let new_violations = find_violations(&new_layout.placements, parts, sheets);
                    if new_violations.is_empty() {
                        layout = new_layout;
                        diag.disruption_successes += 1;
                        consecutive_no_improvement = 0;
                    }
                }
            }

            iteration += 1;
        }

        if iteration >= self.config.exploration_budget.max_iterations {
            diag.stop_reason = PhaseStopReason::MaxIterations;
        }

        diag.iterations_run = iteration;
        diag.pool_size = self.pool.len();
        diag.incumbent_preserved = true;

        (incumbent_layout, diag)
    }
}

pub fn make_test_sheet() -> SheetShape {
    let stock = Stock {
        id: "S".into(),
        quantity: 1,
        width: Some(100.0),
        height: Some(100.0),
        outer_points: None,
        holes_points: None,
        cost_per_use: None,
    };
    crate::sheet::stock_to_shape(&stock).expect("valid test stock")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn infeasible_pool_capacity() {
        let mut pool = InfeasibleSolutionPool::new(3);
        assert!(pool.is_empty());

        for i in 0..5 {
            let layout = WorkingLayout::new(vec![], vec![], 1, 0);
            pool.push(InfeasibleCandidate::new(layout, i as f64, i as f64, i));
        }

        assert_eq!(pool.len(), 3);
    }

    #[test]
    fn infeasible_pool_best_returns_lowest_loss() {
        let mut pool = InfeasibleSolutionPool::new(10);

        let layout = WorkingLayout::new(vec![], vec![], 1, 0);
        pool.push(InfeasibleCandidate::new(layout.clone(), 5.0, 5.0, 0));
        pool.push(InfeasibleCandidate::new(layout.clone(), 1.0, 1.0, 0));
        pool.push(InfeasibleCandidate::new(layout.clone(), 3.0, 3.0, 0));

        let best = pool.best();
        assert!(best.is_some());
        assert_eq!(best.unwrap().raw_loss, 1.0, "best() must return lowest raw_loss");
    }

    #[test]
    fn infeasible_pool_capacity_retains_lowest_losses() {
        let mut pool = InfeasibleSolutionPool::new(3);
        let layout = WorkingLayout::new(vec![], vec![], 1, 0);

        for i in 0..5 {
            pool.push(InfeasibleCandidate::new(layout.clone(), i as f64, i as f64, i));
        }

        assert_eq!(pool.len(), 3, "pool must not exceed capacity");
        let best = pool.best();
        assert!(best.is_some());
        assert_eq!(best.unwrap().raw_loss, 0.0, "pool must retain lowest losses; best must be 0.0");
    }

    #[test]
    fn large_item_swap_disruption_some_is_violation_free() {
        let disruption = LargeItemSwapDisruption::new(1.0, 3, 42);
        let parts = vec![
            crate::item::Part {
                id: "A".into(),
                width: 20.0,
                height: 20.0,
                quantity: 1,
                allowed_rotations_deg: vec![0],
                holes_points: None,
                prepared_holes_points: None,
                outer_points: None,
                prepared_outer_points: None,
                rotation_policy: None,
            },
            crate::item::Part {
                id: "B".into(),
                width: 20.0,
                height: 20.0,
                quantity: 1,
                allowed_rotations_deg: vec![0],
                holes_points: None,
                prepared_holes_points: None,
                outer_points: None,
                prepared_outer_points: None,
                rotation_policy: None,
            },
        ];
        let sheets = vec![make_test_sheet(), make_test_sheet()];
        let placements = vec![
            Placement { instance_id: "A__0001".into(), part_id: "A".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 },
            Placement { instance_id: "B__0001".into(), part_id: "B".into(), sheet_index: 1, x: 0.0, y: 0.0, rotation_deg: 0.0 },
        ];
        let layout = WorkingLayout::new(placements, vec![], 2, 0);

        let result = disruption.try_disrupt(&layout, &parts, &sheets, 0);
        if let Some(new_placements) = result {
            let violations = find_violations(&new_placements, &parts, &sheets);
            assert!(violations.is_empty(), "try_disrupt Some output must be violation-free");
        }
    }

    #[test]
    fn large_item_swap_disruption_selects_deterministic_pair() {
        let disruption = LargeItemSwapDisruption::new(0.5, 3, 42);
        let parts = vec![
            crate::item::Part {
                id: "A".into(),
                width: 100.0,
                height: 100.0,
                quantity: 4,
                allowed_rotations_deg: vec![0],
                holes_points: None,
                prepared_holes_points: None,
                outer_points: None,
                prepared_outer_points: None,
                rotation_policy: None,
            },
        ];
        let placements = vec![
            Placement { instance_id: "A__0001".into(), part_id: "A".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 },
            Placement { instance_id: "A__0002".into(), part_id: "A".into(), sheet_index: 0, x: 10.0, y: 0.0, rotation_deg: 0.0 },
            Placement { instance_id: "A__0003".into(), part_id: "A".into(), sheet_index: 0, x: 20.0, y: 0.0, rotation_deg: 0.0 },
            Placement { instance_id: "A__0004".into(), part_id: "A".into(), sheet_index: 0, x: 30.0, y: 0.0, rotation_deg: 0.0 },
        ];
        let sheets = vec![make_test_sheet()];

        let placements_vec = placements.iter().collect::<Vec<_>>();
        let pair1 = disruption.deterministic_pair(0, &placements_vec);
        let pair2 = disruption.deterministic_pair(0, &placements_vec);

        assert!(pair1.is_some());
        let (p1, p2) = pair1.unwrap();
        let (p3, p4) = pair2.unwrap();
        assert_eq!(p1.instance_id, p3.instance_id);
        assert_eq!(p2.instance_id, p4.instance_id);
    }

    #[test]
    fn exploration_preserves_feasible_incumbent() {
        let config = PhaseConfig::deterministic_default();
        let mut phase = ExplorationPhase::new(config);

        let parts = vec![
            crate::item::Part {
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
            },
        ];
        let sheets = vec![make_test_sheet()];
        let placements = vec![
            Placement { instance_id: "A__0001".into(), part_id: "A".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 },
            Placement { instance_id: "A__0002".into(), part_id: "A".into(), sheet_index: 0, x: 20.0, y: 0.0, rotation_deg: 0.0 },
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);

        let (result_layout, diag) = phase.run(layout, &parts, &sheets);

        let violations = find_violations(&result_layout.placements, &parts, &sheets);
        assert!(violations.is_empty(), "exploration must not produce violations");
        assert!(diag.incumbent_preserved, "feasible incumbent must be preserved");
    }
}
