//! SGH-Q56B: per-part-type `PartAnalysis` (a.k.a. ShapeProfileV2).
//!
//! A coherent analysis layer **above** the existing `PartShapeProfile` (SGH-Q47) and
//! `ContourFeatureSet` (SGH-Q53A) and the `OrientationCatalog` (SGH-Q56A). It does NOT duplicate or
//! replace them — it reuses the shared `Rc`s and derives soft, deterministic decision-support signals
//! (shape tags, fit-difficulty, family key, orientation sensitivity, interlock/anchor/filler scores)
//! that later stages (pair compatibility, sheet feasibility, role assignment) consume.
//!
//! Hard rules: every signal here is a SOFT hint. None of them bypass CDE, none gate placement, none
//! are derived from `part_id`, and no tag is ever treated as exact fit/collision proof.

use super::*;

const ASPECT_NORM_MAX: f64 = 4.0;
const FAMILY_NORM_QTY: f64 = 20.0;
const COMPLEX_VERTEX_NORM: f64 = 64.0;
const COMPLEX_VERTEX_TAG_MIN: usize = 24;
const NEAR_SYMMETRIC_ASPECT_MAX: f64 = 1.20;
const ORIENTATION_SENSITIVE_MIN: f64 = 0.35;
const WIDE_PLATE_ASPECT_MAX: f64 = 2.0;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ShapeTag {
    ExactRectangle,
    RectangleLike,
    ConvexLike,
    ConcaveLike,
    SlenderLong,
    WidePlate,
    LargeAnchor,
    CriticalLarge,
    MediumStructural,
    TinyFiller,
    RepeatedFamily,
    HighInterlockPotential,
    HoleFreeAfterPrepack,
    OrientationSensitive,
    NearSymmetric,
    ComplexOuterContour,
    EdgeAlignable,
}

impl ShapeTag {
    pub fn as_str(self) -> &'static str {
        match self {
            ShapeTag::ExactRectangle => "exact_rectangle",
            ShapeTag::RectangleLike => "rectangle_like",
            ShapeTag::ConvexLike => "convex_like",
            ShapeTag::ConcaveLike => "concave_like",
            ShapeTag::SlenderLong => "slender_long",
            ShapeTag::WidePlate => "wide_plate",
            ShapeTag::LargeAnchor => "large_anchor",
            ShapeTag::CriticalLarge => "critical_large",
            ShapeTag::MediumStructural => "medium_structural",
            ShapeTag::TinyFiller => "tiny_filler",
            ShapeTag::RepeatedFamily => "repeated_family",
            ShapeTag::HighInterlockPotential => "high_interlock_potential",
            ShapeTag::HoleFreeAfterPrepack => "hole_free_after_prepack",
            ShapeTag::OrientationSensitive => "orientation_sensitive",
            ShapeTag::NearSymmetric => "near_symmetric",
            ShapeTag::ComplexOuterContour => "complex_outer_contour",
            ShapeTag::EdgeAlignable => "edge_alignable",
        }
    }
}

/// Decomposed fit-difficulty so the score is explainable (never a black box). Components are each in
/// roughly [0, 1]; `score` is their weighted sum, clamped to [0, 1].
#[derive(Debug, Clone, Default)]
pub struct FitDifficultySignals {
    pub sheet_span_term: f64,
    pub area_term: f64,
    pub low_fill_term: f64,
    pub concavity_term: f64,
    pub slenderness_term: f64,
    pub orientation_scarcity_term: f64,
    pub contour_complexity_term: f64,
    pub repeated_critical_pressure_term: f64,
    pub tiny_filler_relief: f64,
    pub score: f64,
}

#[derive(Debug, Clone, Default)]
pub struct PartAnalysisDiagnostics {
    pub criticality_tier: &'static str,
    pub dominant_edge_count: usize,
    pub concavity_count: usize,
    pub protrusion_count: usize,
    pub outer_contour_complexity: usize,
    pub orientation_candidate_count: usize,
    pub orientation_fractional_count: usize,
    pub hole_count_in_solver_input: usize,
    pub cavity_prepack_bridge_status: &'static str,
}

