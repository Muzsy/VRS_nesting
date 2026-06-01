use std::collections::HashSet;

use super::boundary::rect_within_boundary;
use super::candidates::{generate_candidates_with_sheets, PlacedBbox};
use super::collision_backend::{
    BackendValidationDiagnostics, CdeCollisionBackend, CollisionBackend, CollisionDecision,
    JaguaPolygonExactBackend,
};
use super::initializer::bbox_from_placement;
use super::stopping::StoppingPolicy;
use crate::geometry::Rect;
use crate::io::{CollisionBackendKind, Placement, Unplaced};
use crate::item::{
    dims_for_rotation, placement_anchor_from_rect_min, resolve_instance_rotation_angles, Part,
};
use crate::rotation_policy::RotationResolveContext;
use crate::sheet::SheetShape;

/// Violation type detected during repair audit.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ViolationType {
    /// Bbox of this placement overlaps a previously validated bbox on the same sheet.
    Overlap,
    /// Placement is out of its sheet boundary or has an invalid sheet_index.
    BoundaryOrSheet,
}

/// Diagnostics for a single repair pass.
#[derive(Debug, Default, Clone)]
pub struct RepairDiagnostics {
    /// Number of overlap violations detected in the input layout.
    pub overlap_detected: usize,
    /// Number of boundary/sheet violations detected in the input layout.
    pub boundary_detected: usize,
    /// Total reinsert attempts (one per repaired/unplaced item tried).
    pub attempts: usize,
    /// Items successfully reinserted to a valid position.
    pub successes: usize,
    /// Items that could not be reinserted (reason: REPAIR_FAILED).
    pub failures: usize,
    /// Items skipped because stopping policy triggered.
    pub stopped_by_policy: usize,
    /// Human-readable stop reason string.
    pub stop_reason: String,
}

impl RepairDiagnostics {
    pub fn summary(&self) -> String {
        format!(
            "overlap={} boundary={} attempts={} ok={} fail={} stopped={} reason={}",
            self.overlap_detected,
            self.boundary_detected,
            self.attempts,
            self.successes,
            self.failures,
            self.stopped_by_policy,
            self.stop_reason,
        )
    }
}

/// Scan the placement list and identify invalid entries.
///
/// Violations are detected sequentially:
///  - boundary: out-of-bounds sheet_index or bbox outside sheet shape.
///  - overlap: bbox overlaps any *earlier* valid (non-violated) bbox on the same sheet.
///
/// Returns list of `(placement_index, ViolationType)` for all violations found.
pub fn find_violations(
    placements: &[Placement],
    parts: &[Part],
    sheets: &[SheetShape],
) -> Vec<(usize, ViolationType)> {
    let mut valid_bboxes: Vec<PlacedBbox> = Vec::with_capacity(placements.len());
    let mut violations: Vec<(usize, ViolationType)> = Vec::new();

    for (idx, p) in placements.iter().enumerate() {
        // Resolve part dimensions.
        let part = parts.iter().find(|pt| pt.id == p.part_id);
        let (pw, ph) = match part {
            Some(pt) => (pt.width, pt.height),
            None => {
                violations.push((idx, ViolationType::BoundaryOrSheet));
                continue;
            }
        };

        // Recover bbox from placement.
        let bbox = match bbox_from_placement(p, pw, ph) {
            Some(b) => b,
            None => {
                violations.push((idx, ViolationType::BoundaryOrSheet));
                continue;
            }
        };

        // Sheet index and boundary check.
        if p.sheet_index >= sheets.len() {
            violations.push((idx, ViolationType::BoundaryOrSheet));
            // Do not add to valid_bboxes — this is invalid.
            continue;
        }
        let sheet = &sheets[p.sheet_index];
        let rect = Rect {
            x1: bbox.x1,
            y1: bbox.y1,
            x2: bbox.x2,
            y2: bbox.y2,
        };
        if !rect_within_boundary(rect, sheet) {
            violations.push((idx, ViolationType::BoundaryOrSheet));
            continue;
        }

        // Overlap check against all earlier valid bboxes.
        if valid_bboxes.iter().any(|pb| pb.overlaps(&bbox)) {
            violations.push((idx, ViolationType::Overlap));
            // Do not add overlapping item to valid_bboxes so it doesn't pollute
            // subsequent overlap checks.
            continue;
        }

        valid_bboxes.push(bbox);
    }

    violations
}

