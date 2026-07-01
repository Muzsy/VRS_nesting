//! SGH-Q54A — Skeleton state + critical role assignment.
//!
//! The critical sheet-building skeleton's base layer: a [`SheetSkeletonState`] that tracks, per
//! sheet, the critical parts already admitted (with their role and world bbox), plus an
//! [`assign_role`] function that classifies the next critical candidate as `Anchor` / `Interlock` /
//! `BandInsert` — **without any per-sheet count hardcode**, purely from the sheet's current skeleton
//! topology and the part's Q47 profile.
//!
//! This layer does **not** change placement; it only carries state and a role decision that Q54B–E
//! build on (clearance-aware candidates, overlap-tolerant separation, free-space band insertion).
//! Gated by `VRS_SHEET_BUILDER_SKELETON` (default off) — when off, the state is never built and the
//! Q51/Q52 behaviour is byte-identical.

use super::shape_profile::PartShapeProfile;

/// True when the Q54 skeleton-aware critical admission is enabled (`VRS_SHEET_BUILDER_SKELETON=1`).
pub fn skeleton_builder_enabled() -> bool {
    std::env::var("VRS_SHEET_BUILDER_SKELETON").ok().as_deref() == Some("1")
}

/// SGH-Q54D: occupancy-grid cell size (mm) for the free-space proxy. Coarse on purpose (ranking
/// proxy, not collision truth). `VRS_SKELETON_FREESPACE_CELL_MM`, default 50, clamped [10, 200].
pub(crate) fn freespace_cell_mm() -> f64 {
    std::env::var("VRS_SKELETON_FREESPACE_CELL_MM")
        .ok()
        .and_then(|v| v.parse::<f64>().ok())
        .unwrap_or(50.0)
        .clamp(10.0, 200.0)
}

/// SGH-Q54D: largest **edge-connected** free-region area (mm²) on a sheet, via a coarse occupancy
/// grid. `occupied` are world bboxes `[min_x, min_y, max_x, max_y]` of already-placed parts; free
/// cells form connected components; we return the largest component that touches the sheet border
/// (the reference's third big part needs a large edge-connected band, not an enclosed pocket).
/// Rough ranking proxy only — the CDE remains the clearance truth.
pub fn largest_edge_connected_free_area(
    occupied: &[[f64; 4]],
    sheet_min_x: f64,
    sheet_min_y: f64,
    sheet_max_x: f64,
    sheet_max_y: f64,
    cell_mm: f64,
) -> f64 {
    let Some((nx, ny, cw, ch)) =
        grid_dims(sheet_min_x, sheet_min_y, sheet_max_x, sheet_max_y, cell_mm)
    else {
        return 0.0;
    };
    let occ = build_occ_from_bboxes(occupied, nx, ny, sheet_min_x, sheet_min_y, cw, ch);
    largest_border_free_area_from_occ(&occ, nx, ny, cw * ch)
}

/// SGH-Q76: contour-aware variant of [`largest_edge_connected_free_area`]. Occupancy is marked from
/// the parts' **real world contours** (even-odd scanline polygon raster) instead of their bounding
/// boxes, so a concave part's bay or a tight interlock gap is correctly counted as *free* useful
/// residual space — exactly what the skeleton-first seed objective must reward. `polys` are
/// world-space rings of `[x, y]` points (implicit last→first edge). Additive: the bbox version above
/// is byte-identical. Coarse ranking proxy; the CDE remains the clearance truth.
pub fn largest_edge_connected_free_area_contour(
    polys: &[Vec<[f64; 2]>],
    sheet_min_x: f64,
    sheet_min_y: f64,
    sheet_max_x: f64,
    sheet_max_y: f64,
    cell_mm: f64,
) -> f64 {
    let Some((nx, ny, cw, ch)) =
        grid_dims(sheet_min_x, sheet_min_y, sheet_max_x, sheet_max_y, cell_mm)
    else {
        return 0.0;
    };
    let occ = build_occ_from_contours(polys, nx, ny, sheet_min_x, sheet_min_y, cw, ch);
    largest_border_free_area_from_occ(&occ, nx, ny, cw * ch)
}

