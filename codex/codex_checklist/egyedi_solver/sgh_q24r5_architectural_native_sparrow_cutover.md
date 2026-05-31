# SGH-Q24R5 checklist — Architectural native Sparrow cutover

## A. Mandatory starting evidence

- [ ] Read Q24R4 report: `codex/reports/egyedi_solver/sgh_q24r4_native_sparrow_model_cutover.md`.
- [ ] Read Q24R4 cutover map: `docs/egyedi_solver/sgh_q24r4_native_sparrow_model_cutover_map.md`.
- [ ] Read `.cache/sparrow` reference files:
  - [ ] `.cache/sparrow/src/optimizer/mod.rs`
  - [ ] `.cache/sparrow/src/optimizer/separator.rs`
  - [ ] `.cache/sparrow/src/optimizer/worker.rs`
  - [ ] `.cache/sparrow/src/optimizer/explore.rs`
  - [ ] `.cache/sparrow/src/sample/search.rs`
  - [ ] `.cache/sparrow/src/quantify/tracker.rs`
- [ ] Skim `.cache/sparrow/src/optimizer/compress.rs` only to keep it out of scope.

## B. Native module cut

- [ ] Replace the production `rust/vrs_solver/src/optimizer/sparrow.rs` implementation with a native module tree or equivalent real split.
- [ ] Old Q24R3/Q24R4 `SparrowSeparationKernel` code is removed from production `sparrow_cde` or quarantined as legacy-only.
- [ ] Native production modules define and use:
  - [ ] `SparrowProblem`
  - [ ] `SPInstance`
  - [ ] `SparrowPlacement`
  - [ ] `SparrowLayout`
  - [ ] `SparrowSolution`
  - [ ] `SparrowCollisionTracker`
  - [ ] `SparrowOptimizer`
  - [ ] `SparrowSolveResult`

## C. Production path cutover

- [ ] `run_sparrow_pipeline` no longer calls `WorkingLayout::new`.
- [ ] `run_sparrow_pipeline` no longer imports `SparrowSeparationKernel` or `build_constructive_seed_layout`.
- [ ] `run_sparrow_pipeline` constructs `SparrowProblem` and calls `SparrowOptimizer::solve`.
- [ ] Projection to `crate::io::Placement` happens only after native solve completion.
- [ ] Legacy fallback / LBF fallback / phase optimizer / multisheet manager is not reachable from production `sparrow_cde`.

## D. Native data model

- [ ] `SparrowProblem` owns or references sheets, parts, rotation policy, seed, time budget, and expanded instances.
- [ ] `SPInstance` has stable native index and external `instance_id` mapping.
- [ ] `SparrowPlacement` is not `crate::io::Placement` and does not embed it.
- [ ] `SparrowLayout` indexes placements by `SPInstance` index/key.
- [ ] `SparrowSolution` can project to `Vec<crate::io::Placement>` only at the output boundary.
- [ ] Pre-unplaced/never-fits cases are represented without silently dropping instances.

## E. Native tracker and CDE truth

- [ ] `SparrowCollisionTracker` is not a wrapper around `VrsCollisionTracker`.
- [ ] It owns pair collision records, boundary/container records, raw loss, weighted loss, per-item loss, and GLS weights.
- [ ] It uses `prepare_shape_native`, `prepare_shape_from_sheet`, `CdeAdapter::query_pair`, `CdeAdapter::query_boundary`, and/or native candidate-session helpers.
- [ ] It supports full rebuild, update-after-move, snapshot/restore, and final validation.
- [ ] Bbox is allowed only as broad-phase/no-collision pruning, never as positive collision truth or decisive production loss.

## F. Native lifecycle

- [ ] Initial solution builder creates native `SparrowLayout` / `SparrowSolution`.
- [ ] `separate` operates on native layout/tracker.
- [ ] `move_items_multi` and workers operate on native snapshots.
- [ ] Search samples native `SparrowPlacement` candidates and evaluates them with native tracker/CDE state.
- [ ] Exploration pool/restore/disruption stores native solution/state, not `WorkingLayout` snapshots.
- [ ] Compression stays disabled/gated and is not needed for PASS.

## G. Diagnostics and gates

- [ ] Add diagnostics fields proving native model activity, e.g. `sparrow_native_model_active`, `sparrow_native_tracker_active`, `sparrow_old_core_used`.
- [ ] Add `scripts/smoke_sgh_q24r5_architectural_native_sparrow_cutover.py`.
- [ ] Static smoke rejects old core tokens in production `optimizer/sparrow` and `run_sparrow_pipeline`.
- [ ] Runtime smoke verifies production `sparrow_cde` with CDE backend, 12/12 medium, final pairs 0, boundary 0, no fallback, no compression.

## H. Required commands

- [ ] `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release`
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`
- [ ] `python3 scripts/smoke_sgh_q24r5_architectural_native_sparrow_cutover.py`
- [ ] `./scripts/check.sh`

## Reject conditions

Reject if any is true:

- [ ] production `sparrow_cde` still creates `WorkingLayout` before solve;
- [ ] production `sparrow_cde` still uses `VrsCollisionTracker`;
- [ ] new native types are wrappers/aliases over old VRS core types;
- [ ] `crate::io::Placement` remains the internal layout placement type;
- [ ] old `SparrowSeparationKernel` remains the production solve engine;
- [ ] task is mainly docs/reports/scripts;
- [ ] task returns another Q24R4-style map-only REVISE;
- [ ] medium gate passes via legacy fallback, LBF fallback, bbox truth, or compression.
