# SGH-Q24R4 — Native Sparrow model cutover package

This package defines the next VRS_nesting task after SGH-Q24R3.

The task is **coding-first** and **model-cutover-first**. Its purpose is not to add another adapter layer, not to polish diagnostics, and not to tune compression. The purpose is to remove the old VRS solver-core model from the production `sparrow_cde` path and make a Sparrow-native `Problem` / `SPInstance` / `Layout` / `Solution` / `CollisionTracker` model the only production truth.

## Start here

```bash
codex/prompts/egyedi_solver/sgh_q24r4_native_sparrow_model_cutover/run.md
```

## Controlling objective

After this task, production `sparrow_cde` must no longer run on `WorkingLayout` + `Placement` + `VrsCollisionTracker` as its internal truth model. The only allowed conversion from VRS structures is a one-way I/O normalization step:

```text
SolverInput / stocks / parts / rotation policy
  -> SparrowProblem + SPInstance + SparrowLayout/Solution
  -> Sparrow-native lifecycle
  -> SolverOutput-compatible projection
```

That projection is not a retained VRS adapter model. It is only API compatibility at the boundary.

## Main expected code movement

Prefer converting the current monolithic file:

```text
rust/vrs_solver/src/optimizer/sparrow.rs
```

into a real module tree:

```text
rust/vrs_solver/src/optimizer/sparrow/mod.rs
rust/vrs_solver/src/optimizer/sparrow/problem.rs
rust/vrs_solver/src/optimizer/sparrow/instance.rs
rust/vrs_solver/src/optimizer/sparrow/layout.rs
rust/vrs_solver/src/optimizer/sparrow/solution.rs
rust/vrs_solver/src/optimizer/sparrow/tracker.rs
rust/vrs_solver/src/optimizer/sparrow/state.rs
rust/vrs_solver/src/optimizer/sparrow/optimizer.rs
rust/vrs_solver/src/optimizer/sparrow/separator.rs
rust/vrs_solver/src/optimizer/sparrow/worker.rs
rust/vrs_solver/src/optimizer/sparrow/explore.rs
rust/vrs_solver/src/optimizer/sparrow/search.rs
rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs
rust/vrs_solver/src/optimizer/sparrow/rng.rs
```

If Rust module resolution complains, remove/rename the old `sparrow.rs` and expose the module directory through `optimizer/mod.rs` as `pub mod sparrow;`.

## Reject if

- Production `sparrow_cde` still creates a `WorkingLayout` before entering the Sparrow optimizer.
- Production `sparrow_cde` still uses `VrsCollisionTracker` as the main tracker.
- Production `sparrow_cde` still treats `crate::io::Placement` as the internal layout item type instead of only output projection.
- The task creates a new wrapper that simply hides `WorkingLayout`/`VrsCollisionTracker` behind Sparrow-like names.
- The main diff is docs, smoke scripts, reports, bbox rhetoric, or compression.
- Medium CDE succeeds only because search/compression/fallback was weakened or rerouted.
- Legacy/phase/multisheet/row-cursor code remains callable from the production `sparrow_cde` solve path.
