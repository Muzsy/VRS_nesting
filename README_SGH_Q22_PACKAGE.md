# SGH-Q22 package — Real SparrowState + separation kernel

This is the next serious implementation task after Q21R1.

## Purpose

Implement the first explicit, testable `sparrow_experimental` solver mode in the Rust solver.

This task is intentionally larger than the previous repair tasks. It must introduce:

```text
SparrowState
infeasible layout lifecycle
CollisionGraphSnapshot
GLS-guided separation loop
search_position relocation
backend-oracle evaluation
commit/rollback
final backend validation
measurement smoke + quick benchmark
```

## Why now

Q20R/R1 added a search_position kernel with top-k coordinate descent. Q21R1 added improved backend-oracle collision severity. The missing core is now the actual Sparrow-style state and separation lifecycle.

## Files

```text
canvases/egyedi_solver/sgh_q22_sparrow_state_separation_kernel.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q22_sparrow_state_separation_kernel.yaml
codex/prompts/egyedi_solver/sgh_q22_sparrow_state_separation_kernel/run.md
codex/codex_checklist/egyedi_solver/sgh_q22_sparrow_state_separation_kernel.md
README_SGH_Q22_PACKAGE.md
```

## Hard rule

Do not relabel `phase_optimizer` as Sparrow. PASS requires a real, adapter-routed, measured `sparrow_experimental` kernel.
