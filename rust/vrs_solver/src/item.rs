use serde::Deserialize;
use serde_json::Value as JsonValue;

use crate::geometry::EPS;
use crate::rotation_policy::{
    candidate_angles, dedup_angles, dims_for_rotation_f64, normalize_angle,
    placement_anchor_from_rect_min_f64, rotated_bbox_min_offset_f64, RotationPolicyKind,
    RotationResolveContext,
};
use crate::sheet::SheetShape;

#[derive(Debug, Deserialize, Clone)]
pub struct Part {
    pub id: String,
    pub width: f64,
    pub height: f64,
    pub quantity: i64,
    /// Legacy rotation list. Interpreted as Discrete policy when rotation_policy is absent.
    #[serde(default)]
    pub allowed_rotations_deg: Vec<i64>,
    /// SGH-Q07: part-level rotation policy override.
    /// Precedence: rotation_policy > allowed_rotations_deg > global > Orthogonal default.
    #[serde(default)]
    pub rotation_policy: Option<RotationPolicyKind>,
    #[serde(default)]
    pub holes_points: Option<JsonValue>,
    #[serde(default)]
    pub prepared_holes_points: Option<JsonValue>,
    #[serde(default)]
    #[allow(dead_code)]
    pub outer_points: Option<JsonValue>,
    #[serde(default)]
    #[allow(dead_code)]
    pub prepared_outer_points: Option<JsonValue>,
}

pub fn part_has_holes(part: &Part) -> bool {
    fn is_non_empty(v: &Option<JsonValue>) -> bool {
        match v {
            None | Some(JsonValue::Null) => false,
            Some(JsonValue::Array(arr)) => !arr.is_empty(),
            Some(_) => true,
        }
    }
    is_non_empty(&part.holes_points) || is_non_empty(&part.prepared_holes_points)
}

#[derive(Debug)]
pub struct Instance {
    pub instance_id: String,
    pub part_id: String,
    pub width: f64,
    pub height: f64,
    /// SGH-Q07: resolved f64 angles, already normalized to [0°, 360°) and deduped.
    pub allowed_rotations_deg: Vec<f64>,
}

// ---------------------------------------------------------------------------
// Rotation angle resolution
// ---------------------------------------------------------------------------

/// Resolve effective rotation angles for a part, applying the precedence rule:
///   1. Part.rotation_policy (highest)
///   2. Part.allowed_rotations_deg (non-empty legacy list → Discrete)
///   3. global_policy
///   4. Orthogonal (documented default, no silent downgrade)
///
/// `seed` is used only for Continuous policy. `sample_count` controls Continuous samples.
pub fn resolve_part_rotation_angles(
    part: &Part,
    global_policy: Option<&RotationPolicyKind>,
    seed: u64,
    sample_count: usize,
) -> Vec<f64> {
    if let Some(policy) = &part.rotation_policy {
        return candidate_angles(policy, seed, sample_count);
    }
    if !part.allowed_rotations_deg.is_empty() {
        let angles: Vec<f64> = part
            .allowed_rotations_deg
            .iter()
            .map(|&r| normalize_angle(r as f64))
            .collect();
        return dedup_angles(angles);
    }
    if let Some(policy) = global_policy {
        return candidate_angles(policy, seed, sample_count);
    }
    // Default: Orthogonal — matches legacy behavior for inputs with no rotation spec.
    candidate_angles(&RotationPolicyKind::Orthogonal, seed, sample_count)
}

pub fn resolve_part_rotation_angles_with_context(
    part: &Part,
    context: &RotationResolveContext,
) -> Vec<f64> {
    resolve_part_rotation_angles(
        part,
        context.global_policy.as_ref(),
        context.seed_for_part(&part.id),
        context.continuous_sample_count,
    )
}

pub fn resolve_instance_rotation_angles(
    part: &Part,
    instance_id: &str,
    context: &RotationResolveContext,
) -> Vec<f64> {
    resolve_part_rotation_angles(
        part,
        context.global_policy.as_ref(),
        context.seed_for_instance(&part.id, instance_id),
        context.continuous_sample_count,
    )
}

// ---------------------------------------------------------------------------
// normalize_allowed_rotations
// ---------------------------------------------------------------------------

