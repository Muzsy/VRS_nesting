//! SGH-Q58B: consume `SheetFeasibilityHints` (Q58A) to steer the critical-aware sheet builder.
//!
//! This module supplies the *decision pieces* the BPP/sheet-builder needs, behind an explicit gate
//! (`VRS_SHEET_FEASIBILITY_HINTS`): hint-aware critical queue ordering, per-sheet target quotas, a
//! hint-aware critical-phase frontier, and — most importantly — the **mandatory best-partial
//! preservation** incumbent, by construction making the "valid 2/3 → returned 1/3" regression class
//! impossible. Hints are advisory: every placement still passes exact validation upstream; this layer
//! only orders, quota-targets and preserves the best valid partial it is told about.

use super::*;

pub fn sheet_feasibility_hints_enabled() -> bool {
    std::env::var("VRS_SHEET_FEASIBILITY_HINTS").ok().as_deref() == Some("1")
}

/// A valid (already exact-validated upstream) partial critical layout on one sheet.
#[derive(Debug, Clone)]
pub struct CriticalIncumbent {
    pub critical_count: usize,
    pub placed_area: f64,
    pub free_space_score: f64,
    pub hint_target_met: bool,
    pub source: String,
}

impl CriticalIncumbent {
    /// Strict "is `self` better than `other`" ordering: more critical parts first, then hint-target
    /// satisfaction, then placed area, then free-space score. This is the comparison that makes a
    /// worse 1/N result unable to displace a better 2/N incumbent.
    pub fn is_better_than(&self, other: &CriticalIncumbent) -> bool {
        if self.critical_count != other.critical_count {
            return self.critical_count > other.critical_count;
        }
        if self.hint_target_met != other.hint_target_met {
            return self.hint_target_met && !other.hint_target_met;
        }
        if (self.placed_area - other.placed_area).abs() > 1e-6 {
            return self.placed_area > other.placed_area;
        }
        self.free_space_score > other.free_space_score
    }
}

/// Keeps the best valid critical partial seen for a sheet. Never downgrades.
#[derive(Debug, Clone, Default)]
pub struct BestPartialTracker {
    best: Option<CriticalIncumbent>,
    offers: usize,
    downgrades_rejected: usize,
}

impl BestPartialTracker {
    pub fn new() -> Self {
        Self::default()
    }

    /// Offer a newly found valid partial. Returns true iff it became the new incumbent.
    pub fn offer(&mut self, candidate: CriticalIncumbent) -> bool {
        self.offers += 1;
        match &self.best {
            None => {
                self.best = Some(candidate);
                true
            }
            Some(cur) => {
                if candidate.is_better_than(cur) {
                    self.best = Some(candidate);
                    true
                } else {
                    self.downgrades_rejected += 1;
                    false
                }
            }
        }
    }

    pub fn best(&self) -> Option<&CriticalIncumbent> {
        self.best.as_ref()
    }
    pub fn best_critical_count(&self) -> usize {
        self.best.as_ref().map(|b| b.critical_count).unwrap_or(0)
    }
    pub fn offers(&self) -> usize {
        self.offers
    }
    pub fn downgrades_rejected(&self) -> usize {
        self.downgrades_rejected
    }
}

/// Per-sheet target quota derived from the hints for one critical part type.
#[derive(Debug, Clone)]
pub struct SheetTargetQuota {
    pub part_id: String,
    pub target_per_sheet: usize,
    pub fallback_min_useful: usize,
    pub estimated_max_per_sheet: usize,
}

/// Build per-type target quotas from the Q58A hints (hint-aware, bounded). Quota never exceeds the
/// estimated max; the fallback minimum is the smallest useful partial worth preserving (>=1 when any
/// placement is plausible).
pub fn sheet_target_quotas(hints: &SheetFeasibilityHints) -> Vec<SheetTargetQuota> {
    hints
        .critical_part_type_hints
        .iter()
        .map(|c| SheetTargetQuota {
            part_id: c.part_id.clone(),
            target_per_sheet: c.target_per_sheet,
            fallback_min_useful: if c.estimated_max_per_sheet >= 1 { 1 } else { 0 },
            estimated_max_per_sheet: c.estimated_max_per_sheet,
        })
        .collect()
}

