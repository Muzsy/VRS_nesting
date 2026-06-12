//! SGH-Q32: Sparrow-native finite-stock heterogeneous multisheet manager.
//!
//! Production flow:
//!   `run_finite_stock_multisheet` →
//!     generate_sheet_subsets →
//!     for each subset: run_core_attempt →
//!       SparrowProblem::from_solver_input + SparrowOptimizer::solve →
//!       remap sheet indices →
//!       sanitize_if_infeasible →
//!       score_and_update_incumbent →
//!   return best incumbent
//!
//! Strict prohibitions (per canvas):
//! - No WorkingLayout / VrsCollisionTracker
//! - No legacy optimizer/multisheet.rs
//! - No Python multi_sheet_wrapper.py
//! - No compression
//! - Q31 base-shape cache must be preserved
//! - ok status only when final_pairs=0 AND boundary_violations=0
//! - partial status output must be collision-free (pairs=0, violations=0)

use super::*;
use crate::sheet::{expand_sheets, Stock};
use std::time::{Duration, Instant};

// ── Public config ────────────────────────────────────────────────────────────

/// Configuration for a finite-stock multisheet run.
pub struct FiniteStockRunConfig {
    pub time_limit_s: f64,
    pub seed: u64,
    pub backend: CollisionBackendKind,
    pub rotation_context: RotationResolveContext,
    /// SGH-Q34: margin-shrunk solver sheets. When Some, the Sparrow core uses these
    /// for collision/boundary checking while the original expanded sheets are kept
    /// for area reporting. Length must equal expand_sheets(stocks).
    pub solver_sheets_override: Option<Vec<SheetShape>>,
    /// SGH-Q36: part-part spacing (mm) for spacing-expanded collision geometry.
    /// `0.0` ⇒ no spacing geometry (unchanged solver path).
    pub spacing_mm: f64,
}

// ── Public result ────────────────────────────────────────────────────────────

/// Result of a finite-stock multisheet run. Always collision-free / boundary-safe.
pub struct FiniteStockRunResult {
    pub placements: Vec<Placement>,
    pub unplaced: Vec<Unplaced>,
    /// "ok" when all instances placed and collision-free; "partial" when some unplaced.
    pub status: String,
    /// True when all available stock was used and still not all parts placed.
    pub stock_exhausted: bool,
    /// Original expanded sheet indices that have at least one placement.
    pub used_sheet_indices: Vec<usize>,
    /// Sum of areas of unique used sheets (mm²).
    pub used_sheet_area: f64,
    /// Sum of part areas for placed instances (mm²).
    pub placed_part_area: f64,
    /// 100 * placed_part_area / used_sheet_area, 0.0 when no sheets used.
    pub utilization_pct: f64,
    pub total_instances: usize,
    pub placed_instances: usize,
    pub unplaced_instances: usize,
    /// How many core solver attempts were made.
    pub attempts: usize,
    /// Total candidate subsets generated.
    pub candidate_subsets: usize,
    /// True when at least one full feasible solution (all placed, pairs=0) was found.
    pub best_full_solution_found: bool,
    pub runtime_ms: f64,
    /// Configured time limit (seconds) passed in via FiniteStockRunConfig.
    pub time_limit_s: f64,
    /// True if the global deadline was reached before all subsets were tried.
    pub deadline_hit: bool,
    /// Best incumbent score (lower is better for feasible; for partial: covered area).
    pub best_score: f64,
    /// Diagnostics from the best core attempt.
    pub best_core_diag: Option<SparrowDiagnostics>,
    pub available_sheet_count: usize,
    pub final_pairs: usize,
    pub boundary_violations: usize,
}

// ── Internal incumbent ───────────────────────────────────────────────────────

struct Incumbent {
    placements: Vec<Placement>,
    unplaced: Vec<Unplaced>,
    feasible: bool,
    used_sheet_indices: Vec<usize>,
    used_sheet_area: f64,
    placed_part_area: f64,
    utilization_pct: f64,
    final_pairs: usize,
    boundary_violations: usize,
    score: f64,
    core_diag: SparrowDiagnostics,
}

