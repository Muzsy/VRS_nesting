# SGH-Q50 — Density-guided LNS "sheet-drop" pass

## Goal

Attack the last gap the programme isolated: SGH-Q49 proved the density compaction now runs at full
scale (full276: 480 interlock moves accepted) but stays at 3 sheets, because **single-part greedy
compaction tightens within a sheet but cannot create the deep coordinated 3-curved-parts-per-sheet
interlock** that drops a sheet. Q50 adds a **standalone, gated, ruin-recreate Large Neighborhood
Search (LNS)** that — after the reduction + density compaction — tries to **drop one more sheet** by
moving a whole sheet's parts *together* onto the others, via density-guided interlock insertion +
receiving-sheet density compaction.

**Honest framing (the programme's hardest, most uncertain step).** LNS is the standard NFP-free tool
and the **best shot at 2 sheets**, but it is **stochastic and not guaranteed** — the big curved-part
interlock is the hard case. Deliverable: a working density-LNS that **demonstrably attempts
coordinated multi-part sheet elimination** (and drops a sheet on a constructed fixture where it is
possible), measured on full276, with **safe revert** (restores the layout if it cannot drop a
sheet), gated, no regression. Sheet reduction on full276 is the real (unpromised) target.

## Why single-part wasn't enough (Q49 finding)

`utilization = placed_part_area ÷ (used_sheet_count × sheet_area)` is invariant to within-sheet
tightening; only a **sheet-count drop** moves it. Q49 accepted 497 within-sheet moves yet stayed 3
sheets. Dropping a sheet requires re-homing a whole sheet's parts at once — a coordinated
(multi-part) move, which LNS provides.

## Non-goals (hard constraints)

- Continuous stays continuous; CDE is the collision truth; no NFP / bbox shortcut / clustering /
  per-sheet prediction; cavity stays in prepack.
- **Default OFF** (`VRS_BPP_LNS`); off ⇒ pre-Q50 behaviour exactly. Deterministic (fixed seed +
  deterministic restart order); additive IO.
- **Feasibility-preserving** — an LNS attempt is accepted only if *every* ruined part is re-placed
  feasibly on *fewer* sheets; otherwise the whole attempt is reverted.

## Mechanism (ruin-recreate)

1. Pick the **least-utilized** used sheet `S`.
2. **Ruin** — remove all parts on `S`.
3. **Recreate** — insert them (priority order) into the other used sheets via density-guided
   interlock insertion (Q48 contour sampling + density score), compacting the receiving sheets (Q49
   `density_compact_sheet`) to make room; a few **perturbed restarts** to escape local optima.
4. If all fit without `S` ⇒ **accept** (sheet dropped); else **revert**.
5. Repeat on the next-least sheet while budget remains.

## Task breakdown

- **T1** `density_insert_part(part, target_sheet)` — density-guided insertion of a not-yet-placed
  part onto a chosen sheet (best clear interlock position) + unit test.
- **T2** `lns_sheet_drop` ruin-recreate pass (gated `VRS_BPP_LNS`, default off): ruin the least-full
  sheet, recreate into the rest via T1 + `density_compact_sheet`, perturbed restarts
  (`VRS_BPP_LNS_RESTARTS`, default 4), full revert on failure; runs after the density compaction.
- **T3** Diagnostics: `bpp_lns_applied`, `bpp_lns_attempts`, `bpp_lns_sheets_dropped`,
  `bpp_lns_parts_reinserted`, `bpp_lns_restarts`.
- **T4** Tests: LNS drops a sheet on a constructed fixture where it is possible; safe revert when
  not; `VRS_BPP_LNS=0` unchanged; deterministic; existing suites green.
- **T5** A/B benchmark full276 (LNS on/off): used_sheets, sheets_dropped, attempts/restarts,
  utilization, validity.
- **T6** verify + report + checklist.

## Acceptance criteria

- `VRS_BPP_LNS=0` reproduces pre-Q50 behaviour; CDE/rotation/NFP guardrails held.
- LNS drops a sheet on the constructed positive fixture; reverts safely on the negative one.
- full276 with LNS on does **not** regress validity/sheet-count; the pass demonstrably attempts
  elimination (attempts > 0). Sheet reduction to 2 is a stretch goal, not promised.
- Deterministic.

## Risks

- full276 may still not drop the 3rd sheet (hard curved-part interlock) — measured in T5; **no
  2-sheet promise**. If not, the next steps are: integrate the LNS into the reduction attempts, a
  larger neighborhood, or targeted part-pair interlock seeding.
- LNS stochasticity ⇒ determinism preserved via fixed seed + deterministic restart order.
- Gated default-off + full revert ⇒ no production regression.

## Status

Planned. T1 in progress. Stacked on `sgh-q49-density-budget-allocation` (now also on `main`).
