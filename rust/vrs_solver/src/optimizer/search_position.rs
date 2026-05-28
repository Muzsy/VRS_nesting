/// SGH-Q20R: Sparrow-style search_position kernel.
///
/// Replaces the primary finite LBF/bbox candidate relocation path with:
///   1. Global uniform sheet grid sampling
///   2. Focused sampling around the current placement
///   3. Top-k coordinate descent on x, y and (Continuous only) rotation axes
///   4. Active backend evaluation — no silent bbox fallback for CDE/JaguaExact
use std::collections::HashSet;

use crate::geometry::Rect;
use crate::io::{CollisionBackendKind, Placement};
use crate::item::{
    effective_policy_kind, dims_for_rotation, placement_anchor_from_rect_min,
    resolve_instance_rotation_angles, Part,
};
use crate::rotation_policy::{RotationPolicyKind, RotationResolveContext};
use crate::sheet::SheetShape;
use super::boundary::rect_within_boundary;
use super::candidates::PlacedBbox;
use super::collision_backend::{CdeCollisionBackend, CollisionBackend, CollisionDecision, JaguaPolygonExactBackend};
use super::initializer::bbox_from_placement;
use super::loss_model::LossModelKind;
use super::working::WorkingLayout;

// ---------------------------------------------------------------------------
// DeterministicRng (same xorshift as separator.rs — local copy to avoid dep)
// ---------------------------------------------------------------------------

struct DeterministicRng {
    state: u64,
}

impl DeterministicRng {
    fn new(seed: u64) -> Self {
        let state = if seed == 0 { 0x9E37_79B9_7F4A_7C15 } else { seed };
        Self { state }
    }

    fn next_u64(&mut self) -> u64 {
        let mut x = self.state;
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        self.state = x;
        x.wrapping_mul(0x2545_F491_4F6C_DD1D)
    }

    fn next_f64(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 * (1.0 / (1u64 << 53) as f64)
    }

    fn next_f64_range(&mut self, lo: f64, hi: f64) -> f64 {
        lo + self.next_f64() * (hi - lo)
    }
}

// ---------------------------------------------------------------------------
// SearchPositionStats
// ---------------------------------------------------------------------------

/// Diagnostics accumulated across all search_position calls in a separator run.
#[derive(Debug, Clone)]
pub struct SearchPositionStats {
    pub calls: usize,
    pub global_samples_evaluated: usize,
    pub focused_samples_evaluated: usize,
    pub samples_unsupported: usize,
    pub refined_samples: usize,
    pub coord_descent_steps: usize,
    pub lbf_fallback_used: usize,
    /// Minimum evaluation loss seen (lower = better; f64::MAX = no calls).
    pub best_eval: f64,
}

impl Default for SearchPositionStats {
    fn default() -> Self {
        Self {
            calls: 0,
            global_samples_evaluated: 0,
            focused_samples_evaluated: 0,
            samples_unsupported: 0,
            refined_samples: 0,
            coord_descent_steps: 0,
            lbf_fallback_used: 0,
            best_eval: f64::MAX,
        }
    }
}

impl SearchPositionStats {
    pub fn accumulate(&mut self, other: &Self) {
        self.calls += other.calls;
        self.global_samples_evaluated += other.global_samples_evaluated;
        self.focused_samples_evaluated += other.focused_samples_evaluated;
        self.samples_unsupported += other.samples_unsupported;
        self.refined_samples += other.refined_samples;
        self.coord_descent_steps += other.coord_descent_steps;
        self.lbf_fallback_used += other.lbf_fallback_used;
        if other.best_eval < self.best_eval {
            self.best_eval = other.best_eval;
        }
    }
}

// ---------------------------------------------------------------------------
// SearchPositionConfig
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct SearchPositionConfig {
    /// Grid divisions per axis for global uniform sheet sampling. Total = n².
    pub global_grid_n: usize,
    /// Number of focused samples around the current bbox_min position.
    pub focused_sample_count: usize,
    /// Focused sampling radius = sheet_diagonal * this factor.
    pub focused_radius_factor: f64,
    /// Coordinate descent initial step = sheet_diagonal * this factor.
    pub coord_descent_initial_step_factor: f64,
    /// Stop halving the step below this threshold (mm).
    pub coord_descent_min_step: f64,
    /// Maximum total coordinate descent steps per call.
    pub coord_descent_max_steps: usize,
    /// Initial rotation step for coord descent (degrees, Continuous only).
    pub coord_descent_rotation_step_deg: f64,
    /// Number of top candidates (by eval) to refine with coordinate descent.
    pub coord_descent_top_k: usize,
}

impl Default for SearchPositionConfig {
    fn default() -> Self {
        Self {
            global_grid_n: 6,
            focused_sample_count: 8,
            focused_radius_factor: 0.3,
            coord_descent_initial_step_factor: 0.05,
            coord_descent_min_step: 0.01,
            coord_descent_max_steps: 15,
            coord_descent_rotation_step_deg: 5.0,
            coord_descent_top_k: 3,
        }
    }
}

// ---------------------------------------------------------------------------
// TransformCandidate
// ---------------------------------------------------------------------------