/// SGH-Q55C: world bbox `[min_x, min_y, max_x, max_y]` of the **largest edge-connected free**
/// component — the band the next BandInsert big part is placed into. `None` if there is no
/// border-touching free band. Same coarse occupancy grid as `largest_edge_connected_free_area`.
pub fn largest_edge_connected_free_slot(
    occupied: &[[f64; 4]],
    sheet_min_x: f64,
    sheet_min_y: f64,
    sheet_max_x: f64,
    sheet_max_y: f64,
    cell_mm: f64,
) -> Option<[f64; 4]> {
    let (nx, ny, cw, ch) =
        grid_dims(sheet_min_x, sheet_min_y, sheet_max_x, sheet_max_y, cell_mm)?;
    let occ = build_occ_from_bboxes(occupied, nx, ny, sheet_min_x, sheet_min_y, cw, ch);
    largest_border_free_slot_from_occ(&occ, nx, ny, sheet_min_x, sheet_min_y, cw, ch)
}

/// SGH-Q76: contour-aware variant of [`largest_edge_connected_free_slot`]. The largest
/// border-touching free band measured from real contours (scanline raster), so the residual-fill
/// targeting sees the true open space (concave bays included). Additive; bbox version unchanged.
pub fn largest_edge_connected_free_slot_contour(
    polys: &[Vec<[f64; 2]>],
    sheet_min_x: f64,
    sheet_min_y: f64,
    sheet_max_x: f64,
    sheet_max_y: f64,
    cell_mm: f64,
) -> Option<[f64; 4]> {
    let (nx, ny, cw, ch) =
        grid_dims(sheet_min_x, sheet_min_y, sheet_max_x, sheet_max_y, cell_mm)?;
    let occ = build_occ_from_contours(polys, nx, ny, sheet_min_x, sheet_min_y, cw, ch);
    largest_border_free_slot_from_occ(&occ, nx, ny, sheet_min_x, sheet_min_y, cw, ch)
}

/// SGH-Q76.1: **useful** (thickness-weighted) free area (mm²) from real contours. The plain
/// "largest edge-connected free area" is near-blind when one big part sits on a large sheet (every
/// valid placement leaves ~the same single big region), so it cannot steer the alignment. This
/// instead weights each free cell by its (capped) chamfer distance to the nearest *occupied* cell
/// (a coarse distance transform): thick, fill-able open space counts more than thin slivers wedged
/// between a part and a wall. The sheet border is NOT an obstacle (edge-adjacent open space is still
/// fillable), so a part's concave bay opening *into* the sheet scores higher than one trapped against
/// a wall. `cap_cells` saturates the reward beyond a useful thickness (≈ the fillers' half-size).
/// Additive — the area/slot functions above are unchanged. Coarse proxy; CDE stays the truth.
pub fn useful_free_area_contour(
    polys: &[Vec<[f64; 2]>],
    sheet_min_x: f64,
    sheet_min_y: f64,
    sheet_max_x: f64,
    sheet_max_y: f64,
    cell_mm: f64,
    cap_cells: u32,
) -> f64 {
    let Some((nx, ny, cw, ch)) =
        grid_dims(sheet_min_x, sheet_min_y, sheet_max_x, sheet_max_y, cell_mm)
    else {
        return 0.0;
    };
    let occ = build_occ_from_contours(polys, nx, ny, sheet_min_x, sheet_min_y, cw, ch);
    let cell_area = cw * ch;
    let cap = cap_cells.max(1);
    // Multi-source BFS (4-neighbour) seeded from every occupied cell → each free cell's distance
    // (in cells) to the nearest occupied cell. No occupied cell ⇒ every free cell is "fully thick".
    let mut dist = vec![u32::MAX; nx * ny];
    let mut queue: std::collections::VecDeque<usize> = std::collections::VecDeque::new();
    for idx in 0..nx * ny {
        if occ[idx] {
            dist[idx] = 0;
            queue.push_back(idx);
        }
    }
    if queue.is_empty() {
        // Empty sheet: maximal useful area (all cells saturated at the cap).
        return nx as f64 * ny as f64 * cap as f64 * cell_area;
    }
    while let Some(idx) = queue.pop_front() {
        let (i, j) = (idx % nx, idx / nx);
        let d = dist[idx];
        let mut relax = |ni: usize, nj: usize, dist: &mut [u32], q: &mut std::collections::VecDeque<usize>| {
            let nidx = nj * nx + ni;
            if dist[nidx] == u32::MAX {
                dist[nidx] = d + 1;
                q.push_back(nidx);
            }
        };
        if i > 0 {
            relax(i - 1, j, &mut dist, &mut queue);
        }
        if i + 1 < nx {
            relax(i + 1, j, &mut dist, &mut queue);
        }
        if j > 0 {
            relax(i, j - 1, &mut dist, &mut queue);
        }
        if j + 1 < ny {
            relax(i, j + 1, &mut dist, &mut queue);
        }
    }
    let mut useful = 0.0_f64;
    for idx in 0..nx * ny {
        if !occ[idx] {
            useful += dist[idx].min(cap) as f64 * cell_area;
        }
    }
    useful
}