/// Backend-aware violation scan. Semantics match `find_violations` when `backend`
/// is `BboxCollisionBackend`.
///
/// If the backend returns `Unsupported` for boundary or overlap queries, the
/// function falls back to bbox-based checks transparently (conservative path).
pub fn find_violations_with_backend(
    placements: &[Placement],
    parts: &[Part],
    sheets: &[SheetShape],
    backend: &dyn CollisionBackend,
) -> Vec<(usize, ViolationType)> {
    let mut valid_indices: Vec<usize> = Vec::with_capacity(placements.len());
    let mut violations: Vec<(usize, ViolationType)> = Vec::new();

    for (idx, p) in placements.iter().enumerate() {
        let part = match parts.iter().find(|pt| pt.id == p.part_id) {
            Some(pt) => pt,
            None => {
                violations.push((idx, ViolationType::BoundaryOrSheet));
                continue;
            }
        };

        if p.sheet_index >= sheets.len() {
            violations.push((idx, ViolationType::BoundaryOrSheet));
            continue;
        }
        let sheet = &sheets[p.sheet_index];

        // Boundary check via backend; fall back to bbox on Unsupported.
        let boundary_violated = match backend.placement_within_sheet(p, part, sheet) {
            CollisionDecision::Collision => true,
            CollisionDecision::NoCollision => false,
            CollisionDecision::Unsupported { .. } => {
                match bbox_from_placement(p, part.width, part.height) {
                    Some(bbox) => {
                        let rect = Rect {
                            x1: bbox.x1,
                            y1: bbox.y1,
                            x2: bbox.x2,
                            y2: bbox.y2,
                        };
                        !rect_within_boundary(rect, sheet)
                    }
                    None => true,
                }
            }
        };
        if boundary_violated {
            violations.push((idx, ViolationType::BoundaryOrSheet));
            continue;
        }

        // Overlap check against all previously validated placements.
        let mut has_overlap = false;
        'outer: for &vi in &valid_indices {
            let vp = &placements[vi];
            if vp.sheet_index != p.sheet_index {
                continue;
            }
            let vpart = match parts.iter().find(|pt| pt.id == vp.part_id) {
                Some(pt) => pt,
                None => continue,
            };
            let decision = backend.placement_overlaps(vp, vpart, p, part);
            match decision {
                CollisionDecision::Collision => {
                    has_overlap = true;
                    break 'outer;
                }
                CollisionDecision::NoCollision => {}
                CollisionDecision::Unsupported { .. } => {
                    // Fall back to bbox overlap check.
                    if let (Some(ba), Some(bb)) = (
                        bbox_from_placement(vp, vpart.width, vpart.height),
                        bbox_from_placement(p, part.width, part.height),
                    ) {
                        if ba.overlaps(&bb) {
                            has_overlap = true;
                            break 'outer;
                        }
                    }
                }
            }
        }

        if has_overlap {
            violations.push((idx, ViolationType::Overlap));
        } else {
            valid_indices.push(idx);
        }
    }

    violations
}

/// Result from a backend-checked validation pass (no silent fallback).
pub struct BackendValidationResult {
    pub violations: Vec<(usize, ViolationType)>,
    pub diagnostics: BackendValidationDiagnostics,
}

