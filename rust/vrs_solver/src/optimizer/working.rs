//! WorkingLayout — infeasible search state for the VRS separator migration.
//!
//! This type holds an in-progress layout that may temporarily contain colliding
//! or boundary-violating placements.  It is intentionally distinct from
//! `LayoutState` (internal post-commit state) and from `io::SolverOutput` (the
//! accepted JSON output contract).
//!
//! The only path from `WorkingLayout` to accepted output passes through
//! `validate_and_commit`, which calls `repair::find_violations` and rejects
//! any layout with violations.  There is no implicit conversion.

use crate::io::{CollisionBackendKind, Placement, Unplaced};
use crate::item::Part;
use crate::sheet::SheetShape;
use super::collision_backend::{BackendValidationDiagnostics, JaguaPolygonExactBackend};
use super::repair::{find_violations, validate_placements_with_backend_checked, ViolationType};

// ---------------------------------------------------------------------------
// Diagnostics and error
// ---------------------------------------------------------------------------

/// Violation counts produced by the commit gate.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct WorkingCommitDiagnostics {
    /// Total number of violations.
    pub violation_count: usize,
    /// Placements that overlap another placement on the same sheet.
    pub overlap_count: usize,
    /// Placements that are outside their sheet boundary or reference an invalid sheet.
    pub boundary_count: usize,
}

impl WorkingCommitDiagnostics {
    pub fn summary(&self) -> String {
        format!(
            "violations={} overlap={} boundary={}",
            self.violation_count, self.overlap_count, self.boundary_count
        )
    }
}

/// Error returned when `validate_and_commit`, `validate_for_commit`, or
/// `validate_and_commit_with_backend` finds violations or an unsupported backend query.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum WorkingCommitError {
    Violations(WorkingCommitDiagnostics),
    /// The selected backend returned Unsupported for one or more placement queries.
    /// For jagua_polygon_exact: invalid/missing exact geometry. For cde: always.
    UnsupportedBackend { reason: String, unsupported_queries: usize },
}

impl std::fmt::Display for WorkingCommitError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            WorkingCommitError::Violations(d) => write!(f, "commit blocked: {}", d.summary()),
            WorkingCommitError::UnsupportedBackend { reason, unsupported_queries } => {
                write!(f, "commit unsupported: {reason} (unsupported_queries={unsupported_queries})")
            }
        }
    }
}

/// Successful outcome from `validate_and_commit_with_backend`.
pub struct BackendCommitResult {
    pub placements: Vec<Placement>,
    pub unplaced: Vec<Unplaced>,
    pub backend_diagnostics: BackendValidationDiagnostics,
}

// ---------------------------------------------------------------------------
// WorkingLayout
// ---------------------------------------------------------------------------

/// In-progress layout that may temporarily contain overlapping or out-of-bounds
/// placements.
///
/// Rules:
/// - Storing a placement here does NOT validate it.  Violations are allowed.
/// - Call `validate_and_commit` to obtain accepted `(Vec<Placement>, Vec<Unplaced>)`.
///   This is the only valid path to committed output.
/// - `snapshot()` produces a full clone for rollback purposes.
/// - No field on this type implicitly converts to `LayoutState` or `SolverOutput`.
#[derive(Debug, Clone)]
pub struct WorkingLayout {
    pub placements: Vec<Placement>,
    pub unplaced: Vec<Unplaced>,
    /// Number of expanded sheet slots available (mirrors `LayoutState::sheet_count`).
    pub sheet_count: usize,
    /// RNG seed forwarded from input for determinism tracing.
    pub seed: i64,
}

impl WorkingLayout {
    pub fn new(
        placements: Vec<Placement>,
        unplaced: Vec<Unplaced>,
        sheet_count: usize,
        seed: i64,
    ) -> Self {
        Self { placements, unplaced, sheet_count, seed }
    }

    /// Full clone of the current state for snapshot / rollback.
    pub fn snapshot(&self) -> Self {
        self.clone()
    }

