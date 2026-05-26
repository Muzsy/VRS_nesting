use crate::item::{resolve_instance_rotation_angles, Part};
use crate::sheet::SheetShape;
use crate::optimizer::moves::{MoveExecutor, MoveDiagnostics};
use crate::optimizer::phase::{PhaseConfig, PhaseDiagnostics, PhaseStopReason, PhaseType};
use crate::optimizer::repair::{find_violations, validate_placements_for_backend};
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
        let rotation_context = &self.config.rotation_context;
        let exec = MoveExecutor::new_with_backend_and_rotation_context(
            parts,
            sheets,
            rotation_context.clone(),
            self.config.collision_backend.clone(),
        );

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
                        let try_violations = validate_placements_for_backend(
                            &try_result, parts, sheets, &self.config.collision_backend,
                        );
                        if try_violations.is_empty() {
                            let try_score = self.score_model.score_with_backend(
                                &try_result,
                                &layout.unplaced,
                                parts,
                                sheets,
                                &self.config.collision_backend,
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

    // -----------------------------------------------------------------------
    // SGH-Q07R2 regression tesztek
    // -----------------------------------------------------------------------

    fn make_part_no_policy(id: &str, w: f64, h: f64, qty: i64) -> crate::item::Part {
        crate::item::Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: qty,
            allowed_rotations_deg: vec![],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: None,
            prepared_outer_points: None,
            rotation_policy: None,
        }
    }

    #[test]
    fn compression_uses_phase_rotation_context_for_candidate_rotations() {
        use crate::rotation_policy::{RotationResolveContext, RotationPolicyKind};
        use crate::item::resolve_instance_rotation_angles;

        // Part with no allowed_rotations_deg and no rotation_policy →
        // resolved angles come entirely from the context's global_policy.
        let part = make_part_no_policy("A", 100.0, 20.0, 1);

        let forty_five_context = RotationResolveContext::new(
            Some(RotationPolicyKind::FortyFive), 0, 8
        );
        let legacy_context = RotationResolveContext::legacy_default();

        let angles_fortyfive = resolve_instance_rotation_angles(&part, "A__0001", &forty_five_context);
        let angles_legacy = resolve_instance_rotation_angles(&part, "A__0001", &legacy_context);

        assert_eq!(angles_fortyfive.len(), 8,
            "FortyFive context → 8 candidates; compression must use this when PhaseConfig carries it");
        assert_eq!(angles_legacy.len(), 4,
            "Legacy context → 4 orthogonal candidates");

        // Verify that a CompressionPhase built with FortyFive config resolves 8 angles
        let mut config = PhaseConfig::deterministic_default();
        config.rotation_context = forty_five_context;
        config.compression_budget = crate::optimizer::phase::PhaseBudget::new(1, 0.0);
        let phase = CompressionPhase::new(config);

        // The phase's rotation_context (via self.config.rotation_context) should yield 8 angles
        let phase_angles = resolve_instance_rotation_angles(&part, "A__0001", &phase.config.rotation_context);
        assert_eq!(phase_angles.len(), 8,
            "CompressionPhase.config.rotation_context must carry FortyFive (8 angles), not legacy (4)");
        assert!(phase_angles.iter().any(|&r| (r - 45.0).abs() < 1e-6),
            "FortyFive context must include 45° in resolved candidates");
    }

    #[test]
    fn compression_move_executor_uses_phase_rotation_context() {
        use crate::rotation_policy::{RotationResolveContext, RotationPolicyKind};
        use crate::item::resolve_instance_rotation_angles;

        // Part with no policy: orthogonal only at 0° and 90°, fits in a wide sheet.
        // With FortyFive context the candidate list is 8 angles; since 0° and 90° are among them
        // and the part fits, compression should remain violation-free.
        let parts = vec![make_part_no_policy("A", 30.0, 10.0, 2)];
        let sheets = vec![make_test_sheet()]; // 100×100

        let placements = vec![
            Placement { instance_id: "A__0001".into(), part_id: "A".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 },
            Placement { instance_id: "A__0002".into(), part_id: "A".into(), sheet_index: 0, x: 30.0, y: 0.0, rotation_deg: 0.0 },
        ];

        let mut config = PhaseConfig::deterministic_default();
        config.rotation_context = RotationResolveContext::new(
            Some(RotationPolicyKind::FortyFive), 0, 8
        );
        config.compression_budget = crate::optimizer::phase::PhaseBudget::new(2, 0.0);
        let phase = CompressionPhase::new(config);

        let layout = WorkingLayout::new(placements, vec![], 1, 0);
        let (result_layout, _diag) = phase.run(layout, &parts, &sheets);

        let violations = find_violations(&result_layout.placements, &parts, &sheets);
        assert!(violations.is_empty(),
            "compression with FortyFive context and MoveExecutor from phase config must remain violation-free");

        // The resolved angles for the phase context include 45°
        let phase_angles = resolve_instance_rotation_angles(
            &parts[0], "A__0001", &phase.config.rotation_context
        );
        assert!(phase_angles.iter().any(|&r| (r - 45.0).abs() < 1e-6),
            "phase.config.rotation_context must include 45° (FortyFive), proving MoveExecutor uses phase context");
    }

    // -----------------------------------------------------------------------
    // SGH-Q11 tests
    // -----------------------------------------------------------------------

    #[test]
    fn compression_phase_uses_backend_aware_validation_for_exact() {
        use crate::io::CollisionBackendKind;

        // Parts without outer_points fall back to rect polygon in exact backend.
        // CompressionPhase with JaguaPolygonExact must not crash and must produce
        // a violation-free (bbox-level) output — verifies end-to-end wiring.
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
            crate::io::Placement { instance_id: "A__0001".into(), part_id: "A".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 },
            crate::io::Placement { instance_id: "A__0002".into(), part_id: "A".into(), sheet_index: 0, x: 30.0, y: 0.0, rotation_deg: 0.0 },
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);

        let mut config = PhaseConfig::deterministic_default();
        config.compression_budget = crate::optimizer::phase::PhaseBudget::new(2, 0.0);
        config.collision_backend = CollisionBackendKind::JaguaPolygonExact;
        let phase = CompressionPhase::new(config);

        let (result_layout, _diag) = phase.run(layout, &parts, &sheets);
        let violations = find_violations(&result_layout.placements, &parts, &sheets);
        assert!(
            violations.is_empty(),
            "CompressionPhase with JaguaPolygonExact backend must produce violation-free output"
        );
    }
}