/// Backend-aware violation scan without silent fallback.
///
/// Unlike `find_violations_with_backend`, this function does NOT fall back to bbox when the
/// backend returns Unsupported. Unsupported queries are counted in `diagnostics.unsupported_queries`.
/// Callers decide whether unsupported_queries > 0 blocks acceptance.
pub fn validate_placements_with_backend_checked(
    placements: &[Placement],
    parts: &[Part],
    sheets: &[SheetShape],
    backend: &dyn CollisionBackend,
) -> BackendValidationResult {
    let mut valid_indices: Vec<usize> = Vec::with_capacity(placements.len());
    let mut violations: Vec<(usize, ViolationType)> = Vec::new();
    let mut unsupported_queries: usize = 0;

    for (idx, p) in placements.iter().enumerate() {
        let part = match parts.iter().find(|pt| pt.id == p.part_id) {
            Some(pt) => pt,
            None => {
                violations.push((idx, ViolationType::BoundaryOrSheet));
                continue;
            }
        };

        if p.sheet_index >= sheets.len() {
            violations.push((idx, ViolationType::BoundaryOrSheet));
            continue;
        }
        let sheet = &sheets[p.sheet_index];

        // Boundary check — no silent fallback on Unsupported.
        match backend.placement_within_sheet(p, part, sheet) {
            CollisionDecision::Collision => {
                violations.push((idx, ViolationType::BoundaryOrSheet));
                continue;
            }
            CollisionDecision::NoCollision => {}
            CollisionDecision::Unsupported { .. } => {
                unsupported_queries += 1;
                // Do not treat as violation; caller enforces policy via unsupported_queries count.
            }
        }

        // Overlap check — no silent fallback on Unsupported.
        let mut has_overlap = false;
        'outer: for &vi in &valid_indices {
            let vp = &placements[vi];
            if vp.sheet_index != p.sheet_index {
                continue;
            }
            let vpart = match parts.iter().find(|pt| pt.id == vp.part_id) {
                Some(pt) => pt,
                None => continue,
            };
            match backend.placement_overlaps(vp, vpart, p, part) {
                CollisionDecision::Collision => {
                    has_overlap = true;
                    break 'outer;
                }
                CollisionDecision::NoCollision => {}
                CollisionDecision::Unsupported { .. } => {
                    unsupported_queries += 1;
                }
            }
        }

        if has_overlap {
            violations.push((idx, ViolationType::Overlap));
        } else {
            valid_indices.push(idx);
        }
    }

    BackendValidationResult {
        violations,
        diagnostics: BackendValidationDiagnostics {
            backend_name: backend.name().to_string(),
            unsupported_queries,
            bbox_fallback_queries: 0, // no fallbacks in checked path
        },
    }
}

/// Central backend-aware validation helper for internal search commit gates.
///
/// Routes based on `backend_kind`:
/// - Bbox: identical to `find_violations` (backward-compatible, no behavior change).
/// - JaguaPolygonExact / Cde: uses `validate_placements_with_backend_checked`.
///   If `unsupported_queries > 0`, a sentinel violation is appended so that callers
///   checking `violations.is_empty()` reject the candidate — no silent bbox fallback.
pub fn validate_placements_for_backend(
    placements: &[Placement],
    parts: &[Part],
    sheets: &[SheetShape],
    backend_kind: &CollisionBackendKind,
) -> Vec<(usize, ViolationType)> {
    match backend_kind {
        CollisionBackendKind::Bbox => find_violations(placements, parts, sheets),
        CollisionBackendKind::JaguaPolygonExact => {
            let result = validate_placements_with_backend_checked(
                placements,
                parts,
                sheets,
                &JaguaPolygonExactBackend,
            );
            if result.diagnostics.unsupported_queries > 0 {
                let mut v = result.violations;
                v.push((usize::MAX, ViolationType::BoundaryOrSheet));
                v
            } else {
                result.violations
            }
        }
        CollisionBackendKind::Cde => {
            let result = validate_placements_with_backend_checked(
                placements,
                parts,
                sheets,
                &CdeCollisionBackend,
            );
            if result.diagnostics.unsupported_queries > 0 {
                let mut v = result.violations;
                v.push((usize::MAX, ViolationType::BoundaryOrSheet));
                v
            } else {
                result.violations
            }
        }
    }
}

/// Internal record for an item queued for repair reinsertion.
struct RepairItem {
    instance_id: String,
    part_id: String,
    width: f64,
    height: f64,
    allowed_rotations: Vec<f64>,
}

/// Run one repair pass on the given layout.
///
/// Algorithm:
/// 1. Identify overlap and boundary violations via `find_violations`.
/// 2. Remove invalid placements → repair queue.
/// 3. Add previously-unplaced items (except PART_NEVER_FITS_STOCK) → repair queue.
/// 4. Sort repair queue: area desc → instance_id asc (deterministic, no RNG).
/// 5. For each item in the queue: try to reinsert via candidate-point generation
///    (same logic as `build_initial_layout`: sheet-origin + placed-bbox corners,
///    sorted by sheet_index → y → x, all allowed rotations tried per candidate).
///
/// Invariant: `placed.len() + unplaced.len() == input_placed.len() + input_unplaced.len()`.
pub fn run_repair(
    placements: Vec<Placement>,
    unplaced: Vec<Unplaced>,
    parts: &[Part],
    sheets: &[SheetShape],
    policy: &mut StoppingPolicy,
) -> (Vec<Placement>, Vec<Unplaced>, RepairDiagnostics) {
    run_repair_with_rotation_context(
        placements,
        unplaced,
        parts,
        sheets,
        policy,
        &RotationResolveContext::legacy_default(),
    )
}

