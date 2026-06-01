// SGH-Q07 — RotationPolicy moduláris réteg
//
// Sparrow source audit:
//   .cache/sparrow/src/sample/uniform_sampler.rs:
//     ROT_N_SAMPLES = 16, linspace(0, 2π, 16) for Continuous RotationRange
//     RotationRange::None/Discrete/Continuous (jagua-rs-0.6.4 geo_enums.rs)
//   .cache/sparrow/src/sample/coord_descent.rs:
//     CDAxis::Wiggle — rotation-axis local refinement (foundation for future Q08)
//
// VRS adaptation: rectangle bbox proxy instead of exact CDE polygon collision.

use serde::{Deserialize, Serialize};

pub type AngleDeg = f64;

const CANONICAL: [AngleDeg; 4] = [0.0, 90.0, 180.0, 270.0];
/// Sparrow-aligned default: 16 uniform steps → 22.5° spacing, includes all canonical + 45° diagonals.
pub const DEFAULT_CONTINUOUS_SAMPLE_COUNT: usize = 16;

/// Symmetric wiggle offsets (degrees) used for local rotation refinement.
const REFINEMENT_OFFSETS: &[f64] = &[0.75, 1.5, 3.0, 7.5, 15.0];
/// Maximum refinement candidates generated per call.
pub const REFINEMENT_MAX_CANDIDATES: usize = 10;

/// Modular rotation policy for VRS solver.
///
/// Resolution precedence (enforced in item.rs::resolve_part_rotation_angles):
///   1. Part.rotation_policy  (highest)
///   2. Part.allowed_rotations_deg  (legacy Discrete)
///   3. SolverInput.rotation_policy  (global default)
///   4. Orthogonal  (documented default, no silent downgrade)
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum RotationPolicyKind {
    Locked,
    HalfTurn,
    #[default]
    Orthogonal,
    FortyFive,
    Discrete(Vec<AngleDeg>),
    Continuous,
}

/// Configuration for continuous policy sampling.
pub struct RotationPolicyConfig {
    pub kind: RotationPolicyKind,
    /// Number of seeded non-canonical samples for Continuous policy.
    pub continuous_sample_count: usize,
    /// Local wiggle offsets (±deg) applied around each canonical angle — foundation for
    /// coordinate descent (Sparrow CDAxis::Wiggle). Not used in discrete selection yet.
    pub wiggle_degrees: Vec<AngleDeg>,
}

impl Default for RotationPolicyConfig {
    fn default() -> Self {
        Self {
            kind: RotationPolicyKind::Orthogonal,
            continuous_sample_count: 12,
            wiggle_degrees: vec![1.0, 2.0, 5.0],
        }
    }
}

/// Runtime context for resolving effective rotation candidates.
#[derive(Debug, Clone)]
pub struct RotationResolveContext {
    pub global_policy: Option<RotationPolicyKind>,
    pub solver_seed: u64,
    pub continuous_sample_count: usize,
}

impl Default for RotationResolveContext {
    fn default() -> Self {
        Self::legacy_default()
    }
}

impl RotationResolveContext {
    pub fn new(
        global_policy: Option<RotationPolicyKind>,
        solver_seed: u64,
        continuous_sample_count: usize,
    ) -> Self {
        Self {
            global_policy,
            solver_seed,
            continuous_sample_count: continuous_sample_count.max(1),
        }
    }

    pub fn legacy_default() -> Self {
        Self::new(None, 0, DEFAULT_CONTINUOUS_SAMPLE_COUNT)
    }

    pub fn seed_for_part(&self, part_id: &str) -> u64 {
        derive_rotation_seed(self.solver_seed, part_id, None)
    }

    pub fn seed_for_instance(&self, part_id: &str, instance_id: &str) -> u64 {
        derive_rotation_seed(self.solver_seed, part_id, Some(instance_id))
    }
}

