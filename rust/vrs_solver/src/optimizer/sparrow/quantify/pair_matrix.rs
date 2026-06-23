//! SGH-Q57A: `PairCompatibilityIndex` — critical-only precomputed pair candidates.
//!
//! Supersedes the former `PairMatrix` stub. Builds a bounded, critical-only index of high-value pair
//! candidates (same-part flips, dominant-edge-parallel, orientation-catalog pairs) for later Interlock
//! work (Q57B). It reuses the Q56A `OrientationCatalog`, the Q56B `PartAnalysis` and the spacing-expanded
//! collision contour — it does NOT duplicate contour-feature extraction and does NOT (yet) change any
//! placement decision. Clearance here is a deterministic grid proxy on the spacing-expanded contours;
//! the CDE remains the final clearance truth.

use super::*;

const GRID_SAMPLES: usize = 48;
const SIDE_GAP_MM: f64 = 0.0; // spacing already baked into the spacing-expanded contour
const INTERLOCK_OVERLAP_FRAC: f64 = 0.35; // how far the flipped partner is nudged into A's long span

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PairCandidateSource {
    SamePartFlip,
    SameFamilyFlip,
    DominantEdgeParallel,
    OrientationCatalogPair,
}

impl PairCandidateSource {
    pub fn as_str(self) -> &'static str {
        match self {
            PairCandidateSource::SamePartFlip => "same_part_flip",
            PairCandidateSource::SameFamilyFlip => "same_family_flip",
            PairCandidateSource::DominantEdgeParallel => "dominant_edge_parallel",
            PairCandidateSource::OrientationCatalogPair => "orientation_catalog_pair",
        }
    }
}

#[derive(Debug, Clone)]
pub struct PairCompatibilityCandidate {
    pub part_a_id: String,
    pub part_b_id: String,
    pub rotation_a_deg: f64,
    pub rotation_b_deg: f64,
    pub relative_dx: f64,
    pub relative_dy: f64,
    pub candidate_source: PairCandidateSource,
    pub compactness_gain: f64,
    pub bbox_area_reduction: f64,
    pub interlock_depth_score: f64,
    pub spacing_clear: bool,
    pub cde_clear: bool,
    pub score: f64,
    pub rejection_reason: Option<String>,
}

#[derive(Debug, Clone, Copy)]
pub struct PairIndexConfig {
    pub max_part_types: usize,
    pub topk_per_part: usize,
    pub max_candidates: usize,
}

impl Default for PairIndexConfig {
    fn default() -> Self {
        Self {
            max_part_types: 64,
            topk_per_part: 12,
            max_candidates: 512,
        }
    }
}

impl PairIndexConfig {
    pub fn from_env() -> Self {
        let d = Self::default();
        Self {
            max_part_types: env_usize("VRS_PAIR_INDEX_MAX_PART_TYPES", d.max_part_types),
            topk_per_part: env_usize("VRS_PAIR_INDEX_TOPK_PER_PART", d.topk_per_part),
            max_candidates: env_usize("VRS_PAIR_INDEX_MAX_CANDIDATES", d.max_candidates),
        }
    }
}

pub fn pair_index_enabled() -> bool {
    std::env::var("VRS_PAIR_INDEX").ok().as_deref() == Some("1")
}

#[derive(Debug, Clone)]
pub struct PairCompatibilityIndex {
    pub unique_part_count: usize,
    pub critical_part_type_count: usize,
    pub candidates: Vec<PairCompatibilityCandidate>,
}

impl PairCompatibilityIndex {
    pub fn valid_candidates(&self) -> usize {
        self.candidates.iter().filter(|c| c.cde_clear && c.spacing_clear).count()
    }

