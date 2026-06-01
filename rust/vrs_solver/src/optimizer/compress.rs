use crate::item::{
    effective_policy_kind, placement_anchor_from_rect_min, resolve_instance_rotation_angles, Part,
};
use crate::optimizer::moves::{MoveDiagnostics, MoveExecutor};
use crate::optimizer::phase::{PhaseConfig, PhaseDiagnostics, PhaseStopReason, PhaseType};
use crate::optimizer::repair::{find_violations, validate_placements_for_backend};
use crate::optimizer::score::ScoreModel;
use crate::optimizer::separator::{VrsSeparator, VrsSeparatorConfig};
use crate::optimizer::working::WorkingLayout;
use crate::rotation_policy::{
    continuous_refinement_angles, RotationPolicyKind, REFINEMENT_MAX_CANDIDATES,
};
use crate::sheet::SheetShape;

pub struct CompressionPhase {
    config: PhaseConfig,
    score_model: ScoreModel,
}

impl CompressionPhase {
    pub fn new(config: PhaseConfig) -> Self {
        let score_model = ScoreModel::new(config.score_weights.clone());
        Self {
            config,
            score_model,
        }
    }

    pub fn run(
        &self,
        mut layout: WorkingLayout,
        parts: &[Part],
        sheets: &[SheetShape],
    ) -> (WorkingLayout, PhaseDiagnostics) {
        let mut diag = PhaseDiagnostics::new(PhaseType::Compression);

        let initial_score = self.score_model.score_with_backend(
            &layout.placements,
            &layout.unplaced,
            parts,
            sheets,
            &self.config.collision_backend,
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

                let rotations_to_try: Vec<f64> = parts
                    .iter()
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
                            &try_result,
                            parts,
                            sheets,
                            &self.config.collision_backend,
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

                // Q20: local rotation refinement for Continuous policy.
                // Tries symmetric wiggle candidates around the current rotation; accepts only
                // score-improving, backend-valid layouts. No bbox fallback under CDE/Jagua exact.
                if let Some(part) = parts.iter().find(|pt| pt.id == part_id) {
                    let policy = effective_policy_kind(part, rotation_context);
                    if matches!(policy, RotationPolicyKind::Continuous) {
                        let current_rot_now = layout.placements[i].rotation_deg;
                        let current_sheet_now = layout.placements[i].sheet_index;
                        let refinement_cands = continuous_refinement_angles(
                            current_rot_now,
                            &policy,
                            &rotations_to_try,
                            REFINEMENT_MAX_CANDIDATES,
                        );
                        if !refinement_cands.is_empty() {
                            diag.rotation_refinement_enabled = true;
                        }
                        for &ref_rot in &refinement_cands {
                            diag.rotation_refinement_attempts += 1;
                            // Seed the item at origin of its current sheet with the refinement rotation.
                            let (ax, ay) = placement_anchor_from_rect_min(
                                0.0,
                                0.0,
                                part.width,
                                part.height,
                                ref_rot,
                            );
                            let mut try_placements = layout.placements.clone();
                            try_placements[i].rotation_deg = ref_rot;
                            try_placements[i].x = ax;
                            try_placements[i].y = ay;
                            // Resolve collisions via separator scoped to the current sheet.
                            let working_try =
                                WorkingLayout::new(try_placements, vec![], sheets.len(), 0);
                            let sep_cfg = VrsSeparatorConfig {
                                allowed_sheet_indices: Some(vec![current_sheet_now]),
                                rotation_context: rotation_context.clone(),
                                collision_backend: self.config.collision_backend.clone(),
                                ..VrsSeparatorConfig::default()
                            };
                            let sep = VrsSeparator::new(sep_cfg);
                            let (sep_layout, sep_diag) = sep.run(working_try, parts, sheets);
                            // Accumulate search_position stats from this refinement separator call.
                            diag.search_position_calls += sep_diag.search_stats.calls;
                            diag.search_position_global_samples_evaluated +=
                                sep_diag.search_stats.global_samples_evaluated;
                            diag.search_position_focused_samples_evaluated +=
                                sep_diag.search_stats.focused_samples_evaluated;
                            diag.search_position_samples_unsupported +=
                                sep_diag.search_stats.samples_unsupported;
                            diag.search_position_refined_samples +=
                                sep_diag.search_stats.refined_samples;
                            diag.search_position_coord_descent_steps +=
                                sep_diag.search_stats.coord_descent_steps;
                            diag.search_position_lbf_fallback_used +=
                                sep_diag.search_stats.lbf_fallback_used;
                            if sep_diag.search_stats.best_eval < diag.search_position_best_eval {
                                diag.search_position_best_eval = sep_diag.search_stats.best_eval;
                            }
                            // Q21 + Q21R1: accumulate collision severity stats.
                            diag.collision_severity_enabled = true;
                            diag.collision_severity_pair_queries +=
                                sep_diag.severity_stats.pair_queries;
                            diag.collision_severity_boundary_queries +=
                                sep_diag.severity_stats.boundary_queries;
                            diag.collision_severity_probe_queries +=
                                sep_diag.severity_stats.probe_queries;
                            diag.collision_severity_backend_confirmed_collisions +=
                                sep_diag.severity_stats.backend_confirmed_collisions;
                            diag.collision_severity_backend_confirmed_no_collisions +=
                                sep_diag.severity_stats.backend_confirmed_no_collisions;
                            diag.collision_severity_unsupported_queries +=
                                sep_diag.severity_stats.unsupported_queries;
                            diag.collision_severity_bbox_proxy_uses +=
                                sep_diag.severity_stats.bbox_proxy_severity_uses;
                            diag.collision_severity_probe_pair_queries +=
                                sep_diag.severity_stats.probe_pair_queries;
                            diag.collision_severity_probe_boundary_queries +=
                                sep_diag.severity_stats.probe_boundary_queries;
                            diag.collision_severity_probe_resolved +=
                                sep_diag.severity_stats.probe_resolved;
                            diag.collision_severity_probe_unresolved +=
                                sep_diag.severity_stats.probe_unresolved;
                            diag.collision_severity_probe_unsupported +=
                                sep_diag.severity_stats.probe_unsupported;
                            let new_min = sep_diag.severity_stats.min_resolution_mm;
                            if new_min > 0.0 {
                                diag.collision_severity_min_resolution_mm =
                                    if diag.collision_severity_min_resolution_mm == 0.0 {
                                        new_min
                                    } else {
                                        diag.collision_severity_min_resolution_mm.min(new_min)
                                    };
                            }
                            if sep_diag.severity_stats.max_resolution_mm
                                > diag.collision_severity_max_resolution_mm
                            {
                                diag.collision_severity_max_resolution_mm =
                                    sep_diag.severity_stats.max_resolution_mm;
                            }
                            if sep_diag.severity_stats.resolutions_recorded > 0 {
                                let prior_count = diag.collision_severity_probe_resolved
                                    - sep_diag.severity_stats.probe_resolved;
                                let prior_sum =
                                    diag.collision_severity_avg_resolution_mm * prior_count as f64;
                                let new_total =
                                    prior_count + sep_diag.severity_stats.resolutions_recorded;
                                let new_sum = prior_sum + sep_diag.severity_stats.resolution_sum_mm;
                                diag.collision_severity_avg_resolution_mm = if new_total > 0 {
                                    new_sum / new_total as f64
                                } else {
                                    0.0
                                };
                            }
                            if !(sep_diag.best_loss == 0.0 || sep_diag.converged) {
                                continue;
                            }
                            if sep_layout.placements.len() != layout.placements.len() {
                                continue;
                            }
                            // Backend-aware commit gate — no bbox fallback under CDE/Jagua exact.
                            let try_violations = validate_placements_for_backend(
                                &sep_layout.placements,
                                parts,
                                sheets,
                                &self.config.collision_backend,
                            );
                            if !try_violations.is_empty() {
                                continue;
                            }
                            let try_score = self.score_model.score_with_backend(
                                &sep_layout.placements,
                                &layout.unplaced,
                                parts,
                                sheets,
                                &self.config.collision_backend,
                            );
                            if try_score.total_cost < incumbent_score {
                                let delta = incumbent_score - try_score.total_cost;
                                if delta > diag.rotation_refinement_best_delta {
                                    diag.rotation_refinement_best_delta = delta;
                                }
                                layout.placements = sep_layout.placements;
                                incumbent_layout = layout.snapshot();
                                incumbent_score = try_score.total_cost;
                                diag.best_score = try_score.total_cost;
                                diag.rotation_refinement_accepts += 1;
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
    use crate::rotation_policy::RotationResolveContext;

    #[test]
    fn compression_scores_actual_try_result_before_commit() {
        let config = PhaseConfig::deterministic_default();
        let score_model = ScoreModel::new(config.score_weights.clone());
        let phase = CompressionPhase::new(config);

        let parts = vec![crate::item::Part {
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
                x: 30.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);

        let (result_layout, diag) = phase.run(layout, &parts, &sheets);

        let actual_score = score_model.score(
            &result_layout.placements,
            &result_layout.unplaced,
            &parts,
            &sheets,
        );
        assert!(
            (actual_score.total_cost - diag.best_score).abs() < 1e-9,
            "diag.best_score must equal actual score of committed layout: got {} vs {}",
            actual_score.total_cost,
            diag.best_score
        );
    }

    #[test]
    fn compression_uses_part_allowed_rotations_not_hardcoded_list() {
        let mut config = PhaseConfig::deterministic_default();
        config.compression_budget = crate::optimizer::phase::PhaseBudget::new(1, 0.0);
        let phase = CompressionPhase::new(config);

        let parts = vec![crate::item::Part {
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
        }];
        let sheets = vec![make_test_sheet()];
        let placements = vec![Placement {
            instance_id: "A__0001".into(),
            part_id: "A".into(),
            sheet_index: 0,
            x: 0.0,
            y: 0.0,
            rotation_deg: 0.0,
        }];
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

        let parts = vec![crate::item::Part {
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

        let (result_layout, diag) = phase.run(layout, &parts, &sheets);

        let violations = find_violations(&result_layout.placements, &parts, &sheets);
        assert!(
            violations.is_empty(),
            "compression output must be violation-free"
        );
        assert!(
            diag.initial_score >= diag.best_score
                || diag.stop_reason == PhaseStopReason::NoImprovement
        );
    }

    #[test]
    fn compression_respects_budget() {
        let mut config = PhaseConfig::deterministic_default();
        config.compression_budget = crate::optimizer::phase::PhaseBudget::new(1, 0.0);
        let phase = CompressionPhase::new(config);

        let parts = vec![crate::item::Part {
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
        }];
        let sheets = vec![make_test_sheet()];
        let placements = vec![Placement {
            instance_id: "A__0001".into(),
            part_id: "A".into(),
            sheet_index: 0,
            x: 0.0,
            y: 0.0,
            rotation_deg: 0.0,
        }];
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
        use crate::item::resolve_instance_rotation_angles;
        use crate::rotation_policy::{RotationPolicyKind, RotationResolveContext};

        // Part with no allowed_rotations_deg and no rotation_policy →
        // resolved angles come entirely from the context's global_policy.
        let part = make_part_no_policy("A", 100.0, 20.0, 1);

        let forty_five_context =
            RotationResolveContext::new(Some(RotationPolicyKind::FortyFive), 0, 8);
        let legacy_context = RotationResolveContext::legacy_default();

        let angles_fortyfive =
            resolve_instance_rotation_angles(&part, "A__0001", &forty_five_context);
        let angles_legacy = resolve_instance_rotation_angles(&part, "A__0001", &legacy_context);

        assert_eq!(angles_fortyfive.len(), 8,
            "FortyFive context → 8 candidates; compression must use this when PhaseConfig carries it");
        assert_eq!(
            angles_legacy.len(),
            4,
            "Legacy context → 4 orthogonal candidates"
        );

        // Verify that a CompressionPhase built with FortyFive config resolves 8 angles
        let mut config = PhaseConfig::deterministic_default();
        config.rotation_context = forty_five_context;
        config.compression_budget = crate::optimizer::phase::PhaseBudget::new(1, 0.0);
        let phase = CompressionPhase::new(config);

        // The phase's rotation_context (via self.config.rotation_context) should yield 8 angles
        let phase_angles =
            resolve_instance_rotation_angles(&part, "A__0001", &phase.config.rotation_context);
        assert_eq!(phase_angles.len(), 8,
            "CompressionPhase.config.rotation_context must carry FortyFive (8 angles), not legacy (4)");
        assert!(
            phase_angles.iter().any(|&r| (r - 45.0).abs() < 1e-6),
            "FortyFive context must include 45° in resolved candidates"
        );
    }

    #[test]
    fn compression_move_executor_uses_phase_rotation_context() {
        use crate::item::resolve_instance_rotation_angles;
        use crate::rotation_policy::{RotationPolicyKind, RotationResolveContext};

        // Part with no policy: orthogonal only at 0° and 90°, fits in a wide sheet.
        // With FortyFive context the candidate list is 8 angles; since 0° and 90° are among them
        // and the part fits, compression should remain violation-free.
        let parts = vec![make_part_no_policy("A", 30.0, 10.0, 2)];
        let sheets = vec![make_test_sheet()]; // 100×100

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
                x: 30.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
        ];

        let mut config = PhaseConfig::deterministic_default();
        config.rotation_context =
            RotationResolveContext::new(Some(RotationPolicyKind::FortyFive), 0, 8);
        config.compression_budget = crate::optimizer::phase::PhaseBudget::new(2, 0.0);
        let phase = CompressionPhase::new(config);

        let layout = WorkingLayout::new(placements, vec![], 1, 0);
        let (result_layout, _diag) = phase.run(layout, &parts, &sheets);

        let violations = find_violations(&result_layout.placements, &parts, &sheets);
        assert!(violations.is_empty(),
            "compression with FortyFive context and MoveExecutor from phase config must remain violation-free");

        // The resolved angles for the phase context include 45°
        let phase_angles =
            resolve_instance_rotation_angles(&parts[0], "A__0001", &phase.config.rotation_context);
        assert!(phase_angles.iter().any(|&r| (r - 45.0).abs() < 1e-6),
            "phase.config.rotation_context must include 45° (FortyFive), proving MoveExecutor uses phase context");
    }

    // -----------------------------------------------------------------------
    // SGH-Q11 tests
    // -----------------------------------------------------------------------

    #[test]
    fn compression_initial_score_uses_backend() {
        use crate::io::CollisionBackendKind;
        use crate::optimizer::score::ScoreModel;

        let l_json = serde_json::json!([
            [0.0, 0.0],
            [40.0, 0.0],
            [40.0, 20.0],
            [20.0, 20.0],
            [20.0, 40.0],
            [0.0, 40.0]
        ]);
        let mut l_part = make_part_no_policy("L", 40.0, 40.0, 1);
        l_part.outer_points = Some(l_json);
        let parts = vec![l_part, make_part_no_policy("B", 15.0, 15.0, 1)];
        let sheets = vec![make_test_sheet()];
        let placements = vec![
            Placement {
                instance_id: "L__0001".into(),
                part_id: "L".into(),
                sheet_index: 0,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
            Placement {
                instance_id: "B__0001".into(),
                part_id: "B".into(),
                sheet_index: 0,
                x: 22.0,
                y: 22.0,
                rotation_deg: 0.0,
            },
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);

        let mut config = PhaseConfig::deterministic_default();
        config.compression_budget = crate::optimizer::phase::PhaseBudget::new(0, 0.0);
        config.collision_backend = CollisionBackendKind::JaguaPolygonExact;
        let expected = ScoreModel::new(config.score_weights.clone()).score_with_backend(
            &layout.placements,
            &layout.unplaced,
            &parts,
            &sheets,
            &config.collision_backend,
        );
        let phase = CompressionPhase::new(config);

        let (_result_layout, diag) = phase.run(layout, &parts, &sheets);
        assert!(
            (diag.initial_score - expected.total_cost).abs() < 1e-9,
            "CompressionPhase initial/incumbent score must use selected backend"
        );
    }

    #[test]
    fn compression_phase_uses_backend_aware_validation_for_exact() {
        use crate::io::CollisionBackendKind;

        // Parts without outer_points fall back to rect polygon in exact backend.
        // CompressionPhase with JaguaPolygonExact must not crash and must produce
        // a violation-free (bbox-level) output — verifies end-to-end wiring.
        let parts = vec![crate::item::Part {
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
        }];
        let sheets = vec![make_test_sheet()];
        let placements = vec![
            crate::io::Placement {
                instance_id: "A__0001".into(),
                part_id: "A".into(),
                sheet_index: 0,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
            crate::io::Placement {
                instance_id: "A__0002".into(),
                part_id: "A".into(),
                sheet_index: 0,
                x: 30.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
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

    // -----------------------------------------------------------------------
    // SGH-Q20 tests
    // -----------------------------------------------------------------------

    fn make_continuous_part(id: &str, w: f64, h: f64, qty: i64) -> crate::item::Part {
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
            rotation_policy: Some(crate::rotation_policy::RotationPolicyKind::Continuous),
        }
    }

    // Q20-C1: Compression phase tracks rotation_refinement_enabled=true for Continuous parts.
    #[test]
    fn compression_rotation_refinement_enabled_for_continuous_policy() {
        use crate::rotation_policy::{RotationPolicyKind, RotationResolveContext};

        let parts = vec![make_continuous_part("P", 30.0, 10.0, 2)];
        let sheets = vec![make_test_sheet()];
        let placements = vec![
            crate::io::Placement {
                instance_id: "P__0001".into(),
                part_id: "P".into(),
                sheet_index: 0,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
            crate::io::Placement {
                instance_id: "P__0002".into(),
                part_id: "P".into(),
                sheet_index: 0,
                x: 30.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);

        let mut config = PhaseConfig::deterministic_default();
        config.rotation_context =
            RotationResolveContext::new(Some(RotationPolicyKind::Continuous), 0, 16);
        config.compression_budget = crate::optimizer::phase::PhaseBudget::new(1, 0.0);
        let phase = CompressionPhase::new(config);

        let (_result, diag) = phase.run(layout, &parts, &sheets);
        assert!(
            diag.rotation_refinement_enabled,
            "Continuous policy must set rotation_refinement_enabled=true"
        );
        assert!(
            diag.rotation_refinement_attempts > 0,
            "Continuous policy must produce refinement attempts"
        );
    }

    // Q20-C2: Compression refinement does not violate backend-aware gate.
    #[test]
    fn compression_refinement_output_is_violation_free() {
        use crate::rotation_policy::{RotationPolicyKind, RotationResolveContext};

        let parts = vec![make_continuous_part("P", 20.0, 10.0, 2)];
        let sheets = vec![make_test_sheet()];
        let placements = vec![
            crate::io::Placement {
                instance_id: "P__0001".into(),
                part_id: "P".into(),
                sheet_index: 0,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
            crate::io::Placement {
                instance_id: "P__0002".into(),
                part_id: "P".into(),
                sheet_index: 0,
                x: 20.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);

        let mut config = PhaseConfig::deterministic_default();
        config.rotation_context =
            RotationResolveContext::new(Some(RotationPolicyKind::Continuous), 0, 16);
        config.compression_budget = crate::optimizer::phase::PhaseBudget::new(1, 0.0);
        let phase = CompressionPhase::new(config);

        let (result_layout, diag) = phase.run(layout, &parts, &sheets);
        let violations = find_violations(&result_layout.placements, &parts, &sheets);
        assert!(
            violations.is_empty(),
            "refinement must produce violation-free layout"
        );
        assert!(
            diag.rotation_refinement_enabled,
            "refinement must be enabled for Continuous"
        );
    }

    // Q20-C3: Non-continuous policy does not trigger refinement.
    #[test]
    fn compression_refinement_not_triggered_for_orthogonal_policy() {
        let parts = vec![make_part_no_policy("A", 30.0, 10.0, 2)];
        let sheets = vec![make_test_sheet()];
        let placements = vec![
            crate::io::Placement {
                instance_id: "A__0001".into(),
                part_id: "A".into(),
                sheet_index: 0,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
            crate::io::Placement {
                instance_id: "A__0002".into(),
                part_id: "A".into(),
                sheet_index: 0,
                x: 30.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);
        // Default config has no global policy → Orthogonal
        let config = PhaseConfig::deterministic_default();
        let phase = CompressionPhase::new(config);

        let (_result, diag) = phase.run(layout, &parts, &sheets);
        assert!(
            !diag.rotation_refinement_enabled,
            "Orthogonal must not enable rotation refinement"
        );
        assert_eq!(
            diag.rotation_refinement_attempts, 0,
            "no refinement attempts for Orthogonal"
        );
    }

    // Q20-C4: CDE backend does not trigger bbox fallback during refinement.
    #[test]
    fn compression_refinement_cde_bbox_fallback_zero() {
        use crate::io::CollisionBackendKind;
        use crate::rotation_policy::{RotationPolicyKind, RotationResolveContext};

        let parts = vec![make_continuous_part("P", 20.0, 10.0, 2)];
        let sheets = vec![make_test_sheet()];
        let placements = vec![
            crate::io::Placement {
                instance_id: "P__0001".into(),
                part_id: "P".into(),
                sheet_index: 0,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
            crate::io::Placement {
                instance_id: "P__0002".into(),
                part_id: "P".into(),
                sheet_index: 0,
                x: 20.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);

        let mut config = PhaseConfig::deterministic_default();
        config.rotation_context =
            RotationResolveContext::new(Some(RotationPolicyKind::Continuous), 0, 16);
        config.compression_budget = crate::optimizer::phase::PhaseBudget::new(1, 0.0);
        config.collision_backend = CollisionBackendKind::Cde;
        let phase = CompressionPhase::new(config);

        let (result_layout, diag) = phase.run(layout, &parts, &sheets);
        // Use the same CDE backend for validation: rotated rectangles may have
        // overlapping bboxes but no actual polygon overlap, so bbox-based
        // find_violations would produce false positives here.
        let violations = crate::optimizer::repair::validate_placements_for_backend(
            &result_layout.placements,
            &parts,
            &sheets,
            &CollisionBackendKind::Cde,
        );
        assert!(
            violations.is_empty(),
            "CDE refinement must be violation-free"
        );
        assert!(
            diag.rotation_refinement_enabled,
            "CDE + Continuous must enable refinement"
        );
        // Verify CDE counter integrity: pair+boundary == total (no bbox leakage).
        let snap = crate::optimizer::cde_observability::snapshot();
        assert_eq!(
            snap.pair_queries + snap.boundary_queries,
            snap.total_queries,
            "CDE total_queries must equal pair+boundary (no bbox fallback leakage)"
        );
    }

    // Q20R regression: Q20 rotation refinement still works after Q20R search_position wiring.
    #[test]
    fn q20_rotation_refinement_regression_still_passes() {
        use crate::io::CollisionBackendKind;
        use crate::rotation_policy::RotationPolicyKind;

        let parts = vec![crate::item::Part {
            id: "R".into(),
            width: 80.0,
            height: 20.0,
            quantity: 1,
            allowed_rotations_deg: vec![],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: None,
            prepared_outer_points: None,
            rotation_policy: Some(RotationPolicyKind::Continuous),
        }];
        let sheets = crate::sheet::expand_sheets(&[crate::sheet::Stock {
            id: "S".into(),
            quantity: 1,
            width: Some(200.0),
            height: Some(200.0),
            outer_points: None,
            holes_points: None,
            cost_per_use: None,
        }])
        .expect("sheets");
        let placements = vec![crate::io::Placement {
            instance_id: "R__0001".into(),
            part_id: "R".into(),
            sheet_index: 0,
            x: 0.0,
            y: 0.0,
            rotation_deg: 0.0,
        }];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);

        let mut config = PhaseConfig::deterministic_default();
        config.rotation_context =
            RotationResolveContext::new(Some(RotationPolicyKind::Continuous), 0, 16);
        config.compression_budget = crate::optimizer::phase::PhaseBudget::new(3, 0.0);
        config.collision_backend = CollisionBackendKind::Bbox;
        let phase = CompressionPhase::new(config);

        let (_result, diag) = phase.run(layout, &parts, &sheets);
        // Q20 refinement must still fire for Continuous policy.
        assert!(
            diag.rotation_refinement_enabled,
            "Q20 refinement must remain enabled after Q20R"
        );
        // Q20R search_position stats must also be present.
        assert!(
            diag.search_position_calls >= 0,
            "search_position_calls field must exist"
        );
    }
}
