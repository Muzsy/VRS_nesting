# SGH-Q23R2 — Real Sparrow cutover completion package

This package is a **REVISE-fix implementation task** for Q23R1. It is not an audit task.

Q23R1 made real progress (solve-scoped CDE decision/prepared-geometry cache), but it did **not** complete the cutover:

- `SGH-Q23R1_STATUS: REVISE`
- production default still legacy
- medium CDE fixture not converged (`0/12`, residual collision pairs)
- CDE engine build reduction only ~45%, not the required ≥80%
- graph still O(n²) snapshot
- no true multi-target/move_items_multi Sparrow pass
- no fixed-sheet exploration/compression lifecycle

Q23R2 must implement the remaining production cutover, not document it.

Start from:

```bash
codex/prompts/egyedi_solver/sgh_q23r2_real_sparrow_cutover_completion/run.md
```

Expected result:

- production Phase1 default routes to `sparrow_cde`
- legacy is explicit opt-in only
- medium CDE fixture converges 12/12 with zero final collisions
- single-engine multi-hazard CDE query path replaces N pairwise builds in candidate evaluation
- incremental collision graph replaces full O(n²) snapshot on every move
- multi-target/multi-worker Sparrow pass is active
- fixed-sheet exploration/compression is implemented
- no bbox/LBF/legacy fallback in production Sparrow mode
