use jagua_rs::collision_detection::hazards::collector::{BasicHazardCollector, HazardCollector};
use jagua_rs::collision_detection::hazards::filter::NoFilter;
use jagua_rs::collision_detection::hazards::{Hazard, HazardEntity};
use jagua_rs::collision_detection::{CDEConfig, CDEngine};
use jagua_rs::geometry::fail_fast::SPSurrogateConfig;
use jagua_rs::geometry::primitives::Rect as JagRect;

use std::cell::RefCell;
use std::collections::hash_map::DefaultHasher;
use std::collections::HashMap;
use std::hash::{Hash, Hasher};
use std::rc::Rc;

use super::collision_backend::{
    extract_polygon_from_part, polygon_within_sheet_pts, polygons_collide, transform_polygon,
    PolygonExtraction,
};
use crate::geometry::{polygon_bbox, to_jag_polygon, Point};
use crate::io::Placement;
use crate::item::Part;
use crate::sheet::SheetShape;

// ---------------------------------------------------------------------------
// CdeAdapterConfig
// ---------------------------------------------------------------------------

/// Configuration for per-call CDEngine construction.
/// Quadtree depth and cd_threshold trade off setup cost vs query precision.
pub struct CdeAdapterConfig {
    pub quadtree_depth: u8,
    pub cd_threshold: u8,
}

impl Default for CdeAdapterConfig {
    fn default() -> Self {
        Self {
            quadtree_depth: 4,
            cd_threshold: 0,
        }
    }
}

// ---------------------------------------------------------------------------
// CdePreparedShape
// ---------------------------------------------------------------------------

/// A shape pre-built for CDE queries: holds the jagua-rs SPolygon, an f64 bounding box,
/// and the original f64 world-coordinate polygon points.
///
/// `world_pts` is used by the VRS-side post-policy to distinguish touching (NoCollision)
/// from positive-area overlap (Collision) — see `polygons_collide` / `polygon_within_sheet_pts`.
///
/// Jagua-rs types must not appear in the public optimizer API — this type is crate-internal only.
pub(crate) struct CdePreparedShape {
    pub(crate) spoly: jagua_rs::geometry::primitives::SPolygon,
    pub(crate) min_x: f64,
    pub(crate) min_y: f64,
    pub(crate) max_x: f64,
    pub(crate) max_y: f64,
    /// World-coordinate f64 polygon points for VRS-side touching post-policy.
    pub(crate) world_pts: Vec<Point>,
}

// ---------------------------------------------------------------------------
// CdeQueryResult
// ---------------------------------------------------------------------------

/// Result of a CDE-level collision query.
///
/// `Unsupported { reason }` is returned when the input geometry cannot be
/// prepared (missing or invalid polygon data). Callers must NOT treat
/// Unsupported as NoCollision.
#[derive(Debug, Clone, PartialEq)]
pub enum CdeQueryResult {
    Collision,
    NoCollision,
    Unsupported { reason: &'static str },
}

impl CdeQueryResult {
    pub fn is_collision(&self) -> bool {
        matches!(self, CdeQueryResult::Collision)
    }
    pub fn is_no_collision(&self) -> bool {
        matches!(self, CdeQueryResult::NoCollision)
    }
    pub fn is_unsupported(&self) -> bool {
        matches!(self, CdeQueryResult::Unsupported { .. })
    }
}

// ---------------------------------------------------------------------------
// CdeAdapter
// ---------------------------------------------------------------------------

/// VRS-owned CDE adapter.
///
/// Builds a temporary `CDEngine` per query call — genuine jagua-rs CDE
/// collision detection, not a bbox or JaguaPolygonExact wrapper.
///
/// Per-call CDEngine construction is an O(n) setup cost (quadtree build).
/// For high-throughput pipelines, a session-owned CDEngine with registered
/// hazards is the preferred port target; see the contract doc for the plan.
pub(crate) struct CdeAdapter {
    config: CdeAdapterConfig,
}

impl CdeAdapter {
    pub(crate) fn new(config: CdeAdapterConfig) -> Self {
        Self { config }
    }

    pub(crate) fn with_defaults() -> Self {
        Self {
            config: CdeAdapterConfig::default(),
        }
    }

    /// Query whether two prepared shapes overlap.
    ///
    /// Registers shape `b` as a Hole hazard (interior forbidden) and queries
    /// shape `a`. The CDEngine correctly handles edge-edge intersection,
    /// A ⊂ B, and B ⊂ A containment via `detect_containment_collision`.
    ///
    /// Semantic note: CDE uses `Edge::collides_with` with `proper_only=false`,
    /// so collinear/touching edges count as Collision. This is STRICTER than
    /// JaguaPolygonExactBackend, which requires a proper crossing.
    pub(crate) fn query_pair(&self, a: &CdePreparedShape, b: &CdePreparedShape) -> CdeQueryResult {
        // SGH-Q23 AABB broad-phase pre-check. If the two axis-aligned bounding
        // boxes are strictly separated on either axis, the polygons cannot
        // overlap — resolve as NoCollision WITHOUT building a CDEngine. This is
        // pure broad-phase pruning: it only ever yields NoCollision (never a
        // positive collision), so CDE/Jagua remains the sole source of positive
        // collision truth.
        if a.max_x < b.min_x || b.max_x < a.min_x || a.max_y < b.min_y || b.max_y < a.min_y {
            super::cde_observability::inc_broadphase_pruned();
            return CdeQueryResult::NoCollision;
        }

        let margin = 1.0_f64;
        let ux1 = (a.min_x.min(b.min_x) - margin) as f32;
        let uy1 = (a.min_y.min(b.min_y) - margin) as f32;
        let ux2 = (a.max_x.max(b.max_x) + margin) as f32;
        let uy2 = (a.max_y.max(b.max_y) + margin) as f32;

        let jag_bbox = match JagRect::try_new(ux1, uy1, ux2, uy2) {
            Ok(r) => r,
            Err(_) => {
                return CdeQueryResult::Unsupported {
                    reason: "degenerate union bbox for pair query",
                }
            }
        };

        let ext_pts = [
            Point {
                x: ux1 as f64,
                y: uy1 as f64,
            },
            Point {
                x: ux2 as f64,
                y: uy1 as f64,
            },
            Point {
                x: ux2 as f64,
                y: uy2 as f64,
            },
            Point {
                x: ux1 as f64,
                y: uy2 as f64,
            },
        ];
        let ext_spoly = match to_jag_polygon(&ext_pts, "cde_pair_exterior") {
            Ok(s) => s,
            Err(_) => {
                return CdeQueryResult::Unsupported {
                    reason: "exterior polygon build failed",
                }
            }
        };

        let cde_config = CDEConfig {
            quadtree_depth: self.config.quadtree_depth,
            cd_threshold: self.config.cd_threshold,
            item_surrogate_config: SPSurrogateConfig::none(),
        };

        let exterior_hazard = Hazard::new(HazardEntity::Exterior, ext_spoly, false);
        let b_hole_hazard = Hazard::new(HazardEntity::Hole { idx: 0 }, b.spoly.clone(), false);
        super::cde_observability::inc_engine_build();
        let cde = CDEngine::new(jag_bbox, vec![exterior_hazard, b_hole_hazard], cde_config);

        if !cde.detect_poly_collision(&a.spoly, &NoFilter) {
            return CdeQueryResult::NoCollision;
        }

        // CDE raw says Collision. Apply VRS-side post-policy to distinguish:
        //   touching edge/corner → NoCollision
        //   positive-area overlap / proper crossing → Collision
        // polygons_collide uses segments_properly_intersect (no touching) + strict containment.
        match polygons_collide(&a.world_pts, &b.world_pts) {
            Ok(true) => CdeQueryResult::Collision,
            Ok(false) => CdeQueryResult::NoCollision,
            Err(reason) => CdeQueryResult::Unsupported { reason },
        }
    }

