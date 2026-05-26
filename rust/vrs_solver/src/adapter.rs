use std::fmt;

use crate::io::{
    CollisionBackendDiagnosticsOutput, CollisionBackendKind, Metrics, OptimizerDiagnosticsOutput,
    OptimizerPipelineKind, Placement, ScoreBreakdownOutput, SolverInput, SolverOutput, Unplaced,
};
use crate::item::{can_fit_any_stock_with_policy, expand_instances_with_policy, part_has_holes};
use crate::optimizer::score::ScoreModel;
use crate::optimizer::{
    initializer::build_initial_layout_with_rotation_context,
    multisheet::MultiSheetManager,
    phase::{PhaseBudget, PhaseConfig, PhaseOptimizer},
    stopping::StoppingPolicy,
    try_place_on_sheet,
    working::{BackendCommitResult, WorkingCommitError, WorkingLayout},
    SheetCursor,
};
use crate::rotation_policy::{RotationResolveContext, DEFAULT_CONTINUOUS_SAMPLE_COUNT};
use crate::sheet::{expand_sheets, stock_has_holes};

const PROFILE_PHASE1: &str = "jagua_optimizer_phase1_outer_only";

fn _unsupported_output(reason: &str, input: &SolverInput) -> SolverOutput {
    SolverOutput {
        contract_version: "v1".to_string(),
        status: "unsupported".to_string(),
        unsupported_reason: Some(reason.to_string()),
        placements: vec![],
        unplaced: vec![],
        metrics: Metrics {
            placed_count: 0,
            unplaced_count: input.parts.iter().map(|p| p.quantity as usize).sum(),
            sheet_count_used: 0,
            seed: input.seed,
            time_limit_s: input.time_limit_s,
            project_name: input.project_name.clone(),
        },
        score_breakdown: None,
        optimizer_diagnostics: None,
        collision_backend_diagnostics: None,
    }
}

fn pipeline_kind(input: &SolverInput) -> OptimizerPipelineKind {
    input.optimizer_pipeline.clone().unwrap_or_default()
}

fn resolve_backend_kind(input: &SolverInput) -> CollisionBackendKind {
    input.collision_backend.clone().unwrap_or_default()
}

fn backend_err_reason(e: WorkingCommitError, violation_reason: &str) -> String {
    match e {
        WorkingCommitError::Violations(_) => violation_reason.to_string(),
        WorkingCommitError::UnsupportedBackend { reason, .. } => reason,
    }
}

fn diag_output_from(result: &BackendCommitResult) -> CollisionBackendDiagnosticsOutput {
    CollisionBackendDiagnosticsOutput {
        backend_used: result.backend_diagnostics.backend_name.clone(),
        unsupported_queries: result.backend_diagnostics.unsupported_queries,
        bbox_fallback_queries: result.backend_diagnostics.bbox_fallback_queries,
    }
}

fn phase_config_from_input(
    input: &SolverInput,
    rotation_context: RotationResolveContext,
) -> PhaseConfig {
    let total_budget_s = (input.time_limit_s as f64).max(1.0);
    let mut config = PhaseConfig::deterministic_default();
    config.seed = input.seed;
    config.worker_count = 1;
    config.rotation_context = rotation_context;
    config.exploration_budget = PhaseBudget::new(16, total_budget_s * 0.60);
    config.compression_budget = PhaseBudget::new(8, total_budget_s * 0.25);
    config.bpp_budget = PhaseBudget::new(4, total_budget_s * 0.15);
    config.bpp_max_eliminations = 16;
    config.collision_backend = resolve_backend_kind(input);
    config
}

#[allow(dead_code)]
fn phase_commit_or_unsupported(
    input: &SolverInput,
    layout: WorkingLayout,
    parts: &[crate::item::Part],
    sheets: &[crate::sheet::SheetShape],
) -> Result<(Vec<Placement>, Vec<Unplaced>), SolverOutput> {
    layout
        .validate_and_commit(parts, sheets)
        .map_err(|_| _unsupported_output("PHASE_OPTIMIZER_COMMIT_VIOLATION", input))
}