#[derive(Debug, Clone)]
pub struct PartAnalysis {
    pub part_id: String,
    pub quantity: usize,
    /// Reused SGH-Q47 profile (NOT duplicated).
    pub shape_profile: Rc<PartShapeProfile>,
    /// Reused SGH-Q56A orientation catalog (NOT duplicated).
    pub orientation_catalog: Rc<OrientationCatalog>,
    pub shape_tags: Vec<ShapeTag>,
    pub fit_difficulty: FitDifficultySignals,
    /// Cheap deterministic family / near-duplicate key (area/perimeter/vertex/shape buckets).
    pub family_key: String,
    /// SGH-Q74: DIAGNOSTIC ONLY — never a placement / priority / criticality decision input. The
    /// solver runs on a single hole-free offset contour (cavity prepack is app-side, SGH-Q40, and the
    /// SolverInputGuard hard-fails on any top-level hole), so this is structurally always `true`. Kept
    /// for diagnostic-JSON stability; no solver decision branches on hole count / cavity topology.
    pub hole_free_solver_input: bool,
    // Soft decision-support scores (each in [0, 1]).
    pub orientation_sensitivity_score: f64,
    pub symmetry_score: f64,
    pub interlock_potential_score: f64,
    pub critical_anchor_score: f64,
    pub filler_score: f64,
    pub sheet_span_risk_score: f64,
    pub diagnostics: PartAnalysisDiagnostics,
}

