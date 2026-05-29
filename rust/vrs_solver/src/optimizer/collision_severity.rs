/// SGH-Q21: Central backend-aware collision severity / evaluate_transform layer.
///
/// Replaces local bbox-proxy severity in search_position and separator/GLS with
/// backend-confirmed severity under CDE/JaguaPolygonExact backends.
///
/// When the backend confirms a collision but cannot provide exact penetration depth,
/// an oracle-probe strategy is used: translate the candidate in +x/-x/+y/-y directions
/// with an exponentially increasing step until the backend reports NoCollision, then
/// use the minimum resolution distance as the severity signal. This is monotonically
/// related to overlap depth (deeper overlaps require larger steps to resolve).
use crate::geometry::Rect;
use crate::io::{CollisionBackendKind, Placement};
use crate::item::Part;
use crate::sheet::SheetShape;
use super::boundary::rect_within_boundary;
use super::candidates::PlacedBbox;
use super::collision_backend::{
    CdeCollisionBackend, CollisionBackend, CollisionDecision, JaguaPolygonExactBackend,
};
use super::initializer::bbox_from_placement;
use super::loss_model::LossModelKind;
use super::working::WorkingLayout;

pub const HARD_UNSUPPORTED_LOSS: f64 = 1_000_000.0;

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct CollisionSeverityConfig {
    /// Enable backend-aware severity for JaguaPolygonExact and CDE backends.
    /// When false, falls back to bbox proxy for all backends.
    pub enabled_for_exact_backends: bool,
    /// Enable oracle-probe severity estimation for confirmed collisions.
    /// When false, uses bbox proxy as severity for confirmed collisions (counted as bbox_proxy_severity_uses).
    pub probe_enabled: bool,
    /// Initial probe step = sheet_diagonal * this factor.
    pub probe_initial_step_factor: f64,
    /// Minimum probe step (mm). Steps below this are not tried.
    pub probe_min_step: f64,
    /// Maximum probe steps per direction before giving up.
    pub probe_max_steps: usize,
    /// Loss returned for Unsupported backend queries.
    pub hard_unsupported_loss: f64,
}

impl Default for CollisionSeverityConfig {
    fn default() -> Self {
        Self {
            enabled_for_exact_backends: true,
            probe_enabled: true,
            probe_initial_step_factor: 0.05,
            probe_min_step: 0.01,
            probe_max_steps: 5,
            hard_unsupported_loss: HARD_UNSUPPORTED_LOSS,
        }
    }
}

// ---------------------------------------------------------------------------
// Stats
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Default)]
pub struct CollisionSeverityStats {
    pub pair_queries: usize,
    pub boundary_queries: usize,
    pub probe_queries: usize,
    pub backend_confirmed_collisions: usize,
    pub backend_confirmed_no_collisions: usize,
    pub unsupported_queries: usize,
    pub bbox_proxy_severity_uses: usize,
}

impl CollisionSeverityStats {
    pub fn accumulate(&mut self, other: &Self) {
        self.pair_queries += other.pair_queries;
        self.boundary_queries += other.boundary_queries;
        self.probe_queries += other.probe_queries;
        self.backend_confirmed_collisions += other.backend_confirmed_collisions;
        self.backend_confirmed_no_collisions += other.backend_confirmed_no_collisions;
        self.unsupported_queries += other.unsupported_queries;
        self.bbox_proxy_severity_uses += other.bbox_proxy_severity_uses;
    }
}

// ---------------------------------------------------------------------------
// EvaluationResult
// ---------------------------------------------------------------------------

pub struct EvaluationResult {
    pub loss: f64,
    pub unsupported: bool,
    pub pair_collision_count: usize,
    pub boundary_collision: bool,
}

// ---------------------------------------------------------------------------
// Oracle-probe helpers (private)
// ---------------------------------------------------------------------------

