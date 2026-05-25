use jagua_rs::geometry::geo_traits::CollidesWith;

use crate::geometry::{jag_edge_from_points, to_jag_point, to_jag_polygon, Point, Rect};
use crate::io::Placement;
use crate::item::Part;
use crate::sheet::SheetShape;
use super::boundary::rect_within_boundary;
use super::candidates::PlacedBbox;
use super::initializer::bbox_from_placement;

// ---------------------------------------------------------------------------
// CollisionDecision
// ---------------------------------------------------------------------------

/// Result of a collision query from a CollisionBackend.
#[derive(Debug, Clone, PartialEq)]
pub enum CollisionDecision {
    /// The two shapes overlap (item-item) or the item violates the boundary.
    Collision,
    /// No collision detected.
    NoCollision,
    /// Backend cannot process this query (missing polygon data, not yet implemented).
    /// Do NOT silently treat as NoCollision — callers must handle this explicitly.
    Unsupported { reason: &'static str },
}

impl CollisionDecision {
    pub fn is_collision(&self) -> bool {
        matches!(self, CollisionDecision::Collision)
    }
    pub fn is_no_collision(&self) -> bool {
        matches!(self, CollisionDecision::NoCollision)
    }
    pub fn is_unsupported(&self) -> bool {
        matches!(self, CollisionDecision::Unsupported { .. })
    }
}

// ---------------------------------------------------------------------------
// CollisionBackend trait
// ---------------------------------------------------------------------------

/// VRS-owned collision backend abstraction.
///
/// Implementations must NOT silently fall back to bbox behavior when exact data
/// is unavailable — they must return `Unsupported` instead.
///
/// Jagua-rs types must not appear in the public optimizer API; this trait is
/// the boundary.
pub trait CollisionBackend {
    /// Human-readable backend name for diagnostics and logging.
    fn name(&self) -> &'static str;

    /// Returns Collision if placement `a` and placement `b` overlap.
    ///
    /// Only placements on the same sheet can collide; different sheet_index
    /// must return NoCollision.
    fn placement_overlaps(
        &self,
        a: &Placement,
        a_part: &Part,
        b: &Placement,
        b_part: &Part,
    ) -> CollisionDecision;

    /// Returns Collision if `placement` violates the sheet boundary (is fully or
    /// partially outside `sheet`).
    fn placement_within_sheet(
        &self,
        placement: &Placement,
        part: &Part,
        sheet: &SheetShape,
    ) -> CollisionDecision;
}

// ---------------------------------------------------------------------------
// BboxCollisionBackend
// ---------------------------------------------------------------------------

/// Bbox-only collision backend.
///
/// Preserves the pre-Q08 behavior exactly: PlacedBbox overlap for item-item,
/// rect_within_boundary for item-container. This is the default backend used by
/// `find_violations`.
pub struct BboxCollisionBackend;

impl CollisionBackend for BboxCollisionBackend {
    fn name(&self) -> &'static str {
        "bbox"
    }

    fn placement_overlaps(
        &self,
        a: &Placement,
        a_part: &Part,
        b: &Placement,
        b_part: &Part,
    ) -> CollisionDecision {
        if a.sheet_index != b.sheet_index {
            return CollisionDecision::NoCollision;
        }
        let bbox_a = bbox_from_placement(a, a_part.width, a_part.height);
        let bbox_b = bbox_from_placement(b, b_part.width, b_part.height);
        match (bbox_a, bbox_b) {
            (Some(ba), Some(bb)) => {
                if ba.overlaps(&bb) {
                    CollisionDecision::Collision
                } else {
                    CollisionDecision::NoCollision
                }
            }
            _ => CollisionDecision::Unsupported {
                reason: "bbox_from_placement failed for one or both placements",
            },
        }
    }

    fn placement_within_sheet(
        &self,
        placement: &Placement,
        part: &Part,
        sheet: &SheetShape,
    ) -> CollisionDecision {
        match bbox_from_placement(placement, part.width, part.height) {
            Some(bbox) => {
                let rect = Rect {
                    x1: bbox.x1,
                    y1: bbox.y1,
                    x2: bbox.x2,
                    y2: bbox.y2,
                };
                if rect_within_boundary(rect, sheet) {
                    CollisionDecision::NoCollision
                } else {
                    CollisionDecision::Collision
                }
            }
            None => CollisionDecision::Unsupported {
                reason: "bbox_from_placement failed",
            },
        }
    }
}

