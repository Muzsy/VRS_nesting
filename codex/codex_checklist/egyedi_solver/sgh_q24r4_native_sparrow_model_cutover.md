# SGH-Q24R4 checklist — Native Sparrow model cutover

## Purpose

Cut the production `sparrow_cde` path away from the old VRS solver-core model and move it to native Sparrow solver structures.

## Acceptance checklist

### A. Reference and cutover plan

- [ ] Read `.cache/sparrow` current code, at minimum:
  - `.cache/sparrow/src/optimizer/mod.rs`
  - `.cache/sparrow/src/optimizer/separator.rs`
  - `.cache/sparrow/src/optimizer/worker.rs`
  - `.cache/sparrow/src/optimizer/explore.rs`
  - `.cache/sparrow/src/sample/search.rs`
  - `.cache/sparrow/src/quantify/tracker.rs`
- [ ] Create `docs/egyedi_solver/sgh_q24r4_native_sparrow_model_cutover_map.md`.
- [ ] The map must show old Q24R3 VRS-core concepts and their Q24R4 native replacement.

### B. Native module tree

- [ ] Replace or split `rust/vrs_solver/src/optimizer/sparrow.rs` into a real native module tree.
- [ ] Define a native `SparrowProblem` / `FixedSheetSparrowProblem` equivalent.
- [ ] Define native `SPInstance` with stable id/index and geometry/rotation metadata.
- [ ] Define native `SparrowLayout` that does not store `crate::io::Placement` as its internal item.
- [ ] Define native `SparrowSolution` / feasible-infeasible incumbent state.
- [ ] Define native `SparrowCollisionTracker` that is not a rename/wrapper over `VrsCollisionTracker`.
- [ ] Define native snapshot/restore semantics for layout+tracker+weights.

### C. Production path cutover

- [ ] In `rust/vrs_solver/src/adapter.rs`, production `run_sparrow_pipeline` no longer constructs `WorkingLayout` before calling the Sparrow optimizer.
- [ ] `run_sparrow_pipeline` converts input once into native `SparrowProblem`.
- [ ] The optimizer returns a native `SparrowResult` / `SparrowSolution`.
- [ ] Only after solve completion is the result projected into `Vec<crate::io::Placement>` and `Vec<Unplaced>`.
- [ ] No legacy/phase/multisheet/row-cursor fallback is reachable from production `sparrow_cde`.

### D. Tracker and CDE truth

- [ ] Native tracker owns pair/container/boundary loss state.
- [ ] Native tracker uses CDE-backed evaluation as decisive truth for production `sparrow_cde`.
- [ ] GLS weights live in the native tracker or native solver state, not in `VrsCollisionTracker`.
- [ ] `colliding_indices`, item weighted loss, total raw loss, total weighted loss, save/restore, update-after-move all use the same native state.
- [ ] Final success still runs full CDE validation over all placements/sheets.

### E. Search/separation/exploration lifecycle

- [ ] Separation runs over native layout + native tracker.
- [ ] Worker snapshots load from native master state.
- [ ] Worker accepted/rejected moves update native tracker state coherently.
- [ ] Exploration pool stores native solutions/states, not `WorkingLayout` snapshots.
- [ ] Restore/disrupt/separate operates on native states.
- [ ] Compression remains disabled/gated and is not required for PASS.

### F. Static anti-hybrid gate

- [ ] Add `scripts/smoke_sgh_q24r4_native_sparrow_model_cutover.py`.
- [ ] The smoke must fail if production `optimizer/sparrow` native modules import/use:
  - `WorkingLayout`
  - `VrsCollisionTracker`
  - `PhaseOptimizer`
  - `MultiSheetManager`
  - `build_initial_layout_with_rotation_context`
- [ ] The smoke must allow `crate::io::Placement` only in boundary projection/output code, not in native layout/tracker/search modules.

### G. Runtime gate

- [ ] `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release` passes.
- [ ] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` passes.
- [ ] `python3 scripts/smoke_sgh_q24r4_native_sparrow_model_cutover.py` passes.
- [ ] Existing Q24R3 medium CDE hard gate still passes:
  - 12/12 placed,
  - final collision pairs 0,
  - final boundary violations 0,
  - backend `cde_adapter`,
  - compression passes 0/default gated.

## Reject conditions

Reject the task if any is true:

- [ ] Main production `sparrow_cde` path still runs on `WorkingLayout`.
- [ ] Main production `sparrow_cde` path still runs on `VrsCollisionTracker`.
- [ ] New native types are thin wrappers around old VRS core types.
- [ ] `crate::io::Placement` remains the internal layout placement type.
- [ ] The implementation adds another adapter layer instead of deleting the old core dependency.
- [ ] The task mostly changes documentation/scripts/reports.
- [ ] Compression becomes the way to pass the medium gate.
- [ ] Legacy fallback remains callable from production `sparrow_cde`.
