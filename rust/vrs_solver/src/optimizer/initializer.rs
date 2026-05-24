use std::collections::HashSet;

use crate::geometry::Rect;
use crate::io::{Placement, Unplaced};
use crate::item::{
    dims_for_rotation, normalize_allowed_rotations, placement_anchor_from_rect_min,
    rotated_bbox_min_offset, Instance, Part,
};
use crate::sheet::SheetShape;
use super::boundary::rect_within_boundary;
use super::candidates::{generate_candidates_with_sheets, CandidatePoint, PlacedBbox};
use super::separator::{VrsSeparator, VrsSeparatorConfig};
use super::working::WorkingLayout;

// ---------------------------------------------------------------------------
// ConstructionDiagnostics
// ---------------------------------------------------------------------------

/// Diagnostics collected during a single construction run.
#[derive(Debug, Default, Clone)]
pub struct ConstructionDiagnostics {
    pub candidates_tried: usize,
    pub rejected_out_of_sheet: usize,
    pub rejected_collision: usize,
    pub rejected_unsupported_rotation: usize,
    pub items_unplaced_no_candidate: usize,
    /// Total candidate points generated across all per-item generations (JG-18).
    pub total_candidates_generated: usize,
    /// Candidates from irregular sheet vertex-near sources (JG-18).
    pub candidates_from_vertex: usize,
    /// Candidates from irregular sheet edge-near sources (JG-18).
    pub candidates_from_edge: usize,
    /// Candidates from irregular sheet interior sampling (JG-18).
    pub candidates_from_interior: usize,
    // SGH-03: LBF scoring and separator fallback counters
    /// Number of valid (boundary + collision-free) candidates scored by the LBF scorer.
    pub lbf_candidates_scored: usize,
    /// Number of items placed via the LBF clear candidate path (no fallback needed).
    pub lbf_clear_accepts: usize,
    /// Number of separator fallback attempts (activated when no clear LBF candidate found).
    pub separator_fallback_attempts: usize,
    /// Separator fallback attempts that produced a commit-gate-valid result.
    pub separator_fallback_successes: usize,
    /// Separator fallback attempts that failed to produce a commit-gate-valid result.
    pub separator_fallback_failures: usize,
    /// Fallback attempts that passed the separator but were rejected by validate_for_commit.
    pub separator_fallback_rejected_by_commit_gate: usize,
}

impl ConstructionDiagnostics {
    pub fn summary(&self) -> String {
        format!(
            "candidates_tried={} out_of_sheet={} collision={} unsupported_rot={} no_candidate={} \
             total_gen={} vertex={} edge={} interior={} \
             lbf_scored={} lbf_clear={} \
             sep_attempts={} sep_ok={} sep_fail={} sep_commit_reject={}",
            self.candidates_tried,
            self.rejected_out_of_sheet,
            self.rejected_collision,
            self.rejected_unsupported_rotation,
            self.items_unplaced_no_candidate,
            self.total_candidates_generated,
            self.candidates_from_vertex,
            self.candidates_from_edge,
            self.candidates_from_interior,
            self.lbf_candidates_scored,
            self.lbf_clear_accepts,
            self.separator_fallback_attempts,
            self.separator_fallback_successes,
            self.separator_fallback_failures,
            self.separator_fallback_rejected_by_commit_gate,
        )
    }
}

// ---------------------------------------------------------------------------
// sort_instances_for_placement
// ---------------------------------------------------------------------------

/// Sort instances for placement: descending area → descending max bbox dim → part_id asc → instance_id asc.
pub fn sort_instances_for_placement<'a>(instances: &'a [Instance], parts: &[Part]) -> Vec<&'a Instance> {
    let part_area = |inst: &&Instance| -> f64 {
        parts.iter().find(|p| p.id == inst.part_id)
            .map(|p| p.width * p.height)
            .unwrap_or(0.0)
    };
    let max_dim = |inst: &&Instance| -> f64 { inst.width.max(inst.height) };
    let mut v: Vec<&Instance> = instances.iter().collect();
    v.sort_by(|a, b| {
        part_area(b).partial_cmp(&part_area(a)).unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| max_dim(b).partial_cmp(&max_dim(a)).unwrap_or(std::cmp::Ordering::Equal))
            .then_with(|| a.part_id.cmp(&b.part_id))
            .then_with(|| a.instance_id.cmp(&b.instance_id))
    });
    v
}

