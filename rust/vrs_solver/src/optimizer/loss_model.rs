use super::candidates::PlacedBbox;
use crate::sheet::SheetShape;
use std::f64::consts::PI;

/// Minimum penetration depth for smooth decay continuity (VRS units, typically mm).
const SMOOTH_EPSILON: f64 = 1.0;

/// Quality risk classification for loss models.
///
/// Describes whether the model provides an exact signal or a surrogate proxy.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LossQualityRisk {
    /// Exact for rectangular items at 0/90/180/270°; overestimates for irregular shapes.
    BboxOnlyProxy,
    /// Smooth surrogate with continuous gradient signal; not exact collision parity.
    /// No CDE, no exact irregular polygon collision. VRS Phase-1 rectangle/bbox only.
    SmoothBboxSurrogate,
}

/// Selects which collision loss model the separator uses.
///
/// - `BboxArea` (default): backward-compatible `dx*dy` overlap area and binary boundary proxy.
/// - `PolePenetrationSmooth`: Sparrow Algorithm 3–inspired smooth severity (VRS bbox surrogate).
///
/// Known limitations of `PolePenetrationSmooth`:
/// - Not a CDE (Collision Detection Engine) backend — uses bbox overlap as penetration depth.
/// - Not exact for irregular polygons.
/// - Does not model continuous rotation.
/// - Remaining gap: `RotationPolicy` (SGH-Q07), `CollisionBackend/CDE` (SGH-Q08).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum LossModelKind {
    /// Legacy bbox overlap area (dx*dy) and binary 0/1 boundary proxy.
    /// Default. Preserves all pre-Q06 separator and BPP behavior.
    #[default]
    BboxArea,
    /// Smooth penetration severity (Sparrow Algorithm 3, VRS bbox surrogate).
    /// Provides gradient signal proportional to penetration depth and item size.
    PolePenetrationSmooth,
    /// SGH-Q24: production CDE-separation loss identity for `sparrow_cde`.
    ///
    /// The authoritative search loss for this model is the CDE-truth separation
    /// distance computed by the single-engine batch evaluator
    /// (`collision_severity::evaluate_transform_cde_batch`), NOT a bbox area.
    /// The `pair_loss` / `compute_boundary_loss` methods here are only the
    /// tracker/graph secondary signal and intentionally use the smooth
    /// penetration surrogate (never `dx*dy` bbox-area), so bbox area is never the
    /// primary production loss. `loss_bbox_proxy_used_as_primary` is `false`.
    CdeSeparation,
}

/// Equivalent circle radius for a placed bbox, used as shape scale in smooth loss.
///
/// Mirrors Sparrow Algorithm 3's pole radius as a size-proportional scale factor.
fn rect_equiv_radius(bbox: &PlacedBbox) -> f64 {
    let area = (bbox.x2 - bbox.x1) * (bbox.y2 - bbox.y1);
    (area / PI).sqrt()
}

/// Smooth penetration decay (Sparrow Algorithm 3 core formula).
///
/// For `pd >= epsilon`: linear — returns `pd`.
/// For `0 < pd < epsilon`: hyperbolic extension — returns `ε²/(-pd + 2ε)`.
///
/// The function is continuous at `pd = epsilon` (both branches return `epsilon`)
/// and provides a non-zero gradient for shallow penetrations below the linear threshold.
pub fn smooth_decay(pd: f64, epsilon: f64) -> f64 {
    if pd >= epsilon {
        pd
    } else {
        epsilon * epsilon / (-pd + 2.0 * epsilon)
    }
}