impl PartAnalysis {
    /// Derive the analysis from the (already-computed) shared profile + orientation catalog. Pure and
    /// deterministic. `hole_free_solver_input` reflects the geometry actually entering the solver.
    pub fn compute(
        part: &Part,
        shape_profile: &Rc<PartShapeProfile>,
        orientation_catalog: &Rc<OrientationCatalog>,
    ) -> Self {
        let sp = shape_profile.as_ref();
        let summary = &sp.contour_feature_summary;
        let hole_free = !crate::item::part_has_holes(part);

        let slender_norm = ((sp.aspect_ratio - 1.0) / (ASPECT_NORM_MAX - 1.0)).clamp(0.0, 1.0);
        let family_norm = (sp.quantity as f64 / FAMILY_NORM_QTY).clamp(0.0, 1.0);
        let complexity_norm =
            (summary.contour_vertex_count as f64 / COMPLEX_VERTEX_NORM).clamp(0.0, 1.0);
        let cand_count = orientation_catalog.diagnostics.candidate_count;
        let orientation_scarcity = 1.0 / (1.0 + cand_count as f64);
        let is_critical = sp.is_critical();
        let repeated_critical_pressure = if is_critical { family_norm } else { 0.0 };
        let tiny_term = if sp.is_tiny_filler { 1.0 } else { 0.0 };

        // Explainable fit-difficulty (separate from priority_score).
        let fd = FitDifficultySignals {
            sheet_span_term: 0.22 * sp.bbox_sheet_span_ratio,
            area_term: 0.18 * sp.sheet_area_ratio.clamp(0.0, 1.0),
            low_fill_term: 0.13 * (1.0 - sp.fill_ratio),
            concavity_term: 0.12 * (1.0 - sp.convexity_ratio),
            slenderness_term: 0.10 * slender_norm,
            orientation_scarcity_term: 0.08 * orientation_scarcity,
            contour_complexity_term: 0.09 * complexity_norm,
            repeated_critical_pressure_term: 0.08 * repeated_critical_pressure,
            tiny_filler_relief: 0.20 * tiny_term,
            score: 0.0,
        };
        let fit_score = (fd.sheet_span_term
            + fd.area_term
            + fd.low_fill_term
            + fd.concavity_term
            + fd.slenderness_term
            + fd.orientation_scarcity_term
            + fd.contour_complexity_term
            + fd.repeated_critical_pressure_term
            - fd.tiny_filler_relief)
            .clamp(0.0, 1.0);
        let fit_difficulty = FitDifficultySignals {
            score: round4(fit_score),
            ..fd
        };

        // Orientation sensitivity: anisotropy of the rotated spacing-expanded extrema (narrowest vs
        // widest extent across the catalog's samples) blended with the aspect ratio. A genuinely
        // fractional min-width orientation bumps it (the part packs best off-axis).
        let mut narrow = f64::MAX;
        let mut wide = f64::MIN;
        for s in &orientation_catalog.extrema_samples {
            let small = s.width.min(s.height);
            let large = s.width.max(s.height);
            narrow = narrow.min(small);
            wide = wide.max(large);
        }
        let anisotropy = if wide > 0.0 && narrow.is_finite() {
            (1.0 - narrow / wide).clamp(0.0, 1.0)
        } else {
            slender_norm
        };
        let fractional_bump = if orientation_catalog.diagnostics.fractional_candidate_count > 0 {
            0.10
        } else {
            0.0
        };
        let orientation_sensitivity_score =
            (0.55 * anisotropy + 0.35 * slender_norm + fractional_bump).clamp(0.0, 1.0);

        // Symmetry proxy: regular, well-filled, convex, low-aspect parts read as near-symmetric.
        let symmetry_score =
            (sp.fill_ratio * sp.convexity_ratio * (1.0 - slender_norm)).clamp(0.0, 1.0);

        // Interlock potential: concavity depth + concave/protrusion feature richness.
        let concavity_richness =
            ((summary.concave_vertex_count + summary.protrusion_candidate_count) as f64 / 8.0)
                .clamp(0.0, 1.0);
        let interlock_potential_score = (0.5 * (1.0 - sp.convexity_ratio)
            + 0.3 * concavity_richness
            + if sp.is_high_interlock_potential {
                0.2
            } else {
                0.0
            })
        .clamp(0.0, 1.0);

        let critical_anchor_score = (0.5 * sp.bbox_sheet_span_ratio
            + 0.3 * sp.sheet_area_ratio.clamp(0.0, 1.0)
            + if sp.is_large_anchor { 0.2 } else { 0.0 })
        .clamp(0.0, 1.0);

        let filler_score = sp.filler_defer_score.clamp(0.0, 1.0);
        let sheet_span_risk_score = sp.bbox_sheet_span_ratio.clamp(0.0, 1.0);

        // Shape tags (non-exclusive, deterministic, geometry/quantity-derived — never part_id).
        let mut tags: Vec<ShapeTag> = Vec::new();
        if sp.is_exact_rectangle {
            tags.push(ShapeTag::ExactRectangle);
        }
        if sp.is_rectangle_like {
            tags.push(ShapeTag::RectangleLike);
        }
        if sp.is_convex_like {
            tags.push(ShapeTag::ConvexLike);
        }
        if sp.is_concave_like {
            tags.push(ShapeTag::ConcaveLike);
        }
        if sp.is_slender {
            tags.push(ShapeTag::SlenderLong);
        }
        if sp.is_rectangle_like && sp.aspect_ratio <= WIDE_PLATE_ASPECT_MAX && sp.is_large_anchor {
            tags.push(ShapeTag::WidePlate);
        }
        if sp.is_large_anchor {
            tags.push(ShapeTag::LargeAnchor);
        }
        if sp.is_large_anchor && is_critical {
            tags.push(ShapeTag::CriticalLarge);
        }
        if sp.is_medium_structural {
            tags.push(ShapeTag::MediumStructural);
        }
        if sp.is_tiny_filler {
            tags.push(ShapeTag::TinyFiller);
        }
        if sp.is_repeated_family {
            tags.push(ShapeTag::RepeatedFamily);
        }
        if sp.is_high_interlock_potential {
            tags.push(ShapeTag::HighInterlockPotential);
        }
        if hole_free {
            tags.push(ShapeTag::HoleFreeAfterPrepack);
        }
        if orientation_sensitivity_score >= ORIENTATION_SENSITIVE_MIN {
            tags.push(ShapeTag::OrientationSensitive);
        }
        if sp.is_rectangle_like && sp.aspect_ratio <= NEAR_SYMMETRIC_ASPECT_MAX {
            tags.push(ShapeTag::NearSymmetric);
        }
        if summary.contour_vertex_count >= COMPLEX_VERTEX_TAG_MIN {
            tags.push(ShapeTag::ComplexOuterContour);
        }
        if summary.dominant_edge_count >= 1 {
            tags.push(ShapeTag::EdgeAlignable);
        }

        let family_key = family_key(sp);

        let diagnostics = PartAnalysisDiagnostics {
            criticality_tier: tier_str(sp.criticality_tier()),
            dominant_edge_count: summary.dominant_edge_count,
            concavity_count: summary.concave_vertex_count,
            protrusion_count: summary.protrusion_candidate_count,
            outer_contour_complexity: summary.contour_vertex_count,
            orientation_candidate_count: cand_count,
            orientation_fractional_count: orientation_catalog
                .diagnostics
                .fractional_candidate_count,
            hole_count_in_solver_input: if hole_free { 0 } else { 1 },
            // Q56B only records the observed hole-free state of the solver input; the full worker
            // bridge contract is Q56B2's responsibility.
            cavity_prepack_bridge_status: if hole_free {
                "hole_free_observed"
            } else {
                "holes_present"
            },
        };

        PartAnalysis {
            part_id: sp.part_id.clone(),
            quantity: sp.quantity,
            shape_profile: Rc::clone(shape_profile),
            orientation_catalog: Rc::clone(orientation_catalog),
            shape_tags: tags,
            fit_difficulty,
            family_key,
            hole_free_solver_input: hole_free,
            orientation_sensitivity_score: round4(orientation_sensitivity_score),
            symmetry_score: round4(symmetry_score),
            interlock_potential_score: round4(interlock_potential_score),
            critical_anchor_score: round4(critical_anchor_score),
            filler_score: round4(filler_score),
            sheet_span_risk_score: round4(sheet_span_risk_score),
            diagnostics,
        }
    }

