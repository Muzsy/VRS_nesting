//! SGH-Q21R1: Central backend-aware collision severity / evaluate_transform layer.
//!
//! Sparrow-aligned oracle severity engine:
//!   - active backend (CDE / JaguaPolygonExact) is collision/boundary source-of-truth;
//!   - severity = backend-confirmed translation distance required to resolve the
//!     collision via multi-direction adaptive probe (bracket + binary refinement);
//!   - bbox proxy severity is only used when the Bbox backend is selected OR oracle
//!     probe is explicitly disabled — every such use is counted in stats;
//!   - all backend queries (including probe sub-queries) are accounted for;
//!   - Unsupported queries return `cfg.hard_unsupported_loss`, never `f64::MAX`.

use crate::geometry::Rect;
use crate::io::{CollisionBackendKind, Placement};
use crate::item::Part;
use crate::sheet::SheetShape;
use super::boundary::rect_within_boundary;
use super::candidates::PlacedBbox;
use super::collision_backend::{
    CdeCollisionBackend, CollisionBackend, CollisionDecision, JaguaPolygonExactBackend,
};
use super::initializer::bbox_from_placement;
use super::loss_model::LossModelKind;
use super::working::WorkingLayout;

pub const HARD_UNSUPPORTED_LOSS: f64 = 1_000_000.0;

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

/// Configuration for backend-aware collision severity engine.
///
/// Defaults are chosen to be safe on industrial sheets up to 1500×3000 mm:
/// the initial probe step is bounded by `probe_max_initial_step_mm` (10 mm),
/// independent of sheet size, so small overlaps get a meaningful binary-refined
/// resolution distance instead of a coarse 167 mm sentinel.
#[derive(Debug, Clone)]
pub struct CollisionSeverityConfig {
    /// Enable backend-oracle severity for JaguaPolygonExact and CDE backends.
    /// When false, the bbox proxy severity path is used (counted as bbox_proxy_severity_uses).
    pub enabled_for_exact_backends: bool,
    /// Enable oracle-probe severity estimation for confirmed collisions.
    /// When false, bbox proxy severity is used for confirmed collisions.
    pub probe_enabled: bool,
    /// Multiplier applied to sheet diagonal to derive a candidate initial step.
    pub probe_initial_step_factor: f64,
    /// Absolute cap (mm) on the initial probe step — protects industrial-size
    /// sheets from a 167 mm initial step on 1500×3000 boards.
    pub probe_max_initial_step_mm: f64,
    /// Minimum probe step (mm). Steps below this are not tried.
    pub probe_min_step: f64,
    /// Growth factor between bracketing probe steps (>= 1.0).
    pub probe_bracket_growth: f64,
    /// Maximum bracketing steps per direction before giving up.
    pub probe_max_steps: usize,
    /// Number of binary refinement steps once a clear bracket is found.
    pub probe_binary_refine_steps: usize,
    /// Binary refinement converges once `(first_clear - last_collide) < tolerance`.
    pub probe_tolerance_mm: f64,
    /// Include diagonal directions in the probe set.
    pub probe_use_diagonal_directions: bool,
    /// Include the candidate→sheet-center direction in boundary probes.
    pub probe_use_center_direction: bool,
    /// Include the away-from-other-part-center direction in pair probes.
    pub probe_use_pair_center_direction: bool,
    /// Loss returned to callers for an Unsupported backend query.
    pub hard_unsupported_loss: f64,
}

impl Default for CollisionSeverityConfig {
    fn default() -> Self {
        Self {
            enabled_for_exact_backends: true,
            probe_enabled: true,
            probe_initial_step_factor: 0.05,
            probe_max_initial_step_mm: 10.0,
            probe_min_step: 0.05,
            probe_bracket_growth: 2.0,
            probe_max_steps: 10,
            probe_binary_refine_steps: 8,
            probe_tolerance_mm: 0.05,
            probe_use_diagonal_directions: true,
            probe_use_center_direction: true,
            probe_use_pair_center_direction: true,
            hard_unsupported_loss: HARD_UNSUPPORTED_LOSS,
        }
    }
}

impl CollisionSeverityConfig {
    /// Effective initial probe step capped by `probe_max_initial_step_mm`
    /// and floored by `probe_min_step`.
    pub fn effective_initial_step(&self, sheet_diag: f64) -> f64 {
        let scaled = self.probe_initial_step_factor * sheet_diag;
        let capped = scaled.min(self.probe_max_initial_step_mm);
        capped.max(self.probe_min_step)
    }
}

// ---------------------------------------------------------------------------
// Stats
// ---------------------------------------------------------------------------

/// Counters that describe what the severity engine actually did this run.
///
/// Semantics:
/// - `pair_queries`, `boundary_queries` — backend queries issued to *decide*
///   collision existence (one per pair or per boundary check); does NOT include
///   probe sub-queries (those live in `probe_pair_queries` / `probe_boundary_queries`).
/// - `probe_queries` = total probe sub-queries = `probe_pair_queries` + `probe_boundary_queries`
///   (kept for backward compatibility with Q21 diagnostics).
/// - `backend_confirmed_*` are tallied on the decisive query, not on probe sub-queries.
/// - `bbox_proxy_severity_uses` increments only when a confirmed collision falls back
///   to bbox proxy severity (probe disabled or Bbox backend).
/// - `probe_resolved` / `probe_unresolved` / `probe_unsupported` — direction outcomes.
#[derive(Debug, Clone, Default)]
pub struct CollisionSeverityStats {
    pub pair_queries: usize,
    pub boundary_queries: usize,
    pub probe_queries: usize,
    pub probe_pair_queries: usize,
    pub probe_boundary_queries: usize,
    pub backend_confirmed_collisions: usize,
    pub backend_confirmed_no_collisions: usize,
    pub unsupported_queries: usize,
    pub bbox_proxy_severity_uses: usize,
    pub probe_resolved: usize,
    pub probe_unresolved: usize,
    pub probe_unsupported: usize,
    /// Sum of recorded resolution distances (mm). Used to derive avg.
    pub resolution_sum_mm: f64,
    /// Number of resolution distances summed into `resolution_sum_mm`.
    pub resolutions_recorded: usize,
    /// Minimum recorded resolution distance (mm). `f64::MAX` sentinel = none.
    pub min_resolution_mm: f64,
    /// Maximum recorded resolution distance (mm). 0.0 sentinel = none.
    pub max_resolution_mm: f64,
}

impl CollisionSeverityStats {
    pub fn record_resolution(&mut self, distance_mm: f64) {
        self.resolution_sum_mm += distance_mm;
        self.resolutions_recorded += 1;
        if self.min_resolution_mm == 0.0 || distance_mm < self.min_resolution_mm {
            // 0.0 → uninitialized sentinel from Default (handled in accumulator/output)
            self.min_resolution_mm = if self.min_resolution_mm == 0.0 {
                distance_mm
            } else {
                self.min_resolution_mm.min(distance_mm)
            };
        }
        if distance_mm > self.max_resolution_mm {
            self.max_resolution_mm = distance_mm;
        }
    }

    pub fn accumulate(&mut self, other: &Self) {
        self.pair_queries += other.pair_queries;
        self.boundary_queries += other.boundary_queries;
        self.probe_queries += other.probe_queries;
        self.probe_pair_queries += other.probe_pair_queries;
        self.probe_boundary_queries += other.probe_boundary_queries;
        self.backend_confirmed_collisions += other.backend_confirmed_collisions;
        self.backend_confirmed_no_collisions += other.backend_confirmed_no_collisions;
        self.unsupported_queries += other.unsupported_queries;
        self.bbox_proxy_severity_uses += other.bbox_proxy_severity_uses;
        self.probe_resolved += other.probe_resolved;
        self.probe_unresolved += other.probe_unresolved;
        self.probe_unsupported += other.probe_unsupported;
        self.resolution_sum_mm += other.resolution_sum_mm;
        self.resolutions_recorded += other.resolutions_recorded;
        if other.min_resolution_mm > 0.0 {
            self.min_resolution_mm = if self.min_resolution_mm == 0.0 {
                other.min_resolution_mm
            } else {
                self.min_resolution_mm.min(other.min_resolution_mm)
            };
        }
        if other.max_resolution_mm > self.max_resolution_mm {
            self.max_resolution_mm = other.max_resolution_mm;
        }
    }
}