// ---------------------------------------------------------------------------
// JaguaPolygonExactBackend
// ---------------------------------------------------------------------------

/// Exact polygon collision backend using jagua-rs SPolygon + Edge primitives.
///
/// For parts without outer_points: falls back to bbox behavior (rect-rect is
/// exact for axis-aligned items regardless).
///
/// For parts with outer_points: builds world-coordinate polygons and performs
/// edge-edge intersection + point-in-polygon tests via jagua-rs.
///
/// CDE status: BLOCKED — CDEngine requires hazard registration infrastructure
/// not compatible with VRS's synchronous placement-query pattern.
/// Use this backend for exact polygon collision; see CdeCollisionBackend for
/// the CDEngine scaffold.
pub struct JaguaPolygonExactBackend;

impl CollisionBackend for JaguaPolygonExactBackend {
    fn name(&self) -> &'static str {
        "jagua_polygon_exact"
    }

    fn placement_overlaps(
        &self,
        a: &Placement,
        a_part: &Part,
        b: &Placement,
        b_part: &Part,
    ) -> CollisionDecision {
        if a.sheet_index != b.sheet_index {
            return CollisionDecision::NoCollision;
        }

        let a_local = extract_polygon_from_part(a_part);
        let b_local = extract_polygon_from_part(b_part);

        match (a_local, b_local) {
            (Some(al), Some(bl)) => {
                // Both irregular: exact polygon-polygon.
                let a_world = transform_polygon(&al, a.x, a.y, a.rotation_deg);
                let b_world = transform_polygon(&bl, b.x, b.y, b.rotation_deg);
                if polygons_collide(&a_world, &b_world) {
                    CollisionDecision::Collision
                } else {
                    CollisionDecision::NoCollision
                }
            }
            (Some(al), None) => {
                // A irregular, B rect: check B bbox as polygon against A.
                let a_world = transform_polygon(&al, a.x, a.y, a.rotation_deg);
                let Some(bb) = bbox_from_placement(b, b_part.width, b_part.height) else {
                    return CollisionDecision::Unsupported {
                        reason: "bbox_from_placement failed for rect part B",
                    };
                };
                let b_pts = bbox_to_rect_pts(&bb);
                if polygons_collide(&a_world, &b_pts) {
                    CollisionDecision::Collision
                } else {
                    CollisionDecision::NoCollision
                }
            }
            (None, Some(bl)) => {
                // A rect, B irregular: check A bbox as polygon against B.
                let b_world = transform_polygon(&bl, b.x, b.y, b.rotation_deg);
                let Some(ba) = bbox_from_placement(a, a_part.width, a_part.height) else {
                    return CollisionDecision::Unsupported {
                        reason: "bbox_from_placement failed for rect part A",
                    };
                };
                let a_pts = bbox_to_rect_pts(&ba);
                if polygons_collide(&a_pts, &b_world) {
                    CollisionDecision::Collision
                } else {
                    CollisionDecision::NoCollision
                }
            }
            (None, None) => {
                // Both rect: bbox is exact for axis-aligned rectangles.
                let bbox_a = bbox_from_placement(a, a_part.width, a_part.height);
                let bbox_b = bbox_from_placement(b, b_part.width, b_part.height);
                match (bbox_a, bbox_b) {
                    (Some(ba), Some(bb)) => {
                        if ba.overlaps(&bb) {
                            CollisionDecision::Collision
                        } else {
                            CollisionDecision::NoCollision
                        }
                    }
                    _ => CollisionDecision::Unsupported {
                        reason: "bbox_from_placement failed for rect-rect pair",
                    },
                }
            }
        }
    }

    fn placement_within_sheet(
        &self,
        placement: &Placement,
        part: &Part,
        sheet: &SheetShape,
    ) -> CollisionDecision {
        let local_poly = extract_polygon_from_part(part);
        match local_poly {
            None => {
                // No outer polygon: bbox boundary check (same as BboxCollisionBackend).
                match bbox_from_placement(placement, part.width, part.height) {
                    Some(bbox) => {
                        let rect = Rect {
                            x1: bbox.x1,
                            y1: bbox.y1,
                            x2: bbox.x2,
                            y2: bbox.y2,
                        };
                        if rect_within_boundary(rect, sheet) {
                            CollisionDecision::NoCollision
                        } else {
                            CollisionDecision::Collision
                        }
                    }
                    None => CollisionDecision::Unsupported {
                        reason: "bbox_from_placement failed",
                    },
                }
            }
            Some(local_pts) => {
                // Irregular item: check each world vertex is inside sheet polygon,
                // and no item edge crosses the sheet boundary.
                let world_pts =
                    transform_polygon(&local_pts, placement.x, placement.y, placement.rotation_deg);

                // All vertices must be inside the sheet polygon.
                for &wp in &world_pts {
                    if !sheet._outer_poly.collides_with(&to_jag_point(wp)) {
                        return CollisionDecision::Collision;
                    }
                }

                // No item edge may cross any sheet boundary edge.
                let n_item = world_pts.len();
                let sheet_verts = &sheet.outer_vertices;
                let n_sheet = sheet_verts.len();
                for i in 0..n_item {
                    let p0 = world_pts[i];
                    let p1 = world_pts[(i + 1) % n_item];
                    if let Some(item_edge) = jag_edge_from_points(p0, p1) {
                        for j in 0..n_sheet {
                            let s0 = sheet_verts[j];
                            let s1 = sheet_verts[(j + 1) % n_sheet];
                            if let Some(sheet_edge) = jag_edge_from_points(s0, s1) {
                                if item_edge.collides_with(&sheet_edge) {
                                    return CollisionDecision::Collision;
                                }
                            }
                        }
                    }
                }

                CollisionDecision::NoCollision
            }
        }
    }
}

