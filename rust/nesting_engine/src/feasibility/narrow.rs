use rstar::{RTree, RTreeObject, AABB};
use std::sync::OnceLock;
use std::time::Instant;

use crate::feasibility::aabb::{
    aabb_from_polygon, aabb_from_polygon64, aabb_inside, aabb_overlaps, Aabb,
};
use crate::geometry::{
    scale::TOUCH_TOL,
    types::{cross_product_i128, Point64, Polygon64},
};

// =============================================================================
// Narrow-phase strategy selection
// =============================================================================

/// NESTING_ENGINE_NARROW_PHASE values supported by this engine.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NarrowPhaseStrategy {
    /// Own hand-rolled polygon intersection (default).
    Own,
    /// i_overlay PredicateOverlay-based alternative.
    IOverlay,
    /// GEOS PreparedGeometry (optional, compiled only with geos_narrow_phase feature).
    #[cfg(feature = "geos_narrow_phase")]
    Geos,
}

impl Default for NarrowPhaseStrategy {
    fn default() -> Self {
        NarrowPhaseStrategy::Own
    }
}

impl NarrowPhaseStrategy {
    /// Parse from NESTING_ENGINE_NARROW_PHASE env var.
    /// Invalid values return Ok(NarrowPhaseStrategy::Own) with a warning.
    pub fn from_env() -> Self {
        match std::env::var("NESTING_ENGINE_NARROW_PHASE")
            .as_deref()
            .map(str::trim)
        {
            Ok("own") => NarrowPhaseStrategy::Own,
            Ok("i_overlay") => NarrowPhaseStrategy::IOverlay,
            #[cfg(feature = "geos_narrow_phase")]
            Ok("geos") => NarrowPhaseStrategy::Geos,
            Ok(other) => {
                eprintln!(
                    "[NARROW_PHASE] unknown strategy '{}', defaulting to 'own'",
                    other
                );
                NarrowPhaseStrategy::Own
            }
            Err(_) => NarrowPhaseStrategy::Own,
        }
    }

    /// Human-readable name for stats output.
    pub fn as_str(&self) -> &'static str {
        match self {
            NarrowPhaseStrategy::Own => "own",
            NarrowPhaseStrategy::IOverlay => "i_overlay",
            #[cfg(feature = "geos_narrow_phase")]
            NarrowPhaseStrategy::Geos => "geos",
        }
    }
}

// T06o: Cache the narrow-phase strategy for the lifetime of the process.
// Avoids paying a `std::env::var()` lookup on every dispatcher call (potentially
// hundreds of thousands of times per nfp_place run). The env var is read exactly
// once, at the first call site reached. Subsequent in-process env mutations are
// not observed — matches the prior implicit contract (strategy never changed
// mid-run in any production path).
static NARROW_PHASE_STRATEGY_CACHE: OnceLock<NarrowPhaseStrategy> = OnceLock::new();

/// Returns the narrow-phase strategy resolved from the environment, cached.
#[inline]
pub fn cached_narrow_phase_strategy() -> NarrowPhaseStrategy {
    *NARROW_PHASE_STRATEGY_CACHE.get_or_init(NarrowPhaseStrategy::from_env)
}

// =============================================================================
// GEOS feature gate — stubs when geos_narrow_phase is not compiled
// =============================================================================

#[cfg(not(feature = "geos_narrow_phase"))]
mod geos_narrow_phase {
    use super::Polygon64;

    /// Always returns false — GEOS not compiled.
    pub fn polygons_intersect_or_touch_geos(
        _a: &Polygon64,
        _b: &Polygon64,
    ) -> bool {
        false
    }

    pub fn is_available() -> bool {
        false
    }
}

#[cfg(feature = "geos_narrow_phase")]
mod geos_narrow_phase {
    use super::Polygon64;

    pub fn is_available() -> bool {
        true
    }

    pub fn polygons_intersect_or_touch_geos(a: &Polygon64, b: &Polygon64) -> bool {
        // Placeholder — actual GEOS implementation would go here
        // when geos_narrow_phase feature is enabled
        let _ = (a, b);
        false
    }
}

// =============================================================================
// i_overlay narrow-phase implementation
// =============================================================================

pub mod i_overlay_narrow {
    use super::*;
    use i_overlay::core::overlay::ShapeType;
    use i_overlay::core::relate::PredicateOverlay;

    // ---------------------------------------------------------------------
    // Coordinate encoding for i_overlay int precision
    // ---------------------------------------------------------------------

    /// Encode two polygons into shared i32 coordinate space for i_overlay.
    /// Returns (shape_a, shape_b) in i_overlay format or None on overflow.
    fn encode_pair(
        a: &Polygon64,
        b: &Polygon64,
    ) -> Option<(
        i_overlay::i_shape::int::shape::IntShape,
        i_overlay::i_shape::int::shape::IntShape,
    )> {
        
        use i_overlay::i_shape::int::shape::{IntContour, IntShape};

        // Compute bounding box of both polygons (all rings)
        let mut min_x = i64::MAX;
        let mut min_y = i64::MAX;
        let mut max_x = i64::MIN;
        let mut max_y = i64::MIN;

        for poly in [a, b] {
            for &pt in &poly.outer {
                min_x = min_x.min(pt.x);
                min_y = min_y.min(pt.y);
                max_x = max_x.max(pt.x);
                max_y = max_y.max(pt.y);
            }
            for hole in &poly.holes {
                for &pt in hole {
                    min_x = min_x.min(pt.x);
                    min_y = min_y.min(pt.y);
                    max_x = max_x.max(pt.x);
                    max_y = max_y.max(pt.y);
                }
            }
        }

        if min_x == i64::MAX {
            return None;
        }

        // Compute scale/shift to fit into i32 range.
        // Allow some headroom; i32::MAX ≈ 2.1e9, and coordinates are in micrometers.
        // For sheet sizes up to several meters (millions of µm), shift=0 works fine.
        // For very large coordinates, fall back to conservative collision.
        let span_x = max_x.checked_sub(min_x)?;
        let span_y = max_y.checked_sub(min_y)?;
        let max_span = span_x.max(span_y);

        // If the coordinate range exceeds i32 by too much, fall back conservatively.
        if max_span > i32::MAX as i64 {
            return None;
        }

        let shift = if max_span > i32::MAX as i64 { 1 } else { 0 };

        fn encode_ring(
            ring: &[Point64],
            min_x: i64,
            min_y: i64,
            shift: u32,
        ) -> Option<IntContour> {
            use i_overlay::i_float::int::point::IntPoint;
            let mut contour = Vec::with_capacity(ring.len());
            for pt in ring {
                let tx = (pt.x - min_x) >> shift;
                let ty = (pt.y - min_y) >> shift;
                let x = i32::try_from(tx).ok()?;
                let y = i32::try_from(ty).ok()?;
                contour.push(IntPoint::new(x, y));
            }
            Some(contour)
        }

        fn encode_poly(poly: &Polygon64, min_x: i64, min_y: i64, shift: u32) -> Option<IntShape> {
            let mut shape: IntShape = Vec::with_capacity(1 + poly.holes.len());
            shape.push(encode_ring(&poly.outer, min_x, min_y, shift)?);
            for hole in &poly.holes {
                shape.push(encode_ring(hole, min_x, min_y, shift)?);
            }
            Some(shape)
        }

        let shape_a = encode_poly(a, min_x, min_y, shift)?;
        let shape_b = encode_poly(b, min_x, min_y, shift)?;
        Some((shape_a, shape_b))
    }

    /// Returns true if two polygons intersect or touch, using i_overlay PredicateOverlay.
    /// Falls back conservatively (returns true) on any conversion/encoding error.
    pub fn polygons_intersect_or_touch_i_overlay(a: &Polygon64, b: &Polygon64) -> bool {
        // Fast path: try encoding, fall back to own on error
        let (shape_a, shape_b) = match encode_pair(a, b) {
            Some(pair) => pair,
            None => return true, // conservative: treat as collision
        };

        // predicate_overlay_capacity: number of vertices as rough estimate
        let cap_a: usize = shape_a.iter().map(|c| c.len()).sum();
        let cap_b = shape_b.iter().map(|c| c.len()).sum();
        let capacity = cap_a.max(cap_b).max(16);

        let mut overlay = PredicateOverlay::new(capacity);
        overlay.add_shape(&shape_a, ShapeType::Subject);
        overlay.add_shape(&shape_b, ShapeType::Clip);

        // intersects() includes boundary contact = collision in our semantics
        overlay.intersects()
    }
}

// =============================================================================
// Core narrow-phase functions
// =============================================================================

#[derive(Debug, Clone)]
pub struct PlacedPart {
    pub inflated_polygon: Polygon64,
    pub aabb: Aabb,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum PointLocation {
    Outside,
    Inside,
    OnBoundary,
}

#[derive(Debug, Clone, Copy)]
struct PlacedPartEnvelope {
    idx: usize,
    aabb: Aabb,
}

impl RTreeObject for PlacedPartEnvelope {
    type Envelope = AABB<[i64; 2]>;

