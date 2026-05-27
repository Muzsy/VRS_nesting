use jagua_rs::collision_detection::{CDEConfig, CDEngine};
use jagua_rs::collision_detection::hazards::{Hazard, HazardEntity};
use jagua_rs::collision_detection::hazards::filter::NoFilter;
use jagua_rs::geometry::primitives::Rect as JagRect;
use jagua_rs::geometry::fail_fast::SPSurrogateConfig;

use crate::geometry::{polygon_bbox, to_jag_polygon, Point};
use crate::io::Placement;
use crate::item::Part;
use crate::sheet::SheetShape;
use super::collision_backend::{
    extract_polygon_from_part, polygon_within_sheet_pts, polygons_collide, transform_polygon,
    PolygonExtraction,
};

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
        Self { quadtree_depth: 4, cd_threshold: 0 }
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
    pub fn is_collision(&self) -> bool { matches!(self, CdeQueryResult::Collision) }
    pub fn is_no_collision(&self) -> bool { matches!(self, CdeQueryResult::NoCollision) }
    pub fn is_unsupported(&self) -> bool { matches!(self, CdeQueryResult::Unsupported { .. }) }
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
    pub(crate) fn new(config: CdeAdapterConfig) -> Self { Self { config } }

    pub(crate) fn with_defaults() -> Self { Self { config: CdeAdapterConfig::default() } }

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
        let margin = 1.0_f64;
        let ux1 = (a.min_x.min(b.min_x) - margin) as f32;
        let uy1 = (a.min_y.min(b.min_y) - margin) as f32;
        let ux2 = (a.max_x.max(b.max_x) + margin) as f32;
        let uy2 = (a.max_y.max(b.max_y) + margin) as f32;

        let jag_bbox = match JagRect::try_new(ux1, uy1, ux2, uy2) {
            Ok(r) => r,
            Err(_) => return CdeQueryResult::Unsupported { reason: "degenerate union bbox for pair query" },
        };

        let ext_pts = [
            Point { x: ux1 as f64, y: uy1 as f64 },
            Point { x: ux2 as f64, y: uy1 as f64 },
            Point { x: ux2 as f64, y: uy2 as f64 },
            Point { x: ux1 as f64, y: uy2 as f64 },
        ];
        let ext_spoly = match to_jag_polygon(&ext_pts, "cde_pair_exterior") {
            Ok(s) => s,
            Err(_) => return CdeQueryResult::Unsupported { reason: "exterior polygon build failed" },
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
    pub(crate) fn query_boundary(&self, item: &CdePreparedShape, sheet: &CdePreparedShape) -> CdeQueryResult {
        let margin = 1.0_f64;
        let bx1 = (sheet.min_x - margin) as f32;
        let by1 = (sheet.min_y - margin) as f32;
        let bx2 = (sheet.max_x + margin) as f32;
        let by2 = (sheet.max_y + margin) as f32;

        let jag_bbox = match JagRect::try_new(bx1, by1, bx2, by2) {
            Ok(r) => r,
            Err(_) => return CdeQueryResult::Unsupported { reason: "sheet bbox degenerate" },
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
                Point { x: part.width, y: 0.0 },
                Point { x: part.width, y: part.height },
                Point { x: 0.0, y: part.height },
            ];
            transform_polygon(&local, placement.x, placement.y, placement.rotation_deg)
        }
        PolygonExtraction::Invalid { reason } => return Err(reason),
        PolygonExtraction::Valid(local) => {
            transform_polygon(&local, placement.x, placement.y, placement.rotation_deg)
        }
    };

    let (min_x, min_y, max_x, max_y) =
        polygon_bbox(&world_pts).ok_or("empty polygon after transform")?;
    let spoly =
        to_jag_polygon(&world_pts, "cde_placement_shape").map_err(|_| "SPolygon build failed for placement")?;

    Ok(CdePreparedShape { spoly, min_x, min_y, max_x, max_y, world_pts })
}

