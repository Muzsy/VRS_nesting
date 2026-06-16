# SGH-Q48 — Interlocking-aware density compaction

## Goal

Make the placement **search** discover and keep **bbox-overlapping / polygon-clear (interlocked)**
configurations, by replacing the current bottom-left / y-only density mechanism with a real
**density objective + contour-aware sampling**, CDE-validated. This is the density lever that
SGH-Q47 proved is missing (Q47 A==B: ordering+budget are outcome-neutral; the gap is in the
*search*, not item priority).

**Honest framing.** This is the highest-uncertainty, R&D step of the programme. The realistic
deliverable is a working density mechanism that **demonstrably generates + keeps interlock
candidates** and tightens layouts; **sheet-count reduction (2 sheets) is a stretch goal, not a
guarantee.** The plan is measure-driven: a decision-diagnostic gate after T1–T3 tells us whether we
generate interlock candidates at all before investing in the full compaction.

## Non-goals (hard constraints, from the conversation)

- **Continuous rotation stays continuous** — the search keeps continuous rotational freedom
  (`coord_descent` already rotates continuous parts continuously); no discrete-degree snapping.
- **No NFP** — contour-aware sampling means sampling *near a neighbour's vertices/edges*, NOT
  computing a no-fit polygon.
- **CDE stays the collision truth** — the density score only *steers* the search.
- **No compression as a main motor** — the M3 `compress_layout`/`strip_compress_fit` (default off)
  stay a deprecated experiment; Q48 does not build on them.
- **No prediction / cluster forcing / per-sheet part count.** Cavity stays in prepack (outer
  contour only).
- **Default OFF** — gated by `VRS_BPP_DENSITY_COMPACT` (=1 to enable); production unchanged.

## Approach (verified code hooks)

| hook | file | role in Q48 |
| --- | --- | --- |
| `LBFEvaluator::score_lbf_candidate` bottom-left score | `eval/lbf_evaluator.rs:72` | parallel `DensityEvaluator` rewards interlock instead |
| `compact_sheet` y-only accept (`pl.y < old.y`) | `bpp_reduction.rs:649` | replaced by density-improving accept |
| `UniformBBoxSampler::sample` uniform random | `sample/uniform_sampler.rs:81` | + sample near placed neighbours' contour |
| pole-based `overlap_area_proxy` | `quantify/overlap_proxy.rs:59` | smooth proximity/contact gradient (attraction) |
| `fitting_rotation` discrete seed | `fixed_sheet.rs:7` | continuous-correct seed for continuous parts |

**Density score** (minimise): `w_extent · added_used_extent(part) − w_contact · proximity(part,
neighbours)`. `added_used_extent` = growth of the sheet's used bounding extent when the part is
placed (a part tucked into a concavity grows it little); `proximity` = pole/centroid closeness to
neighbours (contact reward). Smooth ⇒ coord-descent-able; collision-free decided by the CDE.

## Task breakdown

- **T1** `DensityEvaluator` + density-score (added-extent + attraction term) + unit tests proving an
  interlocked (in-concavity) placement scores better than a separated one.
- **T2** Interlock decision-diagnostics: count bbox-overlap/polygon-clear candidates generated +
  accepted per sheet (the measurement gate).
- **T3** Density-aware sampling: also draw samples near placed neighbours' contour.
- **(measure gate)** does the mechanism generate interlock candidates on the 6×`Lv8_11612`
  *mechanism* fixture (a unit-level check, NOT a proving benchmark)? If not, stop & rethink.
- **T4** Density-compaction pass replacing the y-only `compact_sheet` accept (translation +
  continuous rotation), gated `VRS_BPP_DENSITY_COMPACT`.
- **T5** Continuous-rotation seed correctness (`fitting_rotation` honours `continuous_rotation`).
- **T6** Tests (unit + integration; existing suites stay green).
- **T7** A/B regression + decision-diagnostic benchmark (density-compact ON vs OFF, full276 +
  fixtures): acceptance = valid + no sheet/util regression + interlock candidates generated; stretch
  = tighter extent / fewer sheets.
- **T8** verify + report + checklist.

## Acceptance criteria

- CDE collision pipeline unchanged; no NFP; no bbox shortcut; continuous rotation still continuous;
  cavity/holes not in the main solver; `VRS_BPP_DENSITY_COMPACT=0` reproduces pre-Q48 behaviour.
- Output valid; decision-diagnostics show whether interlock candidates are generated/accepted.
- full276 LV8 does not regress in sheet-count or validity with the pass enabled.
- Deterministic.

## Risks

- **Primary:** the 3-curved-part interlock may need *coordinated multi-part* motion that single-part
  density compaction cannot find. T7 measures this; if so, multi-part LNS is a separate later task.
  **No 2-sheet promise.**
- Score-weight tuning (`w_extent`/`w_contact`) is A/B-driven.
- All gated (default off) ⇒ no production regression, no IO-contract break.

## Status

Planned. T1 in progress. Stacked on `sgh-q47-shape-profile-priority-layer` (Q47 not yet merged).