pub fn solve(input: SolverInput) -> Result<SolverOutput, String> {
    if input.solver_profile.as_deref() == Some(PROFILE_PHASE1) {
        for part in &input.parts {
            if part_has_holes(part) {
                return Ok(_unsupported_output("UNSUPPORTED_PART_HOLES_PHASE1", &input));
            }
        }
        for stock in &input.stocks {
            if stock_has_holes(stock) {
                return Ok(_unsupported_output(
                    "UNSUPPORTED_STOCK_HOLES_PHASE1",
                    &input,
                ));
            }
        }
        if let Some(margin_mm) = input.margin_mm {
            if margin_mm > 0.0 {
                return Ok(_unsupported_output("UNSUPPORTED_MARGIN_MM_RUNTIME", &input));
            }
        }
    }

    let rotation_context = RotationResolveContext::new(
        input.rotation_policy.clone(),
        input.seed as u64,
        DEFAULT_CONTINUOUS_SAMPLE_COUNT,
    );
    let sheets = expand_sheets(&input.stocks)?;
    let all_instances = expand_instances_with_policy(&input.parts, &rotation_context)?;
    let pipeline = pipeline_kind(&input);
    let mut collision_backend_diag: Option<CollisionBackendDiagnosticsOutput> = None;
    let (placements, unplaced, optimizer_diagnostics) = if input.solver_profile.as_deref()
        == Some(PROFILE_PHASE1)
    {
        // Pre-filter: instances whose part cannot fit any sheet get PART_NEVER_FITS_STOCK.
        let mut pre_unplaced: Vec<Unplaced> = Vec::new();
        let mut instances: Vec<_> = Vec::new();
        for inst in all_instances {
            let part = input
                .parts
                .iter()
                .find(|p| p.id == inst.part_id)
                .ok_or_else(|| format!("internal error: part not found: {}", inst.part_id))?;
            if !can_fit_any_stock_with_policy(part, &sheets, &rotation_context)? {
                pre_unplaced.push(Unplaced {
                    instance_id: inst.instance_id,
                    part_id: inst.part_id,
                    reason: "PART_NEVER_FITS_STOCK".to_string(),
                });
            } else {
                instances.push(inst);
            }
        }
        let backend_kind = resolve_backend_kind(&input);
        match pipeline {
            OptimizerPipelineKind::LegacyMultisheet => {
                let repair_time_s = (input.time_limit_s as f64).max(1.0);
                let mut policy = StoppingPolicy::new(256, repair_time_s);
                let manager = MultiSheetManager::new_with_rotation_context(
                    &input.parts,
                    &sheets,
                    rotation_context.clone(),
                );
                let (p, mut u, _ms_diag) = manager.run(&instances, &mut policy);
                u.extend(pre_unplaced);
                if backend_kind != CollisionBackendKind::Bbox {
                    let working = WorkingLayout::new(p, u, sheets.len(), input.seed);
                    match working.validate_and_commit_with_backend(
                        &input.parts,
                        &sheets,
                        backend_kind,
                    ) {
                        Ok(commit) => {
                            collision_backend_diag = Some(diag_output_from(&commit));
                            (commit.placements, commit.unplaced, None)
                        }
                        Err(e) => {
                            let reason = backend_err_reason(e, "COLLISION_BACKEND_COMMIT_VIOLATION");
                            return Ok(_unsupported_output(&reason, &input));
                        }
                    }
                } else {
                    (p, u, None)
                }
            }
            OptimizerPipelineKind::PhaseOptimizer => {
                let (init_p, mut init_u, _construction_diag) =
                    build_initial_layout_with_rotation_context(
                        &instances,
                        &input.parts,
                        &sheets,
                        &rotation_context,
                    );
                init_u.extend(pre_unplaced);
                let working = WorkingLayout::new(init_p, init_u, sheets.len(), input.seed);
                let config = phase_config_from_input(&input, rotation_context.clone());
                let result = PhaseOptimizer::new(config).run(working, &input.parts, &sheets);
                let diagnostics = OptimizerDiagnosticsOutput {
                    pipeline_used: "phase_optimizer".to_string(),
                    phase_optimizer_invoked: true,
                    exploration_iterations: result.diagnostics.exploration_iterations,
                    compression_iterations: result.diagnostics.compression_iterations,
                    bpp_attempts: result.diagnostics.bpp_attempts,
                };
                let layout = result.layout;
                match layout.validate_and_commit_with_backend(
                    &input.parts,
                    &sheets,
                    backend_kind,
                ) {
                    Ok(commit) => {
                        collision_backend_diag = Some(diag_output_from(&commit));
                        (commit.placements, commit.unplaced, Some(diagnostics))
                    }
                    Err(e) => {
                        let reason = backend_err_reason(
                            e,
                            "PHASE_OPTIMIZER_COMMIT_VIOLATION_BACKEND",
                        );
                        return Ok(_unsupported_output(&reason, &input));
                    }
                }
            }
        }
    } else {
        // Row/cursor fallback for non-Phase1 profiles.
        let mut placements: Vec<Placement> = Vec::new();
        let mut unplaced: Vec<Unplaced> = Vec::new();
        let mut per_sheet_cursor: Vec<SheetCursor> = sheets
            .iter()
            .map(|_| SheetCursor {
                x: 0.0,
                y: 0.0,
                row_h: 0.0,
            })
            .collect();
        for instance in &all_instances {
            let part = input
                .parts
                .iter()
                .find(|p| p.id == instance.part_id)
                .ok_or_else(|| format!("internal error: part not found: {}", instance.part_id))?;
            if !can_fit_any_stock_with_policy(part, &sheets, &rotation_context)? {
                unplaced.push(Unplaced {
                    instance_id: instance.instance_id.clone(),
                    part_id: instance.part_id.clone(),
                    reason: "PART_NEVER_FITS_STOCK".to_string(),
                });
                continue;
            }
            let mut placed = None;
            for (idx, sheet) in sheets.iter().enumerate() {
                if let Some(c) =
                    try_place_on_sheet(instance, sheet, &mut per_sheet_cursor[idx], idx)
                {
                    placed = Some(c);
                    break;
                }
            }
            if let Some(p) = placed {
                placements.push(p);
            } else {
                unplaced.push(Unplaced {
                    instance_id: instance.instance_id.clone(),
                    part_id: instance.part_id.clone(),
                    reason: "NO_CAPACITY".to_string(),
                });
            }
        }
        (placements, unplaced, None)
    };
    // Compute score breakdown for Phase1 profile (JG-19 — backward-compatible optional output field).
    let score_breakdown = if input.solver_profile.as_deref() == Some(PROFILE_PHASE1) {
        let model = ScoreModel::default();
        let result = model.score(&placements, &unplaced, &input.parts, &sheets);
        let bd = &result.breakdown;
        Some(ScoreBreakdownOutput {
            total_cost: bd.total_cost,
            placed_area_contribution: bd.placed_area_contribution,
            unplaced_contribution: bd.unplaced_contribution,
            sheet_cost_contribution: bd.sheet_count_contribution,
            sheet_cost_total: bd.sheet_cost_total,
            usable_area_utilization: bd.usable_area_utilization,
            overlap_contribution: bd.overlap_contribution,
            boundary_contribution: bd.boundary_contribution,
            compactness_contribution: bd.compactness_contribution,
        })
    } else {
        None
    };
    let status = if unplaced.is_empty() { "ok" } else { "partial" }.to_string();
    let sheet_count_used = placements
        .iter()
        .map(|p| p.sheet_index)
        .max()
        .map(|v| v + 1)
        .unwrap_or(0);

    let placed_count = placements.len();
    let unplaced_count = unplaced.len();

    Ok(SolverOutput {
        contract_version: "v1".to_string(),
        status,
        unsupported_reason: None,
        placements,
        unplaced,
        metrics: Metrics {
            placed_count,
            unplaced_count,
            sheet_count_used,
            seed: input.seed,
            time_limit_s: input.time_limit_s,
            project_name: input.project_name,
        },
        score_breakdown,
        optimizer_diagnostics,
        collision_backend_diagnostics: collision_backend_diag,
    })
}

