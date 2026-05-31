# SGH-Q24R5 — Architectural native Sparrow cutover package

This package is the next task after SGH-Q24R4 returned `REVISE`.

Q24R4 proved one thing clearly: the old VRS solver-core model is still the real production truth behind `sparrow_cde`. This task is therefore **not** another audit, map, wrapper, benchmark, or diagnostics pass. It is the architectural cut.

## Start here

```bash
codex/prompts/egyedi_solver/sgh_q24r5_architectural_native_sparrow_cutover/run.md
```

## Controlling objective

After this task, production `sparrow_cde` must run through a native Sparrow core:

```text
SolverInput / sheets / parts / policy
  -> SparrowProblem
  -> SparrowOptimizer::solve(...)
  -> SparrowSolution / SparrowSolveResult
  -> native final CDE validation
  -> SolverOutput projection
```

The old route is forbidden:

```text
build_constructive_seed_layout(...)
  -> WorkingLayout::new(...)
  -> SparrowSeparationKernel::run(...)
  -> VrsCollisionTracker
  -> WorkingLayout final commit
```

## What is allowed to remain temporarily

The public API/input-output structures may remain. Legacy solver files may remain only as quarantined, non-production code while tests are being migrated.

Allowed boundary only:

```text
VRS JSON/API structures -> native SparrowProblem
native SparrowSolution -> VRS-compatible SolverOutput
```

Forbidden: preserving a VRS-adapter-like model inside the solver core or leaving a reachable production escape hatch to it.

## Compression

Compression remains out of scope. Do not spend the task on compression. Default production `sparrow_cde` must still solve the required medium CDE gate with compression disabled/zero-pass.

## Reject if

- `run_sparrow_pipeline` still constructs `WorkingLayout` before solve.
- production `optimizer/sparrow` still imports or uses `WorkingLayout`.
- production `optimizer/sparrow` still imports or uses `VrsCollisionTracker`.
- native types are only aliases/wrappers around old VRS types.
- `crate::io::Placement` remains the internal layout placement type.
- the task mainly produces docs/reports/scripts instead of code.
- Q24R5 returns another “map-only REVISE”.
- the medium CDE gate is recovered by re-enabling legacy fallback, LBF fallback, bbox truth, or compression.