// ---- shared occupancy-grid helpers (SGH-Q54D / Q55C / Q76) ----

/// Coarse occupancy-grid dimensions for a sheet: `(nx, ny, cell_w, cell_h)`, clamped to [1, 400]
/// cells per axis. `None` when the sheet or cell size is degenerate.
fn grid_dims(
    sheet_min_x: f64,
    sheet_min_y: f64,
    sheet_max_x: f64,
    sheet_max_y: f64,
    cell_mm: f64,
) -> Option<(usize, usize, f64, f64)> {
    let w = sheet_max_x - sheet_min_x;
    let h = sheet_max_y - sheet_min_y;
    if w <= 0.0 || h <= 0.0 || cell_mm <= 0.0 {
        return None;
    }
    let nx = ((w / cell_mm).ceil() as usize).clamp(1, 400);
    let ny = ((h / cell_mm).ceil() as usize).clamp(1, 400);
    Some((nx, ny, w / nx as f64, h / ny as f64))
}

/// Occupancy grid where a cell is occupied iff its centre falls inside any bbox (the Q54D rule).
fn build_occ_from_bboxes(
    occupied: &[[f64; 4]],
    nx: usize,
    ny: usize,
    sheet_min_x: f64,
    sheet_min_y: f64,
    cw: f64,
    ch: f64,
) -> Vec<bool> {
    let mut occ = vec![false; nx * ny];
    for j in 0..ny {
        let cy = sheet_min_y + (j as f64 + 0.5) * ch;
        for i in 0..nx {
            let cx = sheet_min_x + (i as f64 + 0.5) * cw;
            if occupied
                .iter()
                .any(|b| cx >= b[0] && cx <= b[2] && cy >= b[1] && cy <= b[3])
            {
                occ[j * nx + i] = true;
            }
        }
    }
    occ
}

/// SGH-Q76: occupancy grid where a cell is occupied iff its centre falls inside any real contour,
/// via even-odd scanline polygon rasterisation. High-vertex contours are decimated to ~half a cell
/// (the grid is a coarse proxy), bounding cost without changing the discretised result.
fn build_occ_from_contours(
    polys: &[Vec<[f64; 2]>],
    nx: usize,
    ny: usize,
    sheet_min_x: f64,
    sheet_min_y: f64,
    cw: f64,
    ch: f64,
) -> Vec<bool> {
    let mut occ = vec![false; nx * ny];
    let min_seg = 0.5 * cw.min(ch);
    for poly in polys {
        let simplified = decimate_poly(poly, min_seg);
        rasterize_polygon_into_occ(&simplified, &mut occ, nx, ny, sheet_min_x, sheet_min_y, cw, ch);
    }
    occ
}