/// Normalize and validate a legacy allowed_rotations_deg list.
///
/// SGH-Q07: removed 0/90/180/270 restriction; any integer angle is now accepted.
/// Returns Err only when raw is empty.
pub fn normalize_allowed_rotations(raw: &[i64]) -> Result<Vec<f64>, String> {
    if raw.is_empty() {
        return Err("part.allowed_rotations_deg must be non-empty".to_string());
    }
    let angles: Vec<f64> = raw.iter().map(|&r| normalize_angle(r as f64)).collect();
    Ok(dedup_angles(angles))
}

// ---------------------------------------------------------------------------
// Rotation math — f64 wrappers for optimizer call sites
// ---------------------------------------------------------------------------

/// Compute (bbox_width, bbox_height) for an axis-aligned bounding box of the rotated rectangle.
///
/// SGH-Q07: accepts any f64 angle (degrees). For 0/90/180/270 the result matches the
/// legacy i64 implementation within floating-point epsilon.
pub fn dims_for_rotation(width: f64, height: f64, rot_deg: f64) -> (f64, f64) {
    dims_for_rotation_f64(width, height, rot_deg)
}

/// Compute (min_x_offset, min_y_offset) of the rotated bbox from the placement anchor (0,0).
pub fn rotated_bbox_min_offset(width: f64, height: f64, rot_deg: f64) -> (f64, f64) {
    rotated_bbox_min_offset_f64(width, height, rot_deg)
}

/// Compute the placement anchor so the rotated bbox's min-corner is at (rect_min_x, rect_min_y).
pub fn placement_anchor_from_rect_min(
    rect_min_x: f64,
    rect_min_y: f64,
    width: f64,
    height: f64,
    rot_deg: f64,
) -> (f64, f64) {
    placement_anchor_from_rect_min_f64(rect_min_x, rect_min_y, width, height, rot_deg)
}

// ---------------------------------------------------------------------------
// can_fit_any_stock
// ---------------------------------------------------------------------------

pub fn can_fit_any_stock_with_policy(
    part: &Part,
    sheets: &[SheetShape],
    context: &RotationResolveContext,
) -> Result<bool, String> {
    let allowed_rotations = resolve_part_rotation_angles_with_context(part, context);
    if allowed_rotations.is_empty() {
        return Err("part has no rotation angles".to_string());
    }
    for sheet in sheets {
        for &rot in &allowed_rotations {
            let (w, h) = dims_for_rotation(part.width, part.height, rot);
            if w <= sheet.width + EPS && h <= sheet.height + EPS {
                return Ok(true);
            }
        }
    }
    Ok(false)
}

pub fn can_fit_any_stock(part: &Part, sheets: &[SheetShape]) -> Result<bool, String> {
    can_fit_any_stock_with_policy(part, sheets, &RotationResolveContext::legacy_default())
}

// ---------------------------------------------------------------------------
// expand_instances
// ---------------------------------------------------------------------------

pub fn expand_instances_with_policy(
    parts: &[Part],
    context: &RotationResolveContext,
) -> Result<Vec<Instance>, String> {
    let mut instances = Vec::new();
    for part in parts {
        for idx in 0..part.quantity {
            let instance_id = format!("{}__{:04}", part.id, idx + 1);
            let allowed_rotations = if part.rotation_policy.is_some() || part.allowed_rotations_deg.is_empty() {
                resolve_instance_rotation_angles(part, &instance_id, context)
            } else {
                normalize_allowed_rotations(&part.allowed_rotations_deg)?
            };
            if allowed_rotations.is_empty() {
                return Err(format!("part {} has no valid rotation angles", part.id));
            }
            instances.push(Instance {
                instance_id,
                part_id: part.id.clone(),
                width: part.width,
                height: part.height,
                allowed_rotations_deg: allowed_rotations.clone(),
            });
        }
    }
    instances.sort_by(|a, b| a.instance_id.cmp(&b.instance_id));
    Ok(instances)
}

pub fn expand_instances(parts: &[Part]) -> Result<Vec<Instance>, String> {
    expand_instances_with_policy(parts, &RotationResolveContext::legacy_default())
}

// ---------------------------------------------------------------------------
// ItemGeometryStore — stable per-part geometry cache (JG-06)
// ---------------------------------------------------------------------------

/// Pre-computed geometry for one rotation of a part (SGH-Q07: rotation_deg is now f64).
#[derive(Debug, Clone)]
pub struct RotationCacheEntry {
    pub rotation_deg: f64,
    pub width: f64,
    pub height: f64,
    pub bbox_min_offset_x: f64,
    pub bbox_min_offset_y: f64,
}