struct TransformCandidate {
    sheet_index: usize,
    rect_min_x: f64,
    rect_min_y: f64,
    rotation_deg: f64,
    eval: f64,
}

// ---------------------------------------------------------------------------
// Seed mixing
// ---------------------------------------------------------------------------

fn mix_seed(base: u64, instance_id: &str, call_index: usize) -> u64 {
    let inst_hash = instance_id.bytes().fold(0u64, |acc, b| {
        acc.wrapping_mul(0x9E37_79B9_7F4A_7C15).wrapping_add(b as u64)
    });
    base ^ inst_hash ^ (call_index as u64).wrapping_mul(0x517C_C1B7_2722_0A95)
}

// ---------------------------------------------------------------------------
// Backend-aware candidate evaluation
// ---------------------------------------------------------------------------

fn eval_with_backend_trait(
    backend: &dyn CollisionBackend,
    candidate: &Placement,
    part: &Part,
    cand_bbox: &PlacedBbox,
    sheet: &SheetShape,
    layout: &WorkingLayout,
    target_idx: usize,
    parts: &[Part],
    loss_model: LossModelKind,
    unsupported_count: &mut usize,
) -> f64 {
    let mut loss = match backend.placement_within_sheet(candidate, part, sheet) {
        CollisionDecision::NoCollision => 0.0,
        CollisionDecision::Collision => {
            loss_model.compute_boundary_loss(cand_bbox, sheet, false).max(1.0)
        }
        CollisionDecision::Unsupported { .. } => {
            *unsupported_count += 1;
            return f64::MAX;
        }
    };

    for (idx, other) in layout.placements.iter().enumerate() {
        if idx == target_idx || other.sheet_index != candidate.sheet_index {
            continue;
        }
        let Some(other_part) = parts.iter().find(|pt| pt.id == other.part_id) else {
            return f64::MAX;
        };
        match backend.placement_overlaps(candidate, part, other, other_part) {
            CollisionDecision::NoCollision => {}
            CollisionDecision::Collision => {
                if let Some(ob) = bbox_from_placement(other, other_part.width, other_part.height) {
                    loss += loss_model.pair_loss(&ob, cand_bbox).max(1.0);
                } else {
                    return f64::MAX;
                }
            }
            CollisionDecision::Unsupported { .. } => {
                *unsupported_count += 1;
                return f64::MAX;
            }
        }
    }
    loss
}

fn eval_candidate_loss(
    candidate: &Placement,
    part: &Part,
    cand_bbox: &PlacedBbox,
    sheet: &SheetShape,
    layout: &WorkingLayout,
    target_idx: usize,
    parts: &[Part],
    collision_backend: &CollisionBackendKind,
    loss_model: LossModelKind,
    unsupported_count: &mut usize,
) -> f64 {
    match collision_backend {
        CollisionBackendKind::Bbox => {
            let rect = Rect {
                x1: cand_bbox.x1, y1: cand_bbox.y1,
                x2: cand_bbox.x2, y2: cand_bbox.y2,
            };
            if !rect_within_boundary(rect, sheet) {
                return f64::MAX;
            }
            layout.placements.iter().enumerate()
                .filter(|(i, p)| *i != target_idx && p.sheet_index == candidate.sheet_index)
                .filter_map(|(_, p)| {
                    parts.iter().find(|pt| pt.id == p.part_id)
                        .and_then(|pt| bbox_from_placement(p, pt.width, pt.height))
                        .map(|pb| loss_model.pair_loss(&pb, cand_bbox))
                })
                .sum()
        }
        CollisionBackendKind::JaguaPolygonExact => {
            eval_with_backend_trait(
                &JaguaPolygonExactBackend,
                candidate, part, cand_bbox, sheet, layout, target_idx, parts, loss_model,
                unsupported_count,
            )
        }
        CollisionBackendKind::Cde => {
            eval_with_backend_trait(
                &CdeCollisionBackend,
                candidate, part, cand_bbox, sheet, layout, target_idx, parts, loss_model,
                unsupported_count,
            )
        }
    }
}

// ---------------------------------------------------------------------------
// Point evaluation helper
// ---------------------------------------------------------------------------

struct EvalResult {
    loss: f64,
    placement: Placement,
    unsupported: bool,
}

fn eval_at_point(
    rect_min_x: f64,
    rect_min_y: f64,
    rot: f64,
    sheet_idx: usize,
    instance_id: &str,
    part_id: &str,
    part: &Part,
    sheet: &SheetShape,
    layout: &WorkingLayout,
    target_idx: usize,
    parts: &[Part],
    collision_backend: &CollisionBackendKind,
    loss_model: LossModelKind,
) -> EvalResult {
    let (rw, rh) = dims_for_rotation(part.width, part.height, rot);
    let (ax, ay) = placement_anchor_from_rect_min(rect_min_x, rect_min_y, part.width, part.height, rot);
    let candidate = Placement {
        instance_id: instance_id.to_string(),
        part_id: part_id.to_string(),
        sheet_index: sheet_idx,
        x: ax,
        y: ay,
        rotation_deg: rot,
    };
    let cand_bbox = PlacedBbox {
        sheet_index: sheet_idx,
        x1: rect_min_x,
        y1: rect_min_y,
        x2: rect_min_x + rw,
        y2: rect_min_y + rh,
    };
    let mut unsup = 0usize;
    let loss = eval_candidate_loss(
        &candidate, part, &cand_bbox, sheet,
        layout, target_idx, parts, collision_backend, loss_model, &mut unsup,
    );
    EvalResult { loss, placement: candidate, unsupported: unsup > 0 }
}

