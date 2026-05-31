# SGH-Q24R6 checklist — Native Sparrow tracker + search parity hardening

## A. Mandatory starting evidence

- [ ] Read Q24R5 report: `codex/reports/egyedi_solver/sgh_q24r5_architectural_native_sparrow_cutover.md`.
- [ ] Read Q24R5 verify log: `codex/reports/egyedi_solver/sgh_q24r5_architectural_native_sparrow_cutover.verify.log`.
- [ ] Read Q24R5 smoke script: `scripts/smoke_sgh_q24r5_architectural_native_sparrow_cutover.py`.
- [ ] Read current native Sparrow core: `rust/vrs_solver/src/optimizer/sparrow/mod.rs` or split modules under `rust/vrs_solver/src/optimizer/sparrow/`.
- [ ] Read adapter projection: `rust/vrs_solver/src/adapter.rs`, especially `run_sparrow_pipeline` and native diagnostics projection.
- [ ] Read CDE helpers: `rust/vrs_solver/src/optimizer/cde_adapter.rs` and `rust/vrs_solver/src/optimizer/collision_severity.rs`.
- [ ] Read local Sparrow reference files:
  - [ ] `.cache/sparrow/src/optimizer/mod.rs`
  - [ ] `.cache/sparrow/src/optimizer/separator.rs`
  - [ ] `.cache/sparrow/src/optimizer/worker.rs`
  - [ ] `.cache/sparrow/src/optimizer/explore.rs`
  - [ ] `.cache/sparrow/src/sample/search.rs`
  - [ ] `.cache/sparrow/src/quantify/tracker.rs`
- [ ] Skim `.cache/sparrow/src/optimizer/compress.rs` only to keep compression out of scope.

## B. Preserve Q24R5 architecture

- [ ] Production `sparrow_cde` still constructs `SparrowProblem`.
- [ ] Production `sparrow_cde` still calls `SparrowOptimizer::solve`.
- [ ] Production `sparrow_cde` still projects `SparrowSolution` to VRS output only at the boundary.
- [ ] No `WorkingLayout`, `VrsCollisionTracker`, `SparrowSeparationKernel`, `PhaseOptimizer`, or `MultiSheetManager` inside production `optimizer/sparrow`.
- [ ] `crate::io::Placement` is not used as native internal layout state.

## C. Native tracker parity hardening

- [ ] `SparrowCollisionTracker` still owns native pair records, boundary/container records, GLS weights, prepared shapes, and sheet shapes.
- [ ] Pair loss is not a binary count proxy (`1.0` per collision). It is CDE-truth quantified loss, preferably separation/resolution distance or equivalent deterministic severity.
- [ ] Boundary/container loss is not a binary count proxy. It is quantified by CDE-truth boundary/container clearance/separation or equivalent deterministic severity.
- [ ] Search and tracker ranking use the same quantified loss semantics or a clearly documented compatible split.
- [ ] GLS weights multiply quantified pair/boundary losses.
- [ ] Full rebuild recomputes all loss records.
- [ ] Incremental update recomputes all records touching the moved item and preserves unrelated records/weights.
- [ ] Snapshot/restore preserves or intentionally handles GLS weights according to Sparrow-like semantics.
- [ ] Final validation does a full CDE rebuild and rejects unsupported/colliding/boundary-violating layouts.
- [ ] Diagnostics expose real native tracker full rebuilds and incremental updates from the actual solve, not only final validation rebuilds.

## D. Native search parity hardening

- [ ] `native_search_placement` or equivalent considers all eligible sheets/containers for a target, not only `cur.sheet_index`.
- [ ] Search considers all allowed rotations for the instance.
- [ ] Search has global/container-wide candidates.
- [ ] Search has focused candidates around current placement / colliding neighborhood.
- [ ] Search has coordinate descent or equivalent refinement on top candidates.
- [ ] Candidate evaluation reuses `CdeCandidateSession` or a native batch CDE equivalent for fixed same-sheet hazards.
- [ ] Search score is quantified CDE loss, not only colliding item count.
- [ ] Diagnostics distinguish global samples, focused samples, refined samples, coord-descent steps, unsupported samples, best eval.

## E. Native worker/separation parity hardening

- [ ] `move_items_multi` or equivalent creates multiple worker snapshots/states from native `SparrowState`.
- [ ] Workers can evaluate different target orderings / seeds / candidate choices.
- [ ] Workers produce candidate states with raw + weighted loss.
- [ ] The master loads back the best worker candidate deterministically.
- [ ] Rejected candidates rollback cleanly.
- [ ] Separator no-improve/strike behavior works on native state.
- [ ] GLS update is applied after no-improve/worker rounds in a Sparrow-like manner.
- [ ] Diagnostics expose worker count, worker candidate evaluations, commits, rollbacks, best loss, targets attempted/accepted/rejected.

## F. Exploration / disruption

- [ ] Exploration pool stores native layouts/solutions/states, not old VRS snapshots.
- [ ] Restore is biased toward least-infeasible native states.
- [ ] Disruption is stronger than swapping only the two largest items. It should include at least one additional geometry-aware or container-aware perturbation.
- [ ] Exploration remains focused on feasibility/separation, not compression.

## G. Runtime gates

- [ ] Medium native CDE gate passes: 12/12 placed, final pairs 0, boundary 0, no fallback, no compression.
- [ ] LV8 12 part types × 1 quantity smoke is attempted and reported.
- [ ] LV8 smoke uses the real fixture `tests/fixtures/nesting_engine/ne2_input_lv8jav.json` converted to v1 solver input, outer-only, quantity=1 per type.
- [ ] LV8 smoke reports placed/required, final pairs, boundary, native flags, search/tracker/worker diagnostics, runtime.
- [ ] If LV8 fails, report exact failure and do not fake PASS; medium must still pass.

## H. Required commands

- [ ] `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release`
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`
- [ ] `python3 scripts/smoke_sgh_q24r6_native_sparrow_tracker_search_parity_hardening.py`
- [ ] `./scripts/check.sh`

## Reject conditions

Reject if any is true:

- [ ] production `sparrow_cde` reuses old VRS core as a dependency;
- [ ] tracker remains binary count-only;
- [ ] search is current-sheet-only;
- [ ] worker logic is still a single sequential pass without snapshot/competition/load-back;
- [ ] compression is enabled or needed for default PASS;
- [ ] medium gate passes through legacy, LBF, bbox truth, or fallback;
- [ ] task mainly produces docs/reports/scripts instead of Rust core changes;
- [ ] LV8 12×1 is skipped without concrete blocker evidence.