// ---------------------------------------------------------------------------
// EvaluationResult
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub enum SeverityMode {
    #[default]
    BboxLegacy,
    BackendOracleProbe,
    BboxProxyForBackend,
    Unsupported,
}

#[derive(Debug, Clone)]
pub struct EvaluationResult {
    pub loss: f64,
    pub unsupported: bool,
    pub pair_collision_count: usize,
    pub boundary_collision: bool,
    pub backend_confirmed_collision: bool,
    pub unresolved_probe: bool,
    pub severity_mode: SeverityMode,
}

impl EvaluationResult {
    fn zero(mode: SeverityMode) -> Self {
        Self {
            loss: 0.0,
            unsupported: false,
            pair_collision_count: 0,
            boundary_collision: false,
            backend_confirmed_collision: false,
            unresolved_probe: false,
            severity_mode: mode,
        }
    }
}

// ---------------------------------------------------------------------------
// Direction helpers
// ---------------------------------------------------------------------------

const NEAR_ZERO: f64 = 1.0e-9;
const DEDUP_TOL: f64 = 1.0e-3;

fn normalize(dx: f64, dy: f64) -> Option<(f64, f64)> {
    let mag = (dx * dx + dy * dy).sqrt();
    if mag < NEAR_ZERO {
        None
    } else {
        Some((dx / mag, dy / mag))
    }
}

fn push_unique(dirs: &mut Vec<(f64, f64)>, candidate: (f64, f64)) {
    for &(dx, dy) in dirs.iter() {
        if (dx - candidate.0).abs() < DEDUP_TOL && (dy - candidate.1).abs() < DEDUP_TOL {
            return;
        }
    }
    dirs.push(candidate);
}

fn bbox_center(p: &Placement, part: &Part) -> Option<(f64, f64)> {
    let pb = bbox_from_placement(p, part.width, part.height)?;
    Some(((pb.x1 + pb.x2) * 0.5, (pb.y1 + pb.y2) * 0.5))
}

/// Deterministic ordered list of unit-vector probe directions for a pair collision.
fn pair_probe_directions(
    candidate: &Placement,
    part: &Part,
    other: &Placement,
    other_part: &Part,
    cfg: &CollisionSeverityConfig,
) -> Vec<(f64, f64)> {
    let mut dirs: Vec<(f64, f64)> = Vec::with_capacity(9);
    // Cardinal directions.
    push_unique(&mut dirs, (1.0, 0.0));
    push_unique(&mut dirs, (-1.0, 0.0));
    push_unique(&mut dirs, (0.0, 1.0));
    push_unique(&mut dirs, (0.0, -1.0));
    // Diagonals.
    if cfg.probe_use_diagonal_directions {
        let inv = std::f64::consts::FRAC_1_SQRT_2;
        push_unique(&mut dirs, (inv, inv));
        push_unique(&mut dirs, (inv, -inv));
        push_unique(&mut dirs, (-inv, inv));
        push_unique(&mut dirs, (-inv, -inv));
    }
    // Pair-center-away direction: from other → candidate (normalized).
    if cfg.probe_use_pair_center_direction {
        if let (Some(c_cand), Some(c_other)) =
            (bbox_center(candidate, part), bbox_center(other, other_part))
        {
            if let Some(unit) = normalize(c_cand.0 - c_other.0, c_cand.1 - c_other.1) {
                push_unique(&mut dirs, unit);
            }
        }
    }
    dirs
}

/// Deterministic ordered list of unit-vector probe directions for a boundary violation.
fn boundary_probe_directions(
    candidate: &Placement,
    part: &Part,
    sheet: &SheetShape,
    cfg: &CollisionSeverityConfig,
) -> Vec<(f64, f64)> {
    let mut dirs: Vec<(f64, f64)> = Vec::with_capacity(9);
    push_unique(&mut dirs, (1.0, 0.0));
    push_unique(&mut dirs, (-1.0, 0.0));
    push_unique(&mut dirs, (0.0, 1.0));
    push_unique(&mut dirs, (0.0, -1.0));
    if cfg.probe_use_diagonal_directions {
        let inv = std::f64::consts::FRAC_1_SQRT_2;
        push_unique(&mut dirs, (inv, inv));
        push_unique(&mut dirs, (inv, -inv));
        push_unique(&mut dirs, (-inv, inv));
        push_unique(&mut dirs, (-inv, -inv));
    }
    if cfg.probe_use_center_direction {
        if let Some(c_cand) = bbox_center(candidate, part) {
            let c_sheet = (sheet.width * 0.5, sheet.height * 0.5);
            if let Some(unit) = normalize(c_sheet.0 - c_cand.0, c_sheet.1 - c_cand.1) {
                push_unique(&mut dirs, unit);
            }
        }
    }
    dirs
}

// ---------------------------------------------------------------------------
// Adaptive oracle probe (bracket + binary refinement)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy)]
enum ProbeKind {
    Pair,
    Boundary,
}

#[derive(Debug, Clone, Copy)]
enum DirectionOutcome {
    Resolved(f64),
    Unresolved,
    Unsupported,
}

fn shifted(candidate: &Placement, dx: f64, dy: f64, step: f64) -> Placement {
    Placement {
        instance_id: candidate.instance_id.clone(),
        part_id: candidate.part_id.clone(),
        sheet_index: candidate.sheet_index,
        x: candidate.x + dx * step,
        y: candidate.y + dy * step,
        rotation_deg: candidate.rotation_deg,
    }
}

/// Query the backend for a probed placement, counting under the correct probe
/// counter and unsupported counter on failure.
fn probe_query_pair(
    backend: &dyn CollisionBackend,
    probed: &Placement,
    part: &Part,
    other: &Placement,
    other_part: &Part,
    stats: &mut CollisionSeverityStats,
) -> CollisionDecision {
    stats.probe_queries += 1;
    stats.probe_pair_queries += 1;
    let d = backend.placement_overlaps(probed, part, other, other_part);
    if matches!(d, CollisionDecision::Unsupported { .. }) {
        stats.unsupported_queries += 1;
    }
    d
}

fn probe_query_boundary(
    backend: &dyn CollisionBackend,
    probed: &Placement,
    part: &Part,
    sheet: &SheetShape,
    stats: &mut CollisionSeverityStats,
) -> CollisionDecision {
    stats.probe_queries += 1;
    stats.probe_boundary_queries += 1;
    let d = backend.placement_within_sheet(probed, part, sheet);
    if matches!(d, CollisionDecision::Unsupported { .. }) {
        stats.unsupported_queries += 1;
    }
    d
}

