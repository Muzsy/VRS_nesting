//! SGH-Q53B: contour-feature driven placement seed generation for critical admission.
//!
//! This module generates a bounded set of candidate rect-min seeds from the moving part's
//! contour features and already-placed neighbour features (or the sheet boundary). The seeds are
//! advisory only: CDE remains the single clearance truth, and the legacy contour-near bbox-corner
//! path stays available as an explicit fallback.

use super::*;
use crate::item::resolve_part_rotation_angles_with_context;
use crate::optimizer::sparrow::density::DensityWeights;
use crate::rotation_policy::normalize_angle;

const FEATURE_SEED_EPS: f64 = 0.5;
const KEY_SCALE: f64 = 100.0;
const EPS: f64 = 1e-9;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CandidateSeedSource {
    ContourFeature,
    BboxCornerFallback,
}

#[derive(Debug, Clone, PartialEq)]
pub struct CandidateSeed {
    /// Rect-min x in sheet coordinates.
    pub x: f64,
    /// Rect-min y in sheet coordinates.
    pub y: f64,
    /// Original pre-refine rotation hint derived from feature alignment.
    pub seed_rotation_deg: f64,
    /// Final rotation actually handed back to the caller after optional local refine.
    pub rotation_seed_deg: f64,
    pub source: CandidateSeedSource,
    pub moving_feature_type: &'static str,
    pub target_feature_type: &'static str,
    pub alignment_kind: &'static str,
    pub source_score: f64,
    pub refine_iterations: usize,
    pub refine_success: bool,
    pub refine_rejection_reason: Option<String>,
}

impl CandidateSeed {
    pub fn pair_type(&self) -> String {
        format!(
            "{}->{}:{}@seed={:.2}@refined={:.2}@iters={}@success={}",
            self.moving_feature_type,
            self.target_feature_type,
            self.alignment_kind,
            self.seed_rotation_deg,
            self.rotation_seed_deg,
            self.refine_iterations,
            self.refine_success
        )
    }
}

#[derive(Debug, Clone)]
pub struct DebugPlacedNeighbour {
    pub part: Part,
    pub x: f64,
    pub y: f64,
    pub rotation_deg: f64,
}

#[derive(Debug, Clone, Copy)]
pub(crate) struct PlacedFeatureNeighbour<'a> {
    pub placement: &'a SparrowPlacement,
    pub instance: &'a SPInstance,
}

struct MovingFeatureSpec<'a> {
    part: &'a Part,
    allowed_rotations_deg: &'a [f64],
    continuous_rotation: bool,
    feature_base_shape: &'a CdeBaseShape,
    collision_base_shape: &'a CdeBaseShape,
    features: &'a ContourFeatureSet,
    /// SGH-Q54B: clearance offset (mm) applied to neighbour feature alignments so the two
    /// spacing-expanded contours just touch instead of overlapping. ≈ the technology spacing
    /// (both contours are half-spacing expanded). 0.0 reproduces the Q53 point-on-point seed.
    clearance: f64,
}

struct NeighbourFeatureSpec<'a> {
    placement_x: f64,
    placement_y: f64,
    rotation_deg: f64,
    features: &'a ContourFeatureSet,
    collision_base_shape: &'a CdeBaseShape,
}

#[derive(Debug, Clone, Copy)]
struct RotationFrame {
    bbox_min_x: f64,
    bbox_min_y: f64,
    bbox_max_x: f64,
    bbox_max_y: f64,
}

#[derive(Debug, Clone, Copy)]
struct RawSeed {
    anchor_x: f64,
    anchor_y: f64,
    rotation_seed_deg: f64,
    moving_feature_type: &'static str,
    target_feature_type: &'static str,
    alignment_kind: &'static str,
    source_score: f64,
}

#[derive(Debug, Clone)]
pub struct FeatureRefineDiagnostics {
    pub seed_rotation_deg: f64,
    pub refined_rotation_deg: f64,
    pub refine_iterations: usize,
    pub refine_success: bool,
    pub rejection_reason: Option<String>,
}

pub fn feature_candidate_generation_enabled() -> bool {
    std::env::var("VRS_FEATURE_CANDIDATES").ok().as_deref() == Some("1")
}

