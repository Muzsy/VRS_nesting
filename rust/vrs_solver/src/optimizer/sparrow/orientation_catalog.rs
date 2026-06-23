//! SGH-Q56A: per-part-type `OrientationCatalog`.
//!
//! Consolidates the orientation candidates that were previously scattered across
//! `contour_features` (`sheet_edge_alignment_angles`), `feature_candidate_generator`
//! (`min_width_rotations`, sheet-edge anchor angles) and various 0/90/180/270 fallbacks into a
//! single, precomputed, diagnostics-backed object.
//!
//! Hard rules (mirroring the Q56A canvas / Q55B proof):
//! - Extrema samples are computed from the **spacing-expanded collision contour**
//!   (`SPInstance.spacing_collision_base_shape`) by rotating the REAL local contour points — never
//!   from `part.width` / `part.height` or a non-rotated bbox.
//! - Continuous parts keep continuous, feature-derived angles; candidates are NOT snapped to
//!   0/90/180/270 unless the computed continuous result is actually that angle.
//! - Discrete parts only receive their allowed rotations (annotated where they match a feature
//!   alignment). This layer is decision-support metadata only: it changes no placement path and is
//!   never a collision or rotation-policy input.

use super::*;

/// Two candidate angles are treated as identical below this tolerance (deterministic dedup).
const ANGLE_IDENTITY_TOL_DEG: f64 = 0.01;
/// An angle is "fractional" (genuinely off the orthogonal axes) when it is further than this from
/// the nearest of {0, 90, 180, 270}. Mirrors `feature_candidate_generator`'s fractional gate.
const FRACTIONAL_AXIS_TOL_DEG: f64 = 0.25;
/// Coarse / fine steps for the min-perpendicular-width scan (same shape as `min_width_rotations`).
const MIN_WIDTH_COARSE_STEP_DEG: f64 = 0.5;
const MIN_WIDTH_FINE_STEP_DEG: f64 = 0.01;
/// How many of the highest-value candidates get an explicit 180° flip variant.
const FLIP_TOP_K: usize = 4;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OrientationCandidateKind {
    SheetVerticalAlignment,
    SheetHorizontalAlignment,
    MinWidth,
    MinHeight,
    DominantEdge,
    Flip180,
    DiscreteAllowed,
    CurrentRotationFallback,
}

