//! Phase 1 ScoreModel V1 — minimization objective for rectangular nesting.
//!
//! Score direction: **lower `total_cost` is better**.
//!
//! Weight invariants (see [`ScoreWeights::default`]):
//! - `overlap_penalty_per_pair` and `boundary_penalty_per_item` dominate all other
//!   contributions, so an invalid layout always scores worse than any valid layout.
//! - `compactness_weight` is tiny — tie-breaker only, never overrides validity or count.
//! - Penalty hierarchy: overlap/boundary (1e9) >> unplaced (1e6) >> sheet_count (1e4)
//!   >> placed_area_reward (1.0) >> compactness (0.001).

use crate::io::{Placement, Unplaced};
use crate::item::{dims_for_rotation, Part};
use crate::sheet::SheetShape;
use super::candidates::PlacedBbox;
use super::initializer::bbox_from_placement;
use super::repair::{find_violations, ViolationType};

// ---------------------------------------------------------------------------
// ScoreWeights — default weight profile
// ---------------------------------------------------------------------------

/// Weight profile for the Phase 1 ScoreModel.
///
/// All weights are positive. The score direction is minimization: every
/// contribution either reduces cost (placed area, as a negative term) or
/// adds cost (penalties).
///
/// Default profile:
///
/// | Component                  | Default weight     | Rationale                          |
/// |----------------------------|--------------------|------------------------------------|
/// | `placed_area_reward`       | 1.0                | Reward per unit² placed            |
/// | `unplaced_penalty_per_item`| 1_000_000.0        | Strong incentive to place all      |
/// | `sheet_count_penalty_per_sheet` | 10_000.0      | Prefer fewer sheets                |
/// | `overlap_penalty_per_pair` | 1_000_000_000.0    | Validity guard — dominates all     |
/// | `boundary_penalty_per_item`| 1_000_000_000.0    | Validity guard — dominates all     |
/// | `compactness_weight`       | 0.001              | Tie-breaker, never overrides above |
#[derive(Debug, Clone)]
pub struct ScoreWeights {
    /// Reward per unit² of placed item area (contributes negative cost).
    pub placed_area_reward: f64,
    /// Penalty added per unplaced instance.
    pub unplaced_penalty_per_item: f64,
    /// Penalty per sheet index used (`max_sheet_index + 1`).
    pub sheet_count_penalty_per_sheet: f64,
    /// Penalty per overlapping placement pair detected by `find_violations`.
    pub overlap_penalty_per_pair: f64,
    /// Penalty per placement that is out-of-boundary or on an invalid sheet index.
    pub boundary_penalty_per_item: f64,
    /// Weight applied to the compactness proxy (bounding-rect gap per sheet).
    /// Must remain tiny so it never overrides validity or count penalties.
    pub compactness_weight: f64,
}

impl Default for ScoreWeights {
    fn default() -> Self {
        Self {
            placed_area_reward:               1.0,
            unplaced_penalty_per_item:        1_000_000.0,
            sheet_count_penalty_per_sheet:    10_000.0,
            overlap_penalty_per_pair:         1_000_000_000.0,
            boundary_penalty_per_item:        1_000_000_000.0,
            compactness_weight:               0.001,
        }
    }
}

// ---------------------------------------------------------------------------
// ObjectiveBreakdown and ScoreResult
// ---------------------------------------------------------------------------

/// Auditálható breakdown of all score components.
///
/// Each `_contribution` field carries the sign-corrected cost value:
/// - `placed_area_contribution` is **negative** (reward).
/// - All other contributions are **non-negative** (penalties).
/// - `total_cost = sum of all contributions`.
///
/// JG-19 additions:
/// - `sheet_cost_total`: sum of `cost_per_use` for each used sheet slot (1.0 per sheet by default).
/// - `sheet_count_contribution`: now equals `sheet_cost_total * sheet_count_penalty_per_sheet`
///   (backward-compat: default cost_per_use=1.0 → identical to old `sheet_count_used * weight`).
/// - `usable_area_utilization`: `placed_area / total usable area of used sheets` in [0, 1].
#[derive(Debug, Clone)]
pub struct ObjectiveBreakdown {
    pub placed_count: usize,
    pub unplaced_count: usize,
    pub sheet_count_used: usize,
    pub placed_area: f64,
    pub overlap_violations: usize,
    pub boundary_violations: usize,
    pub compactness_proxy: f64,
    /// Sum of cost_per_use for each used sheet slot (JG-19). Default: sheet_count_used * 1.0.
    pub sheet_cost_total: f64,
    /// placed_area / total usable area of used sheets (JG-19). 0.0 if no sheets used.
    pub usable_area_utilization: f64,
    pub placed_area_contribution: f64,
    pub unplaced_contribution: f64,
    /// Cost from sheet usage: sheet_cost_total * sheet_count_penalty_per_sheet (JG-19).
    pub sheet_count_contribution: f64,
    pub overlap_contribution: f64,
    pub boundary_contribution: f64,
    pub compactness_contribution: f64,
    pub total_cost: f64,
}

