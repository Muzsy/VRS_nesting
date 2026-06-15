# SGH-Q47 — Shape Profile Priority Layer for the VRS Sparrow/BPP solver

## Goal

Introduce a cheap, deterministic **per-part-type shape-profile metadata layer** that informs the
existing jagua-rs / Sparrow / CDE + BPP solver's *decisions* — without changing the collision
engine, without NFP, without a bbox collision shortcut, and without clustering or any predicted
per-sheet part count. The concrete target is to make the solver **less flat**: large/structurally
hard (concave, slender, low-fill) parts should claim space *before* easily-placed tiny fillers.

This is the **prioritisation half** of the agreed two-part goal (the *interlocking-search* half —
density compact rewrite + continuous bootstrap — is deferred to SGH-Q48/Q49). On its own this
increment is not expected to reach the 2-sheet LV8 result; its acceptance is *no regression* plus
*decision-diagnostics that prove the priority actually changed*.

## Non-goals (hard constraints)

- No internal holes / cavities (the main solver always receives an outer contour only).
- **Continuous rotation stays continuous.** Shape-profile angle-sensitive metrics (`min_dim`,
  `slenderness`) are one-time descriptors and must NEVER leak into a continuous part's placement
  rotation. The diff touches no rotation/sampler code.
- No NFP, no bbox collision decision, no `exact_rectangle` rect shortcut (first round).
- No part-pair compatibility matrix, no cluster builder, no "this family needs 3/sheet" prediction.
- No `part_id`-specific behaviour — only general shape metrics.

## Approach (VRS code integration points, all verified)

A `PartShapeProfile` is computed **once per unique `part_id`** alongside the existing
`base_shape_cache` in `model.rs::from_solver_input`, reusing existing helpers:
`part_polygon_area` (true area), `convex_hull_area_and_diameter` (hull area + diameter via the same
`transform_base_to_candidate` path as `lbf_order_key`), and `Part.width/height/quantity`. It is
attached to each `SPInstance` via an `Rc<PartShapeProfile>`.

The profile feeds five decision points (gated by `VRS_SHAPE_PROFILE`, default on):

1. **Construction / LBF ordering** — `lbf.rs::lbf_order_key`: primary key = `priority_score`,
   tie-break = existing `convex_hull_area × diameter`, then `instance_id` (determinism).
2. **BPP redistribution / compaction order** — `bpp_reduction.rs` displaced-sort and compact-sort:
   `priority_score` instead of raw `instance_area` (heavy parts first, tiny fillers last).
3. **Placement budget** — `bpp_reduction.rs::search_placement_on_sheet` per-placement deadline
   scaled by `search_budget_multiplier` (large concave anchors get more, tiny fillers less).
4. **Decision diagnostics** — per-part `ShapeProfileDiagnostics` (classes, priority_score,
   placement_order_rank, budget_multiplier, candidate/accepted counts, rejection summary).
5. (Density compact scoring 8.5 is **deferred** to SGH-Q48.)

## Deliverables

- `rust/vrs_solver/src/optimizer/sparrow/shape_profile.rs` (new module).
- `model.rs` (profile cache + `SPInstance.shape_profile`), `lbf.rs`, `bpp_reduction.rs` wiring.
- `io.rs` `ShapeProfileDiagnostics` + `OptimizerDiagnosticsOutput.shape_profiles`, adapter wiring.
- `rust/vrs_solver/tests/sparrow_shape_profile.rs` (deterministic compute, classification,
  ordering change, no-collision-semantics-change, continuous guardrail) + green existing suite.
- `scripts/bench_sgh_q47_shape_profile_full276.py` (A/B `VRS_SHAPE_PROFILE=0|1` regression).
- `artifacts/benchmarks/sgh_q47/`, report + checklist.

## Acceptance criteria (canvas §10)

- CDE collision pipeline unchanged; no bbox shortcut; continuous rotation still continuous;
  no cavity/hole info in the main solver.
- Output valid; profile actually changes ordering/budget (visible in diagnostics: heavy/slender/
  concave ranked earlier, tiny fillers later).
- LV8 full276 does **not** regress in sheet-count or validity. Change is deterministic.
- `VRS_SHAPE_PROFILE=0` reproduces the pre-Q47 behaviour exactly.

## Task breakdown

- **T1** PartShapeProfile module + per-type compute + `SPInstance` field.
- **T2** Decision diagnostics (`ShapeProfileDiagnostics`, output wiring).
- **T3** Profile-aware ordering (LBF construction + BPP redistribution/compaction).
- **T4** Profile-aware placement budget (medium risk; after T2/T3 diagnostics).
- **T5** Tests. **T6** A/B regression benchmark. **T7** verify + report + checklist.

## Status

Planned. T1 in progress.
