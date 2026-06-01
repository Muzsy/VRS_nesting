use std::collections::HashSet;

use super::multisheet::compute_sheet_count_used;
use super::phase::PhaseConfig;
use super::repair::validate_placements_for_backend;
use super::score::ScoreModel;
use super::sheet_elimination::{SheetEliminationDiagnostics, SheetEliminationEngine};
use super::stopping::StoppingPolicy;
use super::working::WorkingLayout;
use crate::item::Part;
use crate::sheet::SheetShape;

// ---------------------------------------------------------------------------
// BppPhaseDiagnostics
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Default)]
pub struct BppPhaseDiagnostics {
    pub initial_sheet_count: usize,
    pub final_sheet_count: usize,
    pub attempts: usize,
    pub successful_eliminations: usize,
    pub failed_eliminations: usize,
    pub rollback_count: usize,
    pub stop_reason: String,
    /// Score of the input layout before the BPP phase runs.
    pub initial_score: f64,
    /// Score of the last successfully committed incumbent; equals initial_score if no eliminations.
    pub best_score: f64,
    /// Per-attempt diagnostics from each SheetEliminationEngine::run() call.
    pub per_attempt: Vec<SheetEliminationDiagnostics>,
}

impl BppPhaseDiagnostics {
    pub fn summary(&self) -> String {
        format!(
            "initial_sheets={} final_sheets={} attempts={} ok={} fail={} rollbacks={} reason={} \
             initial_score={:.3} best_score={:.3} per_attempt_count={}",
            self.initial_sheet_count,
            self.final_sheet_count,
            self.attempts,
            self.successful_eliminations,
            self.failed_eliminations,
            self.rollback_count,
            self.stop_reason,
            self.initial_score,
            self.best_score,
            self.per_attempt.len(),
        )
    }
}

// ---------------------------------------------------------------------------
// BppPhase
// ---------------------------------------------------------------------------

pub struct BppPhase {
    config: PhaseConfig,
    score_model: ScoreModel,
}

impl BppPhase {
    pub fn new(config: PhaseConfig) -> Self {
        let score_model = ScoreModel::new(config.score_weights.clone());
        Self {
            config,
            score_model,
        }
    }