/// Result of a single score evaluation. Lower `total_cost` is better.
#[derive(Debug, Clone)]
pub struct ScoreResult {
    pub total_cost: f64,
    pub breakdown: ObjectiveBreakdown,
}

// ---------------------------------------------------------------------------
// ScoreModel
// ---------------------------------------------------------------------------

/// Phase 1 ScoreModel. Lower `total_cost` is better (minimization).
///
/// Operates directly on `Vec<Placement>` / `Vec<Unplaced>` — consistent with
/// the JG-10 repair engine. LayoutState conversion is not required for Phase 1
/// rectangular scoring; all needed geometry is recoverable from `io::Placement`
/// and `Part` dimensions via `bbox_from_placement`.
pub struct ScoreModel {
    pub weights: ScoreWeights,
}

impl ScoreModel {
    pub fn new(weights: ScoreWeights) -> Self {
        Self { weights }
    }

    /// Score a layout. Lower `total_cost` is better.
    pub fn score(
        &self,
        placements: &[Placement],
        unplaced: &[Unplaced],
        parts: &[Part],
        sheets: &[SheetShape],
    ) -> ScoreResult {
        score_layout(placements, unplaced, parts, sheets, &self.weights)
    }

    /// Returns `true` if `a` is strictly better (lower cost) than `b`.
    pub fn is_better(&self, a: &ScoreResult, b: &ScoreResult) -> bool {
        a.total_cost < b.total_cost
    }
}

impl Default for ScoreModel {
    fn default() -> Self {
        Self::new(ScoreWeights::default())
    }
}

// ---------------------------------------------------------------------------
// score_layout — core computation
// ---------------------------------------------------------------------------