pub fn run_repair_with_rotation_context(
    placements: Vec<Placement>,
    unplaced: Vec<Unplaced>,
    parts: &[Part],
    sheets: &[SheetShape],
    policy: &mut StoppingPolicy,
    rotation_context: &RotationResolveContext,
) -> (Vec<Placement>, Vec<Unplaced>, RepairDiagnostics) {
    let mut diag = RepairDiagnostics::default();

    // 1. Detect violations.
    let violations = find_violations(&placements, parts, sheets);
    let violation_indices: HashSet<usize> = violations.iter().map(|(i, _)| *i).collect();
    for (_, vtype) in &violations {
        match vtype {
            ViolationType::Overlap => diag.overlap_detected += 1,
            ViolationType::BoundaryOrSheet => diag.boundary_detected += 1,
        }
    }

    // 2. Split: keep valid placements, queue invalid ones for repair.
    let mut valid_placements: Vec<Placement> = Vec::new();
    let mut repair_items: Vec<RepairItem> = Vec::new();

    for (idx, p) in placements.into_iter().enumerate() {
        if violation_indices.contains(&idx) {
            let (w, h, rots) =
                resolve_part_dims(&p.part_id, &p.instance_id, parts, rotation_context);
            repair_items.push(RepairItem {
                instance_id: p.instance_id,
                part_id: p.part_id,
                width: w,
                height: h,
                allowed_rotations: rots,
            });
        } else {
            valid_placements.push(p);
        }
    }

    // 3. Add previously-unplaced items (skip PART_NEVER_FITS_STOCK).
    let mut out_unplaced: Vec<Unplaced> = Vec::new();
    for u in &unplaced {
        if u.reason == "PART_NEVER_FITS_STOCK" {
            out_unplaced.push(u.clone());
            continue;
        }
        let (w, h, rots) = resolve_part_dims(&u.part_id, &u.instance_id, parts, rotation_context);
        repair_items.push(RepairItem {
            instance_id: u.instance_id.clone(),
            part_id: u.part_id.clone(),
            width: w,
            height: h,
            allowed_rotations: rots,
        });
    }

    // 4. Sort repair queue deterministically: area desc → instance_id asc.
    repair_items.sort_by(|a, b| {
        let area_b = b.width * b.height;
        let area_a = a.width * a.height;
        area_b
            .partial_cmp(&area_a)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| a.instance_id.cmp(&b.instance_id))
    });

    // 5. Build bboxes from valid placements as starting point.
    let mut placed_bboxes: Vec<PlacedBbox> = Vec::new();
    for p in &valid_placements {
        if let Some(pt) = parts.iter().find(|pt| pt.id == p.part_id) {
            if let Some(bbox) = bbox_from_placement(p, pt.width, pt.height) {
                placed_bboxes.push(bbox);
            }
        }
    }

    // 6. Try to reinsert each item in the queue.
    for item in repair_items {
        if policy.should_stop() {
            diag.stopped_by_policy += 1;
            out_unplaced.push(Unplaced {
                instance_id: item.instance_id,
                part_id: item.part_id,
                reason: "REPAIR_STOPPED".to_string(),
            });
            continue;
        }
        policy.tick();
        diag.attempts += 1;

        if item.allowed_rotations.is_empty() || item.width <= 0.0 || item.height <= 0.0 {
            diag.failures += 1;
            out_unplaced.push(Unplaced {
                instance_id: item.instance_id,
                part_id: item.part_id,
                reason: "REPAIR_FAILED".to_string(),
            });
            continue;
        }

        let (candidates, _) = generate_candidates_with_sheets(sheets, &placed_bboxes);
        let mut placed_this = false;

        'cand: for candidate in &candidates {
            let sheet = &sheets[candidate.sheet_index];
            for &rot in &item.allowed_rotations {
                let (rw, rh) = dims_for_rotation(item.width, item.height, rot);
                let rect = Rect {
                    x1: candidate.x,
                    y1: candidate.y,
                    x2: candidate.x + rw,
                    y2: candidate.y + rh,
                };
                if !rect_within_boundary(rect, sheet) {
                    continue;
                }
                let candidate_bbox = PlacedBbox {
                    sheet_index: candidate.sheet_index,
                    x1: candidate.x,
                    y1: candidate.y,
                    x2: candidate.x + rw,
                    y2: candidate.y + rh,
                };
                if placed_bboxes.iter().any(|pb| pb.overlaps(&candidate_bbox)) {
                    continue;
                }
                let (anchor_x, anchor_y) = placement_anchor_from_rect_min(
                    candidate.x,
                    candidate.y,
                    item.width,
                    item.height,
                    rot,
                );
                placed_bboxes.push(candidate_bbox);
                valid_placements.push(Placement {
                    instance_id: item.instance_id.clone(),
                    part_id: item.part_id.clone(),
                    sheet_index: candidate.sheet_index,
                    x: anchor_x,
                    y: anchor_y,
                    rotation_deg: rot,
                });
                placed_this = true;
                diag.successes += 1;
                break 'cand;
            }
        }

        if !placed_this {
            diag.failures += 1;
            out_unplaced.push(Unplaced {
                instance_id: item.instance_id,
                part_id: item.part_id,
                reason: "REPAIR_FAILED".to_string(),
            });
        }
    }

    diag.stop_reason = format!("{:?}", policy.stop_reason());
    (valid_placements, out_unplaced, diag)
}