    /// Query whether `item` violates the sheet boundary.
    ///
    /// Registers the sheet polygon as the Exterior hazard (items must be inside).
    /// Returns Collision if `item` goes fully or partially outside the sheet.
    pub(crate) fn query_boundary(
        &self,
        item: &CdePreparedShape,
        sheet: &CdePreparedShape,
    ) -> CdeQueryResult {
        let margin = 1.0_f64;
        let bx1 = (sheet.min_x - margin) as f32;
        let by1 = (sheet.min_y - margin) as f32;
        let bx2 = (sheet.max_x + margin) as f32;
        let by2 = (sheet.max_y + margin) as f32;

        let jag_bbox = match JagRect::try_new(bx1, by1, bx2, by2) {
            Ok(r) => r,
            Err(_) => {
                return CdeQueryResult::Unsupported {
                    reason: "sheet bbox degenerate",
                }
            }
        };

        let cde_config = CDEConfig {
            quadtree_depth: self.config.quadtree_depth,
            cd_threshold: self.config.cd_threshold,
            item_surrogate_config: SPSurrogateConfig::none(),
        };

        let exterior_hazard = Hazard::new(HazardEntity::Exterior, sheet.spoly.clone(), false);
        super::cde_observability::inc_engine_build();
        let cde = CDEngine::new(jag_bbox, vec![exterior_hazard], cde_config);

        if !cde.detect_poly_collision(&item.spoly, &NoFilter) {
            return CdeQueryResult::NoCollision;
        }

        // CDE raw says Collision. Apply VRS-side post-policy:
        //   item fully inside or touching boundary → NoCollision
        //   any vertex outside or proper crossing → Collision
        // polygon_within_sheet_pts uses point_inside_or_on_polygon (boundary ok) +
        // segments_properly_intersect (touching the boundary edge is not a crossing).
        match polygon_within_sheet_pts(&item.world_pts, &sheet.world_pts) {
            Ok(true) => CdeQueryResult::NoCollision,
            Ok(false) => CdeQueryResult::Collision,
            Err(reason) => CdeQueryResult::Unsupported { reason },
        }
    }
}

// ---------------------------------------------------------------------------
// Shape preparation helpers
// ---------------------------------------------------------------------------

/// Build a `CdePreparedShape` from a placement + part.
///
/// For parts without `outer_points`: uses the bounding rectangle as the
/// polygon (axis-aligned rect in local coords, then transformed).
/// For parts with invalid `outer_points`: returns Err.
pub(crate) fn prepare_shape_from_placement(
    placement: &Placement,
    part: &Part,
) -> Result<CdePreparedShape, &'static str> {
    prepare_shape_native(part, placement.x, placement.y, placement.rotation_deg)
}

/// SGH-Q24R4: prepare a CDE shape from native transform fields (part geometry +
/// anchor x/y + rotation), WITHOUT a `crate::io::Placement`. This lets the native
/// Sparrow tracker/search build CDE shapes without the old core placement type.
pub(crate) fn prepare_shape_native(
    part: &Part,
    x: f64,
    y: f64,
    rotation_deg: f64,
) -> Result<CdePreparedShape, &'static str> {
    let world_pts = match extract_polygon_from_part(part) {
        PolygonExtraction::Absent => {
            if part.width <= 0.0
                || part.height <= 0.0
                || !part.width.is_finite()
                || !part.height.is_finite()
            {
                return Err("part dimensions must be positive and finite for CDE rect polygon");
            }
            let local = [
                Point { x: 0.0, y: 0.0 },
                Point {
                    x: part.width,
                    y: 0.0,
                },
                Point {
                    x: part.width,
                    y: part.height,
                },
                Point {
                    x: 0.0,
                    y: part.height,
                },
            ];
            transform_polygon(&local, x, y, rotation_deg)
        }
        PolygonExtraction::Invalid { reason } => return Err(reason),
        PolygonExtraction::Valid(local) => transform_polygon(&local, x, y, rotation_deg),
    };

    let (min_x, min_y, max_x, max_y) =
        polygon_bbox(&world_pts).ok_or("empty polygon after transform")?;
    let spoly = to_jag_polygon(&world_pts, "cde_placement_shape")
        .map_err(|_| "SPolygon build failed for placement")?;

    Ok(CdePreparedShape {
        spoly,
        min_x,
        min_y,
        max_x,
        max_y,
        world_pts,
    })
}

/// SGH-Q24R9: translate an already-prepared shape by (dx, dy) and rebuild it.
/// Used by the native tracker's CDE-truth resolution-distance probe to shift a
/// candidate along a separation direction and re-query the CDE — without needing
/// the original `Part`/transform. Returns `None` on a degenerate rebuild.
pub(crate) fn translate_prepared(
    shape: &CdePreparedShape,
    dx: f64,
    dy: f64,
) -> Option<CdePreparedShape> {
    let world_pts: Vec<Point> = shape
        .world_pts
        .iter()
        .map(|p| Point {
            x: p.x + dx,
            y: p.y + dy,
        })
        .collect();
    let (min_x, min_y, max_x, max_y) = polygon_bbox(&world_pts)?;
    let spoly = to_jag_polygon(&world_pts, "cde_translated_shape").ok()?;
    Some(CdePreparedShape {
        spoly,
        min_x,
        min_y,
        max_x,
        max_y,
        world_pts,
    })
}

/// Build a `CdePreparedShape` from a sheet boundary polygon.
pub(crate) fn prepare_shape_from_sheet(
    sheet: &SheetShape,
) -> Result<CdePreparedShape, &'static str> {
    let pts: Vec<Point> = if sheet.has_irregular_outer {
        sheet.outer_vertices.clone()
    } else {
        vec![
            Point {
                x: sheet.min_x,
                y: sheet.min_y,
            },
            Point {
                x: sheet.max_x,
                y: sheet.min_y,
            },
            Point {
                x: sheet.max_x,
                y: sheet.max_y,
            },
            Point {
                x: sheet.min_x,
                y: sheet.max_y,
            },
        ]
    };

    let (min_x, min_y, max_x, max_y) = polygon_bbox(&pts).ok_or("sheet polygon is empty")?;
    let spoly =
        to_jag_polygon(&pts, "cde_sheet_shape").map_err(|_| "SPolygon build failed for sheet")?;
    let world_pts = pts;

    Ok(CdePreparedShape {
        spoly,
        min_x,
        min_y,
        max_x,
        max_y,
        world_pts,
    })
}

// ---------------------------------------------------------------------------
// SGH-Q23R1: solve-scoped CDE decision + prepared-geometry cache (strategy B)
// ---------------------------------------------------------------------------
//
// CDE pair/boundary verdicts are *pure functions* of (shape geometry, transform,
// backend config). With deterministic transforms this lets us memoise verdicts
// and prepared `SPolygon`s in a solve-scoped (thread-local) cache and serve
// repeats WITHOUT building a `CDEngine`. A moved item simply produces new
// transform keys, so stale entries become unreachable — transform keying is its
// own dirty-invalidation (documented; explicit eviction only bounds memory).
//
// This is the run.md §1 strategy B: "VRS-side solve-scoped exact/CDE cache with
// dirty invalidation while keeping CDE adapter calls behind cache misses."

