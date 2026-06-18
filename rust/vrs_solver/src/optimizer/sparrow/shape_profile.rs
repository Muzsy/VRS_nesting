//! SGH-Q47: per-part-type shape profile — cheap, deterministic decision-support metadata.
//!
//! Computed ONCE per unique `part_id` (alongside the CDE base-shape cache in
//! `model.rs::from_solver_input`) and attached to every `SPInstance` via an `Rc`. It feeds solver
//! DECISIONS only — ordering, BPP redistribution, placement budget, diagnostics. It is NEVER:
//!   * a collision input — the CDE remains the single source of truth; and
//!   * a rotation input — continuous parts keep continuous rotational freedom. The angle-sensitive
//!     metrics here (`min_dim`, `slenderness`) are one-time descriptors and must not reach
//!     placement.
//!
//! All metrics reuse existing helpers (`part_polygon_area`, `convex_hull_area_and_diameter` via the
//! same `transform_base_to_candidate` path as `lbf_order_key`). No NFP, no bbox shortcut, no
//! part_id-specific behaviour.

use super::multisheet::part_polygon_area;
use super::*;

// ── Classification thresholds (documented, deterministic; tunable via benchmark, not magic) ──
const RECTANGLE_FILL: f64 = 0.85; // fill_ratio at/above ≈ fills its bbox
const EXACT_RECT_FILL: f64 = 0.995; // ≈ a true rectangle (NO collision shortcut is taken from this)
const EXACT_RECT_CONVEXITY: f64 = 0.995;
const CONVEX_CONVEXITY: f64 = 0.95; // convexity_ratio at/above ≈ convex
const CONCAVE_CONVEXITY: f64 = 0.90; // below ≈ concave outer contour
const SLENDER_ASPECT: f64 = 4.0; // max_dim/min_dim at/above ≈ slender
const LARGE_ANCHOR_SPAN: f64 = 0.5; // bbox spans ≥ half the largest sheet dimension
const LARGE_ANCHOR_AREA: f64 = 0.15; // bbox covers ≥ 15% of a sheet
const TINY_FILLER_AREA: f64 = 0.005; // bbox covers ≤ 0.5% of a sheet
const REPEATED_FAMILY_QTY: usize = 6; // quantity at/above ≈ a family
const HIGH_INTERLOCK_FILL: f64 = 0.5; // low fill + concave ⇒ interlock potential

// ── priority_score weights (positives sum ≈ 1.0; tiny penalty moderate; "not too aggressive") ──
const W_SPAN: f64 = 0.35;
const W_AREA: f64 = 0.20;
const W_LOWFILL: f64 = 0.20;
const W_CONCAVE: f64 = 0.10;
const W_SLENDER: f64 = 0.10;
const W_FAMILY: f64 = 0.05;
const W_TINY_PENALTY: f64 = 0.30;
const ASPECT_NORM_MAX: f64 = 10.0; // aspect 1→0, ≥10→1 for slenderness normalisation
const FAMILY_NORM_QTY: f64 = 20.0; // quantity normalisation reference

const EPS: f64 = 1e-9;

/// SGH-Q47 master gate. Default ON; `VRS_SHAPE_PROFILE=0` reproduces the pre-Q47 behaviour
/// exactly (profile-aware ordering/budget fall back to the legacy keys).
pub fn shape_profile_enabled() -> bool {
    std::env::var("VRS_SHAPE_PROFILE").ok().as_deref() != Some("0")
}

/// Per-part-type shape descriptor + derived solver-control signals. Decision-support only.
#[derive(Debug, Clone)]
pub struct PartShapeProfile {
    pub part_id: String,
    pub contour_features: ContourFeatureSet,
    pub contour_feature_summary: ContourFeatureSummary,
    // base geometry
    pub true_area: f64,
    pub bbox_area: f64,
    pub convex_hull_area: f64,
    pub diameter: f64,
    pub max_dim: f64,
    pub min_dim: f64,
    pub aspect_ratio: f64,
    // shape indicators
    pub fill_ratio: f64,
    pub convexity_ratio: f64,
    pub slenderness: f64,
    // quantity / scale
    pub quantity: usize,
    pub sheet_area_ratio: f64,
    pub bbox_sheet_span_ratio: f64,
    // classes (non-exclusive)
    pub is_exact_rectangle: bool,
    pub is_rectangle_like: bool,
    pub is_convex_like: bool,
    pub is_concave_like: bool,
    pub is_slender: bool,
    pub is_large_anchor: bool,
    pub is_medium_structural: bool,
    pub is_tiny_filler: bool,
    pub is_repeated_family: bool,
    pub is_high_interlock_potential: bool,
    // solver control
    pub priority_score: f64,
    pub search_budget_multiplier: f64,
    pub filler_defer_score: f64,
}