    pub fn to_diagnostics_json(&self) -> serde_json::Value {
        let by_source = |src: PairCandidateSource| {
            self.candidates.iter().filter(|c| c.candidate_source == src).count()
        };
        let top: Vec<serde_json::Value> = self
            .candidates
            .iter()
            .map(|c| {
                serde_json::json!({
                    "part_a_id": c.part_a_id,
                    "part_b_id": c.part_b_id,
                    "rotation_a_deg": round4(c.rotation_a_deg),
                    "rotation_b_deg": round4(c.rotation_b_deg),
                    "relative_dx": round4(c.relative_dx),
                    "relative_dy": round4(c.relative_dy),
                    "source": c.candidate_source.as_str(),
                    "compactness_gain": round4(c.compactness_gain),
                    "bbox_area_reduction": round4(c.bbox_area_reduction),
                    "interlock_depth_score": round4(c.interlock_depth_score),
                    "spacing_clear": c.spacing_clear,
                    "cde_clear": c.cde_clear,
                    "score": round4(c.score),
                    "rejection_reason": c.rejection_reason,
                })
            })
            .collect();
        let lv8_same_part: Vec<serde_json::Value> = self
            .candidates
            .iter()
            .filter(|c| c.candidate_source == PairCandidateSource::SamePartFlip && c.part_a_id == c.part_b_id)
            .map(|c| {
                serde_json::json!({
                    "part_id": c.part_a_id,
                    "rotation_a_deg": round4(c.rotation_a_deg),
                    "rotation_b_deg": round4(c.rotation_b_deg),
                    "cde_clear": c.cde_clear,
                    "compactness_gain": round4(c.compactness_gain),
                    "score": round4(c.score),
                })
            })
            .collect();
        serde_json::json!({
            "unique_part_count": self.unique_part_count,
            "critical_part_type_count": self.critical_part_type_count,
            "candidate_count_total": self.candidates.len(),
            "candidate_count_valid": self.valid_candidates(),
            "candidate_count_by_source": {
                "same_part_flip": by_source(PairCandidateSource::SamePartFlip),
                "same_family_flip": by_source(PairCandidateSource::SameFamilyFlip),
                "dominant_edge_parallel": by_source(PairCandidateSource::DominantEdgeParallel),
                "orientation_catalog_pair": by_source(PairCandidateSource::OrientationCatalogPair),
            },
            "top_pairs": top,
            "lv8_critical_same_part_pair_candidates": lv8_same_part,
        })
    }
}

/// One unique critical part type, with the geometry/analysis needed for pairing.
struct PairPartCtx {
    part_id: String,
    family_key: String,
    is_critical: bool,
    is_large_anchor: bool,
    is_high_interlock: bool,
    interlock_potential: f64,
    primary_rotations: Vec<f64>,
    spacing_shape: Rc<CdeBaseShape>,
}