// ---------------------------------------------------------------------------
// bbox_from_placement (public — used by repair, score, separator)
// ---------------------------------------------------------------------------

/// Recover the bbox (bbox-min coords) from a v1 Placement and the original part dimensions.
pub fn bbox_from_placement(placement: &Placement, w: f64, h: f64) -> Option<PlacedBbox> {
    let (bx_off, by_off) = rotated_bbox_min_offset(w, h, placement.rotation_deg)?;
    let (rw, rh) = dims_for_rotation(w, h, placement.rotation_deg)?;
    let x1 = placement.x + bx_off;
    let y1 = placement.y + by_off;
    Some(PlacedBbox { sheet_index: placement.sheet_index, x1, y1, x2: x1 + rw, y2: y1 + rh })
}

// ---------------------------------------------------------------------------
// Private helpers — SGH-03
// ---------------------------------------------------------------------------

/// Rebuild the placed_bboxes cache from a placement list.
///
/// Placements that cannot be resolved (unknown part or invalid rotation) are skipped.
/// After a successful separator fallback the entire cache must be rebuilt because the
/// separator may have moved items from earlier in the construction order.
fn rebuild_placed_bboxes(placements: &[Placement], parts: &[Part]) -> Vec<PlacedBbox> {
    placements.iter()
        .filter_map(|p| {
            let pt = parts.iter().find(|pt| pt.id == p.part_id)?;
            bbox_from_placement(p, pt.width, pt.height)
        })
        .collect()
}

/// Find the target sheet for the separator fallback seed placement.
///
/// Returns the already-used sheet with the most estimated free area
/// (sheet.area − sum of placed bbox areas on that sheet).
/// Falls back to sheet index 0 if no sheet is currently in use.
fn find_seed_sheet_index(placed_bboxes: &[PlacedBbox], sheets: &[SheetShape]) -> usize {
    if sheets.is_empty() { return 0; }

    let used: HashSet<usize> = placed_bboxes.iter().map(|pb| pb.sheet_index).collect();
    if used.is_empty() { return 0; }

    let mut best_sheet = 0usize;
    let mut best_free = f64::NEG_INFINITY;

    for &si in &used {
        if si >= sheets.len() { continue; }
        let placed_area: f64 = placed_bboxes.iter()
            .filter(|pb| pb.sheet_index == si)
            .map(|pb| (pb.x2 - pb.x1) * (pb.y2 - pb.y1))
            .sum();
        let free = sheets[si].area - placed_area;
        // Prefer larger free area; tie-break by lower sheet index.
        if free > best_free || (free == best_free && si < best_sheet) {
            best_free = free;
            best_sheet = si;
        }
    }

    best_sheet
}

/// Returns true when score key `a` is strictly better (lower) than `b`.
///
/// LBF V1 priority:
///   1. Used sheet (is_unused=false) beats unused sheet (is_unused=true).
///   2. Smaller y.
///   3. Smaller x.
///   4. Smaller sheet_index.
fn lbf_key_better_than(
    (ia, ya, xa, sia): (bool, f64, f64, usize),
    (ib, yb, xb, sib): (bool, f64, f64, usize),
) -> bool {
    if ia != ib { return !ia; } // used (false) beats unused (true)
    const EPS: f64 = 1e-12;
    if (ya - yb).abs() > EPS { return ya < yb; }
    if (xa - xb).abs() > EPS { return xa < xb; }
    sia < sib
}

/// One clear (collision-free, boundary-valid) candidate selected by LBF scoring.
struct LbfClear {
    placement: Placement,
    bbox: PlacedBbox,
}

