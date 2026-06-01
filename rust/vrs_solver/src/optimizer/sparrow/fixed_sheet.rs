use super::*;

// ---------------------------------------------------------------------------
// CDE-truth quantification primitives
// ---------------------------------------------------------------------------

/// Bbox-center of a prepared shape (used only as a direction/centroid hint —
/// never as collision truth).
fn shape_center(s: &CdePreparedShape) -> (f64, f64) {
    ((s.min_x + s.max_x) * 0.5, (s.min_y + s.max_y) * 0.5)
}

/// Normalize a 2-vector; falls back to +x for a degenerate (zero) vector.
fn unit(dx: f64, dy: f64) -> (f64, f64) {
    let n = (dx * dx + dy * dy).sqrt();
    if n < 1e-9 {
        (1.0, 0.0)
    } else {
        (dx / n, dy / n)
    }
}

/// CDE-truth pairwise *resolution distance*: the minimal translation of the
/// moving part (along unit `dir`) that clears `fixed` according to the CDE.
/// Uses bracket doubling to find a clearing distance, then binary refinement to
/// tighten it. Returns a positive separation magnitude (>= a small floor when a
/// collision is confirmed at the start). bbox/AABB never decides collision here:
/// every probe step is resolved by `CdeAdapter::query_pair`.
#[allow(clippy::too_many_arguments)]
fn probe_pair_resolution_distance(
    part: &Part,
    x: f64,
    y: f64,
    rot: f64,
    dir: (f64, f64),
    base_step: f64,
    fixed: &CdePreparedShape,
    cfg: &SparrowConfig,
    diag: &mut SparrowDiagnostics,
) -> f64 {
    let adapter = CdeAdapter::with_defaults();
    let step0 = base_step.max(1e-3);
    let collides_at = |t: f64, diag: &mut SparrowDiagnostics| -> bool {
        let nx = x + dir.0 * t;
        let ny = y + dir.1 * t;
        match prepare_shape_native(part, nx, ny, rot) {
            Ok(s) => {
                diag.quantified_pair_queries += 1;
                matches!(adapter.query_pair(&s, fixed), CdeQueryResult::Collision)
            }
            Err(_) => {
                diag.unsupported_queries += 1;
                // Treat a prepare failure as "still colliding" so the probe keeps
                // its honest positive bias (never silently clears).
                true
            }
        }
    };
    // Bracket: grow until clear or budget exhausted.
    let mut lo = 0.0_f64; // known colliding (caller confirmed a collision)
    let mut hi = step0;
    let mut bracketed = false;
    for _ in 0..cfg.probe_bracket_steps.max(1) {
        if collides_at(hi, diag) {
            lo = hi;
            hi *= 2.0;
        } else {
            bracketed = true;
            break;
        }
    }
    if !bracketed {
        // Could not clear within the bracket budget: report the deepest probe as
        // the (large) resolution distance — a strong, honest separation penalty.
        return hi.max(step0);
    }
    // Binary refine the clearing distance in (lo, hi].
    for _ in 0..cfg.probe_binary_refine_steps {
        let mid = 0.5 * (lo + hi);
        if collides_at(mid, diag) {
            lo = mid;
        } else {
            hi = mid;
        }
    }
    hi.max(step0 * 0.25)
}

/// CDE-truth *container clearance* distance: minimal translation of the moving
/// part toward the sheet centroid that brings it inside the sheet boundary.
#[allow(clippy::too_many_arguments)]
fn probe_boundary_resolution_distance(
    part: &Part,
    x: f64,
    y: f64,
    rot: f64,
    sheet_center: (f64, f64),
    item_center: (f64, f64),
    diag_diam: f64,
    sheet_shape: &CdePreparedShape,
    cfg: &SparrowConfig,
    diag: &mut SparrowDiagnostics,
) -> f64 {
    let adapter = CdeAdapter::with_defaults();
    let dir = unit(
        sheet_center.0 - item_center.0,
        sheet_center.1 - item_center.1,
    );
    let base_step = (diag_diam * 0.1).max(1e-3);
    let outside_at = |t: f64, diag: &mut SparrowDiagnostics| -> bool {
        let nx = x + dir.0 * t;
        let ny = y + dir.1 * t;
        match prepare_shape_native(part, nx, ny, rot) {
            Ok(s) => {
                diag.quantified_boundary_queries += 1;
                matches!(
                    adapter.query_boundary(&s, sheet_shape),
                    CdeQueryResult::Collision
                )
            }
            Err(_) => {
                diag.unsupported_queries += 1;
                true
            }
        }
    };
    let mut lo = 0.0_f64;
    let mut hi = base_step;
    let mut bracketed = false;
    for _ in 0..cfg.probe_bracket_steps.max(1) {
        if outside_at(hi, diag) {
            lo = hi;
            hi *= 2.0;
        } else {
            bracketed = true;
            break;
        }
    }
    if !bracketed {
        return hi.max(base_step);
    }
    for _ in 0..cfg.probe_binary_refine_steps {
        let mid = 0.5 * (lo + hi);
        if outside_at(mid, diag) {
            lo = mid;
        } else {
            hi = mid;
        }
    }
    hi.max(base_step * 0.25)
}


/// Pick the first allowed rotation under which the part fits at least one sheet
/// (rotation-aware: parts that only fit rotated — e.g. a strip wider than the
/// sheet at 0° — get a fitting rotation instead of being dropped).
pub(crate) fn fitting_rotation(inst: &SPInstance, sheets: &[SheetShape]) -> f64 {
    let rots: Vec<f64> = if inst.allowed_rotations_deg.is_empty() {
        vec![0.0]
    } else {
        inst.allowed_rotations_deg.clone()
    };
    for &rot in &rots {
        let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, rot);
        if sheets
            .iter()
            .any(|s| rw <= s.width + 1e-9 && rh <= s.height + 1e-9)
        {
            return rot;
        }
    }
    rots[0]
}

pub(crate) fn rect_min_from_anchor(x: f64, y: f64, width: f64, height: f64, rot_deg: f64) -> (f64, f64) {
    let (ox, oy) = rotated_bbox_min_offset(width, height, rot_deg);
    (x + ox, y + oy)
}