impl PartShapeProfile {
    /// Compute the profile for `part` using its CDE base shape (for the convex hull) and a
    /// representative sheet scale (`sheet_area`, `max_sheet_span`). Pure and deterministic.
    pub fn compute(
        part: &Part,
        base_shape: &CdeBaseShape,
        sheet_area: f64,
        max_sheet_span: f64,
    ) -> Self {
        let contour_features = ContourFeatureSet::extract(base_shape);
        let contour_feature_summary = contour_features.summary();
        let w = part.width.max(0.0);
        let h = part.height.max(0.0);
        let bbox_area = (w * h).max(EPS);
        let true_area = {
            let a = part_polygon_area(part);
            if a > EPS {
                a
            } else {
                bbox_area
            }
        };
        // Convex hull via the same surrogate path as lbf_order_key; fallback = bbox / diagonal.
        let (convex_hull_area, diameter) =
            match transform_base_to_candidate(base_shape, 0.0, 0.0, 0.0) {
                Some(prepared) => convex_hull_area_and_diameter(&prepared),
                None => (bbox_area, (w * w + h * h).sqrt()),
            };
        let convex_hull_area = convex_hull_area.max(EPS);
        let max_dim = w.max(h);
        let min_dim = w.min(h).max(EPS);
        let aspect_ratio = max_dim / min_dim;
        let fill_ratio = (true_area / bbox_area).clamp(0.0, 1.0);
        let convexity_ratio = (true_area / convex_hull_area).clamp(0.0, 1.0);
        // Rotation-invariant slenderness (diameter² / true_area); ~1.27 for a disk, grows when thin.
        let slenderness = (diameter * diameter) / true_area.max(EPS);
        let quantity = part.quantity.max(0) as usize;
        let sheet_area = sheet_area.max(EPS);
        let max_sheet_span = max_sheet_span.max(EPS);
        let sheet_area_ratio = bbox_area / sheet_area;
        let bbox_sheet_span_ratio = (max_dim / max_sheet_span).clamp(0.0, 1.0);

        let is_exact_rectangle =
            fill_ratio >= EXACT_RECT_FILL && convexity_ratio >= EXACT_RECT_CONVEXITY;
        let is_rectangle_like = fill_ratio >= RECTANGLE_FILL;
        let is_convex_like = convexity_ratio >= CONVEX_CONVEXITY;
        let is_concave_like = convexity_ratio < CONCAVE_CONVEXITY;
        let is_slender = aspect_ratio >= SLENDER_ASPECT;
        let is_large_anchor =
            bbox_sheet_span_ratio >= LARGE_ANCHOR_SPAN || sheet_area_ratio >= LARGE_ANCHOR_AREA;
        let is_tiny_filler = sheet_area_ratio <= TINY_FILLER_AREA;
        let is_medium_structural = !is_large_anchor && !is_tiny_filler;
        let is_repeated_family = quantity >= REPEATED_FAMILY_QTY;
        let is_high_interlock_potential = is_concave_like && fill_ratio < HIGH_INTERLOCK_FILL;

        // Normalised positive-term inputs (each ≈ [0, 1]).
        let slender_norm = ((aspect_ratio - 1.0) / (ASPECT_NORM_MAX - 1.0)).clamp(0.0, 1.0);
        let family_norm = (quantity as f64 / FAMILY_NORM_QTY).clamp(0.0, 1.0);
        let tiny_term = if is_tiny_filler { 1.0 } else { 0.0 };
        let priority_score = W_SPAN * bbox_sheet_span_ratio
            + W_AREA * sheet_area_ratio.clamp(0.0, 1.0)
            + W_LOWFILL * (1.0 - fill_ratio)
            + W_CONCAVE * (1.0 - convexity_ratio)
            + W_SLENDER * slender_norm
            + W_FAMILY * family_norm
            - W_TINY_PENALTY * tiny_term;

        let mut budget = 1.0_f64;
        if is_large_anchor {
            budget *= 1.5;
        }
        if is_high_interlock_potential {
            budget *= 1.5;
        }
        if is_tiny_filler {
            budget *= 0.5;
        }
        let search_budget_multiplier = budget.clamp(0.4, 3.0);

        let filler_defer_score = if is_tiny_filler {
            1.0
        } else if is_medium_structural {
            0.3
        } else {
            0.0
        };

        PartShapeProfile {
            part_id: part.id.clone(),
            contour_features,
            contour_feature_summary,
            true_area,
            bbox_area,
            convex_hull_area,
            diameter,
            max_dim,
            min_dim,
            aspect_ratio,
            fill_ratio,
            convexity_ratio,
            slenderness,
            quantity,
            sheet_area_ratio,
            bbox_sheet_span_ratio,
            is_exact_rectangle,
            is_rectangle_like,
            is_convex_like,
            is_concave_like,
            is_slender,
            is_large_anchor,
            is_medium_structural,
            is_tiny_filler,
            is_repeated_family,
            is_high_interlock_potential,
            priority_score,
            search_budget_multiplier,
            filler_defer_score,
        }
    }