/// Select the best clear candidate for `instance` using LBF scoring.
///
/// Iterates all pre-generated candidates × allowed rotations.
/// For each (candidate, rotation) that passes boundary and collision checks,
/// computes an LBF score key (is_unused_sheet, y, x, sheet_index) and keeps the best.
/// Only the first valid rotation per candidate point is scored (stable rotation order).
///
/// Updates `diag` counters for tried / rejected candidates.
fn lbf_select_clear_candidate(
    candidates: &[CandidatePoint],
    instance: &Instance,
    part: &Part,
    allowed_rotations: &[i64],
    placed_bboxes: &[PlacedBbox],
    sheets: &[SheetShape],
    used_sheets: &HashSet<usize>,
    diag: &mut ConstructionDiagnostics,
) -> Option<LbfClear> {
    // best score key: (is_unused: bool, y, x, sheet_index) — lower is better
    let mut best_key: Option<(bool, f64, f64, usize)> = None;
    let mut best_result: Option<LbfClear> = None;

    for candidate in candidates {
        if candidate.sheet_index >= sheets.len() {
            continue;
        }
        let sheet = &sheets[candidate.sheet_index];
        let is_unused = !used_sheets.contains(&candidate.sheet_index);

        for &rot in allowed_rotations {
            let Some((rw, rh)) = dims_for_rotation(part.width, part.height, rot) else {
                diag.rejected_unsupported_rotation += 1;
                continue;
            };
            diag.candidates_tried += 1;
            let rect = Rect {
                x1: candidate.x,
                y1: candidate.y,
                x2: candidate.x + rw,
                y2: candidate.y + rh,
            };
            if !rect_within_boundary(rect, sheet) {
                diag.rejected_out_of_sheet += 1;
                continue;
            }
            let cand_bbox = PlacedBbox {
                sheet_index: candidate.sheet_index,
                x1: candidate.x,
                y1: candidate.y,
                x2: candidate.x + rw,
                y2: candidate.y + rh,
            };
            if placed_bboxes.iter().any(|pb| pb.overlaps(&cand_bbox)) {
                diag.rejected_collision += 1;
                continue;
            }

            // Valid candidate — score it.
            diag.lbf_candidates_scored += 1;
            let score_key = (is_unused, candidate.y, candidate.x, candidate.sheet_index);
            let is_better = best_key.map_or(true, |bk| lbf_key_better_than(score_key, bk));

            if is_better {
                let Some((ax, ay)) = placement_anchor_from_rect_min(
                    candidate.x, candidate.y, part.width, part.height, rot,
                ) else {
                    continue;
                };
                best_key = Some(score_key);
                best_result = Some(LbfClear {
                    placement: Placement {
                        instance_id: instance.instance_id.clone(),
                        part_id: instance.part_id.clone(),
                        sheet_index: candidate.sheet_index,
                        x: ax,
                        y: ay,
                        rotation_deg: rot,
                    },
                    bbox: cand_bbox,
                });
            }
            // Only the first valid rotation per candidate point is considered.
            break;
        }
    }

    best_result
}

/// Try separator fallback for an instance that has no clear LBF candidate.
///
/// 1. Selects a seed sheet (used with most free area, or sheet 0).
/// 2. Creates a deterministic seed placement at the sheet origin for the
///    first rotation that fits within the sheet boundary (or the first
///    supported rotation if none fits cleanly).
/// 3. Builds a WorkingLayout from current_placements + seed placement.
/// 4. Runs VrsSeparator.
/// 5. Accepts the result only when sep_diag.best_loss == 0.0 or converged,
///    AND WorkingLayout::validate_for_commit passes.
/// 6. On success, returns (new_placements, rebuilt placed_bboxes).
/// 7. On failure, returns None and leaves current_placements untouched.
fn try_separator_fallback_for_instance(
    current_placements: &[Placement],
    instance: &Instance,
    part: &Part,
    parts: &[Part],
    sheets: &[SheetShape],
    placed_bboxes: &[PlacedBbox],
    diag: &mut ConstructionDiagnostics,
) -> Option<(Vec<Placement>, Vec<PlacedBbox>)> {
    diag.separator_fallback_attempts += 1;

    if sheets.is_empty() {
        diag.separator_fallback_failures += 1;
        return None;
    }

    let allowed_rotations = match normalize_allowed_rotations(&part.allowed_rotations_deg) {
        Ok(r) => r,
        Err(_) => {
            diag.separator_fallback_failures += 1;
            return None;
        }
    };

    // Pick seed sheet: used sheet with most free area, or sheet 0.
    let target_sheet = find_seed_sheet_index(placed_bboxes, sheets);
    if target_sheet >= sheets.len() {
        diag.separator_fallback_failures += 1;
        return None;
    }

    // Prefer a rotation that fits at the sheet origin; fall back to any supported rotation.
    let seed_rot = allowed_rotations.iter().copied()
        .find(|&rot| {
            let Some((rw, rh)) = dims_for_rotation(part.width, part.height, rot) else { return false; };
            let rect = Rect { x1: 0.0, y1: 0.0, x2: rw, y2: rh };
            rect_within_boundary(rect, &sheets[target_sheet])
        })
        .or_else(|| allowed_rotations.first().copied());

    let seed_rot = match seed_rot {
        Some(r) => r,
        None => {
            diag.separator_fallback_failures += 1;
            return None;
        }
    };

    let (anchor_x, anchor_y) = match placement_anchor_from_rect_min(
        0.0, 0.0, part.width, part.height, seed_rot,
    ) {
        Some(a) => a,
        None => {
            diag.separator_fallback_failures += 1;
            return None;
        }
    };

    let seed_placement = Placement {
        instance_id: instance.instance_id.clone(),
        part_id: instance.part_id.clone(),
        sheet_index: target_sheet,
        x: anchor_x,
        y: anchor_y,
        rotation_deg: seed_rot,
    };

    // WorkingLayout = current placements + seed placement (may collide — separator will fix it).
    let mut working_placements = current_placements.to_vec();
    working_placements.push(seed_placement);
    let working = WorkingLayout::new(working_placements, vec![], sheets.len(), 0);

    let sep = VrsSeparator::new(VrsSeparatorConfig::default());
    let (result_layout, sep_diag) = sep.run(working, parts, sheets);

    if sep_diag.best_loss == 0.0 || sep_diag.converged {
        if result_layout.validate_for_commit(parts, sheets).is_ok() {
            let new_placements = result_layout.placements;
            let new_bboxes = rebuild_placed_bboxes(&new_placements, parts);
            diag.separator_fallback_successes += 1;
            return Some((new_placements, new_bboxes));
        } else {
            diag.separator_fallback_rejected_by_commit_gate += 1;
            diag.separator_fallback_failures += 1;
        }
    } else {
        diag.separator_fallback_failures += 1;
    }

    None
}