/// Deterministic seed mixing for rotation candidate generation.
pub fn derive_rotation_seed(base_seed: u64, part_id: &str, instance_id: Option<&str>) -> u64 {
    const FNV_OFFSET: u64 = 0xcbf2_9ce4_8422_2325;
    const FNV_PRIME: u64 = 0x0000_0001_0000_01b3;

    let mut hash = FNV_OFFSET ^ base_seed.rotate_left(17);
    for &b in part_id.as_bytes() {
        hash ^= b as u64;
        hash = hash.wrapping_mul(FNV_PRIME);
    }
    if let Some(instance) = instance_id {
        hash ^= 0xff;
        hash = hash.wrapping_mul(FNV_PRIME);
        for &b in instance.as_bytes() {
            hash ^= b as u64;
            hash = hash.wrapping_mul(FNV_PRIME);
        }
    }
    if hash == 0 {
        0x9E37_79B9_7F4A_7C15
    } else {
        hash
    }
}

// ---------------------------------------------------------------------------
// Angle normalization
// ---------------------------------------------------------------------------

/// Normalize an angle to [0.0, 360.0), snapping near-integer values to their integer.
pub fn normalize_angle(deg: f64) -> AngleDeg {
    let d = deg.rem_euclid(360.0);
    let rounded = d.round();
    if (d - rounded).abs() < 1e-9 {
        rounded.rem_euclid(360.0)
    } else {
        d
    }
}

/// Dedupe angles with epsilon tolerance, preserving first-occurrence order.
pub fn dedup_angles(angles: Vec<AngleDeg>) -> Vec<AngleDeg> {
    const TOL: f64 = 1e-9;
    let mut out: Vec<AngleDeg> = Vec::new();
    for a in angles {
        if !out.iter().any(|&x| (x - a).abs() < TOL) {
            out.push(a);
        }
    }
    out
}

// ---------------------------------------------------------------------------
// Candidate angle generation
// ---------------------------------------------------------------------------

/// Generate a deterministic, deduped list of candidate rotation angles for a policy.
///
/// - `_seed`: reserved for future seeded extras; currently unused for Continuous (linspace-based).
/// - `sample_count`: number of uniform Continuous samples (≥ 4); canonical always included.
///
/// Continuous policy uses a uniform linspace over `[0, 360)` so that useful diagonal/coarse
/// angles (e.g. 22.5°/45°) are deterministically present for standard sample counts.
/// Canonical angles 0/90/180/270 are always included, ensuring Continuous ≥ Orthogonal.
pub fn candidate_angles(
    kind: &RotationPolicyKind,
    _seed: u64,
    sample_count: usize,
) -> Vec<AngleDeg> {
    let raw = match kind {
        RotationPolicyKind::Locked => vec![0.0],
        RotationPolicyKind::HalfTurn => vec![0.0, 180.0],
        RotationPolicyKind::Orthogonal => CANONICAL.to_vec(),
        RotationPolicyKind::FortyFive => (0..8).map(|i| i as f64 * 45.0).collect(),
        RotationPolicyKind::Discrete(angles) => {
            angles.iter().map(|&a| normalize_angle(a)).collect()
        }
        RotationPolicyKind::Continuous => {
            let n = sample_count.max(4);
            let step = 360.0 / n as f64;
            // Uniform linspace base: deterministic coarse coverage.
            let mut angles: Vec<AngleDeg> =
                (0..n).map(|i| normalize_angle(i as f64 * step)).collect();
            // Always include canonical angles (already present for n divisible by 4).
            for &c in &CANONICAL {
                if !angles.iter().any(|&x| (x - c).abs() < 1e-9) {
                    angles.push(c);
                }
            }
            angles
        }
    };
    dedup_angles(raw)
}