// ---------------------------------------------------------------------------
// JaguaAdapter contract — VRS-owned PoC boundary (JG-04)
// Jagua-rs types stay internal; only VRS geometry types cross the public API.
// ---------------------------------------------------------------------------

/// VRS-owned error categories for the jagua backend boundary.
/// No jagua-rs types appear here.
#[derive(Debug)]
pub enum JaguaAdapterError {
    /// Input geometry could not be converted to jagua internal representation.
    ConversionError(String),
    /// A jagua backend operation returned an unexpected runtime error.
    BackendError(String),
    /// The requested operation is not yet supported by the adapter PoC.
    Unsupported(String),
}

impl fmt::Display for JaguaAdapterError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::ConversionError(s) => write!(f, "conversion_error: {s}"),
            Self::BackendError(s) => write!(f, "backend_error: {s}"),
            Self::Unsupported(s) => write!(f, "unsupported: {s}"),
        }
    }
}

/// Thin VRS adapter to the jagua-rs collision/geometry backend.
/// Accepts VRS-owned point slices; jagua types never appear in the public API.
/// Precision note: f64 VRS coordinates are narrowed to f32 for jagua (documented).
pub struct JaguaAdapter;

impl JaguaAdapter {
    /// Returns `true` if the two polygons (given as VRS Point slices) collide.
    ///
    /// Detection strategy (composing known jagua primitives):
    /// 1. Any corner of poly_b inside poly_a → collision.
    /// 2. Any corner of poly_a inside poly_b → collision.
    /// 3. Any edge of poly_a intersects any edge of poly_b → collision.
    pub fn check_polygon_collision(
        poly_a: &[crate::geometry::Point],
        poly_b: &[crate::geometry::Point],
    ) -> Result<bool, JaguaAdapterError> {
        use crate::geometry::{jag_edge_from_points, to_jag_point, to_jag_polygon};
        use jagua_rs::geometry::geo_traits::CollidesWith;

        let spoly_a =
            to_jag_polygon(poly_a, "poly_a").map_err(JaguaAdapterError::ConversionError)?;
        let spoly_b =
            to_jag_polygon(poly_b, "poly_b").map_err(JaguaAdapterError::ConversionError)?;

        // Point containment: any corner of B inside A?
        for p in poly_b {
            if spoly_a.collides_with(&to_jag_point(*p)) {
                return Ok(true);
            }
        }
        // Point containment: any corner of A inside B?
        for p in poly_a {
            if spoly_b.collides_with(&to_jag_point(*p)) {
                return Ok(true);
            }
        }
        // Edge-edge intersection
        let n_a = poly_a.len();
        let n_b = poly_b.len();
        for i in 0..n_a {
            let Some(edge_a) = jag_edge_from_points(poly_a[i], poly_a[(i + 1) % n_a]) else {
                continue;
            };
            for j in 0..n_b {
                let Some(edge_b) = jag_edge_from_points(poly_b[j], poly_b[(j + 1) % n_b]) else {
                    continue;
                };
                if edge_a.collides_with(&edge_b) {
                    return Ok(true);
                }
            }
        }
        Ok(false)
    }