/// Hint-aware critical queue ordering: returns part ids ordered by a blended priority that combines the
/// existing `priority_score` family with hint signals (danger parts, low estimated max-per-sheet, high
/// repeated quantity). Pure; the caller applies it only when the gate is on (otherwise the legacy order
/// is reproduced byte-for-byte).
pub fn hint_aware_critical_order(hints: &SheetFeasibilityHints) -> Vec<String> {
    let danger: std::collections::HashMap<&str, f64> = hints
        .danger_parts
        .iter()
        .map(|d| (d.part_id.as_str(), d.fit_difficulty_score))
        .collect();
    let mut ids: Vec<(&CriticalPartTypeSheetHint, f64)> = hints
        .critical_part_type_hints
        .iter()
        .map(|c| {
            let danger_term = danger.get(c.part_id.as_str()).copied().unwrap_or(0.0);
            // Lower estimated max per sheet → harder → earlier. Larger quantity → earlier.
            let scarcity = 1.0 / (1.0 + c.estimated_max_per_sheet as f64);
            let qty_term = (c.quantity as f64 / 20.0).min(1.0);
            let key = 0.5 * danger_term + 0.3 * scarcity + 0.2 * qty_term;
            (c, key)
        })
        .collect();
    ids.sort_by(|a, b| {
        b.1.partial_cmp(&a.1)
            .unwrap_or(Ordering::Equal)
            .then_with(|| a.0.part_id.cmp(&b.0.part_id))
    });
    ids.into_iter().map(|(c, _)| c.part_id.clone()).collect()
}

/// Hint-aware critical-phase frontier: how many consecutive shallow failures to tolerate before closing
/// the critical phase. When the hint targets a higher per-sheet quota, allow more attempts (bounded).
pub fn hint_aware_frontier(base_frontier: usize, target_per_sheet: usize) -> usize {
    let extended = base_frontier.max(target_per_sheet.saturating_mul(2));
    extended.min(base_frontier + 8) // bounded: never unbounded retry
}

#[derive(Debug, Clone)]
pub struct SheetBuilderHintDiagnostics {
    pub hints_used: bool,
    pub target_critical_distribution: Vec<(String, Vec<usize>)>,
    pub sheet_target_quota: Vec<(String, usize)>,
    pub queue_reorder_applied: bool,
    pub frontier_extension_applied: bool,
}

pub fn build_hint_diagnostics(hints: &SheetFeasibilityHints, gate_on: bool) -> SheetBuilderHintDiagnostics {
    SheetBuilderHintDiagnostics {
        hints_used: gate_on,
        target_critical_distribution: hints
            .critical_part_type_hints
            .iter()
            .map(|c| (c.part_id.clone(), c.target_distribution.clone()))
            .collect(),
        sheet_target_quota: hints
            .critical_part_type_hints
            .iter()
            .map(|c| (c.part_id.clone(), c.target_per_sheet))
            .collect(),
        queue_reorder_applied: gate_on,
        frontier_extension_applied: gate_on
            && hints.critical_part_type_hints.iter().any(|c| c.target_per_sheet >= 2),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn inc(count: usize, area: f64, free: f64, target_met: bool) -> CriticalIncumbent {
        CriticalIncumbent {
            critical_count: count,
            placed_area: area,
            free_space_score: free,
            hint_target_met: target_met,
            source: "test".to_string(),
        }
    }

    #[test]
    fn best_partial_never_downgrades_two_to_one() {
        let mut t = BestPartialTracker::new();
        assert!(t.offer(inc(2, 1000.0, 50.0, false)), "first 2/3 becomes incumbent");
        // A valid 1-part result must NOT replace the held 2-part incumbent.
        assert!(!t.offer(inc(1, 2000.0, 99.0, true)), "1/3 must not displace 2/3");
        assert_eq!(t.best_critical_count(), 2, "incumbent stays at 2 critical parts");
        assert_eq!(t.downgrades_rejected(), 1);
    }

    #[test]
    fn best_partial_upgrades_two_to_three() {
        let mut t = BestPartialTracker::new();
        t.offer(inc(2, 1000.0, 50.0, false));
        assert!(t.offer(inc(3, 1500.0, 40.0, true)), "3/3 upgrades the incumbent");
        assert_eq!(t.best_critical_count(), 3);
    }

    #[test]
    fn equal_count_prefers_hint_target_then_area() {
        let mut t = BestPartialTracker::new();
        t.offer(inc(2, 1000.0, 50.0, false));
        assert!(t.offer(inc(2, 900.0, 10.0, true)), "same count but hint-target-met wins");
        assert!(t.best().unwrap().hint_target_met);
    }

    #[test]
    fn frontier_extension_is_bounded() {
        assert_eq!(hint_aware_frontier(4, 3), 6); // 3*2=6 > 4 → 6, within 4+8
        assert_eq!(hint_aware_frontier(4, 100), 12); // bounded to base+8
        assert_eq!(hint_aware_frontier(4, 1), 4); // no extension below base
    }
}