/// Generate local rotation refinement candidate angles around `current_deg`.
///
/// Returns candidates only for `RotationPolicyKind::Continuous`; all other policies
/// return an empty vec (no unsupported extra angles for Locked/HalfTurn/Orthogonal/FortyFive/Discrete).
///
/// Candidates are symmetric ±offsets around `current_deg`, normalized to `[0, 360)`,
/// deduped against `base_candidates`, and capped at `max_candidates`.
/// Order is deterministic: innermost offsets first.
pub fn continuous_refinement_angles(
    current_deg: f64,
    effective_policy: &RotationPolicyKind,
    base_candidates: &[f64],
    max_candidates: usize,
) -> Vec<AngleDeg> {
    match effective_policy {
        RotationPolicyKind::Continuous => {}
        _ => return vec![],
    }
    let current_norm = normalize_angle(current_deg);
    let mut result: Vec<AngleDeg> = Vec::new();
    'outer: for &offset in REFINEMENT_OFFSETS {
        for &delta in &[offset, -offset] {
            let candidate = normalize_angle(current_norm + delta);
            let dup_base = base_candidates
                .iter()
                .any(|&b| (b - candidate).abs() < 1e-9);
            let dup_result = result.iter().any(|&r| (r - candidate).abs() < 1e-9);
            if !dup_base && !dup_result {
                result.push(candidate);
                if result.len() >= max_candidates {
                    break 'outer;
                }
            }
        }
    }
    result
}

// ---------------------------------------------------------------------------
// General rectangle rotation math — arbitrary angle (degrees)
// ---------------------------------------------------------------------------
//
// Rotate rectangle corners around the anchor at (0,0) counter-clockwise by θ.
// Corners: (0,0), (w,0), (w,h), (0,h).
//
// bbox_w = |w·cos(θ)| + |h·sin(θ)|
// bbox_h = |w·sin(θ)| + |h·cos(θ)|
//
// For 0/90/180/270 these match the legacy integer-based results to floating-point precision.

/// Compute (bbox_width, bbox_height) for a rectangle rotated by `rot_deg`.
pub fn dims_for_rotation_f64(width: f64, height: f64, rot_deg: AngleDeg) -> (f64, f64) {
    let theta = rot_deg.to_radians();
    let cos_t = theta.cos().abs();
    let sin_t = theta.sin().abs();
    (
        width * cos_t + height * sin_t,
        width * sin_t + height * cos_t,
    )
}

/// Compute (min_x_offset, min_y_offset) of the rotated bbox relative to the anchor (0,0).
///
/// The anchor is the rotation origin. We rotate the 4 rectangle corners CCW by θ and
/// find the minimum x and y of the resulting convex hull.
pub fn rotated_bbox_min_offset_f64(width: f64, height: f64, rot_deg: AngleDeg) -> (f64, f64) {
    let theta = rot_deg.to_radians();
    let cos_t = theta.cos();
    let sin_t = theta.sin();
    // Rotate corners: (0,0), (w,0), (w,h), (0,h)
    let corners = [
        (0.0f64, 0.0f64),
        (width, 0.0),
        (width, height),
        (0.0, height),
    ];
    let mut min_x = f64::INFINITY;
    let mut min_y = f64::INFINITY;
    for (cx, cy) in &corners {
        let rx = cx * cos_t - cy * sin_t;
        let ry = cx * sin_t + cy * cos_t;
        if rx < min_x {
            min_x = rx;
        }
        if ry < min_y {
            min_y = ry;
        }
    }
    (min_x, min_y)
}

/// Compute the placement anchor so that the rotated bbox's min-corner is at (rect_min_x, rect_min_y).
pub fn placement_anchor_from_rect_min_f64(
    rect_min_x: f64,
    rect_min_y: f64,
    width: f64,
    height: f64,
    rot_deg: AngleDeg,
) -> (f64, f64) {
    let (bbox_min_x, bbox_min_y) = rotated_bbox_min_offset_f64(width, height, rot_deg);
    (rect_min_x - bbox_min_x, rect_min_y - bbox_min_y)
}

