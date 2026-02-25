use std::cmp::Ordering;
use std::collections::{hash_map::DefaultHasher, HashSet};
use std::fmt::Write as _;
use std::hash::Hasher;

use i_overlay::{
    core::{
        fill_rule::FillRule,
        overlay::IntOverlayOptions,
        overlay::Overlay,
        overlay_rule::OverlayRule,
        solver::{Precision, Solver, Strategy},
    },
    i_float::int::point::IntPoint,
    i_shape::int::shape::{IntContour, IntShape},
};

use crate::geometry::types::{
    cross_product_i128, is_ccw, is_convex, signed_area2_i128, Point64, Polygon64,
};
use crate::nfp::boundary_clean::{clean_polygon_boundary, ring_has_self_intersection};

use super::{convex::compute_convex_nfp, NfpError};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConcaveNfpMode {
    StableDefault,
    ExactOrbit,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ConcaveNfpOptions {
    pub mode: ConcaveNfpMode,
    pub max_steps: usize,
    pub enable_fallback: bool,
}

impl Default for ConcaveNfpOptions {
    fn default() -> Self {
        Self {
            mode: ConcaveNfpMode::StableDefault,
            max_steps: 1_024,
            enable_fallback: true,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct OrbitTraceDirection {
    pub dx: i64,
    pub dy: i64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OrbitNextEventTraceStep {
    pub step_index: usize,
    pub touching_group_signature: String,
    pub chosen_direction: OrbitTraceDirection,
    pub next_event_kind: String,
    pub next_event_t_num: i128,
    pub next_event_t_den: i128,
    pub tie_break_reason: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OrbitTraceOutcomeKind {
    ExactClosed,
    FallbackStable,
    FailedNoFallback,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OrbitNextEventTrace {
    pub outcome: OrbitTraceOutcomeKind,
    pub steps: Vec<OrbitNextEventTraceStep>,
}

#[derive(Debug, Default)]
struct OrbitTraceCollector {
    max_steps: usize,
    steps: Vec<OrbitNextEventTraceStep>,
}

impl OrbitTraceCollector {
    fn new(max_steps: usize) -> Self {
        Self {
            max_steps,
            steps: Vec::new(),
        }
    }

    fn push(&mut self, step: OrbitNextEventTraceStep) {
        if self.steps.len() < self.max_steps {
            self.steps.push(step);
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct TouchingContact {
    edge_a: usize,
    edge_b: usize,
    point: Point64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
enum EventKind {
    VertexBToEdgeA,
    VertexAToEdgeB,
}

impl EventKind {
    fn as_trace_kind(self) -> &'static str {
        match self {
            Self::VertexBToEdgeA => "vertex_b_to_edge_a",
            Self::VertexAToEdgeB => "vertex_a_to_edge_b",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct Fraction {
    num: i128,
    den: i128,
}

impl Fraction {
    fn positive(num: i128, den: i128) -> Option<Self> {
        if den == 0 {
            return None;
        }

        let (mut num, mut den) = (num, den);
        if den < 0 {
            num = -num;
            den = -den;
        }
        if num <= 0 {
            return None;
        }

        let gcd = gcd_i128(num.abs(), den.abs()).max(1);
        Some(Self {
            num: num / gcd,
            den: den / gcd,
        })
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct EventCandidate {
    t: Fraction,
    event_kind: EventKind,
    vertex_idx: usize,
    edge_idx: usize,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct CandidateDirection {
    vector: Point64,
    source_kind: u8,
    source_edge_a: usize,
    source_edge_b: usize,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct NextOrbitStep {
    next_translation: Point64,
    direction: CandidateDirection,
    event: EventCandidate,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct OrbitTelemetry {
    steps_count: usize,
    events_count: usize,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum OrbitFailureReason {
    LoopDetected,
    DeadEnd,
    MaxStepsReached,
}

impl OrbitFailureReason {
    fn as_error(self) -> NfpError {
        match self {
            Self::LoopDetected => NfpError::OrbitLoopDetected,
            Self::DeadEnd => NfpError::OrbitDeadEnd,
            Self::MaxStepsReached => NfpError::OrbitMaxStepsReached,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
enum OrbitOutcome {
    ExactClosed {
        polygon: Polygon64,
        telemetry: OrbitTelemetry,
    },
    FallbackStable {
        polygon: Polygon64,
        telemetry: OrbitTelemetry,
        reason: OrbitFailureReason,
    },
    FailedNoFallback {
        telemetry: OrbitTelemetry,
        reason: OrbitFailureReason,
    },
}

pub fn compute_concave_nfp(
    a: &Polygon64,
    b: &Polygon64,
    options: ConcaveNfpOptions,
) -> Result<Polygon64, NfpError> {
    match options.mode {
        ConcaveNfpMode::StableDefault => compute_stable_concave_nfp(a, b),
        ConcaveNfpMode::ExactOrbit => compute_orbit_exact_nfp(a, b, options),
    }
}

pub fn compute_concave_nfp_default(a: &Polygon64, b: &Polygon64) -> Result<Polygon64, NfpError> {
    compute_concave_nfp(a, b, ConcaveNfpOptions::default())
}

pub fn collect_orbit_next_event_trace(
    a: &Polygon64,
    b: &Polygon64,
    options: ConcaveNfpOptions,
    max_trace_steps: usize,
) -> Result<OrbitNextEventTrace, NfpError> {
    let mut trace = OrbitTraceCollector::new(max_trace_steps);
    let trace_options = ConcaveNfpOptions {
        mode: ConcaveNfpMode::ExactOrbit,
        ..options
    };
    let outcome = compute_orbit_exact_outcome_with_trace(a, b, trace_options, Some(&mut trace))?;
    Ok(OrbitNextEventTrace {
        outcome: orbit_outcome_kind(&outcome),
        steps: trace.steps,
    })
}

fn orbit_outcome_kind(outcome: &OrbitOutcome) -> OrbitTraceOutcomeKind {
    match outcome {
        OrbitOutcome::ExactClosed { .. } => OrbitTraceOutcomeKind::ExactClosed,
        OrbitOutcome::FallbackStable { .. } => OrbitTraceOutcomeKind::FallbackStable,
        OrbitOutcome::FailedNoFallback { .. } => OrbitTraceOutcomeKind::FailedNoFallback,
    }
}

fn compute_stable_concave_nfp(a: &Polygon64, b: &Polygon64) -> Result<Polygon64, NfpError> {
    if a.outer.len() < 3 || b.outer.len() < 3 {
        return Err(NfpError::EmptyPolygon);
    }
    if !a.holes.is_empty() || !b.holes.is_empty() {
        return Err(NfpError::DecompositionFailed);
    }

    let convex_parts_a = decompose_to_convex_parts(&a.outer)?;
    let convex_parts_b = decompose_to_convex_parts(&b.outer)?;
    if convex_parts_a.is_empty() || convex_parts_b.is_empty() {
        return Err(NfpError::DecompositionFailed);
    }

    let mut partial_nfpc: Vec<Polygon64> = Vec::new();
    for part_a in &convex_parts_a {
        for part_b in &convex_parts_b {
            let nfp = compute_convex_nfp(part_a, part_b)?;
            partial_nfpc.push(nfp);
        }
    }

    let unioned = union_nfp_fragments(&partial_nfpc)?;
    clean_polygon_boundary(&unioned)
}

fn compute_orbit_exact_nfp(
    a: &Polygon64,
    b: &Polygon64,
    options: ConcaveNfpOptions,
) -> Result<Polygon64, NfpError> {
    let outcome = compute_orbit_exact_outcome(a, b, options)?;
    match outcome {
        OrbitOutcome::ExactClosed { polygon, .. } => Ok(polygon),
        OrbitOutcome::FallbackStable { polygon, .. } => Ok(polygon),
        OrbitOutcome::FailedNoFallback { reason, .. } => Err(reason.as_error()),
    }
}

fn compute_orbit_exact_outcome(
    a: &Polygon64,
    b: &Polygon64,
    options: ConcaveNfpOptions,
) -> Result<OrbitOutcome, NfpError> {
    compute_orbit_exact_outcome_with_trace(a, b, options, None)
}

fn compute_orbit_exact_outcome_with_trace(
    a: &Polygon64,
    b: &Polygon64,
    options: ConcaveNfpOptions,
    mut trace: Option<&mut OrbitTraceCollector>,
) -> Result<OrbitOutcome, NfpError> {
    let ring_a = normalize_simple_ring(&a.outer)?;
    let ring_b = normalize_simple_ring(&b.outer)?;
    if ring_a.len() < 3 || ring_b.len() < 3 {
        return Err(NfpError::EmptyPolygon);
    }

    let Some(start) = initial_orbit_anchor(&ring_a, &ring_b) else {
        return orbit_failure_outcome(
            a,
            b,
            options,
            OrbitTelemetry {
                steps_count: 0,
                events_count: 0,
            },
            OrbitFailureReason::DeadEnd,
        );
    };
    let mut orbit: Vec<Point64> = Vec::new();
    let mut current = start;
    orbit.push(start);

    let mut visited: HashSet<u64> = HashSet::new();
    let max_steps = options.max_steps.max(1);
    let mut telemetry = OrbitTelemetry {
        steps_count: 0,
        events_count: 0,
    };

    for step_idx in 0..max_steps {
        telemetry.steps_count = telemetry.steps_count.saturating_add(1);
        let touching_group = build_touching_group(&ring_a, &ring_b, current);
        let touching_signature = touching_group_signature(&touching_group);
        let signature = hash_state(current, &touching_group);
        if !visited.insert(signature) {
            return orbit_failure_outcome(
                a,
                b,
                options,
                telemetry,
                OrbitFailureReason::LoopDetected,
            );
        }

        let previous = if orbit.len() >= 2 {
            Some(orbit[orbit.len() - 2])
        } else {
            None
        };
        let Some(next_step) =
            choose_next_orbit_step(&ring_a, &ring_b, current, &touching_group, previous)
        else {
            return orbit_failure_outcome(a, b, options, telemetry, OrbitFailureReason::DeadEnd);
        };

        if let Some(collector) = trace.as_deref_mut() {
            collector.push(OrbitNextEventTraceStep {
                step_index: step_idx,
                touching_group_signature: touching_signature,
                chosen_direction: OrbitTraceDirection {
                    dx: next_step.direction.vector.x,
                    dy: next_step.direction.vector.y,
                },
                next_event_kind: next_step.event.event_kind.as_trace_kind().to_string(),
                next_event_t_num: next_step.event.t.num,
                next_event_t_den: next_step.event.t.den,
                tie_break_reason: build_tie_break_reason(next_step.direction, next_step.event),
            });
        }

        current = next_step.next_translation;
        telemetry.events_count = telemetry.events_count.saturating_add(1);
        orbit.push(current);
        if orbit.len() > 3 && current == start {
            let orbit_poly = Polygon64 {
                outer: orbit,
                holes: Vec::new(),
            };
            let cleaned = clean_polygon_boundary(&orbit_poly)?;
            return Ok(OrbitOutcome::ExactClosed {
                polygon: cleaned,
                telemetry,
            });
        }
    }

    orbit_failure_outcome(
        a,
        b,
        options,
        telemetry,
        OrbitFailureReason::MaxStepsReached,
    )
}

fn initial_orbit_anchor(a: &[Point64], b: &[Point64]) -> Option<Point64> {
    if a.is_empty() || b.is_empty() {
        return None;
    }
    let min_ax = a.iter().map(|p| p.x).min()?;
    let min_ay = a.iter().map(|p| p.y).min()?;
    let max_bx = b.iter().map(|p| p.x).max()?;
    let min_by = b.iter().map(|p| p.y).min()?;
    Some(Point64 {
        x: min_ax.checked_sub(max_bx)?,
        y: min_ay.checked_sub(min_by)?,
    })
}

fn orbit_failure_outcome(
    a: &Polygon64,
    b: &Polygon64,
    options: ConcaveNfpOptions,
    telemetry: OrbitTelemetry,
    reason: OrbitFailureReason,
) -> Result<OrbitOutcome, NfpError> {
    if options.enable_fallback {
        let stable = compute_stable_concave_nfp(a, b)?;
        Ok(OrbitOutcome::FallbackStable {
            polygon: stable,
            telemetry,
            reason,
        })
    } else {
        Ok(OrbitOutcome::FailedNoFallback { telemetry, reason })
    }
}

fn choose_next_orbit_step(
    a: &[Point64],
    b: &[Point64],
    translation: Point64,
    touching_group: &[TouchingContact],
    previous: Option<Point64>,
) -> Option<NextOrbitStep> {
    let directions = build_candidate_slide_vectors(a, b, touching_group);
    if directions.is_empty() {
        return None;
    }

    for direction in directions {
        let Some(next_event) = next_event_translation(a, b, translation, direction.vector) else {
            continue;
        };
        if next_event.next_translation == translation {
            continue;
        }
        if previous.is_some() && previous == Some(next_event.next_translation) {
            continue;
        }
        return Some(NextOrbitStep {
            next_translation: next_event.next_translation,
            direction,
            event: next_event.event,
        });
    }

    None
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct NextEventTranslation {
    event: EventCandidate,
    next_translation: Point64,
}

fn next_event_translation(
    a: &[Point64],
    b: &[Point64],
    translation: Point64,
    slide: Point64,
) -> Option<NextEventTranslation> {
    if slide.x == 0 && slide.y == 0 {
        return None;
    }

    let mut best: Option<NextEventTranslation> = None;

    for vertex_idx in 0..b.len() {
        let moving_vertex = translated_point(b[vertex_idx], translation);
        for edge_idx in 0..a.len() {
            let a0 = a[edge_idx];
            let a1 = a[(edge_idx + 1) % a.len()];
            let Some(event) = vertex_edge_event(
                moving_vertex,
                a0,
                a1,
                slide,
                EventKind::VertexBToEdgeA,
                vertex_idx,
                edge_idx,
            ) else {
                continue;
            };
            let Some(next_translation) = apply_translation_fraction(translation, slide, event.t)
            else {
                continue;
            };
            if !event_contact_holds(a, b, next_translation, event) {
                continue;
            }
            if polygons_strict_overlap(a, b, next_translation) {
                continue;
            }

            let translated = NextEventTranslation {
                event,
                next_translation,
            };
            if is_better_event(&translated, &best) {
                best = Some(translated);
            }
        }
    }

    let opposite_slide = Point64 {
        x: -slide.x,
        y: -slide.y,
    };
    for vertex_idx in 0..a.len() {
        let static_vertex = a[vertex_idx];
        for edge_idx in 0..b.len() {
            let b0 = translated_point(b[edge_idx], translation);
            let b1 = translated_point(b[(edge_idx + 1) % b.len()], translation);
            let Some(event) = vertex_edge_event(
                static_vertex,
                b0,
                b1,
                opposite_slide,
                EventKind::VertexAToEdgeB,
                vertex_idx,
                edge_idx,
            ) else {
                continue;
            };
            let Some(next_translation) = apply_translation_fraction(translation, slide, event.t)
            else {
                continue;
            };
            if !event_contact_holds(a, b, next_translation, event) {
                continue;
            }
            if polygons_strict_overlap(a, b, next_translation) {
                continue;
            }

            let translated = NextEventTranslation {
                event,
                next_translation,
            };
            if is_better_event(&translated, &best) {
                best = Some(translated);
            }
        }
    }

    best
}

fn vertex_edge_event(
    moving_vertex: Point64,
    edge_start: Point64,
    edge_end: Point64,
    moving_vector: Point64,
    event_kind: EventKind,
    vertex_idx: usize,
    edge_idx: usize,
) -> Option<EventCandidate> {
    let edge_dx = edge_end.x.checked_sub(edge_start.x)?;
    let edge_dy = edge_end.y.checked_sub(edge_start.y)?;
    if edge_dx == 0 && edge_dy == 0 {
        return None;
    }

    let rel_x = moving_vertex.x.checked_sub(edge_start.x)?;
    let rel_y = moving_vertex.y.checked_sub(edge_start.y)?;
    let signed_dist = cross_product_i128(edge_dx, edge_dy, rel_x, rel_y);
    let dist_delta = cross_product_i128(edge_dx, edge_dy, moving_vector.x, moving_vector.y);
    let t = Fraction::positive(-signed_dist, dist_delta)?;

    if !moving_vertex_projects_on_edge(
        moving_vertex,
        edge_start,
        edge_dx,
        edge_dy,
        moving_vector,
        t,
    ) {
        return None;
    }

    Some(EventCandidate {
        t,
        event_kind,
        vertex_idx,
        edge_idx,
    })
}

fn moving_vertex_projects_on_edge(
    moving_vertex: Point64,
    edge_start: Point64,
    edge_dx: i64,
    edge_dy: i64,
    moving_vector: Point64,
    t: Fraction,
) -> bool {
    let rel_x = match moving_vertex.x.checked_sub(edge_start.x) {
        Some(v) => v,
        None => return false,
    };
    let rel_y = match moving_vertex.y.checked_sub(edge_start.y) {
        Some(v) => v,
        None => return false,
    };

    let dot0 = dot_product_i128(rel_x, rel_y, edge_dx, edge_dy);
    let dot_delta = dot_product_i128(moving_vector.x, moving_vector.y, edge_dx, edge_dy);
    let edge_len2 = dot_product_i128(edge_dx, edge_dy, edge_dx, edge_dy);
    if edge_len2 <= 0 {
        return false;
    }

    let lhs = match scaled_fraction_sum(dot0, t.den, dot_delta, t.num) {
        Some(v) => v,
        None => return false,
    };
    let upper = match edge_len2.checked_mul(t.den) {
        Some(v) => v,
        None => return false,
    };
    lhs >= 0 && lhs <= upper
}

fn scaled_fraction_sum(a: i128, a_scale: i128, b: i128, b_scale: i128) -> Option<i128> {
    let a_scaled = a.checked_mul(a_scale)?;
    let b_scaled = b.checked_mul(b_scale)?;
    a_scaled.checked_add(b_scaled)
}

fn apply_translation_fraction(
    translation: Point64,
    slide: Point64,
    t: Fraction,
) -> Option<Point64> {
    let dx_num = (slide.x as i128).checked_mul(t.num)?;
    let dy_num = (slide.y as i128).checked_mul(t.num)?;
    if dx_num % t.den != 0 || dy_num % t.den != 0 {
        return None;
    }

    let dx = i64::try_from(dx_num / t.den).ok()?;
    let dy = i64::try_from(dy_num / t.den).ok()?;

    Some(Point64 {
        x: translation.x.checked_add(dx)?,
        y: translation.y.checked_add(dy)?,
    })
}

fn event_contact_holds(
    a: &[Point64],
    b: &[Point64],
    translation: Point64,
    event: EventCandidate,
) -> bool {
    match event.event_kind {
        EventKind::VertexBToEdgeA => {
            if a.is_empty() || b.is_empty() {
                return false;
            }
            let vertex = translated_point(b[event.vertex_idx % b.len()], translation);
            let a0 = a[event.edge_idx % a.len()];
            let a1 = a[(event.edge_idx + 1) % a.len()];
            point_on_segment_inclusive(a0, a1, vertex)
        }
        EventKind::VertexAToEdgeB => {
            if a.is_empty() || b.is_empty() {
                return false;
            }
            let vertex = a[event.vertex_idx % a.len()];
            let b0 = translated_point(b[event.edge_idx % b.len()], translation);
            let b1 = translated_point(b[(event.edge_idx + 1) % b.len()], translation);
            point_on_segment_inclusive(b0, b1, vertex)
        }
    }
}

fn is_better_event(
    candidate: &NextEventTranslation,
    current: &Option<NextEventTranslation>,
) -> bool {
    let Some(current) = current else {
        return true;
    };

    event_candidate_cmp(candidate.event, current.event)
        .then(
            candidate
                .next_translation
                .x
                .cmp(&current.next_translation.x),
        )
        .then(
            candidate
                .next_translation
                .y
                .cmp(&current.next_translation.y),
        )
        == Ordering::Less
}

fn event_candidate_cmp(lhs: EventCandidate, rhs: EventCandidate) -> Ordering {
    fraction_cmp(lhs.t, rhs.t)
        .then(lhs.event_kind.cmp(&rhs.event_kind))
        .then(lhs.vertex_idx.cmp(&rhs.vertex_idx))
        .then(lhs.edge_idx.cmp(&rhs.edge_idx))
}

fn fraction_cmp(lhs: Fraction, rhs: Fraction) -> Ordering {
    match (lhs.num.checked_mul(rhs.den), rhs.num.checked_mul(lhs.den)) {
        (Some(l), Some(r)) => l.cmp(&r),
        _ => compare_positive_ratios(lhs.num, lhs.den, rhs.num, rhs.den),
    }
}

fn compare_positive_ratios(
    mut a_num: i128,
    mut a_den: i128,
    mut b_num: i128,
    mut b_den: i128,
) -> Ordering {
    let mut flipped = false;
    loop {
        let q_a = a_num / a_den;
        let q_b = b_num / b_den;
        if q_a != q_b {
            let ord = q_a.cmp(&q_b);
            return if flipped { ord.reverse() } else { ord };
        }

        let r_a = a_num % a_den;
        let r_b = b_num % b_den;
        if r_a == 0 || r_b == 0 {
            let ord = match (r_a == 0, r_b == 0) {
                (true, true) => Ordering::Equal,
                (true, false) => Ordering::Less,
                (false, true) => Ordering::Greater,
                (false, false) => Ordering::Equal,
            };
            return if flipped { ord.reverse() } else { ord };
        }

        a_num = a_den;
        a_den = r_a;
        b_num = b_den;
        b_den = r_b;
        flipped = !flipped;
    }
}

fn decompose_to_convex_parts(ring: &[Point64]) -> Result<Vec<Polygon64>, NfpError> {
    let ring = normalize_simple_ring(ring)?;
    if ring.len() < 3 {
        return Err(NfpError::DecompositionFailed);
    }

    if is_convex(&ring) {
        return Ok(vec![Polygon64 {
            outer: ring,
            holes: Vec::new(),
        }]);
    }

    let triangles = ear_clip_triangulate(&ring)?;
    if triangles.is_empty() {
        return Err(NfpError::DecompositionFailed);
    }

    let mut out = Vec::with_capacity(triangles.len());
    for tri in triangles {
        let mut outer = tri.to_vec();
        if !is_ccw(&outer) {
            outer.reverse();
        }
        out.push(Polygon64 {
            outer,
            holes: Vec::new(),
        });
    }

    Ok(out)
}

fn normalize_simple_ring(points: &[Point64]) -> Result<Vec<Point64>, NfpError> {
    let mut ring: Vec<Point64> = Vec::with_capacity(points.len());
    for &p in points {
        if ring.last().copied() != Some(p) {
            ring.push(p);
        }
    }
    if ring.len() > 1 && ring.first() == ring.last() {
        ring.pop();
    }
    if ring.len() < 3 {
        return Err(NfpError::EmptyPolygon);
    }

    if !is_ccw(&ring) {
        ring.reverse();
    }
    if ring_has_self_intersection(&ring) {
        return Err(NfpError::DecompositionFailed);
    }
    Ok(ring)
}

fn ear_clip_triangulate(ring: &[Point64]) -> Result<Vec<[Point64; 3]>, NfpError> {
    let n = ring.len();
    if n < 3 {
        return Err(NfpError::DecompositionFailed);
    }

    let mut remaining: Vec<usize> = (0..n).collect();
    let mut triangles = Vec::with_capacity(n.saturating_sub(2));
    let mut guard = 0usize;
    let max_guard = n * n * 4;

    while remaining.len() > 3 {
        if guard > max_guard {
            return Err(NfpError::DecompositionFailed);
        }
        guard += 1;

        let mut ear_found = false;
        let m = remaining.len();
        for i in 0..m {
            let prev_idx = remaining[(i + m - 1) % m];
            let curr_idx = remaining[i];
            let next_idx = remaining[(i + 1) % m];

            let prev = ring[prev_idx];
            let curr = ring[curr_idx];
            let next = ring[next_idx];

            let turn = cross_product_i128(
                curr.x - prev.x,
                curr.y - prev.y,
                next.x - curr.x,
                next.y - curr.y,
            );
            if turn <= 0 {
                continue;
            }

            let mut contains_other = false;
            for &other_idx in &remaining {
                if other_idx == prev_idx || other_idx == curr_idx || other_idx == next_idx {
                    continue;
                }
                if point_in_or_on_triangle(ring[other_idx], prev, curr, next) {
                    contains_other = true;
                    break;
                }
            }
            if contains_other {
                continue;
            }

            triangles.push([prev, curr, next]);
            remaining.remove(i);
            ear_found = true;
            break;
        }

        if !ear_found {
            return Err(NfpError::DecompositionFailed);
        }
    }

    if remaining.len() == 3 {
        triangles.push([ring[remaining[0]], ring[remaining[1]], ring[remaining[2]]]);
    }
    Ok(triangles)
}

fn point_in_or_on_triangle(p: Point64, a: Point64, b: Point64, c: Point64) -> bool {
    let o1 = orient(a, b, p);
    let o2 = orient(b, c, p);
    let o3 = orient(c, a, p);

    let has_pos = o1 > 0 || o2 > 0 || o3 > 0;
    let has_neg = o1 < 0 || o2 < 0 || o3 < 0;
    !(has_pos && has_neg)
}

fn orient(a: Point64, b: Point64, c: Point64) -> i8 {
    let v = cross_product_i128(b.x - a.x, b.y - a.y, c.x - a.x, c.y - a.y);
    if v > 0 {
        1
    } else if v < 0 {
        -1
    } else {
        0
    }
}

fn union_nfp_fragments(fragments: &[Polygon64]) -> Result<Polygon64, NfpError> {
    if fragments.is_empty() {
        return Err(NfpError::DecompositionFailed);
    }

    let bounds = OverlayBounds::from_fragments(fragments).ok_or(NfpError::DecompositionFailed)?;
    let subject_shapes: Vec<IntShape> = fragments
        .iter()
        .map(|poly| encode_overlay_contour(&poly.outer, bounds).map(|contour| vec![contour]))
        .collect::<Result<Vec<_>, _>>()?;

    let empty_shapes: [IntShape; 0] = [];
    let mut overlay = Overlay::with_shapes_options(
        &subject_shapes,
        &empty_shapes,
        IntOverlayOptions::keep_all_points(),
        Solver::with_strategy_and_precision(Strategy::List, Precision::ABSOLUTE),
    );
    let unioned = overlay.overlay(OverlayRule::Union, FillRule::NonZero);

    let mut best: Option<(i128, Vec<Point64>, Polygon64)> = None;
    for shape in unioned {
        if shape.is_empty() {
            continue;
        }

        let outer = restore_axis_notches(&decode_overlay_contour(&shape[0], bounds)?, fragments);
        if outer.len() < 3 {
            continue;
        }
        let candidate = Polygon64 {
            outer: outer.clone(),
            holes: Vec::new(),
        };
        let area = signed_area2_i128(&outer).abs();
        let key = canonical_key(&outer);
        match &best {
            None => best = Some((area, key, candidate)),
            Some((best_area, best_key, _)) => {
                if area > *best_area || (area == *best_area && lex_less(&key, best_key)) {
                    best = Some((area, key, candidate));
                }
            }
        }
    }

    best.map(|(_, _, poly)| poly)
        .ok_or(NfpError::DecompositionFailed)
}

#[derive(Debug, Clone, Copy)]
struct OverlayBounds {
    min_x: i64,
    min_y: i64,
    shift: u32,
}

impl OverlayBounds {
    fn from_fragments(fragments: &[Polygon64]) -> Option<Self> {
        let mut min_x = i64::MAX;
        let mut min_y = i64::MAX;
        let mut max_x = i64::MIN;
        let mut max_y = i64::MIN;

        for fragment in fragments {
            for point in &fragment.outer {
                min_x = min_x.min(point.x);
                min_y = min_y.min(point.y);
                max_x = max_x.max(point.x);
                max_y = max_y.max(point.y);
            }
        }

        if min_x == i64::MAX || min_y == i64::MAX {
            return None;
        }

        let span_x = max_x.checked_sub(min_x)?;
        let span_y = max_y.checked_sub(min_y)?;
        let mut max_span = span_x.max(span_y);
        let mut shift = 0_u32;

        while max_span > i32::MAX as i64 {
            max_span = (max_span + 1) >> 1;
            shift = shift.checked_add(1)?;
        }

        Some(Self {
            min_x,
            min_y,
            shift,
        })
    }

    fn encode_x(self, x: i64) -> Option<i32> {
        self.encode_coord(x, self.min_x)
    }

    fn encode_y(self, y: i64) -> Option<i32> {
        self.encode_coord(y, self.min_y)
    }

    fn decode_x(self, x: i32) -> Option<i64> {
        self.decode_coord(x, self.min_x)
    }

    fn decode_y(self, y: i32) -> Option<i64> {
        self.decode_coord(y, self.min_y)
    }

    fn encode_coord(self, value: i64, min: i64) -> Option<i32> {
        let translated = value.checked_sub(min)?;
        let scaled = if self.shift == 0 {
            translated
        } else {
            translated >> self.shift
        };
        i32::try_from(scaled).ok()
    }

    fn decode_coord(self, value: i32, min: i64) -> Option<i64> {
        let scaled = (value as i64).checked_shl(self.shift)?;
        min.checked_add(scaled)
    }
}

fn encode_overlay_contour(
    points: &[Point64],
    bounds: OverlayBounds,
) -> Result<IntContour, NfpError> {
    let mut contour = Vec::with_capacity(points.len());
    for point in points {
        let x = bounds
            .encode_x(point.x)
            .ok_or(NfpError::DecompositionFailed)?;
        let y = bounds
            .encode_y(point.y)
            .ok_or(NfpError::DecompositionFailed)?;
        contour.push(IntPoint::new(x, y));
    }
    Ok(contour)
}

fn decode_overlay_contour(
    contour: &IntContour,
    bounds: OverlayBounds,
) -> Result<Vec<Point64>, NfpError> {
    let mut outer = Vec::with_capacity(contour.len());
    for point in contour {
        let x = bounds
            .decode_x(point.x)
            .ok_or(NfpError::DecompositionFailed)?;
        let y = bounds
            .decode_y(point.y)
            .ok_or(NfpError::DecompositionFailed)?;
        outer.push(Point64 { x, y });
    }
    Ok(outer)
}

fn restore_axis_notches(ring: &[Point64], fragments: &[Polygon64]) -> Vec<Point64> {
    let n = ring.len();
    if n < 3 {
        return ring.to_vec();
    }

    let mut out = Vec::with_capacity(n * 2);
    for i in 0..n {
        let prev = ring[(i + n - 1) % n];
        let curr = ring[i];
        let next = ring[(i + 1) % n];
        let next_next = ring[(i + 2) % n];
        out.push(curr);

        let dx = next.x - curr.x;
        let dy = next.y - curr.y;
        if dx == 0 || dy == 0 {
            continue;
        }
        if dx.abs() > 1 && dy.abs() > 1 {
            continue;
        }

        let candidates = [
            Point64 {
                x: curr.x,
                y: next.y,
            },
            Point64 {
                x: next.x,
                y: curr.y,
            },
        ];

        let mut chosen: Option<Point64> = None;
        for candidate in candidates {
            if candidate == curr || candidate == next || candidate == prev || candidate == next_next
            {
                continue;
            }
            if !point_in_any_fragment(candidate, fragments) {
                continue;
            }

            chosen = match chosen {
                None => Some(candidate),
                Some(current) => {
                    let current_key = (current.x, current.y);
                    let candidate_key = (candidate.x, candidate.y);
                    if candidate_key < current_key {
                        Some(candidate)
                    } else {
                        Some(current)
                    }
                }
            };
        }

        if let Some(candidate) = chosen {
            out.push(candidate);
        }
    }

    out
}

fn point_in_any_fragment(point: Point64, fragments: &[Polygon64]) -> bool {
    fragments
        .iter()
        .any(|fragment| point_in_or_on_ring(point, &fragment.outer))
}

fn point_in_or_on_ring(point: Point64, ring: &[Point64]) -> bool {
    let n = ring.len();
    if n < 3 {
        return false;
    }

    for i in 0..n {
        let a = ring[i];
        let b = ring[(i + 1) % n];
        if point_on_segment_inclusive(a, b, point) {
            return true;
        }
    }

    let mut winding = 0_i32;
    for i in 0..n {
        let a = ring[i];
        let b = ring[(i + 1) % n];

        if a.y <= point.y {
            if b.y > point.y {
                let cross = cross_product_i128(b.x - a.x, b.y - a.y, point.x - a.x, point.y - a.y);
                if cross > 0 {
                    winding += 1;
                }
            }
        } else if b.y <= point.y {
            let cross = cross_product_i128(b.x - a.x, b.y - a.y, point.x - a.x, point.y - a.y);
            if cross < 0 {
                winding -= 1;
            }
        }
    }

    winding != 0
}

fn canonical_key(points: &[Point64]) -> Vec<Point64> {
    let mut ring = points.to_vec();
    if ring.len() > 1 && ring.first() == ring.last() {
        ring.pop();
    }
    if signed_area2_i128(&ring) < 0 {
        ring.reverse();
    }
    if ring.is_empty() {
        return ring;
    }

    let start = ring
        .iter()
        .enumerate()
        .min_by_key(|(_, p)| (p.x, p.y))
        .map(|(idx, _)| idx)
        .unwrap_or(0);
    ring.rotate_left(start);
    ring
}

fn lex_less(lhs: &[Point64], rhs: &[Point64]) -> bool {
    let n = lhs.len().min(rhs.len());
    for i in 0..n {
        let c = lhs[i].x.cmp(&rhs[i].x).then(lhs[i].y.cmp(&rhs[i].y));
        if c != Ordering::Equal {
            return c == Ordering::Less;
        }
    }
    lhs.len() < rhs.len()
}

fn build_touching_group(
    a: &[Point64],
    b: &[Point64],
    translation: Point64,
) -> Vec<TouchingContact> {
    let mut contacts = Vec::new();

    for edge_a in 0..a.len() {
        let a0 = a[edge_a];
        let a1 = a[(edge_a + 1) % a.len()];
        for edge_b in 0..b.len() {
            let b0 = translated_point(b[edge_b], translation);
            let b1 = translated_point(b[(edge_b + 1) % b.len()], translation);
            if segments_intersect_or_touch(a0, a1, b0, b1) {
                let point = min_lex_point([a0, a1, b0, b1]);
                contacts.push(TouchingContact {
                    edge_a,
                    edge_b,
                    point,
                });
            }
        }
    }

    contacts.sort_by(|lhs, rhs| {
        lhs.edge_a
            .cmp(&rhs.edge_a)
            .then(lhs.edge_b.cmp(&rhs.edge_b))
            .then(lhs.point.x.cmp(&rhs.point.x))
            .then(lhs.point.y.cmp(&rhs.point.y))
    });
    contacts.dedup();
    if contacts.len() <= 1 {
        return contacts;
    }

    let mut components: Vec<Vec<TouchingContact>> = Vec::new();
    let mut seen = vec![false; contacts.len()];
    for idx in 0..contacts.len() {
        if seen[idx] {
            continue;
        }
        let mut stack = vec![idx];
        let mut component = Vec::new();
        seen[idx] = true;

        while let Some(node) = stack.pop() {
            let current = contacts[node];
            component.push(current);
            for next_idx in 0..contacts.len() {
                if seen[next_idx] {
                    continue;
                }
                if touching_contacts_connected(current, contacts[next_idx]) {
                    seen[next_idx] = true;
                    stack.push(next_idx);
                }
            }
        }
        component.sort_by(touching_contact_cmp);
        components.push(component);
    }

    components.sort_by(|lhs, rhs| {
        rhs.len()
            .cmp(&lhs.len())
            .then_with(|| touching_component_key(lhs).cmp(&touching_component_key(rhs)))
    });
    components.into_iter().next().unwrap_or_default()
}

fn touching_contacts_connected(lhs: TouchingContact, rhs: TouchingContact) -> bool {
    lhs.edge_a == rhs.edge_a || lhs.edge_b == rhs.edge_b || lhs.point == rhs.point
}

fn touching_component_key(component: &[TouchingContact]) -> (usize, usize, i64, i64) {
    component
        .iter()
        .map(|c| (c.edge_a, c.edge_b, c.point.x, c.point.y))
        .next()
        .unwrap_or((usize::MAX, usize::MAX, i64::MAX, i64::MAX))
}

fn touching_contact_cmp(lhs: &TouchingContact, rhs: &TouchingContact) -> Ordering {
    lhs.edge_a
        .cmp(&rhs.edge_a)
        .then(lhs.edge_b.cmp(&rhs.edge_b))
        .then(lhs.point.x.cmp(&rhs.point.x))
        .then(lhs.point.y.cmp(&rhs.point.y))
}

fn translated_point(p: Point64, translation: Point64) -> Point64 {
    Point64 {
        x: p.x.saturating_add(translation.x),
        y: p.y.saturating_add(translation.y),
    }
}

fn build_candidate_slide_vectors(
    a: &[Point64],
    b: &[Point64],
    touching_group: &[TouchingContact],
) -> Vec<CandidateDirection> {
    let mut vectors: Vec<CandidateDirection> = Vec::new();

    for contact in touching_group {
        let edge_a = edge_vector(a, contact.edge_a);
        let edge_b = edge_vector(b, contact.edge_b);

        push_candidate_direction(&mut vectors, edge_a, 0, contact.edge_a, contact.edge_b);
        push_candidate_direction(
            &mut vectors,
            Point64 {
                x: -edge_a.x,
                y: -edge_a.y,
            },
            0,
            contact.edge_a,
            contact.edge_b,
        );
        push_candidate_direction(
            &mut vectors,
            Point64 {
                x: -edge_b.x,
                y: -edge_b.y,
            },
            1,
            contact.edge_a,
            contact.edge_b,
        );
        push_candidate_direction(&mut vectors, edge_b, 1, contact.edge_a, contact.edge_b);
    }

    if vectors.is_empty() {
        for edge_idx in 0..a.len().min(8) {
            push_candidate_direction(&mut vectors, edge_vector(a, edge_idx), 2, edge_idx, 0);
            push_candidate_direction(
                &mut vectors,
                Point64 {
                    x: -edge_vector(a, edge_idx).x,
                    y: -edge_vector(a, edge_idx).y,
                },
                2,
                edge_idx,
                0,
            );
        }
        for edge_idx in 0..b.len().min(8) {
            let edge = edge_vector(b, edge_idx);
            push_candidate_direction(
                &mut vectors,
                Point64 {
                    x: -edge.x,
                    y: -edge.y,
                },
                3,
                0,
                edge_idx,
            );
            push_candidate_direction(&mut vectors, edge, 3, 0, edge_idx);
        }
    }

    vectors.sort_by(candidate_direction_cmp);
    vectors.dedup_by(|lhs, rhs| lhs.vector == rhs.vector);
    vectors
}

fn push_candidate_direction(
    out: &mut Vec<CandidateDirection>,
    raw: Point64,
    source_kind: u8,
    source_edge_a: usize,
    source_edge_b: usize,
) {
    let Some(vector) = normalize_vector(raw) else {
        return;
    };
    out.push(CandidateDirection {
        vector,
        source_kind,
        source_edge_a,
        source_edge_b,
    });
}

fn edge_vector(ring: &[Point64], edge_idx: usize) -> Point64 {
    let a = ring[edge_idx];
    let b = ring[(edge_idx + 1) % ring.len()];
    Point64 {
        x: b.x - a.x,
        y: b.y - a.y,
    }
}

fn normalize_vector(v: Point64) -> Option<Point64> {
    if v.x == 0 && v.y == 0 {
        return None;
    }
    let g = gcd_i64(v.x.abs(), v.y.abs()).max(1);
    Some(Point64 {
        x: v.x / g,
        y: v.y / g,
    })
}

fn candidate_direction_cmp(lhs: &CandidateDirection, rhs: &CandidateDirection) -> Ordering {
    let lhs_quad = vector_quadrant(lhs.vector);
    let rhs_quad = vector_quadrant(rhs.vector);
    if lhs_quad != rhs_quad {
        return lhs_quad.cmp(&rhs_quad);
    }

    let cross = cross_product_i128(lhs.vector.x, lhs.vector.y, rhs.vector.x, rhs.vector.y);
    if cross > 0 {
        return Ordering::Less;
    } else if cross < 0 {
        return Ordering::Greater;
    }

    lhs.vector
        .x
        .cmp(&rhs.vector.x)
        .then(lhs.vector.y.cmp(&rhs.vector.y))
        .then(lhs.source_kind.cmp(&rhs.source_kind))
        .then(lhs.source_edge_a.cmp(&rhs.source_edge_a))
        .then(lhs.source_edge_b.cmp(&rhs.source_edge_b))
}

fn vector_quadrant(v: Point64) -> u8 {
    match (v.x >= 0, v.y >= 0) {
        (true, true) => 0,
        (false, true) => 1,
        (false, false) => 2,
        (true, false) => 3,
    }
}

fn gcd_i64(mut a: i64, mut b: i64) -> i64 {
    while b != 0 {
        let r = a % b;
        a = b;
        b = r;
    }
    a.abs()
}

fn gcd_i128(mut a: i128, mut b: i128) -> i128 {
    while b != 0 {
        let r = a % b;
        a = b;
        b = r;
    }
    a.abs()
}

fn hash_state(translation: Point64, touching_group: &[TouchingContact]) -> u64 {
    let mut hasher = DefaultHasher::new();
    hasher.write_i64(translation.x);
    hasher.write_i64(translation.y);
    for contact in touching_group {
        hasher.write_usize(contact.edge_a);
        hasher.write_usize(contact.edge_b);
        hasher.write_i64(contact.point.x);
        hasher.write_i64(contact.point.y);
    }
    hasher.finish()
}

fn touching_group_signature(touching_group: &[TouchingContact]) -> String {
    if touching_group.is_empty() {
        return "none".to_string();
    }

    let mut out = String::new();
    for (idx, contact) in touching_group.iter().enumerate() {
        if idx > 0 {
            out.push('|');
        }
        let _ = write!(
            out,
            "a{}:b{}@{},{}",
            contact.edge_a, contact.edge_b, contact.point.x, contact.point.y
        );
    }
    out
}

fn build_tie_break_reason(direction: CandidateDirection, event: EventCandidate) -> String {
    format!(
        "dir[q{}|{},{}|src{}|a{}|b{}];event[{}|v{}|e{}]",
        vector_quadrant(direction.vector),
        direction.vector.x,
        direction.vector.y,
        direction.source_kind,
        direction.source_edge_a,
        direction.source_edge_b,
        event.event_kind.as_trace_kind(),
        event.vertex_idx,
        event.edge_idx
    )
}

fn min_lex_point(points: [Point64; 4]) -> Point64 {
    points
        .into_iter()
        .min_by_key(|p| (p.x, p.y))
        .unwrap_or(Point64 { x: 0, y: 0 })
}

fn point_on_segment_inclusive(a: Point64, b: Point64, p: Point64) -> bool {
    let cross = cross_product_i128(b.x - a.x, b.y - a.y, p.x - a.x, p.y - a.y);
    if cross != 0 {
        return false;
    }

    let min_x = a.x.min(b.x);
    let max_x = a.x.max(b.x);
    let min_y = a.y.min(b.y);
    let max_y = a.y.max(b.y);
    p.x >= min_x && p.x <= max_x && p.y >= min_y && p.y <= max_y
}

fn segments_intersect_or_touch(a0: Point64, a1: Point64, b0: Point64, b1: Point64) -> bool {
    let o1 = orient(a0, a1, b0);
    let o2 = orient(a0, a1, b1);
    let o3 = orient(b0, b1, a0);
    let o4 = orient(b0, b1, a1);

    if o1 == 0 && point_on_segment_inclusive(a0, a1, b0) {
        return true;
    }
    if o2 == 0 && point_on_segment_inclusive(a0, a1, b1) {
        return true;
    }
    if o3 == 0 && point_on_segment_inclusive(b0, b1, a0) {
        return true;
    }
    if o4 == 0 && point_on_segment_inclusive(b0, b1, a1) {
        return true;
    }
    o1 != o2 && o3 != o4
}

fn segments_proper_intersect(a0: Point64, a1: Point64, b0: Point64, b1: Point64) -> bool {
    let o1 = orient(a0, a1, b0);
    let o2 = orient(a0, a1, b1);
    let o3 = orient(b0, b1, a0);
    let o4 = orient(b0, b1, a1);
    o1 != 0 && o2 != 0 && o3 != 0 && o4 != 0 && o1 != o2 && o3 != o4
}

fn polygons_strict_overlap(a: &[Point64], b: &[Point64], translation: Point64) -> bool {
    if a.len() < 3 || b.len() < 3 {
        return false;
    }
    let translated_b: Vec<Point64> = b
        .iter()
        .map(|&point| translated_point(point, translation))
        .collect();

    for edge_a in 0..a.len() {
        let a0 = a[edge_a];
        let a1 = a[(edge_a + 1) % a.len()];
        for edge_b in 0..translated_b.len() {
            let b0 = translated_b[edge_b];
            let b1 = translated_b[(edge_b + 1) % translated_b.len()];
            if segments_proper_intersect(a0, a1, b0, b1) {
                return true;
            }
        }
    }

    if a.iter()
        .any(|&point| point_in_ring_strict(point, &translated_b))
    {
        return true;
    }
    translated_b
        .iter()
        .any(|&point| point_in_ring_strict(point, a))
}

fn point_in_ring_strict(point: Point64, ring: &[Point64]) -> bool {
    if ring.len() < 3 {
        return false;
    }

    for idx in 0..ring.len() {
        let start = ring[idx];
        let end = ring[(idx + 1) % ring.len()];
        if point_on_segment_inclusive(start, end, point) {
            return false;
        }
    }

    let mut winding = 0_i32;
    for idx in 0..ring.len() {
        let start = ring[idx];
        let end = ring[(idx + 1) % ring.len()];

        if start.y <= point.y {
            if end.y > point.y {
                let cross = cross_product_i128(
                    end.x - start.x,
                    end.y - start.y,
                    point.x - start.x,
                    point.y - start.y,
                );
                if cross > 0 {
                    winding += 1;
                }
            }
        } else if end.y <= point.y {
            let cross = cross_product_i128(
                end.x - start.x,
                end.y - start.y,
                point.x - start.x,
                point.y - start.y,
            );
            if cross < 0 {
                winding -= 1;
            }
        }
    }

    winding != 0
}

fn dot_product_i128(dx1: i64, dy1: i64, dx2: i64, dy2: i64) -> i128 {
    (dx1 as i128) * (dx2 as i128) + (dy1 as i128) * (dy2 as i128)
}

#[cfg(test)]
mod tests {
    use crate::geometry::types::Point64;

    use super::{
        compute_concave_nfp, compute_concave_nfp_default, compute_orbit_exact_outcome,
        decompose_to_convex_parts, ConcaveNfpMode, ConcaveNfpOptions, OrbitFailureReason,
        OrbitOutcome,
    };
    use crate::geometry::types::Polygon64;
    use crate::nfp::boundary_clean::ring_has_self_intersection;
    use crate::nfp::NfpError;

    fn poly(points: &[[i64; 2]]) -> Polygon64 {
        Polygon64 {
            outer: points
                .iter()
                .map(|p| Point64 { x: p[0], y: p[1] })
                .collect(),
            holes: Vec::new(),
        }
    }

    #[test]
    fn decomposition_splits_l_shape_into_triangles() {
        let l_shape = vec![
            Point64 { x: 0, y: 0 },
            Point64 { x: 4, y: 0 },
            Point64 { x: 4, y: 1 },
            Point64 { x: 1, y: 1 },
            Point64 { x: 1, y: 4 },
            Point64 { x: 0, y: 4 },
        ];
        let parts = decompose_to_convex_parts(&l_shape).expect("decomposition should succeed");
        assert!(
            parts.len() >= 2,
            "concave ring should be split to multiple parts"
        );
    }

    #[test]
    fn stable_concave_nfp_is_deterministic_and_simple() {
        let a = poly(&[[0, 0], [4, 0], [4, 1], [1, 1], [1, 4], [0, 4]]);
        let b = poly(&[[0, 0], [2, 0], [2, 3], [1, 3], [1, 1], [0, 1]]);

        let nfp_1 = compute_concave_nfp_default(&a, &b).expect("stable concave nfp");
        let nfp_2 = compute_concave_nfp_default(&a, &b).expect("stable concave nfp");
        assert_eq!(nfp_1.outer, nfp_2.outer);
        assert!(!ring_has_self_intersection(&nfp_1.outer));
    }

    #[test]
    fn exact_mode_remains_deterministic_under_loop_guard() {
        let a = poly(&[[0, 0], [4, 0], [4, 1], [1, 1], [1, 4], [0, 4]]);
        let b = poly(&[[0, 0], [2, 0], [2, 3], [1, 3], [1, 1], [0, 1]]);

        let exact_1 = compute_concave_nfp(
            &a,
            &b,
            ConcaveNfpOptions {
                mode: ConcaveNfpMode::ExactOrbit,
                max_steps: 1,
                enable_fallback: true,
            },
        )
        .expect("exact mode should produce a valid loop-guarded output");
        let exact_2 = compute_concave_nfp(
            &a,
            &b,
            ConcaveNfpOptions {
                mode: ConcaveNfpMode::ExactOrbit,
                max_steps: 1,
                enable_fallback: true,
            },
        )
        .expect("exact mode should stay deterministic under loop-guard");

        assert_eq!(exact_1.outer, exact_2.outer);
        assert!(!ring_has_self_intersection(&exact_1.outer));
    }

    #[test]
    fn exact_mode_no_fallback_returns_explicit_error() {
        let a = poly(&[[0, 0], [4, 0], [4, 1], [1, 1], [1, 4], [0, 4]]);
        let b = poly(&[[0, 0], [2, 0], [2, 3], [1, 3], [1, 1], [0, 1]]);

        let err = compute_concave_nfp(
            &a,
            &b,
            ConcaveNfpOptions {
                mode: ConcaveNfpMode::ExactOrbit,
                max_steps: 1,
                enable_fallback: false,
            },
        )
        .expect_err("no-fallback exact mode must not silently return stable seed");

        assert!(
            matches!(
                err,
                NfpError::OrbitLoopDetected
                    | NfpError::OrbitDeadEnd
                    | NfpError::OrbitMaxStepsReached
                    | NfpError::OrbitNotClosed
            ),
            "exact mode should fail with explicit orbit error"
        );
    }

    #[test]
    fn exact_mode_reports_explicit_fallback_outcome_when_enabled() {
        let a = poly(&[[0, 0], [4, 0], [4, 1], [1, 1], [1, 4], [0, 4]]);
        let b = poly(&[[0, 0], [2, 0], [2, 3], [1, 3], [1, 1], [0, 1]]);

        let stable = compute_concave_nfp_default(&a, &b).expect("stable path");
        let outcome = compute_orbit_exact_outcome(
            &a,
            &b,
            ConcaveNfpOptions {
                mode: ConcaveNfpMode::ExactOrbit,
                max_steps: 1,
                enable_fallback: true,
            },
        )
        .expect("outcome computation must succeed");

        match outcome {
            OrbitOutcome::FallbackStable {
                polygon,
                telemetry,
                reason,
            } => {
                assert_eq!(polygon.outer, stable.outer);
                assert!(telemetry.steps_count >= 1);
                assert!(
                    matches!(
                        reason,
                        OrbitFailureReason::LoopDetected
                            | OrbitFailureReason::DeadEnd
                            | OrbitFailureReason::MaxStepsReached
                    ),
                    "fallback reason must be explicit"
                );
            }
            OrbitOutcome::ExactClosed { .. } => {
                panic!("max_steps=1 fixture should not close exact orbit")
            }
            OrbitOutcome::FailedNoFallback { .. } => {
                panic!("enable_fallback=true must not produce FailedNoFallback outcome")
            }
        }
    }
}