/// Drop consecutive contour points closer than `min_seg` (coarse-grid simplification). Keeps the
/// ring's shape at the grid scale; falls back to the original on a near-degenerate result.
fn decimate_poly(poly: &[[f64; 2]], min_seg: f64) -> Vec<[f64; 2]> {
    if poly.len() <= 4 || min_seg <= 0.0 {
        return poly.to_vec();
    }
    let min_sq = min_seg * min_seg;
    let mut out: Vec<[f64; 2]> = Vec::with_capacity(poly.len());
    out.push(poly[0]);
    for p in &poly[1..] {
        let last = *out.last().unwrap();
        let (dx, dy) = (p[0] - last[0], p[1] - last[1]);
        if dx * dx + dy * dy >= min_sq {
            out.push(*p);
        }
    }
    if out.len() < 3 {
        return poly.to_vec();
    }
    out
}

/// Mark every cell whose centre lies inside `poly` (even-odd rule) on the occupancy grid. Classic
/// scanline fill: per grid row, intersect the polygon edges with the row-centre line, sort the
/// crossings, and fill the spans between consecutive pairs. A half-open vertical edge interval
/// counts each crossing once at shared vertices.
fn rasterize_polygon_into_occ(
    poly: &[[f64; 2]],
    occ: &mut [bool],
    nx: usize,
    ny: usize,
    sheet_min_x: f64,
    sheet_min_y: f64,
    cw: f64,
    ch: f64,
) {
    let n = poly.len();
    if n < 3 {
        return;
    }
    let mut xs: Vec<f64> = Vec::new();
    for j in 0..ny {
        let cy = sheet_min_y + (j as f64 + 0.5) * ch;
        xs.clear();
        for k in 0..n {
            let (x0, y0) = (poly[k][0], poly[k][1]);
            let (x1, y1) = (poly[(k + 1) % n][0], poly[(k + 1) % n][1]);
            if (cy >= y0 && cy < y1) || (cy >= y1 && cy < y0) {
                let t = (cy - y0) / (y1 - y0);
                xs.push(x0 + t * (x1 - x0));
            }
        }
        if xs.len() < 2 {
            continue;
        }
        xs.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        let mut p = 0;
        while p + 1 < xs.len() {
            let (xstart, xend) = (xs[p], xs[p + 1]);
            for i in 0..nx {
                let cx = sheet_min_x + (i as f64 + 0.5) * cw;
                if cx >= xstart && cx <= xend {
                    occ[j * nx + i] = true;
                }
            }
            p += 2;
        }
    }
}

/// Largest border-touching free-component area (mm²) on an occupancy grid (4-neighbour flood-fill).
fn largest_border_free_area_from_occ(occ: &[bool], nx: usize, ny: usize, cell_area: f64) -> f64 {
    let mut seen = vec![false; nx * ny];
    let mut best = 0.0_f64;
    let mut stack: Vec<(usize, usize)> = Vec::new();
    for j0 in 0..ny {
        for i0 in 0..nx {
            if occ[j0 * nx + i0] || seen[j0 * nx + i0] {
                continue;
            }
            stack.clear();
            stack.push((i0, j0));
            seen[j0 * nx + i0] = true;
            let mut cells = 0usize;
            let mut touches_border = false;
            while let Some((i, j)) = stack.pop() {
                cells += 1;
                if i == 0 || j == 0 || i == nx - 1 || j == ny - 1 {
                    touches_border = true;
                }
                flood_push_neighbours(i, j, nx, ny, occ, &mut seen, &mut stack);
            }
            if touches_border {
                best = best.max(cells as f64 * cell_area);
            }
        }
    }
    best
}

