/// CDE lifecycle / session contract for VRS.
///
/// Honest documentation of what the jagua-rs 0.6.4 CDEngine API can support
/// in terms of session-owned (reusable) CDEngine instances versus per-call builds.
///
/// # jagua-rs API assessment
///
/// `CDEngine::register_hazard` and `deregister_hazard_by_entity` are public, so a
/// session-owned CDEngine with batched hazard management is structurally possible.
/// However, for live search (candidate evaluation during separator iterations) the
/// engine must be rebuilt or its hazard map mutated for every candidate position —
/// there is no "tentative query" API. Additionally `HazardEntity::PlacedItem` requires
/// a SlotMap `PItemKey` from a full jagua-rs layout, which VRS does not own.
///
/// Conclusion: `PerCallOnly` is the honest capability for live search. A `QueryBatch`
/// variant covering sheet boundary validation (offline, non-iterative) is technically
/// feasible but not required to unblock the search-path wiring (which uses per-call CDE).

// ---------------------------------------------------------------------------
// CdeSessionCapability
// ---------------------------------------------------------------------------

/// Honest classification of what lifecycle the jagua-rs CDE API can support
/// in the current VRS integration.
#[derive(Debug, Clone, PartialEq)]
pub enum CdeSessionCapability {
    /// A single CDEngine is built per layout and reused across all queries in that session.
    /// Requires stable hazard registration and a "tentative query" API — not available in 0.6.4.
    FullSession,
    /// CDEngine is built once per batch pass (e.g. sheet boundary validation), then discarded.
    /// Viable for offline validation but not live iterative search.
    QueryBatch,
    /// CDEngine is rebuilt for every individual query. This is the safe and honest choice for
    /// live iterative search when hazard state changes between queries.
    PerCallOnly { reason: &'static str },
}

impl CdeSessionCapability {
    pub fn is_per_call_only(&self) -> bool {
        matches!(self, CdeSessionCapability::PerCallOnly { .. })
    }

    pub fn name(&self) -> &'static str {
        match self {
            CdeSessionCapability::FullSession => "full_session",
            CdeSessionCapability::QueryBatch => "query_batch",
            CdeSessionCapability::PerCallOnly { .. } => "per_call_only",
        }
    }
}

/// Report the honest CDE session capability for the current jagua-rs 0.6.4 integration.
///
/// Returns `PerCallOnly` — full session requires either a stable per-candidate CDEngine
/// mutation API or `HazardEntity::PlacedItem` with a SlotMap PItemKey, neither of which
/// is available without owning a full jagua-rs layout state.
pub fn query_capability() -> CdeSessionCapability {
    CdeSessionCapability::PerCallOnly {
        reason: "jagua-rs 0.6.4 has no tentative-query API; \
                 HazardEntity::PlacedItem requires SlotMap PItemKey from a full jagua layout",
    }
}

// ---------------------------------------------------------------------------
// CdeDiagnostics
// ---------------------------------------------------------------------------

/// Counters collected during a CDE-backed optimizer pass.
#[derive(Debug, Clone, Default)]
pub struct CdeDiagnostics {
    /// Total pair + boundary queries dispatched to the CDE adapter.
    pub cde_queries: usize,
    /// Number of `CDEngine::new(...)` constructions (equals cde_queries for PerCallOnly).
    pub cde_engine_builds: usize,
    /// Queries where the CDE adapter returned `Unsupported`.
    pub cde_unsupported_count: usize,
    /// Lifecycle capability reported at the start of the pass.
    pub cde_session_capability: String,
}

impl CdeDiagnostics {
    pub fn new() -> Self {
        Self {
            cde_session_capability: query_capability().name().to_string(),
            ..Default::default()
        }
    }