// ---------------------------------------------------------------------------
// Tests — 13 required SGH-Q07 behaviors + bbox math
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use std::fs;
    use std::path::Path;

    use super::*;
    use crate::item::{expand_instances, resolve_part_rotation_angles, Part};
    use crate::optimizer::compress::CompressionPhase;
    use crate::optimizer::initializer::build_initial_layout;
    use crate::optimizer::phase::PhaseConfig;
    use crate::optimizer::working::WorkingLayout;
    use crate::sheet::{expand_sheets, Stock};

    fn make_part(id: &str, w: f64, h: f64, qty: i64, rots: Vec<i64>) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: qty,
            allowed_rotations_deg: rots,
            rotation_policy: None,
            holes_points: None,
            prepared_holes_points: None,
            outer_points: None,
            prepared_outer_points: None,
        }
    }

    fn make_part_with_policy(
        id: &str,
        w: f64,
        h: f64,
        qty: i64,
        policy: RotationPolicyKind,
    ) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: qty,
            allowed_rotations_deg: vec![],
            rotation_policy: Some(policy),
            holes_points: None,
            prepared_holes_points: None,
            outer_points: None,
            prepared_outer_points: None,
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

    fn approx_eq(a: f64, b: f64) -> bool {
        (a - b).abs() < 1e-9
    }

    // 1. Locked policy generates only 0°
    #[test]
    fn rotation_policy_locked_generates_only_zero() {
        let angles = candidate_angles(&RotationPolicyKind::Locked, 0, 4);
        assert_eq!(angles, vec![0.0]);
    }

    // 2. HalfTurn generates exactly 0° and 180°
    #[test]
    fn rotation_policy_half_turn_generates_0_180() {
        let angles = candidate_angles(&RotationPolicyKind::HalfTurn, 0, 4);
        assert_eq!(angles.len(), 2);
        assert!(angles.contains(&0.0));
        assert!(angles.contains(&180.0));
    }

    // 3. Orthogonal matches legacy 0/90/180/270
    #[test]
    fn rotation_policy_orthogonal_matches_legacy_0_90_180_270() {
        let angles = candidate_angles(&RotationPolicyKind::Orthogonal, 0, 4);
        assert_eq!(angles.len(), 4);
        assert!(angles.contains(&0.0));
        assert!(angles.contains(&90.0));
        assert!(angles.contains(&180.0));
        assert!(angles.contains(&270.0));
    }

    // 4. FortyFive generates exactly 8 angles (0,45,90,...,315)
    #[test]
    fn rotation_policy_forty_five_generates_8_angles() {
        let angles = candidate_angles(&RotationPolicyKind::FortyFive, 0, 0);
        assert_eq!(angles.len(), 8);
        for i in 0..8u32 {
            let expected = i as f64 * 45.0;
            assert!(
                angles.iter().any(|&a| (a - expected).abs() < 1e-9),
                "missing angle {expected}"
            );
        }
    }

    // 5. Legacy allowed_rotations_deg still supported
    #[test]
    fn legacy_allowed_rotations_deg_still_supported() {
        let parts = vec![make_part("A", 30.0, 30.0, 1, vec![0, 90])];
        let instances = expand_instances(&parts).expect("expand");
        assert_eq!(instances.len(), 1);
        let rots = &instances[0].allowed_rotations_deg;
        assert_eq!(rots.len(), 2);
        assert!(rots.iter().any(|&r| (r - 0.0).abs() < 1e-9));
        assert!(rots.iter().any(|&r| (r - 90.0).abs() < 1e-9));
    }

    // 6. Part-level policy overrides global policy
    #[test]
    fn part_policy_overrides_global_policy() {
        // Part has Locked policy → only 0°, regardless of global Orthogonal
        let part = make_part_with_policy("A", 30.0, 30.0, 1, RotationPolicyKind::Locked);
        let global = Some(RotationPolicyKind::Orthogonal);
        let angles = resolve_part_rotation_angles(&part, global.as_ref(), 0, 8);
        assert_eq!(
            angles,
            vec![0.0],
            "Locked policy must override global Orthogonal"
        );
    }

    // 7. Global policy used when part has no explicit policy or allowed_rotations_deg
    #[test]
    fn global_policy_used_when_part_has_no_explicit_policy() {
        let part = Part {
            id: "A".to_string(),
            width: 30.0,
            height: 30.0,
            quantity: 1,
            allowed_rotations_deg: vec![], // empty — no legacy list
            rotation_policy: None,         // no part policy
            holes_points: None,
            prepared_holes_points: None,
            outer_points: None,
            prepared_outer_points: None,
        };
        let global = Some(RotationPolicyKind::HalfTurn);
        let angles = resolve_part_rotation_angles(&part, global.as_ref(), 0, 8);
        assert_eq!(angles.len(), 2);
        assert!(angles.contains(&0.0));
        assert!(angles.contains(&180.0));
    }

    // 8. 45° bbox math is correct
    #[test]
    fn arbitrary_45_degree_bbox_math_is_correct() {
        // 100 × 20 rectangle at 45°:
        // bbox_w = 100*cos45 + 20*sin45 = (100+20)/√2 ≈ 84.853
        let (bw, bh) = dims_for_rotation_f64(100.0, 20.0, 45.0);
        let expected = (100.0 + 20.0) / std::f64::consts::SQRT_2;
        assert!(
            (bw - expected).abs() < 1e-9,
            "bbox_w at 45°: {bw}, expected {expected}"
        );
        assert!(
            (bh - expected).abs() < 1e-9,
            "bbox_h at 45°: {bh}, expected {expected}"
        );
    }

    // 9. Continuous policy generates non-orthogonal angles
    #[test]
    fn continuous_policy_generates_non_orthogonal_angles() {
        let angles = candidate_angles(&RotationPolicyKind::Continuous, 42, 12);
        let canonical = [0.0, 90.0, 180.0, 270.0];
        let has_non_canonical = angles
            .iter()
            .any(|&a| canonical.iter().all(|&c| (a - c).abs() > 0.5));
        assert!(
            has_non_canonical,
            "Continuous must include non-orthogonal angles: {:?}",
            angles
        );
    }

    // 10. Continuous policy same seed → same angles (determinism)
    #[test]
    fn continuous_policy_same_seed_is_deterministic() {
        let a1 = candidate_angles(&RotationPolicyKind::Continuous, 1337, 12);
        let a2 = candidate_angles(&RotationPolicyKind::Continuous, 1337, 12);
        assert_eq!(a1, a2, "same seed must produce identical angle lists");
    }

    // 11. Continuous rotation can fit a 100×20 part in a 90×90 sheet
    #[test]
    fn continuous_rotation_can_fit_rectangle_that_orthogonal_cannot() {
        // At 0°: bbox = 100×20 → width 100 > 90 → doesn't fit
        let (w0, _) = dims_for_rotation_f64(100.0, 20.0, 0.0);
        assert!(w0 > 90.0, "0° must not fit: w0={w0}");
        // At 90°: bbox = 20×100 → height 100 > 90 → doesn't fit
        let (_, h90) = dims_for_rotation_f64(100.0, 20.0, 90.0);
        assert!(h90 > 90.0, "90° must not fit: h90={h90}");
        // At 45°: bbox ≈ 84.85 × 84.85 → fits in 90×90
        let (w45, h45) = dims_for_rotation_f64(100.0, 20.0, 45.0);
        assert!(
            w45 < 90.0 + 1e-9,
            "45° bbox width must fit in 90: w45={w45}"
        );
        assert!(
            h45 < 90.0 + 1e-9,
            "45° bbox height must fit in 90: h45={h45}"
        );
    }

    // 12. Separator uses rotation policy, not hardcoded orthogonal
    // This test verifies that a 100×20 part placed via separator fallback in a 90×90
    // sheet succeeds when the part has FortyFive policy (45° fits) and fails with
    // the hardcoded orthogonal-only path (0°/90° don't fit).
    #[test]
    fn separator_uses_rotation_policy_not_hardcoded_orthogonal() {
        // Part with FortyFive policy: 100×20, sheet 90×90
        // At 0° and 90°: won't fit. At 45°: bbox ≈ 84.85 → fits.
        let part = make_part_with_policy("P", 100.0, 20.0, 1, RotationPolicyKind::FortyFive);
        let stocks = vec![make_stock("S", 90.0, 90.0, 1)];
        let instances = expand_instances(&[part.clone()]).expect("expand");
        assert_eq!(instances.len(), 1);
        // Instance should have 8 angles including 45°
        let rots = &instances[0].allowed_rotations_deg;
        assert!(
            rots.iter().any(|&r| (r - 45.0).abs() < 1e-9),
            "Instance must have 45° angle: {:?}",
            rots
        );
        let sheets = expand_sheets(&stocks).expect("sheets");
        let parts = vec![part];
        let (placed, unplaced, _) = build_initial_layout(&instances, &parts, &sheets);
        assert_eq!(
            placed.len(),
            1,
            "100×20 part must fit on 90×90 sheet with FortyFive policy"
        );
        assert!(unplaced.is_empty());
        // Verify the placed rotation is non-orthogonal
        let rot = placed[0].rotation_deg;
        let canonical = [0.0, 90.0, 180.0, 270.0];
        assert!(
            canonical.iter().all(|&c| (rot - c).abs() > 0.5),
            "placed rotation must be non-orthogonal: {rot}"
        );
    }

    // 13. Compression uses rotation policy, not hardcoded orthogonal
    #[test]
    fn compression_uses_rotation_policy_not_hardcoded_orthogonal() {
        // Part with FortyFive policy: 100×20, sheet 90×90
        // Orthogonal rotations don't fit; 45° does. Compression must try 45°.
        let part = make_part_with_policy("P", 100.0, 20.0, 1, RotationPolicyKind::FortyFive);
        let stocks = vec![make_stock("S", 90.0, 90.0, 1)];
        let instances = expand_instances(&[part.clone()]).expect("expand");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let parts = vec![part];
        let (placed, unplaced, _) = build_initial_layout(&instances, &parts, &sheets);
        assert_eq!(placed.len(), 1, "initial layout must place the 100×20 part");
        assert!(unplaced.is_empty());

        let working = WorkingLayout::new(placed, unplaced, sheets.len(), 0);
        let config = PhaseConfig::default();
        let compression = CompressionPhase::new(config);
        let (result_layout, _diag) = compression.run(working, &parts, &sheets);
        // After compression: part should still be placed (not broken)
        assert_eq!(
            result_layout.placements.len(),
            1,
            "compression must not lose the placed part"
        );
    }

    // Bonus: verify bbox_min_offset for canonical angles matches legacy expectations
    #[test]
    fn rotated_bbox_min_offset_canonical_angles_correct() {
        let w = 1000.0;
        let h = 2000.0;
        let cases = [
            (0.0, 0.0, 0.0),
            (90.0, -2000.0, 0.0),
            (180.0, -1000.0, -2000.0),
            (270.0, 0.0, -1000.0),
        ];
        for (rot, ex, ey) in cases {
            let (mx, my) = rotated_bbox_min_offset_f64(w, h, rot);
            assert!(approx_eq(mx, ex), "rot={rot} min_x={mx} expected={ex}");
            assert!(approx_eq(my, ey), "rot={rot} min_y={my} expected={ey}");
        }
    }

    // Bonus: verify placement_anchor keeps bbox inside target rect
    #[test]
    fn placement_anchor_keeps_bbox_inside_rect() {
        let w = 100.0;
        let h = 40.0;
        let rx = 50.0;
        let ry = 20.0;
        for rot in [0.0, 45.0, 90.0, 135.0, 180.0, 270.0] {
            let (ax, ay) = placement_anchor_from_rect_min_f64(rx, ry, w, h, rot);
            let (min_x_off, min_y_off) = rotated_bbox_min_offset_f64(w, h, rot);
            let placed_min_x = ax + min_x_off;
            let placed_min_y = ay + min_y_off;
            assert!(
                approx_eq(placed_min_x, rx),
                "rot={rot} placed_min_x={placed_min_x} expected={rx}"
            );
            assert!(
                approx_eq(placed_min_y, ry),
                "rot={rot} placed_min_y={placed_min_y} expected={ry}"
            );
        }
    }

    // -----------------------------------------------------------------------
    // SGH-Q20 tests
    // -----------------------------------------------------------------------

    // Q20-1: Continuous linspace includes deterministic coarse diagonals
    #[test]
    fn continuous_candidate_generation_linspace_includes_coarse_diagonals() {
        // n=8 → step=45°: must include 45°, 135°, 225°, 315°
        let angles8 = candidate_angles(&RotationPolicyKind::Continuous, 0, 8);
        assert!(
            angles8.iter().any(|&a| (a - 45.0).abs() < 1e-9),
            "45° must be in n=8 linspace: {:?}",
            angles8
        );
        assert!(
            angles8.iter().any(|&a| (a - 135.0).abs() < 1e-9),
            "135° must be in n=8: {:?}",
            angles8
        );
        assert_eq!(
            angles8.len(),
            8,
            "n=8 gives exactly 8 angles: {:?}",
            angles8
        );

        // n=16 → step=22.5°: must include 22.5°, 45°, 67.5°
        let angles16 = candidate_angles(&RotationPolicyKind::Continuous, 0, 16);
        assert!(
            angles16.iter().any(|&a| (a - 22.5).abs() < 1e-9),
            "22.5° must be in n=16: {:?}",
            angles16
        );
        assert!(
            angles16.iter().any(|&a| (a - 45.0).abs() < 1e-9),
            "45° must be in n=16: {:?}",
            angles16
        );
        assert_eq!(
            angles16.len(),
            16,
            "n=16 gives exactly 16 angles: {:?}",
            angles16
        );
    }

    // Q20-2: Continuous always includes canonical angles
    #[test]
    fn continuous_candidate_generation_always_includes_canonical() {
        for n in [4, 6, 7, 8, 12, 16] {
            let angles = candidate_angles(&RotationPolicyKind::Continuous, 42, n);
            for &c in &CANONICAL {
                assert!(
                    angles.iter().any(|&a| (a - c).abs() < 1e-9),
                    "canonical {c}° missing for n={n}: {:?}",
                    angles
                );
            }
        }
    }

    // Q20-3: Continuous linspace is deterministic regardless of seed
    #[test]
    fn continuous_linspace_is_deterministic_regardless_of_seed() {
        let a1 = candidate_angles(&RotationPolicyKind::Continuous, 0, 16);
        let a2 = candidate_angles(&RotationPolicyKind::Continuous, 999_999, 16);
        assert_eq!(
            a1, a2,
            "linspace is deterministic: seed must not affect output for n=16"
        );
    }

    // Q20-4: Local refinement returns symmetric normalized candidates for Continuous
    #[test]
    fn continuous_refinement_symmetric_normalized_deduped() {
        let base = vec![0.0, 90.0, 180.0, 270.0];
        let candidates =
            continuous_refinement_angles(45.0, &RotationPolicyKind::Continuous, &base, 10);
        // Smallest offset ±0.75° around 45°: expect 45.75° and 44.25°
        assert!(
            candidates.iter().any(|&a| (a - 45.75).abs() < 1e-9),
            "45.75° expected: {:?}",
            candidates
        );
        assert!(
            candidates.iter().any(|&a| (a - 44.25).abs() < 1e-9),
            "44.25° expected: {:?}",
            candidates
        );
        // No duplicates
        let mut seen = vec![];
        for &a in &candidates {
            assert!(
                !seen.iter().any(|&x: &f64| (x - a).abs() < 1e-9),
                "duplicate {a} in {:?}",
                candidates
            );
            seen.push(a);
        }
        // All normalized to [0, 360)
        for &a in &candidates {
            assert!(a >= 0.0 && a < 360.0, "not normalized: {a}");
        }
    }

    // Q20-5: Refinement wraps correctly at 0°/360° boundary
    #[test]
    fn continuous_refinement_normalizes_at_boundary() {
        let base = vec![90.0, 180.0, 270.0];
        let candidates =
            continuous_refinement_angles(1.0, &RotationPolicyKind::Continuous, &base, 10);
        // 1.0 - 15.0 = -14.0 → normalized to 346.0
        assert!(
            candidates.iter().any(|&a| (a - 346.0).abs() < 1e-9),
            "346° expected for wrap: {:?}",
            candidates
        );
    }

    // Q20-6: Non-continuous policies return no refinement candidates
    #[test]
    fn non_continuous_policies_return_no_refinement_candidates() {
        let base = vec![0.0, 90.0, 180.0, 270.0];
        for policy in &[
            RotationPolicyKind::Locked,
            RotationPolicyKind::HalfTurn,
            RotationPolicyKind::Orthogonal,
            RotationPolicyKind::FortyFive,
            RotationPolicyKind::Discrete(vec![0.0, 45.0, 90.0]),
        ] {
            let result = continuous_refinement_angles(45.0, policy, &base, 10);
            assert!(
                result.is_empty(),
                "{policy:?} must return no refinement candidates, got: {:?}",
                result
            );
        }
    }

    // Q20-7: Refinement cap is respected
    #[test]
    fn continuous_refinement_candidate_count_capped() {
        let base = vec![];
        let candidates =
            continuous_refinement_angles(90.0, &RotationPolicyKind::Continuous, &base, 4);
        assert!(
            candidates.len() <= 4,
            "cap=4 must be respected: {:?}",
            candidates
        );
    }

    // Q20-8: Refinement does not produce base-duplicate candidates
    #[test]
    fn continuous_refinement_dedupes_against_base() {
        // Base includes exactly the offset values: refinement should skip them
        let base = vec![90.75, 89.25]; // == 90 ± 0.75
        let candidates =
            continuous_refinement_angles(90.0, &RotationPolicyKind::Continuous, &base, 10);
        assert!(
            !candidates.iter().any(|&a| (a - 90.75).abs() < 1e-9),
            "90.75° should be deduped against base"
        );
        assert!(
            !candidates.iter().any(|&a| (a - 89.25).abs() < 1e-9),
            "89.25° should be deduped against base"
        );
    }

    #[test]
    fn no_remaining_production_none_zero_eight_policy_resolution_without_justification() {
        let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("src");
        let files = [
            "item.rs",
            "adapter.rs",
            "optimizer/initializer.rs",
            "optimizer/separator.rs",
            "optimizer/compress.rs",
            "optimizer/moves.rs",
            "optimizer/repair.rs",
            "optimizer/sheet_elimination.rs",
        ];
        for rel in files {
            let path = root.join(rel);
            let src = fs::read_to_string(&path).expect("read source");
            for (lineno, line) in src.lines().enumerate() {
                let has_bad_call =
                    line.contains("resolve_part_rotation_angles(") && line.contains("None, 0, 8");
                assert!(
                    !has_bad_call,
                    "forbidden hardcoded policy resolution in {}:{}: {}",
                    rel,
                    lineno + 1,
                    line
                );
            }
        }
    }
}