/// Bbox `[min_x, min_y, max_x, max_y]` of the largest border-touching free component, or `None`.
fn largest_border_free_slot_from_occ(
    occ: &[bool],
    nx: usize,
    ny: usize,
    sheet_min_x: f64,
    sheet_min_y: f64,
    cw: f64,
    ch: f64,
) -> Option<[f64; 4]> {
    let mut seen = vec![false; nx * ny];
    let mut best_cells = 0usize;
    let mut best_bbox: Option<[f64; 4]> = None;
    let mut stack: Vec<(usize, usize)> = Vec::new();
    for j0 in 0..ny {
        for i0 in 0..nx {
            if occ[j0 * nx + i0] || seen[j0 * nx + i0] {
                continue;
            }
            stack.clear();
            stack.push((i0, j0));
            seen[j0 * nx + i0] = true;
            let (mut imin, mut jmin, mut imax, mut jmax) = (i0, j0, i0, j0);
            let mut cells = 0usize;
            let mut touches_border = false;
            while let Some((i, j)) = stack.pop() {
                cells += 1;
                imin = imin.min(i);
                jmin = jmin.min(j);
                imax = imax.max(i);
                jmax = jmax.max(j);
                if i == 0 || j == 0 || i == nx - 1 || j == ny - 1 {
                    touches_border = true;
                }
                flood_push_neighbours(i, j, nx, ny, occ, &mut seen, &mut stack);
            }
            if touches_border && cells > best_cells {
                best_cells = cells;
                best_bbox = Some([
                    sheet_min_x + imin as f64 * cw,
                    sheet_min_y + jmin as f64 * ch,
                    sheet_min_x + (imax + 1) as f64 * cw,
                    sheet_min_y + (jmax + 1) as f64 * ch,
                ]);
            }
        }
    }
    best_bbox
}

/// Push the 4-neighbour free, unseen cells of `(i, j)` onto the flood-fill stack.
fn flood_push_neighbours(
    i: usize,
    j: usize,
    nx: usize,
    ny: usize,
    occ: &[bool],
    seen: &mut [bool],
    stack: &mut Vec<(usize, usize)>,
) {
    let mut push = |ni: usize, nj: usize| {
        if !occ[nj * nx + ni] && !seen[nj * nx + ni] {
            seen[nj * nx + ni] = true;
            stack.push((ni, nj));
        }
    };
    if i > 0 {
        push(i - 1, j);
    }
    if i + 1 < nx {
        push(i + 1, j);
    }
    if j > 0 {
        push(i, j - 1);
    }
    if j + 1 < ny {
        push(i, j + 1);
    }
}

/// The skeleton role of a critical part on a sheet. Roles mirror the reference LV8 layout: an
/// edge-anchored first part (`Anchor`), a second part interlocked into it (`Interlock`), and a third
/// part placed into the remaining edge-connected free band (`BandInsert`).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SkeletonRole {
    Anchor,
    Interlock,
    BandInsert,
}

impl SkeletonRole {
    pub fn as_str(self) -> &'static str {
        match self {
            SkeletonRole::Anchor => "anchor",
            SkeletonRole::Interlock => "interlock",
            SkeletonRole::BandInsert => "band_insert",
        }
    }
}

/// One admitted critical part on a sheet: which instance, its role, and its world-space bbox
/// (`[min_x, min_y, max_x, max_y]`). The bbox is decision-support geometry for Q54D's free-space
/// proxy; Q54A only records it.
#[derive(Debug, Clone, Copy)]
pub struct AdmittedCritical {
    pub instance_idx: usize,
    pub role: SkeletonRole,
    pub bbox: [f64; 4],
}

/// Per-sheet skeleton state: the ordered list of admitted critical parts on each sheet.
#[derive(Debug, Clone, Default)]
pub struct SheetSkeletonState {
    sheets: Vec<Vec<AdmittedCritical>>,
}

impl SheetSkeletonState {
    pub fn new(n_sheets: usize) -> Self {
        Self {
            sheets: vec![Vec::new(); n_sheets],
        }
    }

    /// Record a successful critical admission on `sheet_idx`.
    pub fn record_admission(
        &mut self,
        sheet_idx: usize,
        instance_idx: usize,
        role: SkeletonRole,
        bbox: [f64; 4],
    ) {
        if let Some(s) = self.sheets.get_mut(sheet_idx) {
            s.push(AdmittedCritical {
                instance_idx,
                role,
                bbox,
            });
        }
    }