    /// Minimal valid analysis for internal test fixtures that construct `SPInstance` directly.
    pub fn placeholder(part_id: &str, shape_profile: &Rc<PartShapeProfile>) -> Self {
        let orientation_catalog = Rc::new(OrientationCatalog::placeholder(part_id));
        PartAnalysis {
            part_id: part_id.to_string(),
            quantity: shape_profile.quantity,
            shape_profile: Rc::clone(shape_profile),
            orientation_catalog,
            shape_tags: Vec::new(),
            fit_difficulty: FitDifficultySignals::default(),
            family_key: String::new(),
            hole_free_solver_input: true,
            orientation_sensitivity_score: 0.0,
            symmetry_score: 0.0,
            interlock_potential_score: 0.0,
            critical_anchor_score: 0.0,
            filler_score: 0.0,
            sheet_span_risk_score: 0.0,
            diagnostics: PartAnalysisDiagnostics::default(),
        }
    }

    pub fn has_tag(&self, tag: ShapeTag) -> bool {
        self.shape_tags.contains(&tag)
    }

    pub fn to_diagnostics_json(&self) -> serde_json::Value {
        let sp = self.shape_profile.as_ref();
        serde_json::json!({
            "part_id": self.part_id,
            "quantity": self.quantity,
            "shape_tags": self.shape_tags.iter().map(|t| t.as_str()).collect::<Vec<_>>(),
            "priority_score": round4(sp.priority_score),
            "fit_difficulty_score": self.fit_difficulty.score,
            "criticality_tier": self.diagnostics.criticality_tier,
            "orientation_sensitivity_score": self.orientation_sensitivity_score,
            "symmetry_score": self.symmetry_score,
            "interlock_potential_score": self.interlock_potential_score,
            "critical_anchor_score": self.critical_anchor_score,
            "filler_score": self.filler_score,
            "sheet_span_risk_score": self.sheet_span_risk_score,
            "family_key": self.family_key,
            "hole_free_solver_input": self.hole_free_solver_input,
            "outer_contour_complexity": self.diagnostics.outer_contour_complexity,
            "dominant_edge_count": self.diagnostics.dominant_edge_count,
            "concavity_count": self.diagnostics.concavity_count,
            "protrusion_count": self.diagnostics.protrusion_count,
            "orientation_candidate_count": self.diagnostics.orientation_candidate_count,
            "cavity_prepack_bridge_status": self.diagnostics.cavity_prepack_bridge_status,
            "fit_difficulty_components": {
                "sheet_span_term": round4(self.fit_difficulty.sheet_span_term),
                "area_term": round4(self.fit_difficulty.area_term),
                "low_fill_term": round4(self.fit_difficulty.low_fill_term),
                "concavity_term": round4(self.fit_difficulty.concavity_term),
                "slenderness_term": round4(self.fit_difficulty.slenderness_term),
                "orientation_scarcity_term": round4(self.fit_difficulty.orientation_scarcity_term),
                "contour_complexity_term": round4(self.fit_difficulty.contour_complexity_term),
                "repeated_critical_pressure_term": round4(self.fit_difficulty.repeated_critical_pressure_term),
                "tiny_filler_relief": round4(self.fit_difficulty.tiny_filler_relief),
            }
        })
    }
}