    /// Returns `true` if the rectangular item fits entirely inside the sheet shape.
    /// Delegates to `optimizer::boundary::rect_within_boundary` — the canonical
    /// boundary policy point for all construction, repair, and scoring paths.
    pub fn check_rect_in_sheet(
        item_rect: crate::geometry::Rect,
        sheet: &crate::sheet::SheetShape,
    ) -> bool {
        crate::optimizer::boundary::rect_within_boundary(item_rect, sheet)
    }
}

#[cfg(test)]
mod tests {
    use super::{phase_commit_or_unsupported, solve};
    use crate::io::{CollisionBackendKind, OptimizerPipelineKind, Placement, SolverInput, SolverOutput};
    use crate::item::Part;
    use crate::optimizer::repair::find_violations;
    use crate::optimizer::working::WorkingLayout;
    use crate::rotation_policy::RotationPolicyKind;
    use crate::sheet::{expand_sheets, Stock};

    fn make_part(
        id: &str,
        w: f64,
        h: f64,
        qty: i64,
        rots: Vec<i64>,
        rotation_policy: Option<RotationPolicyKind>,
    ) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: qty,
            allowed_rotations_deg: rots,
            rotation_policy,
            holes_points: None,
            prepared_holes_points: None,
            outer_points: None,
            prepared_outer_points: None,
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

    fn make_input(
        seed: i64,
        stocks: Vec<Stock>,
        parts: Vec<Part>,
        rotation_policy: Option<RotationPolicyKind>,
    ) -> SolverInput {
        SolverInput {
            contract_version: "v1".to_string(),
            project_name: "test".to_string(),
            seed,
            time_limit_s: 5,
            stocks,
            parts,
            solver_profile: Some("jagua_optimizer_phase1_outer_only".to_string()),
            margin_mm: None,
            rotation_policy,
            optimizer_pipeline: None,
            collision_backend: None,
        }
    }

    fn assert_same_output(left: &SolverOutput, right: &SolverOutput) {
        assert_eq!(left.contract_version, right.contract_version);
        assert_eq!(left.status, right.status);
        assert_eq!(left.unsupported_reason, right.unsupported_reason);
        assert_eq!(left.metrics.placed_count, right.metrics.placed_count);
        assert_eq!(left.metrics.unplaced_count, right.metrics.unplaced_count);
        assert_eq!(
            left.metrics.sheet_count_used,
            right.metrics.sheet_count_used
        );
        assert_eq!(left.metrics.seed, right.metrics.seed);
        assert_eq!(left.metrics.time_limit_s, right.metrics.time_limit_s);
        assert_eq!(left.metrics.project_name, right.metrics.project_name);
        assert_eq!(left.placements.len(), right.placements.len());
        for (a, b) in left.placements.iter().zip(right.placements.iter()) {
            assert_eq!(a.instance_id, b.instance_id);
            assert_eq!(a.part_id, b.part_id);
            assert_eq!(a.sheet_index, b.sheet_index);
            assert!((a.x - b.x).abs() < 1e-9);
            assert!((a.y - b.y).abs() < 1e-9);
            assert!((a.rotation_deg - b.rotation_deg).abs() < 1e-9);
        }
        assert_eq!(left.unplaced.len(), right.unplaced.len());
        for (a, b) in left.unplaced.iter().zip(right.unplaced.iter()) {
            assert_eq!(a.instance_id, b.instance_id);
            assert_eq!(a.part_id, b.part_id);
            assert_eq!(a.reason, b.reason);
        }
        assert_eq!(
            left.optimizer_diagnostics.is_some(),
            right.optimizer_diagnostics.is_some()
        );
        assert_eq!(
            left.collision_backend_diagnostics.is_some(),
            right.collision_backend_diagnostics.is_some()
        );
    }

