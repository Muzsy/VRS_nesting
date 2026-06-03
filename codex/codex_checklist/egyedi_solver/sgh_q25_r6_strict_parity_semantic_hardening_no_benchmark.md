# Checklist — SGH-Q25-R6 Strict parity semantic hardening

## Scope / hygiene

- [x] Read `AGENTS.md`, Codex docs, Q25-R5 report, and relevant upstream `.cache/sparrow` files.
- [x] Record `.cache/sparrow` commit hash: `c95454e390276231b278c879d25b39708398b7d3`.
- [x] Record `.cache/sparrow` status: clean.
- [x] Record `git status --porcelain=v1` before editing.
- [x] Record `git diff --name-only` before editing.
- [x] List pre-existing dirty files separately in the report.
- [x] Do not modify out-of-scope implementation files.
- [x] End with `OUT_OF_SCOPE_NEW_CHANGES: NONE`.

## Convex-hull large-item disruption

- [x] Add explicit `large_item_disruption_area_key` helper.
- [x] Use convex-hull area as the normal strict large-item disruption area key.
- [x] Use cumulative convex-hull area for the 0.75 large-item cutoff.
- [x] Remove normal-path `inst.part.width * inst.part.height` bbox-area cutoff/ranking from `select_large_item_swap_pair`.
- [x] Keep bbox fallback only for shape-preparation failure.
- [x] Add irregular/non-rectangular test where bbox area and convex hull area diverge.
- [x] Add/verify `strict_large_item_disruption_uses_convex_hull_area_not_bbox_area`.
- [x] Add/verify `strict_large_item_cutoff_uses_cumulative_convex_hull_area_percentile`.
- [x] Add/verify `strict_large_item_bbox_fallback_is_only_for_unprepared_shape`.

## Strict touching / boundary edge cases

- [x] Pair edge touching is collision in `SparrowStrict`.
- [x] Pair corner touching is collision in `SparrowStrict`.
- [x] Pair edge/corner touching is clear only under explicit `VrsTouchAllowed`.
- [x] Strict exact boundary fit / boundary touching is not feasible.
- [x] Strict epsilon-inside boundary placement is feasible.
- [x] Strict epsilon-outside boundary placement is collision/infeasible.
- [x] Tests exercise the real strict CDE/tracker/evaluator path, not fake-only helpers.
- [x] Add/verify `strict_pair_edge_touching_is_collision`.
- [x] Add/verify `strict_pair_corner_touching_is_collision`.
- [x] Add/verify `vrs_touch_allowed_pair_edge_and_corner_touching_are_clear`.
- [x] Add/verify `strict_boundary_exact_fit_is_not_feasible`.
- [x] Add/verify `strict_boundary_epsilon_inside_is_feasible`.
- [x] Add/verify `strict_boundary_epsilon_outside_is_collision`.

## Upstream mapping audit

- [x] Read and map `.cache/sparrow/src/optimizer/explore.rs`.
- [x] Read and map `.cache/sparrow/src/optimizer/worker.rs`.
- [x] Read and map `.cache/sparrow/src/optimizer/separator.rs`.
- [x] Read and map `.cache/sparrow/src/sample/search.rs`.
- [x] Read and map `.cache/sparrow/src/optimizer/lbf.rs`.
- [x] Read and map `.cache/sparrow/src/eval/sep_evaluator.rs`.
- [x] Read and map `.cache/sparrow/src/eval/lbf_evaluator.rs`.
- [x] Read and map `.cache/sparrow/src/consts.rs::LBF_SAMPLE_CONFIG`.
- [x] Read and map `.cache/sparrow/src/config.rs::DEFAULT_SPARROW_CONFIG`.
- [x] Mark each mapping row as `PORTED`, `ADAPTED_FIXED_SHEET`, or `DEFERRED_COMPRESSION` as applicable.
- [x] Do not mark true core gaps as fixed-sheet adaptations.

## Q25-R5 invariant preservation

- [x] `SparrowStrictParity` exists and remains the parity/default strict profile.
- [x] `CdeTouchingPolicy::{SparrowStrict,VrsTouchAllowed}` exists.
- [x] Strict LBF = 1000/0/3.
- [x] Strict separator = 50/25/3.
- [x] Strict separator loop = 200/3.
- [x] Strict worker count = 3.
- [x] Strict instance-count downscaling remains disabled.
- [x] Strict worker ordering remains RNG shuffle only.
- [x] No compression is added.
- [x] No LV8 quality benchmark acceptance is added.

## Regression prevention

- [x] No `WorkingLayout` in `optimizer/sparrow`.
- [x] No `VrsCollisionTracker` in `optimizer/sparrow`.
- [x] No bbox/AABB/proxy ranking added to LBF or separation.
- [x] No legacy fallback production path added to native Sparrow strict profile.

## Report

- [x] Add all required Q25-R6 report sections.
- [x] Include exact PASS tokens only after source/tests/gates prove them.
- [x] Include upstream commit and mapping table.
- [x] Include changed file list and build/test/gate results.

## Verification

- [x] Run `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release`.
- [x] Run `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`.
- [x] Run `python3 scripts/smoke_sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.py`.
- [x] Run `./scripts/check.sh`.
- [x] Run `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md`.