impl LossModelKind {
    /// Pairwise collision loss for two placed bboxes.
    ///
    /// Returns 0.0 if items are on different sheets or if there is no actual bbox overlap.
    pub fn pair_loss(&self, a: &PlacedBbox, b: &PlacedBbox) -> f64 {
        if a.sheet_index != b.sheet_index {
            return 0.0;
        }
        let dx = (a.x2.min(b.x2) - a.x1.max(b.x1)).max(0.0);
        let dy = (a.y2.min(b.y2) - a.y1.max(b.y1)).max(0.0);
        match self {
            LossModelKind::BboxArea => dx * dy,
            LossModelKind::PolePenetrationSmooth | LossModelKind::CdeSeparation => {
                if dx == 0.0 || dy == 0.0 {
                    return 0.0;
                }
                // Penetration depth surrogate: minimum overlap extent (tightest squeeze axis).
                let pd = dx.min(dy);
                let pd_decay = smooth_decay(pd, SMOOTH_EPSILON);
                // Shape scale: minimum equivalent circle radius of the two items.
                let ra = rect_equiv_radius(a);
                let rb = rect_equiv_radius(b);
                pd_decay * ra.min(rb) * PI
            }
        }
    }

    /// Precomputed boundary loss for an item at a given sheet.
    ///
    /// Must be called with the `boundary_valid` flag already determined by
    /// `rect_within_boundary`. The result is stored in `VrsCollisionTracker.boundary_losses`
    /// and returned by `VrsCollisionTracker::boundary_loss(i)`.
    pub fn compute_boundary_loss(
        &self,
        bbox: &PlacedBbox,
        sheet: &SheetShape,
        boundary_valid: bool,
    ) -> f64 {
        if boundary_valid {
            return 0.0;
        }
        match self {
            LossModelKind::BboxArea => 1.0,
            LossModelKind::PolePenetrationSmooth | LossModelKind::CdeSeparation => {
                // Rectangular sheet bounds violation depth.
                let viol = (sheet.min_x - bbox.x1)
                    .max(bbox.x2 - sheet.max_x)
                    .max(sheet.min_y - bbox.y1)
                    .max(bbox.y2 - sheet.max_y)
                    .max(0.0);
                let r = rect_equiv_radius(bbox);
                if viol > 0.0 {
                    // Rectangular boundary violation: smooth decay proportional to depth.
                    smooth_decay(viol, SMOOTH_EPSILON) * r * PI
                } else {
                    // Irregular sheet polygon violation: rectangular bounds do not capture
                    // the exact depth. Documented fallback: constant proxy = r * PI.
                    r * PI
                }
            }
        }
    }