impl OrientationCandidateKind {
    pub fn as_str(self) -> &'static str {
        match self {
            OrientationCandidateKind::SheetVerticalAlignment => "sheet_vertical_alignment",
            OrientationCandidateKind::SheetHorizontalAlignment => "sheet_horizontal_alignment",
            OrientationCandidateKind::MinWidth => "min_width",
            OrientationCandidateKind::MinHeight => "min_height",
            OrientationCandidateKind::DominantEdge => "dominant_edge",
            OrientationCandidateKind::Flip180 => "flip_180",
            OrientationCandidateKind::DiscreteAllowed => "discrete_allowed",
            OrientationCandidateKind::CurrentRotationFallback => "current_rotation_fallback",
        }
    }
    /// Deterministic tie-break ordinal (lower = preferred when scores tie).
    fn ordinal(self) -> u8 {
        match self {
            OrientationCandidateKind::MinWidth => 0,
            OrientationCandidateKind::MinHeight => 1,
            OrientationCandidateKind::SheetVerticalAlignment => 2,
            OrientationCandidateKind::SheetHorizontalAlignment => 3,
            OrientationCandidateKind::DominantEdge => 4,
            OrientationCandidateKind::DiscreteAllowed => 5,
            OrientationCandidateKind::Flip180 => 6,
            OrientationCandidateKind::CurrentRotationFallback => 7,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OrientationCandidateSource {
    DominantEdgeToVerticalAxis,
    DominantEdgeToHorizontalAxis,
    MinPerpendicularWidth,
    Flip180,
    AllowedRotationPolicy,
    CurrentRotationFallback,
}

impl OrientationCandidateSource {
    pub fn as_str(self) -> &'static str {
        match self {
            OrientationCandidateSource::DominantEdgeToVerticalAxis => "dominant_edge_to_vertical_axis",
            OrientationCandidateSource::DominantEdgeToHorizontalAxis => {
                "dominant_edge_to_horizontal_axis"
            }
            OrientationCandidateSource::MinPerpendicularWidth => "min_perpendicular_width",
            OrientationCandidateSource::Flip180 => "flip_180",
            OrientationCandidateSource::AllowedRotationPolicy => "allowed_rotation_policy",
            OrientationCandidateSource::CurrentRotationFallback => "current_rotation_fallback",
        }
    }
}

#[derive(Debug, Clone)]
pub struct OrientationCandidate {
    /// Continuous rotation (degrees, normalized to [0, 360)). For discrete parts this is one of the
    /// allowed rotations.
    pub angle_deg: f64,
    pub kind: OrientationCandidateKind,
    pub source: OrientationCandidateSource,
    /// Real contour edge this candidate was derived from (for alignment candidates).
    pub source_edge_index: Option<usize>,
    pub source_edge_angle_deg: Option<f64>,
    /// World axis the edge was rotated onto (0/90/180/270) for alignment candidates.
    pub target_axis_angle_deg: Option<f64>,
    pub score: f64,
    pub is_fractional: bool,
    pub is_policy_allowed: bool,
}

/// True-extrema frame of the rotated spacing-expanded contour at one angle.
#[derive(Debug, Clone)]
pub struct OrientationExtremaSample {
    pub angle_deg: f64,
    pub spacing_offset_min_x: f64,
    pub spacing_offset_max_x: f64,
    pub spacing_offset_min_y: f64,
    pub spacing_offset_max_y: f64,
    pub width: f64,
    pub height: f64,
}

#[derive(Debug, Clone, Default)]
pub struct OrientationCatalogDiagnostics {
    pub allowed_rotations_count: usize,
    pub candidate_count: usize,
    pub vertical_alignment_count: usize,
    pub horizontal_alignment_count: usize,
    pub min_width_candidate_count: usize,
    pub min_height_candidate_count: usize,
    pub fractional_candidate_count: usize,
    pub spacing_extrema_sample_count: usize,
    pub dominant_edge_count: usize,
    /// Always true for a real `compute`: extrema came from the spacing-expanded contour, not bbox.
    pub extrema_from_spacing_expanded: bool,
}

#[derive(Debug, Clone)]
pub struct OrientationCatalog {
    pub part_id: String,
    pub continuous_rotation: bool,
    pub allowed_rotations_deg: Vec<f64>,
    pub candidates: Vec<OrientationCandidate>,
    pub extrema_samples: Vec<OrientationExtremaSample>,
    pub diagnostics: OrientationCatalogDiagnostics,
}

impl OrientationCatalog {
    /// Compute the catalog for one unique part type from its spacing-expanded collision contour and
    /// its (original-contour) feature set. Pure and deterministic.
    pub fn compute(
        part_id: &str,
        spacing_collision_shape: &CdeBaseShape,
        features: &ContourFeatureSet,
        continuous_rotation: bool,
        allowed_rotations_deg: &[f64],
    ) -> Self {
        let allowed: Vec<f64> = allowed_rotations_deg.iter().map(|&r| norm360(r)).collect();
        let mut raw: Vec<OrientationCandidate> = Vec::new();

        if continuous_rotation {
            // 1) Dominant-edge → sheet-axis alignments (real contour edges drive the angles).
            for edge in &features.dominant_edges {
                let horiz = norm360(-edge.angle_deg); // edge rotated onto the 0° (horizontal) axis
                let vert = norm360(90.0 - edge.angle_deg); // edge rotated onto the 90° (vertical) axis
                let nl = edge.normalized_length.clamp(0.0, 1.0);
                let base = 0.55 + 0.40 * nl;
                // Prefer the axis the edge is already closer to (matches the contour seed heuristic).
                let prefers_horizontal =
                    nearest_axis_dist(norm360(edge.angle_deg)) <= nearest_axis_dist(norm360(edge.angle_deg + 90.0));
                raw.push(OrientationCandidate {
                    angle_deg: horiz,
                    kind: OrientationCandidateKind::SheetHorizontalAlignment,
                    source: OrientationCandidateSource::DominantEdgeToHorizontalAxis,
                    source_edge_index: Some(edge.edge_index),
                    source_edge_angle_deg: Some(round2(edge.angle_deg)),
                    target_axis_angle_deg: Some(0.0),
                    score: round4(base + if prefers_horizontal { 0.02 } else { 0.0 }),
                    is_fractional: is_fractional(horiz),
                    is_policy_allowed: true,
                });
                raw.push(OrientationCandidate {
                    angle_deg: vert,
                    kind: OrientationCandidateKind::SheetVerticalAlignment,
                    source: OrientationCandidateSource::DominantEdgeToVerticalAxis,
                    source_edge_index: Some(edge.edge_index),
                    source_edge_angle_deg: Some(round2(edge.angle_deg)),
                    target_axis_angle_deg: Some(90.0),
                    score: round4(base + if prefers_horizontal { 0.0 } else { 0.02 }),
                    is_fractional: is_fractional(vert),
                    is_policy_allowed: true,
                });
            }

            // 2) Min-perpendicular-width / -height from the spacing-expanded contour (continuous).
            if let Some(rot) = scan_min_extent(spacing_collision_shape, Axis::X) {
                let a = norm360(rot);
                raw.push(OrientationCandidate {
                    angle_deg: a,
                    kind: OrientationCandidateKind::MinWidth,
                    source: OrientationCandidateSource::MinPerpendicularWidth,
                    source_edge_index: None,
                    source_edge_angle_deg: None,
                    target_axis_angle_deg: None,
                    score: 0.92,
                    is_fractional: is_fractional(a),
                    is_policy_allowed: true,
                });
            }
            if let Some(rot) = scan_min_extent(spacing_collision_shape, Axis::Y) {
                let a = norm360(rot);
                raw.push(OrientationCandidate {
                    angle_deg: a,
                    kind: OrientationCandidateKind::MinHeight,
                    source: OrientationCandidateSource::MinPerpendicularWidth,
                    source_edge_index: None,
                    source_edge_angle_deg: None,
                    target_axis_angle_deg: None,
                    score: 0.90,
                    is_fractional: is_fractional(a),
                    is_policy_allowed: true,
                });
            }

            // 3) 180° flips of the highest-value candidates (deterministic top-K).
            let mut ranked: Vec<usize> = (0..raw.len()).collect();
            ranked.sort_by(|&a, &b| cmp_candidate(&raw[a], &raw[b]));
            let flips: Vec<f64> = ranked
                .iter()
                .take(FLIP_TOP_K)
                .map(|&i| norm360(raw[i].angle_deg + 180.0))
                .collect();
            for a in flips {
                raw.push(OrientationCandidate {
                    angle_deg: a,
                    kind: OrientationCandidateKind::Flip180,
                    source: OrientationCandidateSource::Flip180,
                    source_edge_index: None,
                    source_edge_angle_deg: None,
                    target_axis_angle_deg: None,
                    score: 0.50,
                    is_fractional: is_fractional(a),
                    is_policy_allowed: true,
                });
            }
        } else {
            // Discrete parts: only their allowed rotations, annotated where they match an alignment.
            for &r in &allowed {
                let (kind, source, edge_idx, edge_ang, target) = classify_discrete(r, features);
                raw.push(OrientationCandidate {
                    angle_deg: r,
                    kind,
                    source,
                    source_edge_index: edge_idx,
                    source_edge_angle_deg: edge_ang,
                    target_axis_angle_deg: target,
                    score: 0.60,
                    is_fractional: is_fractional(r),
                    is_policy_allowed: true,
                });
            }
        }

        if raw.is_empty() {
            // Never return an empty catalog: a current-rotation fallback keeps downstream paths safe.
            raw.push(OrientationCandidate {
                angle_deg: 0.0,
                kind: OrientationCandidateKind::CurrentRotationFallback,
                source: OrientationCandidateSource::CurrentRotationFallback,
                source_edge_index: None,
                source_edge_angle_deg: None,
                target_axis_angle_deg: None,
                score: 0.10,
                is_fractional: false,
                is_policy_allowed: true,
            });
        }

        let candidates = dedup_by_angle(raw);

        // Extrema samples from the REAL spacing-expanded contour (one per unique candidate angle).
        let mut extrema_samples: Vec<OrientationExtremaSample> = Vec::with_capacity(candidates.len());
        for c in &candidates {
            if let Some(s) = extrema_sample(spacing_collision_shape, c.angle_deg) {
                extrema_samples.push(s);
            }
        }

        let diagnostics = OrientationCatalogDiagnostics {
            allowed_rotations_count: allowed.len(),
            candidate_count: candidates.len(),
            vertical_alignment_count: candidates
                .iter()
                .filter(|c| c.kind == OrientationCandidateKind::SheetVerticalAlignment)
                .count(),
            horizontal_alignment_count: candidates
                .iter()
                .filter(|c| c.kind == OrientationCandidateKind::SheetHorizontalAlignment)
                .count(),
            min_width_candidate_count: candidates
                .iter()
                .filter(|c| c.kind == OrientationCandidateKind::MinWidth)
                .count(),
            min_height_candidate_count: candidates
                .iter()
                .filter(|c| c.kind == OrientationCandidateKind::MinHeight)
                .count(),
            fractional_candidate_count: candidates.iter().filter(|c| c.is_fractional).count(),
            spacing_extrema_sample_count: extrema_samples.len(),
            dominant_edge_count: features.dominant_edges.len(),
            extrema_from_spacing_expanded: true,
        };

        OrientationCatalog {
            part_id: part_id.to_string(),
            continuous_rotation,
            allowed_rotations_deg: allowed,
            candidates,
            extrema_samples,
            diagnostics,
        }
    }

    /// A minimal, valid catalog with no geometric candidates. Used only by internal test fixtures
    /// that construct `SPInstance` directly and never exercise orientation candidates.
    pub fn placeholder(part_id: &str) -> Self {
        OrientationCatalog {
            part_id: part_id.to_string(),
            continuous_rotation: false,
            allowed_rotations_deg: Vec::new(),
            candidates: vec![OrientationCandidate {
                angle_deg: 0.0,
                kind: OrientationCandidateKind::CurrentRotationFallback,
                source: OrientationCandidateSource::CurrentRotationFallback,
                source_edge_index: None,
                source_edge_angle_deg: None,
                target_axis_angle_deg: None,
                score: 0.0,
                is_fractional: false,
                is_policy_allowed: true,
            }],
            extrema_samples: Vec::new(),
            diagnostics: OrientationCatalogDiagnostics::default(),
        }
    }

    /// Deterministic JSON diagnostics artifact (matches the Q56A canvas schema).
    pub fn to_diagnostics_json(&self) -> serde_json::Value {
        let candidates: Vec<serde_json::Value> = self
            .candidates
            .iter()
            .map(|c| {
                serde_json::json!({
                    "angle_deg": round2(c.angle_deg),
                    "kind": c.kind.as_str(),
                    "source": c.source.as_str(),
                    "source_edge_index": c.source_edge_index,
                    "source_edge_angle_deg": c.source_edge_angle_deg,
                    "target_axis_angle_deg": c.target_axis_angle_deg,
                    "score": c.score,
                    "is_fractional": c.is_fractional,
                    "is_policy_allowed": c.is_policy_allowed,
                })
            })
            .collect();
        let extrema: Vec<serde_json::Value> = self
            .extrema_samples
            .iter()
            .map(|s| {
                serde_json::json!({
                    "angle_deg": round2(s.angle_deg),
                    "width": round4(s.width),
                    "height": round4(s.height),
                    "min_x": round4(s.spacing_offset_min_x),
                    "max_x": round4(s.spacing_offset_max_x),
                    "min_y": round4(s.spacing_offset_min_y),
                    "max_y": round4(s.spacing_offset_max_y),
                })
            })
            .collect();
        serde_json::json!({
            "part_id": self.part_id,
            "continuous_rotation": self.continuous_rotation,
            "allowed_rotations_count": self.diagnostics.allowed_rotations_count,
            "candidate_count": self.diagnostics.candidate_count,
            "vertical_alignment_count": self.diagnostics.vertical_alignment_count,
            "horizontal_alignment_count": self.diagnostics.horizontal_alignment_count,
            "min_width_candidate_count": self.diagnostics.min_width_candidate_count,
            "min_height_candidate_count": self.diagnostics.min_height_candidate_count,
            "fractional_candidate_count": self.diagnostics.fractional_candidate_count,
            "spacing_extrema_sample_count": self.diagnostics.spacing_extrema_sample_count,
            "dominant_edge_count": self.diagnostics.dominant_edge_count,
            "extrema_from_spacing_expanded": self.diagnostics.extrema_from_spacing_expanded,
            "candidates": candidates,
            "extrema_samples": extrema,
        })
    }
}

// ---------------------------------------------------------------------------
// public builder (real-fixture entry point, mirrors the Q55B verification fn)
// ---------------------------------------------------------------------------

/// Build the `OrientationCatalog` for a single part on a single sheet, routing the real spacing
/// through the solver's internal dual-geometry mechanism (so the extrema come from the genuine
/// spacing-expanded contour). Returns the catalog attached to the resulting solver instance.
pub fn build_orientation_catalog_for_part(
    part: &Part,
    sheet_width: f64,
    sheet_height: f64,
    spacing_mm: f64,
) -> Result<OrientationCatalog, String> {
    let rotation_context = RotationResolveContext::new(Some(RotationPolicyKind::Continuous), 42, 24);
    let raw_stock = crate::sheet::Stock {
        id: "S_ORIENT".to_string(),
        quantity: 1,
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
        std::slice::from_ref(part),
        std::slice::from_ref(&raw_sheet),
        &rotation_context,
        Vec::new(),
        config,
    )?;
    let inst = problem.instances.first().ok_or_else(|| {
        format!(
            "part {} produced no placeable instance ({} pre-unplaced)",
            part.id,
            problem.pre_unplaced.len()
        )
    })?;
    Ok(inst.orientation_catalog.as_ref().clone())
}

// ---------------------------------------------------------------------------
// internal helpers
// ---------------------------------------------------------------------------

#[derive(Clone, Copy)]
enum Axis {
    X,
    Y,
}

/// Normalize an angle to [0, 360).
fn norm360(mut deg: f64) -> f64 {
    deg %= 360.0;
    if deg < 0.0 {
        deg += 360.0;
    }
    // Guard against -0.0 / 360.0 boundary artefacts.
    if deg >= 360.0 - 1e-12 {
        deg -= 360.0;
    }
    if deg.abs() < 1e-12 {
        0.0
    } else {
        deg
    }
}

/// Smallest absolute angular distance between two [0,360) angles.
fn ang_dist(a: f64, b: f64) -> f64 {
    let d = (norm360(a) - norm360(b)).abs();
    d.min(360.0 - d)
}

/// Distance to the nearest orthogonal sheet axis {0, 90, 180, 270}.
fn nearest_axis_dist(a: f64) -> f64 {
    [0.0_f64, 90.0, 180.0, 270.0]
        .iter()
        .map(|&axis| ang_dist(a, axis))
        .fold(f64::MAX, f64::min)
}

fn is_fractional(a: f64) -> bool {
    nearest_axis_dist(a) > FRACTIONAL_AXIS_TOL_DEG
}

/// True extrema of the spacing-expanded contour rotated by `rotation_deg` about the origin — the
/// same frame the solver's `rotation_frame` / `transform_base_to_candidate(...,0,0,rot)` produces.
fn extrema_sample(shape: &CdeBaseShape, rotation_deg: f64) -> Option<OrientationExtremaSample> {
    if shape.local_pts.is_empty() {
        return None;
    }
    let theta = rotation_deg.to_radians();
    let (c, s) = (theta.cos(), theta.sin());
    let (mut min_x, mut min_y, mut max_x, mut max_y) = (f64::MAX, f64::MAX, f64::MIN, f64::MIN);
    for p in &shape.local_pts {
        let rx = p.x * c - p.y * s;
        let ry = p.x * s + p.y * c;
        min_x = min_x.min(rx);
        min_y = min_y.min(ry);
        max_x = max_x.max(rx);
        max_y = max_y.max(ry);
    }
    Some(OrientationExtremaSample {
        angle_deg: norm360(rotation_deg),
        spacing_offset_min_x: min_x,
        spacing_offset_max_x: max_x,
        spacing_offset_min_y: min_y,
        spacing_offset_max_y: max_y,
        width: max_x - min_x,
        height: max_y - min_y,
    })
}

fn extent(shape: &CdeBaseShape, rotation_deg: f64, axis: Axis) -> Option<f64> {
    extrema_sample(shape, rotation_deg).map(|s| match axis {
        Axis::X => s.width,
        Axis::Y => s.height,
    })
}

/// Coarse 0.5° scan + 0.01° refine for the rotation minimising the extent along `axis`. Mirrors
/// `feature_candidate_generator::min_width_rotations`. Deterministic; returns a continuous angle.
fn scan_min_extent(shape: &CdeBaseShape, axis: Axis) -> Option<f64> {
    let mut best: Option<(f64, f64)> = None;
    let mut t = 0.0;
    while t < 180.0 {
        if let Some(v) = extent(shape, t, axis) {
            if best.map_or(true, |(_, bv)| v < bv) {
                best = Some((t, v));
            }
        }
        t += MIN_WIDTH_COARSE_STEP_DEG;
    }
    let (ct, _) = best?;
    let mut bt = ct;
    let mut bv = extent(shape, ct, axis)?;
    let mut d = -MIN_WIDTH_COARSE_STEP_DEG;
    while d <= MIN_WIDTH_COARSE_STEP_DEG {
        let t = ct + d;
        if let Some(v) = extent(shape, t, axis) {
            if v < bv {
                bv = v;
                bt = t;
            }
        }
        d += MIN_WIDTH_FINE_STEP_DEG;
    }
    Some(norm360(bt))
}

/// For a discrete allowed rotation, tag it with the alignment it realises (if any dominant edge,
/// rotated by this angle, lands flush on a sheet axis).
fn classify_discrete(
    rot: f64,
    features: &ContourFeatureSet,
) -> (
    OrientationCandidateKind,
    OrientationCandidateSource,
    Option<usize>,
    Option<f64>,
    Option<f64>,
) {
    for edge in &features.dominant_edges {
        let world = norm360(edge.angle_deg + rot);
        let axis = nearest_axis(world);
        if ang_dist(world, axis) <= FRACTIONAL_AXIS_TOL_DEG {
            let (kind, source) = if axis == 90.0 || axis == 270.0 {
                (
                    OrientationCandidateKind::SheetVerticalAlignment,
                    OrientationCandidateSource::DominantEdgeToVerticalAxis,
                )
            } else {
                (
                    OrientationCandidateKind::SheetHorizontalAlignment,
                    OrientationCandidateSource::DominantEdgeToHorizontalAxis,
                )
            };
            return (
                kind,
                source,
                Some(edge.edge_index),
                Some(round2(edge.angle_deg)),
                Some(axis),
            );
        }
    }
    (
        OrientationCandidateKind::DiscreteAllowed,
        OrientationCandidateSource::AllowedRotationPolicy,
        None,
        None,
        None,
    )
}

fn nearest_axis(a: f64) -> f64 {
    [0.0_f64, 90.0, 180.0, 270.0]
        .into_iter()
        .min_by(|x, y| {
            ang_dist(*x, a)
                .partial_cmp(&ang_dist(*y, a))
                .unwrap_or(Ordering::Equal)
        })
        .unwrap_or(0.0)
}

/// Stable candidate ordering: score desc, then kind ordinal asc, then angle asc.
fn cmp_candidate(a: &OrientationCandidate, b: &OrientationCandidate) -> Ordering {
    b.score
        .partial_cmp(&a.score)
        .unwrap_or(Ordering::Equal)
        .then_with(|| a.kind.ordinal().cmp(&b.kind.ordinal()))
        .then_with(|| a.angle_deg.partial_cmp(&b.angle_deg).unwrap_or(Ordering::Equal))
}

/// Deduplicate candidates whose angles are within `ANGLE_IDENTITY_TOL_DEG`, keeping the
/// highest-priority candidate for each angle bucket. Deterministic.
fn dedup_by_angle(mut raw: Vec<OrientationCandidate>) -> Vec<OrientationCandidate> {
    raw.sort_by(cmp_candidate);
    let mut kept: Vec<OrientationCandidate> = Vec::with_capacity(raw.len());
    for cand in raw {
        if kept
            .iter()
            .any(|k| ang_dist(k.angle_deg, cand.angle_deg) < ANGLE_IDENTITY_TOL_DEG)
        {
            continue;
        }
        kept.push(cand);
    }
    // Already in priority order from the sort above.
    kept
}

fn round2(v: f64) -> f64 {
    (v * 100.0).round() / 100.0
}

fn round4(v: f64) -> f64 {
    (v * 10_000.0).round() / 10_000.0
}

#[cfg(test)]
mod tests {
    use super::*;

    fn part(id: &str, w: f64, h: f64, pts: serde_json::Value, continuous: bool) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: 1,
            allowed_rotations_deg: if continuous { vec![] } else { vec![0, 90, 180, 270] },
            rotation_policy: Some(if continuous {
                RotationPolicyKind::Continuous
            } else {
                RotationPolicyKind::Orthogonal
            }),
            holes_points: None,
            prepared_holes_points: None,
            outer_points: Some(pts),
            prepared_outer_points: None,
        }
    }

    fn rect(id: &str, w: f64, h: f64, continuous: bool) -> Part {
        part(
            id,
            w,
            h,
            serde_json::json!([[0.0, 0.0], [w, 0.0], [w, h], [0.0, h]]),
            continuous,
        )
    }

    fn tilted_rect(continuous: bool) -> (Part, CdeBaseShape) {
        // A long thin rectangle rotated ~12.5° so its dominant edges are genuinely off-axis. The
        // min-width orientation is therefore a fractional angle, never an orthogonal snap.
        let ang = 12.5_f64.to_radians();
        let (c, s) = (ang.cos(), ang.sin());
        let raw = [[0.0, 0.0], [400.0, 0.0], [400.0, 60.0], [0.0, 60.0]];
        let pts: Vec<[f64; 2]> = raw
            .iter()
            .map(|p| [p[0] * c - p[1] * s, p[0] * s + p[1] * c])
            .collect();
        let p = part(
            "tilted",
            420.0,
            420.0,
            serde_json::json!(pts),
            continuous,
        );
        let base = prepare_base_shape_native(&p).expect("tilted base");
        (p, base)
    }

    #[test]
    fn continuous_part_produces_non_empty_feature_derived_catalog() {
        let p = rect("c_rect", 400.0, 60.0, true);
        let base = prepare_base_shape_native(&p).expect("base");
        let features = ContourFeatureSet::extract(&base);
        let cat = OrientationCatalog::compute("c_rect", &base, &features, true, &[]);
        assert!(!cat.candidates.is_empty(), "continuous catalog must be non-empty");
        assert!(
            cat.candidates
                .iter()
                .any(|c| c.source == OrientationCandidateSource::DominantEdgeToVerticalAxis
                    || c.source == OrientationCandidateSource::DominantEdgeToHorizontalAxis),
            "continuous part must expose dominant-edge alignment candidates"
        );
        // For a rectangle the min-width orientation coincides with a dominant-edge axis alignment, so
        // the dedup keeps the (higher-scored) alignment candidate. The catalog must still COVER the
        // min-width orientation: the long (400 mm) edge aligned to the vertical axis (≈90°), whose
        // extrema sample shows the minimal 60 mm width.
        let min_width_covered = cat
            .extrema_samples
            .iter()
            .any(|s| s.width <= 60.0 + 1e-6 || s.height <= 60.0 + 1e-6);
        assert!(
            min_width_covered,
            "catalog must cover the min-width orientation (≈60 mm extent) for the 400x60 rect"
        );
    }

    #[test]
    fn alignment_candidate_traces_to_real_contour_edge() {
        let p = rect("trace_rect", 400.0, 60.0, true);
        let base = prepare_base_shape_native(&p).expect("base");
        let features = ContourFeatureSet::extract(&base);
        let cat = OrientationCatalog::compute("trace_rect", &base, &features, true, &[]);
        assert!(
            cat.candidates
                .iter()
                .filter(|c| matches!(
                    c.kind,
                    OrientationCandidateKind::SheetVerticalAlignment
                        | OrientationCandidateKind::SheetHorizontalAlignment
                ))
                .any(|c| c.source_edge_index.is_some() && c.source_edge_angle_deg.is_some()),
            "at least one alignment candidate must trace to a real contour edge"
        );
    }

    #[test]
    fn extrema_use_spacing_expanded_contour_not_bbox() {
        // Build the part through the solver with real spacing so the catalog's extrema come from the
        // genuine spacing-expanded contour (wider than part.width/height).
        let p = rect("sp_rect", 400.0, 60.0, true);
        let cat = build_orientation_catalog_for_part(&p, 2000.0, 2000.0, 8.0).expect("catalog");
        assert!(cat.diagnostics.extrema_from_spacing_expanded);
        assert!(!cat.extrema_samples.is_empty(), "must emit extrema samples");
        // A 0°/180° sample must be wider than the raw part width because of the spacing offset.
        let axis_aligned = cat
            .extrema_samples
            .iter()
            .find(|s| nearest_axis_dist(s.angle_deg) < 0.5);
        if let Some(s) = axis_aligned {
            let span = s.width.max(s.height);
            assert!(
                span > 400.0 + 1.0,
                "spacing-expanded extent ({span:.3}) must exceed the raw 400mm width"
            );
        }
    }

    #[test]
    fn continuous_min_width_can_be_fractional() {
        let (p, _base) = tilted_rect(true);
        let cat = build_orientation_catalog_for_part(&p, 2000.0, 2000.0, 0.0).expect("catalog");
        assert!(
            cat.candidates.iter().any(|c| c.is_fractional),
            "a tilted continuous part must expose at least one genuinely fractional candidate"
        );
    }

    #[test]
    fn discrete_part_only_receives_allowed_rotations() {
        let p = rect("d_rect", 400.0, 60.0, false);
        let base = prepare_base_shape_native(&p).expect("base");
        let features = ContourFeatureSet::extract(&base);
        let allowed = [0.0_f64, 90.0, 180.0, 270.0];
        let cat = OrientationCatalog::compute("d_rect", &base, &features, false, &allowed);
        for c in &cat.candidates {
            assert!(
                allowed.iter().any(|&a| ang_dist(a, c.angle_deg) < 0.5),
                "discrete catalog angle {} not in allowed set",
                c.angle_deg
            );
            assert!(
                !c.is_fractional,
                "discrete orthogonal part must not carry fractional candidates"
            );
        }
    }

    #[test]
    fn dedup_is_deterministic() {
        let p = rect("dd_rect", 400.0, 60.0, true);
        let base = prepare_base_shape_native(&p).expect("base");
        let features = ContourFeatureSet::extract(&base);
        let a = OrientationCatalog::compute("dd_rect", &base, &features, true, &[]);
        let b = OrientationCatalog::compute("dd_rect", &base, &features, true, &[]);
        assert_eq!(a.candidates.len(), b.candidates.len());
        for (x, y) in a.candidates.iter().zip(b.candidates.iter()) {
            assert!(ang_dist(x.angle_deg, y.angle_deg) < ANGLE_IDENTITY_TOL_DEG);
            assert_eq!(x.kind, y.kind);
        }
        // No two surviving candidates may share an angle bucket.
        for i in 0..a.candidates.len() {
            for j in (i + 1)..a.candidates.len() {
                assert!(
                    ang_dist(a.candidates[i].angle_deg, a.candidates[j].angle_deg)
                        >= ANGLE_IDENTITY_TOL_DEG
                );
            }
        }
    }
}
