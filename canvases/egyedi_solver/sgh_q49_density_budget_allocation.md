# SGH-Q49 — Budget allocation for the density compaction pass

## Goal

Fix the SGH-Q48 budget-starvation finding: the interlock-aware density compaction pass is gated to
the time left *after* the BPP sheet-reduction, which consumes the whole budget on full276 — so the
pass only reaches a few parts (full276: 20 interlock generated / 2 accepted, vs the focused
6×`Lv8_11612` fixture: 189 / 4 where the reduction finished early). Q49 gives the density pass a
**reserved time budget** and makes its per-part search **efficient enough that a full sweep over all
276 parts fits** in that budget.

**Honest framing (unchanged).** Q49 does **not** promise 2 sheets. Its goal is that the density pass
**actually runs on all parts** within the budget and measurably accepts more interlock moves /
tightens the layout. If single-part greedy density at full budget still does not reduce the sheet
count, the next lever is coordinated **multi-part LNS (SGH-Q50)**.

## Root cause (verified)

- The reduction loop runs until `total_budget − guard` (`bpp_reduction.rs:1383`).
- `density_deadline = total_budget − guard` (`bpp_reduction.rs:1473`).
- ⇒ on full276 the reduction consumes the budget and density starts at ≈ its own deadline (≈ 0 s);
  on the 6-big fixture the reduction finishes early so density has time. Same code, opposite
  outcome — purely a budget-allocation problem.

## Non-goals (hard constraints)

- Continuous stays continuous; CDE is the collision truth; no NFP / bbox shortcut / clustering /
  per-sheet prediction; cavity stays in prepack.
- **Gated, default OFF** — everything behind `VRS_BPP_DENSITY_COMPACT`; the new knobs are inert when
  off, and the budget reservation collapses to the pre-Q49 deadlines (`frac = 0`).
- Deterministic; additive IO; no production regression.

## Approach

1. **Budget reservation (T1).** New `VRS_BPP_DENSITY_BUDGET_FRAC` (default 0.35, active only when
   density is on). Cap the reduction loop at `total_budget·(1−frac) − guard`; keep
   `density_deadline = total_budget − guard` so the pass gets the reserved ≈ frac. When density is
   off, `frac = 0` ⇒ reduction deadline unchanged. Add reduction/density time-split diagnostics.
2. **Per-part efficiency (T2).** Replace the per-part full `SparrowCollisionTracker::build` in
   `density_compact_sheet` with an incremental update (build once per sweep, update only the moved
   part's `tracker.shapes[li]`, which is all `build_sheet_session` reads). Add a tunable, bounded
   candidate budget (`VRS_BPP_DENSITY_SAMPLES`), prioritise contour samples, and early-exit when no
   improvement — so a full sweep over all parts fits in the reserved budget.
3. **Multi-sweep (T3).** Repeat density sweeps until convergence (no accepted move) or the deadline.

## Task breakdown

- **T1** Budget reservation + reduction-deadline cap + time-split diagnostics.
- **T2** Per-part efficiency: incremental tracker + tunable candidate budget + early-exit.
- **T3** Multi-sweep loop until convergence/deadline; sweep/parts-processed diagnostics.
- **T4** Tests (budget split honoured; density processes all parts on a small fixture; default-off
  unchanged; deterministic).
- **T5** A/B re-benchmark full276 (density on with reservation) vs Q48-starved vs off:
  parts_processed, sweeps, interlock accepted, utilization, used_sheets.
- **T6** verify + report + checklist.

## Acceptance criteria

- `VRS_BPP_DENSITY_COMPACT=0` reproduces pre-Q49 behaviour exactly; CDE/rotation/NFP guardrails held.
- With density on, the pass runs across (most/all of) the 276 parts within the reserved budget
  (diagnostics: parts_processed, sweeps, density_time_ms) and does **not** regress sheet-count or
  validity vs off.
- Deterministic.

## Risks

- Capping the reduction *could* in rare cases drop a late elimination — measured in T5; `frac` is
  tunable and off-path is unaffected.
- Full budget does not guarantee sheet reduction (single-part greedy) — **no 2-sheet promise**; the
  lever beyond is SGH-Q50 (multi-part LNS).

## Status

Planned. T1 in progress. Stacked on `sgh-q48-interlocking-density-compaction`.