    fn envelope(&self) -> Self::Envelope {
        AABB::from_corners(
            [self.aabb.min_x, self.aabb.min_y],
            [self.aabb.max_x, self.aabb.max_y],
        )
    }
}

/// T06p #4: Per-placed-part cached geometry used by the narrow-phase to skip
/// edge-AABB recomputation and to scan rings of A only against the edges of
/// ring B whose x-range can possibly overlap (binary search on a sorted
/// permutation by `min_x`). Built once at insertion; immutable thereafter.
#[derive(Debug, Clone, Default)]
pub struct PlacedPartCache {
    /// Per-ring flat edge AABBs (one entry per edge of that ring).
    pub edge_aabbs_per_ring: Vec<Vec<Aabb>>,
    /// Per-ring permutation: edge indices sorted ascending by `min_x`.
    pub edges_sorted_by_min_x_per_ring: Vec<Vec<u32>>,
}

impl PlacedPartCache {
    fn from_polygon(poly: &Polygon64) -> Self {
        let mut edge_aabbs_per_ring: Vec<Vec<Aabb>> = Vec::with_capacity(1 + poly.holes.len());
        for ring in polygon_rings(poly) {
            let n = ring.len();
            let mut aabbs = Vec::with_capacity(n);
            for i in 0..n {
                let a0 = ring[i];
                let a1 = ring[(i + 1) % n];
                aabbs.push(Aabb {
                    min_x: a0.x.min(a1.x),
                    min_y: a0.y.min(a1.y),
                    max_x: a0.x.max(a1.x),
                    max_y: a0.y.max(a1.y),
                });
            }
            edge_aabbs_per_ring.push(aabbs);
        }
        let edges_sorted_by_min_x_per_ring: Vec<Vec<u32>> = edge_aabbs_per_ring
            .iter()
            .map(|aabbs| {
                let mut indices: Vec<u32> = (0..aabbs.len() as u32).collect();
                indices.sort_unstable_by_key(|&i| aabbs[i as usize].min_x);
                indices
            })
            .collect();
        Self {
            edge_aabbs_per_ring,
            edges_sorted_by_min_x_per_ring,
        }
    }
}

#[derive(Debug, Clone, Default)]
pub struct PlacedIndex {
    parts: Vec<PlacedPart>,
    caches: Vec<PlacedPartCache>,
    tree: RTree<PlacedPartEnvelope>,
}

impl PlacedIndex {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn insert(&mut self, part: PlacedPart) {
        let idx = self.parts.len();
        let aabb = part.aabb;
        let cache = PlacedPartCache::from_polygon(&part.inflated_polygon);
        self.parts.push(part);
        self.caches.push(cache);
        self.tree.insert(PlacedPartEnvelope { idx, aabb });
    }

    pub fn query_overlaps(&self, aabb: &Aabb) -> Vec<usize> {
        let envelope = AABB::from_corners(
            [
                aabb.min_x.saturating_sub(TOUCH_TOL),
                aabb.min_y.saturating_sub(TOUCH_TOL),
            ],
            [
                aabb.max_x.saturating_add(TOUCH_TOL),
                aabb.max_y.saturating_add(TOUCH_TOL),
            ],
        );
        self.tree
            .locate_in_envelope_intersecting(&envelope)
            .map(|entry| entry.idx)
            .collect()
    }

    pub fn get(&self, idx: usize) -> &PlacedPart {
        &self.parts[idx]
    }