/// Score a candidate: full feasible always beats partial.
/// Within the same type: smaller used_sheet_area is better, then higher utilization.
fn score_candidate(
    feasible: bool,
    placed_area: f64,
    used_area: f64,
    used_sheet_count: usize,
) -> f64 {
    if feasible {
        // Full feasible: small used_area is better → use used_area directly (lower = better)
        used_area + used_sheet_count as f64 * 1e-3
    } else {
        // Partial: more placed area is better → invert (lower score = better)
        // Offset by a large constant so partial always scores worse than feasible.
        1e15 - placed_area
    }
}

fn is_better_than(candidate: &Incumbent, incumbent: &Option<Incumbent>) -> bool {
    match incumbent {
        None => true,
        Some(inc) => {
            // Full feasible > partial
            if candidate.feasible && !inc.feasible {
                return true;
            }
            if !candidate.feasible && inc.feasible {
                return false;
            }
            candidate.score < inc.score
        }
    }
}

// ── Subset generation ────────────────────────────────────────────────────────

/// Generate candidate sheet subsets in order: smallest-area-sum first.
/// Returns Vec<Vec<usize>> where each inner vec is expanded sheet indices.
/// Always includes the full pool as the last entry.
fn generate_sheet_subsets(all_sheets: &[SheetShape], _seed: u64) -> Vec<Vec<usize>> {
    let n = all_sheets.len();
    if n == 0 {
        return vec![];
    }
    if n == 1 {
        return vec![vec![0]];
    }

    // For small pools (n <= 8), enumerate all non-empty subsets ordered by size then area.
    // For larger pools use greedy approach below.
    let mut subsets: Vec<Vec<usize>> = Vec::new();

    if n <= 8 {
        // All non-empty subsets
        for mask in 1u32..(1u32 << n) {
            let subset: Vec<usize> = (0..n).filter(|&i| (mask >> i) & 1 == 1).collect();
            subsets.push(subset);
        }
        // Sort: first by size (ascending), then by total area (ascending).
        subsets.sort_by(|a, b| {
            let area_a: f64 = a.iter().map(|&i| all_sheets[i].area).sum();
            let area_b: f64 = b.iter().map(|&i| all_sheets[i].area).sum();
            a.len()
                .cmp(&b.len())
                .then_with(|| area_a.partial_cmp(&area_b).unwrap_or(std::cmp::Ordering::Equal))
        });
    } else {
        // Greedy: add sheets from largest to smallest first (fit the biggest parts).
        // Start with single-sheet subsets (sorted by area descending — largest first).
        let mut order: Vec<usize> = (0..n).collect();
        order.sort_by(|&a, &b| {
            all_sheets[b]
                .area
                .partial_cmp(&all_sheets[a].area)
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        // Add single sheets
        for &i in &order {
            subsets.push(vec![i]);
        }
        // Add the full pool at the end
        let full: Vec<usize> = (0..n).collect();
        if !subsets.contains(&full) {
            subsets.push(full);
        }
    }

    // Deduplicate by sheet-dimension signature.
    // Two subsets are equivalent iff they have the same SORTED multiset of (width, height) pairs.
    // This avoids redundant attempts for homogeneous stock (e.g. 2×1500×3000 gives
    // subsets [0] and [1] which are identical), while preserving heterogeneous distinctions
    // (a 300×100 sheet and a 100×300 sheet have the same area but different shapes and are NOT equivalent).
    let mut seen_sigs: std::collections::HashSet<Vec<(u64, u64)>> =
        std::collections::HashSet::new();
    subsets.retain(|subset| {
        let mut dims: Vec<(u64, u64)> = subset
            .iter()
            .map(|&i| {
                (
                    all_sheets[i].width.to_bits(),
                    all_sheets[i].height.to_bits(),
                )
            })
            .collect();
        dims.sort();
        seen_sigs.insert(dims)
    });

    subsets
}

// ── Part area computation ────────────────────────────────────────────────────

/// Polygon area for a part using the shoelace formula on `outer_points`.
/// Falls back to bounding-box area (width×height) when `outer_points` is
/// absent, malformed, or has fewer than 3 vertices.
fn part_polygon_area(part: &crate::item::Part) -> f64 {
    let json_pts = part.outer_points.as_ref().or(part.prepared_outer_points.as_ref());
    if let Some(val) = json_pts {
        if let Some(arr) = val.as_array() {
            let pts: Vec<(f64, f64)> = arr
                .iter()
                .filter_map(|v| {
                    let pair = v.as_array()?;
                    if pair.len() >= 2 {
                        Some((pair[0].as_f64()?, pair[1].as_f64()?))
                    } else {
                        None
                    }
                })
                .collect();
            if pts.len() >= 3 {
                let n = pts.len();
                let mut signed = 0.0f64;
                for i in 0..n {
                    let j = (i + 1) % n;
                    signed += pts[i].0 * pts[j].1;
                    signed -= pts[j].0 * pts[i].1;
                }
                return (signed / 2.0).abs();
            }
        }
    }
    part.width * part.height
}

// ── Utilization ─────────────────────────────────────────────────────────────

/// Compute used sheet indices, used area, placed part area, and utilization pct.
/// `all_sheets` is the full expanded sheet list; `original_indices[i]` is the
/// original expanded index of all_sheets[i] (identity when no remapping needed).
fn compute_utilization(
    placements: &[Placement],
    parts: &[crate::item::Part],
    all_sheets_with_orig: &[(SheetShape, usize)], // (sheet, original_expanded_idx)
) -> (Vec<usize>, f64, f64, f64) {
    // Collect unique used original sheet indices.
    let mut used_orig: std::collections::BTreeSet<usize> = std::collections::BTreeSet::new();
    for pl in placements {
        used_orig.insert(pl.sheet_index);
    }
    let used_sheet_indices: Vec<usize> = used_orig.iter().cloned().collect();

    // Sum of areas of unique used sheets.
    let used_sheet_area: f64 = used_sheet_indices
        .iter()
        .map(|&orig_idx| {
            all_sheets_with_orig
                .iter()
                .find(|(_, oi)| *oi == orig_idx)
                .map(|(s, _)| s.area)
                .unwrap_or(0.0)
        })
        .sum();

    // Sum of placed part areas (polygon-based via shoelace formula).
    let placed_part_area: f64 = placements
        .iter()
        .map(|pl| {
            parts
                .iter()
                .find(|p| p.id == pl.part_id)
                .map(|p| part_polygon_area(p))
                .unwrap_or(0.0)
        })
        .sum();

    let utilization_pct = if used_sheet_area > 0.0 {
        100.0 * placed_part_area / used_sheet_area
    } else {
        0.0
    };

    (
        used_sheet_indices,
        used_sheet_area,
        placed_part_area,
        utilization_pct,
    )
}

/// SGH-Q35: recompute multisheet result aggregates after a safety net removed placements.
///
/// Keeps `used_sheet_*`, `placed_part_area`, `utilization_pct`, placed/unplaced instance
/// counts, `status`, and `best_full_solution_found` consistent with the (possibly reduced)
/// `placements`/`unplaced`. `original_sheets` are the physical expanded sheets (identity
/// index order), used for the physical `used_sheet_area`.
pub(crate) fn recompute_multisheet_result_after_safety_net(
    result: &mut FiniteStockRunResult,
    parts: &[crate::item::Part],
    original_sheets: &[SheetShape],
) {
    let all_sheets_with_orig: Vec<(SheetShape, usize)> = original_sheets
        .iter()
        .cloned()
        .enumerate()
        .map(|(i, s)| (s, i))
        .collect();
    let (used_idx, used_area, placed_area, util) =
        compute_utilization(&result.placements, parts, &all_sheets_with_orig);
    result.used_sheet_indices = used_idx;
    result.used_sheet_area = used_area;
    result.placed_part_area = placed_area;
    result.utilization_pct = util;
    result.placed_instances = result.placements.len();
    result.unplaced_instances = result.unplaced.len();
    result.status = if result.unplaced.is_empty() {
        "ok".to_string()
    } else {
        "partial".to_string()
    };
    if !result.unplaced.is_empty() {
        result.best_full_solution_found = false;
    }
}

// ── Partial sanitize ─────────────────────────────────────────────────────────

/// Unplaced reason assigned when a placement is removed to make the layout feasible.
const REASON_STOCK_EXHAUSTED_PARTIAL: &str = "STOCK_EXHAUSTED_PARTIAL";
const REASON_INSUFFICIENT_STOCK: &str = "INSUFFICIENT_STOCK_CAPACITY";
const REASON_UNRESOLVED: &str = "UNRESOLVED_AFTER_STOCK_EXHAUSTED";

/// Remove colliding/boundary-violating instances from a partial layout to produce
/// a collision-free, boundary-safe partial using greedy Maximum Independent Set.
///
/// Strategy:
/// 1. Build a SparrowCollisionTracker for all pairs and boundary violations.
/// 2. Exclude all boundary violators first.
/// 3. Greedy MIS on the conflict graph: sort remaining items by raw_loss ascending
///    (least conflicting = highest priority to keep). Include an item, exclude its
///    conflicting neighbours.
/// 4. Return (valid_placements, newly_unplaced).
///
/// This correctly handles the case of N parts on a sheet that can only hold K<N
/// (all N collide with each other): the greedy approach picks the K=1 best item
/// rather than removing everything via cluster-based two-pass logic.
fn sanitize_partial(
    layout: &SparrowLayout,
    instances: &[SPInstance],
    sheets: &[SheetShape],
    placements: &[Placement],
    reason: &str,
) -> (Vec<Placement>, Vec<Unplaced>) {
    if placements.is_empty() {
        return (vec![], vec![]);
    }

    let tracker = SparrowCollisionTracker::build(layout, instances, sheets);

    // Fast path: already feasible.
    if tracker.is_feasible() {
        return (placements.to_vec(), vec![]);
    }

    let n = layout.placements.len();

    // --- Build adjacency from pair collisions ---
    let mut adj: Vec<Vec<usize>> = vec![vec![]; n];
    for i in 0..n {
        for j in (i + 1)..n {
            if tracker.pair_loss(i, j) > 0.0 {
                adj[i].push(j);
                adj[j].push(i);
            }
        }
    }

    // --- Greedy MIS ---
    // First, mark boundary violators as excluded (they're outside the container).
    let mut excluded = vec![false; n];
    for i in 0..n {
        if tracker.container_loss(i) > 0.0 {
            excluded[i] = true;
        }
    }

    // Sort non-excluded items by raw_loss ascending: least conflicting = keep first.
    let mut order: Vec<usize> = (0..n).filter(|&i| !excluded[i]).collect();
    order.sort_by(|&a, &b| {
        tracker
            .item_raw_loss(a)
            .partial_cmp(&tracker.item_raw_loss(b))
            .unwrap_or(Ordering::Equal)
    });

    let mut included = vec![false; n];
    for &i in &order {
        if excluded[i] {
            continue;
        }
        included[i] = true;
        for &j in &adj[i] {
            excluded[j] = true;
        }
    }

    // --- Build result ---
    let mut valid_placements: Vec<Placement> = Vec::new();
    let mut newly_unplaced: Vec<Unplaced> = Vec::new();

    for (layout_idx, pl) in layout.placements.iter().enumerate() {
        let inst = &instances[pl.instance_idx];
        if included[layout_idx] {
            if let Some(vrs_pl) = placements.iter().find(|p| p.instance_id == inst.instance_id) {
                valid_placements.push(vrs_pl.clone());
            }
        } else {
            newly_unplaced.push(Unplaced {
                instance_id: inst.instance_id.clone(),
                part_id: inst.part_id.clone(),
                reason: reason.to_string(),
            });
        }
    }

    (valid_placements, newly_unplaced)
}

// ── Core attempt runner ──────────────────────────────────────────────────────

/// Run Sparrow core on a selected sheet subset, return placements with
/// subset-local sheet indices and the raw SparrowSolveResult.
fn run_core_attempt(
    parts: &[crate::item::Part],
    subset_sheets: &[SheetShape],
    rotation_context: &RotationResolveContext,
    pre_unplaced: Vec<Unplaced>,
    time_limit_s: f64,
    config: &FiniteStockRunConfig,
) -> SparrowSolveResult {
    let core_config = SparrowConfig::from_solver_input(
        time_limit_s.max(1.0),
        config.backend.clone(),
        rotation_context.clone(),
        config.seed,
    )
    .with_spacing_mm(config.spacing_mm);

    let problem = match SparrowProblem::from_solver_input(
        parts,
        subset_sheets,
        rotation_context,
        pre_unplaced,
        core_config.clone(),
    ) {
        Ok(p) => p,
        Err(_) => {
            // Cannot build problem — return empty result.
            let mut diag = SparrowDiagnostics::default();
            diag.invoked = false;
            return SparrowSolveResult {
                solution: SparrowSolution {
                    layout: SparrowLayout { placements: vec![] },
                    feasible: false,
                },
                placements: vec![],
                unplaced: vec![],
                feasible: false,
                diagnostics: diag,
            };
        }
    };

    let optimizer = SparrowOptimizer::new(core_config);
    optimizer.solve(problem)
}

// ── Main entry point ─────────────────────────────────────────────────────────

/// Run the finite-stock multisheet manager.
///
/// Takes all parts and the full stock list (with quantities). Generates candidate
/// sheet subsets, runs Sparrow core on each, and returns the best valid incumbent.
pub fn run_finite_stock_multisheet(
    parts: &[crate::item::Part],
    stocks: &[Stock],
    rotation_context: &RotationResolveContext,
    extra_pre_unplaced: Vec<Unplaced>,
    config: FiniteStockRunConfig,
) -> FiniteStockRunResult {
    let t_start = Instant::now();
    let deadline = t_start + Duration::from_secs_f64(config.time_limit_s.max(1.0));

    // Expand stocks → flat sheet list with original indices.
    let all_sheets = match expand_sheets(stocks) {
        Ok(s) => s,
        Err(e) => {
            let err_reason = format!("STOCK_BUILD_ERROR: {e}");
            return FiniteStockRunResult {
                placements: vec![],
                unplaced: parts
                    .iter()
                    .flat_map(|p| {
                        let reason = err_reason.clone();
                        (0..p.quantity as usize).map(move |i| Unplaced {
                            instance_id: format!("{}#{i}", p.id),
                            part_id: p.id.clone(),
                            reason: reason.clone(),
                        })
                    })
                    .chain(extra_pre_unplaced)
                    .collect(),
                status: "partial".to_string(),
                stock_exhausted: true,
                used_sheet_indices: vec![],
                used_sheet_area: 0.0,
                placed_part_area: 0.0,
                utilization_pct: 0.0,
                total_instances: parts.iter().map(|p| p.quantity as usize).sum(),
                placed_instances: 0,
                unplaced_instances: parts.iter().map(|p| p.quantity as usize).sum(),
                attempts: 0,
                candidate_subsets: 0,
                best_full_solution_found: false,
                runtime_ms: t_start.elapsed().as_secs_f64() * 1000.0,
                time_limit_s: config.time_limit_s,
                deadline_hit: false,
                best_score: f64::MAX,
                best_core_diag: None,
                available_sheet_count: 0,
                final_pairs: 0,
                boundary_violations: 0,
            };
        }
    };

    let available_sheet_count = all_sheets.len();
    // all_sheets_with_orig[i] = (SheetShape, original_expanded_index)
    // Since expand_sheets returns sheets in order without remapping, index == original index.
    let all_sheets_with_orig: Vec<(SheetShape, usize)> = all_sheets
        .iter()
        .cloned()
        .enumerate()
        .map(|(i, s)| (s, i))
        .collect();

    let total_instances: usize = parts.iter().map(|p| p.quantity as usize).sum();

    // Generate candidate subsets (sorted: smallest area first, full pool last).
    let subsets = generate_sheet_subsets(&all_sheets, config.seed);
    let candidate_subsets = subsets.len();

    let mut incumbent: Option<Incumbent> = None;
    let mut attempts = 0usize;
    let full_pool_idx = subsets.len().saturating_sub(1);

    // Time budget per subset: leave at least a fraction for later subsets.
    // We always try the smallest subsets first; once a full feasible is found
    // on a k-sheet subset we stop.
    for (subset_ord, subset_indices) in subsets.iter().enumerate() {
        let now = Instant::now();
        if now >= deadline {
            break;
        }
        let remaining_s = (deadline - now).as_secs_f64();
        // If we already have a full feasible solution and we've started on larger subsets, stop.
        if let Some(ref inc) = incumbent {
            if inc.feasible && subset_ord > 0 {
                let subset_size = subset_indices.len();
                // If current subset is at least as large as what already worked, skip.
                let incumbent_used = inc.used_sheet_indices.len();
                if subset_size >= incumbent_used {
                    break;
                }
            }
        }

        // Time allocation strategy (proportional to total budget and subset count):
        //
        // probe_cap  = min(30s, total / subsets / 2)  — keeps single-sheet probes short
        //              even with small total budgets (e.g. 30s in tests = 5s per probe).
        //
        // second-to-last multi-sheet (e.g. 2-of-3 for Case 02 gate "≤2 sheets"):
        //              50% of total budget, capped to leave probe_cap for the full pool.
        //              If it finds a full feasible solution, the loop breaks early and
        //              the full pool never runs — this is the desired behaviour.
        //
        // full pool:   remaining time minus FULL_POOL_GUARD_S.
        //              The Sparrow GLS checks the deadline at iteration START, so the
        //              last iteration can overrun by one iter time (~27s for LV8-dense).
        //              Per-attempt overhead (LBF seed + tracker init + final validation)
        //              adds ~39s for LV8-dense. I/O overhead outside sparrow_ms_runtime
        //              (JSON parse + output serialise) adds ~20s for LV8-dense.
        //              Together: GUARD ≥ 27+39+20-5 = 81s. Using 90s for 9s margin.
        const FULL_POOL_GUARD_S: f64 = 90.0;

        let probe_cap = (config.time_limit_s / candidate_subsets.max(1) as f64 / 2.0)
            .min(30.0)
            .max(5.0);
        let is_second_to_last = subset_ord + 1 == full_pool_idx;
        let attempt_time = if subset_ord == full_pool_idx {
            (remaining_s - FULL_POOL_GUARD_S).max(1.0)
        } else if is_second_to_last && subset_indices.len() > 1 {
            // Generous budget for the key multi-sheet candidate.
            let budget = (config.time_limit_s * 0.50)
                .min(remaining_s - probe_cap.max(10.0)) // always leave room for full pool
                .max(probe_cap);
            budget.min(remaining_s)
        } else {
            // Single-sheet probe or other small subset: brief.
            probe_cap.min(remaining_s)
        };

        // SGH-Q34: use margin-shrunk solver sheets for the core attempt when provided.
        // Original all_sheets are still used for area reporting (compute_utilization).
        let subset_sheets: Vec<SheetShape> = subset_indices
            .iter()
            .map(|&i| {
                if let Some(ref solver_override) = config.solver_sheets_override {
                    solver_override.get(i).cloned().unwrap_or_else(|| all_sheets[i].clone())
                } else {
                    all_sheets[i].clone()
                }
            })
            .collect();

        let result = run_core_attempt(
            parts,
            &subset_sheets,
            rotation_context,
            extra_pre_unplaced.clone(),
            attempt_time,
            &config,
        );
        attempts += 1;

        // Remap placement sheet_index from subset-local → original expanded index.
        // result.placements[k].sheet_index is an index into subset_sheets.
        // subset_indices[local_sheet_idx] is the original expanded sheet index.
        let remapped_placements: Vec<Placement> = result
            .placements
            .iter()
            .map(|pl| {
                let orig_sheet_idx = subset_indices
                    .get(pl.sheet_index)
                    .cloned()
                    .unwrap_or(pl.sheet_index);
                Placement {
                    sheet_index: orig_sheet_idx,
                    ..pl.clone()
                }
            })
            .collect();

        let is_core_feasible = result.feasible;
        let core_final_pairs = result.diagnostics.collision_graph_final_pairs;
        let core_boundary_viol = result.diagnostics.boundary_violations_final;

        // Determine validity of this result.
        let (valid_placements, mut extra_unplaced_this, final_pairs, boundary_violations) =
            if is_core_feasible {
                // Core says feasible: trust it.
                (remapped_placements, vec![], core_final_pairs, core_boundary_viol)
            } else if core_final_pairs > 0 || core_boundary_viol > 0 {
                // Core infeasible: sanitize to produce collision-free partial.
                let sanitize_reason = if subset_ord == full_pool_idx || attempts >= candidate_subsets {
                    REASON_STOCK_EXHAUSTED_PARTIAL
                } else {
                    REASON_INSUFFICIENT_STOCK
                };

                // Rebuild instances from SparrowSolveResult for the sanitize call.
                // We only have the subset_sheets here; build a minimal problem to get instances.
                let core_config = SparrowConfig::from_solver_input(
                    1.0,
                    config.backend.clone(),
                    rotation_context.clone(),
                    config.seed,
                )
                .with_spacing_mm(config.spacing_mm);
                let sanitize_placements;
                let sanitize_unplaced;

                match SparrowProblem::from_solver_input(
                    parts,
                    &subset_sheets,
                    rotation_context,
                    extra_pre_unplaced.clone(),
                    core_config,
                ) {
                    Ok(problem) => {
                        let (sp, su) = sanitize_partial(
                            &result.solution.layout,
                            &problem.instances,
                            &subset_sheets,
                            &result.placements,
                            sanitize_reason,
                        );
                        // Remap sanitized placements
                        sanitize_placements = sp
                            .into_iter()
                            .map(|pl| {
                                let orig_sheet_idx = subset_indices
                                    .get(pl.sheet_index)
                                    .cloned()
                                    .unwrap_or(pl.sheet_index);
                                Placement {
                                    sheet_index: orig_sheet_idx,
                                    ..pl
                                }
                            })
                            .collect();
                        sanitize_unplaced = su;
                    }
                    Err(_) => {
                        sanitize_placements = vec![];
                        sanitize_unplaced = remapped_placements
                            .iter()
                            .map(|pl| Unplaced {
                                instance_id: pl.instance_id.clone(),
                                part_id: pl.part_id.clone(),
                                reason: sanitize_reason.to_string(),
                            })
                            .collect();
                    }
                }
                (sanitize_placements, sanitize_unplaced, 0usize, 0usize)
            } else {
                // Core returned not-feasible but 0 pairs and 0 violations — means some
                // instances were put in pre_unplaced by the core (PART_NEVER_FITS_STOCK
                // or PART_GEOMETRY_UNSUPPORTED). Treat as valid partial.
                (remapped_placements, vec![], 0usize, 0usize)
            };

        // Merge unplaced from core + sanitize + pre_unplaced.
        let all_unplaced_this: Vec<Unplaced> = result
            .unplaced
            .into_iter()
            .chain(extra_unplaced_this.drain(..))
            .collect();

        let this_feasible =
            all_unplaced_this.is_empty() && final_pairs == 0 && boundary_violations == 0;

        let (used_indices, used_area, placed_area, util_pct) =
            compute_utilization(&valid_placements, parts, &all_sheets_with_orig);

        let score = score_candidate(
            this_feasible,
            placed_area,
            used_area,
            used_indices.len(),
        );

        let candidate = Incumbent {
            placements: valid_placements,
            unplaced: all_unplaced_this,
            feasible: this_feasible,
            used_sheet_indices: used_indices,
            used_sheet_area: used_area,
            placed_part_area: placed_area,
            utilization_pct: util_pct,
            final_pairs,
            boundary_violations,
            score,
            core_diag: result.diagnostics,
        };

        if is_better_than(&candidate, &incumbent) {
            incumbent = Some(candidate);
        }

        // If full feasible on a k-sheet subset, we found an optimal; stop early
        // unless we can still try smaller subsets.
        if this_feasible && subset_indices.len() <= 2 {
            // Already using ≤2 sheets and fully feasible — optimal for typical cases.
            break;
        }
    }

    // Determine if stock was exhausted (we ran the full pool and still partial).
    let stock_exhausted = match &incumbent {
        Some(inc) => !inc.feasible && attempts >= candidate_subsets,
        None => attempts >= candidate_subsets,
    };

    let runtime_ms = t_start.elapsed().as_secs_f64() * 1000.0;
    let deadline_hit = Instant::now() >= deadline;

    match incumbent {
        None => {
            // No successful attempt at all.
            let unplaced: Vec<Unplaced> = extra_pre_unplaced
                .into_iter()
                .chain(parts.iter().flat_map(|p| {
                    (0..p.quantity as usize).map(move |i| Unplaced {
                        instance_id: format!("{}#{i}", p.id),
                        part_id: p.id.clone(),
                        reason: REASON_UNRESOLVED.to_string(),
                    })
                }))
                .collect();
            let unplaced_count = unplaced.len();
            FiniteStockRunResult {
                placements: vec![],
                unplaced,
                status: "partial".to_string(),
                stock_exhausted: true,
                used_sheet_indices: vec![],
                used_sheet_area: 0.0,
                placed_part_area: 0.0,
                utilization_pct: 0.0,
                total_instances,
                placed_instances: 0,
                unplaced_instances: unplaced_count,
                attempts,
                candidate_subsets,
                best_full_solution_found: false,
                runtime_ms,
                time_limit_s: config.time_limit_s,
                deadline_hit,
                best_score: f64::MAX,
                best_core_diag: None,
                available_sheet_count,
                final_pairs: 0,
                boundary_violations: 0,
            }
        }
        Some(inc) => {
            let placed_instances = inc.placements.len();
            let unplaced_instances = inc.unplaced.len();
            let best_full = inc.feasible;
            let status = if inc.feasible { "ok" } else { "partial" }.to_string();
            FiniteStockRunResult {
                placements: inc.placements,
                unplaced: inc.unplaced,
                status,
                stock_exhausted,
                used_sheet_indices: inc.used_sheet_indices,
                used_sheet_area: inc.used_sheet_area,
                placed_part_area: inc.placed_part_area,
                utilization_pct: inc.utilization_pct,
                total_instances,
                placed_instances,
                unplaced_instances,
                attempts,
                candidate_subsets,
                best_full_solution_found: best_full,
                runtime_ms,
                time_limit_s: config.time_limit_s,
                deadline_hit,
                best_score: inc.score,
                best_core_diag: Some(inc.core_diag),
                available_sheet_count,
                final_pairs: inc.final_pairs,
                boundary_violations: inc.boundary_violations,
            }
        }
    }
}