/// Bracket the first clear step in this direction by geometric growth, then
/// binary-refine between `last_colliding` and `first_clear` until tolerance.
fn probe_direction_pair(
    backend: &dyn CollisionBackend,
    candidate: &Placement,
    part: &Part,
    other: &Placement,
    other_part: &Part,
    dx: f64,
    dy: f64,
    cfg: &CollisionSeverityConfig,
    stats: &mut CollisionSeverityStats,
    initial_step: f64,
) -> DirectionOutcome {
    let mut step = initial_step;
    let mut last_collide = 0.0_f64;
    let mut first_clear: Option<f64> = None;
    for _ in 0..cfg.probe_max_steps {
        let probed = shifted(candidate, dx, dy, step);
        match probe_query_pair(backend, &probed, part, other, other_part, stats) {
            CollisionDecision::Collision => {
                last_collide = step;
                step *= cfg.probe_bracket_growth.max(1.0);
            }
            CollisionDecision::NoCollision => {
                first_clear = Some(step);
                break;
            }
            CollisionDecision::Unsupported { .. } => {
                return DirectionOutcome::Unsupported;
            }
        }
    }
    let mut hi = match first_clear {
        Some(s) => s,
        None => return DirectionOutcome::Unresolved,
    };
    let mut lo = last_collide;
    for _ in 0..cfg.probe_binary_refine_steps {
        if (hi - lo) < cfg.probe_tolerance_mm.max(NEAR_ZERO) {
            break;
        }
        let mid = (lo + hi) * 0.5;
        let probed = shifted(candidate, dx, dy, mid);
        match probe_query_pair(backend, &probed, part, other, other_part, stats) {
            CollisionDecision::Collision => {
                lo = mid;
            }
            CollisionDecision::NoCollision => {
                hi = mid;
            }
            CollisionDecision::Unsupported { .. } => {
                // Refinement aborts on unsupported; return the unrefined bracket clear.
                return DirectionOutcome::Resolved(hi);
            }
        }
    }
    DirectionOutcome::Resolved(hi)
}

fn probe_direction_boundary(
    backend: &dyn CollisionBackend,
    candidate: &Placement,
    part: &Part,
    sheet: &SheetShape,
    dx: f64,
    dy: f64,
    cfg: &CollisionSeverityConfig,
    stats: &mut CollisionSeverityStats,
    initial_step: f64,
) -> DirectionOutcome {
    let mut step = initial_step;
    let mut last_collide = 0.0_f64;
    let mut first_clear: Option<f64> = None;
    for _ in 0..cfg.probe_max_steps {
        let probed = shifted(candidate, dx, dy, step);
        match probe_query_boundary(backend, &probed, part, sheet, stats) {
            CollisionDecision::Collision => {
                last_collide = step;
                step *= cfg.probe_bracket_growth.max(1.0);
            }
            CollisionDecision::NoCollision => {
                first_clear = Some(step);
                break;
            }
            CollisionDecision::Unsupported { .. } => {
                return DirectionOutcome::Unsupported;
            }
        }
    }
    let mut hi = match first_clear {
        Some(s) => s,
        None => return DirectionOutcome::Unresolved,
    };
    let mut lo = last_collide;
    for _ in 0..cfg.probe_binary_refine_steps {
        if (hi - lo) < cfg.probe_tolerance_mm.max(NEAR_ZERO) {
            break;
        }
        let mid = (lo + hi) * 0.5;
        let probed = shifted(candidate, dx, dy, mid);
        match probe_query_boundary(backend, &probed, part, sheet, stats) {
            CollisionDecision::Collision => {
                lo = mid;
            }
            CollisionDecision::NoCollision => {
                hi = mid;
            }
            CollisionDecision::Unsupported { .. } => {
                return DirectionOutcome::Resolved(hi);
            }
        }
    }
    DirectionOutcome::Resolved(hi)
}

/// Returns `(severity, unresolved)`:
/// - `severity` = best refined resolution distance across all probed directions,
///   or `cfg.hard_unsupported_loss` if no direction resolved.
/// - `unresolved = true` when no direction returned `Resolved(_)`.
fn run_pair_probe(
    backend: &dyn CollisionBackend,
    candidate: &Placement,
    part: &Part,
    other: &Placement,
    other_part: &Part,
    sheet_diag: f64,
    cfg: &CollisionSeverityConfig,
    stats: &mut CollisionSeverityStats,
) -> (f64, bool) {
    let initial = cfg.effective_initial_step(sheet_diag);
    let dirs = pair_probe_directions(candidate, part, other, other_part, cfg);
    let mut best: Option<f64> = None;
    for &(dx, dy) in &dirs {
        match probe_direction_pair(
            backend, candidate, part, other, other_part,
            dx, dy, cfg, stats, initial,
        ) {
            DirectionOutcome::Resolved(d) => {
                stats.probe_resolved += 1;
                stats.record_resolution(d);
                best = Some(match best {
                    Some(b) => b.min(d),
                    None => d,
                });
            }
            DirectionOutcome::Unresolved => {
                stats.probe_unresolved += 1;
            }
            DirectionOutcome::Unsupported => {
                stats.probe_unsupported += 1;
            }
        }
    }
    match best {
        Some(d) => (d.max(cfg.probe_min_step), false),
        None => (cfg.hard_unsupported_loss, true),
    }
}

fn run_boundary_probe(
    backend: &dyn CollisionBackend,
    candidate: &Placement,
    part: &Part,
    sheet: &SheetShape,
    cfg: &CollisionSeverityConfig,
    stats: &mut CollisionSeverityStats,
) -> (f64, bool) {
    let sheet_diag = (sheet.width * sheet.width + sheet.height * sheet.height).sqrt();
    let initial = cfg.effective_initial_step(sheet_diag);
    let dirs = boundary_probe_directions(candidate, part, sheet, cfg);
    let mut best: Option<f64> = None;
    for &(dx, dy) in &dirs {
        match probe_direction_boundary(
            backend, candidate, part, sheet, dx, dy, cfg, stats, initial,
        ) {
            DirectionOutcome::Resolved(d) => {
                stats.probe_resolved += 1;
                stats.record_resolution(d);
                best = Some(match best {
                    Some(b) => b.min(d),
                    None => d,
                });
            }
            DirectionOutcome::Unresolved => {
                stats.probe_unresolved += 1;
            }
            DirectionOutcome::Unsupported => {
                stats.probe_unsupported += 1;
            }
        }
    }
    match best {
        Some(d) => (d.max(cfg.probe_min_step), false),
        None => (cfg.hard_unsupported_loss, true),
    }
}

// Public probe helpers (kept for separator tracker's existing call sites).
#[allow(clippy::too_many_arguments)]
pub fn compute_probe_pair_severity(
    collision_backend: &CollisionBackendKind,
    pi: &Placement,
    part_i: &Part,
    pj: &Placement,
    part_j: &Part,
    sheet_diag: f64,
    cfg: &CollisionSeverityConfig,
    stats: &mut CollisionSeverityStats,
) -> f64 {
    if !cfg.probe_enabled {
        return 1.0;
    }
    let backend: &dyn CollisionBackend = match collision_backend {
        CollisionBackendKind::JaguaPolygonExact => &JaguaPolygonExactBackend,
        CollisionBackendKind::Cde => &CdeCollisionBackend,
        CollisionBackendKind::Bbox => return 1.0,
    };
    let (sev, _unresolved) = run_pair_probe(
        backend, pi, part_i, pj, part_j, sheet_diag, cfg, stats,
    );
    sev
}

pub fn compute_probe_boundary_severity(
    collision_backend: &CollisionBackendKind,
    pi: &Placement,
    part_i: &Part,
    sheet: &SheetShape,
    cfg: &CollisionSeverityConfig,
    stats: &mut CollisionSeverityStats,
) -> f64 {
    if !cfg.probe_enabled {
        return 1.0;
    }
    let backend: &dyn CollisionBackend = match collision_backend {
        CollisionBackendKind::JaguaPolygonExact => &JaguaPolygonExactBackend,
        CollisionBackendKind::Cde => &CdeCollisionBackend,
        CollisionBackendKind::Bbox => return 1.0,
    };
    let (sev, _unresolved) = run_boundary_probe(backend, pi, part_i, sheet, cfg, stats);
    sev
}