    /// Deterministic class-label list for diagnostics.
    pub fn class_labels(&self) -> Vec<&'static str> {
        let mut v = Vec::new();
        if self.is_exact_rectangle {
            v.push("exact_rectangle");
        }
        if self.is_rectangle_like {
            v.push("rectangle_like");
        }
        if self.is_convex_like {
            v.push("convex_like");
        }
        if self.is_concave_like {
            v.push("concave_like");
        }
        if self.is_slender {
            v.push("slender");
        }
        if self.is_large_anchor {
            v.push("large_anchor");
        }
        if self.is_medium_structural {
            v.push("medium_structural");
        }
        if self.is_tiny_filler {
            v.push("tiny_filler");
        }
        if self.is_repeated_family {
            v.push("repeated_family");
        }
        if self.is_high_interlock_potential {
            v.push("high_interlock_potential");
        }
        v
    }

    /// SGH-Q51: true when the part is layout-determining (a critical anchor): a large anchor, a
    /// high-interlock concave part, a slender part, or a high-priority part — and never a tiny
    /// filler. Project-general (no `part_id`), deterministic.
    pub fn is_critical(&self) -> bool {
        !self.is_tiny_filler
            && (self.is_large_anchor
                || self.is_high_interlock_potential
                || self.is_slender
                || self.priority_score >= CRITICAL_PRIORITY)
    }

    /// SGH-Q51: construction tier — `Critical` (admitted anchor-first), `Filler` (tiny, last),
    /// or `Structural` (everything between).
    pub fn criticality_tier(&self) -> CriticalityTier {
        if self.is_critical() {
            CriticalityTier::Critical
        } else if self.is_tiny_filler {
            CriticalityTier::Filler
        } else {
            CriticalityTier::Structural
        }
    }
}

/// SGH-Q51 priority threshold above which a (non-tiny) part counts as critical even without a
/// dominant class flag. ≈ the big GRAVÍR-class parts; tunable, documented.
const CRITICAL_PRIORITY: f64 = 0.15;

/// SGH-Q51: the three construction tiers, admitted in this order per sheet.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CriticalityTier {
    Critical,
    Structural,
    Filler,
}

/// Representative sheet scale used by the profile (largest sheet area + longest sheet span).
pub fn profile_sheet_scale(sheets: &[SheetShape]) -> (f64, f64) {
    sheets.iter().fold((0.0_f64, 0.0_f64), |(area, span), s| {
        (area.max(s.area), span.max(s.width.max(s.height)))
    })
}