// ---------------------------------------------------------------------------
// Coordinate descent
// ---------------------------------------------------------------------------

fn normalize_deg(deg: f64) -> f64 {
    let d = deg % 360.0;
    if d < 0.0 { d + 360.0 } else { d }
}

/// Step-halving coordinate descent from `(start_x, start_y, start_rot)` on a single sheet.
///
/// Axes: x ± step, y ± step, and (Continuous only) rotation ± rot_step.
/// Never mutates the incumbent until loss strictly improves.
fn coord_descent_from(
    start_x: f64,
    start_y: f64,
    start_rot: f64,
    start_loss: f64,
    sheet_idx: usize,
    instance_id: &str,
    part_id: &str,
    part: &Part,
    sheet: &SheetShape,
    layout: &WorkingLayout,
    target_idx: usize,
    parts: &[Part],
    collision_backend: &CollisionBackendKind,
    loss_model: LossModelKind,
    cfg: &SearchPositionConfig,
    is_continuous: bool,
    stats: &mut SearchPositionStats,
) -> (f64, f64, f64, f64) {
    let sheet_diag = (sheet.width * sheet.width + sheet.height * sheet.height).sqrt();
    let mut step = (cfg.coord_descent_initial_step_factor * sheet_diag).max(cfg.coord_descent_min_step);
    let mut rot_step = cfg.coord_descent_rotation_step_deg;

    let mut best_x = start_x;
    let mut best_y = start_y;
    let mut best_rot = start_rot;
    let mut best_loss = start_loss;
    let mut total_steps = 0usize;

    while step >= cfg.coord_descent_min_step && total_steps < cfg.coord_descent_max_steps {
        let mut improved = false;

        // x and y axes
        for &(dx, dy) in &[(step, 0.0_f64), (-step, 0.0), (0.0, step), (0.0, -step)] {
            let r = eval_at_point(
                best_x + dx, best_y + dy, best_rot, sheet_idx,
                instance_id, part_id, part, sheet, layout, target_idx, parts,
                collision_backend, loss_model,
            );
            total_steps += 1;
            stats.coord_descent_steps += 1;
            if r.loss < best_loss {
                best_x += dx;
                best_y += dy;
                best_loss = r.loss;
                improved = true;
                if best_loss == 0.0 {
                    return (best_x, best_y, best_rot, best_loss);
                }
            }
        }

        // Rotation axis (Continuous only)
        if is_continuous && rot_step >= 0.01 {
            for &dr in &[rot_step, -rot_step] {
                let nr = normalize_deg(best_rot + dr);
                let r = eval_at_point(
                    best_x, best_y, nr, sheet_idx,
                    instance_id, part_id, part, sheet, layout, target_idx, parts,
                    collision_backend, loss_model,
                );
                total_steps += 1;
                stats.coord_descent_steps += 1;
                if r.loss < best_loss {
                    best_rot = nr;
                    best_loss = r.loss;
                    improved = true;
                    if best_loss == 0.0 {
                        return (best_x, best_y, best_rot, best_loss);
                    }
                }
            }
        }

        if !improved {
            step /= 2.0;
            rot_step /= 2.0;
        }
    }

    (best_x, best_y, best_rot, best_loss)
}

// ---------------------------------------------------------------------------
// Main entry point
// ---------------------------------------------------------------------------