    /// Run the iterative BPP phase: repeatedly attempt sheet elimination until
    /// no further reduction is possible or the budget is exhausted.
    ///
    /// Invariants maintained:
    /// - sheet_count_used never increases
    /// - every committed output passes find_violations
    /// - placement count and instance set preserved across each pass
    /// - failed attempt rolls back to exact incumbent (implicit: clone-based)
    pub fn run(
        &self,
        layout: WorkingLayout,
        parts: &[Part],
        sheets: &[SheetShape],
    ) -> (WorkingLayout, BppPhaseDiagnostics) {
        let mut diag = BppPhaseDiagnostics::default();
        let start_time = std::time::Instant::now();

        let initial_sheet_count = compute_sheet_count_used(&layout.placements);
        diag.initial_sheet_count = initial_sheet_count;
        diag.final_sheet_count = initial_sheet_count;

        let layout_seed = layout.seed;
        let layout_sheet_count = layout.sheet_count;

        let mut incumbent_placements = layout.placements;
        let mut incumbent_unplaced = layout.unplaced;
        let mut incumbent_sheet_count = initial_sheet_count;

        let initial_score = self.score_model.score_with_backend(
            &incumbent_placements,
            &incumbent_unplaced,
            parts,
            sheets,
            &self.config.collision_backend,
        );
        diag.initial_score = initial_score.total_cost;
        diag.best_score = initial_score.total_cost;

        loop {
            if diag.successful_eliminations >= self.config.bpp_max_eliminations {
                diag.stop_reason = "max_eliminations_reached".to_string();
                break;
            }

            if self.config.bpp_budget.time_limit_s > 0.0
                && start_time.elapsed().as_secs_f64() >= self.config.bpp_budget.time_limit_s
            {
                diag.stop_reason = "time_limit".to_string();
                break;
            }

            if incumbent_sheet_count <= 1 {
                diag.stop_reason = "single_sheet_reached".to_string();
                break;
            }

            // Pass budget to the inner StoppingPolicy.
            // Time is controlled by the outer loop; inner policy uses iteration count only.
            let engine = SheetEliminationEngine::new_with_backend_and_rotation_context(
                parts,
                sheets,
                self.config.rotation_context.clone(),
                self.config.collision_backend.clone(),
            );
            let mut policy = StoppingPolicy::new(self.config.bpp_budget.max_iterations, f64::MAX);

            let (new_placements, new_unplaced, elim_diag) = engine.run(
                incumbent_placements.clone(),
                incumbent_unplaced.clone(),
                &mut policy,
            );

            diag.attempts += 1;

            // Commit gate
            let new_sheet_count = compute_sheet_count_used(&new_placements);
            let violations = validate_placements_for_backend(
                &new_placements,
                parts,
                sheets,
                &self.config.collision_backend,
            );
            let count_preserved = new_placements.len() == incumbent_placements.len();
            let ids_match = {
                let orig: HashSet<&str> = incumbent_placements
                    .iter()
                    .map(|p| p.instance_id.as_str())
                    .collect();
                let updated: HashSet<&str> = new_placements
                    .iter()
                    .map(|p| p.instance_id.as_str())
                    .collect();
                orig == updated
            };

            let commit_ok = elim_diag.successful_eliminations > 0
                && new_sheet_count < incumbent_sheet_count
                && violations.is_empty()
                && count_preserved
                && ids_match;

            diag.per_attempt.push(elim_diag);

            if commit_ok {
                incumbent_placements = new_placements;
                incumbent_unplaced = new_unplaced;
                incumbent_sheet_count = new_sheet_count;
                diag.successful_eliminations += 1;
                diag.final_sheet_count = new_sheet_count;
                let committed_score = self.score_model.score_with_backend(
                    &incumbent_placements,
                    &incumbent_unplaced,
                    parts,
                    sheets,
                    &self.config.collision_backend,
                );
                diag.best_score = committed_score.total_cost;
            } else {
                // Rollback: incumbent unchanged (clone-based rollback safety).
                diag.failed_eliminations += 1;
                diag.rollback_count += 1;
                if diag.stop_reason.is_empty() {
                    diag.stop_reason = "elimination_failed".to_string();
                }
                break;
            }
        }

        if diag.stop_reason.is_empty() {
            diag.stop_reason = "completed".to_string();
        }

        let result_layout = WorkingLayout::new(
            incumbent_placements,
            incumbent_unplaced,
            layout_sheet_count,
            layout_seed,
        );

        (result_layout, diag)
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::io::Placement;
    use crate::item::{expand_instances, Part};
    use crate::optimizer::initializer::build_initial_layout;
    use crate::optimizer::phase::{PhaseBudget, PhaseConfig};
    use crate::optimizer::repair::{find_violations, run_repair};
    use crate::optimizer::score::{ScoreModel, ScoreWeights};
    use crate::optimizer::stopping::StoppingPolicy;
    use crate::sheet::{expand_sheets, Stock};

    fn make_part(id: &str, w: f64, h: f64, qty: i64) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: qty,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: None,
            prepared_outer_points: None,
            rotation_policy: None,
        }
    }

    fn make_stock(id: &str, w: f64, h: f64, qty: i64) -> Stock {
        Stock {
            id: id.to_string(),
            quantity: qty,
            width: Some(w),
            height: Some(h),
            outer_points: None,
            holes_points: None,
            cost_per_use: None,
        }
    }

    fn bpp_test_config(max_eliminations: usize, max_iter_per_pass: usize) -> PhaseConfig {
        let mut cfg = PhaseConfig::deterministic_default();
        cfg.bpp_budget = PhaseBudget::new(max_iter_per_pass, 0.0);
        cfg.bpp_max_eliminations = max_eliminations;
        cfg
    }

    fn build_repaired_layout(
        parts: &[Part],
        stocks: &[Stock],
    ) -> (WorkingLayout, Vec<crate::sheet::SheetShape>) {
        let instances = expand_instances(parts).expect("instances");
        let sheets = expand_sheets(stocks).expect("sheets");
        let (p, u, _) = build_initial_layout(&instances, parts, &sheets);
        let mut policy = StoppingPolicy::new(512, 30.0);
        let (p, u, _) = run_repair(p, u, parts, &sheets, &mut policy);
        let layout = WorkingLayout::new(p, u, sheets.len(), 0);
        (layout, sheets)
    }

    /// Manually build layout with one 40×40 item per sheet (3 sheets).
    /// All three fit on a single 100×100 sheet, so 2 eliminations should succeed.
    fn three_item_three_sheet_layout() -> (Vec<Placement>, Vec<crate::sheet::SheetShape>, Vec<Part>)
    {
        let parts = vec![make_part("A", 40.0, 40.0, 3)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 3)];
        let sheets = expand_sheets(&stocks).expect("sheets");
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
            Placement {
                instance_id: "A__0003".into(),
                part_id: "A".into(),
                sheet_index: 2,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
        ];
        (placements, sheets, parts)
    }

    #[test]
    fn bpp_phase_iteratively_reduces_multiple_sheets() {
        let (placements, sheets, parts) = three_item_three_sheet_layout();
        let layout = WorkingLayout::new(placements, vec![], sheets.len(), 0);
        assert_eq!(compute_sheet_count_used(&layout.placements), 3);

        let config = bpp_test_config(3, 512);
        let phase = BppPhase::new(config);
        let (result, diag) = phase.run(layout, &parts, &sheets);

        let final_count = compute_sheet_count_used(&result.placements);
        assert!(
            final_count == 1 || diag.successful_eliminations >= 2,
            "3 items on 3 sheets must reduce to 1 sheet or achieve >= 2 eliminations; \
             final_count={} eliminations={}; diag={}",
            final_count,
            diag.successful_eliminations,
            diag.summary()
        );
        assert!(find_violations(&result.placements, &parts, &sheets).is_empty());
    }

    #[test]
    fn bpp_phase_failed_attempt_rolls_back_exact_incumbent() {
        // Two 55×55 items on 60×60 sheets cannot consolidate — each needs its own sheet.
        let parts = vec![make_part("A", 55.0, 55.0, 2)];
        let stocks = vec![make_stock("S", 60.0, 60.0, 2)];
        let sheets = expand_sheets(&stocks).expect("sheets");
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
        let layout = WorkingLayout::new(placements.clone(), vec![], sheets.len(), 0);

        let config = bpp_test_config(4, 512);
        let phase = BppPhase::new(config);
        let (result, diag) = phase.run(layout, &parts, &sheets);

        assert_eq!(
            diag.successful_eliminations, 0,
            "no elimination should succeed"
        );
        assert_eq!(diag.rollback_count, 1, "one rollback must occur");
        assert_eq!(result.placements.len(), placements.len());
        for (a, b) in result.placements.iter().zip(placements.iter()) {
            assert_eq!(a.instance_id, b.instance_id, "rollback: instance_id");
            assert_eq!(a.sheet_index, b.sheet_index, "rollback: sheet_index");
            assert_eq!(a.x.to_bits(), b.x.to_bits(), "rollback: x");
            assert_eq!(a.y.to_bits(), b.y.to_bits(), "rollback: y");
        }
    }

    #[test]
    fn bpp_phase_never_increases_sheet_count() {
        let parts = vec![make_part("A", 40.0, 40.0, 4)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 4)];
        let (layout, sheets) = build_repaired_layout(&parts, &stocks);
        let initial_count = compute_sheet_count_used(&layout.placements);

        let config = bpp_test_config(4, 512);
        let phase = BppPhase::new(config);
        let (result, diag) = phase.run(layout, &parts, &sheets);

        let final_count = compute_sheet_count_used(&result.placements);
        assert!(
            final_count <= initial_count,
            "BPP must never increase sheet count: {} -> {}; diag={}",
            initial_count,
            final_count,
            diag.summary()
        );
    }

    #[test]
    fn bpp_phase_output_is_violation_free() {
        let parts = vec![make_part("A", 30.0, 30.0, 4)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 4)];
        let (layout, sheets) = build_repaired_layout(&parts, &stocks);

        let config = bpp_test_config(4, 512);
        let phase = BppPhase::new(config);
        let (result, diag) = phase.run(layout, &parts, &sheets);

        let violations = find_violations(&result.placements, &parts, &sheets);
        assert!(
            violations.is_empty(),
            "BPP output must be violation-free; diag={}",
            diag.summary()
        );
    }

    #[test]
    fn bpp_budget_limits_attempts() {
        // max_eliminations=1 → loop stops after first successful elimination.
        let parts = vec![make_part("A", 20.0, 20.0, 4)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 4)];
        let sheets = expand_sheets(&stocks).expect("sheets");
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
            Placement {
                instance_id: "A__0003".into(),
                part_id: "A".into(),
                sheet_index: 2,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
            Placement {
                instance_id: "A__0004".into(),
                part_id: "A".into(),
                sheet_index: 3,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
        ];
        let layout = WorkingLayout::new(placements, vec![], sheets.len(), 0);

        let config = bpp_test_config(1, 512);
        let phase = BppPhase::new(config);
        let (_, diag) = phase.run(layout, &parts, &sheets);

        assert!(
            diag.successful_eliminations <= 1,
            "max_eliminations=1 must limit successful eliminations; got {}",
            diag.successful_eliminations
        );
        assert_eq!(
            diag.stop_reason, "max_eliminations_reached",
            "stop reason must be max_eliminations_reached when limit hit"
        );
    }

    #[test]
    fn same_seed_bpp_phase_determinism() {
        let (placements, sheets, parts) = three_item_three_sheet_layout();
        let config = bpp_test_config(3, 512);

        let make_layout = || WorkingLayout::new(placements.clone(), vec![], sheets.len(), 0);

        let (r1, _) = BppPhase::new(config.clone()).run(make_layout(), &parts, &sheets);
        let (r2, _) = BppPhase::new(config).run(make_layout(), &parts, &sheets);

        assert_eq!(
            r1.placements.len(),
            r2.placements.len(),
            "determinism: placement count"
        );
        for (a, b) in r1.placements.iter().zip(r2.placements.iter()) {
            assert_eq!(a.instance_id, b.instance_id, "determinism: instance_id");
            assert_eq!(a.sheet_index, b.sheet_index, "determinism: sheet_index");
            assert_eq!(a.x.to_bits(), b.x.to_bits(), "determinism: x");
            assert_eq!(a.y.to_bits(), b.y.to_bits(), "determinism: y");
        }
        assert!(find_violations(&r1.placements, &parts, &sheets).is_empty());
    }

    #[test]
    fn bpp_phase_diagnostics_records_per_attempt() {
        let (placements, sheets, parts) = three_item_three_sheet_layout();
        let layout = WorkingLayout::new(placements, vec![], sheets.len(), 0);

        let config = bpp_test_config(3, 512);
        let (_, diag) = BppPhase::new(config).run(layout, &parts, &sheets);

        assert_eq!(
            diag.attempts,
            diag.per_attempt.len(),
            "attempts must equal per_attempt.len(): {} vs {}",
            diag.attempts,
            diag.per_attempt.len()
        );
        assert!(
            diag.attempts > 0,
            "at least one attempt must have run on a 3-sheet fixture"
        );
        for (i, attempt_diag) in diag.per_attempt.iter().enumerate() {
            assert!(
                !attempt_diag.stop_reason.is_empty(),
                "per_attempt[{i}].stop_reason must not be empty"
            );
        }
        assert!(
            diag.per_attempt.iter().any(|a| a.selected_sheet.is_some()),
            "at least one attempt must have selected_sheet = Some (fixture has placements)"
        );
    }

    #[test]
    fn bpp_phase_diagnostics_score_fields_are_real() {
        let (placements, sheets, parts) = three_item_three_sheet_layout();
        let score_model = ScoreModel::new(ScoreWeights::default());

        let input_layout = WorkingLayout::new(placements.clone(), vec![], sheets.len(), 0);
        let input_score = score_model.score(
            &input_layout.placements,
            &input_layout.unplaced,
            &parts,
            &sheets,
        );

        let config = bpp_test_config(3, 512);
        let (result, diag) = BppPhase::new(config).run(input_layout, &parts, &sheets);

        assert!(
            (diag.initial_score - input_score.total_cost).abs() < 1e-9,
            "initial_score must equal score(input layout): {} vs {}",
            diag.initial_score,
            input_score.total_cost
        );

        if diag.successful_eliminations > 0 {
            assert!(
                diag.best_score < diag.initial_score,
                "best_score must improve over initial_score after successful eliminations: \
                 best={} initial={}",
                diag.best_score,
                diag.initial_score
            );
            let final_score =
                score_model.score(&result.placements, &result.unplaced, &parts, &sheets);
            assert!(
                (diag.best_score - final_score.total_cost).abs() < 1e-9,
                "best_score must equal score(final committed layout): {} vs {}",
                diag.best_score,
                final_score.total_cost
            );
        } else {
            assert!(
                (diag.best_score - diag.initial_score).abs() < 1e-9,
                "best_score must equal initial_score when no eliminations succeed"
            );
        }
    }

    // -----------------------------------------------------------------------
    // SGH-Q11 tests
    // -----------------------------------------------------------------------

    #[test]
    fn bpp_phase_uses_backend_aware_commit_gate_for_exact() {
        use crate::io::CollisionBackendKind;

        // BppPhase with JaguaPolygonExact must not crash and must produce violation-free output.
        // Parts without outer_points fall back to rect polygon in exact backend.
        let (placements, sheets, parts) = three_item_three_sheet_layout();
        let layout = WorkingLayout::new(placements, vec![], sheets.len(), 0);

        let mut config = bpp_test_config(2, 64);
        config.collision_backend = CollisionBackendKind::JaguaPolygonExact;
        let phase = BppPhase::new(config);

        let (result, _diag) = phase.run(layout, &parts, &sheets);
        let violations = find_violations(&result.placements, &parts, &sheets);
        assert!(
            violations.is_empty(),
            "BppPhase with JaguaPolygonExact backend must produce violation-free output"
        );
    }
}