/// Find the minimum translation distance in one of 4 cardinal directions
/// that resolves a pair collision according to the backend oracle.
///
/// Doubles the step each attempt. Returns `f64::MAX` if not resolved within probe_max_steps.
fn oracle_probe_resolution(
    backend: &dyn CollisionBackend,
    candidate: &Placement,
    part: &Part,
    other: &Placement,
    other_part: &Part,
    sheet_diag: f64,
    cfg: &CollisionSeverityConfig,
    stats: &mut CollisionSeverityStats,
) -> f64 {
    let initial_step = (cfg.probe_initial_step_factor * sheet_diag).max(cfg.probe_min_step);
    let mut min_resolution = f64::MAX;

    for &(dx, dy) in &[(1.0_f64, 0.0_f64), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0)] {
        let mut step = initial_step;
        for _ in 0..cfg.probe_max_steps {
            stats.probe_queries += 1;
            let probed = Placement {
                instance_id: candidate.instance_id.clone(),
                part_id: candidate.part_id.clone(),
                sheet_index: candidate.sheet_index,
                x: candidate.x + dx * step,
                y: candidate.y + dy * step,
                rotation_deg: candidate.rotation_deg,
            };
            match backend.placement_overlaps(&probed, part, other, other_part) {
                CollisionDecision::NoCollision => {
                    if step < min_resolution {
                        min_resolution = step;
                    }
                    break;
                }
                CollisionDecision::Collision => {
                    step *= 2.0;
                }
                CollisionDecision::Unsupported { .. } => {
                    break;
                }
            }
        }
    }

    if min_resolution == f64::MAX {
        // upper-bound: last step tried (2^probe_max_steps * initial_step)
        initial_step * (1u64 << cfg.probe_max_steps.min(53)) as f64
    } else {
        min_resolution
    }
}

/// Find the minimum translation distance that resolves a boundary violation.
fn oracle_probe_boundary_resolution(
    backend: &dyn CollisionBackend,
    candidate: &Placement,
    part: &Part,
    sheet: &SheetShape,
    cfg: &CollisionSeverityConfig,
    stats: &mut CollisionSeverityStats,
) -> f64 {
    let sheet_diag = (sheet.width * sheet.width + sheet.height * sheet.height).sqrt();
    let initial_step = (cfg.probe_initial_step_factor * sheet_diag).max(cfg.probe_min_step);
    let mut min_resolution = f64::MAX;

    for &(dx, dy) in &[(1.0_f64, 0.0_f64), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0)] {
        let mut step = initial_step;
        for _ in 0..cfg.probe_max_steps {
            stats.probe_queries += 1;
            let probed = Placement {
                instance_id: candidate.instance_id.clone(),
                part_id: candidate.part_id.clone(),
                sheet_index: candidate.sheet_index,
                x: candidate.x + dx * step,
                y: candidate.y + dy * step,
                rotation_deg: candidate.rotation_deg,
            };
            match backend.placement_within_sheet(&probed, part, sheet) {
                CollisionDecision::NoCollision => {
                    if step < min_resolution {
                        min_resolution = step;
                    }
                    break;
                }
                CollisionDecision::Collision => {
                    step *= 2.0;
                }
                CollisionDecision::Unsupported { .. } => {
                    break;
                }
            }
        }
    }

    if min_resolution == f64::MAX {
        initial_step * (1u64 << cfg.probe_max_steps.min(53)) as f64
    } else {
        min_resolution
    }
}

// ---------------------------------------------------------------------------
// Backend-aware evaluation (private)
// ---------------------------------------------------------------------------