// ---------------------------------------------------------------------------
// Backend-aware evaluation core
// ---------------------------------------------------------------------------

fn eval_with_severity_backend(
    backend: &dyn CollisionBackend,
    candidate: &Placement,
    part: &Part,
    cand_bbox: &PlacedBbox,
    sheet: &SheetShape,
    layout: &WorkingLayout,
    target_idx: usize,
    parts: &[Part],
    loss_model: LossModelKind,
    cfg: &CollisionSeverityConfig,
    stats: &mut CollisionSeverityStats,
) -> EvaluationResult {
    let sheet_diag = (sheet.width * sheet.width + sheet.height * sheet.height).sqrt();

    // Boundary decision.
    stats.boundary_queries += 1;
    let mut backend_confirmed_collision = false;
    let mut unresolved_probe = false;
    let (boundary_loss, boundary_collision) =
        match backend.placement_within_sheet(candidate, part, sheet) {
            CollisionDecision::NoCollision => {
                stats.backend_confirmed_no_collisions += 1;
                (0.0, false)
            }
            CollisionDecision::Collision => {
                stats.backend_confirmed_collisions += 1;
                backend_confirmed_collision = true;
                let sev = if cfg.probe_enabled {
                    let (s, unresolved) =
                        run_boundary_probe(backend, candidate, part, sheet, cfg, stats);
                    if unresolved {
                        unresolved_probe = true;
                    }
                    s.max(1.0)
                } else {
                    stats.bbox_proxy_severity_uses += 1;
                    loss_model.compute_boundary_loss(cand_bbox, sheet, false).max(1.0)
                };
                (sev, true)
            }
            CollisionDecision::Unsupported { .. } => {
                stats.unsupported_queries += 1;
                return EvaluationResult {
                    loss: cfg.hard_unsupported_loss,
                    unsupported: true,
                    pair_collision_count: 0,
                    boundary_collision: false,
                    backend_confirmed_collision: false,
                    unresolved_probe: false,
                    severity_mode: SeverityMode::Unsupported,
                };
            }
        };

    let mut pair_loss = 0.0_f64;
    let mut pair_collision_count = 0usize;
    let severity_mode = if cfg.probe_enabled {
        SeverityMode::BackendOracleProbe
    } else {
        SeverityMode::BboxProxyForBackend
    };

    for (idx, other) in layout.placements.iter().enumerate() {
        if idx == target_idx || other.sheet_index != candidate.sheet_index {
            continue;
        }
        let Some(other_part) = parts.iter().find(|pt| pt.id == other.part_id) else {
            stats.unsupported_queries += 1;
            return EvaluationResult {
                loss: cfg.hard_unsupported_loss,
                unsupported: true,
                pair_collision_count,
                boundary_collision,
                backend_confirmed_collision,
                unresolved_probe,
                severity_mode: SeverityMode::Unsupported,
            };
        };

        stats.pair_queries += 1;
        match backend.placement_overlaps(candidate, part, other, other_part) {
            CollisionDecision::NoCollision => {
                stats.backend_confirmed_no_collisions += 1;
            }
            CollisionDecision::Collision => {
                stats.backend_confirmed_collisions += 1;
                backend_confirmed_collision = true;
                pair_collision_count += 1;
                let sev = if cfg.probe_enabled {
                    let (s, unresolved) = run_pair_probe(
                        backend, candidate, part, other, other_part, sheet_diag, cfg, stats,
                    );
                    if unresolved {
                        unresolved_probe = true;
                    }
                    s.max(1.0)
                } else {
                    stats.bbox_proxy_severity_uses += 1;
                    match bbox_from_placement(other, other_part.width, other_part.height) {
                        Some(ob) => loss_model.pair_loss(&ob, cand_bbox).max(1.0),
                        None => cfg.hard_unsupported_loss,
                    }
                };
                pair_loss += sev;
            }
            CollisionDecision::Unsupported { .. } => {
                stats.unsupported_queries += 1;
                return EvaluationResult {
                    loss: cfg.hard_unsupported_loss,
                    unsupported: true,
                    pair_collision_count,
                    boundary_collision,
                    backend_confirmed_collision,
                    unresolved_probe,
                    severity_mode: SeverityMode::Unsupported,
                };
            }
        }
    }

    EvaluationResult {
        loss: boundary_loss + pair_loss,
        unsupported: false,
        pair_collision_count,
        boundary_collision,
        backend_confirmed_collision,
        unresolved_probe,
        severity_mode,
    }
}

fn eval_bbox_loss(
    candidate: &Placement,
    cand_bbox: &PlacedBbox,
    sheet: &SheetShape,
    layout: &WorkingLayout,
    target_idx: usize,
    parts: &[Part],
    loss_model: LossModelKind,
) -> EvaluationResult {
    let rect = Rect {
        x1: cand_bbox.x1,
        y1: cand_bbox.y1,
        x2: cand_bbox.x2,
        y2: cand_bbox.y2,
    };
    if !rect_within_boundary(rect, sheet) {
        // Legacy reject sentinel: Bbox backend signals "out of sheet" — this is
        // not an Unsupported severity case; preserves Q21 behavior for compatibility.
        return EvaluationResult {
            loss: f64::MAX,
            unsupported: false,
            pair_collision_count: 0,
            boundary_collision: true,
            backend_confirmed_collision: false,
            unresolved_probe: false,
            severity_mode: SeverityMode::BboxLegacy,
        };
    }
    let pair_loss: f64 = layout
        .placements
        .iter()
        .enumerate()
        .filter(|(i, p)| *i != target_idx && p.sheet_index == candidate.sheet_index)
        .filter_map(|(_, p)| {
            parts
                .iter()
                .find(|pt| pt.id == p.part_id)
                .and_then(|pt| bbox_from_placement(p, pt.width, pt.height))
                .map(|pb| loss_model.pair_loss(&pb, cand_bbox))
        })
        .sum();
    EvaluationResult {
        loss: pair_loss,
        unsupported: false,
        pair_collision_count: if pair_loss > 0.0 { 1 } else { 0 },
        boundary_collision: false,
        backend_confirmed_collision: false,
        unresolved_probe: false,
        severity_mode: SeverityMode::BboxLegacy,
    }
}

// ---------------------------------------------------------------------------
// Central public evaluate_transform_loss
// ---------------------------------------------------------------------------

/// Evaluate the total loss for placing `candidate` at a given transform.
///
/// Bbox backend: preserves legacy `loss_model` behavior.
/// CDE/JaguaPolygonExact: active backend decides collision existence; on Collision,
/// severity = backend-oracle multi-direction probe distance (bracket + binary refine).
/// Unsupported → `cfg.hard_unsupported_loss`, `unsupported = true`.
#[allow(clippy::too_many_arguments)]
pub fn evaluate_transform_loss(
    candidate: &Placement,
    part: &Part,
    cand_bbox: &PlacedBbox,
    sheet: &SheetShape,
    layout: &WorkingLayout,
    target_idx: usize,
    parts: &[Part],
    collision_backend: &CollisionBackendKind,
    loss_model: LossModelKind,
    cfg: &CollisionSeverityConfig,
    stats: &mut CollisionSeverityStats,
) -> EvaluationResult {
    if !cfg.enabled_for_exact_backends || matches!(collision_backend, CollisionBackendKind::Bbox) {
        return eval_bbox_loss(candidate, cand_bbox, sheet, layout, target_idx, parts, loss_model);
    }
    match collision_backend {
        CollisionBackendKind::JaguaPolygonExact => eval_with_severity_backend(
            &JaguaPolygonExactBackend,
            candidate, part, cand_bbox, sheet, layout, target_idx, parts,
            loss_model, cfg, stats,
        ),
        CollisionBackendKind::Cde => {
            // SGH-Q23R2: production CDE path uses the single-engine multi-hazard
            // batch evaluator (one CDEngine for all same-sheet hazards, candidate
            // queried once + cheap CDE-truth separation probe). Falls back to the
            // pairwise severity path only if the session cannot be built.
            evaluate_transform_cde_batch(
                candidate, part, sheet, layout, target_idx, parts, cfg, stats,
            )
        }
        CollisionBackendKind::Bbox => unreachable!(),
    }
}