/// Build the critical-only pair compatibility index for `parts` on a representative sheet.
pub fn build_pair_compatibility_index(
    parts: &[Part],
    sheet_width: f64,
    sheet_height: f64,
    spacing_mm: f64,
    config: PairIndexConfig,
) -> Result<PairCompatibilityIndex, String> {
    let rotation_context = RotationResolveContext::new(Some(RotationPolicyKind::Continuous), 42, 24);
    let raw_stock = crate::sheet::Stock {
        id: "S_PAIR".to_string(),
        quantity: parts.len().max(1) as i64,
        width: Some(sheet_width),
        height: Some(sheet_height),
        outer_points: None,
        holes_points: None,
        cost_per_use: None,
    };
    let raw_sheet = crate::sheet::stock_to_shape(&raw_stock)?;
    let cfg = SparrowConfig::from_solver_input(1.0, CollisionBackendKind::Cde, rotation_context.clone(), 42)
        .with_spacing_mm(spacing_mm);
    let problem = SparrowProblem::from_solver_input(
        parts,
        std::slice::from_ref(&raw_sheet),
        &rotation_context,
        Vec::new(),
        cfg,
    )?;

    let mut seen: std::collections::HashSet<String> = std::collections::HashSet::new();
    let mut ctxs: Vec<PairPartCtx> = Vec::new();
    for inst in &problem.instances {
        if !seen.insert(inst.part_id.clone()) {
            continue;
        }
        let pa = inst.part_analysis.as_ref();
        let sp = inst.shape_profile.as_ref();
        let mut rots: Vec<f64> = inst
            .orientation_catalog
            .candidates
            .iter()
            .filter(|c| {
                matches!(
                    c.kind,
                    OrientationCandidateKind::SheetVerticalAlignment
                        | OrientationCandidateKind::MinWidth
                        | OrientationCandidateKind::SheetHorizontalAlignment
                )
            })
            .map(|c| c.angle_deg)
            .collect();
        rots.dedup_by(|a, b| (*a - *b).abs() < 0.01);
        if rots.is_empty() {
            rots.push(0.0);
        }
        ctxs.push(PairPartCtx {
            part_id: inst.part_id.clone(),
            family_key: pa.family_key.clone(),
            is_critical: sp.is_critical(),
            is_large_anchor: sp.is_large_anchor,
            is_high_interlock: sp.is_high_interlock_potential,
            interlock_potential: pa.interlock_potential_score,
            primary_rotations: rots,
            spacing_shape: Rc::clone(&inst.spacing_collision_base_shape),
        });
    }
    let unique_part_count = ctxs.len();
    // Critical-only, bounded.
    let critical: Vec<&PairPartCtx> = ctxs
        .iter()
        .filter(|c| c.is_critical)
        .take(config.max_part_types)
        .collect();
    let critical_part_type_count = critical.len();

    let mut candidates: Vec<PairCompatibilityCandidate> = Vec::new();
    for (i, a) in critical.iter().enumerate() {
        let mut per_part = 0usize;
        for b in critical.iter().skip(i) {
            // Stage-1 cheap filter: skip pairs that aren't structurally interesting.
            let same_part = a.part_id == b.part_id;
            let same_family = a.family_key == b.family_key && !a.family_key.is_empty();
            let cheap_ok = same_part
                || same_family
                || (a.is_large_anchor && b.is_high_interlock)
                || (a.is_high_interlock && b.is_large_anchor)
                || (a.is_large_anchor && b.is_large_anchor);
            if !cheap_ok {
                continue;
            }
            // Stage-2 bounded geometric candidates.
            let mut local = generate_pair_candidates(a, b, same_part, same_family);
            local.sort_by(|x, y| y.score.partial_cmp(&x.score).unwrap_or(Ordering::Equal));
            local.truncate(config.topk_per_part);
            for c in local {
                candidates.push(c);
                per_part += 1;
                if per_part >= config.topk_per_part {
                    break;
                }
            }
            if candidates.len() >= config.max_candidates {
                break;
            }
        }
        if candidates.len() >= config.max_candidates {
            break;
        }
    }
    candidates.sort_by(|x, y| {
        y.score
            .partial_cmp(&x.score)
            .unwrap_or(Ordering::Equal)
            .then_with(|| x.part_a_id.cmp(&y.part_a_id))
            .then_with(|| x.part_b_id.cmp(&y.part_b_id))
    });
    candidates.truncate(config.max_candidates);

    Ok(PairCompatibilityIndex {
        unique_part_count,
        critical_part_type_count,
        candidates,
    })
}