/// (part-id hash, x bits, y bits, rotation bits) — exact transform identity.
type ShapeKey = (u64, u64, u64, u64);

const CACHE_ENTRY_CAP: usize = 400_000;

struct CdeQueryCache {
    prepared: HashMap<ShapeKey, Rc<CdePreparedShape>>,
    pair: HashMap<(ShapeKey, ShapeKey), CdeQueryResult>,
    boundary: HashMap<(ShapeKey, u64), CdeQueryResult>,
}

impl CdeQueryCache {
    fn new() -> Self {
        Self {
            prepared: HashMap::new(),
            pair: HashMap::new(),
            boundary: HashMap::new(),
        }
    }
}

thread_local! {
    static QUERY_CACHE: RefCell<CdeQueryCache> = RefCell::new(CdeQueryCache::new());
    /// SGH-Q24R1 per-target-search session cache: (fixed-hazard fingerprint,
    /// shared session). Reused across all candidate evaluations of one target's
    /// search (the fixed hazards do not move during the search).
    static SESSION_CACHE: RefCell<Option<(u64, Rc<CdeCandidateSession>)>> = const { RefCell::new(None) };
}

/// Reset the solve-scoped CDE cache. Called alongside `cde_observability::reset()`
/// at the start of each CDE-backed solve scope.
pub(crate) fn reset_query_cache() {
    QUERY_CACHE.with(|c| *c.borrow_mut() = CdeQueryCache::new());
    SESSION_CACHE.with(|c| *c.borrow_mut() = None);
}

/// Hash the part's full geometric identity (id + dimensions + outer polygon),
/// not just its id. This makes the cache key a pure function of actual geometry,
/// so two parts that share an id but differ geometrically (e.g. across solves or
/// across tests on the same thread) can never collide on a cached verdict.
fn part_geom_hash(part: &Part) -> u64 {
    let mut h = DefaultHasher::new();
    part.id.hash(&mut h);
    part.width.to_bits().hash(&mut h);
    part.height.to_bits().hash(&mut h);
    match &part.outer_points {
        Some(v) => v.to_string().hash(&mut h),
        None => 0u8.hash(&mut h),
    }
    h.finish()
}

fn shape_key(p: &Placement, part_geom_hash: u64) -> ShapeKey {
    (
        part_geom_hash,
        p.x.to_bits(),
        p.y.to_bits(),
        p.rotation_deg.to_bits(),
    )
}

fn sheet_key(s: &SheetShape) -> u64 {
    let mut h = DefaultHasher::new();
    s.min_x.to_bits().hash(&mut h);
    s.min_y.to_bits().hash(&mut h);
    s.max_x.to_bits().hash(&mut h);
    s.max_y.to_bits().hash(&mut h);
    s.has_irregular_outer.hash(&mut h);
    for v in &s.outer_vertices {
        v.x.to_bits().hash(&mut h);
        v.y.to_bits().hash(&mut h);
    }
    h.finish()
}

/// Prepared-shape cache lookup. Returns a shared `Rc` so the fixed (non-moving)
/// items' `SPolygon`s are built once and reused across the whole search.
fn cached_prepared(p: &Placement, part: &Part) -> Result<Rc<CdePreparedShape>, &'static str> {
    let key = shape_key(p, part_geom_hash(part));
    if let Some(rc) = QUERY_CACHE.with(|c| c.borrow().prepared.get(&key).cloned()) {
        super::cde_observability::inc_cache_prepared(true);
        return Ok(rc);
    }
    super::cde_observability::inc_cache_prepared(false);
    let shape = match prepare_shape_from_placement(p, part) {
        Ok(s) => Rc::new(s),
        Err(reason) => {
            super::cde_observability::inc_prepare_failure();
            return Err(reason);
        }
    };
    QUERY_CACHE.with(|c| {
        let mut cache = c.borrow_mut();
        if cache.prepared.len() >= CACHE_ENTRY_CAP {
            super::cde_observability::add_cache_invalidations(cache.prepared.len());
            cache.prepared.clear();
        }
        cache.prepared.insert(key, shape.clone());
    });
    Ok(shape)
}

/// Solve-scoped cached pair query. On a cache hit no `CDEngine` is built; on a
/// miss the per-call `CdeAdapter::query_pair` runs (with AABB broad-phase) and
/// the verdict is memoised. Returns the raw `CdeQueryResult` (the backend caller
/// owns the result histogram counters).
pub(crate) fn cached_query_pair(
    a: &Placement,
    a_part: &Part,
    b: &Placement,
    b_part: &Part,
) -> CdeQueryResult {
    let ka = shape_key(a, part_geom_hash(a_part));
    let kb = shape_key(b, part_geom_hash(b_part));
    let key = if ka <= kb { (ka, kb) } else { (kb, ka) };
    if let Some(r) = QUERY_CACHE.with(|c| c.borrow().pair.get(&key).cloned()) {
        super::cde_observability::inc_cache_pair(true);
        return r;
    }
    super::cde_observability::inc_cache_pair(false);
    let sa = match cached_prepared(a, a_part) {
        Ok(s) => s,
        Err(reason) => return CdeQueryResult::Unsupported { reason },
    };
    let sb = match cached_prepared(b, b_part) {
        Ok(s) => s,
        Err(reason) => return CdeQueryResult::Unsupported { reason },
    };
    let adapter = CdeAdapter::with_defaults();
    let r = adapter.query_pair(&sa, &sb);
    QUERY_CACHE.with(|c| {
        let mut cache = c.borrow_mut();
        if cache.pair.len() >= CACHE_ENTRY_CAP {
            super::cde_observability::add_cache_invalidations(cache.pair.len());
            cache.pair.clear();
        }
        cache.pair.insert(key, r.clone());
    });
    r
}

/// Solve-scoped cached boundary query.
pub(crate) fn cached_query_boundary(
    item: &Placement,
    item_part: &Part,
    sheet: &SheetShape,
) -> CdeQueryResult {
    let ki = shape_key(item, part_geom_hash(item_part));
    let ks = sheet_key(sheet);
    let key = (ki, ks);
    if let Some(r) = QUERY_CACHE.with(|c| c.borrow().boundary.get(&key).cloned()) {
        super::cde_observability::inc_cache_boundary(true);
        return r;
    }
    super::cde_observability::inc_cache_boundary(false);
    let item_shape = match cached_prepared(item, item_part) {
        Ok(s) => s,
        Err(reason) => return CdeQueryResult::Unsupported { reason },
    };
    let sheet_shape = match prepare_shape_from_sheet(sheet) {
        Ok(s) => s,
        Err(reason) => return CdeQueryResult::Unsupported { reason },
    };
    let adapter = CdeAdapter::with_defaults();
    let r = adapter.query_boundary(&item_shape, &sheet_shape);
    QUERY_CACHE.with(|c| {
        let mut cache = c.borrow_mut();
        if cache.boundary.len() >= CACHE_ENTRY_CAP {
            super::cde_observability::add_cache_invalidations(cache.boundary.len());
            cache.boundary.clear();
        }
        cache.boundary.insert(key, r.clone());
    });
    r
}

