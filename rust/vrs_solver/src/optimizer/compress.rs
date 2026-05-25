use crate::item::{resolve_instance_rotation_angles, Part};
use crate::rotation_policy::RotationResolveContext;
use crate::sheet::SheetShape;
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
        let rotation_context = RotationResolveContext::legacy_default();

        let start_time = std::time::Instant::now();
        let mut iteration = 0;
        while iteration < self.config.compression_budget.max_iterations {
            if self.config.compression_budget.time_limit_s > 0.0 {
                let elapsed = start_time.elapsed().as_secs_f64();
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
                let part_id = layout.placements[i].part_id.clone();

                let rotations_to_try: Vec<f64> = parts.iter()
                    .find(|pt| pt.id == part_id)
                    .map(|pt| resolve_instance_rotation_angles(pt, &instance_id, &rotation_context))
                    .unwrap_or_default();

                for &rot in rotations_to_try.iter() {
                    if (rot - current_rot).abs() < 1e-9 {
                        continue;
                    }

                    let mut diag_inner = MoveDiagnostics::default();
                    if let Some(try_result) = exec.try_reinsert(
                        &layout.placements,
                        &instance_id,
                        current_sheet,
                        rot,
                        &mut diag_inner,
                    ) {
                        let try_violations = find_violations(&try_result, parts, sheets);
                        if try_violations.is_empty() {
                            let try_score = self.score_model.score(
                                &try_result,
                                &layout.unplaced,
                                parts,
                                sheets,
                            );
                            if try_score.total_cost < incumbent_score {
                                layout.placements = try_result;
                                incumbent_layout = layout.snapshot();
                                incumbent_score = try_score.total_cost;
                                diag.best_score = try_score.total_cost;
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
    use crate::io::Placement;
    use crate::optimizer::explore::make_test_sheet;
    use crate::optimizer::score::ScoreModel;

    #[test]
    fn compression_scores_actual_try_result_before_commit() {
        let config = PhaseConfig::deterministic_default();
        let score_model = ScoreModel::new(config.score_weights.clone());
        let phase = CompressionPhase::new(config);

        let parts = vec![
            crate::item::Part {
                id: "A".into(),
                width: 30.0,
                height: 10.0,
                quantity: 2,
                allowed_rotations_deg: vec![0, 90],
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
            Placement { instance_id: "A__0002".into(), part_id: "A".into(), sheet_index: 0, x: 30.0, y: 0.0, rotation_deg: 0.0 },
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);

        let (result_layout, diag) = phase.run(layout, &parts, &sheets);

        let actual_score = score_model.score(&result_layout.placements, &result_layout.unplaced, &parts, &sheets);
        assert!((actual_score.total_cost - diag.best_score).abs() < 1e-9,
            "diag.best_score must equal actual score of committed layout: got {} vs {}",
            actual_score.total_cost, diag.best_score);
    }

    #[test]
    fn compression_uses_part_allowed_rotations_not_hardcoded_list() {
        let mut config = PhaseConfig::deterministic_default();
        config.compression_budget = crate::optimizer::phase::PhaseBudget::new(1, 0.0);
        let phase = CompressionPhase::new(config);

        let parts = vec![
            crate::item::Part {
                id: "A".into(),
                width: 30.0,
                height: 10.0,
                quantity: 1,
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
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);

        let (result_layout, _diag) = phase.run(layout, &parts, &sheets);

        assert!((result_layout.placements[0].rotation_deg - 0.0).abs() < 1e-9,
            "part with allowed_rotations_deg=[0] must stay at rotation 0; no unsupported rotation applied");
        let violations = find_violations(&result_layout.placements, &parts, &sheets);
        assert!(violations.is_empty());
    }

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
                rotation_policy: None,
            },
        ];
        let sheets = vec![make_test_sheet()];
        let placements = vec![
            Placement { instance_id: "A__0001".into(), part_id: "A".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 },
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);

        let (_, diag) = phase.run(layout, &parts, &sheets);
        assert!(diag.iterations_run <= 1);
    }
}