fn generate_pair_candidates(
    a: &PairPartCtx,
    b: &PairPartCtx,
    same_part: bool,
    same_family: bool,
) -> Vec<PairCompatibilityCandidate> {
    let mut out: Vec<PairCompatibilityCandidate> = Vec::new();
    let rot_a = a.primary_rotations[0];
    let rot_b = b.primary_rotations[0];

    // (1) Dominant-edge-parallel side-by-side along X (B placed to the right of A, contours adjacent).
    if let (Some(fa), Some(fb)) = (frame(&a.spacing_shape, rot_a), frame(&b.spacing_shape, rot_b)) {
        let dx = (fa[2] - fa[0]) + SIDE_GAP_MM; // shift B right by A's width
        let dy = 0.0;
        let src = if same_part {
            PairCandidateSource::SamePartFlip
        } else if same_family {
            PairCandidateSource::SameFamilyFlip
        } else {
            PairCandidateSource::DominantEdgeParallel
        };
        out.push(assess_pair(a, b, rot_a, rot_b, dx, dy, &fa, &fb, src));
    }

    // (2) Same-part / same-family flip: B = partner at rot+180, nudged into A's long span (interlock).
    if same_part || same_family {
        let rot_b_flip = rot_a + 180.0;
        if let (Some(fa), Some(fb)) = (frame(&a.spacing_shape, rot_a), frame(&b.spacing_shape, rot_b_flip)) {
            let a_h = fa[3] - fa[1];
            // Stack vertically but nudge down so the flipped partner interlocks into A's long span.
            let dy = a_h - INTERLOCK_OVERLAP_FRAC * a_h;
            out.push(assess_pair(a, b, rot_a, rot_b_flip, 0.0, dy, &fa, &fb, PairCandidateSource::SamePartFlip));
            // Also a guaranteed-clear stacked variant (no interlock overlap) as a valid baseline.
            let dy_clear = a_h + SIDE_GAP_MM;
            out.push(assess_pair(a, b, rot_a, rot_b_flip, 0.0, dy_clear, &fa, &fb, PairCandidateSource::SamePartFlip));
        }
    }

    // (3) Orientation-catalog pair: A primary, B alternate rotation, side-by-side along X.
    if a.primary_rotations.len() > 1 || b.primary_rotations.len() > 1 {
        let ra = a.primary_rotations[0];
        let rb = *b.primary_rotations.last().unwrap();
        if let (Some(fa), Some(fb)) = (frame(&a.spacing_shape, ra), frame(&b.spacing_shape, rb)) {
            let dx = (fa[2] - fa[0]) + SIDE_GAP_MM;
            out.push(assess_pair(a, b, ra, rb, dx, 0.0, &fa, &fb, PairCandidateSource::OrientationCatalogPair));
        }
    }
    out
}

#[allow(clippy::too_many_arguments)]
fn assess_pair(
    a: &PairPartCtx,
    b: &PairPartCtx,
    rot_a: f64,
    rot_b: f64,
    dx: f64,
    dy: f64,
    fa: &[f64; 4],
    fb: &[f64; 4],
    source: PairCandidateSource,
) -> PairCompatibilityCandidate {
    // World bboxes: A at origin, B translated by (dx,dy).
    let a_box = *fa;
    let b_box = [fb[0] + dx, fb[1] + dy, fb[2] + dx, fb[3] + dy];
    let bbox_overlap = !(a_box[2] <= b_box[0]
        || b_box[2] <= a_box[0]
        || a_box[3] <= b_box[1]
        || b_box[3] <= a_box[1]);
    // spacing_clear: spacing-expanded bboxes do not overlap (conservative, definitely clear).
    let spacing_clear = !bbox_overlap;
    // cde_clear: if bboxes are disjoint → clear; otherwise grid-test the spacing-expanded contours.
    let cde_clear = if !bbox_overlap {
        true
    } else {
        !contours_overlap(&a.spacing_shape, rot_a, 0.0, 0.0, &b.spacing_shape, rot_b, dx, dy)
    };

    // Combined bbox vs two separate bboxes → compactness.
    let comb_min_x = a_box[0].min(b_box[0]);
    let comb_min_y = a_box[1].min(b_box[1]);
    let comb_max_x = a_box[2].max(b_box[2]);
    let comb_max_y = a_box[3].max(b_box[3]);
    let comb_area = ((comb_max_x - comb_min_x) * (comb_max_y - comb_min_y)).max(1.0);
    let a_area = ((a_box[2] - a_box[0]) * (a_box[3] - a_box[1])).max(1.0);
    let b_area = ((b_box[2] - b_box[0]) * (b_box[3] - b_box[1])).max(1.0);
    let separate_area = 2.0 * a_area.max(b_area);
    let compactness_gain = (1.0 - comb_area / separate_area).clamp(0.0, 1.0);
    let bbox_area_reduction = (separate_area - comb_area).max(0.0);
    let interlock_depth_score = if bbox_overlap && cde_clear {
        ((a.interlock_potential + b.interlock_potential) * 0.5).clamp(0.0, 1.0)
    } else {
        0.0
    };

    let score = if cde_clear && spacing_clear {
        0.5 * compactness_gain + 0.3 + 0.2 * interlock_depth_score
    } else if cde_clear {
        // overlapping bboxes but contours clear (genuine interlock) — most valuable when it holds.
        0.5 * compactness_gain + 0.4 + 0.3 * interlock_depth_score
    } else {
        0.0
    };
    let rejection_reason = if cde_clear {
        None
    } else {
        Some("contour_overlap_at_relative_transform".to_string())
    };

    PairCompatibilityCandidate {
        part_a_id: a.part_id.clone(),
        part_b_id: b.part_id.clone(),
        rotation_a_deg: rot_a,
        rotation_b_deg: rot_b,
        relative_dx: dx,
        relative_dy: dy,
        candidate_source: source,
        compactness_gain,
        bbox_area_reduction,
        interlock_depth_score,
        spacing_clear,
        cde_clear,
        score,
        rejection_reason,
    }
}