// ---------------------------------------------------------------------------
// build_initial_layout (public, SGH-03 enhanced)
// ---------------------------------------------------------------------------

/// Build the initial layout using LBF-scored candidate placement with separator fallback.
///
/// Item ordering: area desc → max_dim desc → part_id asc → instance_id asc (unchanged).
///
/// Per-item placement flow (SGH-03):
///   1. Generate candidates via `generate_candidates_with_sheets`.
///   2. LBF-score all boundary-valid, collision-free candidates:
///      priority = used-sheet first, then smaller y, smaller x, smaller sheet_index.
///   3. If a clear LBF candidate exists → place it, update placed_bboxes and used_sheets.
///   4. Else → try separator fallback (WorkingLayout + VrsSeparator).
///      On success → replace entire placement list; rebuild placed_bboxes and used_sheets.
///      On failure → item becomes unplaced (NO_CANDIDATE).
///
/// Invariant: `placed.len() + unplaced.len() == instances.len()`.
///
/// Public signature is unchanged from SGH-01/SGH-02.
pub fn build_initial_layout(
    instances: &[Instance],
    parts: &[Part],
    sheets: &[SheetShape],
) -> (Vec<Placement>, Vec<Unplaced>, ConstructionDiagnostics) {
    let mut placements: Vec<Placement> = Vec::new();
    let mut unplaced_list: Vec<Unplaced> = Vec::new();
    let mut diag = ConstructionDiagnostics::default();
    let mut placed_bboxes: Vec<PlacedBbox> = Vec::new();
    let mut used_sheets: HashSet<usize> = HashSet::new();

    let ordered = sort_instances_for_placement(instances, parts);

    for instance in ordered {
        let part = match parts.iter().find(|p| p.id == instance.part_id) {
            Some(p) => p,
            None => {
                unplaced_list.push(Unplaced {
                    instance_id: instance.instance_id.clone(),
                    part_id: instance.part_id.clone(),
                    reason: "INTERNAL_PART_NOT_FOUND".to_string(),
                });
                continue;
            }
        };

        let allowed_rotations = match normalize_allowed_rotations(&instance.allowed_rotations_deg) {
            Ok(r) => r,
            Err(_) => {
                diag.rejected_unsupported_rotation += 1;
                unplaced_list.push(Unplaced {
                    instance_id: instance.instance_id.clone(),
                    part_id: instance.part_id.clone(),
                    reason: "UNSUPPORTED_ROTATION".to_string(),
                });
                continue;
            }
        };

        let (candidates, cgen) = generate_candidates_with_sheets(sheets, &placed_bboxes);
        diag.total_candidates_generated += cgen.total;
        diag.candidates_from_vertex += cgen.from_vertex;
        diag.candidates_from_edge += cgen.from_edge;
        diag.candidates_from_interior += cgen.from_interior;

        // ── LBF-scored clear candidate selection ──────────────────────────
        let clear = lbf_select_clear_candidate(
            &candidates,
            instance,
            part,
            &allowed_rotations,
            &placed_bboxes,
            sheets,
            &used_sheets,
            &mut diag,
        );

        if let Some(LbfClear { placement, bbox }) = clear {
            diag.lbf_clear_accepts += 1;
            used_sheets.insert(placement.sheet_index);
            placed_bboxes.push(bbox);
            placements.push(placement);
            continue;
        }

        // ── Separator fallback ────────────────────────────────────────────
        let fallback = try_separator_fallback_for_instance(
            &placements,
            instance,
            part,
            parts,
            sheets,
            &placed_bboxes,
            &mut diag,
        );

        if let Some((new_placements, new_bboxes)) = fallback {
            used_sheets = new_placements.iter().map(|p| p.sheet_index).collect();
            placed_bboxes = new_bboxes;
            placements = new_placements;
            // The new item was included in the separator result; no separate push needed.
        } else {
            diag.items_unplaced_no_candidate += 1;
            unplaced_list.push(Unplaced {
                instance_id: instance.instance_id.clone(),
                part_id: instance.part_id.clone(),
                reason: "NO_CANDIDATE".to_string(),
            });
        }
    }

    (placements, unplaced_list, diag)
}

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::item::expand_instances;
    use crate::optimizer::repair::find_violations;
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
        Stock { id: id.to_string(), quantity: qty, width: Some(w), height: Some(h), outer_points: None, holes_points: None, cost_per_use: None }
    }

    // ── Existing tests (unchanged) ────────────────────────────────────────────

    #[test]
    fn sort_instances_area_descending() {
        let parts = vec![
            make_part("A", 10.0, 10.0, 1, vec![0]),
            make_part("B", 20.0, 20.0, 1, vec![0]),
        ];
        let instances = expand_instances(&parts).expect("expand");
        let sorted = sort_instances_for_placement(&instances, &parts);
        assert_eq!(sorted[0].part_id, "B");
        assert_eq!(sorted[1].part_id, "A");
    }

    #[test]
    fn small_fixture_all_placed() {
        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (placed, unplaced, _diag) = build_initial_layout(&instances, &parts, &sheets);
        assert_eq!(placed.len(), 2);
        assert!(unplaced.is_empty());
    }

    #[test]
    fn no_capacity_item_goes_to_unplaced() {
        let parts = vec![make_part("A", 200.0, 200.0, 1, vec![0])];
        let stocks = vec![make_stock("S", 50.0, 50.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (placed, unplaced, _diag) = build_initial_layout(&instances, &parts, &sheets);
        assert!(placed.is_empty());
        assert_eq!(unplaced.len(), 1);
        assert_eq!(unplaced[0].reason, "NO_CANDIDATE");
    }

    #[test]
    fn placed_plus_unplaced_equals_total() {
        let parts = vec![make_part("A", 60.0, 60.0, 3, vec![0])];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (placed, unplaced, _diag) = build_initial_layout(&instances, &parts, &sheets);
        assert_eq!(placed.len() + unplaced.len(), 3);
    }

    #[test]
    fn rotation_90_only_fits() {
        // 80×30 part, 40×100 sheet: rot=0 (80×30) → 80>40, fails; rot=90 (30×80) → fits
        let parts = vec![make_part("P", 80.0, 30.0, 1, vec![0, 90])];
        let stocks = vec![make_stock("S", 40.0, 100.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (placed, unplaced, _diag) = build_initial_layout(&instances, &parts, &sheets);
        assert_eq!(placed.len(), 1);
        assert_eq!(placed[0].rotation_deg, 90);
        assert!(unplaced.is_empty());
    }

    #[test]
    fn bbox_from_placement_rot0() {
        let p = Placement { instance_id: "A__0001".into(), part_id: "A".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0 };
        let bb = bbox_from_placement(&p, 100.0, 40.0).expect("bbox");
        assert!((bb.x2 - 100.0).abs() < 1e-9);
        assert!((bb.y2 - 40.0).abs() < 1e-9);
    }

    #[test]
    fn bbox_from_placement_rot90() {
        // anchor=(40,0), rot=90, w=100, h=40: offset=(-40,0) → bbox_min=(0,0), rw=40, rh=100
        let p = Placement { instance_id: "A__0001".into(), part_id: "A".into(), sheet_index: 0, x: 40.0, y: 0.0, rotation_deg: 90 };
        let bb = bbox_from_placement(&p, 100.0, 40.0).expect("bbox");
        assert!((bb.x1 - 0.0).abs() < 1e-9);
        assert!((bb.x2 - 40.0).abs() < 1e-9);
        assert!((bb.y2 - 100.0).abs() < 1e-9);
    }

    // ── SGH-03 new tests ──────────────────────────────────────────────────────

    // Test 1: LBF scorer prefers used sheet over unused sheet
    #[test]
    fn lbf_used_sheet_preferred_over_unused() {
        // Two identical 200×100 sheets. Part A (30×30, qty=1) goes first → lands on sheet 0.
        // Part B (30×30, qty=1) should also go to sheet 0 (used) rather than sheet 1 (unused).
        let parts = vec![
            make_part("A", 30.0, 30.0, 1, vec![0]),
            make_part("B", 30.0, 30.0, 1, vec![0]),
        ];
        let stocks = vec![
            make_stock("S0", 200.0, 100.0, 1),
            make_stock("S1", 200.0, 100.0, 1),
        ];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (placed, unplaced, diag) = build_initial_layout(&instances, &parts, &sheets);

        assert!(unplaced.is_empty(), "both items must be placed");
        assert_eq!(placed.len(), 2);
        // Both should be on sheet 0 (used-sheet preference).
        assert!(
            placed.iter().all(|p| p.sheet_index == 0),
            "LBF must prefer used sheet 0 over unused sheet 1: {:?}", placed
        );
        // LBF accepted both items via the clear path (no fallback needed).
        assert_eq!(diag.lbf_clear_accepts, 2);
    }

    // Test 2: build_initial_layout is deterministic
    #[test]
    fn deterministic_two_runs_identical() {
        let parts = vec![
            make_part("A", 40.0, 40.0, 2, vec![0]),
            make_part("B", 40.0, 40.0, 1, vec![0]),
        ];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (p1, u1, d1) = build_initial_layout(&instances, &parts, &sheets);
        let (p2, u2, d2) = build_initial_layout(&instances, &parts, &sheets);
        let key = |p: &Placement| (p.instance_id.clone(), p.x.to_bits(), p.y.to_bits(), p.rotation_deg);
        assert_eq!(
            p1.iter().map(key).collect::<Vec<_>>(),
            p2.iter().map(key).collect::<Vec<_>>(),
            "placements must be identical across runs"
        );
        assert_eq!(u1.len(), u2.len());
        assert_eq!(d1.lbf_clear_accepts, d2.lbf_clear_accepts);
    }

    // Test 3: placed + unplaced == expanded instances (invariant holds after SGH-03)
    #[test]
    fn placed_plus_unplaced_equals_instances() {
        let parts = vec![
            make_part("A", 30.0, 30.0, 3, vec![0]),
            make_part("B", 50.0, 50.0, 2, vec![0]),
        ];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (placed, unplaced, _) = build_initial_layout(&instances, &parts, &sheets);
        assert_eq!(placed.len() + unplaced.len(), instances.len());
    }

    // Test 4: separator fallback succeeds on a forced colliding seed
    #[test]
    fn separator_fallback_succeeds_on_forced_collision() {
        // A (30×30) already placed. We force a collision seed for B (30×30) at (0,0) on the
        // used sheet — separator should fix this and produce a valid layout.
        let parts = vec![
            make_part("A", 30.0, 30.0, 1, vec![0]),
            make_part("B", 30.0, 30.0, 1, vec![0]),
        ];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let instances_a = expand_instances(&[parts[0].clone()]).expect("a");

        // Place A at (0,0).
        let (placed_a, _, _) = build_initial_layout(&instances_a, &parts, &sheets);
        assert_eq!(placed_a.len(), 1);
        let placed_bboxes_a = rebuild_placed_bboxes(&placed_a, &parts);

        // Build instance for B.
        let instances_b = expand_instances(&[parts[1].clone()]).expect("b");
        let b_instance = &instances_b[0];
        let b_part = &parts[1];

        let mut diag = ConstructionDiagnostics::default();
        let result = try_separator_fallback_for_instance(
            &placed_a,
            b_instance,
            b_part,
            &parts,
            &sheets,
            &placed_bboxes_a,
            &mut diag,
        );

        assert!(result.is_some(), "separator fallback must succeed for two 30×30 items on a 200×100 sheet");
        let (new_placements, _new_bboxes) = result.unwrap();
        assert_eq!(new_placements.len(), 2, "both A and B must be in the result");

        // Result must be violation-free.
        let violations = find_violations(&new_placements, &parts, &sheets);
        assert!(violations.is_empty(), "fallback result must be violation-free: {:?}", violations);
        assert_eq!(diag.separator_fallback_successes, 1);
        assert_eq!(diag.separator_fallback_failures, 0);
    }

    // Test 5: separator fallback failure is rollback-safe (previous placements unchanged)
    #[test]
    fn separator_fallback_failure_is_rollback_safe() {
        // Sheet 50×50. Item A is 40×40, placed at (0,0). Item B is 40×40 — cannot fit alongside A.
        let parts = vec![
            make_part("A", 40.0, 40.0, 1, vec![0]),
            make_part("B", 40.0, 40.0, 1, vec![0]),
        ];
        let stocks = vec![make_stock("S", 50.0, 50.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");

        // Manually place A at (0,0).
        let p_a = Placement {
            instance_id: "A__0001".to_string(),
            part_id: "A".to_string(),
            sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0,
        };
        let placed_a = vec![p_a.clone()];
        let placed_bboxes_a = rebuild_placed_bboxes(&placed_a, &parts);

        let instances_b = expand_instances(&[parts[1].clone()]).expect("b");
        let b_instance = &instances_b[0];
        let b_part = &parts[1];

        let mut diag = ConstructionDiagnostics::default();
        let result = try_separator_fallback_for_instance(
            &placed_a,
            b_instance,
            b_part,
            &parts,
            &sheets,
            &placed_bboxes_a,
            &mut diag,
        );

        // The fallback should fail — B cannot be placed alongside A on a 50×50 sheet.
        assert!(result.is_none(), "fallback must fail when B cannot fit alongside A");
        assert_eq!(diag.separator_fallback_failures, 1, "failure must be counted");

        // The original placed_a slice is unchanged (rollback safety).
        assert_eq!(placed_a.len(), 1, "placed_a must remain untouched");
        assert_eq!(placed_a[0].instance_id, "A__0001");
        assert!((placed_a[0].x).abs() < 1e-9);
        assert!((placed_a[0].y).abs() < 1e-9);
    }

    // Test 6: successful construction output is violation-free
    #[test]
    fn successful_construction_output_is_valid() {
        let parts = vec![
            make_part("A", 30.0, 30.0, 3, vec![0]),
            make_part("B", 20.0, 50.0, 2, vec![0, 90]),
        ];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (placed, _, _) = build_initial_layout(&instances, &parts, &sheets);
        let violations = find_violations(&placed, &parts, &sheets);
        assert!(violations.is_empty(), "construction output must be violation-free: {:?}", violations);
    }

    // Test 7: diagnostics summary contains the new LBF/separator fields
    #[test]
    fn diagnostics_summary_contains_lbf_separator_fields() {
        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (_, _, diag) = build_initial_layout(&instances, &parts, &sheets);
        let summary = diag.summary();
        assert!(summary.contains("lbf_scored="), "summary must contain lbf_scored");
        assert!(summary.contains("lbf_clear="), "summary must contain lbf_clear");
        assert!(summary.contains("sep_attempts="), "summary must contain sep_attempts");
        assert!(summary.contains("sep_ok="), "summary must contain sep_ok");
        assert!(summary.contains("sep_fail="), "summary must contain sep_fail");
        assert!(summary.contains("sep_commit_reject="), "summary must contain sep_commit_reject");
    }

    // Test 8: rebuild_placed_bboxes produces consistent cache
    #[test]
    fn rebuild_placed_bboxes_matches_incremental() {
        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (placed, _, _) = build_initial_layout(&instances, &parts, &sheets);
        let rebuilt = rebuild_placed_bboxes(&placed, &parts);
        assert_eq!(rebuilt.len(), placed.len(), "rebuilt bboxes count must match placements");
        for (bb, p) in rebuilt.iter().zip(placed.iter()) {
            assert_eq!(bb.sheet_index, p.sheet_index);
        }
    }
}