/// Pre-computed geometry record for a single Part (SGH-Q07: allowed_rotations is Vec<f64>).
#[derive(Debug, Clone)]
pub struct ItemGeometryRecord {
    pub part_id: String,
    pub quantity: i64,
    pub base_width: f64,
    pub base_height: f64,
    pub area: f64,
    pub allowed_rotations: Vec<f64>,
    pub rotation_cache: Vec<RotationCacheEntry>,
}

/// Store of pre-computed item geometry records, one per Part.
#[derive(Debug)]
pub struct ItemGeometryStore {
    pub records: Vec<ItemGeometryRecord>,
}

pub fn build_item_geometry_store_with_policy(
    parts: &[Part],
    context: &RotationResolveContext,
) -> Result<ItemGeometryStore, String> {
    let mut records = Vec::new();
    for part in parts {
        let allowed_rotations = if part.rotation_policy.is_some() || part.allowed_rotations_deg.is_empty() {
            resolve_part_rotation_angles_with_context(part, context)
        } else {
            normalize_allowed_rotations(&part.allowed_rotations_deg)?
        };
        if allowed_rotations.is_empty() {
            return Err(format!("part {} has no valid rotation angles", part.id));
        }
        let area = crate::geometry::rect_area(part.width, part.height);
        let mut rotation_cache = Vec::new();
        for &rot in &allowed_rotations {
            let (w, h) = dims_for_rotation(part.width, part.height, rot);
            let (bx, by) = rotated_bbox_min_offset(part.width, part.height, rot);
            rotation_cache.push(RotationCacheEntry {
                rotation_deg: rot,
                width: w,
                height: h,
                bbox_min_offset_x: bx,
                bbox_min_offset_y: by,
            });
        }
        records.push(ItemGeometryRecord {
            part_id: part.id.clone(),
            quantity: part.quantity,
            base_width: part.width,
            base_height: part.height,
            area,
            allowed_rotations,
            rotation_cache,
        });
    }
    Ok(ItemGeometryStore { records })
}