fn frame(shape: &CdeBaseShape, rot: f64) -> Option<[f64; 4]> {
    if shape.local_pts.is_empty() {
        return None;
    }
    let t = rot.to_radians();
    let (c, s) = (t.cos(), t.sin());
    let (mut mnx, mut mny, mut mxx, mut mxy) = (f64::MAX, f64::MAX, f64::MIN, f64::MIN);
    for p in &shape.local_pts {
        let rx = p.x * c - p.y * s;
        let ry = p.x * s + p.y * c;
        mnx = mnx.min(rx);
        mny = mny.min(ry);
        mxx = mxx.max(rx);
        mxy = mxy.max(ry);
    }
    Some([mnx, mny, mxx, mxy])
}

fn rotated_translated(shape: &CdeBaseShape, rot: f64, dx: f64, dy: f64) -> Vec<(f64, f64)> {
    let t = rot.to_radians();
    let (c, s) = (t.cos(), t.sin());
    shape
        .local_pts
        .iter()
        .map(|p| (p.x * c - p.y * s + dx, p.x * s + p.y * c + dy))
        .collect()
}

/// Deterministic grid overlap proxy: sample the bbox-overlap region; report overlap if any sample is
/// interior to BOTH spacing-expanded contours. Conservative ranking proxy only (CDE remains truth).
fn contours_overlap(
    sa: &CdeBaseShape,
    rot_a: f64,
    ax: f64,
    ay: f64,
    sb: &CdeBaseShape,
    rot_b: f64,
    bx: f64,
    by: f64,
) -> bool {
    let pa = rotated_translated(sa, rot_a, ax, ay);
    let pb = rotated_translated(sb, rot_b, bx, by);
    let (amnx, amny, amxx, amxy) = bbox(&pa);
    let (bmnx, bmny, bmxx, bmxy) = bbox(&pb);
    let ox0 = amnx.max(bmnx);
    let oy0 = amny.max(bmny);
    let ox1 = amxx.min(bmxx);
    let oy1 = amxy.min(bmxy);
    if ox0 >= ox1 || oy0 >= oy1 {
        return false;
    }
    for j in 0..GRID_SAMPLES {
        let fy = (j as f64 + 0.5) / GRID_SAMPLES as f64;
        let y = oy0 + fy * (oy1 - oy0);
        for i in 0..GRID_SAMPLES {
            let fx = (i as f64 + 0.5) / GRID_SAMPLES as f64;
            let x = ox0 + fx * (ox1 - ox0);
            if point_in_poly(x, y, &pa) && point_in_poly(x, y, &pb) {
                return true;
            }
        }
    }
    false
}