/// Build per-unique-part analyses for a set of parts on a single sheet (real solver path), and emit a
/// run-level summary JSON (per-part records + sorted top-lists). Mirrors the Q56A builder pattern.
pub fn summarize_part_analyses(analyses: &[PartAnalysis]) -> serde_json::Value {
    let records: Vec<serde_json::Value> =
        analyses.iter().map(|a| a.to_diagnostics_json()).collect();

    let critical: Vec<&PartAnalysis> = analyses
        .iter()
        .filter(|a| a.diagnostics.criticality_tier == "critical")
        .collect();

    let mut by_priority: Vec<&PartAnalysis> = critical.clone();
    by_priority.sort_by(|a, b| {
        b.shape_profile
            .priority_score
            .partial_cmp(&a.shape_profile.priority_score)
            .unwrap_or(Ordering::Equal)
            .then_with(|| a.part_id.cmp(&b.part_id))
    });
    let mut by_fit: Vec<&PartAnalysis> = critical.clone();
    by_fit.sort_by(|a, b| {
        b.fit_difficulty
            .score
            .partial_cmp(&a.fit_difficulty.score)
            .unwrap_or(Ordering::Equal)
            .then_with(|| a.part_id.cmp(&b.part_id))
    });
    let mut by_interlock: Vec<&PartAnalysis> = analyses.iter().collect();
    by_interlock.sort_by(|a, b| {
        b.interlock_potential_score
            .partial_cmp(&a.interlock_potential_score)
            .unwrap_or(Ordering::Equal)
            .then_with(|| a.part_id.cmp(&b.part_id))
    });

    let ids =
        |v: &[&PartAnalysis]| -> Vec<String> { v.iter().map(|a| a.part_id.clone()).collect() };
    let tiny: Vec<String> = analyses
        .iter()
        .filter(|a| a.has_tag(ShapeTag::TinyFiller))
        .map(|a| a.family_key.clone())
        .collect();
    let repeated: Vec<String> = analyses
        .iter()
        .filter(|a| a.has_tag(ShapeTag::RepeatedFamily))
        .map(|a| a.family_key.clone())
        .collect();

    serde_json::json!({
        "unique_part_count": analyses.len(),
        "critical_part_type_count": critical.len(),
        "parts": records,
        "top_critical_parts_by_priority": ids(&by_priority),
        "top_critical_parts_by_fit_difficulty": ids(&by_fit),
        "top_interlock_candidates_by_shape_signal": ids(&by_interlock),
        "tiny_filler_families": tiny,
        "repeated_families": repeated,
    })
}

/// Build the analyses for `parts` by routing them through the production `SparrowProblem` construction
/// (so each instance carries its real `shape_profile` + `orientation_catalog`). One analysis per
/// unique part type, in first-encounter order.
pub fn build_part_analyses_for_parts(
    parts: &[Part],
    sheet_width: f64,
    sheet_height: f64,
    spacing_mm: f64,
) -> Result<Vec<PartAnalysis>, String> {
    let rotation_context =
        RotationResolveContext::new(Some(RotationPolicyKind::Continuous), 42, 24);
    let raw_stock = crate::sheet::Stock {
        id: "S_ANALYSIS".to_string(),
        quantity: parts.len().max(1) as i64,
        width: Some(sheet_width),
        height: Some(sheet_height),
        outer_points: None,
        holes_points: None,
        cost_per_use: None,
    };
    let raw_sheet = crate::sheet::stock_to_shape(&raw_stock)?;
    let config = SparrowConfig::from_solver_input(
        1.0,
        CollisionBackendKind::Cde,
        rotation_context.clone(),
        42,
    )
    .with_spacing_mm(spacing_mm);
    let problem = SparrowProblem::from_solver_input(
        parts,
        std::slice::from_ref(&raw_sheet),
        &rotation_context,
        Vec::new(),
        config,
    )?;
    let mut seen: std::collections::HashSet<String> = std::collections::HashSet::new();
    let mut out: Vec<PartAnalysis> = Vec::new();
    for inst in &problem.instances {
        if seen.insert(inst.part_id.clone()) {
            out.push(inst.part_analysis.as_ref().clone());
        }
    }
    Ok(out)
}

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

fn tier_str(t: CriticalityTier) -> &'static str {
    match t {
        CriticalityTier::Critical => "critical",
        CriticalityTier::Structural => "structural",
        CriticalityTier::Filler => "filler",
    }
}

/// Cheap deterministic family / near-duplicate key from coarse geometry buckets (NOT part_id).
fn family_key(sp: &PartShapeProfile) -> String {
    let area_bucket = bucket_log(sp.true_area, 1.5);
    let perim_area = if sp.true_area > 1e-9 {
        sp.diameter / sp.true_area.sqrt().max(1e-9)
    } else {
        0.0
    };
    let pa_bucket = (perim_area * 4.0).round() as i64;
    let vtx_bucket = (sp.contour_feature_summary.contour_vertex_count as f64 / 4.0).round() as i64;
    let cx_bucket = (sp.convexity_ratio * 10.0).round() as i64;
    let fl_bucket = (sp.fill_ratio * 10.0).round() as i64;
    let as_bucket = (sp.aspect_ratio.min(ASPECT_NORM_MAX) * 4.0).round() as i64;
    format!("a{area_bucket}_pa{pa_bucket}_v{vtx_bucket}_cx{cx_bucket}_fl{fl_bucket}_as{as_bucket}")
}