    pub fn name(&self) -> &'static str {
        match self {
            LossModelKind::BboxArea => "BboxAreaLoss",
            LossModelKind::PolePenetrationSmooth => "PolePenetrationSmoothLoss",
            LossModelKind::CdeSeparation => "CdeSeparationLoss",
        }
    }

    /// True only for the legacy bbox-area model whose primary signal is `dx*dy`.
    /// `CdeSeparation` and the smooth surrogate are NOT primary-bbox-area.
    pub fn is_bbox_area_primary(&self) -> bool {
        matches!(self, LossModelKind::BboxArea)
    }

    pub fn quality_risk(&self) -> LossQualityRisk {
        match self {
            LossModelKind::BboxArea => LossQualityRisk::BboxOnlyProxy,
            LossModelKind::PolePenetrationSmooth => LossQualityRisk::SmoothBboxSurrogate,
            // CDE separation is the authoritative search signal (batch evaluator);
            // the bbox-derived tracker methods are a smooth surrogate only.
            LossModelKind::CdeSeparation => LossQualityRisk::SmoothBboxSurrogate,
        }
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::sheet::{expand_sheets, Stock};

    fn bbox(sheet_index: usize, x1: f64, y1: f64, x2: f64, y2: f64) -> PlacedBbox {
        PlacedBbox {
            sheet_index,
            x1,
            y1,
            x2,
            y2,
        }
    }

    fn make_sheet(w: f64, h: f64) -> SheetShape {
        let stocks = vec![Stock {
            id: "S".to_string(),
            quantity: 1,
            width: Some(w),
            height: Some(h),
            outer_points: None,
            holes_points: None,
            cost_per_use: None,
        }];
        expand_sheets(&stocks).unwrap().into_iter().next().unwrap()
    }

    // SGH-Q06 LossModel test 1: BboxAreaLoss.pair_loss equals legacy dx*dy overlap area
    #[test]
    fn bbox_area_loss_matches_legacy_overlap_area() {
        let a = bbox(0, 0.0, 0.0, 30.0, 30.0);
        let b = bbox(0, 10.0, 10.0, 40.0, 40.0);
        // dx = min(30,40) - max(0,10) = 30 - 10 = 20
        // dy = min(30,40) - max(0,10) = 30 - 10 = 20
        // area = 20 * 20 = 400
        let loss = LossModelKind::BboxArea.pair_loss(&a, &b);
        assert_eq!(loss, 400.0, "BboxAreaLoss.pair_loss must equal dx*dy = 400");

        // Full overlap: 30x30 = 900
        let c = bbox(0, 0.0, 0.0, 30.0, 30.0);
        let d = bbox(0, 0.0, 0.0, 30.0, 30.0);
        assert_eq!(LossModelKind::BboxArea.pair_loss(&c, &d), 900.0);

        // No overlap: 0
        let e = bbox(0, 100.0, 0.0, 130.0, 30.0);
        assert_eq!(LossModelKind::BboxArea.pair_loss(&a, &e), 0.0);

        // Different sheets: 0
        let f = bbox(1, 0.0, 0.0, 30.0, 30.0);
        assert_eq!(LossModelKind::BboxArea.pair_loss(&a, &f), 0.0);
    }

    // SGH-Q06 LossModel test 2: BboxAreaLoss.compute_boundary_loss is binary 0/1 proxy
    #[test]
    fn bbox_area_loss_preserves_binary_boundary_proxy() {
        let sheet = make_sheet(100.0, 100.0);
        let bb = bbox(0, 5.0, 5.0, 30.0, 30.0);

        let loss_valid = LossModelKind::BboxArea.compute_boundary_loss(&bb, &sheet, true);
        assert_eq!(loss_valid, 0.0, "boundary_valid=true must give 0 loss");

        let loss_invalid = LossModelKind::BboxArea.compute_boundary_loss(&bb, &sheet, false);
        assert_eq!(
            loss_invalid, 1.0,
            "boundary_valid=false must give 1.0 binary proxy"
        );
    }

    // SGH-Q06 LossModel test 3: smooth_decay is continuous at epsilon
    #[test]
    fn smooth_penetration_decay_is_continuous_at_epsilon() {
        for &eps in &[0.5_f64, 1.0, 2.5, 10.0] {
            let just_below = eps - eps * 1e-9;
            let at_eps = eps;
            let just_above = eps + eps * 1e-9;

            let decay_below = smooth_decay(just_below, eps);
            let decay_at = smooth_decay(at_eps, eps);
            let decay_above = smooth_decay(just_above, eps);

            assert!(
                (decay_below - decay_at).abs() < 1e-6,
                "smooth_decay must be continuous from below at epsilon={eps}: {decay_below} vs {decay_at}"
            );
            assert!(
                (decay_above - decay_at).abs() < 1e-6,
                "smooth_decay must be continuous from above at epsilon={eps}: {decay_above} vs {decay_at}"
            );
            // Both branches at epsilon should give epsilon
            assert!(
                (decay_at - eps).abs() < 1e-9,
                "smooth_decay(epsilon, epsilon) must equal epsilon={eps}, got {decay_at}"
            );
        }
    }

    // SGH-Q06 LossModel test 4: smooth pair loss increases monotonically with overlap depth
    #[test]
    fn smooth_pair_loss_increases_with_overlap_depth() {
        // base: 50x50 at (0,0)-(50,50)
        let base = bbox(0, 0.0, 0.0, 50.0, 50.0);

        // Small overlap: other at (45,45)-(95,95) → dx=5, dy=5, pd=5
        let small = bbox(0, 45.0, 45.0, 95.0, 95.0);
        // Medium overlap: other at (35,35)-(85,85) → dx=15, dy=15, pd=15
        let medium = bbox(0, 35.0, 35.0, 85.0, 85.0);
        // Large overlap: other at (20,20)-(70,70) → dx=30, dy=30, pd=30
        let large = bbox(0, 20.0, 20.0, 70.0, 70.0);

        let loss_small = LossModelKind::PolePenetrationSmooth.pair_loss(&base, &small);
        let loss_medium = LossModelKind::PolePenetrationSmooth.pair_loss(&base, &medium);
        let loss_large = LossModelKind::PolePenetrationSmooth.pair_loss(&base, &large);

        assert!(
            loss_small > 0.0,
            "smooth pair loss must be positive for overlapping items"
        );
        assert!(
            loss_medium > loss_small,
            "medium overlap must exceed small: medium={loss_medium} small={loss_small}"
        );
        assert!(
            loss_large > loss_medium,
            "large overlap must exceed medium: large={loss_large} medium={loss_medium}"
        );
    }

    // SGH-Q06 LossModel test 5: smooth pair loss is shape-scaled (larger items → larger loss at same pd)
    #[test]
    fn smooth_pair_loss_is_shape_scaled() {
        // Same penetration depth pd=1 for both pairs, but different item sizes.
        // Pair A: 20x20 items, overlap dx=1, dy=1
        let a1 = bbox(0, 0.0, 0.0, 20.0, 20.0);
        let a2 = bbox(0, 19.0, 19.0, 39.0, 39.0); // dx = min(20,39)-max(0,19)=1, dy=1

        // Pair B: 60x60 items, same pd=1
        let b1 = bbox(0, 0.0, 0.0, 60.0, 60.0);
        let b2 = bbox(0, 59.0, 59.0, 119.0, 119.0); // dx=1, dy=1

        let loss_small = LossModelKind::PolePenetrationSmooth.pair_loss(&a1, &a2);
        let loss_large = LossModelKind::PolePenetrationSmooth.pair_loss(&b1, &b2);

        assert!(
            loss_small > 0.0,
            "smooth pair loss must be positive for 20x20 items with pd=1"
        );
        assert!(
            loss_large > loss_small,
            "60x60 items must give larger smooth loss than 20x20 at same penetration depth: \
             large={loss_large} small={loss_small}"
        );
    }

    // SGH-Q06 LossModel test 6: smooth boundary loss increases with violation depth
    #[test]
    fn smooth_boundary_loss_increases_with_violation_depth() {
        let sheet = make_sheet(100.0, 100.0);

        // Small violation: item extends 5 units beyond right edge (x2=105, viol=5)
        let small_viol = bbox(0, 0.0, 0.0, 105.0, 30.0);
        // Large violation: item extends 30 units beyond right edge (x2=130, viol=30)
        let large_viol = bbox(0, 0.0, 0.0, 130.0, 30.0);

        let loss_small =
            LossModelKind::PolePenetrationSmooth.compute_boundary_loss(&small_viol, &sheet, false);
        let loss_large =
            LossModelKind::PolePenetrationSmooth.compute_boundary_loss(&large_viol, &sheet, false);

        assert!(
            loss_small > 0.0,
            "smooth boundary loss must be positive for a violated item"
        );
        assert!(
            loss_large > loss_small,
            "larger boundary violation must give larger smooth boundary loss: \
             large={loss_large} small={loss_small}"
        );

        // Valid boundary → no loss
        let valid_item = bbox(0, 10.0, 10.0, 50.0, 50.0);
        assert_eq!(
            LossModelKind::PolePenetrationSmooth.compute_boundary_loss(&valid_item, &sheet, true),
            0.0,
            "valid item must have zero boundary loss"
        );
    }
}