fn bbox(pts: &[(f64, f64)]) -> (f64, f64, f64, f64) {
    let (mut mnx, mut mny, mut mxx, mut mxy) = (f64::MAX, f64::MAX, f64::MIN, f64::MIN);
    for &(x, y) in pts {
        mnx = mnx.min(x);
        mny = mny.min(y);
        mxx = mxx.max(x);
        mxy = mxy.max(y);
    }
    (mnx, mny, mxx, mxy)
}

fn point_in_poly(x: f64, y: f64, poly: &[(f64, f64)]) -> bool {
    let n = poly.len();
    if n < 3 {
        return false;
    }
    let mut inside = false;
    let mut j = n - 1;
    for i in 0..n {
        let (xi, yi) = poly[i];
        let (xj, yj) = poly[j];
        if ((yi > y) != (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi) {
            inside = !inside;
        }
        j = i;
    }
    inside
}

fn env_usize(key: &str, default: usize) -> usize {
    std::env::var(key).ok().and_then(|v| v.parse().ok()).unwrap_or(default)
}

fn round4(v: f64) -> f64 {
    (v * 10_000.0).round() / 10_000.0
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rect(id: &str, w: f64, h: f64, qty: i64) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: qty,
            allowed_rotations_deg: vec![],
            rotation_policy: Some(RotationPolicyKind::Continuous),
            holes_points: None,
            prepared_holes_points: None,
            outer_points: Some(serde_json::json!([[0.0, 0.0], [w, 0.0], [w, h], [0.0, h]])),
            prepared_outer_points: None,
        }
    }

    fn idx(parts: &[Part]) -> PairCompatibilityIndex {
        build_pair_compatibility_index(parts, 1500.0, 3000.0, 8.0, PairIndexConfig::default())
            .expect("index")
    }

    #[test]
    fn builds_deterministically() {
        let parts = vec![rect("big", 1200.0, 300.0, 6), rect("tiny", 20.0, 20.0, 40)];
        let a = idx(&parts);
        let b = idx(&parts);
        assert_eq!(a.candidates.len(), b.candidates.len());
        assert_eq!(a.critical_part_type_count, b.critical_part_type_count);
    }

    #[test]
    fn critical_only_excludes_tiny_filler_pairs() {
        let parts = vec![rect("big", 1200.0, 300.0, 6), rect("tiny", 20.0, 20.0, 40)];
        let index = idx(&parts);
        assert!(
            index.candidates.iter().all(|c| c.part_a_id != "tiny" && c.part_b_id != "tiny"),
            "tiny filler must not appear in the critical-only index"
        );
    }

    #[test]
    fn repeated_critical_part_produces_same_part_pair() {
        let parts = vec![rect("big", 1200.0, 300.0, 6)];
        let index = idx(&parts);
        assert!(
            index.candidates.iter().any(|c| c.part_a_id == "big"
                && c.part_b_id == "big"
                && c.candidate_source == PairCandidateSource::SamePartFlip),
            "a repeated critical part must yield a same-part flip candidate"
        );
    }

    #[test]
    fn candidates_carry_rotation_metadata_and_have_a_valid_pair() {
        let parts = vec![rect("big", 1200.0, 300.0, 6)];
        let index = idx(&parts);
        assert!(!index.candidates.is_empty());
        assert!(index.valid_candidates() >= 1, "must have at least one valid (clear) pair candidate");
        for c in &index.candidates {
            assert!(c.rotation_a_deg.is_finite() && c.rotation_b_deg.is_finite());
        }
    }
}