// ---------------------------------------------------------------------------
// CdeCollisionBackend — scaffold / BLOCKED
// ---------------------------------------------------------------------------

/// CDEngine-based collision backend scaffold.
///
/// STATUS: BLOCKED — CDEngine requires upfront hazard registration and does not
/// expose a synchronous polygon-polygon query API compatible with VRS's
/// placement-level collision pattern. All methods return Unsupported.
///
/// This struct exists to hold the documented CDE slot in the backend hierarchy.
/// Do not mistake Unsupported responses for NoCollision.
pub struct CdeCollisionBackend;

impl CollisionBackend for CdeCollisionBackend {
    fn name(&self) -> &'static str {
        "cde_scaffold_blocked"
    }

    fn placement_overlaps(
        &self,
        _a: &Placement,
        _a_part: &Part,
        _b: &Placement,
        _b_part: &Part,
    ) -> CollisionDecision {
        CollisionDecision::Unsupported {
            reason: "CdeCollisionBackend is not yet implemented; use JaguaPolygonExactBackend",
        }
    }

    fn placement_within_sheet(
        &self,
        _placement: &Placement,
        _part: &Part,
        _sheet: &SheetShape,
    ) -> CollisionDecision {
        CollisionDecision::Unsupported {
            reason: "CdeCollisionBackend is not yet implemented; use JaguaPolygonExactBackend",
        }
    }
}

// ---------------------------------------------------------------------------
// Private helpers
// ---------------------------------------------------------------------------

/// Try to extract a polygon from Part.outer_points (then prepared_outer_points).
///
/// Returns None if neither field is present or parseable.
/// Does NOT fall back silently — returns None so callers can choose behavior.
pub(crate) fn extract_polygon_from_part(part: &Part) -> Option<Vec<Point>> {
    let json = part.outer_points.as_ref().or(part.prepared_outer_points.as_ref())?;
    parse_points_json(json)
}

/// Parse a serde_json::Value as an array of [x, y] or {x, y} points.
fn parse_points_json(v: &serde_json::Value) -> Option<Vec<Point>> {
    let arr = v.as_array()?;
    let pts: Option<Vec<Point>> = arr
        .iter()
        .map(|item| {
            if let Some(pair) = item.as_array() {
                let x = pair.get(0)?.as_f64()?;
                let y = pair.get(1)?.as_f64()?;
                Some(Point { x, y })
            } else if item.is_object() {
                let x = item.get("x")?.as_f64()?;
                let y = item.get("y")?.as_f64()?;
                Some(Point { x, y })
            } else {
                None
            }
        })
        .collect();
    let pts = pts?;
    if pts.len() >= 3 {
        Some(pts)
    } else {
        None
    }
}