// ---------------------------------------------------------------------------
// SGH-Q23R2: single-engine multi-hazard batch evaluator (CDE production path)
// ---------------------------------------------------------------------------

fn shifted_xy(p: &Placement, dx: f64, dy: f64) -> Placement {
    Placement { x: p.x + dx, y: p.y + dy, ..p.clone() }
}

/// CDE-truth separation loss: the smallest translation distance (over a few
/// directions, bracket + binary refine) that makes the candidate fully clear
/// according to the batch session. No `CDEngine::new` per probe step (the session
/// is reused), and the bbox is never used as loss truth — the session/CDE decides
/// "clear". Returns a finite loss; if no direction clears within the cap, returns
/// a large (but finite) loss proportional to the sheet diagonal.
#[allow(clippy::too_many_arguments)]
fn cde_batch_separation_loss(
    session: &crate::optimizer::cde_adapter::CdeCandidateSession,
    candidate: &Placement,
    part: &Part,
    sheet: &SheetShape,
    cfg: &CollisionSeverityConfig,
    stats: &mut CollisionSeverityStats,
) -> f64 {
    let sheet_diag = (sheet.width * sheet.width + sheet.height * sheet.height).sqrt();
    let initial = cfg.effective_initial_step(sheet_diag);
    let max_reach = sheet_diag;
    // 8 compass directions.
    const DIRS: [(f64, f64); 8] = [
        (1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0),
        (0.7071, 0.7071), (-0.7071, 0.7071), (0.7071, -0.7071), (-0.7071, -0.7071),
    ];
    let clear_at = |dx: f64, dy: f64| -> bool {
        match crate::optimizer::cde_adapter::prepare_candidate(&shifted_xy(candidate, dx, dy), part) {
            Some(s) => session.query(&s).is_clear(),
            None => false,
        }
    };
    let mut best: Option<f64> = None;
    for &(ux, uy) in DIRS.iter() {
        // Bracket: grow step until clear or exceed max_reach.
        let mut step = initial;
        let mut bracket: Option<(f64, f64)> = None; // (last_collide_dist, first_clear_dist)
        let mut prev = 0.0_f64;
        while step <= max_reach {
            stats.probe_pair_queries += 1;
            if clear_at(ux * step, uy * step) {
                bracket = Some((prev, step));
                break;
            }
            prev = step;
            step *= 2.0;
        }
        let Some((mut lo, mut hi)) = bracket else { continue };
        // Binary refine to probe_min_step resolution (bounded iterations).
        for _ in 0..8 {
            if hi - lo <= cfg.probe_min_step {
                break;
            }
            let mid = 0.5 * (lo + hi);
            stats.probe_pair_queries += 1;
            if clear_at(ux * mid, uy * mid) {
                hi = mid;
            } else {
                lo = mid;
            }
        }
        best = Some(match best {
            Some(b) => b.min(hi),
            None => hi,
        });
    }
    match best {
        Some(d) => d.max(cfg.probe_min_step),
        // No direction cleared within reach — finite large loss (still ranks worse
        // than any resolvable candidate, but not the unsupported sentinel).
        None => max_reach + sheet_diag,
    }
}

