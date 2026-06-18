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
}