pub fn generate_feature_candidate_seeds_debug(
    moving_part: &Part,
    moving_rotation_deg: f64,
    sheet: &SheetShape,
    neighbours: &[DebugPlacedNeighbour],
    max_total: usize,
    clearance: f64,
) -> Result<Vec<CandidateSeed>, String> {
    let base = prepare_base_shape_native(moving_part).map_err(|e| e.to_string())?;
    let moving_features = ContourFeatureSet::extract(&base);
    let allowed_rotations = resolve_part_rotation_angles_with_context(
        moving_part,
        &RotationResolveContext::legacy_default(),
    );
    let moving = MovingFeatureSpec {
        part: moving_part,
        allowed_rotations_deg: &allowed_rotations,
        continuous_rotation: moving_part
            .rotation_policy
            .as_ref()
            .is_some_and(|p| matches!(p, RotationPolicyKind::Continuous)),
        feature_base_shape: &base,
        collision_base_shape: &base,
        features: &moving_features,
        clearance,
    };

    let mut neighbour_bases: Vec<CdeBaseShape> = Vec::with_capacity(neighbours.len());
    let mut neighbour_features: Vec<ContourFeatureSet> = Vec::with_capacity(neighbours.len());
    for n in neighbours {
        let base = prepare_base_shape_native(&n.part).map_err(|e| e.to_string())?;
        neighbour_features.push(ContourFeatureSet::extract(&base));
        neighbour_bases.push(base);
    }
    let neighbour_specs: Vec<NeighbourFeatureSpec<'_>> = neighbours
        .iter()
        .zip(neighbour_features.iter())
        .zip(neighbour_bases.iter())
        .map(|((n, features), base)| NeighbourFeatureSpec {
            placement_x: n.x,
            placement_y: n.y,
            rotation_deg: n.rotation_deg,
            features,
            collision_base_shape: base,
        })
        .collect();
    Ok(generate_feature_candidate_seeds_impl(
        &moving,
        moving_rotation_deg,
        sheet,
        &neighbour_specs,
        max_total,
    ))
}

/// SGH-Q54B: local-point bbox span `(width, height)` of a base shape.
fn bbox_span(shape: &CdeBaseShape) -> (f64, f64) {
    let (mut min_x, mut min_y, mut max_x, mut max_y) = (f64::MAX, f64::MAX, f64::MIN, f64::MIN);
    for p in &shape.local_pts {
        min_x = min_x.min(p.x);
        min_y = min_y.min(p.y);
        max_x = max_x.max(p.x);
        max_y = max_y.max(p.y);
    }
    if shape.local_pts.is_empty() {
        (0.0, 0.0)
    } else {
        (max_x - min_x, max_y - min_y)
    }
}

/// SGH-Q54B: clearance ≈ technology spacing, recovered from the half-spacing-expanded collision
/// shape vs the original base shape (their bbox-span difference). 0 when spacing is 0 (same shape).
fn clearance_from_instance(inst: &SPInstance) -> f64 {
    let (bw, bh) = bbox_span(&inst.base_shape);
    let (sw, sh) = bbox_span(&inst.spacing_collision_base_shape);
    ((sw - bw).max(sh - bh)).max(0.0)
}