pub fn build_item_geometry_store(parts: &[Part]) -> Result<ItemGeometryStore, String> {
    build_item_geometry_store_with_policy(parts, &RotationResolveContext::legacy_default())
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::{
        build_item_geometry_store, dims_for_rotation, expand_instances_with_policy,
        normalize_allowed_rotations, placement_anchor_from_rect_min,
        rotated_bbox_min_offset, Part,
    };
    use crate::rotation_policy::{RotationPolicyKind, RotationResolveContext};

    fn make_part(id: &str, w: f64, h: f64, qty: i64, rotations: Vec<i64>) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: qty,
            allowed_rotations_deg: rotations,
            rotation_policy: None,
            holes_points: None,
            prepared_holes_points: None,
            outer_points: None,
            prepared_outer_points: None,
        }
    }

    fn approx_eq(a: f64, b: f64) -> bool {
        (a - b).abs() <= 1e-9
    }

    // ── dims_for_rotation and rotated_bbox_min_offset (f64, any angle) ──────

    #[test]
    fn dims_for_rotation_canonical_matches_legacy() {
        // 0° → (100, 50), 90° → (50, 100)
        let (w0, h0) = dims_for_rotation(100.0, 50.0, 0.0);
        assert!(approx_eq(w0, 100.0));
        assert!(approx_eq(h0, 50.0));
        let (w90, h90) = dims_for_rotation(100.0, 50.0, 90.0);
        assert!(approx_eq(w90, 50.0));
        assert!(approx_eq(h90, 100.0));
        let (w180, h180) = dims_for_rotation(100.0, 50.0, 180.0);
        assert!(approx_eq(w180, 100.0));
        assert!(approx_eq(h180, 50.0));
        let (w270, h270) = dims_for_rotation(100.0, 50.0, 270.0);
        assert!(approx_eq(w270, 50.0));
        assert!(approx_eq(h270, 100.0));
    }

    #[test]
    fn rotated_bbox_min_offset_matches_expected_quadrants() {
        let width = 1000.0;
        let height = 2000.0;
        let expected = [
            (0.0, 0.0, 0.0),
            (90.0, -2000.0, 0.0),
            (180.0, -1000.0, -2000.0),
            (270.0, 0.0, -1000.0),
        ];
        for (rot, exp_x, exp_y) in expected {
            let (x, y) = rotated_bbox_min_offset(width, height, rot);
            assert!(approx_eq(x, exp_x), "rot={rot} min_x={x} expected={exp_x}");
            assert!(approx_eq(y, exp_y), "rot={rot} min_y={y} expected={exp_y}");
        }
    }

    #[test]
    fn placement_anchor_from_rect_min_keeps_rotated_bbox_inside_target_rect() {
        let width = 1000.0;
        let height = 2000.0;
        let rect_min_x = 0.0;
        let rect_min_y = 480.0;

        for rot in [0.0, 90.0, 180.0, 270.0] {
            let (anchor_x, anchor_y) =
                placement_anchor_from_rect_min(rect_min_x, rect_min_y, width, height, rot);
            let (min_off_x, min_off_y) = rotated_bbox_min_offset(width, height, rot);
            let (rw, rh) = dims_for_rotation(width, height, rot);

            let placed_min_x = anchor_x + min_off_x;
            let placed_min_y = anchor_y + min_off_y;
            let placed_max_x = placed_min_x + rw;
            let placed_max_y = placed_min_y + rh;

            assert!(approx_eq(placed_min_x, rect_min_x), "rot={rot} min_x");
            assert!(approx_eq(placed_min_y, rect_min_y), "rot={rot} min_y");
            assert!(approx_eq(placed_max_x, rect_min_x + rw), "rot={rot} max_x");
            assert!(approx_eq(placed_max_y, rect_min_y + rh), "rot={rot} max_y");
        }
    }

    // ── normalize_allowed_rotations ──────────────────────────────────────────

    #[test]
    fn normalize_allowed_rotations_empty_returns_err() {
        assert!(normalize_allowed_rotations(&[]).is_err());
    }

    #[test]
    fn normalize_allowed_rotations_deduplicates() {
        let rots = normalize_allowed_rotations(&[0, 0, 90, 90]).unwrap();
        assert_eq!(rots.len(), 2);
    }

    // SGH-Q07: arbitrary angles now accepted (45° is no longer an error)
    #[test]
    fn normalize_allowed_rotations_accepts_arbitrary_angles() {
        let rots = normalize_allowed_rotations(&[45, 135]).unwrap();
        assert_eq!(rots.len(), 2);
        assert!(rots.iter().any(|&r| (r - 45.0).abs() < 1e-9));
        assert!(rots.iter().any(|&r| (r - 135.0).abs() < 1e-9));
    }

    // ── ItemGeometryStore ────────────────────────────────────────────────────

    #[test]
    fn item_geometry_store_rotation_cache_dims() {
        let parts = vec![make_part("A", 100.0, 50.0, 1, vec![0, 90])];
        let store = build_item_geometry_store(&parts).expect("store build");
        assert_eq!(store.records.len(), 1);
        let rec = &store.records[0];
        assert_eq!(rec.rotation_cache.len(), 2);
        // rot=0: 100×50
        let e0 = &rec.rotation_cache[0];
        assert!((e0.rotation_deg - 0.0).abs() < 1e-9);
        assert!((e0.width - 100.0).abs() < 1e-9);
        assert!((e0.height - 50.0).abs() < 1e-9);
        // rot=90: 50×100
        let e90 = &rec.rotation_cache[1];
        assert!((e90.rotation_deg - 90.0).abs() < 1e-9);
        assert!((e90.width - 50.0).abs() < 1e-9);
        assert!((e90.height - 100.0).abs() < 1e-9);
    }

    #[test]
    fn item_geometry_store_area() {
        let parts = vec![make_part("B", 80.0, 60.0, 3, vec![0])];
        let store = build_item_geometry_store(&parts).expect("store build");
        assert!((store.records[0].area - 4800.0).abs() < 1e-9);
    }

    #[test]
    fn item_geometry_store_duplicate_rotation_deduped() {
        let parts = vec![make_part("C", 50.0, 30.0, 1, vec![0, 0, 90, 90, 0])];
        let store = build_item_geometry_store(&parts).expect("store build");
        let rec = &store.records[0];
        assert_eq!(rec.allowed_rotations.len(), 2, "duplicates deduped");
        assert!((rec.allowed_rotations[0] - 0.0).abs() < 1e-9);
        assert!((rec.allowed_rotations[1] - 90.0).abs() < 1e-9);
        assert_eq!(rec.rotation_cache.len(), 2);
    }

    // SGH-Q07: 45° is now supported — no longer an error
    #[test]
    fn item_geometry_store_allows_arbitrary_rotation() {
        let parts = vec![make_part("D", 50.0, 50.0, 1, vec![45])];
        let store = build_item_geometry_store(&parts).expect("45° must now be supported");
        let rec = &store.records[0];
        assert_eq!(rec.rotation_cache.len(), 1);
        // 45° bbox of 50×50 square: (50+50)/√2 ≈ 70.711
        let expected = (50.0 + 50.0) / std::f64::consts::SQRT_2;
        let entry = &rec.rotation_cache[0];
        assert!(
            (entry.width - expected).abs() < 0.001,
            "bbox width at 45°: {}",
            entry.width
        );
    }

    #[test]
    fn item_geometry_store_deterministic() {
        let parts = vec![
            make_part("X", 120.0, 80.0, 2, vec![0, 90, 180, 270]),
            make_part("Y", 60.0, 40.0, 1, vec![0]),
        ];
        let store1 = build_item_geometry_store(&parts).expect("store1");
        let store2 = build_item_geometry_store(&parts).expect("store2");
        assert_eq!(store1.records.len(), store2.records.len());
        for (r1, r2) in store1.records.iter().zip(store2.records.iter()) {
            assert_eq!(r1.part_id, r2.part_id);
            assert_eq!(r1.allowed_rotations.len(), r2.allowed_rotations.len());
            for (e1, e2) in r1.rotation_cache.iter().zip(r2.rotation_cache.iter()) {
                assert!((e1.rotation_deg - e2.rotation_deg).abs() < 1e-9);
                assert!((e1.width - e2.width).abs() < 1e-9);
                assert!((e1.height - e2.height).abs() < 1e-9);
            }
        }
    }

    #[test]
    fn item_geometry_store_all_four_rotations() {
        let parts = vec![make_part("E", 100.0, 40.0, 1, vec![0, 90, 180, 270])];
        let store = build_item_geometry_store(&parts).expect("store build");
        let cache = &store.records[0].rotation_cache;
        assert_eq!(cache.len(), 4);
        assert!((cache[0].width - 100.0).abs() < 1e-9);
        assert!((cache[0].height - 40.0).abs() < 1e-9);
        assert!((cache[1].width - 40.0).abs() < 1e-9);
        assert!((cache[1].height - 100.0).abs() < 1e-9);
        assert!((cache[2].width - 100.0).abs() < 1e-9);
        assert!((cache[2].height - 40.0).abs() < 1e-9);
        assert!((cache[3].width - 40.0).abs() < 1e-9);
        assert!((cache[3].height - 100.0).abs() < 1e-9);
    }

    #[test]
    fn global_forty_five_policy_affects_expand_instances_when_part_has_no_legacy_rots() {
        let parts = vec![make_part("F", 100.0, 20.0, 1, vec![])];
        let ctx = RotationResolveContext::new(Some(RotationPolicyKind::FortyFive), 11, 8);
        let instances = expand_instances_with_policy(&parts, &ctx).expect("instances");
        let rots = &instances[0].allowed_rotations_deg;
        assert!(rots.iter().any(|&r| (r - 45.0).abs() < 1e-9));
        assert_eq!(rots.len(), 8);
    }

    #[test]
    fn global_continuous_policy_affects_expand_instances_when_part_has_no_legacy_rots() {
        let parts = vec![make_part("G", 100.0, 20.0, 1, vec![])];
        let ctx = RotationResolveContext::new(Some(RotationPolicyKind::Continuous), 1234, 8);
        let instances = expand_instances_with_policy(&parts, &ctx).expect("instances");
        let rots = &instances[0].allowed_rotations_deg;
        assert!(rots.len() >= 5, "continuous must include canonical + sampled");
        let has_non_canonical = rots
            .iter()
            .any(|&r| [0.0, 90.0, 180.0, 270.0].iter().all(|&c| (r - c).abs() > 0.5));
        assert!(has_non_canonical, "continuous must include non-canonical angle");
    }

    #[test]
    fn continuous_policy_different_seed_changes_resolved_candidate_angles() {
        let parts = vec![make_part("H", 100.0, 20.0, 1, vec![])];
        let a = RotationResolveContext::new(Some(RotationPolicyKind::Continuous), 1001, 8);
        let b = RotationResolveContext::new(Some(RotationPolicyKind::Continuous), 2002, 8);
        let ia = expand_instances_with_policy(&parts, &a).expect("a");
        let ib = expand_instances_with_policy(&parts, &b).expect("b");
        assert_ne!(
            ia[0].allowed_rotations_deg, ib[0].allowed_rotations_deg,
            "different seeds must be able to change resolved continuous angles"
        );
    }
}