/// Apply rotation (degrees) around local origin, then translate by (anchor_x, anchor_y).
///
/// The placement anchor (placement.x, placement.y) is the rotation center — local (0,0)
/// maps to world (anchor_x, anchor_y).
fn transform_polygon(
    local_points: &[Point],
    anchor_x: f64,
    anchor_y: f64,
    rot_deg: f64,
) -> Vec<Point> {
    let theta = rot_deg.to_radians();
    let cos_t = theta.cos();
    let sin_t = theta.sin();
    local_points
        .iter()
        .map(|p| Point {
            x: anchor_x + p.x * cos_t - p.y * sin_t,
            y: anchor_y + p.x * sin_t + p.y * cos_t,
        })
        .collect()
}

/// Convert a PlacedBbox (world coordinates) to an array of 4 corner Points.
fn bbox_to_rect_pts(bbox: &PlacedBbox) -> [Point; 4] {
    [
        Point { x: bbox.x1, y: bbox.y1 },
        Point { x: bbox.x2, y: bbox.y1 },
        Point { x: bbox.x2, y: bbox.y2 },
        Point { x: bbox.x1, y: bbox.y2 },
    ]
}

/// Test whether two world-coordinate polygons collide.
///
/// Checks:
/// 1. Edge-edge intersection (any edge of A crosses any edge of B).
/// 2. A vertex inside B (one vertex from each to catch containment cases).
/// 3. B vertex inside A.
fn polygons_collide(a: &[Point], b: &[Point]) -> bool {
    let na = a.len();
    let nb = b.len();
    if na == 0 || nb == 0 {
        return false;
    }

    // 1. Edge-edge intersection.
    for i in 0..na {
        let a0 = a[i];
        let a1 = a[(i + 1) % na];
        if let Some(edge_a) = jag_edge_from_points(a0, a1) {
            for j in 0..nb {
                let b0 = b[j];
                let b1 = b[(j + 1) % nb];
                if let Some(edge_b) = jag_edge_from_points(b0, b1) {
                    if edge_a.collides_with(&edge_b) {
                        return true;
                    }
                }
            }
        }
    }

    // 2. Sample point from B: is it inside A?
    if let Ok(a_spoly) = to_jag_polygon(a, "a_collision_check") {
        if a_spoly.collides_with(&to_jag_point(b[0])) {
            return true;
        }
    }

    // 3. Sample point from A: is it inside B?
    if let Ok(b_spoly) = to_jag_polygon(b, "b_collision_check") {
        if b_spoly.collides_with(&to_jag_point(a[0])) {
            return true;
        }
    }

    false
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::io::Placement;
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
        Placement {
            instance_id: format!("{}__{:04}", part_id, 1),
            part_id: part_id.to_string(),
            sheet_index: sheet,
            x,
            y,
            rotation_deg: 0.0,
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

    fn l_shape_sheet() -> Vec<crate::sheet::SheetShape> {
        use crate::geometry::PointInput;
        let stock = Stock {
            id: "L".to_string(),
            quantity: 1,
            width: None,
            height: None,
            outer_points: Some(vec![
                PointInput::Pair([0.0, 0.0]),
                PointInput::Pair([100.0, 0.0]),
                PointInput::Pair([100.0, 50.0]),
                PointInput::Pair([50.0, 50.0]),
                PointInput::Pair([50.0, 100.0]),
                PointInput::Pair([0.0, 100.0]),
            ]),
            holes_points: None,
            cost_per_use: None,
        };
        expand_sheets(&[stock]).expect("expand_sheets")
    }

    // -------------------------------------------------------------------------
    // bbox_backend_matches_existing_rect_overlap_behavior
    // -------------------------------------------------------------------------

    #[test]
    fn bbox_backend_matches_existing_rect_overlap_behavior() {
        let backend = BboxCollisionBackend;
        let part = make_part("A", 30.0, 30.0);

        // Two overlapping placements on same sheet.
        let p1 = pl("A", 0, 0.0, 0.0);
        let p2 = pl("A", 0, 15.0, 15.0); // overlaps p1 (30x30 bbox)
        assert!(
            backend.placement_overlaps(&p1, &part, &p2, &part).is_collision(),
            "bbox backend: overlapping rects → Collision"
        );

        // Two adjacent non-overlapping placements.
        let p3 = pl("A", 0, 30.0, 0.0); // adjacent, touching boundary
        assert!(
            backend.placement_overlaps(&p1, &part, &p3, &part).is_no_collision(),
            "bbox backend: adjacent (touching) rects → NoCollision"
        );

        // Different sheets → no collision.
        let p4 = pl("A", 1, 0.0, 0.0);
        assert!(
            backend.placement_overlaps(&p1, &part, &p4, &part).is_no_collision(),
            "bbox backend: different sheets → NoCollision"
        );
    }

    // -------------------------------------------------------------------------
    // find_violations_default_matches_pre_q08_behavior
    // -------------------------------------------------------------------------

    #[test]
    fn find_violations_default_matches_pre_q08_behavior() {
        use crate::optimizer::repair::{find_violations, find_violations_with_backend};

        let parts = vec![make_part("A", 30.0, 30.0)];
        let sheets = rect_sheet(100.0, 100.0);

        // Clean layout: no violations expected.
        let placements = vec![
            Placement { instance_id: "A__0001".into(), part_id: "A".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 },
            Placement { instance_id: "A__0002".into(), part_id: "A".into(), sheet_index: 0, x: 30.0, y: 0.0, rotation_deg: 0.0 },
        ];

        let v_old = find_violations(&placements, &parts, &sheets);
        let backend = BboxCollisionBackend;
        let v_new = find_violations_with_backend(&placements, &parts, &sheets, &backend);
        assert_eq!(v_old.len(), v_new.len(), "clean layout: old and new must agree");

        // Layout with overlap.
        let placements_overlap = vec![
            Placement { instance_id: "A__0001".into(), part_id: "A".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 },
            Placement { instance_id: "A__0002".into(), part_id: "A".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 },
        ];
        let v_old2 = find_violations(&placements_overlap, &parts, &sheets);
        let v_new2 = find_violations_with_backend(&placements_overlap, &parts, &sheets, &backend);
        assert_eq!(v_old2.len(), v_new2.len(), "overlap layout: old and new must agree");
        assert_eq!(v_old2.len(), 1, "overlap layout must produce exactly 1 violation");
    }

    // -------------------------------------------------------------------------
    // jagua_or_cde_backend_detects_polygon_overlap
    // -------------------------------------------------------------------------

    #[test]
    fn jagua_or_cde_backend_detects_polygon_overlap() {
        // Two L-shapes placed such that they actually overlap.
        // L-shape: [(0,0),(40,0),(40,20),(20,20),(20,40),(0,40)]
        let l_json = serde_json::json!([
            [0.0, 0.0], [40.0, 0.0], [40.0, 20.0],
            [20.0, 20.0], [20.0, 40.0], [0.0, 40.0]
        ]);

        let part_a = make_part_with_polygon("L", 40.0, 40.0, l_json.clone());
        let part_b = make_part_with_polygon("L2", 40.0, 40.0, l_json);

        // Place B overlapping A's bottom-left region.
        let p_a = Placement { instance_id: "L__0001".into(), part_id: "L".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 };
        let p_b = Placement { instance_id: "L2__0001".into(), part_id: "L2".into(), sheet_index: 0, x: 5.0, y: 5.0, rotation_deg: 0.0 };

        let backend = JaguaPolygonExactBackend;
        let result = backend.placement_overlaps(&p_a, &part_a, &p_b, &part_b);
        assert!(
            result.is_collision(),
            "JaguaPolygonExactBackend must detect overlap when L-shapes share area: {:?}",
            result
        );
    }

    // -------------------------------------------------------------------------
    // jagua_or_cde_backend_rejects_l_shape_notch_or_irregular_outside
    // (also serves as the smoke/benchmark matrix gate)
    // -------------------------------------------------------------------------

    #[test]
    fn jagua_or_cde_backend_rejects_l_shape_notch_or_irregular_outside() {
        // L-shaped item A: [(0,0),(40,0),(40,20),(20,20),(20,40),(0,40)]
        // Bounding box: (0,0,40,40).
        // Notch (missing region): (20,20,40,40).
        let l_json = serde_json::json!([
            [0.0, 0.0], [40.0, 0.0], [40.0, 20.0],
            [20.0, 20.0], [20.0, 40.0], [0.0, 40.0]
        ]);
        let part_a = make_part_with_polygon("L", 40.0, 40.0, l_json);

        // Rect item B: 15×15, placed at (22,22) — entirely inside A's notch.
        let part_b = make_part("B", 15.0, 15.0);

        let p_a = Placement { instance_id: "L__0001".into(), part_id: "L".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 };
        let p_b = Placement { instance_id: "B__0001".into(), part_id: "B".into(), sheet_index: 0, x: 22.0, y: 22.0, rotation_deg: 0.0 };

        // --- Smoke matrix ---

        // BboxCollisionBackend: A bbox (0,0,40,40) overlaps B bbox (22,22,37,37) → Collision (false positive).
        let bbox_backend = BboxCollisionBackend;
        let bbox_result = bbox_backend.placement_overlaps(&p_a, &part_a, &p_b, &part_b);
        assert!(
            bbox_result.is_collision(),
            "BboxCollisionBackend must report Collision for L-shape bbox overlap (expected false positive)"
        );

        // JaguaPolygonExactBackend: B is in the notch → no actual polygon overlap → NoCollision.
        let exact_backend = JaguaPolygonExactBackend;
        let exact_result = exact_backend.placement_overlaps(&p_a, &part_a, &p_b, &part_b);
        assert!(
            exact_result.is_no_collision(),
            "JaguaPolygonExactBackend must report NoCollision when B is in L-shape notch: {:?}",
            exact_result
        );

        // This proves exact backend is NOT just a renamed bbox backend.
        assert_ne!(
            bbox_result, exact_result,
            "bbox and exact backends must disagree for L-shape notch fixture"
        );
    }

    // -------------------------------------------------------------------------
    // geometry_preprocessing_rejects_invalid_polygon — tested in geometry_preprocessing.rs
    // geometry_preprocessing_dedupes_consecutive_duplicate_points — tested in geometry_preprocessing.rs
    // -------------------------------------------------------------------------

    // -------------------------------------------------------------------------
    // backend_does_not_silently_fallback_to_bbox_when_exact_unavailable
    // -------------------------------------------------------------------------

    #[test]
    fn backend_does_not_silently_fallback_to_bbox_when_exact_unavailable() {
        // CdeCollisionBackend must return Unsupported, not Collision or NoCollision.
        let cde = CdeCollisionBackend;
        let part = make_part("A", 30.0, 30.0);
        let p1 = pl("A", 0, 0.0, 0.0);
        let p2 = pl("A", 0, 15.0, 15.0);
        let sheets = rect_sheet(100.0, 100.0);

        let overlap_result = cde.placement_overlaps(&p1, &part, &p2, &part);
        assert!(
            overlap_result.is_unsupported(),
            "CdeCollisionBackend.placement_overlaps must return Unsupported, not {:?}",
            overlap_result
        );

        let boundary_result = cde.placement_within_sheet(&p1, &part, &sheets[0]);
        assert!(
            boundary_result.is_unsupported(),
            "CdeCollisionBackend.placement_within_sheet must return Unsupported, not {:?}",
            boundary_result
        );

        // Verify that Unsupported is distinguishable from Collision and NoCollision.
        assert!(!overlap_result.is_collision());
        assert!(!overlap_result.is_no_collision());
    }

    // -------------------------------------------------------------------------
    // Additional coverage: boundary checks
    // -------------------------------------------------------------------------

    #[test]
    fn bbox_backend_boundary_check_rect_sheet() {
        let backend = BboxCollisionBackend;
        let part = make_part("A", 30.0, 30.0);
        let sheets = rect_sheet(100.0, 100.0);

        let inside = pl("A", 0, 0.0, 0.0);
        assert!(backend.placement_within_sheet(&inside, &part, &sheets[0]).is_no_collision());

        let outside = Placement { instance_id: "A__0001".into(), part_id: "A".into(), sheet_index: 0, x: 90.0, y: 90.0, rotation_deg: 0.0 };
        assert!(backend.placement_within_sheet(&outside, &part, &sheets[0]).is_collision());
    }

    #[test]
    fn exact_backend_boundary_check_l_shape_sheet_notch() {
        // An item placed in the notch of an L-shaped sheet must be rejected.
        let backend = JaguaPolygonExactBackend;
        let part = make_part("A", 20.0, 20.0);
        let sheets = l_shape_sheet();

        // Inside the L region: (10,10,30,30) → valid.
        let inside = pl("A", 0, 10.0, 10.0);
        assert!(backend.placement_within_sheet(&inside, &part, &sheets[0]).is_no_collision(),
            "item inside L-shape region must be valid");

        // In the notch: (60,60,80,80) → invalid.
        let notch = Placement { instance_id: "A__0001".into(), part_id: "A".into(), sheet_index: 0, x: 60.0, y: 60.0, rotation_deg: 0.0 };
        assert!(backend.placement_within_sheet(&notch, &part, &sheets[0]).is_collision(),
            "item in L-shape notch must be a boundary violation");
    }
}