    #[test]
    fn adapter_solve_global_forty_five_places_100x20_on_90x90_sheet() {
        let stock = vec![make_stock("S", 90.0, 90.0, 1)];
        let parts = vec![make_part("P", 100.0, 20.0, 1, vec![], None)];

        let mut no_global = make_input(7, stock.clone(), parts.clone(), None);
        no_global.rotation_policy = Some(RotationPolicyKind::Orthogonal);
        let out_a = solve(no_global).expect("solve A");
        assert_eq!(out_a.metrics.placed_count, 0);
        assert_eq!(out_a.metrics.unplaced_count, 1);

        let with_global = make_input(7, stock, parts, Some(RotationPolicyKind::FortyFive));
        let out_b = solve(with_global).expect("solve B");
        assert_eq!(out_b.metrics.placed_count, 1);
        assert_eq!(out_b.metrics.unplaced_count, 0);
        assert_eq!(out_b.status, "ok");
    }

    #[test]
    fn adapter_solve_legacy_allowed_rotations_overrides_global_policy() {
        let stock = vec![make_stock("S", 90.0, 90.0, 1)];
        let parts = vec![make_part("P", 100.0, 20.0, 1, vec![0], None)];
        let input = make_input(9, stock, parts, Some(RotationPolicyKind::FortyFive));
        let out = solve(input).expect("solve");
        assert_eq!(out.metrics.placed_count, 0);
        assert_eq!(out.metrics.unplaced_count, 1);
    }

    #[test]
    fn part_policy_overrides_global_policy_in_real_solve_path() {
        let stock = vec![make_stock("S", 90.0, 90.0, 1)];
        let parts = vec![make_part(
            "P",
            100.0,
            20.0,
            1,
            vec![],
            Some(RotationPolicyKind::FortyFive),
        )];
        let input = make_input(9, stock, parts, Some(RotationPolicyKind::Orthogonal));
        let out = solve(input).expect("solve");
        assert_eq!(out.metrics.placed_count, 1);
        assert_eq!(out.metrics.unplaced_count, 0);
    }

    #[test]
    fn continuous_policy_same_seed_deterministic_through_solve() {
        let stock = vec![make_stock("S", 90.0, 90.0, 1)];
        let parts = vec![make_part("P", 100.0, 20.0, 1, vec![], None)];
        let a = solve(make_input(
            12345,
            stock.clone(),
            parts.clone(),
            Some(RotationPolicyKind::Continuous),
        ))
        .expect("solve A");
        let b = solve(make_input(
            12345,
            stock,
            parts,
            Some(RotationPolicyKind::Continuous),
        ))
        .expect("solve B");
        assert_eq!(a.metrics.placed_count, b.metrics.placed_count);
        assert_eq!(a.metrics.unplaced_count, b.metrics.unplaced_count);
        assert_eq!(a.placements.len(), b.placements.len());
        for (pa, pb) in a.placements.iter().zip(b.placements.iter()) {
            assert_eq!(pa.instance_id, pb.instance_id);
            assert_eq!(pa.part_id, pb.part_id);
            assert_eq!(pa.sheet_index, pb.sheet_index);
            assert!((pa.rotation_deg - pb.rotation_deg).abs() < 1e-9);
            assert!((pa.x - pb.x).abs() < 1e-9);
            assert!((pa.y - pb.y).abs() < 1e-9);
        }
    }