/// Compute the full score for a layout. Lower `total_cost` is better.
///
/// Uses real Phase 1 helpers:
/// - `bbox_from_placement` to recover bounding boxes.
/// - `find_violations` (from `repair`) for overlap/boundary detection.
/// - `dims_for_rotation` for placed area calculation.
pub fn score_layout(
    placements: &[Placement],
    unplaced: &[Unplaced],
    parts: &[Part],
    sheets: &[SheetShape],
    weights: &ScoreWeights,
) -> ScoreResult {
    // --- Placed area + bboxes ---
    let mut placed_area = 0.0_f64;
    let mut placed_bboxes: Vec<PlacedBbox> = Vec::with_capacity(placements.len());
    for p in placements {
        if let Some(part) = parts.iter().find(|pt| pt.id == p.part_id) {
            if let Some((rw, rh)) = dims_for_rotation(part.width, part.height, p.rotation_deg) {
                placed_area += rw * rh;
            }
            if let Some(bb) = bbox_from_placement(p, part.width, part.height) {
                placed_bboxes.push(bb);
            }
        }
    }

    // --- Sheet count + sheet-cost (JG-19) ---
    let sheet_count_used = placements
        .iter()
        .map(|p| p.sheet_index)
        .max()
        .map(|v| v + 1)
        .unwrap_or(0);

    // Sum cost_per_use for each used sheet slot; also accumulate total usable area.
    let mut sheet_cost_total = 0.0_f64;
    let mut total_used_sheet_area = 0.0_f64;
    for sheet_idx in 0..sheet_count_used {
        if sheet_idx < sheets.len() {
            sheet_cost_total += sheets[sheet_idx].cost_per_use;
            total_used_sheet_area += sheets[sheet_idx].area;
        }
    }

    // --- Violations (overlap + boundary) via repair helper ---
    let violations = find_violations(placements, parts, sheets);
    let overlap_violations = violations
        .iter()
        .filter(|(_, v)| *v == ViolationType::Overlap)
        .count();
    let boundary_violations = violations
        .iter()
        .filter(|(_, v)| *v == ViolationType::BoundaryOrSheet)
        .count();

    // --- Compactness proxy ---
    // Per used sheet: bounding-rect area of all placed items minus their combined
    // placed area. Zero for a single item or perfectly packed items. Rewards
    // packing items closer together (smaller wasted envelope).
    let mut compactness_proxy = 0.0_f64;
    for sheet_idx in 0..sheet_count_used {
        let bbs: Vec<&PlacedBbox> = placed_bboxes
            .iter()
            .filter(|b| b.sheet_index == sheet_idx)
            .collect();
        if bbs.is_empty() {
            continue;
        }
        let min_x = bbs.iter().map(|b| b.x1).fold(f64::INFINITY, f64::min);
        let min_y = bbs.iter().map(|b| b.y1).fold(f64::INFINITY, f64::min);
        let max_x = bbs.iter().map(|b| b.x2).fold(f64::NEG_INFINITY, f64::max);
        let max_y = bbs.iter().map(|b| b.y2).fold(f64::NEG_INFINITY, f64::max);
        let bounding_area = (max_x - min_x) * (max_y - min_y);
        let item_area: f64 = bbs.iter().map(|b| (b.x2 - b.x1) * (b.y2 - b.y1)).sum();
        compactness_proxy += (bounding_area - item_area).max(0.0);
    }

    // --- Usable-area utilization (JG-19) ---
    let usable_area_utilization = if total_used_sheet_area > 0.0 {
        (placed_area / total_used_sheet_area).min(1.0)
    } else {
        0.0
    };

    // --- Contributions (all non-negative except placed_area which is a reward) ---
    let placed_area_contribution = -(placed_area * weights.placed_area_reward);
    let unplaced_contribution = unplaced.len() as f64 * weights.unplaced_penalty_per_item;
    // JG-19: sheet_count_contribution = sheet_cost_total * weight (not raw count * weight).
    // Backward-compat: default cost_per_use=1.0 → sheet_cost_total == sheet_count_used → same value.
    let sheet_count_contribution = sheet_cost_total * weights.sheet_count_penalty_per_sheet;
    let overlap_contribution = overlap_violations as f64 * weights.overlap_penalty_per_pair;
    let boundary_contribution = boundary_violations as f64 * weights.boundary_penalty_per_item;
    let compactness_contribution = compactness_proxy * weights.compactness_weight;

    let total_cost = placed_area_contribution
        + unplaced_contribution
        + sheet_count_contribution
        + overlap_contribution
        + boundary_contribution
        + compactness_contribution;

    ScoreResult {
        total_cost,
        breakdown: ObjectiveBreakdown {
            placed_count: placements.len(),
            unplaced_count: unplaced.len(),
            sheet_count_used,
            placed_area,
            overlap_violations,
            boundary_violations,
            compactness_proxy,
            sheet_cost_total,
            usable_area_utilization,
            placed_area_contribution,
            unplaced_contribution,
            sheet_count_contribution,
            overlap_contribution,
            boundary_contribution,
            compactness_contribution,
            total_cost,
        },
    }
}

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::io::Unplaced;
    use crate::sheet::{expand_sheets, Stock};

    fn make_part(id: &str, w: f64, h: f64) -> Part {
        crate::item::Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: 1,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: None,
            prepared_outer_points: None,
        }
    }

    fn make_sheets(w: f64, h: f64, count: usize) -> Vec<SheetShape> {
        let stocks: Vec<Stock> = (0..count)
            .map(|i| Stock {
                id: format!("S{i}"),
                quantity: 1,
                width: Some(w),
                height: Some(h),
                outer_points: None,
                holes_points: None,
                cost_per_use: None,
            })
            .collect();
        expand_sheets(&stocks).expect("sheets")
    }

    fn p(instance_id: &str, part_id: &str, sheet_index: usize, x: f64, y: f64) -> Placement {
        Placement {
            instance_id: instance_id.to_string(),
            part_id: part_id.to_string(),
            sheet_index,
            x,
            y,
            rotation_deg: 0,
        }
    }

    fn u(instance_id: &str, part_id: &str) -> Unplaced {
        Unplaced {
            instance_id: instance_id.to_string(),
            part_id: part_id.to_string(),
            reason: "NO_CAPACITY".to_string(),
        }
    }

    #[test]
    fn test_valid_layout_score_is_stable() {
        let parts = vec![make_part("A", 50.0, 50.0)];
        let sheets = make_sheets(200.0, 200.0, 1);
        let placements = vec![p("A__0001", "A", 0, 0.0, 0.0)];
        let model = ScoreModel::default();
        let r1 = model.score(&placements, &[], &parts, &sheets);
        let r2 = model.score(&placements, &[], &parts, &sheets);
        assert!((r1.total_cost - r2.total_cost).abs() < 1e-9);
        assert_eq!(r1.breakdown.overlap_violations, 0);
        assert_eq!(r1.breakdown.boundary_violations, 0);
        assert_eq!(r1.breakdown.placed_count, 1);
    }

    #[test]
    fn test_unplaced_item_increases_cost() {
        let parts = vec![make_part("A", 50.0, 50.0)];
        let sheets = make_sheets(200.0, 200.0, 1);
        let all_placed = vec![
            p("A__0001", "A", 0, 0.0, 0.0),
            p("A__0002", "A", 0, 60.0, 0.0),
        ];
        let partial = vec![p("A__0001", "A", 0, 0.0, 0.0)];
        let unplaced_one = vec![u("A__0002", "A")];
        let model = ScoreModel::default();
        let r_all = model.score(&all_placed, &[], &parts, &sheets);
        let r_partial = model.score(&partial, &unplaced_one, &parts, &sheets);
        assert!(
            r_partial.total_cost > r_all.total_cost,
            "unplaced item must worsen score"
        );
        assert_eq!(r_partial.breakdown.unplaced_count, 1);
    }

    #[test]
    fn test_more_sheets_increases_cost() {
        let parts = vec![make_part("A", 50.0, 50.0)];
        let sheets = make_sheets(200.0, 200.0, 2);
        let one_sheet = vec![
            p("A__0001", "A", 0, 0.0, 0.0),
            p("A__0002", "A", 0, 60.0, 0.0),
        ];
        let two_sheets = vec![
            p("A__0001", "A", 0, 0.0, 0.0),
            p("A__0002", "A", 1, 0.0, 0.0),
        ];
        let model = ScoreModel::default();
        let r_one = model.score(&one_sheet, &[], &parts, &sheets);
        let r_two = model.score(&two_sheets, &[], &parts, &sheets);
        assert!(r_two.total_cost > r_one.total_cost, "two sheets must cost more than one");
        assert_eq!(r_one.breakdown.sheet_count_used, 1);
        assert_eq!(r_two.breakdown.sheet_count_used, 2);
    }

    #[test]
    fn test_overlap_increases_cost_dramatically() {
        let parts = vec![make_part("A", 50.0, 50.0)];
        let sheets = make_sheets(200.0, 200.0, 1);
        let valid = vec![
            p("A__0001", "A", 0, 0.0, 0.0),
            p("A__0002", "A", 0, 60.0, 0.0),
        ];
        // Second item overlaps first (10,10 → bbox 10..60, 10..60 overlaps 0..50, 0..50)
        let overlapping = vec![
            p("A__0001", "A", 0, 0.0, 0.0),
            p("A__0002", "A", 0, 10.0, 10.0),
        ];
        let model = ScoreModel::default();
        let r_valid = model.score(&valid, &[], &parts, &sheets);
        let r_overlap = model.score(&overlapping, &[], &parts, &sheets);
        assert!(r_overlap.total_cost > r_valid.total_cost, "overlap must worsen score");
        assert!(r_overlap.breakdown.overlap_violations > 0, "overlap must be detected");
        assert!(
            r_overlap.breakdown.overlap_contribution >= 1_000_000_000.0,
            "overlap penalty is large"
        );
    }

    #[test]
    fn test_boundary_violation_increases_cost_dramatically() {
        let parts = vec![make_part("A", 50.0, 50.0)];
        let sheets = make_sheets(100.0, 100.0, 1);
        let valid = vec![p("A__0001", "A", 0, 0.0, 0.0)];
        // Item placed far outside sheet
        let oob = vec![p("A__0001", "A", 0, 200.0, 200.0)];
        let model = ScoreModel::default();
        let r_valid = model.score(&valid, &[], &parts, &sheets);
        let r_oob = model.score(&oob, &[], &parts, &sheets);
        assert!(r_oob.total_cost > r_valid.total_cost, "boundary violation must worsen score");
        assert!(r_oob.breakdown.boundary_violations > 0, "boundary violation must be detected");
        assert!(
            r_oob.breakdown.boundary_contribution >= 1_000_000_000.0,
            "boundary penalty is large"
        );
    }

    #[test]
    fn test_compactness_is_tiebreaker_only() {
        let parts = vec![make_part("A", 10.0, 10.0)];
        let sheets = make_sheets(200.0, 200.0, 1);
        // Compact: items adjacent (bounding rect = 20×10 = 200, item_area=200, proxy=0)
        let compact = vec![
            p("A__0001", "A", 0, 0.0, 0.0),
            p("A__0002", "A", 0, 10.0, 0.0),
        ];
        // Spread: items far apart (bounding rect = 190×190 = 36100, item_area=200, proxy=35900)
        let spread = vec![
            p("A__0001", "A", 0, 0.0, 0.0),
            p("A__0002", "A", 0, 180.0, 180.0),
        ];
        let model = ScoreModel::default();
        let r_compact = model.score(&compact, &[], &parts, &sheets);
        let r_spread = model.score(&spread, &[], &parts, &sheets);
        assert!(r_compact.total_cost < r_spread.total_cost, "compact must score better");
        // Difference is only from compactness: 35900 * 0.001 ≈ 35.9 — far below 1e6
        let diff = r_spread.total_cost - r_compact.total_cost;
        assert!(
            diff < 1_000.0,
            "compactness contribution is small (tiebreaker only): diff={diff}"
        );
    }

    #[test]
    fn test_deterministic_score() {
        let parts = vec![make_part("A", 40.0, 30.0), make_part("B", 20.0, 20.0)];
        let sheets = make_sheets(200.0, 200.0, 1);
        let placements = vec![
            p("A__0001", "A", 0, 0.0, 0.0),
            p("B__0001", "B", 0, 50.0, 0.0),
        ];
        let unplaced = vec![u("A__0002", "A")];
        let model = ScoreModel::default();
        let r1 = model.score(&placements, &unplaced, &parts, &sheets);
        let r2 = model.score(&placements, &unplaced, &parts, &sheets);
        assert_eq!(
            r1.total_cost.to_bits(),
            r2.total_cost.to_bits(),
            "score must be bit-identical across calls"
        );
    }

    #[test]
    fn test_is_better_lower_cost_wins() {
        let model = ScoreModel::default();
        let better = ScoreResult {
            total_cost: -500.0,
            breakdown: ObjectiveBreakdown {
                placed_count: 2,
                unplaced_count: 0,
                sheet_count_used: 1,
                placed_area: 500.0,
                overlap_violations: 0,
                boundary_violations: 0,
                compactness_proxy: 0.0,
                sheet_cost_total: 1.0,
                usable_area_utilization: 0.0,
                placed_area_contribution: -500.0,
                unplaced_contribution: 0.0,
                sheet_count_contribution: 0.0,
                overlap_contribution: 0.0,
                boundary_contribution: 0.0,
                compactness_contribution: 0.0,
                total_cost: -500.0,
            },
        };
        let worse = ScoreResult {
            total_cost: 1_000_000.0,
            breakdown: ObjectiveBreakdown {
                placed_count: 1,
                unplaced_count: 1,
                sheet_count_used: 1,
                placed_area: 250.0,
                overlap_violations: 0,
                boundary_violations: 0,
                compactness_proxy: 0.0,
                sheet_cost_total: 1.0,
                usable_area_utilization: 0.0,
                placed_area_contribution: -250.0,
                unplaced_contribution: 1_000_000.0,
                sheet_count_contribution: 0.0,
                overlap_contribution: 0.0,
                boundary_contribution: 0.0,
                compactness_contribution: 0.0,
                total_cost: 1_000_000.0,
            },
        };
        assert!(model.is_better(&better, &worse), "lower cost must be better");
        assert!(!model.is_better(&worse, &better), "higher cost must not be better");
    }

    // --- JG-19: remnant preference and usable-area utilization ---

    fn make_sheets_with_cost(w: f64, h: f64, costs: &[f64]) -> Vec<SheetShape> {
        let stocks: Vec<Stock> = costs
            .iter()
            .enumerate()
            .map(|(i, &c)| Stock {
                id: format!("S{i}"),
                quantity: 1,
                width: Some(w),
                height: Some(h),
                outer_points: None,
                holes_points: None,
                cost_per_use: Some(c),
            })
            .collect();
        expand_sheets(&stocks).expect("sheets")
    }

    #[test]
    fn test_remnant_preference_lower_cost_wins() {
        let parts = vec![make_part("A", 50.0, 50.0)];
        // Regular sheet: cost_per_use=1.0; remnant: cost_per_use=0.2
        let regular_sheets = make_sheets_with_cost(200.0, 200.0, &[1.0]);
        let remnant_sheets = make_sheets_with_cost(200.0, 200.0, &[0.2]);
        let placements = vec![p("A__0001", "A", 0, 0.0, 0.0)];
        let model = ScoreModel::default();
        let r_regular = model.score(&placements, &[], &parts, &regular_sheets);
        let r_remnant = model.score(&placements, &[], &parts, &remnant_sheets);
        assert!(
            r_remnant.total_cost < r_regular.total_cost,
            "remnant (cost=0.2) must score better than regular (cost=1.0): remnant={} regular={}",
            r_remnant.total_cost, r_regular.total_cost
        );
        assert!(
            (r_regular.breakdown.sheet_cost_total - 1.0).abs() < 1e-9,
            "regular sheet_cost_total must be 1.0"
        );
        assert!(
            (r_remnant.breakdown.sheet_cost_total - 0.2).abs() < 1e-9,
            "remnant sheet_cost_total must be 0.2"
        );
    }

    #[test]
    fn test_usable_area_utilization_computed() {
        let parts = vec![make_part("A", 50.0, 50.0)]; // area = 2500
        // Single 100×100 sheet (area=10000); place one 50×50 item → utilization = 2500/10000 = 0.25
        let sheets = make_sheets(100.0, 100.0, 1);
        let placements = vec![p("A__0001", "A", 0, 0.0, 0.0)];
        let model = ScoreModel::default();
        let r = model.score(&placements, &[], &parts, &sheets);
        assert!(
            (r.breakdown.usable_area_utilization - 0.25).abs() < 1e-9,
            "utilization must be 0.25 (2500/10000): got {}",
            r.breakdown.usable_area_utilization
        );
    }

    #[test]
    fn test_invalid_layout_dominates_over_remnant_benefit() {
        let parts = vec![make_part("A", 50.0, 50.0)];
        // Remnant sheet with very low cost; but placement is overlapping → overlap penalty dominates
        let remnant_sheets = make_sheets_with_cost(200.0, 200.0, &[0.001]);
        let valid_regular = vec![p("A__0001", "A", 0, 0.0, 0.0)];
        let overlapping_remnant = vec![
            p("A__0001", "A", 0, 0.0, 0.0),
            p("A__0002", "A", 0, 10.0, 10.0), // overlaps A__0001
        ];
        let regular_sheets = make_sheets_with_cost(200.0, 200.0, &[1.0]);
        let model = ScoreModel::default();
        let r_valid = model.score(&valid_regular, &[], &parts, &regular_sheets);
        let r_overlap = model.score(&overlapping_remnant, &[], &parts, &remnant_sheets);
        assert!(
            r_valid.total_cost < r_overlap.total_cost,
            "valid regular layout must beat overlapping remnant layout: valid={} overlap={}",
            r_valid.total_cost, r_overlap.total_cost
        );
        assert!(r_overlap.breakdown.overlap_violations > 0, "overlap must be detected");
    }

    #[test]
    fn test_backward_compat_default_cost_equals_sheet_count() {
        // Default cost_per_use=None (→1.0): sheet_cost_total must equal sheet_count_used.
        let parts = vec![make_part("A", 50.0, 50.0)];
        let sheets = make_sheets(200.0, 200.0, 2);
        let two_sheet_layout = vec![
            p("A__0001", "A", 0, 0.0, 0.0),
            p("A__0002", "A", 1, 0.0, 0.0),
        ];
        let model = ScoreModel::default();
        let r = model.score(&two_sheet_layout, &[], &parts, &sheets);
        assert_eq!(r.breakdown.sheet_count_used, 2);
        assert!(
            (r.breakdown.sheet_cost_total - 2.0).abs() < 1e-9,
            "default cost_per_use=1.0 → sheet_cost_total must equal sheet_count_used=2"
        );
        // Verify contribution is same as old formula: 2 * 10_000 = 20_000
        assert!(
            (r.breakdown.sheet_count_contribution - 2.0 * 10_000.0).abs() < 1e-9,
            "sheet_count_contribution backward compat"
        );
    }
}