/// Find the best placement for `target_idx` using global/focused sampling + top-k coordinate descent.
///
/// Sampling phase: evaluates an n×n global grid and focused random samples; collects all finite
/// (non-Unsupported, loss < f64::MAX) candidates into a list.
///
/// Refinement phase: sorts candidates deterministically (eval ASC, then sheet/rotation/x/y),
/// takes top `cfg.coord_descent_top_k` and runs step-halving coordinate descent on each.
///
/// Returns the best placement found, or `None` if all samples were Unsupported or nothing fits.
pub fn search_position_for_target(
    layout: &WorkingLayout,
    target_idx: usize,
    parts: &[Part],
    sheets: &[SheetShape],
    allowed_sheet_filter: &Option<HashSet<usize>>,
    collision_backend: &CollisionBackendKind,
    loss_model: LossModelKind,
    rotation_context: &RotationResolveContext,
    cfg: &SearchPositionConfig,
    call_seed: u64,
    stats: &mut SearchPositionStats,
) -> Option<Placement> {
    stats.calls += 1;

    let current_p = &layout.placements[target_idx];
    let part = parts.iter().find(|p| p.id == current_p.part_id)?;

    let allowed_rotations = resolve_instance_rotation_angles(
        part,
        &current_p.instance_id,
        rotation_context,
    );
    if allowed_rotations.is_empty() {
        return None;
    }

    let policy = effective_policy_kind(part, rotation_context);
    let is_continuous = matches!(policy, RotationPolicyKind::Continuous);

    let instance_id = &current_p.instance_id;
    let part_id = &current_p.part_id;
    let seed = mix_seed(call_seed, instance_id, 0);

    let mut candidates: Vec<TransformCandidate> = Vec::new();

    for (sheet_idx, sheet) in sheets.iter().enumerate() {
        if let Some(filter) = allowed_sheet_filter {
            if !filter.contains(&sheet_idx) {
                continue;
            }
        }

        let n = cfg.global_grid_n.max(1);
        let step_x = sheet.width / (n as f64 + 1.0);
        let step_y = sheet.height / (n as f64 + 1.0);

        // Global grid
        let mut gy = sheet.min_y + step_y;
        for _yi in 0..n {
            let mut gx = sheet.min_x + step_x;
            for _xi in 0..n {
                for &rot in &allowed_rotations {
                    let r = eval_at_point(
                        gx, gy, rot, sheet_idx,
                        instance_id, part_id, part, sheet, layout, target_idx, parts,
                        collision_backend, loss_model,
                    );
                    stats.global_samples_evaluated += 1;
                    if r.unsupported {
                        stats.samples_unsupported += 1;
                        continue;
                    }
                    if r.loss < f64::MAX {
                        if r.loss == 0.0 {
                            if r.loss < stats.best_eval { stats.best_eval = r.loss; }
                            return Some(r.placement);
                        }
                        candidates.push(TransformCandidate {
                            sheet_index: sheet_idx,
                            rect_min_x: gx,
                            rect_min_y: gy,
                            rotation_deg: rot,
                            eval: r.loss,
                        });
                    }
                }
                gx += step_x;
            }
            gy += step_y;
        }

        // Focused samples around current placement on this sheet
        if current_p.sheet_index == sheet_idx {
            if let Some(cur_bbox) = bbox_from_placement(current_p, part.width, part.height) {
                let sheet_diag = (sheet.width * sheet.width + sheet.height * sheet.height).sqrt();
                let radius = cfg.focused_radius_factor * sheet_diag;
                let focused_seed = seed ^ ((sheet_idx as u64 + 1).wrapping_mul(0x1234_5678_90AB_CDEF));
                let mut rng = DeterministicRng::new(focused_seed);

                for _ in 0..cfg.focused_sample_count {
                    let fx = cur_bbox.x1 + rng.next_f64_range(-radius, radius);
                    let fy = cur_bbox.y1 + rng.next_f64_range(-radius, radius);
                    for &rot in &allowed_rotations {
                        let r = eval_at_point(
                            fx, fy, rot, sheet_idx,
                            instance_id, part_id, part, sheet, layout, target_idx, parts,
                            collision_backend, loss_model,
                        );
                        stats.focused_samples_evaluated += 1;
                        if r.unsupported {
                            stats.samples_unsupported += 1;
                            continue;
                        }
                        if r.loss < f64::MAX {
                            if r.loss == 0.0 {
                                if r.loss < stats.best_eval { stats.best_eval = r.loss; }
                                return Some(r.placement);
                            }
                            candidates.push(TransformCandidate {
                                sheet_index: sheet_idx,
                                rect_min_x: fx,
                                rect_min_y: fy,
                                rotation_deg: rot,
                                eval: r.loss,
                            });
                        }
                    }
                }
            }
        }
    }

    if candidates.is_empty() {
        return None;
    }

    // Sort deterministically: eval ASC, then sheet_index, rotation, x, y
    candidates.sort_by(|a, b| {
        a.eval.total_cmp(&b.eval)
            .then_with(|| a.sheet_index.cmp(&b.sheet_index))
            .then_with(|| a.rotation_deg.total_cmp(&b.rotation_deg))
            .then_with(|| a.rect_min_x.total_cmp(&b.rect_min_x))
            .then_with(|| a.rect_min_y.total_cmp(&b.rect_min_y))
    });

    // Refine top-k candidates with coordinate descent
    let top_k = cfg.coord_descent_top_k.min(candidates.len());
    let mut best_refined: Option<(f64, f64, f64, f64, usize)> = None; // (loss, x, y, rot, sheet)

    for cand in candidates.iter().take(top_k) {
        let sheet = &sheets[cand.sheet_index];
        stats.refined_samples += 1;
        let (cd_x, cd_y, cd_rot, cd_loss) = coord_descent_from(
            cand.rect_min_x, cand.rect_min_y, cand.rotation_deg, cand.eval,
            cand.sheet_index, instance_id, part_id,
            part, sheet, layout, target_idx, parts,
            collision_backend, loss_model,
            cfg, is_continuous, stats,
        );
        if best_refined.map_or(true, |(bl, ..)| cd_loss < bl) {
            best_refined = Some((cd_loss, cd_x, cd_y, cd_rot, cand.sheet_index));
            if cd_loss == 0.0 { break; }
        }
    }

    // If k=0 or no refined candidate beat the unrefined list, use best unrefined
    let (final_loss, final_x, final_y, final_rot, final_sheet) = match best_refined {
        Some((l, x, y, r, s)) => (l, x, y, r, s),
        None => {
            let c = &candidates[0]; // sorted, so [0] is best
            (c.eval, c.rect_min_x, c.rect_min_y, c.rotation_deg, c.sheet_index)
        }
    };

    if final_loss < stats.best_eval {
        stats.best_eval = final_loss;
    }

    let (ax, ay) = placement_anchor_from_rect_min(final_x, final_y, part.width, part.height, final_rot);
    Some(Placement {
        instance_id: instance_id.clone(),
        part_id: part_id.clone(),
        sheet_index: final_sheet,
        x: ax,
        y: ay,
        rotation_deg: final_rot,
    })
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
pub(crate) mod tests {
    use super::*;
    use crate::item::Part;
    use crate::optimizer::cde_observability;
    use crate::rotation_policy::RotationPolicyKind;
    use crate::sheet::{expand_sheets, Stock};

    pub fn make_rect_part(id: &str, w: f64, h: f64, qty: i64, rots: Vec<i64>) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: qty,
            allowed_rotations_deg: rots,
            holes_points: None,
            prepared_holes_points: None,
            outer_points: None,
            prepared_outer_points: None,
            rotation_policy: None,
        }
    }

    pub fn make_continuous_part(id: &str, w: f64, h: f64, qty: i64) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: qty,
            allowed_rotations_deg: vec![],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: None,
            prepared_outer_points: None,
            rotation_policy: Some(RotationPolicyKind::Continuous),
        }
    }

    pub fn make_test_sheets(w: f64, h: f64) -> Vec<SheetShape> {
        expand_sheets(&[Stock {
            id: "S".into(),
            quantity: 1,
            width: Some(w),
            height: Some(h),
            outer_points: None,
            holes_points: None,
            cost_per_use: None,
        }]).expect("expand_sheets")
    }

    fn default_ctx() -> RotationResolveContext {
        RotationResolveContext::new(None, 0, 16)
    }

    fn continuous_ctx() -> RotationResolveContext {
        RotationResolveContext::new(Some(RotationPolicyKind::Continuous), 0, 16)
    }

    // Q20R-T1: same seed → same global sampling result
    #[test]
    fn search_position_global_sampling_is_deterministic() {
        let parts = vec![make_rect_part("P", 20.0, 10.0, 1, vec![0])];
        let sheets = make_test_sheets(200.0, 200.0);
        let layout = WorkingLayout::new(
            vec![Placement {
                instance_id: "P__0001".into(), part_id: "P".into(),
                sheet_index: 0, x: 5.0, y: 5.0, rotation_deg: 0.0,
            }],
            vec![], 1, 0,
        );
        let cfg = SearchPositionConfig::default();
        let ctx = default_ctx();
        let mut s1 = SearchPositionStats::default();
        let mut s2 = SearchPositionStats::default();
        let p1 = search_position_for_target(
            &layout, 0, &parts, &sheets, &None,
            &CollisionBackendKind::Bbox, LossModelKind::BboxArea, &ctx, &cfg, 42, &mut s1,
        );
        let p2 = search_position_for_target(
            &layout, 0, &parts, &sheets, &None,
            &CollisionBackendKind::Bbox, LossModelKind::BboxArea, &ctx, &cfg, 42, &mut s2,
        );
        assert!(p1.is_some() && p2.is_some(), "must find candidate");
        let p1 = p1.unwrap();
        let p2 = p2.unwrap();
        assert!((p1.x - p2.x).abs() < 1e-12, "x must be identical: {} vs {}", p1.x, p2.x);
        assert!((p1.y - p2.y).abs() < 1e-12, "y must be identical: {} vs {}", p1.y, p2.y);
        assert!((p1.rotation_deg - p2.rotation_deg).abs() < 1e-12);
        assert_eq!(s1.global_samples_evaluated, s2.global_samples_evaluated);
    }

    // Q20R-T2: focused sampling is seed-deterministic
    #[test]
    fn search_position_focused_sampling_is_deterministic() {
        let parts = vec![make_rect_part("P", 20.0, 10.0, 1, vec![0])];
        let sheets = make_test_sheets(200.0, 200.0);
        let layout = WorkingLayout::new(
            vec![Placement {
                instance_id: "P__0001".into(), part_id: "P".into(),
                sheet_index: 0, x: 80.0, y: 80.0, rotation_deg: 0.0,
            }],
            vec![], 1, 0,
        );
        let cfg = SearchPositionConfig { focused_sample_count: 12, ..Default::default() };
        let ctx = default_ctx();
        let mut s1 = SearchPositionStats::default();
        let mut s2 = SearchPositionStats::default();
        let r1 = search_position_for_target(
            &layout, 0, &parts, &sheets, &None,
            &CollisionBackendKind::Bbox, LossModelKind::BboxArea, &ctx, &cfg, 99, &mut s1,
        );
        let r2 = search_position_for_target(
            &layout, 0, &parts, &sheets, &None,
            &CollisionBackendKind::Bbox, LossModelKind::BboxArea, &ctx, &cfg, 99, &mut s2,
        );
        assert!(r1.is_some() && r2.is_some());
        let r1 = r1.unwrap(); let r2 = r2.unwrap();
        assert!((r1.x - r2.x).abs() < 1e-12, "focused sampling must be seed-deterministic");
        assert!((r1.y - r2.y).abs() < 1e-12);
        assert_eq!(s1.focused_samples_evaluated, s2.focused_samples_evaluated);
    }

    // Q20R-T3: non-Continuous policies never produce illegal angles
    #[test]
    fn search_position_respects_non_continuous_rotation_policy() {
        let parts = vec![make_rect_part("P", 30.0, 15.0, 1, vec![0, 90])];
        let sheets = make_test_sheets(200.0, 200.0);
        let layout = WorkingLayout::new(
            vec![Placement {
                instance_id: "P__0001".into(), part_id: "P".into(),
                sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0,
            }],
            vec![], 1, 0,
        );
        let cfg = SearchPositionConfig::default();
        let ctx = RotationResolveContext::new(None, 0, 16);
        let mut stats = SearchPositionStats::default();
        let result = search_position_for_target(
            &layout, 0, &parts, &sheets, &None,
            &CollisionBackendKind::Bbox, LossModelKind::BboxArea, &ctx, &cfg, 0, &mut stats,
        );
        assert!(result.is_some(), "must find a placement");
        let rot = result.unwrap().rotation_deg;
        // Orthogonal part: only 0° or 90° are valid
        assert!(
            (rot - 0.0).abs() < 1e-9 || (rot - 90.0).abs() < 1e-9,
            "non-Continuous part must only get 0° or 90°, got {rot}"
        );
    }

    // Q20R-T4: Continuous policy produces non-orthogonal angle candidates
    #[test]
    fn search_position_uses_q20_continuous_candidates() {
        let parts = vec![make_continuous_part("P", 30.0, 15.0, 1)];
        let sheets = make_test_sheets(200.0, 200.0);
        // Place a second part to create something to avoid (drives toward non-trivial rotation)
        let layout = WorkingLayout::new(
            vec![Placement {
                instance_id: "P__0001".into(), part_id: "P".into(),
                sheet_index: 0, x: 100.0, y: 100.0, rotation_deg: 45.0,
            }],
            vec![], 1, 0,
        );
        let ctx = continuous_ctx();
        let resolved = crate::item::resolve_instance_rotation_angles(
            &parts[0], "P__0001", &ctx,
        );
        // With linspace n=16: must include 22.5°, 45°, 67.5° etc.
        let has_non_canonical = resolved.iter().any(|&r| {
            [0.0, 90.0, 180.0, 270.0].iter().all(|&c| (r - c).abs() > 1.0)
        });
        assert!(has_non_canonical, "Continuous policy must produce non-orthogonal candidates");
        // The search must also evaluate those candidates
        let cfg = SearchPositionConfig::default();
        let mut stats = SearchPositionStats::default();
        let result = search_position_for_target(
            &layout, 0, &parts, &sheets, &None,
            &CollisionBackendKind::Bbox, LossModelKind::BboxArea, &ctx, &cfg, 0, &mut stats,
        );
        assert!(result.is_some(), "Continuous must find a candidate");
        assert!(stats.global_samples_evaluated > 0, "must have evaluated global samples");
    }

    // Q20R-T5: Continuous coord descent steps include rotation axis.
    // A full-sheet blocker ensures ALL grid samples overlap it → best_loss > 0 →
    // coord_descent_from is called → rotation axis steps are attempted.
    #[test]
    fn search_position_continuous_uses_rotation_axis_in_coord_descent() {
        // BLK covers the entire sheet so P always overlaps it at any grid point.
        let parts = vec![
            make_continuous_part("P", 10.0, 5.0, 1),
            make_rect_part("BLK", 200.0, 200.0, 1, vec![0]),
        ];
        let sheets = make_test_sheets(200.0, 200.0);
        let layout = WorkingLayout::new(
            vec![
                Placement {
                    instance_id: "P__0001".into(), part_id: "P".into(),
                    sheet_index: 0, x: 90.0, y: 90.0, rotation_deg: 0.0,
                },
                Placement {
                    instance_id: "BLK__0001".into(), part_id: "BLK".into(),
                    sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0,
                },
            ],
            vec![], 1, 0,
        );
        let cfg = SearchPositionConfig {
            global_grid_n: 4,
            focused_sample_count: 0,
            coord_descent_max_steps: 20,
            coord_descent_rotation_step_deg: 5.0,
            coord_descent_min_step: 0.5,
            ..Default::default()
        };
        let ctx = continuous_ctx();
        let mut stats = SearchPositionStats::default();
        search_position_for_target(
            &layout, 0, &parts, &sheets, &None,
            &CollisionBackendKind::Bbox, LossModelKind::BboxArea, &ctx, &cfg, 0, &mut stats,
        );
        assert!(
            stats.refined_samples > 0,
            "Continuous: coord_descent_from must be called when best_loss > 0 (refined={})",
            stats.refined_samples
        );
        assert!(
            stats.coord_descent_steps > 0,
            "Continuous coord descent must produce steps (got {})",
            stats.coord_descent_steps
        );
    }

    // Q20R-T6: samples that return Unsupported are counted and rejected.
    // JaguaPolygonExact returns Unsupported when outer_points is present but malformed
    // (< 3 distinct points → "polygon became degenerate after deduplication").
    #[test]
    fn search_position_rejects_backend_unsupported_samples() {
        // Part with a 2-point outer_points polygon: invalid → JaguaPolygonExact returns Unsupported.
        let invalid_outer = serde_json::json!([[0.0, 0.0], [10.0, 0.0]]);
        let parts = vec![Part {
            id: "P".into(),
            width: 20.0,
            height: 10.0,
            quantity: 1,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: Some(invalid_outer),
            prepared_outer_points: None,
            rotation_policy: None,
        }];
        let sheets = make_test_sheets(200.0, 200.0);
        let layout = WorkingLayout::new(
            vec![Placement {
                instance_id: "P__0001".into(), part_id: "P".into(),
                sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0,
            }],
            vec![], 1, 0,
        );
        let cfg = SearchPositionConfig {
            global_grid_n: 3,
            focused_sample_count: 0,
            coord_descent_max_steps: 0,
            coord_descent_top_k: 0,
            ..Default::default()
        };
        let ctx = default_ctx();
        let mut stats = SearchPositionStats::default();
        search_position_for_target(
            &layout, 0, &parts, &sheets, &None,
            &CollisionBackendKind::JaguaPolygonExact, LossModelKind::BboxArea, &ctx, &cfg, 0, &mut stats,
        );
        assert!(
            stats.samples_unsupported > 0,
            "must count unsupported samples for invalid outer_points (got {})",
            stats.samples_unsupported
        );
    }

    // Q20R-T7 (regression): CDE backend does not trigger bbox fallback (pair+boundary == total)
    #[test]
    fn search_position_existing_cde_no_bbox_fallback_still_passes() {
        let parts = vec![make_continuous_part("P", 20.0, 10.0, 2)];
        let sheets = make_test_sheets(200.0, 200.0);
        let layout = WorkingLayout::new(
            vec![
                Placement { instance_id: "P__0001".into(), part_id: "P".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 },
                Placement { instance_id: "P__0002".into(), part_id: "P".into(), sheet_index: 0, x: 20.0, y: 0.0, rotation_deg: 0.0 },
            ],
            vec![], 1, 0,
        );
        let cfg = SearchPositionConfig { global_grid_n: 3, focused_sample_count: 4, coord_descent_max_steps: 5, ..Default::default() };
        let ctx = continuous_ctx();

        cde_observability::reset();
        let mut stats = SearchPositionStats::default();
        search_position_for_target(
            &layout, 0, &parts, &sheets, &None,
            &CollisionBackendKind::Cde, LossModelKind::BboxArea, &ctx, &cfg, 0, &mut stats,
        );
        let snap = cde_observability::snapshot();
        // CDE counter structural invariant: pair+boundary == total (no bbox leak)
        assert_eq!(
            snap.pair_queries + snap.boundary_queries, snap.total_queries,
            "CDE total must equal pair+boundary (no bbox fallback leak)"
        );
    }

    // Q20R-R1-T1: refines exactly top-k candidates when all have nonzero loss.
    // A full-sheet BLK blocker guarantees every grid position overlaps it, so
    // no zero-loss early-return fires and coord_descent_from is called for each
    // of the top-k candidates. refined_samples must equal coord_descent_top_k.
    #[test]
    fn search_position_refines_top_k_candidates_when_configured() {
        let k = 3usize;
        let parts = vec![
            make_rect_part("P", 10.0, 5.0, 1, vec![0]),
            make_rect_part("BLK", 200.0, 200.0, 1, vec![0]),
        ];
        let sheets = make_test_sheets(200.0, 200.0);
        let layout = WorkingLayout::new(
            vec![
                Placement { instance_id: "P__0001".into(), part_id: "P".into(), sheet_index: 0, x: 90.0, y: 90.0, rotation_deg: 0.0 },
                Placement { instance_id: "BLK__0001".into(), part_id: "BLK".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 },
            ],
            vec![], 1, 0,
        );
        let cfg = SearchPositionConfig {
            global_grid_n: 4,
            focused_sample_count: 0,
            coord_descent_top_k: k,
            coord_descent_max_steps: 5,
            coord_descent_min_step: 0.5,
            ..Default::default()
        };
        let ctx = default_ctx();
        let mut stats = SearchPositionStats::default();
        search_position_for_target(
            &layout, 0, &parts, &sheets, &None,
            &CollisionBackendKind::Bbox, LossModelKind::BboxArea, &ctx, &cfg, 0, &mut stats,
        );
        assert_eq!(
            stats.refined_samples, k,
            "refined_samples must equal coord_descent_top_k={k} (got {})",
            stats.refined_samples
        );
        assert!(stats.coord_descent_steps > 0, "coord_descent_steps must be > 0");
    }

    // Q20R-R1-T2: same seed always selects the same top-k candidates (sort is deterministic).
    #[test]
    fn search_position_top_k_tie_break_is_deterministic() {
        let parts = vec![
            make_rect_part("P", 10.0, 5.0, 1, vec![0]),
            make_rect_part("BLK", 200.0, 200.0, 1, vec![0]),
        ];
        let sheets = make_test_sheets(200.0, 200.0);
        let layout = WorkingLayout::new(
            vec![
                Placement { instance_id: "P__0001".into(), part_id: "P".into(), sheet_index: 0, x: 90.0, y: 90.0, rotation_deg: 0.0 },
                Placement { instance_id: "BLK__0001".into(), part_id: "BLK".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 },
            ],
            vec![], 1, 0,
        );
        let cfg = SearchPositionConfig {
            global_grid_n: 4,
            focused_sample_count: 0,
            coord_descent_top_k: 3,
            coord_descent_max_steps: 5,
            ..Default::default()
        };
        let ctx = default_ctx();
        let mut s1 = SearchPositionStats::default();
        let mut s2 = SearchPositionStats::default();
        let r1 = search_position_for_target(
            &layout, 0, &parts, &sheets, &None,
            &CollisionBackendKind::Bbox, LossModelKind::BboxArea, &ctx, &cfg, 77, &mut s1,
        );
        let r2 = search_position_for_target(
            &layout, 0, &parts, &sheets, &None,
            &CollisionBackendKind::Bbox, LossModelKind::BboxArea, &ctx, &cfg, 77, &mut s2,
        );
        assert!(r1.is_some() && r2.is_some(), "both runs must find a candidate");
        let r1 = r1.unwrap(); let r2 = r2.unwrap();
        assert!((r1.x - r2.x).abs() < 1e-12, "top-k tie-break must be deterministic: x {} vs {}", r1.x, r2.x);
        assert!((r1.y - r2.y).abs() < 1e-12, "top-k tie-break must be deterministic: y {} vs {}", r1.y, r2.y);
        assert_eq!(s1.refined_samples, s2.refined_samples, "refined_samples must be identical");
        assert_eq!(s1.coord_descent_steps, s2.coord_descent_steps, "coord_descent_steps must be identical");
    }

    // Q20R-R1-T3: setting coord_descent_top_k=0 disables refinement (refined_samples == 0).
    #[test]
    fn search_position_refine_top_k_zero_disables_refinement_or_is_rejected_by_config_validation() {
        let parts = vec![
            make_rect_part("P", 10.0, 5.0, 1, vec![0]),
            make_rect_part("BLK", 200.0, 200.0, 1, vec![0]),
        ];
        let sheets = make_test_sheets(200.0, 200.0);
        let layout = WorkingLayout::new(
            vec![
                Placement { instance_id: "P__0001".into(), part_id: "P".into(), sheet_index: 0, x: 90.0, y: 90.0, rotation_deg: 0.0 },
                Placement { instance_id: "BLK__0001".into(), part_id: "BLK".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 },
            ],
            vec![], 1, 0,
        );
        let cfg = SearchPositionConfig {
            global_grid_n: 4,
            focused_sample_count: 0,
            coord_descent_top_k: 0,
            coord_descent_max_steps: 10,
            ..Default::default()
        };
        let ctx = default_ctx();
        let mut stats = SearchPositionStats::default();
        let result = search_position_for_target(
            &layout, 0, &parts, &sheets, &None,
            &CollisionBackendKind::Bbox, LossModelKind::BboxArea, &ctx, &cfg, 0, &mut stats,
        );
        assert!(result.is_some(), "k=0 must still return best unrefined candidate");
        assert_eq!(stats.refined_samples, 0, "k=0 must produce refined_samples=0 (got {})", stats.refined_samples);
        assert_eq!(stats.coord_descent_steps, 0, "k=0 must produce coord_descent_steps=0 (got {})", stats.coord_descent_steps);
    }

    // Q20R-R1-T4: diagnostic refined_samples exactly equals top_k when fixture forces nonzero loss.
    #[test]
    fn search_position_reported_refined_samples_matches_top_k_for_nonzero_loss_fixture() {
        // Use k=2 with full-sheet blocker to guarantee nonzero loss on all grid points.
        let k = 2usize;
        let parts = vec![
            make_rect_part("P", 10.0, 5.0, 1, vec![0]),
            make_rect_part("BLK", 200.0, 200.0, 1, vec![0]),
        ];
        let sheets = make_test_sheets(200.0, 200.0);
        let layout = WorkingLayout::new(
            vec![
                Placement { instance_id: "P__0001".into(), part_id: "P".into(), sheet_index: 0, x: 90.0, y: 90.0, rotation_deg: 0.0 },
                Placement { instance_id: "BLK__0001".into(), part_id: "BLK".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 },
            ],
            vec![], 1, 0,
        );
        let cfg = SearchPositionConfig {
            global_grid_n: 4,
            focused_sample_count: 0,
            coord_descent_top_k: k,
            coord_descent_max_steps: 3,
            ..Default::default()
        };
        let ctx = default_ctx();
        let mut stats = SearchPositionStats::default();
        search_position_for_target(
            &layout, 0, &parts, &sheets, &None,
            &CollisionBackendKind::Bbox, LossModelKind::BboxArea, &ctx, &cfg, 0, &mut stats,
        );
        assert_eq!(
            stats.refined_samples, k,
            "refined_samples must equal coord_descent_top_k={k} for nonzero-loss fixture (got {})",
            stats.refined_samples
        );
    }
}