pub(crate) fn generate_feature_candidate_seeds_for_sheet(
    moving: &SPInstance,
    moving_rotation_deg: f64,
    sheet: &SheetShape,
    neighbours: &[PlacedFeatureNeighbour<'_>],
    max_total: usize,
) -> Vec<CandidateSeed> {
    let moving_spec = MovingFeatureSpec {
        part: &moving.part,
        allowed_rotations_deg: &moving.allowed_rotations_deg,
        continuous_rotation: moving.continuous_rotation,
        feature_base_shape: &moving.base_shape,
        collision_base_shape: &moving.spacing_collision_base_shape,
        features: moving.contour_features(),
        clearance: clearance_from_instance(moving),
    };
    let neighbour_specs: Vec<NeighbourFeatureSpec<'_>> = neighbours
        .iter()
        .map(|n| NeighbourFeatureSpec {
            placement_x: n.placement.x,
            placement_y: n.placement.y,
            rotation_deg: n.placement.rotation_deg,
            features: n.instance.contour_features(),
            collision_base_shape: &n.instance.spacing_collision_base_shape,
        })
        .collect();
    generate_feature_candidate_seeds_impl(
        &moving_spec,
        moving_rotation_deg,
        sheet,
        &neighbour_specs,
        max_total,
    )
}

fn generate_feature_candidate_seeds_impl(
    moving: &MovingFeatureSpec<'_>,
    moving_rotation_deg: f64,
    sheet: &SheetShape,
    neighbours: &[NeighbourFeatureSpec<'_>],
    max_total: usize,
) -> Vec<CandidateSeed> {
    if max_total == 0 {
        return Vec::new();
    }
    let mut raw: Vec<RawSeed> = Vec::new();
    sheet_edge_candidates(moving, moving_rotation_deg, sheet, &mut raw);
    neighbour_feature_candidates(moving, moving_rotation_deg, sheet, neighbours, &mut raw);
    let seeds = finalize_seeds(raw, moving.feature_base_shape, sheet, max_total);
    refine_feature_candidates(moving, sheet, neighbours, seeds)
}

/// SGH-Q55A: sheet-aware rotation seeds for an edge-anchored placement. Align the part's dominant
/// edge to the sheet's **long** AND **short** edge directions, with **180° flips** — instead of a
/// single part-axis seed that ignores the sheet aspect. Continuous parts keep the raw (continuous)
/// seed so the downstream refine can find the precise angle (e.g. ~88.3°); discrete parts snap to
/// their allowed set via `resolve_seed_rotation`. Deduplicated, order-stable.
fn sheet_aware_anchor_rotations(
    moving: &MovingFeatureSpec<'_>,
    edge_angle_deg: f64,
    sheet: &SheetShape,
    moving_rotation_deg: f64,
) -> Vec<f64> {
    // Sheet long/short edge directions (deg): the long edge runs along the larger dimension.
    let (long_dir, short_dir) = if sheet.width >= sheet.height {
        (0.0, 90.0)
    } else {
        (90.0, 0.0)
    };
    let mut seeds: Vec<f64> = Vec::with_capacity(4);
    for &target in &[long_dir, short_dir] {
        for &flip in &[0.0, 180.0] {
            let raw = wrap_deg(target + flip - edge_angle_deg);
            let r = resolve_seed_rotation(moving, raw, moving_rotation_deg);
            if !seeds.iter().any(|&s| angular_distance_deg(s, r) < 1e-6) {
                seeds.push(r);
            }
        }
    }
    seeds
}

/// SGH-Q55A: push the four edge-anchored seeds (both sheet-parallel sides) for one rotation.
fn push_sheet_edge_anchors(
    feature_base_shape: &CdeBaseShape,
    edge: &DominantEdge,
    rot: f64,
    sheet: &SheetShape,
    alignment_score: f64,
    out: &mut Vec<RawSeed>,
) {
    let Some(frame) = rotation_frame(feature_base_shape, rot) else {
        return;
    };
    let moved_mid = rotate_point(edge.midpoint, rot);
    let world_edge_angle = wrap_deg(edge.angle_deg + rot);
    let closer_to_horizontal =
        angular_distance_deg(world_edge_angle, 0.0) <= angular_distance_deg(world_edge_angle, 90.0);
    let left_anchor = sheet.min_x - frame.bbox_min_x;
    let right_anchor = sheet.max_x - frame.bbox_max_x;
    let bottom_anchor = sheet.min_y - frame.bbox_min_y;
    let top_anchor = sheet.max_y - frame.bbox_max_y;
    if closer_to_horizontal {
        for &(anchor_x, kind) in &[
            (left_anchor, "sheet_edge_horizontal_left"),
            (right_anchor, "sheet_edge_horizontal_right"),
        ] {
            out.push(RawSeed {
                anchor_x,
                anchor_y: sheet.min_y - moved_mid.y,
                rotation_seed_deg: rot,
                moving_feature_type: "dominant_edge",
                target_feature_type: "sheet_edge",
                alignment_kind: kind,
                source_score: alignment_score + 0.20,
            });
            out.push(RawSeed {
                anchor_x,
                anchor_y: sheet.max_y - moved_mid.y,
                rotation_seed_deg: rot,
                moving_feature_type: "dominant_edge",
                target_feature_type: "sheet_edge",
                alignment_kind: kind,
                source_score: alignment_score + 0.18,
            });
        }
    } else {
        for &(anchor_y, kind) in &[
            (bottom_anchor, "sheet_edge_vertical_bottom"),
            (top_anchor, "sheet_edge_vertical_top"),
        ] {
            out.push(RawSeed {
                anchor_x: sheet.min_x - moved_mid.x,
                anchor_y,
                rotation_seed_deg: rot,
                moving_feature_type: "dominant_edge",
                target_feature_type: "sheet_edge",
                alignment_kind: kind,
                source_score: alignment_score + 0.20,
            });
            out.push(RawSeed {
                anchor_x: sheet.max_x - moved_mid.x,
                anchor_y,
                rotation_seed_deg: rot,
                moving_feature_type: "dominant_edge",
                target_feature_type: "sheet_edge",
                alignment_kind: kind,
                source_score: alignment_score + 0.18,
            });
        }
    }
}

fn sheet_edge_candidates(
    moving: &MovingFeatureSpec<'_>,
    moving_rotation_deg: f64,
    sheet: &SheetShape,
    out: &mut Vec<RawSeed>,
) {
    for align in &moving.features.sheet_edge_alignment_angles {
        let Some(edge) = moving
            .features
            .dominant_edges
            .iter()
            .find(|edge| edge.edge_index == align.source_edge_index)
        else {
            continue;
        };
        // SGH-Q55A: a ranked sheet-aware rotation set (long+short edge alignment + 180° flips),
        // not a single part-axis seed.
        for rot in sheet_aware_anchor_rotations(moving, edge.angle_deg, sheet, moving_rotation_deg) {
            push_sheet_edge_anchors(
                moving.feature_base_shape,
                edge,
                rot,
                sheet,
                align.alignment_score,
                out,
            );
        }
    }
}

fn neighbour_feature_candidates(
    moving: &MovingFeatureSpec<'_>,
    moving_rotation_deg: f64,
    sheet: &SheetShape,
    neighbours: &[NeighbourFeatureSpec<'_>],
    out: &mut Vec<RawSeed>,
) {
    let _ = sheet;
    let moving_vertex_stride = stride_for(moving.features.vertices.len(), 4);
    for n in neighbours {
        for m_edge in moving.features.dominant_edges.iter().take(4) {
            for n_edge in n.features.dominant_edges.iter().take(4) {
                let base_rot =
                    wrap_deg(world_angle(n_edge.angle_deg, n.rotation_deg) - m_edge.angle_deg);
                for raw_rot in [base_rot, wrap_deg(base_rot + 180.0)] {
                    let rot = resolve_seed_rotation(moving, raw_rot, moving_rotation_deg);
                    let moved_mid = rotate_point(m_edge.midpoint, rot);
                    let theta = world_angle(m_edge.angle_deg, rot).to_radians();
                    let normal = Point {
                        x: -theta.sin(),
                        y: theta.cos(),
                    };
                    let neigh_mid = world_point(
                        n_edge.midpoint,
                        n.placement_x,
                        n.placement_y,
                        n.rotation_deg,
                    );
                    let score = (m_edge.normalized_length * n_edge.normalized_length)
                        .clamp(0.0, 1.5)
                        + 0.35;
                    // SGH-Q54B: offset along the edge normal by the clearance (both spacing-expanded
                    // contours just touch) instead of the point-on-point Q53 seed.
                    let off = FEATURE_SEED_EPS + moving.clearance;
                    for side in [-1.0, 1.0] {
                        out.push(point_alignment_seed(
                            moved_mid,
                            Point {
                                x: neigh_mid.x + side * off * normal.x,
                                y: neigh_mid.y + side * off * normal.y,
                            },
                            rot,
                            "dominant_edge",
                            "dominant_edge",
                            "edge_midpoint_parallel",
                            score,
                        ));
                    }
                }
            }
        }

        for protrusion in moving.features.protrusion_candidates.iter().take(6) {
            for zone in n.features.concave_zones.iter().take(6) {
                let raw_rot = wrap_deg(
                    world_angle(zone.inward_angle_deg, n.rotation_deg) + 180.0
                        - protrusion.outward_angle_deg,
                );
                let rot = resolve_seed_rotation(moving, raw_rot, moving_rotation_deg);
                let target0 = world_point(zone.anchor, n.placement_x, n.placement_y, n.rotation_deg);
                // SGH-Q54B: pull the target OUT of the concavity mouth (opposite the inward
                // direction) by the clearance, so the protrusion seats with a gap rather than
                // point-on-point (the Q53 root cause of `seed_not_clear`).
                let inward = world_angle(zone.inward_angle_deg, n.rotation_deg).to_radians();
                let target = Point {
                    x: target0.x - moving.clearance * inward.cos(),
                    y: target0.y - moving.clearance * inward.sin(),
                };
                let moved_pt = rotate_point(protrusion.point, rot);
                out.push(point_alignment_seed(
                    moved_pt,
                    target,
                    rot,
                    "protrusion",
                    "concave_zone",
                    "protrusion_into_concavity",
                    protrusion.prominence_score + zone.depth_score + 0.30,
                ));
            }
        }

        // SGH-Q54B: pull point targets OUT of the neighbour (away from its geometric centroid, which
        // lies inside the part) by the clearance, so vertex/edge-projection seeds also seat with a
        // gap instead of point-on-point. Centroid (not the placement anchor, which may sit on the
        // contour) gives a robust outward direction.
        let (mut cx, mut cy, mut cnt) = (0.0_f64, 0.0_f64, 0.0_f64);
        for v in &n.features.vertices {
            let w = world_point(v.point, n.placement_x, n.placement_y, n.rotation_deg);
            cx += w.x;
            cy += w.y;
            cnt += 1.0;
        }
        let centroid = if cnt > 0.0 {
            Point { x: cx / cnt, y: cy / cnt }
        } else {
            Point { x: n.placement_x, y: n.placement_y }
        };
        let pull_out = |t: Point| -> Point {
            let dx = t.x - centroid.x;
            let dy = t.y - centroid.y;
            let len = (dx * dx + dy * dy).sqrt();
            if len > 1e-9 {
                Point {
                    x: t.x + moving.clearance * dx / len,
                    y: t.y + moving.clearance * dy / len,
                }
            } else {
                t
            }
        };
        let edge_midpoints: Vec<Point> = n
            .features
            .edges
            .iter()
            .step_by(stride_for(n.features.edges.len(), 6))
            .map(|edge| {
                pull_out(world_point(edge.midpoint, n.placement_x, n.placement_y, n.rotation_deg))
            })
            .collect();
        let vertices: Vec<Point> = n
            .features
            .vertices
            .iter()
            .step_by(stride_for(n.features.vertices.len(), 8))
            .map(|vertex| {
                pull_out(world_point(vertex.point, n.placement_x, n.placement_y, n.rotation_deg))
            })
            .collect();

        for extreme in &moving.features.extreme_points {
            let rot = resolve_seed_rotation(moving, moving_rotation_deg, moving_rotation_deg);
            let moved_pt = rotate_point(extreme.point, rot);
            for target in &vertices {
                out.push(point_alignment_seed(
                    moved_pt,
                    *target,
                    rot,
                    "extreme_point",
                    "vertex",
                    "point_to_vertex",
                    0.72,
                ));
            }
            for target in &edge_midpoints {
                out.push(point_alignment_seed(
                    moved_pt,
                    *target,
                    rot,
                    "extreme_point",
                    "edge_projection",
                    "point_to_edge_projection",
                    0.66,
                ));
            }
        }

        for vertex in moving
            .features
            .vertices
            .iter()
            .step_by(moving_vertex_stride)
        {
            let rot = resolve_seed_rotation(moving, moving_rotation_deg, moving_rotation_deg);
            let moved_pt = rotate_point(vertex.point, rot);
            for target in edge_midpoints.iter().take(4) {
                out.push(point_alignment_seed(
                    moved_pt,
                    *target,
                    rot,
                    "vertex",
                    "edge_projection",
                    "vertex_to_edge_projection",
                    0.58,
                ));
            }
        }
    }
}

fn finalize_seeds(
    mut raw: Vec<RawSeed>,
    feature_base_shape: &CdeBaseShape,
    sheet: &SheetShape,
    max_total: usize,
) -> Vec<CandidateSeed> {
    raw.sort_by(|a, b| {
        b.source_score
            .partial_cmp(&a.source_score)
            .unwrap_or(Ordering::Equal)
            .then_with(|| {
                a.rotation_seed_deg
                    .partial_cmp(&b.rotation_seed_deg)
                    .unwrap_or(Ordering::Equal)
            })
            .then_with(|| {
                a.anchor_x
                    .partial_cmp(&b.anchor_x)
                    .unwrap_or(Ordering::Equal)
            })
            .then_with(|| {
                a.anchor_y
                    .partial_cmp(&b.anchor_y)
                    .unwrap_or(Ordering::Equal)
            })
            .then_with(|| a.moving_feature_type.cmp(b.moving_feature_type))
            .then_with(|| a.target_feature_type.cmp(b.target_feature_type))
            .then_with(|| a.alignment_kind.cmp(b.alignment_kind))
    });

    let mut out: Vec<CandidateSeed> = Vec::new();
    let mut seen: std::collections::HashSet<(i64, i64, i64, &'static str, &'static str)> =
        std::collections::HashSet::new();
    for raw_seed in raw {
        let Some(frame) = rotation_frame(feature_base_shape, raw_seed.rotation_seed_deg) else {
            continue;
        };
        let rect_min_x = raw_seed.anchor_x + frame.bbox_min_x;
        let rect_min_y = raw_seed.anchor_y + frame.bbox_min_y;
        let rect_max_x = raw_seed.anchor_x + frame.bbox_max_x;
        let rect_max_y = raw_seed.anchor_y + frame.bbox_max_y;
        if rect_min_x < sheet.min_x - EPS
            || rect_min_y < sheet.min_y - EPS
            || rect_max_x > sheet.max_x + EPS
            || rect_max_y > sheet.max_y + EPS
        {
            continue;
        }
        let seed = CandidateSeed {
            x: rect_min_x,
            y: rect_min_y,
            seed_rotation_deg: normalize_angle(raw_seed.rotation_seed_deg),
            rotation_seed_deg: normalize_angle(raw_seed.rotation_seed_deg),
            source: CandidateSeedSource::ContourFeature,
            moving_feature_type: raw_seed.moving_feature_type,
            target_feature_type: raw_seed.target_feature_type,
            alignment_kind: raw_seed.alignment_kind,
            source_score: raw_seed.source_score,
            refine_iterations: 0,
            refine_success: false,
            refine_rejection_reason: Some("not_refined".to_string()),
        };
        let key = (
            round_key(seed.x),
            round_key(seed.y),
            round_key(seed.rotation_seed_deg),
            seed.moving_feature_type,
            seed.target_feature_type,
        );
        if seen.insert(key) {
            out.push(seed);
        }
        if out.len() >= max_total {
            break;
        }
    }
    out
}

fn refine_feature_candidates(
    moving: &MovingFeatureSpec<'_>,
    sheet: &SheetShape,
    neighbours: &[NeighbourFeatureSpec<'_>],
    seeds: Vec<CandidateSeed>,
) -> Vec<CandidateSeed> {
    let Some(sheet_shape) = prepare_shape_from_sheet(sheet).ok().map(Rc::new) else {
        return seeds
            .into_iter()
            .map(|seed| CandidateSeed {
                refine_rejection_reason: Some("sheet_shape_unavailable".to_string()),
                ..seed
            })
            .collect();
    };
    let neighbour_shapes: Vec<Rc<CdePreparedShape>> = neighbours
        .iter()
        .filter_map(|n| {
            transform_base_to_candidate(
                n.collision_base_shape,
                n.placement_x,
                n.placement_y,
                n.rotation_deg,
            )
            .map(Rc::new)
        })
        .collect();
    let session = CdeCandidateSession::build_with_policy(
        neighbour_shapes
            .iter()
            .enumerate()
            .map(|(idx, shape)| (idx, shape.clone()))
            .collect(),
        &sheet_shape,
        crate::optimizer::cde_adapter::CdeTouchingPolicy::SparrowStrict,
    );
    let Some(session) = session else {
        return seeds
            .into_iter()
            .map(|seed| CandidateSeed {
                refine_rejection_reason: Some("session_build_failed".to_string()),
                ..seed
            })
            .collect();
    };
    let neighbour_refs: Vec<&CdePreparedShape> =
        neighbour_shapes.iter().map(|s| s.as_ref()).collect();

    seeds
        .into_iter()
        .map(|seed| refine_one_feature_candidate(moving, sheet, &session, &neighbour_refs, seed))
        .collect()
}

fn refine_one_feature_candidate(
    moving: &MovingFeatureSpec<'_>,
    sheet: &SheetShape,
    session: &CdeCandidateSession,
    neighbour_refs: &[&CdePreparedShape],
    seed: CandidateSeed,
) -> CandidateSeed {
    let mut diag = SparrowDiagnostics::default();
    let mut evaluator = FeatureRefineEvaluator {
        sheet,
        session,
        base: moving.collision_base_shape,
        part_width: moving.part.width,
        part_height: moving.part.height,
        neighbours: neighbour_refs.to_vec(),
        weights: DensityWeights::default(),
        n_evals: 0,
    };
    let Some(init) =
        evaluator.evaluate_sample(seed.x, seed.y, seed.seed_rotation_deg, None, &mut diag)
    else {
        return CandidateSeed {
            refine_rejection_reason: Some("seed_not_clear".to_string()),
            ..seed
        };
    };
    let wiggle = moving.continuous_rotation;
    let mut rng = DeterministicRng::new(hash_seed(
        &moving.part.id,
        seed.x,
        seed.y,
        seed.seed_rotation_deg,
    ));
    let Some((refined, rounds)) = refine_feature_seed(
        init,
        &mut evaluator,
        moving.part.width.min(moving.part.height).max(1.0),
        &mut rng,
        &mut diag,
        wiggle,
        5.0,
    ) else {
        return CandidateSeed {
            refine_rejection_reason: Some("refine_failed".to_string()),
            ..seed
        };
    };
    CandidateSeed {
        x: refined.rect_min_x,
        y: refined.rect_min_y,
        rotation_seed_deg: finalize_rotation_for_policy(moving, refined.placement.rotation_deg),
        refine_iterations: rounds,
        refine_success: true,
        refine_rejection_reason: None,
        ..seed
    }
}

pub fn refine_feature_candidate_debug(
    moving_part: &Part,
    seed: &CandidateSeed,
    sheet: &SheetShape,
    neighbours: &[DebugPlacedNeighbour],
) -> Result<FeatureRefineDiagnostics, String> {
    let refined = generate_feature_candidate_seeds_debug(
        moving_part,
        seed.seed_rotation_deg,
        sheet,
        neighbours,
        64,
        0.0,
    )?
    .into_iter()
    .find(|cand| {
        cand.moving_feature_type == seed.moving_feature_type
            && cand.target_feature_type == seed.target_feature_type
            && cand.alignment_kind == seed.alignment_kind
    })
    .unwrap_or_else(|| seed.clone());
    Ok(FeatureRefineDiagnostics {
        seed_rotation_deg: refined.seed_rotation_deg,
        refined_rotation_deg: refined.rotation_seed_deg,
        refine_iterations: refined.refine_iterations,
        refine_success: refined.refine_success,
        rejection_reason: refined.refine_rejection_reason,
    })
}

fn point_alignment_seed(
    moved_local_point: Point,
    target_world_point: Point,
    rotation_seed_deg: f64,
    moving_feature_type: &'static str,
    target_feature_type: &'static str,
    alignment_kind: &'static str,
    source_score: f64,
) -> RawSeed {
    RawSeed {
        anchor_x: target_world_point.x - moved_local_point.x,
        anchor_y: target_world_point.y - moved_local_point.y,
        rotation_seed_deg,
        moving_feature_type,
        target_feature_type,
        alignment_kind,
        source_score,
    }
}

fn rotation_frame(base_shape: &CdeBaseShape, rotation_deg: f64) -> Option<RotationFrame> {
    let prepared = transform_base_to_candidate(base_shape, 0.0, 0.0, rotation_deg)?;
    Some(RotationFrame {
        bbox_min_x: prepared.min_x,
        bbox_min_y: prepared.min_y,
        bbox_max_x: prepared.max_x,
        bbox_max_y: prepared.max_y,
    })
}

fn resolve_seed_rotation(
    moving: &MovingFeatureSpec<'_>,
    raw_seed_deg: f64,
    fallback_deg: f64,
) -> f64 {
    let desired = if raw_seed_deg.is_finite() {
        normalize_angle(raw_seed_deg)
    } else {
        normalize_angle(fallback_deg)
    };
    if moving.continuous_rotation || moving.allowed_rotations_deg.is_empty() {
        return desired;
    }
    moving
        .allowed_rotations_deg
        .iter()
        .copied()
        .min_by(|a, b| {
            angular_distance_deg(*a, desired)
                .partial_cmp(&angular_distance_deg(*b, desired))
                .unwrap_or(Ordering::Equal)
        })
        .unwrap_or(desired)
}

fn finalize_rotation_for_policy(moving: &MovingFeatureSpec<'_>, rotation_deg: f64) -> f64 {
    if moving.continuous_rotation || moving.allowed_rotations_deg.is_empty() {
        return normalize_angle(rotation_deg);
    }
    let desired = normalize_angle(rotation_deg);
    moving
        .allowed_rotations_deg
        .iter()
        .copied()
        .min_by(|a, b| {
            angular_distance_deg(*a, desired)
                .partial_cmp(&angular_distance_deg(*b, desired))
                .unwrap_or(Ordering::Equal)
        })
        .unwrap_or(desired)
}

fn rotate_point(p: Point, rotation_deg: f64) -> Point {
    let theta = rotation_deg.to_radians();
    let cos_t = theta.cos();
    let sin_t = theta.sin();
    Point {
        x: p.x * cos_t - p.y * sin_t,
        y: p.x * sin_t + p.y * cos_t,
    }
}

fn world_point(local: Point, anchor_x: f64, anchor_y: f64, rotation_deg: f64) -> Point {
    let p = rotate_point(local, rotation_deg);
    Point {
        x: anchor_x + p.x,
        y: anchor_y + p.y,
    }
}

fn world_angle(local_angle_deg: f64, rotation_deg: f64) -> f64 {
    wrap_deg(local_angle_deg + rotation_deg)
}

fn wrap_deg(mut deg: f64) -> f64 {
    while deg <= -180.0 {
        deg += 360.0;
    }
    while deg > 180.0 {
        deg -= 360.0;
    }
    deg
}

fn angular_distance_deg(a: f64, b: f64) -> f64 {
    let diff = wrap_deg(a - b).abs();
    diff.min(360.0 - diff)
}

fn stride_for(len: usize, target_samples: usize) -> usize {
    (len / target_samples.max(1)).max(1)
}

fn round_key(v: f64) -> i64 {
    (v * KEY_SCALE).round() as i64
}

fn hash_seed(part_id: &str, x: f64, y: f64, rot: f64) -> u64 {
    let mut h = 0xcbf2_9ce4_8422_2325u64;
    for &b in part_id.as_bytes() {
        h ^= b as u64;
        h = h.wrapping_mul(0x0000_0001_0000_01b3);
    }
    h ^= round_key(x) as u64;
    h = h.wrapping_mul(0x0000_0001_0000_01b3);
    h ^= round_key(y) as u64;
    h = h.wrapping_mul(0x0000_0001_0000_01b3);
    h ^= round_key(rot) as u64;
    h
}

#[cfg(test)]
mod tests {
    use super::*;

    fn part(id: &str, w: f64, h: f64, pts: serde_json::Value) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: 1,
            allowed_rotations_deg: vec![0, 90, 180, 270],
            rotation_policy: None,
            holes_points: None,
            prepared_holes_points: None,
            outer_points: Some(pts),
            prepared_outer_points: None,
        }
    }

    fn sheet() -> SheetShape {
        crate::sheet::stock_to_shape(&crate::sheet::Stock {
            id: "S".to_string(),
            quantity: 1,
            width: Some(400.0),
            height: Some(300.0),
            outer_points: None,
            holes_points: None,
            cost_per_use: None,
        })
        .expect("rect sheet")
    }

    #[test]
    fn sheet_edge_candidates_use_contour_feature_metadata() {
        let moving = part(
            "bar",
            120.0,
            40.0,
            serde_json::json!([[0.0, 0.0], [120.0, 0.0], [120.0, 40.0], [0.0, 40.0]]),
        );
        let seeds =
            generate_feature_candidate_seeds_debug(&moving, 0.0, &sheet(), &[], 16, 0.0).unwrap();
        assert!(
            seeds.iter().any(|seed| {
                seed.source == CandidateSeedSource::ContourFeature
                    && seed.moving_feature_type == "dominant_edge"
                    && seed.target_feature_type == "sheet_edge"
            }),
            "dominant-edge to sheet-edge seed expected"
        );
        assert!(
            seeds
                .iter()
                .all(|seed| seed.moving_feature_type != "bbox_corner"),
            "feature path must not use moving bbox corners"
        );
    }

    #[test]
    fn discrete_parts_snap_to_allowed_rotations() {
        let moving = part(
            "bar",
            120.0,
            40.0,
            serde_json::json!([[0.0, 0.0], [120.0, 0.0], [120.0, 40.0], [0.0, 40.0]]),
        );
        let neighbour = DebugPlacedNeighbour {
            part: part(
                "wall",
                40.0,
                140.0,
                serde_json::json!([[0.0, 0.0], [40.0, 0.0], [40.0, 140.0], [0.0, 140.0]]),
            ),
            x: 200.0,
            y: 20.0,
            rotation_deg: 0.0,
        };
        let seeds =
            generate_feature_candidate_seeds_debug(&moving, 17.0, &sheet(), &[neighbour], 24, 0.0)
                .unwrap();
        assert!(!seeds.is_empty());
        assert!(seeds.iter().all(|seed| {
            [0.0, 90.0, 180.0, 270.0]
                .iter()
                .any(|allowed| angular_distance_deg(*allowed, seed.rotation_seed_deg) < 1e-6)
        }));
    }
}