fn eval_with_severity_backend(
    backend: &dyn CollisionBackend,
    candidate: &Placement,
    part: &Part,
    cand_bbox: &PlacedBbox,
    sheet: &SheetShape,
    layout: &WorkingLayout,
    target_idx: usize,
    parts: &[Part],
    loss_model: LossModelKind,
    cfg: &CollisionSeverityConfig,
    stats: &mut CollisionSeverityStats,
) -> EvaluationResult {
    let sheet_diag = (sheet.width * sheet.width + sheet.height * sheet.height).sqrt();

    stats.boundary_queries += 1;
    let (boundary_loss, boundary_collision) = match backend.placement_within_sheet(candidate, part, sheet) {
        CollisionDecision::NoCollision => {
            stats.backend_confirmed_no_collisions += 1;
            (0.0, false)
        }
        CollisionDecision::Collision => {
            stats.backend_confirmed_collisions += 1;
            let sev = if cfg.probe_enabled {
                oracle_probe_boundary_resolution(backend, candidate, part, sheet, cfg, stats).max(1.0)
            } else {
                stats.bbox_proxy_severity_uses += 1;
                loss_model.compute_boundary_loss(cand_bbox, sheet, false).max(1.0)
            };
            (sev, true)
        }
        CollisionDecision::Unsupported { .. } => {
            stats.unsupported_queries += 1;
            return EvaluationResult {
                loss: f64::MAX,
                unsupported: true,
                pair_collision_count: 0,
                boundary_collision: false,
            };
        }
    };

    let mut pair_loss = 0.0_f64;
    let mut pair_collision_count = 0usize;

    for (idx, other) in layout.placements.iter().enumerate() {
        if idx == target_idx || other.sheet_index != candidate.sheet_index {
            continue;
        }
        let Some(other_part) = parts.iter().find(|pt| pt.id == other.part_id) else {
            return EvaluationResult {
                loss: f64::MAX,
                unsupported: true,
                pair_collision_count,
                boundary_collision,
            };
        };

        stats.pair_queries += 1;
        match backend.placement_overlaps(candidate, part, other, other_part) {
            CollisionDecision::NoCollision => {
                stats.backend_confirmed_no_collisions += 1;
            }
            CollisionDecision::Collision => {
                stats.backend_confirmed_collisions += 1;
                pair_collision_count += 1;
                let sev = if cfg.probe_enabled {
                    oracle_probe_resolution(backend, candidate, part, other, other_part, sheet_diag, cfg, stats).max(1.0)
                } else {
                    stats.bbox_proxy_severity_uses += 1;
                    match bbox_from_placement(other, other_part.width, other_part.height) {
                        Some(ob) => loss_model.pair_loss(&ob, cand_bbox).max(1.0),
                        None => {
                            return EvaluationResult {
                                loss: f64::MAX,
                                unsupported: true,
                                pair_collision_count,
                                boundary_collision,
                            };
                        }
                    }
                };
                pair_loss += sev;
            }
            CollisionDecision::Unsupported { .. } => {
                stats.unsupported_queries += 1;
                return EvaluationResult {
                    loss: f64::MAX,
                    unsupported: true,
                    pair_collision_count,
                    boundary_collision,
                };
            }
        }
    }

    EvaluationResult {
        loss: boundary_loss + pair_loss,
        unsupported: false,
        pair_collision_count,
        boundary_collision,
    }
}

fn eval_bbox_loss(
    candidate: &Placement,
    cand_bbox: &PlacedBbox,
    sheet: &SheetShape,
    layout: &WorkingLayout,
    target_idx: usize,
    parts: &[Part],
    loss_model: LossModelKind,
) -> EvaluationResult {
    let rect = Rect {
        x1: cand_bbox.x1,
        y1: cand_bbox.y1,
        x2: cand_bbox.x2,
        y2: cand_bbox.y2,
    };
    if !rect_within_boundary(rect, sheet) {
        return EvaluationResult {
            loss: f64::MAX,
            unsupported: false,
            pair_collision_count: 0,
            boundary_collision: true,
        };
    }
    let pair_loss: f64 = layout
        .placements
        .iter()
        .enumerate()
        .filter(|(i, p)| *i != target_idx && p.sheet_index == candidate.sheet_index)
        .filter_map(|(_, p)| {
            parts
                .iter()
                .find(|pt| pt.id == p.part_id)
                .and_then(|pt| bbox_from_placement(p, pt.width, pt.height))
                .map(|pb| loss_model.pair_loss(&pb, cand_bbox))
        })
        .sum();
    EvaluationResult {
        loss: pair_loss,
        unsupported: false,
        pair_collision_count: if pair_loss > 0.0 { 1 } else { 0 },
        boundary_collision: false,
    }
}

