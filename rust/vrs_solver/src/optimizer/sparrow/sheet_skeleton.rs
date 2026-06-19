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
    let w = sheet_max_x - sheet_min_x;
    let h = sheet_max_y - sheet_min_y;
    if w <= 0.0 || h <= 0.0 || cell_mm <= 0.0 {
        return 0.0;
    }
    let nx = ((w / cell_mm).ceil() as usize).clamp(1, 400);
    let ny = ((h / cell_mm).ceil() as usize).clamp(1, 400);
    let cw = w / nx as f64;
    let ch = h / ny as f64;
    // occupancy: a cell is occupied if its centre falls inside any occupied bbox.
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
    // connected components of free cells (4-neighbour); track area + whether it touches the border.
    let cell_area = cw * ch;
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
                let mut push = |ni: usize, nj: usize, st: &mut Vec<(usize, usize)>, seen: &mut [bool]| {
                    if !occ[nj * nx + ni] && !seen[nj * nx + ni] {
                        seen[nj * nx + ni] = true;
                        st.push((ni, nj));
                    }
                };
                if i > 0 {
                    push(i - 1, j, &mut stack, &mut seen);
                }
                if i + 1 < nx {
                    push(i + 1, j, &mut stack, &mut seen);
                }
                if j > 0 {
                    push(i, j - 1, &mut stack, &mut seen);
                }
                if j + 1 < ny {
                    push(i, j + 1, &mut stack, &mut seen);
                }
            }
            if touches_border {
                best = best.max(cells as f64 * cell_area);
            }
        }
    }
    best
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
    let w = sheet_max_x - sheet_min_x;
    let h = sheet_max_y - sheet_min_y;
    if w <= 0.0 || h <= 0.0 || cell_mm <= 0.0 {
        return None;
    }
    let nx = ((w / cell_mm).ceil() as usize).clamp(1, 400);
    let ny = ((h / cell_mm).ceil() as usize).clamp(1, 400);
    let cw = w / nx as f64;
    let ch = h / ny as f64;
    let mut occ = vec![false; nx * ny];
    for j in 0..ny {
        let cy = sheet_min_y + (j as f64 + 0.5) * ch;
        for i in 0..nx {
            let cx = sheet_min_x + (i as f64 + 0.5) * cw;
            if occupied.iter().any(|b| cx >= b[0] && cx <= b[2] && cy >= b[1] && cy <= b[3]) {
                occ[j * nx + i] = true;
            }
        }
    }
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
                let mut push = |ni: usize, nj: usize, st: &mut Vec<(usize, usize)>, seen: &mut [bool]| {
                    if !occ[nj * nx + ni] && !seen[nj * nx + ni] {
                        seen[nj * nx + ni] = true;
                        st.push((ni, nj));
                    }
                };
                if i > 0 {
                    push(i - 1, j, &mut stack, &mut seen);
                }
                if i + 1 < nx {
                    push(i + 1, j, &mut stack, &mut seen);
                }
                if j > 0 {
                    push(i, j - 1, &mut stack, &mut seen);
                }
                if j + 1 < ny {
                    push(i, j + 1, &mut stack, &mut seen);
                }
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
        let interlocks = s.iter().filter(|a| a.role == SkeletonRole::Interlock).count();
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
pub fn assign_role(inputs: &RoleInputs, state: &SheetSkeletonState, sheet_idx: usize) -> SkeletonRole {
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
        RoleInputs { interlock_capable: true }
    }

    #[test]
    fn empty_sheet_first_critical_is_anchor() {
        let state = SheetSkeletonState::new(2);
        assert_eq!(assign_role(&interlocky(), &state, SHEET), SkeletonRole::Anchor);
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
        let blocky = RoleInputs { interlock_capable: false };
        assert_eq!(assign_role(&blocky, &state, SHEET), SkeletonRole::BandInsert);
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
}