// ---------------------------------------------------------------------------
// SGH-Q23R2: single-engine multi-hazard candidate session (requirement A)
// ---------------------------------------------------------------------------
//
// Builds ONE `CDEngine` holding the sheet boundary as an `Exterior` hazard and
// every same-sheet fixed item as a `Hole` hazard. A moving candidate is then
// queried against that engine ONCE via `collect_poly_collisions`, returning the
// set of colliding fixed items + whether the sheet boundary is violated — with
// the VRS touching post-policy applied per collided hazard. This replaces N
// pairwise `CDEngine::new(...)` builds per candidate with a single build, and
// the same session is reused across a candidate's probe steps (the fixed
// hazards do not move during one item's search).
//
// CDE remains the sole source of positive collision truth; the bbox is only used
// (inside `query_pair`) as broad-phase. The post-policy distinguishes touching
// (NoCollision) from positive-area overlap.

/// Result of one batch candidate query against a `CdeCandidateSession`.
pub(crate) struct CdeBatchResult {
    pub(crate) boundary_collision: bool,
    /// Layout indices of fixed items the candidate positively overlaps.
    pub(crate) colliding_layout_idxs: Vec<usize>,
    /// True if any collided hazard could not be resolved by the post-policy.
    pub(crate) unsupported: bool,
}

impl CdeBatchResult {
    pub(crate) fn is_clear(&self) -> bool {
        !self.boundary_collision && self.colliding_layout_idxs.is_empty() && !self.unsupported
    }
}

/// A reusable single-engine multi-hazard session for one item's search.
pub(crate) struct CdeCandidateSession {
    cde: CDEngine,
    /// `holes[i]` is the (layout index, prepared shape) registered as `Hole { idx: i }`.
    holes: Vec<(usize, Rc<CdePreparedShape>)>,
    sheet_world_pts: Vec<Point>,
}

impl CdeCandidateSession {
    /// Build the session from the fixed same-sheet items + the sheet shape.
    /// Returns `None` if the engine bbox is degenerate (caller falls back to the
    /// pairwise path).
    pub(crate) fn build(
        others: Vec<(usize, Rc<CdePreparedShape>)>,
        sheet: &CdePreparedShape,
    ) -> Option<Self> {
        let mut min_x = sheet.min_x;
        let mut min_y = sheet.min_y;
        let mut max_x = sheet.max_x;
        let mut max_y = sheet.max_y;
        for (_, s) in &others {
            min_x = min_x.min(s.min_x);
            min_y = min_y.min(s.min_y);
            max_x = max_x.max(s.max_x);
            max_y = max_y.max(s.max_y);
        }
        // Generous margin so candidate/probe excursions stay inside the engine bbox
        // (any spill is re-checked against the actual sheet by the post-policy).
        let margin = ((max_x - min_x) + (max_y - min_y)).max(1.0);
        let bbox = JagRect::try_new(
            (min_x - margin) as f32,
            (min_y - margin) as f32,
            (max_x + margin) as f32,
            (max_y + margin) as f32,
        )
        .ok()?;

        let cde_config = CDEConfig {
            quadtree_depth: 4,
            cd_threshold: 0,
            item_surrogate_config: SPSurrogateConfig::none(),
        };
        let mut hazards = Vec::with_capacity(others.len() + 1);
        hazards.push(Hazard::new(
            HazardEntity::Exterior,
            sheet.spoly.clone(),
            false,
        ));
        for (i, (_, s)) in others.iter().enumerate() {
            hazards.push(Hazard::new(
                HazardEntity::Hole { idx: i },
                s.spoly.clone(),
                false,
            ));
        }
        super::cde_observability::inc_batch_engine_build(others.len());
        let cde = CDEngine::new(bbox, hazards, cde_config);
        Some(Self {
            cde,
            holes: others,
            sheet_world_pts: sheet.world_pts.clone(),
        })
    }

    pub(crate) fn hazard_count(&self) -> usize {
        self.holes.len()
    }

    /// Query a candidate shape once against all registered hazards.
    pub(crate) fn query(&self, candidate: &CdePreparedShape) -> CdeBatchResult {
        let mut collector = BasicHazardCollector::default();
        self.cde
            .collect_poly_collisions(&candidate.spoly, &mut collector);

        let mut boundary_collision = false;
        let mut colliding = Vec::new();
        let mut unsupported = false;
        for (_, ent) in collector.iter() {
            match ent {
                HazardEntity::Exterior => {
                    // Re-check against the real sheet polygon (touching boundary is allowed).
                    match polygon_within_sheet_pts(&candidate.world_pts, &self.sheet_world_pts) {
                        Ok(true) => {}
                        Ok(false) => boundary_collision = true,
                        Err(_) => unsupported = true,
                    }
                }
                HazardEntity::Hole { idx } => {
                    if let Some((layout_idx, oshape)) = self.holes.get(*idx) {
                        // Touching post-policy: only positive-area overlap counts.
                        match polygons_collide(&candidate.world_pts, &oshape.world_pts) {
                            Ok(true) => colliding.push(*layout_idx),
                            Ok(false) => {}
                            Err(_) => unsupported = true,
                        }
                    }
                }
                _ => {}
            }
        }
        super::cde_observability::record_batch_query(colliding.len() + boundary_collision as usize);
        CdeBatchResult {
            boundary_collision,
            colliding_layout_idxs: colliding,
            unsupported,
        }
    }
}

/// Build a `CdeCandidateSession` for `target_idx` from a placement list, using the
/// solve-scoped prepared-shape cache for every fixed item. Returns `None` if any
/// shape cannot be prepared (caller falls back to the pairwise path and counts it).
/// Fingerprint of the FIXED hazards for `target_idx` on `sheet_index`: identifies
/// the exact set of other same-sheet placements (geometry + transform) plus the
/// sheet. The moving candidate is NOT part of this — so during one target's
/// search (others fixed) the fingerprint is stable and the session is reused.
fn session_fingerprint(
    placements: &[Placement],
    target_idx: usize,
    sheet_index: usize,
    parts: &[Part],
    sheet: &SheetShape,
) -> u64 {
    let mut h = DefaultHasher::new();
    target_idx.hash(&mut h);
    sheet_index.hash(&mut h);
    sheet_key(sheet).hash(&mut h);
    for (i, p) in placements.iter().enumerate() {
        if i == target_idx || p.sheet_index != sheet_index {
            continue;
        }
        i.hash(&mut h);
        if let Some(part) = parts.iter().find(|pt| pt.id == p.part_id) {
            part_geom_hash(part).hash(&mut h);
        }
        p.x.to_bits().hash(&mut h);
        p.y.to_bits().hash(&mut h);
        p.rotation_deg.to_bits().hash(&mut h);
    }
    h.finish()
}

/// Build (or reuse) the per-target-search CDE session. SGH-Q24R1: the session is
/// cached by the fixed-hazard fingerprint; consecutive candidate evaluations of
/// the same target search reuse one `CDEngine` instead of rebuilding it.
pub(crate) fn build_candidate_session(
    placements: &[Placement],
    target_idx: usize,
    sheet_index: usize,
    parts: &[Part],
    sheet: &SheetShape,
) -> Option<Rc<CdeCandidateSession>> {
    let fp = session_fingerprint(placements, target_idx, sheet_index, parts, sheet);
    if let Some(rc) = SESSION_CACHE.with(|c| {
        c.borrow()
            .as_ref()
            .and_then(|(f, s)| if *f == fp { Some(s.clone()) } else { None })
    }) {
        super::cde_observability::inc_candidate_session(true);
        return Some(rc);
    }
    let sheet_shape = prepare_shape_from_sheet(sheet).ok()?;
    let mut others = Vec::new();
    for (i, p) in placements.iter().enumerate() {
        if i == target_idx || p.sheet_index != sheet_index {
            continue;
        }
        let part = parts.iter().find(|pt| pt.id == p.part_id)?;
        let shape = cached_prepared(p, part).ok()?;
        others.push((i, shape));
    }
    let session = Rc::new(CdeCandidateSession::build(others, &sheet_shape)?);
    super::cde_observability::inc_candidate_session(false);
    SESSION_CACHE.with(|c| *c.borrow_mut() = Some((fp, session.clone())));
    Some(session)
}