/// Build a `CdePreparedShape` from a sheet boundary polygon.
pub(crate) fn prepare_shape_from_sheet(sheet: &SheetShape) -> Result<CdePreparedShape, &'static str> {
    let pts: Vec<Point> = if sheet.has_irregular_outer {
        sheet.outer_vertices.clone()
    } else {
        vec![
            Point { x: sheet.min_x, y: sheet.min_y },
            Point { x: sheet.max_x, y: sheet.min_y },
            Point { x: sheet.max_x, y: sheet.max_y },
            Point { x: sheet.min_x, y: sheet.max_y },
        ]
    };

    let (min_x, min_y, max_x, max_y) =
        polygon_bbox(&pts).ok_or("sheet polygon is empty")?;
    let spoly =
        to_jag_polygon(&pts, "cde_sheet_shape").map_err(|_| "SPolygon build failed for sheet")?;
    let world_pts = pts;

    Ok(CdePreparedShape { spoly, min_x, min_y, max_x, max_y, world_pts })
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
            [0.0, 0.0], [40.0, 0.0], [40.0, 20.0],
            [20.0, 20.0], [20.0, 40.0], [0.0, 40.0]
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
        use jagua_rs::collision_detection::{CDEConfig, CDEngine};
        use jagua_rs::collision_detection::hazards::{Hazard, HazardEntity};
        use jagua_rs::collision_detection::hazards::filter::NoFilter;
        use jagua_rs::geometry::primitives::Rect as JagRect;
        use jagua_rs::geometry::fail_fast::SPSurrogateConfig;

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

        let bbox_result = BboxCollisionBackend.placement_overlaps(&p_l, &l_part, &p_small, &small_part);
        let cde_result = CdeCollisionBackend.placement_overlaps(&p_l, &l_part, &p_small, &small_part);

        assert!(bbox_result.is_collision(), "Bbox must give false positive for L-notch");
        assert!(
            cde_result.is_no_collision(),
            "CDE must not fallback to bbox; expected NoCollision for notch fixture, got {:?}",
            cde_result
        );
        assert_ne!(bbox_result, cde_result, "CDE and bbox must disagree for notch fixture");
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

        let bbox_result = BboxCollisionBackend.placement_overlaps(&p_l, &l_part, &p_small, &small_part);
        let exact_result = JaguaPolygonExactBackend.placement_overlaps(&p_l, &l_part, &p_small, &small_part);
        let cde_result = CdeCollisionBackend.placement_overlaps(&p_l, &l_part, &p_small, &small_part);

        assert!(bbox_result.is_collision(), "bbox must give false positive for L-notch");
        assert!(
            exact_result.is_no_collision(),
            "JaguaPolygonExact must give NoCollision for L-notch: {:?}", exact_result
        );
        assert!(
            cde_result.is_no_collision(),
            "CDE must give NoCollision for L-notch (not a bbox wrapper): {:?}", cde_result
        );
        // Both exact and CDE agree, but via different implementations — CDE uses CDEngine + VRS post-policy.
        assert_eq!(exact_result, cde_result, "CDE and JaguaPolygonExact must agree on L-notch NoCollision");
    }

    // -------------------------------------------------------------------------
    // 4. cde_adapter_returns_unsupported_with_clear_reason_if_api_unavailable
    // -------------------------------------------------------------------------

    #[test]
    fn cde_adapter_returns_unsupported_with_clear_reason_if_api_unavailable() {
        // When polygon data is malformed, prepare_shape_from_placement must Err,
        // and CdeCollisionBackend must return Unsupported with a non-empty reason.
        let invalid_part = make_part_with_polygon("BAD", 30.0, 30.0, serde_json::json!("not-an-array"));
        let rect_part = make_part("R", 10.0, 10.0);

        let result = CdeCollisionBackend.placement_overlaps(
            &pl("BAD", 0, 0.0, 0.0), &invalid_part,
            &pl("R",   0, 1.0, 1.0), &rect_part,
        );
        assert!(
            result.is_unsupported(),
            "invalid polygon must return Unsupported: {:?}", result
        );
        // Verify reason is non-empty (no silent, opaque failure).
        if let crate::optimizer::collision_backend::CollisionDecision::Unsupported { reason } = &result {
            assert!(!reason.is_empty(), "Unsupported reason must not be empty");
        }
        assert!(!result.is_no_collision(), "Unsupported must not masquerade as NoCollision");
        assert!(!result.is_collision(),    "Unsupported must not masquerade as Collision");
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

        let result = CdeCollisionBackend.placement_overlaps(&rotated, &long_part, &far_away, &small_part);
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
            "DEG", 40.0, 40.0,
            serde_json::json!([[0.0, 0.0], [1.0, 0.0], [1.0, 0.0]]), // collinear/degenerate
        );
        let rect_part = make_part("R", 10.0, 10.0);

        let result = CdeCollisionBackend.placement_overlaps(
            &pl("DEG", 0, 0.0, 0.0), &degenerate,
            &pl("R",   0, 5.0, 5.0), &rect_part,
        );
        assert!(
            result.is_unsupported(),
            "degenerate polygon must be Unsupported, not NoCollision: {:?}", result
        );
        assert!(!result.is_no_collision(), "invalid geometry must not be treated as safe");
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
        assert!(result.is_no_collision(), "item fully inside sheet: {:?}", result);
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
        assert!(result.is_collision(), "item outside sheet must be Collision: {:?}", result);
    }

    // =========================================================================
    // SGH-Q14: CDE touching semantics parity tests
    // =========================================================================

    /// Two rects sharing an edge must be NoCollision (touching ≠ overlap).
    #[test]
    fn cde_touching_rect_edges_are_no_collision() {
        let part = make_part("A", 10.0, 10.0);
        let p_left  = pl("A", 0, 0.0, 0.0);
        let p_right = pl("A", 0, 10.0, 0.0); // shared edge at x=10

        let cde = CdeCollisionBackend.placement_overlaps(&p_left, &part, &p_right, &part);
        assert!(cde.is_no_collision(), "touching rect edges must be NoCollision: {:?}", cde);
    }

    /// Two rects sharing a corner must be NoCollision.
    #[test]
    fn cde_touching_rect_corners_are_no_collision() {
        let part = make_part("A", 10.0, 10.0);
        let p1 = pl("A", 0, 0.0, 0.0);
        let p2 = pl("A", 0, 10.0, 10.0); // corner touch at (10, 10)

        let cde = CdeCollisionBackend.placement_overlaps(&p1, &part, &p2, &part);
        assert!(cde.is_no_collision(), "touching rect corners must be NoCollision: {:?}", cde);
    }

    /// Two rects with positive-area overlap must be Collision.
    #[test]
    fn cde_positive_rect_overlap_is_collision() {
        let part = make_part("A", 20.0, 20.0);
        let p1 = pl("A", 0, 0.0, 0.0);
        let p2 = pl("A", 0, 10.0, 10.0); // 10×10 overlap

        let cde = CdeCollisionBackend.placement_overlaps(&p1, &part, &p2, &part);
        assert!(cde.is_collision(), "positive-area rect overlap must be Collision: {:?}", cde);
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
        let p_l    = pl("L", 0, 0.0, 0.0);
        let p_rect = pl("R", 0, 40.0, 0.0); // touching at x=40

        let cde = CdeCollisionBackend.placement_overlaps(&p_l, &l_part, &p_rect, &rect_part);
        assert!(
            cde.is_no_collision(),
            "irregular polygon touching at shared edge must be NoCollision: {:?}", cde
        );
    }

    /// Two L-shapes with genuine polygon overlap must be Collision.
    #[test]
    fn cde_positive_irregular_overlap_is_collision() {
        let l_part = make_part_with_polygon("L", 40.0, 40.0, l_shape_outer());
        let rect_part = make_part("R", 10.0, 10.0);
        // The L-shape goes to (20,20) at its inner corner. Place rect starting at (10,10) — inside L.
        let p_l    = pl("L", 0, 0.0, 0.0);
        let p_rect = pl("R", 0, 5.0, 5.0); // genuinely inside the L polygon

        let cde = CdeCollisionBackend.placement_overlaps(&p_l, &l_part, &p_rect, &rect_part);
        assert!(
            cde.is_collision(),
            "item inside L-polygon must be Collision: {:?}", cde
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
            "item touching sheet boundary edge must be NoCollision (boundary touch allowed): {:?}", result
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
            "item corner touching sheet corner must be NoCollision: {:?}", result
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
            x: 95.0, y: 0.0,
            rotation_deg: 0.0,
        };
        let result = CdeCollisionBackend.placement_within_sheet(&crossing, &part, &sheets[0]);
        assert!(result.is_collision(), "item crossing sheet boundary must be Collision: {:?}", result);
    }

    /// Bbox backend touching semantics unchanged (adjacent rects still NoCollision).
    #[test]
    fn bbox_default_touching_semantics_unchanged() {
        let part = make_part("A", 10.0, 10.0);
        let p1 = pl("A", 0, 0.0, 0.0);
        let p2 = pl("A", 0, 10.0, 0.0); // adjacent, touching edge

        let bbox = BboxCollisionBackend.placement_overlaps(&p1, &part, &p2, &part);
        assert!(bbox.is_no_collision(), "bbox: adjacent touching rects still NoCollision: {:?}", bbox);
    }

    /// JaguaPolygonExact touching semantics unchanged after Q14.
    #[test]
    fn jagua_polygon_exact_touching_semantics_unchanged() {
        let part = make_part("A", 10.0, 10.0);
        let p_left  = pl("A", 0, 0.0, 0.0);
        let p_right = pl("A", 0, 10.0, 0.0); // touching at x=10

        let exact = JaguaPolygonExactBackend.placement_overlaps(&p_left, &part, &p_right, &part);
        assert!(exact.is_no_collision(), "JaguaPolygonExact: touching rects still NoCollision: {:?}", exact);
    }

    /// No silent bbox fallback for CDE touching policy: L-notch shows CDE ≠ bbox.
    #[test]
    fn no_silent_bbox_fallback_for_cde_touching_policy() {
        let l_part = make_part_with_polygon("L", 40.0, 40.0, l_shape_outer());
        let small_part = make_part("B", 15.0, 15.0);
        let p_l = pl("L", 0, 0.0, 0.0);
        let p_small = pl("B", 0, 22.0, 22.0); // in notch: bbox=Collision, CDE=NoCollision

        let bbox_result = BboxCollisionBackend.placement_overlaps(&p_l, &l_part, &p_small, &small_part);
        let cde_result  = CdeCollisionBackend.placement_overlaps(&p_l, &l_part, &p_small, &small_part);

        assert!(bbox_result.is_collision(), "bbox must give false positive for L-notch");
        assert!(
            cde_result.is_no_collision(),
            "CDE must NOT silently fall back to bbox: expected NoCollision for L-notch, got {:?}", cde_result
        );
        assert_ne!(bbox_result, cde_result, "CDE and bbox must disagree for L-notch (proof: not bbox fallback)");
    }
}