    /// Critical parts already admitted on `sheet_idx`.
    pub fn critical_count(&self, sheet_idx: usize) -> usize {
        self.sheets.get(sheet_idx).map_or(0, Vec::len)
    }

    /// An `Anchor` exists that does not yet have a following `Interlock` partner on this sheet —
    /// i.e. the anchor/interlock pair (the reference's two interlocked big parts) is still open.
    pub fn has_open_anchor(&self, sheet_idx: usize) -> bool {
        let Some(s) = self.sheets.get(sheet_idx) else {
            return false;
        };
        let anchors = s.iter().filter(|a| a.role == SkeletonRole::Anchor).count();
        let interlocks = s
            .iter()
            .filter(|a| a.role == SkeletonRole::Interlock)
            .count();
        anchors > interlocks
    }

    /// Admitted critical records on `sheet_idx` (decision-support geometry for Q54D).
    pub fn admitted(&self, sheet_idx: usize) -> &[AdmittedCritical] {
        self.sheets.get(sheet_idx).map_or(&[], Vec::as_slice)
    }

    /// Total role counts across all sheets `(anchor, interlock, band_insert)` — for diagnostics.
    pub fn role_counts(&self) -> (usize, usize, usize) {
        let mut c = (0usize, 0usize, 0usize);
        for s in &self.sheets {
            for a in s {
                match a.role {
                    SkeletonRole::Anchor => c.0 += 1,
                    SkeletonRole::Interlock => c.1 += 1,
                    SkeletonRole::BandInsert => c.2 += 1,
                }
            }
        }
        c
    }
}

/// The minimal profile signals `assign_role` needs. Kept separate from `PartShapeProfile` so the
/// role decision is unit-testable without building a full profile.
#[derive(Debug, Clone, Copy)]
pub struct RoleInputs {
    /// The part can interlock into an anchor (concave / high interlock potential).
    pub interlock_capable: bool,
}

impl RoleInputs {
    pub fn from_profile(p: &PartShapeProfile) -> Self {
        Self {
            interlock_capable: p.is_high_interlock_potential || p.is_concave_like,
        }
    }
}

/// Assign the skeleton role of the next critical candidate from the sheet's current topology and
/// the candidate's profile signals — **never from a per-sheet count target**.
///
/// - `Anchor`    — the sheet has no critical part yet (the edge-anchored first big part).
/// - `Interlock` — there is an open anchor and the candidate can interlock into it (second big part).
/// - `BandInsert`— otherwise (the anchor/interlock pair is closed): a separate edge-connected band.
pub fn assign_role(
    inputs: &RoleInputs,
    state: &SheetSkeletonState,
    sheet_idx: usize,
) -> SkeletonRole {
    if state.critical_count(sheet_idx) == 0 {
        SkeletonRole::Anchor
    } else if state.has_open_anchor(sheet_idx) && inputs.interlock_capable {
        SkeletonRole::Interlock
    } else {
        SkeletonRole::BandInsert
    }
}

#[cfg(test)]
mod skeleton_tests {
    use super::*;

    const SHEET: usize = 0;
    fn bbox() -> [f64; 4] {
        [0.0, 0.0, 100.0, 100.0]
    }
    fn interlocky() -> RoleInputs {
        RoleInputs {
            interlock_capable: true,
        }
    }

    #[test]
    fn empty_sheet_first_critical_is_anchor() {
        let state = SheetSkeletonState::new(2);
        assert_eq!(
            assign_role(&interlocky(), &state, SHEET),
            SkeletonRole::Anchor
        );
    }

    #[test]
    fn three_critical_sequence_is_anchor_interlock_bandinsert() {
        let mut state = SheetSkeletonState::new(1);

        let r0 = assign_role(&interlocky(), &state, SHEET);
        assert_eq!(r0, SkeletonRole::Anchor);
        state.record_admission(SHEET, 0, r0, bbox());

        let r1 = assign_role(&interlocky(), &state, SHEET);
        assert_eq!(r1, SkeletonRole::Interlock);
        state.record_admission(SHEET, 1, r1, bbox());

        let r2 = assign_role(&interlocky(), &state, SHEET);
        assert_eq!(r2, SkeletonRole::BandInsert);
        state.record_admission(SHEET, 2, r2, bbox());

        assert_eq!(state.role_counts(), (1, 1, 1));
        assert_eq!(state.admitted(SHEET).len(), 3);
    }