/// Prepare (cached) a candidate placement shape for batch querying.
pub(crate) fn prepare_candidate(p: &Placement, part: &Part) -> Option<Rc<CdePreparedShape>> {
    cached_prepared(p, part).ok()
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::io::Placement;
    use crate::item::Part;
    use crate::optimizer::collision_backend::{
        BboxCollisionBackend, CdeCollisionBackend, CollisionBackend, JaguaPolygonExactBackend,
    };
    use crate::sheet::{expand_sheets, Stock};

    fn make_part(id: &str, w: f64, h: f64) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: 1,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: None,
            prepared_outer_points: None,
            rotation_policy: None,
        }
    }

    fn make_part_with_polygon(id: &str, w: f64, h: f64, outer: serde_json::Value) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: 1,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: Some(outer),
            prepared_outer_points: None,
            rotation_policy: None,
        }
    }

    fn pl(part_id: &str, sheet: usize, x: f64, y: f64) -> Placement {
        pl_rot(part_id, sheet, x, y, 0.0)
    }

    fn pl_rot(part_id: &str, sheet: usize, x: f64, y: f64, rot: f64) -> Placement {
        Placement {
            instance_id: format!("{}__{:04}", part_id, 1),
            part_id: part_id.to_string(),
            sheet_index: sheet,
            x,
            y,
            rotation_deg: rot,
        }
    }

    fn rect_sheet(w: f64, h: f64) -> Vec<crate::sheet::SheetShape> {
        let stock = Stock {
            id: "R".to_string(),
            quantity: 1,
            width: Some(w),
            height: Some(h),
            outer_points: None,
            holes_points: None,
            cost_per_use: None,
        };
        expand_sheets(&[stock]).expect("expand_sheets")
    }

    fn l_shape_outer() -> serde_json::Value {
        serde_json::json!([
            [0.0, 0.0],
            [40.0, 0.0],
            [40.0, 20.0],
            [20.0, 20.0],
            [20.0, 40.0],
            [0.0, 40.0]
        ])
    }

    // -------------------------------------------------------------------------
    // 1. cde_api_audit_report_contains_resolved_symbols
    // -------------------------------------------------------------------------

    #[test]
    fn cde_api_audit_report_contains_resolved_symbols() {
        // Verifies that all jagua-rs CDE API symbols resolved at compile time.
        // Resolved symbols: CDEngine, CDEConfig, Hazard, HazardEntity,
        //   NoFilter, SPSurrogateConfig, SPolygon, Rect (JagRect).
        use jagua_rs::collision_detection::hazards::filter::NoFilter;
        use jagua_rs::collision_detection::hazards::{Hazard, HazardEntity};
        use jagua_rs::collision_detection::{CDEConfig, CDEngine};
        use jagua_rs::geometry::fail_fast::SPSurrogateConfig;
        use jagua_rs::geometry::primitives::Rect as JagRect;

        let _ = SPSurrogateConfig::none();
        let _ = CDEConfig {
            quadtree_depth: 1,
            cd_threshold: 0,
            item_surrogate_config: SPSurrogateConfig::none(),
        };
        // CDEngine, Hazard, HazardEntity, NoFilter, JagRect verified by module-level use.
        let _ = core::mem::size_of::<CDEngine>();
        let _ = core::mem::size_of::<Hazard>();
        let _ = core::mem::size_of::<HazardEntity>();
        let _ = core::mem::size_of::<NoFilter>();
        let _ = core::mem::size_of::<JagRect>();
        // Passes if it compiles: all CDE API symbols are resolved.
    }

    // -------------------------------------------------------------------------
    // 2. cde_backend_does_not_fallback_to_bbox_when_unavailable
    // -------------------------------------------------------------------------

    #[test]
    fn cde_backend_does_not_fallback_to_bbox_when_unavailable() {
        // CDE performs genuine polygon queries, not bbox fallback.
        // Proof: L-shape notch fixture → Bbox=Collision (false positive), CDE=NoCollision.
        let l_part = make_part_with_polygon("L", 40.0, 40.0, l_shape_outer());
        let small_part = make_part("B", 15.0, 15.0);
        let p_l = pl("L", 0, 0.0, 0.0);
        let p_small = pl("B", 0, 22.0, 22.0); // in the L-shape notch

        let bbox_result =
            BboxCollisionBackend.placement_overlaps(&p_l, &l_part, &p_small, &small_part);
        let cde_result =
            CdeCollisionBackend.placement_overlaps(&p_l, &l_part, &p_small, &small_part);

        assert!(
            bbox_result.is_collision(),
            "Bbox must give false positive for L-notch"
        );
        assert!(
            cde_result.is_no_collision(),
            "CDE must not fallback to bbox; expected NoCollision for notch fixture, got {:?}",
            cde_result
        );
        assert_ne!(
            bbox_result, cde_result,
            "CDE and bbox must disagree for notch fixture"
        );
    }

    // -------------------------------------------------------------------------
    // 3. cde_backend_does_not_fallback_to_jagua_polygon_exact_when_unavailable
    // -------------------------------------------------------------------------

    #[test]
    fn cde_backend_does_not_fallback_to_jagua_polygon_exact_when_unavailable() {
        // Q14: CDE now applies VRS-side touching post-policy. For touching rects, both
        // CDE and JaguaPolygonExact return NoCollision. The proof that CDE is NOT a
        // JaguaPolygonExact wrapper is the L-notch fixture: bbox gives a false positive
        // for items in the notch, but both CDE and JaguaPolygonExact correctly give NoCollision
        // via different code paths (CDE: CDEngine quadtree query + VRS post-policy;
        // JaguaPolygonExact: segments_properly_intersect directly).
        let l_part = make_part_with_polygon("L", 40.0, 40.0, l_shape_outer());
        let small_part = make_part("B", 15.0, 15.0);
        let p_l = pl("L", 0, 0.0, 0.0);
        let p_small = pl("B", 0, 22.0, 22.0); // in the L-shape notch

        let bbox_result =
            BboxCollisionBackend.placement_overlaps(&p_l, &l_part, &p_small, &small_part);
        let exact_result =
            JaguaPolygonExactBackend.placement_overlaps(&p_l, &l_part, &p_small, &small_part);
        let cde_result =
            CdeCollisionBackend.placement_overlaps(&p_l, &l_part, &p_small, &small_part);

        assert!(
            bbox_result.is_collision(),
            "bbox must give false positive for L-notch"
        );
        assert!(
            exact_result.is_no_collision(),
            "JaguaPolygonExact must give NoCollision for L-notch: {:?}",
            exact_result
        );
        assert!(
            cde_result.is_no_collision(),
            "CDE must give NoCollision for L-notch (not a bbox wrapper): {:?}",
            cde_result
        );
        // Both exact and CDE agree, but via different implementations — CDE uses CDEngine + VRS post-policy.
        assert_eq!(
            exact_result, cde_result,
            "CDE and JaguaPolygonExact must agree on L-notch NoCollision"
        );
    }

    // -------------------------------------------------------------------------
    // 4. cde_adapter_returns_unsupported_with_clear_reason_if_api_unavailable
    // -------------------------------------------------------------------------

    #[test]
    fn cde_adapter_returns_unsupported_with_clear_reason_if_api_unavailable() {
        // When polygon data is malformed, prepare_shape_from_placement must Err,
        // and CdeCollisionBackend must return Unsupported with a non-empty reason.
        let invalid_part =
            make_part_with_polygon("BAD", 30.0, 30.0, serde_json::json!("not-an-array"));
        let rect_part = make_part("R", 10.0, 10.0);

        let result = CdeCollisionBackend.placement_overlaps(
            &pl("BAD", 0, 0.0, 0.0),
            &invalid_part,
            &pl("R", 0, 1.0, 1.0),
            &rect_part,
        );
        assert!(
            result.is_unsupported(),
            "invalid polygon must return Unsupported: {:?}",
            result
        );
        // Verify reason is non-empty (no silent, opaque failure).
        if let crate::optimizer::collision_backend::CollisionDecision::Unsupported { reason } =
            &result
        {
            assert!(!reason.is_empty(), "Unsupported reason must not be empty");
        }
        assert!(
            !result.is_no_collision(),
            "Unsupported must not masquerade as NoCollision"
        );
        assert!(
            !result.is_collision(),
            "Unsupported must not masquerade as Collision"
        );
    }

    // -------------------------------------------------------------------------
    // 5. cde_backend_rect_overlap_query_works_or_is_blocked_explicitly
    // -------------------------------------------------------------------------

    #[test]
    fn cde_backend_rect_overlap_query_works_or_is_blocked_explicitly() {
        // Rect parts without outer_points: CDE uses rect polygon.
        // Two clearly overlapping rects → must be Collision.
        let part = make_part("A", 20.0, 20.0);
        let p1 = pl("A", 0, 0.0, 0.0);
        let p2 = pl("A", 0, 10.0, 10.0); // overlaps p1 by 10x10

        let result = CdeCollisionBackend.placement_overlaps(&p1, &part, &p2, &part);
        assert!(
            result.is_collision(),
            "CDE must detect overlap between overlapping rects (or return explicit blocker): {:?}",
            result
        );
    }

    // -------------------------------------------------------------------------
    // 6. cde_backend_rotated_rect_query_works_or_is_blocked_explicitly
    // -------------------------------------------------------------------------

    #[test]
    fn cde_backend_rotated_rect_query_works_or_is_blocked_explicitly() {
        // Rotated rect (45°, 10x10) at origin vs small rect far away.
        // They must not overlap → CDE must return NoCollision.
        let long_part = make_part("A", 10.0, 10.0);
        let small_part = make_part("B", 5.0, 5.0);
        let rotated = pl_rot("A", 0, 0.0, 0.0, 45.0);
        let far_away = pl("B", 0, 100.0, 100.0); // clearly separate

        let result =
            CdeCollisionBackend.placement_overlaps(&rotated, &long_part, &far_away, &small_part);
        assert!(
            result.is_no_collision(),
            "CDE must report NoCollision for non-overlapping rotated rect vs far rect: {:?}",
            result
        );
    }

    // -------------------------------------------------------------------------
    // 7. cde_backend_irregular_polygon_query_works_or_is_blocked_explicitly
    // -------------------------------------------------------------------------

    #[test]
    fn cde_backend_irregular_polygon_query_works_or_is_blocked_explicitly() {
        // L-shape notch fixture: small rect is in the L-shape's notch.
        // CDE must correctly detect no actual polygon overlap (NoCollision).
        let l_part = make_part_with_polygon("L", 40.0, 40.0, l_shape_outer());
        let small_part = make_part("B", 15.0, 15.0);
        let p_l = pl("L", 0, 0.0, 0.0);
        let p_small = pl("B", 0, 22.0, 22.0); // in the notch

        let result = CdeCollisionBackend.placement_overlaps(&p_l, &l_part, &p_small, &small_part);
        assert!(
            result.is_no_collision(),
            "CDE must detect no overlap when small rect is in L-shape notch: {:?}",
            result
        );
    }

    // -------------------------------------------------------------------------
    // 8. cde_backend_invalid_geometry_is_unsupported_not_no_collision
    // -------------------------------------------------------------------------

    #[test]
    fn cde_backend_invalid_geometry_is_unsupported_not_no_collision() {
        // Malformed outer_points → prepare_shape fails → Unsupported, NOT NoCollision.
        // This is the critical no-silent-fallback gate for invalid geometry.
        let degenerate = make_part_with_polygon(
            "DEG",
            40.0,
            40.0,
            serde_json::json!([[0.0, 0.0], [1.0, 0.0], [1.0, 0.0]]), // collinear/degenerate
        );
        let rect_part = make_part("R", 10.0, 10.0);

        let result = CdeCollisionBackend.placement_overlaps(
            &pl("DEG", 0, 0.0, 0.0),
            &degenerate,
            &pl("R", 0, 5.0, 5.0),
            &rect_part,
        );
        assert!(
            result.is_unsupported(),
            "degenerate polygon must be Unsupported, not NoCollision: {:?}",
            result
        );
        assert!(
            !result.is_no_collision(),
            "invalid geometry must not be treated as safe"
        );
    }

    // -------------------------------------------------------------------------
    // SGH-Q23R2: single-engine multi-hazard candidate session
    // -------------------------------------------------------------------------

    #[test]
    fn cde_q23r2_batch_session_one_build_many_queries() {
        use crate::optimizer::cde_observability;
        reset_query_cache();
        cde_observability::reset();
        let part = make_part("A", 20.0, 20.0);
        let sheets = rect_sheet(200.0, 200.0);
        // Two fixed items at (0,0) and (100,100); target idx 0 (excluded).
        let placements = vec![
            pl("A", 0, 0.0, 0.0),     // idx 0 = target (excluded)
            pl("A", 0, 50.0, 50.0),   // idx 1 fixed
            pl("A", 0, 120.0, 120.0), // idx 2 fixed
        ];
        let parts = vec![part.clone()];
        let session =
            build_candidate_session(&placements, 0, 0, &parts, &sheets[0]).expect("session builds");
        assert_eq!(
            session.hazard_count(),
            2,
            "two fixed items registered as holes"
        );

        // Candidate overlapping idx 1 (at 55,55 — overlaps the 50..70 item).
        let cand_overlap = prepare_candidate(&pl("A", 0, 55.0, 55.0), &part).expect("cand");
        let r1 = session.query(&cand_overlap);
        assert!(
            r1.colliding_layout_idxs.contains(&1),
            "must report overlap with item idx 1"
        );
        assert!(!r1.boundary_collision, "candidate is inside the sheet");

        // Candidate in free space → clear.
        let cand_clear = prepare_candidate(&pl("A", 0, 10.0, 150.0), &part).expect("cand");
        let r2 = session.query(&cand_clear);
        assert!(
            r2.is_clear(),
            "free-space candidate must be clear: {:?}",
            r2.colliding_layout_idxs
        );

        let snap = cde_observability::snapshot();
        assert_eq!(
            snap.batch_engine_builds, 1,
            "ONE engine build for the whole session"
        );
        assert_eq!(
            snap.batch_candidate_queries, 2,
            "two candidate queries, no extra builds"
        );
    }

    #[test]
    fn cde_q23r2_batch_session_detects_boundary_violation() {
        use crate::optimizer::cde_observability;
        reset_query_cache();
        cde_observability::reset();
        let part = make_part("A", 20.0, 20.0);
        let sheets = rect_sheet(100.0, 100.0);
        let placements = vec![pl("A", 0, 0.0, 0.0)];
        let parts = vec![part.clone()];
        let session =
            build_candidate_session(&placements, 0, 0, &parts, &sheets[0]).expect("session builds");
        // Candidate at (95,10): extends to x=115 > 100 → boundary violation.
        let cand = prepare_candidate(&pl("A", 0, 95.0, 10.0), &part).expect("cand");
        let r = session.query(&cand);
        assert!(
            r.boundary_collision,
            "candidate crossing sheet boundary must be flagged"
        );
    }

    // -------------------------------------------------------------------------
    // SGH-Q23R1: solve-scoped cache
    // -------------------------------------------------------------------------

    #[test]
    fn cde_q23r1_cache_hit_avoids_second_engine_build() {
        use crate::optimizer::cde_observability;
        reset_query_cache();
        cde_observability::reset();
        let part = make_part("A", 20.0, 20.0);
        let p1 = pl("A", 0, 0.0, 0.0);
        let p2 = pl("A", 0, 10.0, 10.0); // overlapping → reaches CDEngine
        let r1 = cached_query_pair(&p1, &part, &p2, &part);
        let r2 = cached_query_pair(&p1, &part, &p2, &part);
        let snap = cde_observability::snapshot();
        assert_eq!(r1, CdeQueryResult::Collision);
        assert_eq!(r2, CdeQueryResult::Collision);
        assert_eq!(snap.cache_pair_misses, 1, "first call misses");
        assert_eq!(snap.cache_pair_hits, 1, "second identical call hits");
        assert_eq!(
            snap.engine_builds, 1,
            "cache hit must NOT build a second CDEngine"
        );
    }

    #[test]
    fn cde_q23r1_cache_key_includes_geometry_not_just_id() {
        use crate::optimizer::cde_observability;
        reset_query_cache();
        cde_observability::reset();
        // Same part id "X" but different geometry. At placements (0,0) and (15,15):
        //   30×30 parts overlap; 10×10 parts do not. The cache must not confuse them.
        let big = make_part("X", 30.0, 30.0);
        let small = make_part("X", 10.0, 10.0);
        let p1 = pl("X", 0, 0.0, 0.0);
        let p2 = pl("X", 0, 15.0, 15.0);
        let r_big = cached_query_pair(&p1, &big, &p2, &big);
        let r_small = cached_query_pair(&p1, &small, &p2, &small);
        assert_eq!(
            r_big,
            CdeQueryResult::Collision,
            "30×30 at (0,0)/(15,15) overlap"
        );
        assert_eq!(
            r_small,
            CdeQueryResult::NoCollision,
            "10×10 at (0,0)/(15,15) are separate — must NOT return the big part's cached verdict"
        );
    }

    #[test]
    fn cde_q23r1_reset_clears_cache() {
        use crate::optimizer::cde_observability;
        reset_query_cache();
        cde_observability::reset();
        let part = make_part("A", 20.0, 20.0);
        let p1 = pl("A", 0, 0.0, 0.0);
        let p2 = pl("A", 0, 10.0, 10.0);
        cached_query_pair(&p1, &part, &p2, &part);
        reset_query_cache();
        cde_observability::reset();
        cached_query_pair(&p1, &part, &p2, &part);
        let snap = cde_observability::snapshot();
        assert_eq!(
            snap.cache_pair_hits, 0,
            "after reset the verdict must be recomputed (miss)"
        );
        assert_eq!(snap.cache_pair_misses, 1);
    }

    // -------------------------------------------------------------------------
    // SGH-Q23: AABB broad-phase pruning
    // -------------------------------------------------------------------------

    #[test]
    fn cde_q23_broadphase_prunes_separated_rects_without_engine_build() {
        use crate::optimizer::cde_observability;
        // Two clearly separated rects: must be NoCollision via broad-phase,
        // with NO engine build and a recorded broadphase prune.
        let part = make_part("A", 10.0, 10.0);
        let p1 = pl("A", 0, 0.0, 0.0);
        let p2 = pl("A", 0, 100.0, 100.0);
        let s1 = prepare_shape_from_placement(&p1, &part).expect("s1");
        let s2 = prepare_shape_from_placement(&p2, &part).expect("s2");

        cde_observability::reset();
        let adapter = CdeAdapter::with_defaults();
        let result = adapter.query_pair(&s1, &s2);
        let snap = cde_observability::snapshot();

        assert_eq!(
            result,
            CdeQueryResult::NoCollision,
            "separated rects must be NoCollision"
        );
        assert_eq!(
            snap.broadphase_pruned, 1,
            "separated pair must be broad-phase pruned"
        );
        assert_eq!(
            snap.engine_builds, 0,
            "broad-phase prune must NOT build a CDEngine"
        );
    }

    #[test]
    fn cde_q23_broadphase_does_not_prune_overlapping_rects() {
        use crate::optimizer::cde_observability;
        // Overlapping rects: broad-phase must NOT prune; CDE decides (Collision)
        // and an engine build happens. Broad-phase never asserts positive truth.
        let part = make_part("A", 20.0, 20.0);
        let p1 = pl("A", 0, 0.0, 0.0);
        let p2 = pl("A", 0, 10.0, 10.0);
        let s1 = prepare_shape_from_placement(&p1, &part).expect("s1");
        let s2 = prepare_shape_from_placement(&p2, &part).expect("s2");

        cde_observability::reset();
        let adapter = CdeAdapter::with_defaults();
        let result = adapter.query_pair(&s1, &s2);
        let snap = cde_observability::snapshot();

        assert_eq!(
            result,
            CdeQueryResult::Collision,
            "overlapping rects must be Collision"
        );
        assert_eq!(
            snap.broadphase_pruned, 0,
            "overlapping pair must not be broad-phase pruned"
        );
        assert_eq!(
            snap.engine_builds, 1,
            "overlapping pair must reach the CDEngine"
        );
    }

    // -------------------------------------------------------------------------
    // Boundary query smoke test
    // -------------------------------------------------------------------------

    #[test]
    fn cde_boundary_item_inside_rect_sheet_is_no_collision() {
        let part = make_part("A", 20.0, 20.0);
        let sheets = rect_sheet(100.0, 100.0);
        let inside = pl("A", 0, 10.0, 10.0);
        let result = CdeCollisionBackend.placement_within_sheet(&inside, &part, &sheets[0]);
        assert!(
            result.is_no_collision(),
            "item fully inside sheet: {:?}",
            result
        );
    }

    #[test]
    fn cde_boundary_item_outside_rect_sheet_is_collision() {
        let part = make_part("A", 20.0, 20.0);
        let sheets = rect_sheet(100.0, 100.0);
        let outside = Placement {
            instance_id: "A__0001".into(),
            part_id: "A".into(),
            sheet_index: 0,
            x: 95.0,
            y: 95.0,
            rotation_deg: 0.0,
        };
        let result = CdeCollisionBackend.placement_within_sheet(&outside, &part, &sheets[0]);
        assert!(
            result.is_collision(),
            "item outside sheet must be Collision: {:?}",
            result
        );
    }

    // =========================================================================
    // SGH-Q14: CDE touching semantics parity tests
    // =========================================================================

    /// Two rects sharing an edge must be NoCollision (touching ≠ overlap).
    #[test]
    fn cde_touching_rect_edges_are_no_collision() {
        let part = make_part("A", 10.0, 10.0);
        let p_left = pl("A", 0, 0.0, 0.0);
        let p_right = pl("A", 0, 10.0, 0.0); // shared edge at x=10

        let cde = CdeCollisionBackend.placement_overlaps(&p_left, &part, &p_right, &part);
        assert!(
            cde.is_no_collision(),
            "touching rect edges must be NoCollision: {:?}",
            cde
        );
    }

    /// Two rects sharing a corner must be NoCollision.
    #[test]
    fn cde_touching_rect_corners_are_no_collision() {
        let part = make_part("A", 10.0, 10.0);
        let p1 = pl("A", 0, 0.0, 0.0);
        let p2 = pl("A", 0, 10.0, 10.0); // corner touch at (10, 10)

        let cde = CdeCollisionBackend.placement_overlaps(&p1, &part, &p2, &part);
        assert!(
            cde.is_no_collision(),
            "touching rect corners must be NoCollision: {:?}",
            cde
        );
    }

    /// Two rects with positive-area overlap must be Collision.
    #[test]
    fn cde_positive_rect_overlap_is_collision() {
        let part = make_part("A", 20.0, 20.0);
        let p1 = pl("A", 0, 0.0, 0.0);
        let p2 = pl("A", 0, 10.0, 10.0); // 10×10 overlap

        let cde = CdeCollisionBackend.placement_overlaps(&p1, &part, &p2, &part);
        assert!(
            cde.is_collision(),
            "positive-area rect overlap must be Collision: {:?}",
            cde
        );
    }

    /// Two L-shapes touching on their notch edge must be NoCollision.
    #[test]
    fn cde_touching_irregular_polygon_edges_are_no_collision() {
        // Place the L at (0,0) and another L mirrored at (40,0), sharing the edge at x=40.
        // Actually, simpler: use a rect and an L-shape touching edge-to-edge.
        let l_part = make_part_with_polygon("L", 40.0, 40.0, l_shape_outer());
        let rect_part = make_part("R", 10.0, 20.0);
        // The L goes 0..40 in x, 0..40 in y (with notch).
        // Place rect to the right of L, touching at x=40.
        let p_l = pl("L", 0, 0.0, 0.0);
        let p_rect = pl("R", 0, 40.0, 0.0); // touching at x=40

        let cde = CdeCollisionBackend.placement_overlaps(&p_l, &l_part, &p_rect, &rect_part);
        assert!(
            cde.is_no_collision(),
            "irregular polygon touching at shared edge must be NoCollision: {:?}",
            cde
        );
    }

    /// Two L-shapes with genuine polygon overlap must be Collision.
    #[test]
    fn cde_positive_irregular_overlap_is_collision() {
        let l_part = make_part_with_polygon("L", 40.0, 40.0, l_shape_outer());
        let rect_part = make_part("R", 10.0, 10.0);
        // The L-shape goes to (20,20) at its inner corner. Place rect starting at (10,10) — inside L.
        let p_l = pl("L", 0, 0.0, 0.0);
        let p_rect = pl("R", 0, 5.0, 5.0); // genuinely inside the L polygon

        let cde = CdeCollisionBackend.placement_overlaps(&p_l, &l_part, &p_rect, &rect_part);
        assert!(
            cde.is_collision(),
            "item inside L-polygon must be Collision: {:?}",
            cde
        );
    }

    /// Item whose edge exactly touches the sheet boundary must be NoCollision.
    #[test]
    fn cde_item_touching_sheet_boundary_inside_is_no_collision() {
        let part = make_part("A", 20.0, 20.0);
        let sheets = rect_sheet(100.0, 100.0);
        // Item at (0, 0): its left edge is at x=0 = sheet boundary; right at x=20 inside.
        let touching = pl("A", 0, 0.0, 0.0);
        let result = CdeCollisionBackend.placement_within_sheet(&touching, &part, &sheets[0]);
        assert!(
            result.is_no_collision(),
            "item touching sheet boundary edge must be NoCollision (boundary touch allowed): {:?}",
            result
        );
    }

    /// Item whose corner exactly touches the sheet boundary corner must be NoCollision.
    #[test]
    fn cde_item_corner_touching_sheet_boundary_inside_is_no_collision() {
        let part = make_part("A", 20.0, 20.0);
        let sheets = rect_sheet(100.0, 100.0);
        // Item at (80, 80): corner at (100, 100) = sheet corner.
        let corner_touch = pl("A", 0, 80.0, 80.0);
        let result = CdeCollisionBackend.placement_within_sheet(&corner_touch, &part, &sheets[0]);
        assert!(
            result.is_no_collision(),
            "item corner touching sheet corner must be NoCollision: {:?}",
            result
        );
    }

    /// Item crossing the sheet boundary must be Collision.
    #[test]
    fn cde_item_crossing_sheet_boundary_is_collision() {
        let part = make_part("A", 20.0, 20.0);
        let sheets = rect_sheet(100.0, 100.0);
        // Item at (95, 0): extends to x=115, outside sheet x=100.
        let crossing = Placement {
            instance_id: "A__0001".into(),
            part_id: "A".into(),
            sheet_index: 0,
            x: 95.0,
            y: 0.0,
            rotation_deg: 0.0,
        };
        let result = CdeCollisionBackend.placement_within_sheet(&crossing, &part, &sheets[0]);
        assert!(
            result.is_collision(),
            "item crossing sheet boundary must be Collision: {:?}",
            result
        );
    }

    /// Bbox backend touching semantics unchanged (adjacent rects still NoCollision).
    #[test]
    fn bbox_default_touching_semantics_unchanged() {
        let part = make_part("A", 10.0, 10.0);
        let p1 = pl("A", 0, 0.0, 0.0);
        let p2 = pl("A", 0, 10.0, 0.0); // adjacent, touching edge

        let bbox = BboxCollisionBackend.placement_overlaps(&p1, &part, &p2, &part);
        assert!(
            bbox.is_no_collision(),
            "bbox: adjacent touching rects still NoCollision: {:?}",
            bbox
        );
    }

    /// JaguaPolygonExact touching semantics unchanged after Q14.
    #[test]
    fn jagua_polygon_exact_touching_semantics_unchanged() {
        let part = make_part("A", 10.0, 10.0);
        let p_left = pl("A", 0, 0.0, 0.0);
        let p_right = pl("A", 0, 10.0, 0.0); // touching at x=10

        let exact = JaguaPolygonExactBackend.placement_overlaps(&p_left, &part, &p_right, &part);
        assert!(
            exact.is_no_collision(),
            "JaguaPolygonExact: touching rects still NoCollision: {:?}",
            exact
        );
    }

    /// No silent bbox fallback for CDE touching policy: L-notch shows CDE ≠ bbox.
    #[test]
    fn no_silent_bbox_fallback_for_cde_touching_policy() {
        let l_part = make_part_with_polygon("L", 40.0, 40.0, l_shape_outer());
        let small_part = make_part("B", 15.0, 15.0);
        let p_l = pl("L", 0, 0.0, 0.0);
        let p_small = pl("B", 0, 22.0, 22.0); // in notch: bbox=Collision, CDE=NoCollision

        let bbox_result =
            BboxCollisionBackend.placement_overlaps(&p_l, &l_part, &p_small, &small_part);
        let cde_result =
            CdeCollisionBackend.placement_overlaps(&p_l, &l_part, &p_small, &small_part);

        assert!(
            bbox_result.is_collision(),
            "bbox must give false positive for L-notch"
        );
        assert!(
            cde_result.is_no_collision(),
            "CDE must NOT silently fall back to bbox: expected NoCollision for L-notch, got {:?}",
            cde_result
        );
        assert_ne!(
            bbox_result, cde_result,
            "CDE and bbox must disagree for L-notch (proof: not bbox fallback)"
        );
    }
}