    /// Validate the current layout without consuming it.
    ///
    /// Returns `Ok(WorkingCommitDiagnostics { violation_count: 0, .. })` when the
    /// layout is violation-free.  Returns `Err(WorkingCommitError::Violations(_))`
    /// with per-type counts when any violation is found.
    pub fn validate_for_commit(
        &self,
        parts: &[Part],
        sheets: &[SheetShape],
    ) -> Result<WorkingCommitDiagnostics, WorkingCommitError> {
        let violations = find_violations(&self.placements, parts, sheets);
        if violations.is_empty() {
            return Ok(WorkingCommitDiagnostics::default());
        }
        let overlap_count = violations
            .iter()
            .filter(|(_, vt)| *vt == ViolationType::Overlap)
            .count();
        let boundary_count = violations
            .iter()
            .filter(|(_, vt)| *vt == ViolationType::BoundaryOrSheet)
            .count();
        Err(WorkingCommitError::Violations(WorkingCommitDiagnostics {
            violation_count: violations.len(),
            overlap_count,
            boundary_count,
        }))
    }

    /// Validate and, if valid, return the accepted `(placements, unplaced)` pair.
    ///
    /// Consumes `self`.  On success the caller may build `LayoutState` or
    /// `SolverOutput` from the returned vectors.  On failure the original data
    /// is lost — call `snapshot()` before `validate_and_commit` if rollback is
    /// needed.
    pub fn validate_and_commit(
        self,
        parts: &[Part],
        sheets: &[SheetShape],
    ) -> Result<(Vec<Placement>, Vec<Unplaced>), WorkingCommitError> {
        self.validate_for_commit(parts, sheets)?;
        Ok((self.placements, self.unplaced))
    }

    /// Total item count invariant: `placements.len() + unplaced.len()`.
    pub fn total_item_count(&self) -> usize {
        self.placements.len() + self.unplaced.len()
    }