// ---------------------------------------------------------------------------
// Central public evaluate_transform_loss
// ---------------------------------------------------------------------------

/// Evaluate the total loss for placing `candidate` at a given transform.
///
/// Bbox backend: preserves legacy loss_model behavior (no stats tracked).
/// CDE/JaguaPolygonExact: uses backend-confirmed collision/no-collision decisions.
///   - NoCollision → severity = 0 (no bbox false-positive).
///   - Collision → oracle-probe severity (monotonic with overlap depth).
///   - Unsupported → loss = f64::MAX, unsupported = true.
pub fn evaluate_transform_loss(
    candidate: &Placement,
    part: &Part,
    cand_bbox: &PlacedBbox,
    sheet: &SheetShape,
    layout: &WorkingLayout,
    target_idx: usize,
    parts: &[Part],
    collision_backend: &CollisionBackendKind,
    loss_model: LossModelKind,
    cfg: &CollisionSeverityConfig,
    stats: &mut CollisionSeverityStats,
) -> EvaluationResult {
    if !cfg.enabled_for_exact_backends || matches!(collision_backend, CollisionBackendKind::Bbox) {
        return eval_bbox_loss(candidate, cand_bbox, sheet, layout, target_idx, parts, loss_model);
    }
    match collision_backend {
        CollisionBackendKind::JaguaPolygonExact => eval_with_severity_backend(
            &JaguaPolygonExactBackend,
            candidate, part, cand_bbox, sheet, layout, target_idx, parts,
            loss_model, cfg, stats,
        ),
        CollisionBackendKind::Cde => eval_with_severity_backend(
            &CdeCollisionBackend,
            candidate, part, cand_bbox, sheet, layout, target_idx, parts,
            loss_model, cfg, stats,
        ),
        CollisionBackendKind::Bbox => unreachable!(),
    }
}

// ---------------------------------------------------------------------------
// Probe helpers for VrsCollisionTracker (separator)
// ---------------------------------------------------------------------------

/// Compute oracle-probe severity for a confirmed pair collision in the tracker.
///
/// Returns the minimum translation distance that resolves the collision,
/// usable as a severity value in pair_loss().
pub fn compute_probe_pair_severity(
    collision_backend: &CollisionBackendKind,
    pi: &Placement,
    part_i: &Part,
    pj: &Placement,
    part_j: &Part,
    sheet_diag: f64,
    cfg: &CollisionSeverityConfig,
    stats: &mut CollisionSeverityStats,
) -> f64 {
    if !cfg.probe_enabled {
        return 1.0;
    }
    match collision_backend {
        CollisionBackendKind::JaguaPolygonExact => {
            oracle_probe_resolution(&JaguaPolygonExactBackend, pi, part_i, pj, part_j, sheet_diag, cfg, stats)
        }
        CollisionBackendKind::Cde => {
            oracle_probe_resolution(&CdeCollisionBackend, pi, part_i, pj, part_j, sheet_diag, cfg, stats)
        }
        CollisionBackendKind::Bbox => 1.0,
    }
}