/// Build per-part-type decision diagnostics from the solver instances and the final emitted
/// placements. One record per unique `part_id`, ordered by `priority_rank` (priority_score desc,
/// tie-break part_id asc — deterministic). Decision-support evidence only.
pub fn build_shape_profile_diagnostics(
    instances: &[SPInstance],
    placements: &[Placement],
) -> Vec<crate::io::ShapeProfileDiagnostics> {
    // unique part profiles + expanded-instance counts
    let mut by_part: HashMap<String, (Rc<PartShapeProfile>, usize)> = HashMap::new();
    for inst in instances {
        let e = by_part
            .entry(inst.part_id.clone())
            .or_insert_with(|| (inst.shape_profile.clone(), 0));
        e.1 += 1;
    }
    // placed counts by part_id (from the final emitted layout)
    let mut placed: HashMap<String, usize> = HashMap::new();
    for p in placements {
        *placed.entry(p.part_id.clone()).or_insert(0) += 1;
    }
    let mut rows: Vec<(Rc<PartShapeProfile>, usize)> = by_part.into_values().collect();
    rows.sort_by(|a, b| {
        b.0.priority_score
            .partial_cmp(&a.0.priority_score)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| a.0.part_id.cmp(&b.0.part_id))
    });
    rows.into_iter()
        .enumerate()
        .map(
            |(rank, (prof, instance_count))| crate::io::ShapeProfileDiagnostics {
                part_id: prof.part_id.clone(),
                classes: prof
                    .class_labels()
                    .into_iter()
                    .map(|s| s.to_string())
                    .collect(),
                priority_score: prof.priority_score,
                priority_rank: rank,
                search_budget_multiplier: prof.search_budget_multiplier,
                declared_quantity: prof.quantity,
                instance_count,
                placed_count: placed.get(&prof.part_id).copied().unwrap_or(0),
                fill_ratio: prof.fill_ratio,
                convexity_ratio: prof.convexity_ratio,
                aspect_ratio: prof.aspect_ratio,
                sheet_area_ratio: prof.sheet_area_ratio,
                contour_vertex_count: prof.contour_feature_summary.contour_vertex_count,
                contour_edge_count: prof.contour_feature_summary.contour_edge_count,
                dominant_edge_count: prof.contour_feature_summary.dominant_edge_count,
                extreme_point_count: prof.contour_feature_summary.extreme_point_count,
                concave_vertex_count: prof.contour_feature_summary.concave_vertex_count,
                concave_zone_count: prof.contour_feature_summary.concave_zone_count,
                protrusion_candidate_count: prof.contour_feature_summary.protrusion_candidate_count,
                sheet_alignment_angle_count: prof
                    .contour_feature_summary
                    .sheet_alignment_angle_count,
                contour_feature_total_count: prof.contour_feature_summary.total_feature_count,
                dominant_alignment_angles_deg: prof
                    .contour_feature_summary
                    .dominant_alignment_angles_deg
                    .clone(),
            },
        )
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    const SHEET_AREA: f64 = 3000.0 * 1500.0;
    const SHEET_SPAN: f64 = 3000.0;
    // A large concave "L": bbox 1000×1000, true area 360k (fill 0.36), convex hull 680k
    // (convexity 0.53). Qualifies as large_anchor + concave_like + high_interlock_potential.
    fn l_points() -> serde_json::Value {
        serde_json::json!([
            [0.0, 0.0],
            [1000.0, 0.0],
            [1000.0, 200.0],
            [200.0, 200.0],
            [200.0, 1000.0],
            [0.0, 1000.0]
        ])
    }

    fn rect_part(id: &str, w: f64, h: f64, qty: i64) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: qty,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: Some(serde_json::json!([[0.0, 0.0], [w, 0.0], [w, h], [0.0, h]])),
            prepared_outer_points: None,
            rotation_policy: None,
        }
    }

    fn poly_part(id: &str, w: f64, h: f64, qty: i64, pts: serde_json::Value) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: qty,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: Some(pts),
            prepared_outer_points: None,
            rotation_policy: None,
        }
    }

    fn profile_of(part: &Part) -> PartShapeProfile {
        let base = prepare_base_shape_native(part).expect("test part must be preparable");
        PartShapeProfile::compute(part, &base, SHEET_AREA, SHEET_SPAN)
    }

    #[test]
    fn compute_is_deterministic() {
        let p = poly_part("L", 1000.0, 1000.0, 6, l_points());
        let a = profile_of(&p);
        let b = profile_of(&p);
        assert_eq!(a.priority_score.to_bits(), b.priority_score.to_bits());
        assert_eq!(a.fill_ratio.to_bits(), b.fill_ratio.to_bits());
        assert_eq!(a.convexity_ratio.to_bits(), b.convexity_ratio.to_bits());
        assert_eq!(a.class_labels(), b.class_labels());
    }

    #[test]
    fn rectangle_is_rectangle_like_and_convex() {
        let prof = profile_of(&rect_part("R", 100.0, 100.0, 1));
        assert!(prof.fill_ratio > 0.99, "fill={}", prof.fill_ratio);
        assert!(prof.is_rectangle_like);
        assert!(prof.is_convex_like);
        assert!(!prof.is_concave_like);
    }

    #[test]
    fn slender_bar_is_slender() {
        let prof = profile_of(&rect_part("S", 400.0, 20.0, 1));
        assert!(prof.aspect_ratio >= 4.0, "aspect={}", prof.aspect_ratio);
        assert!(prof.is_slender);
    }

    #[test]
    fn tiny_part_is_filler_with_low_priority_and_budget() {
        let prof = profile_of(&rect_part("T", 20.0, 20.0, 1));
        assert!(prof.is_tiny_filler, "ratio={}", prof.sheet_area_ratio);
        assert!(prof.priority_score < 0.0, "score={}", prof.priority_score);
        assert!(prof.search_budget_multiplier < 1.0);
    }

    #[test]
    fn large_concave_low_fill_is_anchor_and_high_interlock() {
        let prof = profile_of(&poly_part("L", 1000.0, 1000.0, 6, l_points()));
        assert!(
            prof.is_large_anchor,
            "sheet_area_ratio={}",
            prof.sheet_area_ratio
        );
        assert!(prof.is_concave_like, "convexity={}", prof.convexity_ratio);
        assert!(prof.fill_ratio < 0.5, "fill={}", prof.fill_ratio);
        assert!(prof.is_high_interlock_potential);
        assert!(prof.is_repeated_family, "qty=6 must be a family");
        assert!(
            prof.search_budget_multiplier > 1.0,
            "budget={}",
            prof.search_budget_multiplier
        );
    }

    #[test]
    fn anchor_outranks_tiny_filler_in_priority() {
        let anchor = profile_of(&poly_part("L", 1000.0, 1000.0, 6, l_points()));
        let tiny = profile_of(&rect_part("T", 20.0, 20.0, 50));
        assert!(
            anchor.priority_score > tiny.priority_score,
            "anchor={} must outrank tiny={}",
            anchor.priority_score,
            tiny.priority_score
        );
    }

    #[test]
    fn criticality_tiers_classify_anchor_structural_filler() {
        let anchor = profile_of(&poly_part("L", 1000.0, 1000.0, 6, l_points()));
        let structural = profile_of(&rect_part("M", 300.0, 300.0, 1));
        let filler = profile_of(&rect_part("T", 20.0, 20.0, 50));
        assert_eq!(
            anchor.criticality_tier(),
            CriticalityTier::Critical,
            "large concave anchor"
        );
        assert!(anchor.is_critical());
        assert_eq!(
            structural.criticality_tier(),
            CriticalityTier::Structural,
            "medium square"
        );
        assert_eq!(
            filler.criticality_tier(),
            CriticalityTier::Filler,
            "tiny square"
        );
        assert!(!filler.is_critical());
    }

    #[test]
    fn tiny_part_is_never_critical_even_if_slender() {
        // A long thin strip that is tiny relative to the sheet must be Filler, not Critical.
        let strip = profile_of(&rect_part("S", 160.0, 12.0, 10));
        assert!(strip.is_slender, "aspect={}", strip.aspect_ratio);
        assert!(strip.is_tiny_filler, "ratio={}", strip.sheet_area_ratio);
        assert!(
            !strip.is_critical(),
            "a tiny slender strip is a filler, not a critical anchor"
        );
        assert_eq!(strip.criticality_tier(), CriticalityTier::Filler);
    }

    #[test]
    fn criticality_tier_is_deterministic() {
        let a = profile_of(&poly_part("L", 1000.0, 1000.0, 6, l_points()));
        let b = profile_of(&poly_part("L", 1000.0, 1000.0, 6, l_points()));
        assert_eq!(a.criticality_tier(), b.criticality_tier());
        assert_eq!(a.is_critical(), b.is_critical());
    }

    #[test]
    fn gate_default_on_unless_explicitly_zero() {
        // Default (var unset in this process) ⇒ enabled. Explicit "0" path is covered by the
        // T6 A/B benchmark (separate process; avoids in-process env races with parallel tests).
        if std::env::var("VRS_SHAPE_PROFILE").is_err() {
            assert!(shape_profile_enabled());
        }
    }
}