    pub fn get_cache(&self, idx: usize) -> &PlacedPartCache {
        &self.caches[idx]
    }
}

/// T06o: Per-call counters for the own narrow-phase. Tracks budget vs actual
/// segment-pair work and edge-AABB pre-rejects. Default-zeroed; only populated
/// when the profiled path is taken.
#[derive(Debug, Default, Clone, Copy)]
pub struct NarrowPhaseCounters {
    /// Upper-bound: sum of ring_a.len() * ring_b.len() for every ring pair
    /// that the inner loop entered (no early ring-pair short-circuit and no
    /// ring-level AABB pre-reject — T06p).
    pub segment_pair_budget: u64,
    /// Actual `segments_intersect_or_touch()` invocations — i.e. edge pairs
    /// that survived the AABB pre-reject.
    pub segment_pair_actual: u64,
    /// Edge pairs that the AABB pre-reject excluded before any orientation
    /// arithmetic ran.
    pub edge_bbox_rejects: u64,
    /// T06p: Ring-pairs eliminated by the ring-level AABB pre-reject (never
    /// entered the inner edge loop). Each entry would otherwise have produced
    /// `ring_a.len() * ring_b.len()` budget worth of edge-pair work.
    pub ring_bbox_rejects: u64,
}

impl NarrowPhaseCounters {
    #[inline]
    pub fn add(&mut self, other: &NarrowPhaseCounters) {
        self.segment_pair_budget = self
            .segment_pair_budget
            .saturating_add(other.segment_pair_budget);
        self.segment_pair_actual = self
            .segment_pair_actual
            .saturating_add(other.segment_pair_actual);
        self.edge_bbox_rejects = self
            .edge_bbox_rejects
            .saturating_add(other.edge_bbox_rejects);
        self.ring_bbox_rejects = self
            .ring_bbox_rejects
            .saturating_add(other.ring_bbox_rejects);
    }
}

/// Internal counter sink — the inner narrow-phase routine is generic over this
/// trait so that the no-counter path monomorphizes to zero overhead.
///
/// `COUNTS` is a compile-time flag: when `false`, the inner function may take
/// fast-paths that bypass per-segment-pair counting (e.g. the T06p #3 convex
/// SAT short-circuit).
trait NarrowPhaseCounterSink {
    const COUNTS: bool;
    fn add_budget(&mut self, n: u64);
    fn add_actual(&mut self, n: u64);
    fn add_bbox_reject(&mut self, n: u64);
    fn add_ring_bbox_reject(&mut self, n: u64);
}

struct NoNarrowPhaseCounter;

impl NarrowPhaseCounterSink for NoNarrowPhaseCounter {
    const COUNTS: bool = false;
    #[inline(always)]
    fn add_budget(&mut self, _n: u64) {}
    #[inline(always)]
    fn add_actual(&mut self, _n: u64) {}
    #[inline(always)]
    fn add_bbox_reject(&mut self, _n: u64) {}
    #[inline(always)]
    fn add_ring_bbox_reject(&mut self, _n: u64) {}
}

impl NarrowPhaseCounterSink for NarrowPhaseCounters {
    const COUNTS: bool = true;
    #[inline]
    fn add_budget(&mut self, n: u64) {
        self.segment_pair_budget = self.segment_pair_budget.saturating_add(n);
    }
    #[inline]
    fn add_actual(&mut self, n: u64) {
        self.segment_pair_actual = self.segment_pair_actual.saturating_add(n);
    }
    #[inline]
    fn add_bbox_reject(&mut self, n: u64) {
        self.edge_bbox_rejects = self.edge_bbox_rejects.saturating_add(n);
    }
    #[inline]
    fn add_ring_bbox_reject(&mut self, n: u64) {
        self.ring_bbox_rejects = self.ring_bbox_rejects.saturating_add(n);
    }
}

/// T06p: Exact integer AABB disjoint test for two rings. Strict `<` (matching
/// `segment_aabb_disjoint`) — touching AABBs are NOT pre-rejected because the
/// touch policy treats boundary contact as collision.
#[inline]
fn ring_aabb_disjoint(a: &Aabb, b: &Aabb) -> bool {
    a.max_x < b.min_x || b.max_x < a.min_x || a.max_y < b.min_y || b.max_y < a.min_y
}

/// T06p #3: Detect whether a closed ring is convex (every interior turn has
/// the same sign). Collinear triples are skipped. Empty / degenerate rings
/// return false. Cost is O(N) and integer-only.
fn is_convex_ring(ring: &[Point64]) -> bool {
    let n = ring.len();
    if n < 3 {
        return false;
    }
    let mut sign: i8 = 0;
    for i in 0..n {
        let a = ring[i];
        let b = ring[(i + 1) % n];
        let c = ring[(i + 2) % n];
        let cross = cross_product_i128(b.x - a.x, b.y - a.y, c.x - b.x, c.y - b.y);
        let s = if cross > 0 {
            1
        } else if cross < 0 {
            -1
        } else {
            0
        };
        if s == 0 {
            continue; // collinear triple — does not break convexity
        }
        if sign == 0 {
            sign = s;
        } else if sign != s {
            return false;
        }
    }
    sign != 0
}

/// T06p #3: Separating-axis check for two convex rings. Strict-< gap on a
/// candidate axis is required (matches the touch policy: contact = collision,
/// so projections that exactly meet must NOT be reported as separating).
/// Returns `true` if a separating axis is found (i.e. the rings do NOT
/// collide or touch).
fn convex_rings_have_separating_axis(a: &[Point64], b: &[Point64]) -> bool {
    fn project_on_normal(ring: &[Point64], nx: i64, ny: i64) -> (i128, i128) {
        let p0 = ring[0];
        let mut min = (p0.x as i128) * (nx as i128) + (p0.y as i128) * (ny as i128);
        let mut max = min;
        for p in &ring[1..] {
            let v = (p.x as i128) * (nx as i128) + (p.y as i128) * (ny as i128);
            if v < min {
                min = v;
            }
            if v > max {
                max = v;
            }
        }
        (min, max)
    }
    fn check(edges_owner: &[Point64], other: &[Point64]) -> bool {
        let n = edges_owner.len();
        for i in 0..n {
            let p1 = edges_owner[i];
            let p2 = edges_owner[(i + 1) % n];
            // Outward normal: (p2 - p1) rotated 90° CW = (dy, -dx).
            let nx = p2.y - p1.y;
            let ny = -(p2.x - p1.x);
            if nx == 0 && ny == 0 {
                continue;
            }
            let (a_min, a_max) = project_on_normal(edges_owner, nx, ny);
            let (b_min, b_max) = project_on_normal(other, nx, ny);
            if a_max < b_min || b_max < a_min {
                return true;
            }
        }
        false
    }
    check(a, b) || check(b, a)
}

/// T06p #2: Flat-storage precomputed edge AABBs for a polygon. One `Vec<Aabb>`
/// holds every edge AABB across every ring (outer + holes). `offsets` gives
/// start indices: ring r's edges live in `edges[offsets[r]..offsets[r+1]]`.
/// This layout has better cache locality than `Vec<Vec<Aabb>>` and only two
/// allocations per call regardless of the ring count.
struct PolyEdgeAabbs {
    edges: Vec<Aabb>,
    offsets: Vec<usize>,
}

impl PolyEdgeAabbs {
    #[inline]
    fn ring(&self, r: usize) -> &[Aabb] {
        &self.edges[self.offsets[r]..self.offsets[r + 1]]
    }
}

fn precompute_poly_edge_aabbs(poly: &Polygon64) -> PolyEdgeAabbs {
    let total_edges: usize = polygon_rings(poly).map(|r| r.len()).sum();
    let ring_count = 1 + poly.holes.len();
    let mut edges = Vec::with_capacity(total_edges);
    let mut offsets = Vec::with_capacity(ring_count + 1);
    offsets.push(0);
    for ring in polygon_rings(poly) {
        let n = ring.len();
        for i in 0..n {
            let a0 = ring[i];
            let a1 = ring[(i + 1) % n];
            edges.push(Aabb {
                min_x: a0.x.min(a1.x),
                min_y: a0.y.min(a1.y),
                max_x: a0.x.max(a1.x),
                max_y: a0.y.max(a1.y),
            });
        }
        offsets.push(edges.len());
    }
    PolyEdgeAabbs { edges, offsets }
}

/// T06o: Exact integer AABB disjoint test for two segments.
///
/// Returns true iff the AABBs of segments `(a0,a1)` and `(b0,b1)` are strictly
/// separated on at least one axis. The strict `<` (not `<=`) is **required**:
/// touching boundaries (edge/corner contact) must NOT be pre-rejected, because
/// the touch-policy treats boundary contact as collision.
#[inline]
fn segment_aabb_disjoint(a0: Point64, a1: Point64, b0: Point64, b1: Point64) -> bool {
    let a_min_x = a0.x.min(a1.x);
    let a_max_x = a0.x.max(a1.x);
    let a_min_y = a0.y.min(a1.y);
    let a_max_y = a0.y.max(a1.y);

    let b_min_x = b0.x.min(b1.x);
    let b_max_x = b0.x.max(b1.x);
    let b_min_y = b0.y.min(b1.y);
    let b_max_y = b0.y.max(b1.y);

    a_max_x < b_min_x || b_max_x < a_min_x || a_max_y < b_min_y || b_max_y < a_min_y
}

/// Returns true if two polygons intersect or touch.
/// This is the OWN strategy implementation (no profiling counters).
pub fn own_polygons_intersect_or_touch(a: &Polygon64, b: &Polygon64) -> bool {
    own_polygons_intersect_or_touch_inner(a, b, &mut NoNarrowPhaseCounter)
}

/// Profiled variant of `own_polygons_intersect_or_touch` that fills `counters`
/// with budget / actual segment-pair counts and edge-AABB rejects. Boolean
/// return value is bit-for-bit identical to the non-counted variant.
pub fn own_polygons_intersect_or_touch_counted(
    a: &Polygon64,
    b: &Polygon64,
    counters: &mut NarrowPhaseCounters,
) -> bool {
    own_polygons_intersect_or_touch_inner(a, b, counters)
}

/// T06p #4: Hot-path variant of `own_polygons_intersect_or_touch` that uses
/// precomputed `PlacedPartCache` for the placed-side polygon `b`. Compared to
/// the on-the-fly variant this:
///   - avoids recomputing every b-edge AABB on every can_place call;
///   - uses a per-ring permutation of b's edges sorted by `min_x` to skip
///     entire prefixes of edges that cannot overlap a's edge on the x-axis.
/// Boolean result is bit-for-bit identical to `own_polygons_intersect_or_touch`.
pub fn own_polygons_intersect_or_touch_against_cached(
    a: &Polygon64,
    b: &Polygon64,
    b_cache: &PlacedPartCache,
) -> bool {
    own_polygons_intersect_or_touch_against_cached_inner(
        a, b, b_cache, &mut NoNarrowPhaseCounter,
    )
}

/// Counted variant of `own_polygons_intersect_or_touch_against_cached`.
pub fn own_polygons_intersect_or_touch_against_cached_counted(
    a: &Polygon64,
    b: &Polygon64,
    b_cache: &PlacedPartCache,
    counters: &mut NarrowPhaseCounters,
) -> bool {
    own_polygons_intersect_or_touch_against_cached_inner(a, b, b_cache, counters)
}

#[inline(always)]
fn own_polygons_intersect_or_touch_against_cached_inner<C: NarrowPhaseCounterSink>(
    a: &Polygon64,
    b: &Polygon64,
    b_cache: &PlacedPartCache,
    counters: &mut C,
) -> bool {
    if !polygon_has_valid_rings(a) || !polygon_has_valid_rings(b) {
        return true;
    }

    // T06p #3: Convex SAT fast-path (same gating as the non-cached variant).
    if !C::COUNTS
        && a.holes.is_empty()
        && b.holes.is_empty()
        && is_convex_ring(&a.outer)
        && is_convex_ring(&b.outer)
    {
        return !convex_rings_have_separating_axis(&a.outer, &b.outer);
    }

    // Ring AABBs (cheap, on-the-fly).
    let a_ring_aabbs: Vec<Aabb> = polygon_rings(a).map(aabb_from_polygon).collect();
    let b_ring_aabbs: Vec<Aabb> = polygon_rings(b).map(aabb_from_polygon).collect();

    // For very small polygon-pairs the cache + binary-search overhead loses
    // to the simple inline AABB loop. Match the same threshold as the
    // non-cached inner function so behavior stays predictable.
    let a_total_edges: usize = polygon_rings(a).map(|r| r.len()).sum();
    let b_total_edges: usize = b_cache
        .edge_aabbs_per_ring
        .iter()
        .map(Vec::len)
        .sum::<usize>();
    const EDGE_CACHE_THRESHOLD: usize = 16;
    let use_cache = a_total_edges + b_total_edges > EDGE_CACHE_THRESHOLD;

    if use_cache {
        let a_edges = precompute_poly_edge_aabbs(a);
        for (ri, (ring_a, a_aabb)) in polygon_rings(a).zip(&a_ring_aabbs).enumerate() {
            for (rj, (ring_b, b_aabb)) in polygon_rings(b).zip(&b_ring_aabbs).enumerate() {
                if ring_aabb_disjoint(a_aabb, b_aabb) {
                    counters.add_ring_bbox_reject(1);
                    continue;
                }
                if ring_intersects_ring_or_touch_sorted_b(
                    ring_a,
                    a_edges.ring(ri),
                    ring_b,
                    &b_cache.edge_aabbs_per_ring[rj],
                    &b_cache.edges_sorted_by_min_x_per_ring[rj],
                    counters,
                ) {
                    return true;
                }
            }
        }
    } else {
        for (ring_a, a_aabb) in polygon_rings(a).zip(&a_ring_aabbs) {
            for (ring_b, b_aabb) in polygon_rings(b).zip(&b_ring_aabbs) {
                if ring_aabb_disjoint(a_aabb, b_aabb) {
                    counters.add_ring_bbox_reject(1);
                    continue;
                }
                if ring_intersects_ring_or_touch_inner(ring_a, ring_b, counters) {
                    return true;
                }
            }
        }
    }

    point_in_polygon(a.outer[0], b) != PointLocation::Outside
        || point_in_polygon(b.outer[0], a) != PointLocation::Outside
}

#[inline(always)]
fn own_polygons_intersect_or_touch_inner<C: NarrowPhaseCounterSink>(
    a: &Polygon64,
    b: &Polygon64,
    counters: &mut C,
) -> bool {
    if !polygon_has_valid_rings(a) || !polygon_has_valid_rings(b) {
        return true;
    }

    // T06p #3: Convex SAT fast-path. Only fires on the NON-counted hot path
    // (`C::COUNTS == false`) and only when both polygons are hole-free AND
    // have a convex outer ring. For convex hole-free polygons under our
    // touch policy "no strict-< separating axis" is exactly "overlap or
    // touch", which IS our collision predicate. The counted/profiled path
    // stays on the edge loop so segment_pair stats remain populated for
    // audit invariants.
    if !C::COUNTS
        && a.holes.is_empty()
        && b.holes.is_empty()
        && is_convex_ring(&a.outer)
        && is_convex_ring(&b.outer)
    {
        return !convex_rings_have_separating_axis(&a.outer, &b.outer);
    }

    // T06p #1: precompute ring AABBs once per polygon-pair invocation.
    let a_ring_aabbs: Vec<Aabb> = polygon_rings(a).map(aabb_from_polygon).collect();
    let b_ring_aabbs: Vec<Aabb> = polygon_rings(b).map(aabb_from_polygon).collect();

    // T06p #2: precompute per-edge AABBs only when the polygons are rich
    // enough that the cache pays back its allocation cost. For ≤16 total
    // edges (e.g. rectangle-vs-rectangle) the inline AABB path wins.
    let a_total_edges: usize = polygon_rings(a).map(|r| r.len()).sum();
    let b_total_edges: usize = polygon_rings(b).map(|r| r.len()).sum();
    const EDGE_CACHE_THRESHOLD: usize = 16;
    let use_edge_cache = a_total_edges + b_total_edges > EDGE_CACHE_THRESHOLD;

    if use_edge_cache {
        let a_edges = precompute_poly_edge_aabbs(a);
        let b_edges = precompute_poly_edge_aabbs(b);
        for (ri, (ring_a, a_aabb)) in polygon_rings(a).zip(&a_ring_aabbs).enumerate() {
            for (rj, (ring_b, b_aabb)) in polygon_rings(b).zip(&b_ring_aabbs).enumerate() {
                if ring_aabb_disjoint(a_aabb, b_aabb) {
                    counters.add_ring_bbox_reject(1);
                    continue;
                }
                if ring_intersects_ring_or_touch_with_cached_aabbs(
                    ring_a,
                    a_edges.ring(ri),
                    ring_b,
                    b_edges.ring(rj),
                    counters,
                ) {
                    return true;
                }
            }
        }
    } else {
        for (ring_a, a_aabb) in polygon_rings(a).zip(&a_ring_aabbs) {
            for (ring_b, b_aabb) in polygon_rings(b).zip(&b_ring_aabbs) {
                if ring_aabb_disjoint(a_aabb, b_aabb) {
                    counters.add_ring_bbox_reject(1);
                    continue;
                }
                if ring_intersects_ring_or_touch_inner(ring_a, ring_b, counters) {
                    return true;
                }
            }
        }
    }

    point_in_polygon(a.outer[0], b) != PointLocation::Outside
        || point_in_polygon(b.outer[0], a) != PointLocation::Outside
}

/// Returns true if two polygons intersect or touch, using the active strategy.
pub fn polygons_intersect_or_touch(a: &Polygon64, b: &Polygon64) -> bool {
    match cached_narrow_phase_strategy() {
        NarrowPhaseStrategy::Own => own_polygons_intersect_or_touch(a, b),
        NarrowPhaseStrategy::IOverlay => {
            i_overlay_narrow::polygons_intersect_or_touch_i_overlay(a, b)
        }
        #[cfg(feature = "geos_narrow_phase")]
        NarrowPhaseStrategy::Geos => geos_narrow_phase::polygons_intersect_or_touch_geos(a, b),
    }
}

pub fn can_place(candidate: &Polygon64, bin: &Polygon64, placed: &PlacedIndex) -> bool {
    if !polygon_has_valid_rings(candidate) || !polygon_has_valid_rings(bin) {
        return false;
    }

    let candidate_aabb = aabb_from_polygon64(candidate);
    let bin_aabb = aabb_from_polygon64(bin);
    if !aabb_inside(&bin_aabb, &candidate_aabb) {
        return false;
    }

    if !poly_strictly_within(candidate, bin) {
        return false;
    }

    let mut maybe_overlap: Vec<(usize, &PlacedPart)> = placed
        .query_overlaps(&candidate_aabb)
        .into_iter()
        .map(|idx| (idx, placed.get(idx)))
        .filter(|(_, p)| aabb_overlaps(&candidate_aabb, &p.aabb))
        .collect();
    if maybe_overlap.is_empty() {
        return true;
    }

    // Deterministic narrow-phase order for reproducibility.
    maybe_overlap.sort_by(|a, b| {
        a.1.aabb
            .min_x
            .cmp(&b.1.aabb.min_x)
            .then(a.1.aabb.min_y.cmp(&b.1.aabb.min_y))
            .then(a.1.aabb.max_x.cmp(&b.1.aabb.max_x))
            .then(a.1.aabb.max_y.cmp(&b.1.aabb.max_y))
            .then(a.0.cmp(&b.0))
    });

    // T06p #4: route Own strategy through the cached-b variant for the hot
    // can_place loop. Other strategies (i_overlay, geos) keep the existing
    // dispatcher — no caching available for those backends.
    let strategy = cached_narrow_phase_strategy();
    for (idx, other) in maybe_overlap {
        let collides = if strategy == NarrowPhaseStrategy::Own {
            let cache = placed.get_cache(idx);
            own_polygons_intersect_or_touch_against_cached(candidate, &other.inflated_polygon, cache)
        } else {
            polygons_intersect_or_touch(candidate, &other.inflated_polygon)
        };
        if collides {
            return false;
        }
    }
    true
}

/// Profiled variant of `can_place` that returns timing breakdown.
/// Returns (result, CanPlaceProfile).
///
/// T06o: `segment_pair_checks` is the budget (upper-bound: Σ ring_a×ring_b for
/// every ring pair entered). The two new fields below split out the actual
/// `segments_intersect_or_touch()` invocation count and the edge-AABB pre-reject
/// count. For the `Own` strategy these reflect runtime observation; for other
/// strategies (i_overlay, geos) they remain 0 because those backends do not
/// expose comparable internal counters.
#[derive(Debug, Clone, Copy, Default)]
pub struct CanPlaceProfile {
    pub poly_within_ns: u64,
    pub poly_within_called: bool,
    pub overlap_query_ns: u64,
    pub overlap_candidates: u32,
    pub narrow_phase_ns: u64,
    pub narrow_phase_pairs: u32,
    /// Upper-bound (budget) segment-pair count. Same semantics and value as
    /// before T06o; kept under this name to avoid churning consumers.
    pub segment_pair_checks: u64,
    /// T06o: actually invoked `segments_intersect_or_touch()` calls (own only).
    pub segment_pair_actual_checks: u64,
    /// T06o: edge pairs eliminated by the AABB pre-reject (own only).
    pub edge_bbox_rejects: u64,
    pub rejected_by_aabb: bool,
    pub rejected_by_within: bool,
    pub rejected_by_narrow: bool,
}

pub fn can_place_profiled(
    candidate: &Polygon64,
    bin: &Polygon64,
    placed: &PlacedIndex,
) -> (bool, CanPlaceProfile) {
    let mut prof = CanPlaceProfile::default();

    if !polygon_has_valid_rings(candidate) || !polygon_has_valid_rings(bin) {
        return (false, prof);
    }

    let candidate_aabb = aabb_from_polygon64(candidate);
    let bin_aabb = aabb_from_polygon64(bin);
    if !aabb_inside(&bin_aabb, &candidate_aabb) {
        prof.rejected_by_aabb = true;
        return (false, prof);
    }

    let t0 = Instant::now();
    let within = poly_strictly_within(candidate, bin);
    prof.poly_within_ns = t0.elapsed().as_nanos() as u64;
    prof.poly_within_called = true;
    if !within {
        prof.rejected_by_within = true;
        return (false, prof);
    }

    let t1 = Instant::now();
    let mut maybe_overlap: Vec<(usize, &PlacedPart)> = placed
        .query_overlaps(&candidate_aabb)
        .into_iter()
        .map(|idx| (idx, placed.get(idx)))
        .filter(|(_, p)| aabb_overlaps(&candidate_aabb, &p.aabb))
        .collect();
    prof.overlap_query_ns = t1.elapsed().as_nanos() as u64;
    prof.overlap_candidates = maybe_overlap.len() as u32;

    if maybe_overlap.is_empty() {
        return (true, prof);
    }

    maybe_overlap.sort_by(|a, b| {
        a.1.aabb
            .min_x
            .cmp(&b.1.aabb.min_x)
            .then(a.1.aabb.min_y.cmp(&b.1.aabb.min_y))
            .then(a.1.aabb.max_x.cmp(&b.1.aabb.max_x))
            .then(a.1.aabb.max_y.cmp(&b.1.aabb.max_y))
            .then(a.0.cmp(&b.0))
    });

    // T06o + T06p #4: when the active strategy is `Own`, route through the
    // cached counted variant so we observe actual segment-pair work AND get
    // the cached b-side + sorted-edge fast path. For other strategies we keep
    // the dispatcher (no per-edge instrumentation available) and the new
    // counters remain zero — documented in stats output.
    let strategy = cached_narrow_phase_strategy();
    let t2 = Instant::now();
    for (idx, other) in &maybe_overlap {
        prof.narrow_phase_pairs += 1;
        // Budget: upper bound on potential segment-pair tests. Independent of
        // any early-exit; useful as a denominator for actual / bbox-reject.
        for ring_a in polygon_rings(candidate) {
            for ring_b in polygon_rings(&other.inflated_polygon) {
                prof.segment_pair_checks += (ring_a.len() as u64) * (ring_b.len() as u64);
            }
        }

        let collision = if strategy == NarrowPhaseStrategy::Own {
            let mut counters = NarrowPhaseCounters::default();
            let cache = placed.get_cache(*idx);
            let hit = own_polygons_intersect_or_touch_against_cached_counted(
                candidate,
                &other.inflated_polygon,
                cache,
                &mut counters,
            );
            prof.segment_pair_actual_checks = prof
                .segment_pair_actual_checks
                .saturating_add(counters.segment_pair_actual);
            prof.edge_bbox_rejects = prof
                .edge_bbox_rejects
                .saturating_add(counters.edge_bbox_rejects);
            hit
        } else {
            polygons_intersect_or_touch(candidate, &other.inflated_polygon)
        };

        if collision {
            prof.narrow_phase_ns = t2.elapsed().as_nanos() as u64;
            prof.rejected_by_narrow = true;
            return (false, prof);
        }
    }
    prof.narrow_phase_ns = t2.elapsed().as_nanos() as u64;

    (true, prof)
}

fn polygon_has_valid_rings(poly: &Polygon64) -> bool {
    poly.outer.len() >= 3 && poly.holes.iter().all(|ring| ring.len() >= 3)
}

fn poly_strictly_within(candidate: &Polygon64, container: &Polygon64) -> bool {
    if !polygon_has_valid_rings(candidate) || !polygon_has_valid_rings(container) {
        return false;
    }

    for &vertex in &candidate.outer {
        if point_in_polygon(vertex, container) != PointLocation::Inside {
            return false;
        }
    }

    if ring_intersects_polygon_boundaries(&candidate.outer, container) {
        return false;
    }

    for hole in &container.holes {
        if point_in_polygon(hole[0], candidate) != PointLocation::Outside {
            return false;
        }
    }

    true
}

fn polygon_rings(poly: &Polygon64) -> impl Iterator<Item = &[Point64]> {
    std::iter::once(poly.outer.as_slice()).chain(poly.holes.iter().map(Vec::as_slice))
}

fn ring_intersects_polygon_boundaries(ring: &[Point64], poly: &Polygon64) -> bool {
    polygon_rings(poly).any(|other| ring_intersects_ring_or_touch(ring, other))
}

fn ring_intersects_ring_or_touch(a: &[Point64], b: &[Point64]) -> bool {
    ring_intersects_ring_or_touch_inner(a, b, &mut NoNarrowPhaseCounter)
}

#[inline(always)]
fn ring_intersects_ring_or_touch_inner<C: NarrowPhaseCounterSink>(
    a: &[Point64],
    b: &[Point64],
    counters: &mut C,
) -> bool {
    if a.len() < 2 || b.len() < 2 {
        return false;
    }

    for i in 0..a.len() {
        let a0 = a[i];
        let a1 = a[(i + 1) % a.len()];
        for j in 0..b.len() {
            let b0 = b[j];
            let b1 = b[(j + 1) % b.len()];
            counters.add_budget(1);
            if segment_aabb_disjoint(a0, a1, b0, b1) {
                counters.add_bbox_reject(1);
                continue;
            }
            counters.add_actual(1);
            if segments_intersect_or_touch(a0, a1, b0, b1) {
                return true;
            }
        }
    }
    false
}

/// T06p #4: edge-loop variant that uses both precomputed AABBs AND a per-ring
/// permutation of `b`'s edges sorted by `min_x`. For each edge of A we binary
/// search B's permutation for the upper bound where `min_x <= a.max_x`, then
/// iterate only that prefix. Edges with `b.min_x > a.max_x` cannot overlap on
/// the x-axis, so they would be edge-AABB-rejected anyway — but here we skip
/// them without paying even the AABB compare. Boolean result is bit-for-bit
/// identical to the non-sorted variant.
#[inline(always)]
fn ring_intersects_ring_or_touch_sorted_b<C: NarrowPhaseCounterSink>(
    a: &[Point64],
    a_edge_aabbs: &[Aabb],
    b: &[Point64],
    b_edge_aabbs: &[Aabb],
    b_sorted_by_min_x: &[u32],
    counters: &mut C,
) -> bool {
    let na = a.len();
    let nb = b.len();
    if na < 2 || nb < 2 {
        return false;
    }
    debug_assert_eq!(a_edge_aabbs.len(), na);
    debug_assert_eq!(b_edge_aabbs.len(), nb);
    debug_assert_eq!(b_sorted_by_min_x.len(), nb);

    for i in 0..na {
        let a_aabb = &a_edge_aabbs[i];
        // Upper bound: first index k such that b_edge_aabbs[sorted[k]].min_x > a.max_x.
        let upper = b_sorted_by_min_x.partition_point(|&j| {
            b_edge_aabbs[j as usize].min_x <= a_aabb.max_x
        });
        for k in 0..upper {
            let j = b_sorted_by_min_x[k] as usize;
            counters.add_budget(1);
            let b_aabb = &b_edge_aabbs[j];
            if ring_aabb_disjoint(a_aabb, b_aabb) {
                counters.add_bbox_reject(1);
                continue;
            }
            counters.add_actual(1);
            let a0 = a[i];
            let a1 = a[(i + 1) % na];
            let b0 = b[j];
            let b1 = b[(j + 1) % nb];
            if segments_intersect_or_touch(a0, a1, b0, b1) {
                return true;
            }
        }
    }
    false
}

/// T06p #2: edge-loop variant that uses precomputed per-edge AABBs. Each AABB
/// is loaded once from contiguous storage instead of being recomputed from the
/// endpoints on every pair. Boolean result is bit-for-bit identical to
/// `ring_intersects_ring_or_touch_inner` (same predicate, same touch policy).
#[inline(always)]
fn ring_intersects_ring_or_touch_with_cached_aabbs<C: NarrowPhaseCounterSink>(
    a: &[Point64],
    a_edge_aabbs: &[Aabb],
    b: &[Point64],
    b_edge_aabbs: &[Aabb],
    counters: &mut C,
) -> bool {
    let na = a.len();
    let nb = b.len();
    if na < 2 || nb < 2 {
        return false;
    }
    debug_assert_eq!(a_edge_aabbs.len(), na);
    debug_assert_eq!(b_edge_aabbs.len(), nb);

    for i in 0..na {
        let a_aabb = &a_edge_aabbs[i];
        for j in 0..nb {
            counters.add_budget(1);
            let b_aabb = &b_edge_aabbs[j];
            if ring_aabb_disjoint(a_aabb, b_aabb) {
                counters.add_bbox_reject(1);
                continue;
            }
            counters.add_actual(1);
            let a0 = a[i];
            let a1 = a[(i + 1) % na];
            let b0 = b[j];
            let b1 = b[(j + 1) % nb];
            if segments_intersect_or_touch(a0, a1, b0, b1) {
                return true;
            }
        }
    }
    false
}

fn point_in_polygon(point: Point64, poly: &Polygon64) -> PointLocation {
    match point_in_ring(point, &poly.outer) {
        PointLocation::Outside => PointLocation::Outside,
        PointLocation::OnBoundary => PointLocation::OnBoundary,
        PointLocation::Inside => {
            for hole in &poly.holes {
                match point_in_ring(point, hole) {
                    PointLocation::Outside => {}
                    PointLocation::OnBoundary => return PointLocation::OnBoundary,
                    PointLocation::Inside => return PointLocation::Outside,
                }
            }
            PointLocation::Inside
        }
    }
}

fn point_in_ring(point: Point64, ring: &[Point64]) -> PointLocation {
    if ring.len() < 3 {
        return PointLocation::Outside;
    }

    for idx in 0..ring.len() {
        let start = ring[idx];
        let end = ring[(idx + 1) % ring.len()];
        if point_on_segment_inclusive(start, end, point) {
            return PointLocation::OnBoundary;
        }
    }

    let mut winding = 0_i32;
    for idx in 0..ring.len() {
        let start = ring[idx];
        let end = ring[(idx + 1) % ring.len()];

        if start.y <= point.y {
            if end.y > point.y {
                let cross = cross_product_i128(
                    end.x - start.x,
                    end.y - start.y,
                    point.x - start.x,
                    point.y - start.y,
                );
                if cross > 0 {
                    winding += 1;
                }
            }
        } else if end.y <= point.y {
            let cross = cross_product_i128(
                end.x - start.x,
                end.y - start.y,
                point.x - start.x,
                point.y - start.y,
            );
            if cross < 0 {
                winding -= 1;
            }
        }
    }

    if winding == 0 {
        PointLocation::Outside
    } else {
        PointLocation::Inside
    }
}

fn point_on_segment_inclusive(a: Point64, b: Point64, p: Point64) -> bool {
    let cross = cross_product_i128(b.x - a.x, b.y - a.y, p.x - a.x, p.y - a.y);
    if cross != 0 {
        return false;
    }

    let min_x = a.x.min(b.x);
    let max_x = a.x.max(b.x);
    let min_y = a.y.min(b.y);
    let max_y = a.y.max(b.y);
    p.x >= min_x && p.x <= max_x && p.y >= min_y && p.y <= max_y
}

fn orient(a: Point64, b: Point64, c: Point64) -> i8 {
    let v = cross_product_i128(b.x - a.x, b.y - a.y, c.x - a.x, c.y - a.y);
    if v > 0 {
        1
    } else if v < 0 {
        -1
    } else {
        0
    }
}

fn segments_intersect_or_touch(a0: Point64, a1: Point64, b0: Point64, b1: Point64) -> bool {
    let o1 = orient(a0, a1, b0);
    let o2 = orient(a0, a1, b1);
    let o3 = orient(b0, b1, a0);
    let o4 = orient(b0, b1, a1);

    if o1 == 0 && point_on_segment_inclusive(a0, a1, b0) {
        return true;
    }
    if o2 == 0 && point_on_segment_inclusive(a0, a1, b1) {
        return true;
    }
    if o3 == 0 && point_on_segment_inclusive(b0, b1, a0) {
        return true;
    }
    if o4 == 0 && point_on_segment_inclusive(b0, b1, a1) {
        return true;
    }
    o1 != o2 && o3 != o4
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::feasibility::aabb::aabb_from_polygon64;
    use crate::geometry::scale::mm_to_i64;
    use crate::geometry::types::{Point64, Polygon64};

    fn rect(x0: f64, y0: f64, w: f64, h: f64) -> Polygon64 {
        let p = |x: f64, y: f64| Point64 {
            x: mm_to_i64(x),
            y: mm_to_i64(y),
        };
        Polygon64 {
            outer: vec![p(x0, y0), p(x0 + w, y0), p(x0 + w, y0 + h), p(x0, y0 + h)],
            holes: Vec::new(),
        }
    }

    fn poly(points: &[(f64, f64)]) -> Polygon64 {
        Polygon64 {
            outer: points
                .iter()
                .map(|(x, y)| Point64 {
                    x: mm_to_i64(*x),
                    y: mm_to_i64(*y),
                })
                .collect(),
            holes: Vec::new(),
        }
    }

    #[test]
    fn ok_case() {
        let bin = rect(0.0, 0.0, 100.0, 100.0);
        let candidate = rect(10.0, 10.0, 10.0, 10.0);
        let placed = PlacedIndex::new();
        assert!(can_place(&candidate, &bin, &placed));
    }

    #[test]
    fn overlap_case() {
        let bin = rect(0.0, 0.0, 100.0, 100.0);
        let candidate = rect(10.0, 10.0, 10.0, 10.0);
        let other_poly = rect(10.0, 10.0, 10.0, 10.0);
        let other = PlacedPart {
            aabb: aabb_from_polygon64(&other_poly),
            inflated_polygon: other_poly,
        };
        let mut placed = PlacedIndex::new();
        placed.insert(other);
        assert!(!can_place(&candidate, &bin, &placed));
    }

    #[test]
    fn containment_case() {
        let bin = rect(0.0, 0.0, 100.0, 100.0);
        let candidate = rect(95.0, 95.0, 10.0, 10.0);
        let placed = PlacedIndex::new();
        assert!(!can_place(&candidate, &bin, &placed));
    }

    #[test]
    fn touching_case() {
        let bin = rect(0.0, 0.0, 100.0, 100.0);
        let candidate = rect(10.0, 10.0, 10.0, 10.0);
        let other_poly = rect(20.0, 10.0, 10.0, 10.0);
        let other = PlacedPart {
            aabb: aabb_from_polygon64(&other_poly),
            inflated_polygon: other_poly,
        };
        let mut placed = PlacedIndex::new();
        placed.insert(other);
        assert!(!can_place(&candidate, &bin, &placed));
    }

    #[test]
    fn touching_policy_part_part_touching_is_infeasible() {
        let bin = rect(0.0, 0.0, 100.0, 100.0);
        let candidate = rect(10.0, 10.0, 10.0, 10.0);
        let other_poly = rect(20.0, 10.0, 10.0, 10.0);
        let other = PlacedPart {
            aabb: aabb_from_polygon64(&other_poly),
            inflated_polygon: other_poly,
        };
        let mut placed = PlacedIndex::new();
        placed.insert(other);
        assert!(!can_place(&candidate, &bin, &placed));
    }

    #[test]
    fn broad_phase_query_result_is_deterministic_after_sort() {
        let bin = rect(0.0, 0.0, 100.0, 100.0);
        let candidate = rect(10.0, 10.0, 10.0, 10.0);

        let other_a_poly = rect(20.0, 20.0, 10.0, 10.0);
        let other_b_poly = rect(25.0, 20.0, 10.0, 10.0);
        let other_a = PlacedPart {
            aabb: aabb_from_polygon64(&other_a_poly),
            inflated_polygon: other_a_poly,
        };
        let other_b = PlacedPart {
            aabb: aabb_from_polygon64(&other_b_poly),
            inflated_polygon: other_b_poly,
        };

        let mut placed_ab = PlacedIndex::new();
        placed_ab.insert(other_a.clone());
        placed_ab.insert(other_b.clone());

        let mut placed_ba = PlacedIndex::new();
        placed_ba.insert(other_b);
        placed_ba.insert(other_a);

        let res_ab = can_place(&candidate, &bin, &placed_ab);
        let res_ba = can_place(&candidate, &bin, &placed_ba);
        assert_eq!(res_ab, res_ba);
    }

    #[test]
    fn can_place_rejects_touching_bin_boundary() {
        let bin = rect(0.0, 0.0, 100.0, 100.0);
        let candidate = rect(0.0, 10.0, 10.0, 10.0);
        let placed = PlacedIndex::new();
        assert!(!can_place(&candidate, &bin, &placed));
    }

    #[test]
    fn touching_policy_bin_boundary_touching_is_infeasible() {
        let bin = rect(0.0, 0.0, 100.0, 100.0);
        let candidate = rect(0.0, 10.0, 10.0, 10.0);
        let placed = PlacedIndex::new();
        assert!(!can_place(&candidate, &bin, &placed));
    }

    #[test]
    fn narrow_float_policy_mm_rounding_near_touching_is_deterministic() {
        let bin = rect(0.0, 0.0, 100.0, 100.0);
        let candidate = rect(10.0, 10.0, 10.0, 10.0);

        let touching_after_round_poly = rect(20.00000049, 10.0, 10.0, 10.0);
        let touching_after_round = PlacedPart {
            aabb: aabb_from_polygon64(&touching_after_round_poly),
            inflated_polygon: touching_after_round_poly,
        };
        let mut placed_touch = PlacedIndex::new();
        placed_touch.insert(touching_after_round);
        assert!(
            !can_place(&candidate, &bin, &placed_touch),
            "rounding-near touching candidate must stay infeasible"
        );

        let one_micron_gap_poly = rect(20.00000051, 10.0, 10.0, 10.0);
        let one_micron_gap = PlacedPart {
            aabb: aabb_from_polygon64(&one_micron_gap_poly),
            inflated_polygon: one_micron_gap_poly,
        };
        let mut placed_gap = PlacedIndex::new();
        placed_gap.insert(one_micron_gap);
        assert!(
            can_place(&candidate, &bin, &placed_gap),
            "1um gap after scaling should remain feasible"
        );
    }

    #[test]
    fn narrow_float_policy_identical_input_is_stable() {
        let bin = rect(0.0, 0.0, 100.0, 100.0);
        let candidate = rect(10.0, 10.0, 10.0, 10.0);
        let other_poly = rect(20.00000049, 10.0, 10.0, 10.0);
        let other = PlacedPart {
            aabb: aabb_from_polygon64(&other_poly),
            inflated_polygon: other_poly,
        };
        let mut placed = PlacedIndex::new();
        placed.insert(other);

        let first = can_place(&candidate, &bin, &placed);
        let second = can_place(&candidate, &bin, &placed);
        assert_eq!(first, second);
    }

    /// T06l-a: boolean equivalence — `can_place` and `can_place_profiled.0`
    /// MUST return the same boolean across the canonical control cases.
    #[test]
    fn can_place_and_profiled_return_equal_booleans_across_control_cases() {
        let bin = rect(0.0, 0.0, 100.0, 100.0);

        // Case 1: empty sheet, valid placement → both true.
        let candidate_ok = rect(10.0, 10.0, 10.0, 10.0);
        let placed_empty = PlacedIndex::new();
        assert_eq!(
            can_place(&candidate_ok, &bin, &placed_empty),
            can_place_profiled(&candidate_ok, &bin, &placed_empty).0,
            "empty sheet valid case must match",
        );

        // Case 2: bounds violation (containment fails) → both false.
        let candidate_oob = rect(95.0, 95.0, 10.0, 10.0);
        assert_eq!(
            can_place(&candidate_oob, &bin, &placed_empty),
            can_place_profiled(&candidate_oob, &bin, &placed_empty).0,
            "bounds violation must match",
        );

        // Case 3: overlap violation → both false.
        let overlap_poly = rect(10.0, 10.0, 10.0, 10.0);
        let mut placed_overlap = PlacedIndex::new();
        placed_overlap.insert(PlacedPart {
            aabb: aabb_from_polygon64(&overlap_poly),
            inflated_polygon: overlap_poly,
        });
        assert_eq!(
            can_place(&candidate_ok, &bin, &placed_overlap),
            can_place_profiled(&candidate_ok, &bin, &placed_overlap).0,
            "overlap violation must match",
        );

        // Case 4: touching → both false (touching is infeasible by policy).
        let touch_poly = rect(20.0, 10.0, 10.0, 10.0);
        let mut placed_touch = PlacedIndex::new();
        placed_touch.insert(PlacedPart {
            aabb: aabb_from_polygon64(&touch_poly),
            inflated_polygon: touch_poly,
        });
        assert_eq!(
            can_place(&candidate_ok, &bin, &placed_touch),
            can_place_profiled(&candidate_ok, &bin, &placed_touch).0,
            "touching policy decision must match",
        );

        // Case 5: multiple placed parts via RTree query → both should yield same answer.
        let other_a_poly = rect(40.0, 40.0, 10.0, 10.0);
        let other_b_poly = rect(60.0, 60.0, 10.0, 10.0);
        let other_c_poly = rect(80.0, 80.0, 10.0, 10.0);
        let mut placed_multi = PlacedIndex::new();
        placed_multi.insert(PlacedPart {
            aabb: aabb_from_polygon64(&other_a_poly),
            inflated_polygon: other_a_poly,
        });
        placed_multi.insert(PlacedPart {
            aabb: aabb_from_polygon64(&other_b_poly),
            inflated_polygon: other_b_poly,
        });
        placed_multi.insert(PlacedPart {
            aabb: aabb_from_polygon64(&other_c_poly),
            inflated_polygon: other_c_poly,
        });
        let candidate_clear = rect(2.0, 2.0, 5.0, 5.0);
        assert_eq!(
            can_place(&candidate_clear, &bin, &placed_multi),
            can_place_profiled(&candidate_clear, &bin, &placed_multi).0,
            "multi-placed clear case must match",
        );
        let candidate_overlap = rect(42.0, 42.0, 5.0, 5.0);
        assert_eq!(
            can_place(&candidate_overlap, &bin, &placed_multi),
            can_place_profiled(&candidate_overlap, &bin, &placed_multi).0,
            "multi-placed overlap case must match",
        );
    }

    #[test]
    fn can_place_is_deterministic_for_identical_aabb_ties() {
        let bin = rect(0.0, 0.0, 100.0, 100.0);
        let candidate = rect(32.0, 32.0, 2.0, 2.0);

        let overlap_poly = poly(&[(30.0, 30.0), (40.0, 30.0), (30.0, 40.0)]);
        let clear_poly = poly(&[(30.0, 40.0), (40.0, 40.0), (40.0, 30.0)]);

        let overlap_part = PlacedPart {
            aabb: aabb_from_polygon64(&overlap_poly),
            inflated_polygon: overlap_poly,
        };
        let clear_part = PlacedPart {
            aabb: aabb_from_polygon64(&clear_poly),
            inflated_polygon: clear_poly,
        };

        let mut placed_overlap_first = PlacedIndex::new();
        placed_overlap_first.insert(overlap_part.clone());
        placed_overlap_first.insert(clear_part.clone());

        let mut placed_clear_first = PlacedIndex::new();
        placed_clear_first.insert(clear_part);
        placed_clear_first.insert(overlap_part);

        let res_overlap_first = can_place(&candidate, &bin, &placed_overlap_first);
        let res_clear_first = can_place(&candidate, &bin, &placed_clear_first);
        assert_eq!(res_overlap_first, res_clear_first);
    }

    // =====================================================================
    // T06o: edge-pair AABB pre-reject + counter tests
    // =====================================================================

    fn pt(x: f64, y: f64) -> Point64 {
        Point64 {
            x: mm_to_i64(x),
            y: mm_to_i64(y),
        }
    }

    #[test]
    fn segment_aabb_disjoint_rejects_far_segments() {
        // Two clearly far-apart segments: x ranges do not overlap.
        let a0 = pt(0.0, 0.0);
        let a1 = pt(1.0, 1.0);
        let b0 = pt(10.0, 0.0);
        let b1 = pt(11.0, 1.0);
        assert!(segment_aabb_disjoint(a0, a1, b0, b1));
    }

    #[test]
    fn segment_aabb_disjoint_does_not_reject_touching_endpoint() {
        // Endpoint touch — must NOT pre-reject (touch policy: contact = collision).
        let a0 = pt(0.0, 0.0);
        let a1 = pt(10.0, 0.0);
        let b0 = pt(10.0, 0.0); // shared endpoint
        let b1 = pt(10.0, 10.0);
        assert!(!segment_aabb_disjoint(a0, a1, b0, b1));
        // The full segment test must report contact.
        assert!(segments_intersect_or_touch(a0, a1, b0, b1));
    }

    #[test]
    fn segment_aabb_disjoint_does_not_reject_collinear_touch() {
        // Collinear, share endpoint.
        let a0 = pt(0.0, 0.0);
        let a1 = pt(10.0, 0.0);
        let b0 = pt(10.0, 0.0);
        let b1 = pt(20.0, 0.0);
        assert!(!segment_aabb_disjoint(a0, a1, b0, b1));
        assert!(segments_intersect_or_touch(a0, a1, b0, b1));
    }

    #[test]
    fn segment_aabb_disjoint_does_not_reject_collinear_overlap() {
        // Collinear with proper overlap.
        let a0 = pt(0.0, 0.0);
        let a1 = pt(10.0, 0.0);
        let b0 = pt(5.0, 0.0);
        let b1 = pt(15.0, 0.0);
        assert!(!segment_aabb_disjoint(a0, a1, b0, b1));
        assert!(segments_intersect_or_touch(a0, a1, b0, b1));
    }

    #[test]
    fn segment_aabb_disjoint_strict_lt_at_axis_boundary() {
        // X ranges meet at exactly one coordinate (boundary touch in x);
        // y ranges overlap. Must NOT pre-reject (strict < required).
        let a0 = pt(0.0, 0.0);
        let a1 = pt(10.0, 5.0);
        let b0 = pt(10.0, 4.0);
        let b1 = pt(20.0, 6.0);
        assert!(!segment_aabb_disjoint(a0, a1, b0, b1));
    }

    #[test]
    fn edge_bbox_prereject_preserves_polygon_collision_cases() {
        // Reference cases: every result must match the documented expected value.
        let cases: Vec<(&str, Polygon64, Polygon64, bool)> = vec![
            (
                "separated",
                rect(0.0, 0.0, 10.0, 10.0),
                rect(20.0, 0.0, 10.0, 10.0),
                false,
            ),
            (
                "overlap",
                rect(0.0, 0.0, 10.0, 10.0),
                rect(5.0, 5.0, 10.0, 10.0),
                true,
            ),
            (
                "edge_touch",
                rect(0.0, 0.0, 10.0, 10.0),
                rect(10.0, 0.0, 10.0, 10.0),
                true,
            ),
            (
                "corner_touch",
                rect(0.0, 0.0, 10.0, 10.0),
                rect(10.0, 10.0, 10.0, 10.0),
                true,
            ),
            (
                "containment",
                rect(0.0, 0.0, 20.0, 20.0),
                rect(5.0, 5.0, 5.0, 5.0),
                true,
            ),
            (
                "concave_actual_overlap",
                poly(&[
                    (0.0, 0.0),
                    (20.0, 0.0),
                    (20.0, 10.0),
                    (10.0, 10.0),
                    (10.0, 20.0),
                    (0.0, 20.0),
                ]),
                rect(8.0, 8.0, 5.0, 5.0),
                true,
            ),
            (
                "high_vertex_near_miss",
                poly(&[
                    (0.0, 0.0),
                    (50.0, 0.0),
                    (50.0, 10.0),
                    (40.0, 10.0),
                    (40.0, 20.0),
                    (30.0, 20.0),
                    (30.0, 30.0),
                    (20.0, 30.0),
                    (20.0, 40.0),
                    (10.0, 40.0),
                    (10.0, 50.0),
                    (0.0, 50.0),
                ]),
                rect(60.0, 60.0, 5.0, 5.0),
                false,
            ),
        ];
        for (label, a, b, expected) in &cases {
            let got = own_polygons_intersect_or_touch(a, b);
            assert_eq!(got, *expected, "case {} expected {} got {}", label, expected, got);
        }
    }

    #[test]
    fn counted_variant_matches_uncounted_variant_boolean() {
        // Boolean equivalence between counted and non-counted own implementations.
        let cases: Vec<(Polygon64, Polygon64)> = vec![
            (rect(0.0, 0.0, 10.0, 10.0), rect(20.0, 0.0, 10.0, 10.0)),
            (rect(0.0, 0.0, 10.0, 10.0), rect(5.0, 5.0, 10.0, 10.0)),
            (rect(0.0, 0.0, 10.0, 10.0), rect(10.0, 0.0, 10.0, 10.0)),
            (rect(0.0, 0.0, 10.0, 10.0), rect(10.0, 10.0, 10.0, 10.0)),
            (rect(0.0, 0.0, 20.0, 20.0), rect(5.0, 5.0, 5.0, 5.0)),
        ];
        for (a, b) in &cases {
            let plain = own_polygons_intersect_or_touch(a, b);
            let mut counters = NarrowPhaseCounters::default();
            let counted = own_polygons_intersect_or_touch_counted(a, b, &mut counters);
            assert_eq!(plain, counted, "counted variant must agree with plain");
        }
    }

    #[test]
    fn counter_invariant_actual_plus_reject_le_budget() {
        // For any pair, actual + edge_bbox_rejects <= budget. Early-exit may make
        // it strictly less than budget.
        let edge_rich_a = poly(&[
            (0.0, 0.0),
            (50.0, 0.0),
            (50.0, 10.0),
            (40.0, 10.0),
            (40.0, 20.0),
            (30.0, 20.0),
            (30.0, 30.0),
            (20.0, 30.0),
            (20.0, 40.0),
            (10.0, 40.0),
            (10.0, 50.0),
            (0.0, 50.0),
        ]);
        let edge_rich_b = rect(60.0, 60.0, 5.0, 5.0);
        let mut counters = NarrowPhaseCounters::default();
        let _ = own_polygons_intersect_or_touch_counted(&edge_rich_a, &edge_rich_b, &mut counters);
        assert!(
            counters.segment_pair_actual + counters.edge_bbox_rejects
                <= counters.segment_pair_budget,
            "actual+reject ({} + {}) must be <= budget ({})",
            counters.segment_pair_actual,
            counters.edge_bbox_rejects,
            counters.segment_pair_budget
        );
        assert!(
            counters.segment_pair_actual <= counters.segment_pair_budget,
            "actual must be <= budget"
        );
        assert!(
            counters.edge_bbox_rejects <= counters.segment_pair_budget,
            "rejects must be <= budget"
        );
    }

    #[test]
    fn counter_edge_bbox_reject_positive_for_disjoint_edge_rich_pair() {
        // Two edge-rich polygons whose outer AABBs overlap so the ring-level
        // pre-reject does NOT fire — exercises the inner edge-pair AABB pruning.
        // (The far-apart variant of this case is now covered by
        // `ring_bbox_reject_counter_positive_for_polygon_with_disjoint_holes`.)
        let a = poly(&[
            (0.0, 0.0),
            (50.0, 0.0),
            (50.0, 10.0),
            (40.0, 10.0),
            (40.0, 20.0),
            (30.0, 20.0),
            (30.0, 30.0),
            (20.0, 30.0),
            (20.0, 40.0),
            (10.0, 40.0),
            (10.0, 50.0),
            (0.0, 50.0),
        ]);
        // B sits in the concave notch of A — outer AABBs overlap, but most
        // edge pairs (especially around B vs A's far edges) are AABB-disjoint.
        let b = rect(30.0, 30.0, 18.0, 18.0);
        let mut counters = NarrowPhaseCounters::default();
        let _ = own_polygons_intersect_or_touch_counted(&a, &b, &mut counters);
        assert!(
            counters.edge_bbox_rejects > 0,
            "expected edge_bbox_rejects > 0 for AABB-overlapping edge-rich pair, got {}",
            counters.edge_bbox_rejects
        );
        // Invariant: actual + edge_bbox_rejects ≤ budget (early exit may make
        // it strictly less; ring-level skips reduce budget too).
        assert!(
            counters.segment_pair_actual + counters.edge_bbox_rejects
                <= counters.segment_pair_budget,
            "actual+rejects ({} + {}) must be <= budget ({})",
            counters.segment_pair_actual,
            counters.edge_bbox_rejects,
            counters.segment_pair_budget
        );
    }

    #[test]
    fn can_place_profiled_populates_segment_pair_actual_for_own_strategy() {
        // Reject path with a real overlap — the profile should expose nonzero
        // actual segment-pair work and a positive budget.
        let bin = rect(0.0, 0.0, 100.0, 100.0);
        let candidate = rect(10.0, 10.0, 10.0, 10.0);
        let other_poly = rect(15.0, 15.0, 10.0, 10.0);
        let other = PlacedPart {
            aabb: aabb_from_polygon64(&other_poly),
            inflated_polygon: other_poly,
        };
        let mut placed = PlacedIndex::new();
        placed.insert(other);

        let (ok, prof) = can_place_profiled(&candidate, &bin, &placed);
        assert!(!ok, "overlap must be infeasible");
        assert!(prof.rejected_by_narrow, "must be rejected by narrow phase");
        assert!(
            prof.segment_pair_checks > 0,
            "budget must be > 0 for narrow path"
        );
        // For Own strategy (default), actual count must be populated. Do NOT
        // assert on i_overlay default tests in CI without env override.
        if cached_narrow_phase_strategy() == NarrowPhaseStrategy::Own {
            assert!(
                prof.segment_pair_actual_checks > 0,
                "actual must be > 0 when strategy=Own and overlap exists"
            );
            assert!(
                prof.segment_pair_actual_checks + prof.edge_bbox_rejects
                    <= prof.segment_pair_checks,
                "actual+rejects ({} + {}) must be <= budget ({})",
                prof.segment_pair_actual_checks,
                prof.edge_bbox_rejects,
                prof.segment_pair_checks
            );
        }
    }

    // =====================================================================
    // T06p: ring-level AABB pre-reject tests
    // =====================================================================

    #[test]
    fn ring_aabb_disjoint_rejects_far_rings() {
        let a = Aabb { min_x: 0, min_y: 0, max_x: 10, max_y: 10 };
        let b = Aabb { min_x: 20, min_y: 0, max_x: 30, max_y: 10 };
        assert!(ring_aabb_disjoint(&a, &b));
    }

    #[test]
    fn ring_aabb_disjoint_does_not_reject_touching_rings() {
        // Strict <: touching is NOT pre-rejected.
        let a = Aabb { min_x: 0, min_y: 0, max_x: 10, max_y: 10 };
        let b = Aabb { min_x: 10, min_y: 0, max_x: 20, max_y: 10 };
        assert!(!ring_aabb_disjoint(&a, &b));
    }

    #[test]
    fn ring_aabb_disjoint_does_not_reject_overlap() {
        let a = Aabb { min_x: 0, min_y: 0, max_x: 10, max_y: 10 };
        let b = Aabb { min_x: 5, min_y: 5, max_x: 15, max_y: 15 };
        assert!(!ring_aabb_disjoint(&a, &b));
    }

    #[test]
    fn ring_aabb_prereject_preserves_collision_cases() {
        // Same case matrix as edge_bbox_prereject_preserves_polygon_collision_cases.
        let cases: Vec<(&str, Polygon64, Polygon64, bool)> = vec![
            ("separated", rect(0.0, 0.0, 10.0, 10.0), rect(20.0, 0.0, 10.0, 10.0), false),
            ("overlap", rect(0.0, 0.0, 10.0, 10.0), rect(5.0, 5.0, 10.0, 10.0), true),
            ("edge_touch", rect(0.0, 0.0, 10.0, 10.0), rect(10.0, 0.0, 10.0, 10.0), true),
            ("corner_touch", rect(0.0, 0.0, 10.0, 10.0), rect(10.0, 10.0, 10.0, 10.0), true),
            ("containment", rect(0.0, 0.0, 20.0, 20.0), rect(5.0, 5.0, 5.0, 5.0), true),
            (
                "concave_actual_overlap",
                poly(&[
                    (0.0, 0.0), (20.0, 0.0), (20.0, 10.0), (10.0, 10.0),
                    (10.0, 20.0), (0.0, 20.0),
                ]),
                rect(8.0, 8.0, 5.0, 5.0),
                true,
            ),
            (
                "high_vertex_near_miss",
                poly(&[
                    (0.0, 0.0), (50.0, 0.0), (50.0, 10.0), (40.0, 10.0),
                    (40.0, 20.0), (30.0, 20.0), (30.0, 30.0), (20.0, 30.0),
                    (20.0, 40.0), (10.0, 40.0), (10.0, 50.0), (0.0, 50.0),
                ]),
                rect(60.0, 60.0, 5.0, 5.0),
                false,
            ),
        ];
        for (label, a, b, expected) in &cases {
            let got = own_polygons_intersect_or_touch(a, b);
            assert_eq!(got, *expected, "case {} expected {} got {}", label, expected, got);
        }
    }

    #[test]
    fn ring_bbox_reject_counter_positive_for_polygon_with_disjoint_holes() {
        // Polygon A with a hole far from polygon B → ring-level pre-reject must fire
        // for that hole vs B's outer ring.
        let outer_a = vec![
            Point64 { x: mm_to_i64(0.0), y: mm_to_i64(0.0) },
            Point64 { x: mm_to_i64(100.0), y: mm_to_i64(0.0) },
            Point64 { x: mm_to_i64(100.0), y: mm_to_i64(100.0) },
            Point64 { x: mm_to_i64(0.0), y: mm_to_i64(100.0) },
        ];
        let hole_a = vec![
            Point64 { x: mm_to_i64(80.0), y: mm_to_i64(80.0) },
            Point64 { x: mm_to_i64(90.0), y: mm_to_i64(80.0) },
            Point64 { x: mm_to_i64(90.0), y: mm_to_i64(90.0) },
            Point64 { x: mm_to_i64(80.0), y: mm_to_i64(90.0) },
        ];
        let a = Polygon64 { outer: outer_a, holes: vec![hole_a] };
        // B inside A, far from the hole — overlaps A's outer but disjoint from A's hole.
        let b = rect(5.0, 5.0, 10.0, 10.0);
        let mut counters = NarrowPhaseCounters::default();
        let _ = own_polygons_intersect_or_touch_counted(&a, &b, &mut counters);
        assert!(
            counters.ring_bbox_rejects > 0,
            "expected ring_bbox_rejects > 0 for polygon with disjoint hole, got {}",
            counters.ring_bbox_rejects
        );
    }

    #[test]
    fn counter_invariant_actual_plus_reject_le_budget_after_t06p() {
        // After T06p the segment_pair_budget reflects only ring-pairs that
        // entered the inner edge loop. Invariant: actual + edge_bbox_rejects
        // <= segment_pair_budget still holds.
        let edge_rich_a = poly(&[
            (0.0, 0.0), (50.0, 0.0), (50.0, 10.0), (40.0, 10.0),
            (40.0, 20.0), (30.0, 20.0), (30.0, 30.0), (20.0, 30.0),
            (20.0, 40.0), (10.0, 40.0), (10.0, 50.0), (0.0, 50.0),
        ]);
        let edge_rich_b = rect(60.0, 60.0, 5.0, 5.0);
        let mut counters = NarrowPhaseCounters::default();
        let _ = own_polygons_intersect_or_touch_counted(&edge_rich_a, &edge_rich_b, &mut counters);
        assert!(
            counters.segment_pair_actual + counters.edge_bbox_rejects
                <= counters.segment_pair_budget,
            "actual+reject ({} + {}) must be <= budget ({})",
            counters.segment_pair_actual,
            counters.edge_bbox_rejects,
            counters.segment_pair_budget
        );
    }

    // =====================================================================
    // T06p #3: convex SAT fast-path tests
    // =====================================================================

    #[test]
    fn is_convex_ring_true_for_rectangle() {
        let r = rect(0.0, 0.0, 10.0, 5.0);
        assert!(is_convex_ring(&r.outer));
    }

    #[test]
    fn is_convex_ring_false_for_concave_l_shape() {
        let l = poly(&[
            (0.0, 0.0), (20.0, 0.0), (20.0, 10.0),
            (10.0, 10.0), (10.0, 20.0), (0.0, 20.0),
        ]);
        assert!(!is_convex_ring(&l.outer));
    }

    #[test]
    fn convex_sat_matches_edge_loop_for_canonical_cases() {
        // Convex-convex pairs: SAT (via own_polygons_intersect_or_touch) must
        // agree with the edge-loop (via the counted variant which bypasses SAT).
        let cases: Vec<(&str, Polygon64, Polygon64, bool)> = vec![
            ("separated", rect(0.0, 0.0, 10.0, 10.0), rect(20.0, 0.0, 10.0, 10.0), false),
            ("overlap", rect(0.0, 0.0, 10.0, 10.0), rect(5.0, 5.0, 10.0, 10.0), true),
            ("edge_touch", rect(0.0, 0.0, 10.0, 10.0), rect(10.0, 0.0, 10.0, 10.0), true),
            ("corner_touch", rect(0.0, 0.0, 10.0, 10.0), rect(10.0, 10.0, 10.0, 10.0), true),
            ("containment", rect(0.0, 0.0, 20.0, 20.0), rect(5.0, 5.0, 5.0, 5.0), true),
        ];
        for (label, a, b, expected) in &cases {
            let sat_result = own_polygons_intersect_or_touch(a, b);
            let mut counters = NarrowPhaseCounters::default();
            let edge_result = own_polygons_intersect_or_touch_counted(a, b, &mut counters);
            assert_eq!(sat_result, *expected, "SAT case {} expected {}", label, expected);
            assert_eq!(edge_result, *expected, "edge case {} expected {}", label, expected);
            assert_eq!(sat_result, edge_result, "SAT and edge must agree on {}", label);
        }
    }

    #[test]
    fn convex_sat_strict_lt_one_micron_gap_is_separated() {
        // 1 µm gap on x-axis (matches narrow_float_policy_mm_rounding_near_touching).
        let a = rect(0.0, 0.0, 10.0, 10.0);
        let b = rect(10.00000051, 0.0, 10.0, 10.0);
        assert!(!own_polygons_intersect_or_touch(&a, &b));
    }

    #[test]
    fn convex_sat_does_not_fire_when_polygon_has_holes() {
        // Polygon with a hole should NOT take the SAT path even if outer is convex.
        let outer = vec![
            Point64 { x: mm_to_i64(0.0), y: mm_to_i64(0.0) },
            Point64 { x: mm_to_i64(20.0), y: mm_to_i64(0.0) },
            Point64 { x: mm_to_i64(20.0), y: mm_to_i64(20.0) },
            Point64 { x: mm_to_i64(0.0), y: mm_to_i64(20.0) },
        ];
        let hole = vec![
            Point64 { x: mm_to_i64(8.0), y: mm_to_i64(8.0) },
            Point64 { x: mm_to_i64(12.0), y: mm_to_i64(8.0) },
            Point64 { x: mm_to_i64(12.0), y: mm_to_i64(12.0) },
            Point64 { x: mm_to_i64(8.0), y: mm_to_i64(12.0) },
        ];
        let a = Polygon64 { outer, holes: vec![hole] };
        // B sits inside A's hole — for a polygon-with-hole semantics, A and B
        // do NOT collide (B is in the cavity). SAT on outer rings alone would
        // say "B inside A's outer = collision" — wrong. Verify the non-SAT
        // path is taken and the correct answer is returned.
        let b = rect(9.0, 9.0, 2.0, 2.0);
        let result = own_polygons_intersect_or_touch(&a, &b);
        // The correct answer here depends on the touch-policy semantics for
        // hole interiors. With holes treated as cavities, B inside A's hole
        // means no collision (false). The edge-loop returns false here.
        let mut counters = NarrowPhaseCounters::default();
        let edge_result = own_polygons_intersect_or_touch_counted(&a, &b, &mut counters);
        assert_eq!(result, edge_result, "SAT-skip must match edge-loop for polygons with holes");
    }

    #[test]
    fn cached_narrow_phase_strategy_returns_default_when_unset() {
        // We cannot reliably mutate env in unit tests (the cache is process-
        // wide), but we can assert it returns *something* and is consistent
        // across calls.
        let s1 = cached_narrow_phase_strategy();
        let s2 = cached_narrow_phase_strategy();
        assert_eq!(s1, s2, "cached strategy must be stable across calls");
    }

    // =====================================================================
    // T06m: strategy correctness equivalence tests
    // =====================================================================

    /// Verify own_polygons_intersect_or_touch and i_overlay strategy agree
    /// on a range of geometric cases. Disagreement where own says collision
    /// but i_overlay says no-collision is a FAIL (false accept risk).
    #[test]
    fn i_overlay_strategy_equivalence_basic_cases() {
        // Only run when i_overlay strategy is enabled
        if std::env::var("NESTING_ENGINE_NARROW_PHASE") != Ok("i_overlay".into()) {
            return;
        }

        fn check_pair(
            a: Polygon64,
            b: Polygon64,
            expected_collision: bool,
            label: &str,
        ) -> bool {
            let own = own_polygons_intersect_or_touch(&a, &b);
            let iovr = i_overlay_narrow::polygons_intersect_or_touch_i_overlay(&a, &b);

            // i_overlay may be conservative (report collision when own doesn't)
            // but NOT the reverse (that would be a false accept).
            if own && !iovr {
                eprintln!(
                    "[FAIL i_overlay] {}: own=collision i_overlay=no_collision (false accept!)",
                    label
                );
                return false;
            }
            if !own && iovr && expected_collision {
                // conservative: own says no, i_overlay says yes — ok per spec
            }
            true
        }

        let r = |x0, y0, w, h| rect(x0, y0, w, h);

        // Case 1: no overlap, separated rectangles
        assert!(check_pair(r(0.,0.,10.,10.), r(20.,0.,10.,10.), false, "separated"));
        // Case 2: clear overlap
        assert!(check_pair(r(0.,0.,10.,10.), r(5.,5.,10.,10.), true, "overlap"));
        // Case 3: edge touch
        assert!(check_pair(r(0.,0.,10.,10.), r(10.,0.,10.,10.), true, "edge_touch"));
        // Case 4: point/corner touch
        assert!(check_pair(r(0.,0.,10.,10.), r(10.,10.,10.,10.), true, "corner_touch"));
        // Case 5: one fully inside another
        assert!(check_pair(r(0.,0.,20.,20.), r(5.,5.,5.,5.), true, "containment"));
    }
}
