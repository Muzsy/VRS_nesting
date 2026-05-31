# SGH-Q24R3 — Native Sparrow lifecycle parity without compression

This package defines the next VRS_nesting task after SGH-Q24R2.

The task is **coding-first** and **parity-first**. It is not a benchmark campaign, not a bbox topic, and not a compression-hardening task.

## Controlling objective

After this task, the production `sparrow_cde` solver must behave like the current local `.cache/sparrow` / jagua_rs/Sparrow optimizer lifecycle **except for the compression phase**, which is intentionally out of scope for now.

Compression must not consume the main implementation effort. For fixed-sheet multisheet nesting it is only meaningful later, primarily on the last partially used sheet after the full solver lifecycle is correct.

## Start here

```bash
codex/prompts/egyedi_solver/sgh_q24r3_native_sparrow_lifecycle_parity_no_compression/run.md
```

## Required deliverables

- Real Rust code changes in the production `sparrow_cde` path.
- A fixed-sheet native Sparrow model or an equivalent fully explicit adapter layer.
- CDE-backed tracker/loss quantification, not surrogate bbox-derived loss as the decisive separation loss.
- Production search depth restored to Sparrow-like behavior under CDE using active-set/session support where needed.
- CDE medium 12/12 convergence restored as a hard gate.
- Compression excluded from the PASS criteria and from the production default lifecycle for now.

## Main files expected to change

```text
rust/vrs_solver/src/optimizer/sparrow.rs
rust/vrs_solver/src/optimizer/search_position.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/collision_severity.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/io.rs
```

A split module tree is allowed and preferred if `sparrow.rs` remains oversized:

```text
rust/vrs_solver/src/optimizer/sparrow/mod.rs
rust/vrs_solver/src/optimizer/sparrow/state.rs
rust/vrs_solver/src/optimizer/sparrow/problem.rs
rust/vrs_solver/src/optimizer/sparrow/tracker.rs
rust/vrs_solver/src/optimizer/sparrow/separator.rs
rust/vrs_solver/src/optimizer/sparrow/worker.rs
rust/vrs_solver/src/optimizer/sparrow/explore.rs
rust/vrs_solver/src/optimizer/sparrow/search.rs
```

Do not create empty wrapper modules. If modules are split, they must contain real implementation.

## Reject if

- The task mainly changes reports, smoke scripts, docs, or diagnostics.
- The task mainly works on compression.
- The task mainly works on bbox exclusion.
- CDE medium 12-item convergence remains intentionally deferred.
- The production path still relies on toy search budgets to avoid timeout.
- The tracker still uses bbox/surrogate loss as the decisive CDE separation loss.
- The implementation cannot map the current `.cache/sparrow` optimizer functions to VRS equivalents.