    #[test]
    fn non_interlock_capable_second_critical_is_bandinsert_not_interlock() {
        // A non-interlock-capable candidate cannot close the anchor pair → band, not interlock.
        let mut state = SheetSkeletonState::new(1);
        let r0 = assign_role(&interlocky(), &state, SHEET);
        state.record_admission(SHEET, 0, r0, bbox());
        let blocky = RoleInputs {
            interlock_capable: false,
        };
        assert_eq!(
            assign_role(&blocky, &state, SHEET),
            SkeletonRole::BandInsert
        );
    }

    #[test]
    fn role_is_independent_of_queue_size() {
        // The same sheet state + candidate → the same role regardless of how many parts remain in
        // any queue (assign_role only sees the sheet state and the candidate signals).
        let state = SheetSkeletonState::new(1);
        let a = assign_role(&interlocky(), &state, SHEET);
        let b = assign_role(&interlocky(), &state, SHEET);
        assert_eq!(a, b);
        assert_eq!(a, SkeletonRole::Anchor);
    }

    #[test]
    fn deterministic_across_repeats() {
        let build = || {
            let mut s = SheetSkeletonState::new(1);
            let mut roles = Vec::new();
            for i in 0..3 {
                let r = assign_role(&interlocky(), &s, SHEET);
                roles.push(r);
                s.record_admission(SHEET, i, r, bbox());
            }
            roles
        };
        assert_eq!(build(), build());
    }

    #[test]
    fn freespace_picks_largest_edge_connected_band_and_excludes_enclosed() {
        // 1000×1000 sheet.
        let (x0, y0, x1, y1) = (0.0, 0.0, 1000.0, 1000.0);
        let full = largest_edge_connected_free_area(&[], x0, y0, x1, y1, 50.0);
        assert!(full > 900_000.0, "empty sheet ≈ full free area, got {full}");

        // A vertical wall splitting the sheet → largest band ≈ one half, not the whole sheet.
        // (Wall wider than the cell so it reliably occupies the central columns.)
        let wall = [[450.0, 0.0, 550.0, 1000.0]];
        let split = largest_edge_connected_free_area(&wall, x0, y0, x1, y1, 50.0);
        assert!(
            split > 400_000.0 && split < full * 0.6,
            "split → largest edge-connected band ≈ one half, got {split} (full {full})"
        );

        // An enclosed inner pocket (a ring leaving a free centre) is NOT edge-connected: the centre
        // is excluded, so the score is the outer band only — smaller than the same area would give
        // if it were one open region. Here the ring occupies a frame, leaving a small centre pocket.
        let ring = [
            [200.0, 200.0, 800.0, 280.0],
            [200.0, 720.0, 800.0, 800.0],
            [200.0, 200.0, 280.0, 800.0],
            [720.0, 200.0, 800.0, 800.0],
        ];
        let with_ring = largest_edge_connected_free_area(&ring, x0, y0, x1, y1, 50.0);
        // the enclosed centre (~440×440 ≈ 193k) must be excluded from the edge-connected score
        assert!(
            with_ring < full - 150_000.0,
            "enclosed centre must be excluded, got {with_ring} (full {full})"
        );
    }