fn resolve_part_dims(
    part_id: &str,
    instance_id: &str,
    parts: &[Part],
    rotation_context: &RotationResolveContext,
) -> (f64, f64, Vec<f64>) {
    match parts.iter().find(|pt| pt.id == part_id) {
        Some(pt) => {
            let rots = resolve_instance_rotation_angles(pt, instance_id, rotation_context);
            (pt.width, pt.height, rots)
        }
        None => (0.0, 0.0, vec![]),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::item::expand_instances;
    use crate::optimizer::initializer::build_initial_layout;
    use crate::optimizer::stopping::StoppingPolicy;
    use crate::sheet::{expand_sheets, Stock};

    fn make_part(id: &str, w: f64, h: f64, qty: i64, rots: Vec<i64>) -> Part {
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

    #[test]
    fn find_violations_clean_layout() {
        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (placed, _, _) = build_initial_layout(&instances, &parts, &sheets);
        let v = find_violations(&placed, &parts, &sheets);
        assert!(v.is_empty(), "valid layout should have no violations");
    }

    #[test]
    fn find_violations_detects_overlap() {
        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (mut placed, _, _) = build_initial_layout(&instances, &parts, &sheets);
        assert!(placed.len() >= 2);
        placed[1].x = placed[0].x;
        placed[1].y = placed[0].y;
        let v = find_violations(&placed, &parts, &sheets);
        assert_eq!(v.len(), 1);
        assert_eq!(v[0].1, ViolationType::Overlap);
    }

    #[test]
    fn find_violations_detects_boundary() {
        let parts = vec![make_part("A", 30.0, 30.0, 1, vec![0])];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (mut placed, _, _) = build_initial_layout(&instances, &parts, &sheets);
        placed[0].x = 999.0;
        placed[0].y = 999.0;
        let v = find_violations(&placed, &parts, &sheets);
        assert_eq!(v.len(), 1);
        assert_eq!(v[0].1, ViolationType::BoundaryOrSheet);
    }

    #[test]
    fn repair_fixes_overlap() {
        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (mut placed, unplaced, _) = build_initial_layout(&instances, &parts, &sheets);
        assert!(placed.len() >= 2);
        placed[1].x = placed[0].x;
        placed[1].y = placed[0].y;

        let mut policy = StoppingPolicy::new(256, 60.0);
        let (rep, rep_unplaced, diag) = run_repair(placed, unplaced, &parts, &sheets, &mut policy);
        assert_eq!(diag.overlap_detected, 1);
        assert_eq!(rep.len() + rep_unplaced.len(), 2);
        let v = find_violations(&rep, &parts, &sheets);
        assert!(
            v.is_empty(),
            "repaired layout must have no violations: {diag:?}"
        );
    }

    #[test]
    fn repair_fixes_boundary_violation() {
        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (mut placed, unplaced, _) = build_initial_layout(&instances, &parts, &sheets);
        assert!(!placed.is_empty());
        placed[0].x = 500.0;
        placed[0].y = 500.0;

        let mut policy = StoppingPolicy::new(256, 60.0);
        let (rep, rep_unplaced, diag) = run_repair(placed, unplaced, &parts, &sheets, &mut policy);
        assert_eq!(diag.boundary_detected, 1);
        assert_eq!(rep.len() + rep_unplaced.len(), 2);
        let v = find_violations(&rep, &parts, &sheets);
        assert!(v.is_empty(), "repaired layout must have no violations");
    }

    #[test]
    fn repair_reinserts_unplaced() {
        let parts = vec![make_part("A", 30.0, 30.0, 1, vec![0])];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let artificial_unplaced = vec![Unplaced {
            instance_id: "A__0001".to_string(),
            part_id: "A".to_string(),
            reason: "NO_CANDIDATE".to_string(),
        }];

        let mut policy = StoppingPolicy::new(256, 60.0);
        let (rep, rep_unplaced, diag) =
            run_repair(vec![], artificial_unplaced, &parts, &sheets, &mut policy);
        assert_eq!(diag.successes, 1);
        assert_eq!(rep.len(), 1);
        assert!(rep_unplaced.is_empty());
    }

    #[test]
    fn repair_count_invariant() {
        let parts = vec![make_part("A", 30.0, 30.0, 3, vec![0])];
        let stocks = vec![make_stock("S", 60.0, 60.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (mut placed, unplaced, _) = build_initial_layout(&instances, &parts, &sheets);
        let total = placed.len() + unplaced.len();
        if !placed.is_empty() {
            placed[0].x = 9999.0; // corrupt one
        }
        let mut policy = StoppingPolicy::new(256, 60.0);
        let (rep, rep_unplaced, _) = run_repair(placed, unplaced, &parts, &sheets, &mut policy);
        assert_eq!(rep.len() + rep_unplaced.len(), total);
    }

    #[test]
    fn repair_deterministic() {
        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (mut placed, unplaced, _) = build_initial_layout(&instances, &parts, &sheets);
        placed[0].x = 999.0;

        let mut p1 = StoppingPolicy::new(256, 60.0);
        let (r1, u1, _) = run_repair(placed.clone(), unplaced.clone(), &parts, &sheets, &mut p1);
        let mut p2 = StoppingPolicy::new(256, 60.0);
        let (r2, u2, _) = run_repair(placed, unplaced, &parts, &sheets, &mut p2);

        assert_eq!(r1.len(), r2.len());
        assert_eq!(u1.len(), u2.len());
        for (a, b) in r1.iter().zip(r2.iter()) {
            assert_eq!(a.instance_id, b.instance_id);
            assert_eq!(a.x.to_bits(), b.x.to_bits());
            assert_eq!(a.y.to_bits(), b.y.to_bits());
            assert_eq!(a.rotation_deg, b.rotation_deg);
        }
    }

    #[test]
    fn backend_validation_bbox_matches_find_violations() {
        use crate::optimizer::collision_backend::BboxCollisionBackend;

        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (mut placed, _, _) = build_initial_layout(&instances, &parts, &sheets);
        assert!(placed.len() >= 2);
        // Force overlap.
        placed[1].x = placed[0].x;
        placed[1].y = placed[0].y;

        let old = find_violations(&placed, &parts, &sheets);
        let checked = validate_placements_with_backend_checked(
            &placed,
            &parts,
            &sheets,
            &BboxCollisionBackend,
        );

        assert_eq!(
            old.len(),
            checked.violations.len(),
            "bbox checked must match find_violations violation count"
        );
        assert_eq!(
            checked.diagnostics.unsupported_queries, 0,
            "bbox backend has zero unsupported queries on valid geometry"
        );
        assert_eq!(
            checked.diagnostics.bbox_fallback_queries, 0,
            "checked path never does bbox fallback"
        );
    }

    #[test]
    fn backend_validation_reports_unsupported_count() {
        use crate::optimizer::collision_backend::{BboxCollisionBackend, CdeCollisionBackend};

        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (placed, _, _) = build_initial_layout(&instances, &parts, &sheets);
        assert!(!placed.is_empty(), "need at least one placement");

        // CDE adapter works for rect parts (no outer_points) → 0 unsupported queries.
        let cde_result = validate_placements_with_backend_checked(
            &placed,
            &parts,
            &sheets,
            &CdeCollisionBackend,
        );
        assert_eq!(
            cde_result.diagnostics.unsupported_queries, 0,
            "CDE adapter must succeed for valid rect parts (got {} unsupported)",
            cde_result.diagnostics.unsupported_queries
        );
        assert_eq!(
            cde_result.diagnostics.bbox_fallback_queries, 0,
            "checked path must not do bbox fallback"
        );

        // Bbox backend also must have 0 unsupported queries for the same layout.
        let bbox_result = validate_placements_with_backend_checked(
            &placed,
            &parts,
            &sheets,
            &BboxCollisionBackend,
        );
        assert_eq!(
            bbox_result.diagnostics.unsupported_queries, 0,
            "BboxCollisionBackend must not return unsupported for rect parts"
        );
    }

    #[test]
    fn repair_stopping_policy_respected() {
        let parts = vec![make_part("A", 30.0, 30.0, 4, vec![0])];
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (placed, unplaced, _) = build_initial_layout(&instances, &parts, &sheets);
        // Add 4 extra unplaced items to exceed the iteration limit
        let mut extra_unplaced = unplaced;
        for i in 0..4 {
            extra_unplaced.push(Unplaced {
                instance_id: format!("EXTRA__{i:04}"),
                part_id: "A".to_string(),
                reason: "NO_CANDIDATE".to_string(),
            });
        }
        let total = placed.len() + extra_unplaced.len();
        let mut policy = StoppingPolicy::new(2, 60.0); // max 2 iterations
        let (rep, rep_unplaced, diag) =
            run_repair(placed, extra_unplaced, &parts, &sheets, &mut policy);
        assert_eq!(rep.len() + rep_unplaced.len(), total);
        assert!(
            diag.stopped_by_policy > 0,
            "policy should have stopped some items"
        );
    }

    // -----------------------------------------------------------------------
    // SGH-Q11 tests
    // -----------------------------------------------------------------------

    #[test]
    fn explicit_exact_no_silent_bbox_fallback_in_internal_search() {
        use crate::io::CollisionBackendKind;

        // The L-shape notch scenario: part with outer_points (L polygon).
        // Small rect placed inside the notch (x=15,y=15, 3×3).
        // - bbox validate: detects overlap (bbox covers 0..20 × 0..20)
        // - exact validate: no overlap (rect is in the notch [10,20]×[10,20])
        // validate_placements_for_backend(JaguaPolygonExact) must NOT silently fall back
        // to bbox: it must return the exact result (empty violations for this case).
        let l_json = serde_json::json!([
            [0.0, 0.0],
            [20.0, 0.0],
            [20.0, 10.0],
            [10.0, 10.0],
            [10.0, 20.0],
            [0.0, 20.0]
        ]);
        let l_part = Part {
            id: "L".to_string(),
            width: 20.0,
            height: 20.0,
            quantity: 1,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: Some(l_json),
            prepared_outer_points: None,
            rotation_policy: None,
        };
        let s_part = Part {
            id: "S".to_string(),
            width: 3.0,
            height: 3.0,
            quantity: 1,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: None,
            prepared_outer_points: None,
            rotation_policy: None,
        };
        let parts = vec![l_part, s_part];

        let stocks = vec![crate::sheet::Stock {
            id: "SH".to_string(),
            quantity: 1,
            width: Some(100.0),
            height: Some(100.0),
            outer_points: None,
            holes_points: None,
            cost_per_use: None,
        }];
        let sheets = crate::sheet::expand_sheets(&stocks).expect("sheets");

        let placements = vec![
            Placement {
                instance_id: "L__0001".to_string(),
                part_id: "L".to_string(),
                sheet_index: 0,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
            Placement {
                instance_id: "S__0001".to_string(),
                part_id: "S".to_string(),
                sheet_index: 0,
                x: 15.0,
                y: 15.0,
                rotation_deg: 0.0,
            },
        ];

        let bbox_violations = find_violations(&placements, &parts, &sheets);
        assert!(
            !bbox_violations.is_empty(),
            "bbox baseline must detect overlap (S inside L bbox)"
        );

        let exact_violations = validate_placements_for_backend(
            &placements,
            &parts,
            &sheets,
            &CollisionBackendKind::JaguaPolygonExact,
        );
        assert!(
            exact_violations.is_empty(),
            "exact backend must find no overlap: S is in the L notch — no silent bbox fallback"
        );
    }
}
