# SGH-Q24R2 — Native Sparrow core port implementation package

This is a **coding-first** task. It is not a benchmark task and not another CDE micro-optimization task.

The objective is to replace the current partial `sparrow_cde` lifecycle with a faithful fixed-sheet adaptation of the original `jagua_rs`/`Sparrow` optimizer structure.

The coding agent must not drift into:

- only adding tests/reports;
- only tuning timeout limits;
- only optimizing CDE session reuse;
- only changing diagnostics;
- only discussing bbox.

The task is complete only if the actual solver lifecycle is rewritten/ported around the original Sparrow structure:

- Algorithm 11 style optimizer orchestration;
- Algorithm 9 style separator with strike/no-improvement loop;
- Algorithm 10 style multi-worker `move_items_multi`;
- Algorithm 5 style worker `move_items` over all currently colliding items;
- Algorithm 12 style exploration pool + biased restore + disruption;
- Algorithm 13 style compression restore/pressure/separate/accept lifecycle;
- Algorithm 6 style search placement with container sampling, focused sampling, BestSamples, and coordinate descent.

Start from:

```bash
codex/prompts/egyedi_solver/sgh_q24r2_native_sparrow_core_port/run.md
```

Expected implementation focus:

- `rust/vrs_solver/src/optimizer/sparrow.rs`, or a split `optimizer/sparrow/*` module tree.
- `rust/vrs_solver/src/optimizer/search_position.rs` only if needed for true Sparrow search parity.
- `rust/vrs_solver/src/optimizer/cde_adapter.rs` only as support for the new lifecycle, not as the main deliverable.
- `rust/vrs_solver/src/adapter.rs` only to wire the new native lifecycle.

PASS is forbidden if the only meaningful Rust changes are in `cde_adapter.rs`, `cde_observability.rs`, reports, or benchmark scripts.