    #[test]
    fn contour_objective_counts_concave_bay_as_free_unlike_bbox() {
        // 1000×1000 sheet. A C-shaped part: the rectangle [200,200]-[800,800] with a notch cut from
        // the right side. The bay (x∈[500,800], y∈[350,650], ~90k mm²) opens to the part's right
        // edge, so its free cells are edge-connected to the sheet's right border through the gap.
        let (x0, y0, x1, y1) = (0.0, 0.0, 1000.0, 1000.0);
        let c_shape: Vec<[f64; 2]> = vec![
            [200.0, 200.0],
            [800.0, 200.0],
            [800.0, 350.0],
            [500.0, 350.0],
            [500.0, 650.0],
            [800.0, 650.0],
            [800.0, 800.0],
            [200.0, 800.0],
        ];
        // The bbox proxy sees the whole [200,200]-[800,800] block as occupied (bay included).
        let bbox = [[200.0, 200.0, 800.0, 800.0]];
        let area_bbox = largest_edge_connected_free_area(&bbox, x0, y0, x1, y1, 50.0);
        let area_contour = largest_edge_connected_free_area_contour(
            std::slice::from_ref(&c_shape),
            x0,
            y0,
            x1,
            y1,
            50.0,
        );
        // The contour proxy frees the bay → materially larger edge-connected residual space.
        assert!(
            area_contour > area_bbox + 50_000.0,
            "contour must count the concave bay as free: contour {area_contour} vs bbox {area_bbox}"
        );

        // The slot variant must also return a (larger or equal) border-touching band.
        let slot_contour = largest_edge_connected_free_slot_contour(
            std::slice::from_ref(&c_shape),
            x0,
            y0,
            x1,
            y1,
            50.0,
        );
        assert!(
            slot_contour.is_some(),
            "contour slot must find a border-touching free band"
        );

        // Sanity: an empty contour set ≈ the full sheet, same as the bbox version with no occupancy.
        let empty: [Vec<[f64; 2]>; 0] = [];
        let full_contour =
            largest_edge_connected_free_area_contour(&empty, x0, y0, x1, y1, 50.0);
        let full_bbox = largest_edge_connected_free_area(&[], x0, y0, x1, y1, 50.0);
        assert!(
            (full_contour - full_bbox).abs() < 1.0,
            "empty contour set must match empty bbox set: {full_contour} vs {full_bbox}"
        );
    }

    #[test]
    fn useful_area_discriminates_anchored_vs_floating_where_plain_area_is_blind() {
        // 1000×1000 sheet, a tall-thin 100×600 part. Anchored to the bottom-left corner vs floating
        // in the middle leaves the SAME plain edge-connected free area (one big wrap-around region),
        // so the plain objective cannot choose between them — exactly the Full276 blindness. The
        // useful (thickness-weighted) objective must prefer the anchored placement: floating puts the
        // obstacle in the interior so its low-distance "shadow" radiates in all directions, thinning
        // the residual; anchoring confines that shadow to one corner, keeping the open space thick.
        let (x0, y0, x1, y1) = (0.0, 0.0, 1000.0, 1000.0);
        let corner: Vec<[f64; 2]> =
            vec![[0.0, 0.0], [100.0, 0.0], [100.0, 600.0], [0.0, 600.0]];
        let floating: Vec<[f64; 2]> =
            vec![[450.0, 200.0], [550.0, 200.0], [550.0, 800.0], [450.0, 800.0]];

        let area_corner =
            largest_edge_connected_free_area_contour(std::slice::from_ref(&corner), x0, y0, x1, y1, 50.0);
        let area_floating =
            largest_edge_connected_free_area_contour(std::slice::from_ref(&floating), x0, y0, x1, y1, 50.0);
        // Plain area is (near) blind: both leave one connected ~940k region.
        assert!(
            (area_corner - area_floating).abs() < 20_000.0,
            "plain area must be ~equal (blind): corner {area_corner} vs floating {area_floating}"
        );

        let useful_corner =
            useful_free_area_contour(std::slice::from_ref(&corner), x0, y0, x1, y1, 50.0, 6);
        let useful_floating =
            useful_free_area_contour(std::slice::from_ref(&floating), x0, y0, x1, y1, 50.0, 6);
        // Useful discriminates: anchoring to the corner keeps the residual thicker.
        assert!(
            useful_corner > useful_floating + 50_000.0,
            "useful must prefer anchored: corner {useful_corner} vs floating {useful_floating}"
        );
    }
}