    #[test]
    fn solver_input_optimizer_pipeline_defaults_to_legacy() {
        let json = r#"{
            "contract_version": "v1",
            "project_name": "default_pipeline",
            "seed": 1,
            "time_limit_s": 5,
            "stocks": [{"id": "S", "quantity": 1, "width": 100.0, "height": 100.0}],
            "parts": [{"id": "P", "width": 10.0, "height": 10.0, "quantity": 1}]
        }"#;
        let input: SolverInput = serde_json::from_str(json).expect("input");
        assert_eq!(
            input.optimizer_pipeline.unwrap_or_default(),
            OptimizerPipelineKind::LegacyMultisheet
        );
    }

    #[test]
    fn legacy_explicit_matches_implicit_output() {
        let stock = vec![make_stock("S", 160.0, 100.0, 1)];
        let parts = vec![make_part("P", 40.0, 20.0, 3, vec![0], None)];

        let implicit = solve(make_input(17, stock.clone(), parts.clone(), None)).expect("implicit");
        let mut explicit_input = make_input(17, stock, parts, None);
        explicit_input.optimizer_pipeline = Some(OptimizerPipelineKind::LegacyMultisheet);
        let explicit = solve(explicit_input).expect("explicit");

        assert_same_output(&implicit, &explicit);
    }

    #[test]
    fn phase_optimizer_pipeline_invokes_phase_optimizer() {
        let stock = vec![make_stock("S", 160.0, 100.0, 1)];
        let parts = vec![make_part("P", 40.0, 20.0, 2, vec![0], None)];
        let mut input = make_input(21, stock, parts, None);
        input.optimizer_pipeline = Some(OptimizerPipelineKind::PhaseOptimizer);

        let out = solve(input).expect("phase solve");
        let diag = out.optimizer_diagnostics.expect("phase diagnostics");
        assert_eq!(diag.pipeline_used, "phase_optimizer");
        assert!(diag.phase_optimizer_invoked);
        assert!(diag.exploration_iterations + diag.compression_iterations + diag.bpp_attempts > 0);
    }

    #[test]
    fn phase_optimizer_pipeline_preserves_rotation_context() {
        let stock = vec![make_stock("S", 90.0, 90.0, 1)];
        let parts = vec![make_part("P", 100.0, 20.0, 1, vec![], None)];
        let mut input = make_input(21, stock, parts, Some(RotationPolicyKind::FortyFive));
        input.optimizer_pipeline = Some(OptimizerPipelineKind::PhaseOptimizer);

        let out = solve(input).expect("phase solve");
        assert_eq!(out.metrics.placed_count, 1);
        assert_eq!(out.metrics.unplaced_count, 0);
    }

    #[test]
    fn phase_optimizer_pipeline_is_deterministic_for_same_seed() {
        let stock = vec![make_stock("S", 160.0, 100.0, 1)];
        let parts = vec![make_part("P", 40.0, 20.0, 3, vec![0], None)];

        let mut a = make_input(33, stock.clone(), parts.clone(), None);
        a.optimizer_pipeline = Some(OptimizerPipelineKind::PhaseOptimizer);
        let mut b = make_input(33, stock, parts, None);
        b.optimizer_pipeline = Some(OptimizerPipelineKind::PhaseOptimizer);

        let out_a = solve(a).expect("phase A");
        let out_b = solve(b).expect("phase B");
        assert_same_output(&out_a, &out_b);
    }

    #[test]
    fn phase_optimizer_pipeline_output_has_no_violations() {
        let stock = vec![make_stock("S", 160.0, 100.0, 1)];
        let parts = vec![make_part("P", 40.0, 20.0, 3, vec![0], None)];
        let sheets = expand_sheets(&stock).expect("sheets");
        let mut input = make_input(41, stock, parts.clone(), None);
        input.optimizer_pipeline = Some(OptimizerPipelineKind::PhaseOptimizer);

        let out = solve(input).expect("phase solve");
        assert!(find_violations(&out.placements, &parts, &sheets).is_empty());
    }

    // ── Q10: collision backend policy tests ──────────────────────────────────

    #[test]
    fn solver_input_collision_backend_defaults_to_bbox() {
        let json = r#"{
            "contract_version": "v1",
            "project_name": "p",
            "seed": 1,
            "time_limit_s": 5,
            "stocks": [{"id": "S", "quantity": 1, "width": 100.0, "height": 100.0}],
            "parts": [{"id": "P", "width": 10.0, "height": 10.0, "quantity": 1}]
        }"#;
        let input: SolverInput = serde_json::from_str(json).expect("deserialize");
        assert!(input.collision_backend.is_none(), "missing field must deserialize to None");
        assert_eq!(
            input.collision_backend.unwrap_or_default(),
            CollisionBackendKind::Bbox
        );
    }

    #[test]
    fn jagua_polygon_exact_backend_can_be_selected_in_solver_input() {
        let json = r#"{
            "contract_version": "v1",
            "project_name": "p",
            "seed": 1,
            "time_limit_s": 5,
            "stocks": [{"id": "S", "quantity": 1, "width": 100.0, "height": 100.0}],
            "parts": [{"id": "P", "width": 10.0, "height": 10.0, "quantity": 1}],
            "collision_backend": "jagua_polygon_exact"
        }"#;
        let input: SolverInput = serde_json::from_str(json).expect("deserialize");
        assert_eq!(input.collision_backend, Some(CollisionBackendKind::JaguaPolygonExact));
    }

    #[test]
    fn explicit_bbox_matches_implicit_default_output() {
        let stock = vec![make_stock("S", 160.0, 100.0, 1)];
        let parts = vec![make_part("P", 40.0, 20.0, 2, vec![0], None)];

        let implicit = solve(make_input(17, stock.clone(), parts.clone(), None)).expect("implicit");
        let mut explicit_input = make_input(17, stock, parts, None);
        explicit_input.collision_backend = Some(CollisionBackendKind::Bbox);
        let explicit = solve(explicit_input).expect("explicit");

        assert_eq!(implicit.status, explicit.status);
        assert_eq!(implicit.metrics.placed_count, explicit.metrics.placed_count);
        assert_eq!(implicit.placements.len(), explicit.placements.len());
    }

    #[test]
    fn phase_optimizer_with_bbox_backend_preserves_q09_behavior() {
        let stock = vec![make_stock("S", 160.0, 100.0, 1)];
        let parts = vec![make_part("P", 40.0, 20.0, 2, vec![0], None)];

        let mut without_backend = make_input(33, stock.clone(), parts.clone(), None);
        without_backend.optimizer_pipeline = Some(OptimizerPipelineKind::PhaseOptimizer);
        let out_a = solve(without_backend).expect("phase without backend");

        let mut with_bbox = make_input(33, stock, parts, None);
        with_bbox.optimizer_pipeline = Some(OptimizerPipelineKind::PhaseOptimizer);
        with_bbox.collision_backend = Some(CollisionBackendKind::Bbox);
        let out_b = solve(with_bbox).expect("phase with bbox");

        assert_eq!(out_a.status, out_b.status);
        assert_eq!(out_a.metrics.placed_count, out_b.metrics.placed_count);
        assert_eq!(out_a.placements.len(), out_b.placements.len());
    }

    #[test]
    fn jagua_polygon_exact_invalid_outer_points_returns_unsupported_not_bbox_fallback() {
        // Part with malformed outer_points — JaguaPolygonExactBackend returns Unsupported.
        // bbox backend (default) would ignore outer_points and produce ok/partial.
        // jagua_polygon_exact backend must produce status=unsupported (no silent downgrade).
        let json_exact = r#"{
            "contract_version": "v1",
            "project_name": "test_exact_invalid",
            "seed": 1,
            "time_limit_s": 5,
            "solver_profile": "jagua_optimizer_phase1_outer_only",
            "stocks": [{"id": "S", "quantity": 1, "width": 100.0, "height": 100.0}],
            "parts": [{
                "id": "P",
                "width": 20.0,
                "height": 20.0,
                "quantity": 1,
                "outer_points": [["x_bad", 0.0], [10.0, 0.0], [10.0, 10.0]]
            }],
            "collision_backend": "jagua_polygon_exact"
        }"#;
        let input: SolverInput = serde_json::from_str(json_exact).expect("deserialize exact");
        let out = solve(input).expect("solve");
        assert_eq!(out.status, "unsupported",
            "jagua_polygon_exact with invalid outer_points must be unsupported, not ok/partial");
        assert_eq!(
            out.unsupported_reason.as_deref(),
            Some("JAGUA_POLYGON_EXACT_UNSUPPORTED_QUERY"),
            "reason must be JAGUA_POLYGON_EXACT_UNSUPPORTED_QUERY"
        );
        assert!(out.placements.is_empty());

        // Contrast: bbox default ignores outer_points and places successfully.
        let json_bbox = r#"{
            "contract_version": "v1",
            "project_name": "test_bbox_default",
            "seed": 1,
            "time_limit_s": 5,
            "solver_profile": "jagua_optimizer_phase1_outer_only",
            "stocks": [{"id": "S", "quantity": 1, "width": 100.0, "height": 100.0}],
            "parts": [{
                "id": "P",
                "width": 20.0,
                "height": 20.0,
                "quantity": 1,
                "outer_points": [["x_bad", 0.0], [10.0, 0.0], [10.0, 10.0]]
            }]
        }"#;
        let input_bbox: SolverInput = serde_json::from_str(json_bbox).expect("deserialize bbox");
        let out_bbox = solve(input_bbox).expect("solve bbox");
        assert_ne!(out_bbox.status, "unsupported",
            "bbox default must not return unsupported for malformed outer_points");
    }

    #[test]
    fn cde_backend_returns_unsupported_not_bbox_fallback() {
        let stock = vec![make_stock("S", 100.0, 100.0, 1)];
        let parts = vec![make_part("P", 20.0, 20.0, 1, vec![0], None)];
        let mut input = make_input(1, stock, parts, None);
        input.collision_backend = Some(CollisionBackendKind::Cde);
        let out = solve(input).expect("solve");
        assert_eq!(out.status, "unsupported",
            "cde backend must produce unsupported output, not ok/partial");
        assert_eq!(
            out.unsupported_reason.as_deref(),
            Some("CDE_BACKEND_UNSUPPORTED"),
            "reason must be CDE_BACKEND_UNSUPPORTED"
        );
        assert!(out.placements.is_empty());
    }

    #[test]
    fn same_seed_same_backend_is_deterministic() {
        let stock = vec![make_stock("S", 160.0, 100.0, 1)];
        let parts = vec![make_part("P", 40.0, 20.0, 3, vec![0], None)];

        for backend in [None, Some(CollisionBackendKind::Bbox), Some(CollisionBackendKind::JaguaPolygonExact)] {
            let mut a = make_input(42, stock.clone(), parts.clone(), None);
            a.collision_backend = backend.clone();
            let mut b = make_input(42, stock.clone(), parts.clone(), None);
            b.collision_backend = backend;

            let out_a = solve(a).expect("solve A");
            let out_b = solve(b).expect("solve B");

            assert_eq!(out_a.status, out_b.status, "status must be deterministic");
            assert_eq!(out_a.metrics.placed_count, out_b.metrics.placed_count);
            assert_eq!(out_a.placements.len(), out_b.placements.len());
            for (pa, pb) in out_a.placements.iter().zip(out_b.placements.iter()) {
                assert_eq!(pa.instance_id, pb.instance_id);
                assert!((pa.x - pb.x).abs() < 1e-9);
                assert!((pa.y - pb.y).abs() < 1e-9);
                assert!((pa.rotation_deg - pb.rotation_deg).abs() < 1e-9);
            }
        }
    }

    #[test]
    fn jagua_polygon_exact_l_shape_notch_does_not_report_bbox_false_positive() {
        // Helper-level: JaguaPolygonExactBackend must report NoCollision when B sits in A's notch.
        // This test confirms the backend does not produce the bbox false-positive.
        use crate::optimizer::collision_backend::{BboxCollisionBackend, JaguaPolygonExactBackend, CollisionBackend};
        let l_json = serde_json::json!([
            [0.0, 0.0], [40.0, 0.0], [40.0, 20.0],
            [20.0, 20.0], [20.0, 40.0], [0.0, 40.0]
        ]);
        let part_a = crate::item::Part {
            id: "L".to_string(),
            width: 40.0,
            height: 40.0,
            quantity: 1,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: Some(l_json),
            prepared_outer_points: None,
            rotation_policy: None,
        };
        let part_b = crate::item::Part {
            id: "B".to_string(),
            width: 15.0,
            height: 15.0,
            quantity: 1,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: None,
            prepared_outer_points: None,
            rotation_policy: None,
        };
        let p_a = Placement { instance_id: "L__0001".into(), part_id: "L".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 };
        let p_b = Placement { instance_id: "B__0001".into(), part_id: "B".into(), sheet_index: 0, x: 22.0, y: 22.0, rotation_deg: 0.0 };

        let bbox = BboxCollisionBackend;
        let exact = JaguaPolygonExactBackend;
        assert!(bbox.placement_overlaps(&p_a, &part_a, &p_b, &part_b).is_collision(),
            "bbox must report false positive for notch");
        assert!(exact.placement_overlaps(&p_a, &part_a, &p_b, &part_b).is_no_collision(),
            "exact backend must report no collision for item in notch");
    }

    #[test]
    fn phase_optimizer_invalid_commit_does_not_silently_fallback_to_legacy() {
        let stock = vec![make_stock("S", 100.0, 100.0, 1)];
        let parts = vec![make_part("P", 50.0, 50.0, 2, vec![0], None)];
        let input = make_input(51, stock.clone(), parts.clone(), None);
        let sheets = expand_sheets(&stock).expect("sheets");
        let invalid = WorkingLayout::new(
            vec![
                Placement {
                    instance_id: "P__0001".into(),
                    part_id: "P".into(),
                    sheet_index: 0,
                    x: 0.0,
                    y: 0.0,
                    rotation_deg: 0.0,
                },
                Placement {
                    instance_id: "P__0002".into(),
                    part_id: "P".into(),
                    sheet_index: 0,
                    x: 0.0,
                    y: 0.0,
                    rotation_deg: 0.0,
                },
            ],
            vec![],
            sheets.len(),
            input.seed,
        );

        let rejected = phase_commit_or_unsupported(&input, invalid, &parts, &sheets)
            .expect_err("invalid phase commit must be rejected");
        assert_eq!(rejected.status, "unsupported");
        assert_eq!(
            rejected.unsupported_reason.as_deref(),
            Some("PHASE_OPTIMIZER_COMMIT_VIOLATION")
        );
        assert!(rejected.placements.is_empty());
    }

    // -----------------------------------------------------------------------
    // SGH-Q11 tests
    // -----------------------------------------------------------------------

    #[test]
    fn adapter_phase_optimizer_passes_collision_backend_to_phase_config() {
        use crate::rotation_policy::RotationResolveContext;

        // Build an input with explicit JaguaPolygonExact backend.
        let stock = vec![make_stock("S", 100.0, 100.0, 1)];
        let parts = vec![make_part("P", 20.0, 20.0, 1, vec![0], None)];
        let mut input = make_input(99, stock, parts, None);
        input.collision_backend = Some(CollisionBackendKind::JaguaPolygonExact);

        // Reconstruct phase config the same way adapter.rs does.
        let rc = RotationResolveContext::legacy_default();
        let cfg = super::phase_config_from_input(&input, rc);

        assert!(
            matches!(cfg.collision_backend, CollisionBackendKind::JaguaPolygonExact),
            "phase_config_from_input must propagate collision_backend from SolverInput"
        );
    }
}