    /// Backend-aware commit with explicit policy:
    ///
    /// - `Bbox`: identical behavior to `validate_and_commit` (pre-Q10 compatible).
    /// - `JaguaPolygonExact`: blocks if any placement yields Unsupported (invalid/missing exact
    ///   geometry) or has violations. No silent bbox fallback.
    /// - `Cde`: always returns `UnsupportedBackend` (CDE scaffold, not yet implemented).
    pub fn validate_and_commit_with_backend(
        self,
        parts: &[Part],
        sheets: &[SheetShape],
        backend_kind: CollisionBackendKind,
    ) -> Result<BackendCommitResult, WorkingCommitError> {
        match backend_kind {
            CollisionBackendKind::Bbox => {
                self.validate_for_commit(parts, sheets)?;
                Ok(BackendCommitResult {
                    placements: self.placements,
                    unplaced: self.unplaced,
                    backend_diagnostics: BackendValidationDiagnostics {
                        backend_name: "bbox".to_string(),
                        unsupported_queries: 0,
                        bbox_fallback_queries: 0,
                    },
                })
            }
            CollisionBackendKind::JaguaPolygonExact => {
                let result = validate_placements_with_backend_checked(
                    &self.placements,
                    parts,
                    sheets,
                    &JaguaPolygonExactBackend,
                );
                if result.diagnostics.unsupported_queries > 0 {
                    return Err(WorkingCommitError::UnsupportedBackend {
                        reason: "JAGUA_POLYGON_EXACT_UNSUPPORTED_QUERY".to_string(),
                        unsupported_queries: result.diagnostics.unsupported_queries,
                    });
                }
                if !result.violations.is_empty() {
                    let overlap_count = result
                        .violations
                        .iter()
                        .filter(|(_, vt)| *vt == ViolationType::Overlap)
                        .count();
                    let boundary_count = result
                        .violations
                        .iter()
                        .filter(|(_, vt)| *vt == ViolationType::BoundaryOrSheet)
                        .count();
                    return Err(WorkingCommitError::Violations(WorkingCommitDiagnostics {
                        violation_count: result.violations.len(),
                        overlap_count,
                        boundary_count,
                    }));
                }
                Ok(BackendCommitResult {
                    placements: self.placements,
                    unplaced: self.unplaced,
                    backend_diagnostics: result.diagnostics,
                })
            }
            CollisionBackendKind::Cde => {
                let placement_count = self.placements.len();
                Err(WorkingCommitError::UnsupportedBackend {
                    reason: "CDE_BACKEND_UNSUPPORTED".to_string(),
                    unsupported_queries: placement_count,
                })
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::item::expand_instances;
    use crate::optimizer::initializer::build_initial_layout;
    use crate::sheet::{expand_sheets, Stock};
    use crate::item::Part;

    // ── Helpers ──────────────────────────────────────────────────────────────

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

    /// Build a valid (violation-free) WorkingLayout using the real initializer.
    fn valid_working(
        parts: &[Part],
        stocks: &[Stock],
    ) -> (WorkingLayout, Vec<SheetShape>) {
        let instances = expand_instances(parts).expect("instances");
        let sheets = expand_sheets(stocks).expect("sheets");
        let (placed, unplaced, _) = build_initial_layout(&instances, parts, &sheets);
        let wl = WorkingLayout::new(placed, unplaced, sheets.len(), 0);
        (wl, sheets)
    }

    // ── 1. Overlapping placements can be stored ───────────────────────────────

    #[test]
    fn overlapping_placements_can_be_stored_in_working_layout() {
        let parts = vec![make_part("A", 30.0, 30.0, 2)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");

        // Two placements at the exact same position — an impossible overlap.
        let p1 = Placement { instance_id: "A__0001".into(), part_id: "A".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 };
        let p2 = Placement { instance_id: "A__0002".into(), part_id: "A".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 };

        // WorkingLayout stores them without any validation.
        let wl = WorkingLayout::new(vec![p1, p2], vec![], sheets.len(), 0);
        assert_eq!(wl.placements.len(), 2, "both overlapping placements must be stored");
        drop(sheets); // sheets was only needed for context; wl does not validate on new()
    }

    // ── 2. Overlap → commit error ─────────────────────────────────────────────

    #[test]
    fn overlap_commit_returns_error() {
        let parts = vec![make_part("A", 30.0, 30.0, 2)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");

        let (mut placed, unplaced, _) = build_initial_layout(&instances, &parts, &sheets);
        assert!(placed.len() >= 2);
        // Force overlap.
        placed[1].x = placed[0].x;
        placed[1].y = placed[0].y;

        let wl = WorkingLayout::new(placed, unplaced, sheets.len(), 0);
        let result = wl.validate_and_commit(&parts, &sheets);
        assert!(result.is_err(), "overlapping layout must not commit");
        let diag = match result.unwrap_err() {
            WorkingCommitError::Violations(d) => d,
            other => panic!("expected Violations error, got: {:?}", other),
        };
        assert!(diag.overlap_count > 0, "overlap_count must be non-zero");
        assert_eq!(diag.boundary_count, 0, "no boundary violations expected");
        assert_eq!(diag.violation_count, diag.overlap_count + diag.boundary_count);
    }

    // ── 3. Boundary violation → commit error ──────────────────────────────────

    #[test]
    fn boundary_violation_commit_returns_error() {
        let parts = vec![make_part("A", 30.0, 30.0, 1)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");

        let (mut placed, unplaced, _) = build_initial_layout(&instances, &parts, &sheets);
        assert!(!placed.is_empty());
        // Move item far outside the sheet.
        placed[0].x = 9999.0;
        placed[0].y = 9999.0;

        let wl = WorkingLayout::new(placed, unplaced, sheets.len(), 0);
        let result = wl.validate_and_commit(&parts, &sheets);
        assert!(result.is_err(), "out-of-boundary layout must not commit");
        let diag = match result.unwrap_err() {
            WorkingCommitError::Violations(d) => d,
            other => panic!("expected Violations error, got: {:?}", other),
        };
        assert!(diag.boundary_count > 0, "boundary_count must be non-zero");
        assert_eq!(diag.overlap_count, 0, "no overlap expected");
    }

    // ── 4. Valid layout commits successfully ──────────────────────────────────

    #[test]
    fn valid_layout_commits_successfully() {
        let parts = vec![make_part("A", 30.0, 30.0, 2)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let (wl, sheets) = valid_working(&parts, &stocks);
        let total = wl.total_item_count();

        let result = wl.validate_and_commit(&parts, &sheets);
        assert!(result.is_ok(), "valid layout must commit: {:?}", result);
        let (placed, unplaced) = result.unwrap();
        assert_eq!(placed.len() + unplaced.len(), total, "item count invariant preserved");
    }

    // ── 5. validate_for_commit on valid layout returns Ok(zero diag) ──────────

    #[test]
    fn validate_for_commit_returns_zero_diag_on_valid_layout() {
        let parts = vec![make_part("A", 30.0, 30.0, 2)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let (wl, sheets) = valid_working(&parts, &stocks);

        let result = wl.validate_for_commit(&parts, &sheets);
        assert!(result.is_ok());
        let diag = result.unwrap();
        assert_eq!(diag.violation_count, 0);
        assert_eq!(diag.overlap_count, 0);
        assert_eq!(diag.boundary_count, 0);
    }

    // ── 6. Snapshot / clone is deterministic ─────────────────────────────────

    #[test]
    fn snapshot_is_deterministic() {
        let parts = vec![make_part("A", 30.0, 30.0, 2)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let (wl, _sheets) = valid_working(&parts, &stocks);

        let snap = wl.snapshot();
        assert_eq!(wl.placements.len(), snap.placements.len());
        assert_eq!(wl.unplaced.len(), snap.unplaced.len());
        assert_eq!(wl.sheet_count, snap.sheet_count);
        assert_eq!(wl.seed, snap.seed);
        for (a, b) in wl.placements.iter().zip(snap.placements.iter()) {
            assert_eq!(a.instance_id, b.instance_id);
            assert_eq!(a.sheet_index, b.sheet_index);
            assert_eq!(a.x.to_bits(), b.x.to_bits());
            assert_eq!(a.y.to_bits(), b.y.to_bits());
            assert_eq!(a.rotation_deg, b.rotation_deg);
        }
    }

    #[test]
    fn snapshot_is_independent_of_original() {
        let parts = vec![make_part("A", 30.0, 30.0, 1)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let (mut wl, _sheets) = valid_working(&parts, &stocks);

        let snap = wl.snapshot();
        // Mutate original — snapshot must be unaffected.
        if !wl.placements.is_empty() {
            wl.placements[0].x = 99999.0;
        }
        if !snap.placements.is_empty() {
            assert_ne!(snap.placements[0].x.to_bits(), 99999.0_f64.to_bits(),
                "snapshot must be independent of original after mutation");
        }
    }

    // ── 7. Diagnostics correctly separate overlap vs boundary ─────────────────

    #[test]
    fn diagnostics_separate_overlap_and_boundary_counts() {
        let parts = vec![make_part("A", 30.0, 30.0, 3)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");

        // p0 valid at (0,0)
        let p0 = Placement { instance_id: "A__0001".into(), part_id: "A".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 };
        // p1 overlaps p0 (same position)
        let p1 = Placement { instance_id: "A__0002".into(), part_id: "A".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 };
        // p2 out of boundary
        let p2 = Placement { instance_id: "A__0003".into(), part_id: "A".into(), sheet_index: 0, x: 9999.0, y: 9999.0, rotation_deg: 0.0 };

        let wl = WorkingLayout::new(vec![p0, p1, p2], vec![], sheets.len(), 0);
        let diag = match wl.validate_for_commit(&parts, &sheets).unwrap_err() {
            WorkingCommitError::Violations(d) => d,
            other => panic!("expected Violations error, got: {:?}", other),
        };
        assert_eq!(diag.overlap_count, 1, "one overlap violation");
        assert_eq!(diag.boundary_count, 1, "one boundary violation");
        assert_eq!(diag.violation_count, 2, "total = overlap + boundary");
    }

    // ── 8. total_item_count invariant ────────────────────────────────────────

    #[test]
    fn total_item_count_matches_placed_plus_unplaced() {
        let parts = vec![make_part("A", 30.0, 30.0, 3)];
        let stocks = vec![make_stock("S", 60.0, 60.0, 1)];
        let (wl, _sheets) = valid_working(&parts, &stocks);
        assert_eq!(wl.total_item_count(), 3);
    }
}
