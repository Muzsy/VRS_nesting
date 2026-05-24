use std::collections::HashSet;

use crate::geometry::Rect;
use crate::io::{Placement, Unplaced};
use crate::item::{dims_for_rotation, normalize_allowed_rotations, placement_anchor_from_rect_min, Part};
use crate::sheet::SheetShape;
use super::boundary::rect_within_boundary;
use super::candidates::{generate_candidates_with_sheets, PlacedBbox};
use super::initializer::bbox_from_placement;
use super::stopping::StoppingPolicy;

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
        let rect = Rect { x1: bbox.x1, y1: bbox.y1, x2: bbox.x2, y2: bbox.y2 };
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

/// Internal record for an item queued for repair reinsertion.
struct RepairItem {
    instance_id: String,
    part_id: String,
    width: f64,
    height: f64,
    allowed_rotations: Vec<i64>,
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
            let (w, h, rots) = resolve_part_dims(&p.part_id, parts);
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
        let (w, h, rots) = resolve_part_dims(&u.part_id, parts);
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
                let Some((rw, rh)) = dims_for_rotation(item.width, item.height, rot) else {
                    continue;
                };
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
                let Some((anchor_x, anchor_y)) = placement_anchor_from_rect_min(
                    candidate.x, candidate.y, item.width, item.height, rot,
                ) else {
                    continue;
                };
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

fn resolve_part_dims(part_id: &str, parts: &[Part]) -> (f64, f64, Vec<i64>) {
    match parts.iter().find(|pt| pt.id == part_id) {
        Some(pt) => {
            let rots = normalize_allowed_rotations(&pt.allowed_rotations_deg).unwrap_or_default();
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
        assert!(v.is_empty(), "repaired layout must have no violations: {diag:?}");
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
        assert!(diag.stopped_by_policy > 0, "policy should have stopped some items");
    }
}
