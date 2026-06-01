//! Thread-local CDE observability counters.
//!
//! Accumulates per-thread CDE query/call statistics. Thread-local storage
//! avoids race conditions under parallel `cargo test` runs.
//!
//! Usage pattern:
//! ```text
//! cde_observability::reset();          // before solve
//! // ... solve runs, CdeCollisionBackend increments counters ...
//! let snap = cde_observability::snapshot(); // after solve / final commit
//! ```

use std::cell::RefCell;

/// Accumulated CDE query/call counters for one solve scope.
#[derive(Debug, Default, Clone)]
pub struct CdeCounters {
    /// Item-vs-item pair collision queries dispatched to CDE.
    pub pair_queries: usize,
    /// Item-vs-sheet boundary queries dispatched to CDE.
    pub boundary_queries: usize,
    /// Total queries (pair_queries + boundary_queries).
    pub total_queries: usize,
    /// `CDEngine::new(...)` constructions. One per successful pair or boundary
    /// query that reaches the CDEngine stage (i.e. after prepare_shape succeeds).
    pub engine_builds: usize,
    /// Queries that returned `CollisionDecision::Collision`.
    pub collision_results: usize,
    /// Queries that returned `CollisionDecision::NoCollision`.
    pub no_collision_results: usize,
    /// Queries that returned `CollisionDecision::Unsupported`
    /// (includes prepare failures and CDE-internal unsupported).
    pub unsupported_results: usize,
    /// `prepare_shape_from_placement` failures (invalid/missing polygon data).
    pub prepare_failures: usize,
    /// Pair queries skipped because items are on different sheets.
    pub cross_sheet_skipped: usize,
    /// SGH-Q23: pair/boundary queries resolved as `NoCollision` by the AABB
    /// broad-phase pre-check WITHOUT building a `CDEngine`. AABB-separated shapes
    /// are provably non-colliding, so this skips the exact query and saves one
    /// engine build. Broad-phase NEVER produces positive collision truth.
    pub broadphase_pruned: usize,
    /// SGH-Q23R1 solve-scoped cache metrics. A cache hit returns a memoised
    /// CDE verdict (pure function of shapes+transforms) WITHOUT building a
    /// `CDEngine`. Hits are the primary engine-build reduction lever.
    pub cache_pair_hits: usize,
    pub cache_pair_misses: usize,
    pub cache_boundary_hits: usize,
    pub cache_boundary_misses: usize,
    pub cache_prepared_hits: usize,
    pub cache_prepared_misses: usize,
    /// Cache entries dropped because the solve-scoped cache exceeded its size cap
    /// (bounded-memory eviction). Transform-keyed entries are pure, so eviction
    /// only costs a recompute, never correctness.
    pub cache_invalidations: usize,
    /// SGH-Q23R2 single-engine multi-hazard batch candidate evaluation metrics.
    /// One `CDEngine` holds the sheet (Exterior) + all same-sheet fixed items
    /// (Hole hazards); a candidate is queried against it ONCE, replacing N
    /// pairwise `CDEngine::new` builds.
    pub batch_candidate_queries: usize,
    pub batch_engine_builds: usize,
    pub batch_hazards_registered: usize,
    pub batch_collisions_returned: usize,
    /// Pairwise CDE queries that still went through the per-pair path (broad-phase,
    /// tracker rebuild, jagua-exact backend) rather than the batch session.
    pub pairwise_fallback_queries: usize,
    /// SGH-Q24R1 per-target-search CDE session reuse. A `CdeCandidateSession` is
    /// cached by a fingerprint of the FIXED hazards (target + sheet + other
    /// placements); during one target's search all candidate evaluations reuse it
    /// instead of rebuilding. `candidate_session_builds` counts genuine builds,
    /// `candidate_session_reuses` counts fingerprint cache hits.
    pub candidate_session_builds: usize,
    pub candidate_session_reuses: usize,
}

thread_local! {
    static COUNTERS: RefCell<CdeCounters> = RefCell::new(CdeCounters::default());
}

/// Reset all counters to zero for this thread.
pub fn reset() {
    COUNTERS.with(|c| *c.borrow_mut() = CdeCounters::default());
}

/// Return a snapshot of the current counters for this thread.
pub fn snapshot() -> CdeCounters {
    COUNTERS.with(|c| c.borrow().clone())
}

pub(crate) fn inc_pair() {
    COUNTERS.with(|c| {
        let mut b = c.borrow_mut();
        b.pair_queries += 1;
        b.total_queries += 1;
    });
}

pub(crate) fn inc_boundary() {
    COUNTERS.with(|c| {
        let mut b = c.borrow_mut();
        b.boundary_queries += 1;
        b.total_queries += 1;
    });
}

pub(crate) fn inc_engine_build() {
    COUNTERS.with(|c| c.borrow_mut().engine_builds += 1);
}

pub(crate) fn inc_collision() {
    COUNTERS.with(|c| c.borrow_mut().collision_results += 1);
}

