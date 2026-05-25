use crate::io::Placement;
use crate::item::Part;
use crate::sheet::SheetShape;
use crate::optimizer::explore::make_test_sheet;
use crate::optimizer::moves::{MoveExecutor, MoveDiagnostics};
use crate::optimizer::phase::{PhaseConfig, PhaseDiagnostics, PhaseStopReason, PhaseType};
use crate::optimizer::repair::find_violations;
use crate::optimizer::score::ScoreModel;
use crate::optimizer::working::WorkingLayout;

pub struct CompressionPhase {
    config: PhaseConfig,
    score_model: ScoreModel,
}

impl CompressionPhase {
    pub fn new(config: PhaseConfig) -> Self {
        let score_model = ScoreModel::new(config.score_weights.clone());
        Self { config, score_model }
    }

    pub fn run(
        &self,
        mut layout: WorkingLayout,
        parts: &[Part],
        sheets: &[SheetShape],
    ) -> (WorkingLayout, PhaseDiagnostics) {
        let mut diag = PhaseDiagnostics::new(PhaseType::Compression);

        let initial_score = self.score_model.score(
            &layout.placements,
            &layout.unplaced,
            parts,
            sheets,
        );
        diag.initial_score = initial_score.total_cost;
        diag.best_score = initial_score.total_cost;

        let mut incumbent_layout = layout.snapshot();
        let mut incumbent_score = initial_score.total_cost;
        let exec = MoveExecutor::new(parts, sheets);

        let mut iteration = 0;
        while iteration < self.config.compression_budget.max_iterations {
            if self.config.compression_budget.time_limit_s > 0.0 {
                let elapsed = (iteration as f64) * 0.01;
                if elapsed >= self.config.compression_budget.time_limit_s {
                    diag.stop_reason = PhaseStopReason::TimeLimit;
                    break;
                }
            }

            let mut improved = false;

            for i in 0..layout.placements.len() {
                let instance_id = layout.placements[i].instance_id.clone();
                let current_sheet = layout.placements[i].sheet_index;

                let current_rot = layout.placements[i].rotation_deg;
                let rotations_to_try = [0i64, 90, 180, 270];

                for rot in rotations_to_try.iter() {
                    if *rot == current_rot {
                        continue;
                    }

                    let mut new_placements = layout.placements.clone();
                    new_placements[i].rotation_deg = *rot;

                    let violations = find_violations(&new_placements, parts, sheets);
                    if !violations.is_empty() {
                        continue;
                    }

                    let new_score = self.score_model.score(
                        &new_placements,
                        &layout.unplaced,
                        parts,
                        sheets,
                    );

                    if new_score.total_cost < incumbent_score {
                        let mut diag_inner = MoveDiagnostics::default();
                        if let Some(try_result) = exec.try_reinsert(
                            &layout.placements,
                            &instance_id,
                            current_sheet,
                            *rot,
                            &mut diag_inner,
                        ) {
                            let try_violations = find_violations(&try_result, parts, sheets);
                            if try_violations.is_empty() {
                                layout.placements = try_result;
                                incumbent_layout = layout.snapshot();
                                incumbent_score = new_score.total_cost;
                                diag.best_score = new_score.total_cost;
                                improved = true;
                            }
                        }
                    }
                }
            }

            if !improved {
                diag.stop_reason = PhaseStopReason::NoImprovement;
                break;
            }

            iteration += 1;
        }

        if iteration >= self.config.compression_budget.max_iterations {
            diag.stop_reason = PhaseStopReason::MaxIterations;
        }

        diag.iterations_run = iteration;
        diag.incumbent_preserved = true;

        (incumbent_layout, diag)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn compression_no_downgrade() {
        let config = PhaseConfig::deterministic_default();
        let phase = CompressionPhase::new(config);

        let parts = vec![
            crate::item::Part {
                id: "A".into(),
                width: 20.0,
                height: 20.0,
                quantity: 2,
                allowed_rotations_deg: vec![0, 90],
                holes_points: None,
                prepared_holes_points: None,
                outer_points: None,
                prepared_outer_points: None,
            },
        ];
        let sheets = vec![make_test_sheet()];
        let placements = vec![
            Placement { instance_id: "A__0001".into(), part_id: "A".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0 },
            Placement { instance_id: "A__0002".into(), part_id: "A".into(), sheet_index: 0, x: 20.0, y: 0.0, rotation_deg: 0 },
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);

        let (result_layout, diag) = phase.run(layout, &parts, &sheets);

        let violations = find_violations(&result_layout.placements, &parts, &sheets);
        assert!(violations.is_empty(), "compression output must be violation-free");
        assert!(diag.initial_score >= diag.best_score || diag.stop_reason == PhaseStopReason::NoImprovement);
    }

    #[test]
    fn compression_respects_budget() {
        let mut config = PhaseConfig::deterministic_default();
        config.compression_budget = crate::optimizer::phase::PhaseBudget::new(1, 0.0);
        let phase = CompressionPhase::new(config);

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
            },
        ];
        let sheets = vec![make_test_sheet()];
        let placements = vec![
            Placement { instance_id: "A__0001".into(), part_id: "A".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0 },
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);

        let (_, diag) = phase.run(layout, &parts, &sheets);
        assert!(diag.iterations_run <= 1);
    }
}