#[allow(clippy::too_many_arguments)]
fn evaluate_transform_cde_batch(
    candidate: &Placement,
    part: &Part,
    sheet: &SheetShape,
    layout: &WorkingLayout,
    target_idx: usize,
    parts: &[Part],
    cfg: &CollisionSeverityConfig,
    stats: &mut CollisionSeverityStats,
) -> EvaluationResult {
    use crate::optimizer::cde_adapter::{build_candidate_session, prepare_candidate};

    let session = match build_candidate_session(
        &layout.placements, target_idx, candidate.sheet_index, parts, sheet,
    ) {
        Some(s) => s,
        None => {
            // Could not build the batch session → fall back to the pairwise path.
            crate::optimizer::cde_observability::inc_pairwise_fallback();
            let cand_bbox = match bbox_from_placement(candidate, part.width, part.height) {
                Some(b) => b,
                None => {
                    stats.unsupported_queries += 1;
                    return EvaluationResult {
                        loss: cfg.hard_unsupported_loss,
                        unsupported: true,
                        pair_collision_count: 0,
                        boundary_collision: false,
                        backend_confirmed_collision: false,
                        unresolved_probe: false,
                        severity_mode: SeverityMode::Unsupported,
                    };
                }
            };
            return eval_with_severity_backend(
                &CdeCollisionBackend, candidate, part, &cand_bbox, sheet, layout,
                target_idx, parts, LossModelKind::BboxArea, cfg, stats,
            );
        }
    };

    let Some(cand_shape) = prepare_candidate(candidate, part) else {
        stats.unsupported_queries += 1;
        return EvaluationResult {
            loss: cfg.hard_unsupported_loss,
            unsupported: true,
            pair_collision_count: 0,
            boundary_collision: false,
            backend_confirmed_collision: false,
            unresolved_probe: false,
            severity_mode: SeverityMode::Unsupported,
        };
    };

    stats.boundary_queries += 1;
    let res = session.query(&cand_shape);
    if res.unsupported {
        stats.unsupported_queries += 1;
        return EvaluationResult {
            loss: cfg.hard_unsupported_loss,
            unsupported: true,
            pair_collision_count: res.colliding_layout_idxs.len(),
            boundary_collision: res.boundary_collision,
            backend_confirmed_collision: false,
            unresolved_probe: false,
            severity_mode: SeverityMode::Unsupported,
        };
    }
    stats.pair_queries += session.hazard_count();

    if res.is_clear() {
        stats.backend_confirmed_no_collisions += 1;
        return EvaluationResult {
            loss: 0.0,
            unsupported: false,
            pair_collision_count: 0,
            boundary_collision: false,
            backend_confirmed_collision: false,
            unresolved_probe: false,
            severity_mode: SeverityMode::BackendOracleProbe,
        };
    }

    stats.backend_confirmed_collisions += 1;
    let loss = cde_batch_separation_loss(&session, candidate, part, sheet, cfg, stats);
    EvaluationResult {
        loss,
        unsupported: false,
        pair_collision_count: res.colliding_layout_idxs.len(),
        boundary_collision: res.boundary_collision,
        backend_confirmed_collision: true,
        unresolved_probe: false,
        severity_mode: SeverityMode::BackendOracleProbe,
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::item::Part;
    use crate::io::Placement;
    use crate::optimizer::working::WorkingLayout;
    use crate::sheet::{expand_sheets, Stock};

    fn make_rect_part(id: &str, w: f64, h: f64) -> Part {
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

    fn make_placement(instance_id: &str, part_id: &str, x: f64, y: f64) -> Placement {
        Placement {
            instance_id: instance_id.to_string(),
            part_id: part_id.to_string(),
            sheet_index: 0,
            x,
            y,
            rotation_deg: 0.0,
        }
    }

    fn make_sheets(w: f64, h: f64) -> Vec<crate::sheet::SheetShape> {
        expand_sheets(&[Stock {
            id: "S".into(),
            quantity: 1,
            width: Some(w),
            height: Some(h),
            outer_points: None,
            holes_points: None,
            cost_per_use: None,
        }]).expect("expand_sheets")
    }

    fn default_cfg() -> CollisionSeverityConfig {
        CollisionSeverityConfig::default()
    }

    // -----------------------------------------------------------------------
    // Q21R1-T0: Bbox backend preserves legacy pair loss behavior
    // -----------------------------------------------------------------------
    #[test]
    fn collision_severity_bbox_backend_preserves_legacy_pair_loss() {
        let part_a = make_rect_part("A", 30.0, 30.0);
        let part_b = make_rect_part("B", 30.0, 30.0);
        let parts = vec![part_a.clone(), part_b.clone()];
        let sheets = make_sheets(100.0, 100.0);
        let layout = WorkingLayout::new(
            vec![
                make_placement("A__0001", "A", 0.0, 0.0),
                make_placement("B__0001", "B", 10.0, 10.0),
            ], vec![], 1, 0,
        );
        let sheet = &sheets[0];
        let candidate = make_placement("B__0001", "B", 10.0, 10.0);
        let cand_bbox = PlacedBbox { sheet_index: 0, x1: 10.0, y1: 10.0, x2: 40.0, y2: 40.0 };
        let mut stats = CollisionSeverityStats::default();
        let result = evaluate_transform_loss(
            &candidate, &part_b, &cand_bbox, sheet, &layout, 1, &parts,
            &CollisionBackendKind::Bbox, LossModelKind::BboxArea, &default_cfg(), &mut stats,
        );
        assert!(!result.unsupported);
        assert!((result.loss - 400.0).abs() < 1e-9,
            "legacy pair loss must be dx*dy = 400, got {}", result.loss);
        assert_eq!(stats.pair_queries, 0);
        assert_eq!(result.severity_mode, SeverityMode::BboxLegacy);
    }

    // -----------------------------------------------------------------------
    // Q21R1-T1: Initial step is capped on large industrial sheet
    // -----------------------------------------------------------------------
    #[test]
    fn severity_initial_step_is_capped_on_large_sheet() {
        let cfg = default_cfg();
        // 1500 × 3000 sheet diagonal ≈ 3354 mm; legacy 5% → 167.7 mm.
        let diag = (1500.0_f64.powi(2) + 3000.0_f64.powi(2)).sqrt();
        let step = cfg.effective_initial_step(diag);
        assert!(step <= cfg.probe_max_initial_step_mm + 1e-9,
            "initial step must be capped at {} mm on industrial sheet, got {}",
            cfg.probe_max_initial_step_mm, step);
        assert!(step >= cfg.probe_min_step,
            "initial step must be at least probe_min_step={}, got {}",
            cfg.probe_min_step, step);
        // Small sheet (50×50, diag ≈ 70.7 → 5% = 3.54 mm) is well below the cap.
        let small_step = cfg.effective_initial_step(70.7);
        assert!(small_step < cfg.probe_max_initial_step_mm,
            "small-sheet step should be the scaled value, not the cap; got {}", small_step);
    }

    // -----------------------------------------------------------------------
    // Q21R1-T2: Pair probe uses diagonals and pair-center directions
    // -----------------------------------------------------------------------
    #[test]
    fn severity_pair_probe_uses_diagonal_and_pair_center_directions() {
        let part_a = make_rect_part("A", 20.0, 20.0);
        let part_b = make_rect_part("B", 20.0, 20.0);
        let cfg = default_cfg();
        let cand = make_placement("B__0001", "B", 10.0, 0.0);
        let other = make_placement("A__0001", "A", 0.0, 0.0);
        let dirs = pair_probe_directions(&cand, &part_b, &other, &part_a, &cfg);
        // 4 cardinal + 4 diagonal + 1 pair-center (b is to the right of a → +x;
        // dedup'd against cardinal +x).
        assert!(dirs.len() >= 8, "must have at least 8 directions, got {}: {:?}", dirs.len(), dirs);
        let diag_count = dirs.iter().filter(|(dx, dy)| dx.abs() > 0.1 && dy.abs() > 0.1).count();
        assert!(diag_count >= 4, "must have at least 4 diagonal directions, got {}", diag_count);
        // Disable diagonals → only 4 cardinals remain (pair-center dedupes to +x).
        let mut cfg2 = cfg.clone();
        cfg2.probe_use_diagonal_directions = false;
        cfg2.probe_use_pair_center_direction = false;
        let dirs2 = pair_probe_directions(&cand, &part_b, &other, &part_a, &cfg2);
        assert_eq!(dirs2.len(), 4, "with diagonals/center off: 4 cardinals, got {:?}", dirs2);
    }

    // -----------------------------------------------------------------------
    // Q21R1-T3: Boundary probe uses diagonals and sheet-center direction
    // -----------------------------------------------------------------------
    #[test]
    fn severity_boundary_probe_uses_diagonal_and_sheet_center_directions() {
        let cfg = default_cfg();
        let part = make_rect_part("P", 20.0, 20.0);
        let sheets = make_sheets(200.0, 200.0);
        // Candidate near the +x edge → sheet-center direction = (-1, 0) → dedups to cardinal.
        let cand_near_edge = make_placement("P__0001", "P", 175.0, 90.0);
        let dirs = boundary_probe_directions(&cand_near_edge, &part, &sheets[0], &cfg);
        assert!(dirs.len() >= 8, "boundary probe must have ≥ 8 directions, got {}", dirs.len());
        // Off-center sheet-center direction not dedup'd against cardinal.
        let cand_offset = make_placement("P__0001", "P", 25.0, 35.0);
        let dirs_off = boundary_probe_directions(&cand_offset, &part, &sheets[0], &cfg);
        let card = 4;
        let diag = 4;
        let center = 1;
        assert!(
            dirs_off.len() >= card + diag + center - 1,
            "offset candidate must include sheet-center direction, got {} dirs",
            dirs_off.len()
        );
        // Disable diagonals/center → 4 cardinals.
        let mut cfg2 = cfg.clone();
        cfg2.probe_use_diagonal_directions = false;
        cfg2.probe_use_center_direction = false;
        let dirs3 = boundary_probe_directions(&cand_offset, &part, &sheets[0], &cfg2);
        assert_eq!(dirs3.len(), 4);
    }

    // -----------------------------------------------------------------------
    // Q21R1-T4: Binary refinement returns a tighter resolution than the raw bracket
    // -----------------------------------------------------------------------
    #[test]
    fn severity_probe_binary_refines_resolution_distance() {
        let part_a = make_rect_part("A", 20.0, 20.0);
        let part_b = make_rect_part("B", 20.0, 20.0);
        let parts = vec![part_a.clone(), part_b.clone()];
        let sheets = make_sheets(200.0, 200.0);
        let sheet = &sheets[0];
        // A at (0,0), B overlapping at (10, 0) → 10 mm x-overlap.
        let layout = WorkingLayout::new(
            vec![
                make_placement("A__0001", "A", 0.0, 0.0),
                make_placement("B__0001", "B", 10.0, 0.0),
            ], vec![], 1, 0,
        );
        let candidate = make_placement("B__0001", "B", 10.0, 0.0);
        let cand_bbox = PlacedBbox { sheet_index: 0, x1: 10.0, y1: 0.0, x2: 30.0, y2: 20.0 };
        // With binary refinement enabled (default), result should be near 10 mm
        // (true resolution distance) within tolerance.
        let mut stats = CollisionSeverityStats::default();
        let cfg = default_cfg();
        let r = evaluate_transform_loss(
            &candidate, &part_b, &cand_bbox, sheet, &layout, 1, &parts,
            &CollisionBackendKind::JaguaPolygonExact, LossModelKind::BboxArea, &cfg, &mut stats,
        );
        assert!(!r.unsupported);
        // 10 mm true overlap in +x; with binary refinement the +x direction should
        // resolve at ≈ 10 mm with tolerance ≤ probe_tolerance_mm.
        assert!(r.loss < 11.0,
            "binary-refined +x clear must be near 10 mm, got {} (refinement skipped?)",
            r.loss);
        assert!(stats.probe_pair_queries > 4,
            "probe sub-queries must include both bracket+refinement, got {}",
            stats.probe_pair_queries);
        assert!(stats.probe_resolved > 0);
    }

    // -----------------------------------------------------------------------
    // Q21R1-T5: Probe Unsupported increments unsupported_queries + probe_unsupported
    // -----------------------------------------------------------------------
    #[test]
    fn severity_probe_unsupported_increments_unsupported_queries() {
        // Degenerate polygon → JaguaPolygonExact returns Unsupported on all queries.
        let invalid_outer = serde_json::json!([[0.0, 0.0], [10.0, 0.0]]);
        let bad_part = Part {
            id: "P".to_string(), width: 20.0, height: 20.0, quantity: 1,
            allowed_rotations_deg: vec![0], holes_points: None, prepared_holes_points: None,
            outer_points: Some(invalid_outer), prepared_outer_points: None, rotation_policy: None,
        };
        let parts = vec![bad_part.clone()];
        let sheets = make_sheets(100.0, 100.0);
        let sheet = &sheets[0];
        let layout = WorkingLayout::new(
            vec![make_placement("P__0001", "P", 0.0, 0.0)],
            vec![], 1, 0,
        );
        let candidate = make_placement("P__0001", "P", 0.0, 0.0);
        let cand_bbox = PlacedBbox { sheet_index: 0, x1: 0.0, y1: 0.0, x2: 20.0, y2: 20.0 };
        let mut stats = CollisionSeverityStats::default();
        let r = evaluate_transform_loss(
            &candidate, &bad_part, &cand_bbox, sheet, &layout, 0, &parts,
            &CollisionBackendKind::JaguaPolygonExact, LossModelKind::BboxArea,
            &default_cfg(), &mut stats,
        );
        assert!(r.unsupported);
        assert!(stats.unsupported_queries > 0,
            "boundary unsupported query must be counted");
        assert_eq!(r.severity_mode, SeverityMode::Unsupported);
    }

    // -----------------------------------------------------------------------
    // Q21R1-T6: hard_unsupported_loss is returned, not f64::MAX
    // -----------------------------------------------------------------------
    #[test]
    fn severity_hard_unsupported_loss_used_instead_of_f64_max() {
        let invalid_outer = serde_json::json!([[0.0, 0.0], [10.0, 0.0]]);
        let bad_part = Part {
            id: "P".to_string(), width: 20.0, height: 20.0, quantity: 1,
            allowed_rotations_deg: vec![0], holes_points: None, prepared_holes_points: None,
            outer_points: Some(invalid_outer), prepared_outer_points: None, rotation_policy: None,
        };
        let parts = vec![bad_part.clone()];
        let sheets = make_sheets(100.0, 100.0);
        let sheet = &sheets[0];
        let layout = WorkingLayout::new(
            vec![make_placement("P__0001", "P", 0.0, 0.0)],
            vec![], 1, 0,
        );
        let candidate = make_placement("P__0001", "P", 0.0, 0.0);
        let cand_bbox = PlacedBbox { sheet_index: 0, x1: 0.0, y1: 0.0, x2: 20.0, y2: 20.0 };
        let mut stats = CollisionSeverityStats::default();
        let mut cfg = default_cfg();
        cfg.hard_unsupported_loss = 12345.0;
        let r = evaluate_transform_loss(
            &candidate, &bad_part, &cand_bbox, sheet, &layout, 0, &parts,
            &CollisionBackendKind::JaguaPolygonExact, LossModelKind::BboxArea, &cfg, &mut stats,
        );
        assert!(r.unsupported);
        assert!(r.loss < f64::MAX, "unsupported loss must not be f64::MAX");
        assert_eq!(r.loss, 12345.0,
            "unsupported loss must equal cfg.hard_unsupported_loss, got {}", r.loss);
    }

    // -----------------------------------------------------------------------
    // Q21R1-T7: Exact backend, no-collision zeroes bbox false-positive
    // -----------------------------------------------------------------------
    #[test]
    fn severity_bbox_false_positive_exact_backend_no_collision_zero_loss() {
        // L-shape notch fixture: bbox says overlap, exact says no collision.
        let l_json = serde_json::json!([
            [0.0, 0.0], [40.0, 0.0], [40.0, 20.0],
            [20.0, 20.0], [20.0, 40.0], [0.0, 40.0]
        ]);
        let l_part = Part {
            id: "L".to_string(), width: 40.0, height: 40.0, quantity: 1,
            allowed_rotations_deg: vec![0], holes_points: None, prepared_holes_points: None,
            outer_points: Some(l_json), prepared_outer_points: None, rotation_policy: None,
        };
        let b_part = make_rect_part("B", 15.0, 15.0);
        let parts = vec![l_part, b_part.clone()];
        let sheets = make_sheets(100.0, 100.0);
        let sheet = &sheets[0];
        let layout = WorkingLayout::new(
            vec![
                Placement { instance_id: "L__0001".into(), part_id: "L".into(),
                    sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 },
                Placement { instance_id: "B__0001".into(), part_id: "B".into(),
                    sheet_index: 0, x: 22.0, y: 22.0, rotation_deg: 0.0 },
            ], vec![], 1, 0,
        );
        let cand = Placement { instance_id: "B__0001".into(), part_id: "B".into(),
            sheet_index: 0, x: 22.0, y: 22.0, rotation_deg: 0.0 };
        let cand_bbox = PlacedBbox { sheet_index: 0, x1: 22.0, y1: 22.0, x2: 37.0, y2: 37.0 };
        let mut stats = CollisionSeverityStats::default();
        let r = evaluate_transform_loss(
            &cand, &b_part, &cand_bbox, sheet, &layout, 1, &parts,
            &CollisionBackendKind::JaguaPolygonExact, LossModelKind::BboxArea,
            &default_cfg(), &mut stats,
        );
        assert!(!r.unsupported);
        assert_eq!(r.loss, 0.0,
            "JaguaPolygonExact must give zero loss for item in notch, got {}", r.loss);
        assert_eq!(stats.bbox_proxy_severity_uses, 0);
        assert!(stats.backend_confirmed_no_collisions > 0);
    }

    // -----------------------------------------------------------------------
    // Q21R1-T8: Bbox proxy is used only when explicitly enabled (probe disabled)
    //            or when backend is Bbox.
    // -----------------------------------------------------------------------
    #[test]
    fn severity_bbox_proxy_only_when_explicitly_enabled_or_bbox_backend() {
        let part_a = make_rect_part("A", 20.0, 20.0);
        let part_b = make_rect_part("B", 20.0, 20.0);
        let parts = vec![part_a.clone(), part_b.clone()];
        let sheets = make_sheets(200.0, 200.0);
        let sheet = &sheets[0];
        let layout = WorkingLayout::new(
            vec![
                make_placement("A__0001", "A", 0.0, 0.0),
                make_placement("B__0001", "B", 10.0, 0.0),
            ], vec![], 1, 0,
        );
        let cand = make_placement("B__0001", "B", 10.0, 0.0);
        let cand_bbox = PlacedBbox { sheet_index: 0, x1: 10.0, y1: 0.0, x2: 30.0, y2: 20.0 };

        // Probe enabled → bbox proxy must NOT be used under JaguaPolygonExact.
        let mut stats_a = CollisionSeverityStats::default();
        let _ = evaluate_transform_loss(
            &cand, &part_b, &cand_bbox, sheet, &layout, 1, &parts,
            &CollisionBackendKind::JaguaPolygonExact, LossModelKind::BboxArea,
            &default_cfg(), &mut stats_a,
        );
        assert_eq!(stats_a.bbox_proxy_severity_uses, 0,
            "probe enabled: no bbox proxy uses, got {}", stats_a.bbox_proxy_severity_uses);

        // Probe explicitly disabled → bbox proxy IS used and counted.
        let mut cfg_no_probe = default_cfg();
        cfg_no_probe.probe_enabled = false;
        let mut stats_b = CollisionSeverityStats::default();
        let _ = evaluate_transform_loss(
            &cand, &part_b, &cand_bbox, sheet, &layout, 1, &parts,
            &CollisionBackendKind::JaguaPolygonExact, LossModelKind::BboxArea,
            &cfg_no_probe, &mut stats_b,
        );
        assert!(stats_b.bbox_proxy_severity_uses > 0,
            "probe disabled: bbox proxy uses expected > 0, got {}",
            stats_b.bbox_proxy_severity_uses);
    }

    // -----------------------------------------------------------------------
    // Q21R1-T9: Confirmed collision returns positive severity with probe stats
    // -----------------------------------------------------------------------
    #[test]
    fn severity_exact_confirmed_collision_returns_positive_resolved_severity() {
        let part_a = make_rect_part("A", 20.0, 20.0);
        let part_b = make_rect_part("B", 20.0, 20.0);
        let parts = vec![part_a.clone(), part_b.clone()];
        let sheets = make_sheets(200.0, 200.0);
        let sheet = &sheets[0];
        let layout = WorkingLayout::new(
            vec![
                make_placement("A__0001", "A", 0.0, 0.0),
                make_placement("B__0001", "B", 10.0, 10.0),
            ], vec![], 1, 0,
        );
        let cand = make_placement("B__0001", "B", 10.0, 10.0);
        let cand_bbox = PlacedBbox { sheet_index: 0, x1: 10.0, y1: 10.0, x2: 30.0, y2: 30.0 };
        let mut stats = CollisionSeverityStats::default();
        let r = evaluate_transform_loss(
            &cand, &part_b, &cand_bbox, sheet, &layout, 1, &parts,
            &CollisionBackendKind::JaguaPolygonExact, LossModelKind::BboxArea,
            &default_cfg(), &mut stats,
        );
        assert!(!r.unsupported);
        assert!(r.loss > 0.0);
        assert_eq!(r.pair_collision_count, 1);
        assert!(r.backend_confirmed_collision);
        assert!(stats.probe_pair_queries > 0,
            "must record probe_pair_queries > 0");
        assert!(stats.probe_resolved > 0);
        assert!(stats.resolutions_recorded > 0);
    }

    // -----------------------------------------------------------------------
    // Q21R1-T10: Shallow vs deep collision is monotonic with the resolved severity
    // -----------------------------------------------------------------------
    #[test]
    fn severity_shallow_vs_deep_collision_is_monotonic() {
        let part_a = make_rect_part("A", 20.0, 20.0);
        let part_b = make_rect_part("B", 20.0, 20.0);
        let parts = vec![part_a.clone(), part_b.clone()];
        let sheets = make_sheets(200.0, 200.0);
        let sheet = &sheets[0];

        let cfg = default_cfg();
        // Shallow: 1 mm x-overlap.
        let layout_s = WorkingLayout::new(
            vec![
                make_placement("A__0001", "A", 0.0, 0.0),
                make_placement("B__0001", "B", 19.0, 0.0),
            ], vec![], 1, 0,
        );
        let cand_s = make_placement("B__0001", "B", 19.0, 0.0);
        let bbox_s = PlacedBbox { sheet_index: 0, x1: 19.0, y1: 0.0, x2: 39.0, y2: 20.0 };
        let mut st_s = CollisionSeverityStats::default();
        let r_s = evaluate_transform_loss(
            &cand_s, &part_b, &bbox_s, sheet, &layout_s, 1, &parts,
            &CollisionBackendKind::JaguaPolygonExact, LossModelKind::BboxArea, &cfg, &mut st_s,
        );
        // Deep: 15 mm x-overlap.
        let layout_d = WorkingLayout::new(
            vec![
                make_placement("A__0001", "A", 0.0, 0.0),
                make_placement("B__0001", "B", 5.0, 0.0),
            ], vec![], 1, 0,
        );
        let cand_d = make_placement("B__0001", "B", 5.0, 0.0);
        let bbox_d = PlacedBbox { sheet_index: 0, x1: 5.0, y1: 0.0, x2: 25.0, y2: 20.0 };
        let mut st_d = CollisionSeverityStats::default();
        let r_d = evaluate_transform_loss(
            &cand_d, &part_b, &bbox_d, sheet, &layout_d, 1, &parts,
            &CollisionBackendKind::JaguaPolygonExact, LossModelKind::BboxArea, &cfg, &mut st_d,
        );
        assert!(!r_s.unsupported && !r_d.unsupported);
        assert!(r_s.loss < r_d.loss,
            "shallow severity ({}) must be < deep severity ({})", r_s.loss, r_d.loss);
    }

    // -----------------------------------------------------------------------
    // Q21R1-T11: Boundary violation gives positive backend-probed severity
    // -----------------------------------------------------------------------
    #[test]
    fn severity_boundary_violation_positive() {
        let part = make_rect_part("P", 20.0, 20.0);
        let parts = vec![part.clone()];
        let sheets = make_sheets(100.0, 100.0);
        let sheet = &sheets[0];
        let layout = WorkingLayout::new(
            vec![make_placement("P__0001", "P", 95.0, 95.0)],
            vec![], 1, 0,
        );
        let cand = make_placement("P__0001", "P", 95.0, 95.0);
        let cand_bbox = PlacedBbox { sheet_index: 0, x1: 95.0, y1: 95.0, x2: 115.0, y2: 115.0 };
        let mut stats = CollisionSeverityStats::default();
        let r = evaluate_transform_loss(
            &cand, &part, &cand_bbox, sheet, &layout, 0, &parts,
            &CollisionBackendKind::JaguaPolygonExact, LossModelKind::BboxArea,
            &default_cfg(), &mut stats,
        );
        assert!(!r.unsupported);
        assert!(r.loss > 0.0);
        assert!(r.boundary_collision);
        assert!(stats.probe_boundary_queries > 0,
            "must record probe_boundary_queries > 0");
    }

    // -----------------------------------------------------------------------
    // Q21R1-T12: Boundary valid is zero loss
    // -----------------------------------------------------------------------
    #[test]
    fn severity_boundary_valid_is_zero() {
        let part = make_rect_part("P", 20.0, 20.0);
        let parts = vec![part.clone()];
        let sheets = make_sheets(100.0, 100.0);
        let sheet = &sheets[0];
        let layout = WorkingLayout::new(
            vec![make_placement("P__0001", "P", 0.0, 0.0)],
            vec![], 1, 0,
        );
        let cand = make_placement("P__0001", "P", 0.0, 0.0);
        let cand_bbox = PlacedBbox { sheet_index: 0, x1: 0.0, y1: 0.0, x2: 20.0, y2: 20.0 };
        let mut stats = CollisionSeverityStats::default();
        let r = evaluate_transform_loss(
            &cand, &part, &cand_bbox, sheet, &layout, 0, &parts,
            &CollisionBackendKind::JaguaPolygonExact, LossModelKind::BboxArea,
            &default_cfg(), &mut stats,
        );
        assert!(!r.unsupported);
        assert_eq!(r.loss, 0.0);
        assert!(!r.boundary_collision);
        assert!(stats.backend_confirmed_no_collisions > 0);
    }
}