pub(crate) fn inc_no_collision() {
    COUNTERS.with(|c| c.borrow_mut().no_collision_results += 1);
}

pub(crate) fn inc_unsupported() {
    COUNTERS.with(|c| c.borrow_mut().unsupported_results += 1);
}

pub(crate) fn inc_prepare_failure() {
    COUNTERS.with(|c| c.borrow_mut().prepare_failures += 1);
}

pub(crate) fn inc_cross_sheet_skipped() {
    COUNTERS.with(|c| c.borrow_mut().cross_sheet_skipped += 1);
}

/// SGH-Q23: record an AABB broad-phase prune (NoCollision resolved without an
/// engine build). The result histogram (`no_collision_results`) is owned by the
/// backend caller (`placement_overlaps`), so this counts only the prune itself.
pub(crate) fn inc_broadphase_pruned() {
    COUNTERS.with(|c| c.borrow_mut().broadphase_pruned += 1);
}

// SGH-Q23R1 solve-scoped cache counters.
pub(crate) fn inc_cache_pair(hit: bool) {
    COUNTERS.with(|c| {
        let mut b = c.borrow_mut();
        if hit {
            b.cache_pair_hits += 1;
        } else {
            b.cache_pair_misses += 1;
        }
    });
}

pub(crate) fn inc_cache_boundary(hit: bool) {
    COUNTERS.with(|c| {
        let mut b = c.borrow_mut();
        if hit {
            b.cache_boundary_hits += 1;
        } else {
            b.cache_boundary_misses += 1;
        }
    });
}

pub(crate) fn inc_cache_prepared(hit: bool) {
    COUNTERS.with(|c| {
        let mut b = c.borrow_mut();
        if hit {
            b.cache_prepared_hits += 1;
        } else {
            b.cache_prepared_misses += 1;
        }
    });
}

pub(crate) fn add_cache_invalidations(n: usize) {
    COUNTERS.with(|c| c.borrow_mut().cache_invalidations += n);
}

// SGH-Q23R2 batch (single-engine multi-hazard) counters.
pub(crate) fn inc_batch_engine_build(hazards: usize) {
    COUNTERS.with(|c| {
        let mut b = c.borrow_mut();
        b.batch_engine_builds += 1;
        b.batch_hazards_registered += hazards;
    });
}

pub(crate) fn record_batch_query(collisions_returned: usize) {
    COUNTERS.with(|c| {
        let mut b = c.borrow_mut();
        b.batch_candidate_queries += 1;
        b.batch_collisions_returned += collisions_returned;
    });
}

pub(crate) fn inc_pairwise_fallback() {
    COUNTERS.with(|c| c.borrow_mut().pairwise_fallback_queries += 1);
}

pub(crate) fn inc_candidate_session(reused: bool) {
    COUNTERS.with(|c| {
        let mut b = c.borrow_mut();
        if reused {
            b.candidate_session_reuses += 1;
        } else {
            b.candidate_session_builds += 1;
        }
    });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cde_observability_counts_pair_and_boundary_queries() {
        reset();
        inc_pair();
        inc_pair();
        inc_boundary();
        let s = snapshot();
        assert_eq!(s.pair_queries, 2);
        assert_eq!(s.boundary_queries, 1);
        assert_eq!(s.total_queries, 3);
    }

    #[test]
    fn cde_observability_reports_engine_builds() {
        reset();
        inc_pair();
        inc_engine_build();
        inc_boundary();
        inc_engine_build();
        let s = snapshot();
        assert_eq!(s.engine_builds, 2);
    }

    #[test]
    fn cde_observability_reset_clears_all_fields() {
        reset();
        inc_pair();
        inc_boundary();
        inc_engine_build();
        inc_collision();
        inc_prepare_failure();
        inc_cross_sheet_skipped();
        reset();
        let s = snapshot();
        assert_eq!(s.pair_queries, 0);
        assert_eq!(s.boundary_queries, 0);
        assert_eq!(s.total_queries, 0);
        assert_eq!(s.engine_builds, 0);
        assert_eq!(s.collision_results, 0);
        assert_eq!(s.prepare_failures, 0);
        assert_eq!(s.cross_sheet_skipped, 0);
    }

    #[test]
    fn cde_observability_reports_no_bbox_fallback() {
        // CDE counters don't have a bbox_fallback field; absence is the proof.
        reset();
        inc_pair();
        inc_no_collision();
        let s = snapshot();
        // No bbox fallback counter in CdeCounters — by design.
        assert_eq!(s.total_queries, 1);
        assert_eq!(s.no_collision_results, 1);
        // unsupported_results and collision_results remain 0.
        assert_eq!(s.unsupported_results, 0);
        assert_eq!(s.collision_results, 0);
    }

    #[test]
    fn cde_observability_snapshot_is_independent_of_future_increments() {
        reset();
        inc_pair();
        let snap1 = snapshot();
        inc_pair();
        let snap2 = snapshot();
        assert_eq!(snap1.pair_queries, 1);
        assert_eq!(snap2.pair_queries, 2);
    }
}
