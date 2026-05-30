# SGH-Q23R1 package — Production Sparrow cutover implementation

This package is the implementation follow-up to Q23.

Q23 established a partial `sparrow_cde` production path but ended with `REVISE` because medium CDE convergence was blocked by per-call CDE and incomplete Sparrow lifecycle parity.

This R1 task is not another audit. It must implement the missing production cutover pieces:

```text
solve-scoped CDE/Jagua session/cache
incremental collision graph
multi-target Sparrow pass
GLS/stagnation/disruption lifecycle
fixed-sheet exploration/compression
production `sparrow_cde` routing/default
legacy solver quarantine
medium CDE convergence gate
```

## Required local reference

```text
.cache/sparrow
```

This folder is gitignored and is intentionally not in the package. The executing agent must inspect it locally.

## Files

```text
canvases/egyedi_solver/sgh_q23r1_production_sparrow_cutover_implementation.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q23r1_production_sparrow_cutover_implementation.yaml
codex/prompts/egyedi_solver/sgh_q23r1_production_sparrow_cutover_implementation/run.md
codex/codex_checklist/egyedi_solver/sgh_q23r1_production_sparrow_cutover_implementation.md
README_SGH_Q23R1_PRODUCTION_SPARROW_CUTOVER_IMPLEMENTATION_PACKAGE.md
```

## Main acceptance idea

PASS means the normal production solve route has moved to a real fixed-sheet Sparrow/CDE solver and the Q23 medium fixture converges without legacy fallback.

If full cutover cannot be completed, the result must be `REVISE` with concrete blockers, but only after substantial implementation work. A report-only REVISE is not acceptable unless `.cache/sparrow` is missing or an external dependency is broken.