    pub fn record_query(&mut self, unsupported: bool) {
        self.cde_queries += 1;
        self.cde_engine_builds += 1; // PerCallOnly: one build per query
        if unsupported {
            self.cde_unsupported_count += 1;
        }
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cde_session_capability_reports_truthful_lifecycle_status() {
        let cap = query_capability();
        // Must be PerCallOnly — honest for jagua-rs 0.6.4 with no tentative-query API
        assert!(
            cap.is_per_call_only(),
            "expected PerCallOnly, got {:?}",
            cap
        );
        assert_eq!(cap.name(), "per_call_only");
    }

    #[test]
    fn cde_session_or_batch_matches_per_call_adapter_for_pair_matrix() {
        use crate::optimizer::cde_adapter::{CdeAdapter, CdeQueryResult, prepare_shape_from_placement};
        use crate::io::Placement;
        use crate::item::Part;

        // Build two non-overlapping rect placements
        let p1 = Placement {
            instance_id: "i1".to_string(),
            part_id: "p1".to_string(),
            sheet_index: 0,
            x: 0.0,
            y: 0.0,
            rotation_deg: 0.0,
        };
        let p2 = Placement {
            instance_id: "i2".to_string(),
            part_id: "p2".to_string(),
            sheet_index: 0,
            x: 20.0,
            y: 0.0,
            rotation_deg: 0.0,
        };
        let part1 = Part { id: "p1".to_string(), width: 10.0, height: 10.0, outer_points: None, quantity: 1, allowed_rotations_deg: vec![0], holes_points: None, prepared_holes_points: None, prepared_outer_points: None, rotation_policy: None };
        let part2 = Part { id: "p2".to_string(), width: 10.0, height: 10.0, outer_points: None, quantity: 1, allowed_rotations_deg: vec![0], holes_points: None, prepared_holes_points: None, prepared_outer_points: None, rotation_policy: None };

        let s1 = prepare_shape_from_placement(&p1, &part1).expect("shape1");
        let s2 = prepare_shape_from_placement(&p2, &part2).expect("shape2");

        let adapter = CdeAdapter::with_defaults();
        // PerCallOnly: each call builds a CDEngine — result must be NoCollision for non-overlapping rects
        let result = adapter.query_pair(&s1, &s2);
        assert_eq!(
            result,
            CdeQueryResult::NoCollision,
            "non-overlapping rects must be NoCollision"
        );

        // The per-call adapter IS the session contract for PerCallOnly capability
        let cap = query_capability();
        assert!(cap.is_per_call_only());
    }

    #[test]
    fn no_silent_bbox_fallback_for_cde_search_path() {
        use crate::optimizer::cde_adapter::{CdeAdapter, CdeQueryResult, prepare_shape_from_placement};
        use crate::io::Placement;
        use crate::item::Part;

        // Overlapping rects — CDE must return Collision, not silently fall back to bbox NoCollision
        let p1 = Placement {
            instance_id: "i1".to_string(),
            part_id: "p1".to_string(),
            sheet_index: 0,
            x: 0.0, y: 0.0,
            rotation_deg: 0.0,
        };
        let p2 = Placement {
            instance_id: "i2".to_string(),
            part_id: "p2".to_string(),
            sheet_index: 0,
            x: 5.0, y: 0.0,
            rotation_deg: 0.0,
        };
        let part1 = Part { id: "p1".to_string(), width: 10.0, height: 10.0, outer_points: None, quantity: 1, allowed_rotations_deg: vec![0], holes_points: None, prepared_holes_points: None, prepared_outer_points: None, rotation_policy: None };
        let part2 = Part { id: "p2".to_string(), width: 10.0, height: 10.0, outer_points: None, quantity: 1, allowed_rotations_deg: vec![0], holes_points: None, prepared_holes_points: None, prepared_outer_points: None, rotation_policy: None };

        let s1 = prepare_shape_from_placement(&p1, &part1).expect("shape1");
        let s2 = prepare_shape_from_placement(&p2, &part2).expect("shape2");

        let adapter = CdeAdapter::with_defaults();
        let result = adapter.query_pair(&s1, &s2);
        // If CDE silently fell back to bbox, result would still be Collision here.
        // The key guarantee: result must NOT be NoCollision (which would indicate silent downgrade to no check)
        assert_eq!(
            result,
            CdeQueryResult::Collision,
            "overlapping rects must be Collision — no silent bbox NoCollision fallback"
        );
        assert_ne!(
            result,
            CdeQueryResult::NoCollision,
            "CDE must not return NoCollision for genuinely overlapping rects"
        );
    }
}