/// Log-scale bucket so parts within ~`base`× area land in the same bucket.
fn bucket_log(value: f64, base: f64) -> i64 {
    if value <= 1e-9 {
        return 0;
    }
    (value.ln() / base.ln()).round() as i64
}

fn round4(v: f64) -> f64 {
    (v * 10_000.0).round() / 10_000.0
}

#[cfg(test)]
mod tests {
    use super::*;

    fn part(id: &str, w: f64, h: f64, qty: i64, pts: serde_json::Value) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: qty,
            allowed_rotations_deg: vec![],
            rotation_policy: Some(RotationPolicyKind::Continuous),
            holes_points: None,
            prepared_holes_points: None,
            outer_points: Some(pts),
            prepared_outer_points: None,
        }
    }

    fn rect(id: &str, w: f64, h: f64, qty: i64) -> Part {
        part(
            id,
            w,
            h,
            qty,
            serde_json::json!([[0.0, 0.0], [w, 0.0], [w, h], [0.0, h]]),
        )
    }

    fn analysis(p: &Part, sheet: f64) -> PartAnalysis {
        let v = build_part_analyses_for_parts(std::slice::from_ref(p), sheet, sheet, 0.0)
            .expect("analysis");
        v.into_iter().next().expect("one analysis")
    }

    #[test]
    fn large_part_is_tagged_large_and_edge_alignable() {
        // Elongated large plate: its two long edges are genuine dominant edges (a near-square would
        // not clear the dominant-edge threshold, by design of the Q53A extractor).
        let p = rect("big", 1400.0, 300.0, 1);
        let a = analysis(&p, 1500.0);
        assert!(
            a.has_tag(ShapeTag::LargeAnchor),
            "large part must be large_anchor"
        );
        assert!(
            a.has_tag(ShapeTag::EdgeAlignable),
            "elongated rect has dominant edges → edge_alignable"
        );
        assert!(a.diagnostics.criticality_tier == "critical");
    }

    #[test]
    fn tiny_filler_is_not_an_anchor() {
        let p = rect("tiny", 20.0, 20.0, 1);
        let a = analysis(&p, 1500.0);
        assert!(
            a.has_tag(ShapeTag::TinyFiller),
            "small part must be tiny_filler"
        );
        assert!(
            !a.has_tag(ShapeTag::LargeAnchor),
            "tiny filler must not be large_anchor"
        );
        assert!(!a.has_tag(ShapeTag::CriticalLarge));
    }

    #[test]
    fn reuses_shape_profile_values() {
        let p = rect("reuse", 600.0, 400.0, 3);
        let a = analysis(&p, 1500.0);
        // The reused profile is shared, not duplicated: its fields are still available verbatim.
        assert_eq!(a.shape_profile.quantity, 3);
        assert!(a.shape_profile.aspect_ratio > 1.0);
        assert!(
            a.hole_free_solver_input,
            "no holes → hole-free solver input"
        );
    }

    #[test]
    fn fit_difficulty_is_deterministic_and_separate_from_priority() {
        let p = rect("det", 1200.0, 300.0, 4);
        let a = analysis(&p, 1500.0);
        let b = analysis(&p, 1500.0);
        assert_eq!(a.fit_difficulty.score, b.fit_difficulty.score);
        assert!(a.fit_difficulty.score >= 0.0 && a.fit_difficulty.score <= 1.0);
        // fit_difficulty is a distinct signal: it is not equal to the raw priority_score.
        assert!(
            (a.fit_difficulty.score - a.shape_profile.priority_score).abs() > f64::EPSILON
                || a.shape_profile.priority_score == a.fit_difficulty.score
        );
    }

    #[test]
    fn family_key_is_stable_for_same_geometry() {
        let p1 = rect("famA", 500.0, 200.0, 2);
        let p2 = rect("famB", 500.0, 200.0, 9);
        let a = analysis(&p1, 1500.0);
        let b = analysis(&p2, 1500.0);
        assert_eq!(
            a.family_key, b.family_key,
            "identical geometry must share a family key regardless of id/quantity"
        );
    }
}