/// Compute oracle-probe severity for a confirmed boundary violation in the tracker.
///
/// Returns the minimum translation distance that resolves the violation.
pub fn compute_probe_boundary_severity(
    collision_backend: &CollisionBackendKind,
    pi: &Placement,
    part_i: &Part,
    sheet: &SheetShape,
    cfg: &CollisionSeverityConfig,
    stats: &mut CollisionSeverityStats,
) -> f64 {
    if !cfg.probe_enabled {
        return 1.0;
    }
    match collision_backend {
        CollisionBackendKind::JaguaPolygonExact => {
            oracle_probe_boundary_resolution(&JaguaPolygonExactBackend, pi, part_i, sheet, cfg, stats)
        }
        CollisionBackendKind::Cde => {
            oracle_probe_boundary_resolution(&CdeCollisionBackend, pi, part_i, sheet, cfg, stats)
        }
        CollisionBackendKind::Bbox => 1.0,
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::item::Part;
    use crate::io::Placement;
    use crate::optimizer::working::WorkingLayout;
    use crate::sheet::{expand_sheets, Stock};

    fn make_rect_part(id: &str, w: f64, h: f64) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: 1,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: None,
            prepared_outer_points: None,
            rotation_policy: None,
        }
    }

    fn make_placement(instance_id: &str, part_id: &str, x: f64, y: f64) -> Placement {
        Placement {
            instance_id: instance_id.to_string(),
            part_id: part_id.to_string(),
            sheet_index: 0,
            x,
            y,
            rotation_deg: 0.0,
        }
    }

    fn make_sheets_100x100() -> Vec<crate::sheet::SheetShape> {
        expand_sheets(&[Stock {
            id: "S".into(),
            quantity: 1,
            width: Some(100.0),
            height: Some(100.0),
            outer_points: None,
            holes_points: None,
            cost_per_use: None,
        }]).expect("expand_sheets")
    }

    fn default_cfg() -> CollisionSeverityConfig {
        CollisionSeverityConfig::default()
    }

    // -----------------------------------------------------------------------
    // Q21-T1: Bbox backend preserves legacy pair loss behavior
    // -----------------------------------------------------------------------
    #[test]
    fn collision_severity_bbox_backend_preserves_legacy_pair_loss() {
        let part_a = make_rect_part("A", 30.0, 30.0);
        let part_b = make_rect_part("B", 30.0, 30.0);
        let parts = vec![part_a.clone(), part_b.clone()];
        let sheets = make_sheets_100x100();

        // A at (0,0), B overlapping at (10, 10) → 20x20 = 400 overlap
        let layout = WorkingLayout::new(
            vec![
                make_placement("A__0001", "A", 0.0, 0.0),
                make_placement("B__0001", "B", 10.0, 10.0),
            ],
            vec![], 1, 0,
        );
        let sheet = &sheets[0];
        let candidate = make_placement("B__0001", "B", 10.0, 10.0);
        let cand_bbox = PlacedBbox { sheet_index: 0, x1: 10.0, y1: 10.0, x2: 40.0, y2: 40.0 };

        let loss_model = LossModelKind::BboxArea;
        let mut stats = CollisionSeverityStats::default();
        let cfg = default_cfg();

        let result = evaluate_transform_loss(
            &candidate, &part_b, &cand_bbox, sheet,
            &layout, 1, &parts,
            &CollisionBackendKind::Bbox, loss_model, &cfg, &mut stats,
        );
        // Bbox: A bbox = [0,0,30,30], cand bbox = [10,10,40,40]
        // dx = min(30,40) - max(0,10) = 30-10 = 20, dy = 30-10 = 20 → loss = 20*20 = 400
        assert!(!result.unsupported);
        assert!((result.loss - 400.0).abs() < 1e-9, "legacy pair loss must be dx*dy = 400, got {}", result.loss);
        assert_eq!(stats.pair_queries, 0, "Bbox backend must not use severity engine pair_queries");
    }

    // -----------------------------------------------------------------------
    // Q21-T2: Exact backend, no-collision zeroes bbox false-positive
    // -----------------------------------------------------------------------
    #[test]
    fn collision_severity_exact_backend_no_collision_zeroes_bbox_false_positive() {
        // L-shape notch fixture: L-shape at (0,0), small rect in the notch
        // Bbox says overlap (both fit in [0,0,40,40] bounding box)
        // JaguaPolygonExact says no collision (small rect is in the notch region)
        let l_json = serde_json::json!([
            [0.0, 0.0], [40.0, 0.0], [40.0, 20.0],
            [20.0, 20.0], [20.0, 40.0], [0.0, 40.0]
        ]);
        let l_part = Part {
            id: "L".to_string(), width: 40.0, height: 40.0, quantity: 1,
            allowed_rotations_deg: vec![0], holes_points: None, prepared_holes_points: None,
            outer_points: Some(l_json), prepared_outer_points: None, rotation_policy: None,
        };
        let b_part = make_rect_part("B", 15.0, 15.0);
        let parts = vec![l_part, b_part.clone()];

        let sheets = expand_sheets(&[Stock {
            id: "S".into(), quantity: 1, width: Some(100.0), height: Some(100.0),
            outer_points: None, holes_points: None, cost_per_use: None,
        }]).expect("sheets");

        let layout = WorkingLayout::new(
            vec![
                Placement { instance_id: "L__0001".into(), part_id: "L".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 },
                Placement { instance_id: "B__0001".into(), part_id: "B".into(), sheet_index: 0, x: 22.0, y: 22.0, rotation_deg: 0.0 },
            ],
            vec![], 1, 0,
        );
        let sheet = &sheets[0];
        let candidate = Placement { instance_id: "B__0001".into(), part_id: "B".into(), sheet_index: 0, x: 22.0, y: 22.0, rotation_deg: 0.0 };
        let cand_bbox = PlacedBbox { sheet_index: 0, x1: 22.0, y1: 22.0, x2: 37.0, y2: 37.0 };

        // Verify bbox gives false positive
        let mut null_stats = CollisionSeverityStats::default();
        let bbox_result = evaluate_transform_loss(
            &candidate, &b_part, &cand_bbox, sheet, &layout, 1, &parts,
            &CollisionBackendKind::Bbox, LossModelKind::BboxArea, &default_cfg(), &mut null_stats,
        );
        assert!(bbox_result.loss > 0.0, "Bbox must report false-positive overlap for notch fixture");

        // Exact backend must give zero (part is in the notch)
        let mut stats = CollisionSeverityStats::default();
        let exact_result = evaluate_transform_loss(
            &candidate, &b_part, &cand_bbox, sheet, &layout, 1, &parts,
            &CollisionBackendKind::JaguaPolygonExact, LossModelKind::BboxArea, &default_cfg(), &mut stats,
        );
        assert!(!exact_result.unsupported, "must not be unsupported for valid geometry");
        assert_eq!(exact_result.loss, 0.0,
            "JaguaPolygonExact must give zero loss for item in notch (no collision): got {}", exact_result.loss);
        assert_eq!(exact_result.pair_collision_count, 0);
        assert!(stats.backend_confirmed_no_collisions > 0, "must record no-collision confirmations");
    }

    // -----------------------------------------------------------------------
    // Q21-T3: Exact backend, confirmed collision returns positive severity
    // -----------------------------------------------------------------------
    #[test]
    fn collision_severity_exact_backend_collision_returns_positive_severity() {
        let part_a = make_rect_part("A", 20.0, 20.0);
        let part_b = make_rect_part("B", 20.0, 20.0);
        let parts = vec![part_a.clone(), part_b.clone()];
        let sheets = make_sheets_100x100();

        // A at (0,0), B overlapping at (10, 10) → 10x10 overlap
        let layout = WorkingLayout::new(
            vec![
                make_placement("A__0001", "A", 0.0, 0.0),
                make_placement("B__0001", "B", 10.0, 10.0),
            ],
            vec![], 1, 0,
        );
        let sheet = &sheets[0];
        let candidate = make_placement("B__0001", "B", 10.0, 10.0);
        let cand_bbox = PlacedBbox { sheet_index: 0, x1: 10.0, y1: 10.0, x2: 30.0, y2: 30.0 };

        let mut stats = CollisionSeverityStats::default();
        let result = evaluate_transform_loss(
            &candidate, &part_b, &cand_bbox, sheet, &layout, 1, &parts,
            &CollisionBackendKind::JaguaPolygonExact, LossModelKind::BboxArea, &default_cfg(), &mut stats,
        );
        assert!(!result.unsupported);
        assert!(result.loss > 0.0, "confirmed collision must return positive severity, got {}", result.loss);
        assert_eq!(result.pair_collision_count, 1);
        assert!(stats.backend_confirmed_collisions > 0);
    }

    // -----------------------------------------------------------------------
    // Q21-T4: Shallow vs deep collision is monotonic
    // -----------------------------------------------------------------------
    #[test]
    fn collision_severity_shallow_vs_deep_collision_is_monotonic() {
        let part_a = make_rect_part("A", 20.0, 20.0);
        let part_b = make_rect_part("B", 20.0, 20.0);
        let parts = vec![part_a.clone(), part_b.clone()];
        let sheets = make_sheets_100x100();
        let sheet = &sheets[0];

        // Shallow: B at (19,0) → overlap with A[0,0,20,20] is 1mm in x
        let layout_shallow = WorkingLayout::new(
            vec![
                make_placement("A__0001", "A", 0.0, 0.0),
                make_placement("B__0001", "B", 19.0, 0.0),
            ],
            vec![], 1, 0,
        );
        let cand_shallow = make_placement("B__0001", "B", 19.0, 0.0);
        let bbox_shallow = PlacedBbox { sheet_index: 0, x1: 19.0, y1: 0.0, x2: 39.0, y2: 20.0 };

        let mut stats_s = CollisionSeverityStats::default();
        let sev_shallow = evaluate_transform_loss(
            &cand_shallow, &part_b, &bbox_shallow, sheet, &layout_shallow, 1, &parts,
            &CollisionBackendKind::JaguaPolygonExact, LossModelKind::BboxArea, &default_cfg(), &mut stats_s,
        );

        // Deep: B at (5,0) → overlap with A[0,0,20,20] is 15mm in x
        let layout_deep = WorkingLayout::new(
            vec![
                make_placement("A__0001", "A", 0.0, 0.0),
                make_placement("B__0001", "B", 5.0, 0.0),
            ],
            vec![], 1, 0,
        );
        let cand_deep = make_placement("B__0001", "B", 5.0, 0.0);
        let bbox_deep = PlacedBbox { sheet_index: 0, x1: 5.0, y1: 0.0, x2: 25.0, y2: 20.0 };

        let mut stats_d = CollisionSeverityStats::default();
        let sev_deep = evaluate_transform_loss(
            &cand_deep, &part_b, &bbox_deep, sheet, &layout_deep, 1, &parts,
            &CollisionBackendKind::JaguaPolygonExact, LossModelKind::BboxArea, &default_cfg(), &mut stats_d,
        );

        assert!(!sev_shallow.unsupported && !sev_deep.unsupported);
        assert!(sev_shallow.loss > 0.0, "shallow collision must have positive severity");
        assert!(sev_deep.loss > 0.0, "deep collision must have positive severity");
        assert!(
            sev_shallow.loss < sev_deep.loss,
            "shallow overlap severity ({}) must be less than deep overlap severity ({})",
            sev_shallow.loss, sev_deep.loss
        );
    }

    // -----------------------------------------------------------------------
    // Q21-T5: Boundary: valid placement gives zero severity
    // -----------------------------------------------------------------------
    #[test]
    fn collision_severity_boundary_valid_is_zero() {
        let part = make_rect_part("P", 20.0, 20.0);
        let parts = vec![part.clone()];
        let sheets = make_sheets_100x100();
        let sheet = &sheets[0];

        // Item at (0,0) → within 100x100 sheet → valid
        let layout = WorkingLayout::new(
            vec![make_placement("P__0001", "P", 0.0, 0.0)],
            vec![], 1, 0,
        );
        let candidate = make_placement("P__0001", "P", 0.0, 0.0);
        let cand_bbox = PlacedBbox { sheet_index: 0, x1: 0.0, y1: 0.0, x2: 20.0, y2: 20.0 };

        let mut stats = CollisionSeverityStats::default();
        let result = evaluate_transform_loss(
            &candidate, &part, &cand_bbox, sheet, &layout, 0, &parts,
            &CollisionBackendKind::JaguaPolygonExact, LossModelKind::BboxArea, &default_cfg(), &mut stats,
        );
        assert!(!result.unsupported);
        assert_eq!(result.loss, 0.0, "valid boundary must have zero loss, got {}", result.loss);
        assert!(!result.boundary_collision);
        assert!(stats.backend_confirmed_no_collisions > 0, "must record no-collision boundary confirmation");
    }

    // -----------------------------------------------------------------------
    // Q21-T6: Boundary: violation gives positive severity
    // -----------------------------------------------------------------------
    #[test]
    fn collision_severity_boundary_violation_positive() {
        let part = make_rect_part("P", 20.0, 20.0);
        let parts = vec![part.clone()];
        let sheets = make_sheets_100x100();
        let sheet = &sheets[0];

        // Item at (95, 95) → extends to (115, 115) → outside 100x100 sheet
        let layout = WorkingLayout::new(
            vec![make_placement("P__0001", "P", 95.0, 95.0)],
            vec![], 1, 0,
        );
        let candidate = make_placement("P__0001", "P", 95.0, 95.0);
        let cand_bbox = PlacedBbox { sheet_index: 0, x1: 95.0, y1: 95.0, x2: 115.0, y2: 115.0 };

        let mut stats = CollisionSeverityStats::default();
        let result = evaluate_transform_loss(
            &candidate, &part, &cand_bbox, sheet, &layout, 0, &parts,
            &CollisionBackendKind::JaguaPolygonExact, LossModelKind::BboxArea, &default_cfg(), &mut stats,
        );
        assert!(!result.unsupported);
        assert!(result.loss > 0.0, "boundary violation must have positive severity, got {}", result.loss);
        assert!(result.boundary_collision);
        assert!(stats.backend_confirmed_collisions > 0, "must record collision confirmation");
    }

    // -----------------------------------------------------------------------
    // Q21-T7: Unsupported geometry returns hard loss / reject
    // -----------------------------------------------------------------------
    #[test]
    fn collision_severity_unsupported_returns_hard_loss_or_reject() {
        // Part with invalid outer_points (2 points → degenerate polygon)
        let invalid_outer = serde_json::json!([[0.0, 0.0], [10.0, 0.0]]);
        let bad_part = Part {
            id: "P".to_string(), width: 20.0, height: 20.0, quantity: 1,
            allowed_rotations_deg: vec![0], holes_points: None, prepared_holes_points: None,
            outer_points: Some(invalid_outer), prepared_outer_points: None, rotation_policy: None,
        };
        let parts = vec![bad_part.clone()];
        let sheets = make_sheets_100x100();
        let sheet = &sheets[0];

        let layout = WorkingLayout::new(
            vec![make_placement("P__0001", "P", 0.0, 0.0)],
            vec![], 1, 0,
        );
        let candidate = make_placement("P__0001", "P", 0.0, 0.0);
        let cand_bbox = PlacedBbox { sheet_index: 0, x1: 0.0, y1: 0.0, x2: 20.0, y2: 20.0 };

        let mut stats = CollisionSeverityStats::default();
        let result = evaluate_transform_loss(
            &candidate, &bad_part, &cand_bbox, sheet, &layout, 0, &parts,
            &CollisionBackendKind::JaguaPolygonExact, LossModelKind::BboxArea, &default_cfg(), &mut stats,
        );
        assert!(result.loss == f64::MAX || result.unsupported,
            "unsupported geometry must return f64::MAX loss or unsupported=true");
        assert!(stats.unsupported_queries > 0, "must count unsupported queries");
    }
}
